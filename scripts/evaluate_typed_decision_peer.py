"""Run the official thisthat inference API on a pinned typed-decision diagnostic.

This is an evaluation-only adapter. It never writes training data or changes a model.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
import time
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def calibration_metrics(targets: list[int], probabilities: list[list[float]], bins: int = 15) -> dict:
    nll = brier = 0.0
    correct = 0
    buckets = [[0, 0.0, 0.0] for _ in range(bins)]
    for target, probs in zip(targets, probabilities):
        if not probs or not 0 <= target < len(probs):
            raise ValueError("target does not match probability vector")
        if any(not math.isfinite(p) or p < 0 for p in probs) or not math.isclose(sum(probs), 1.0, abs_tol=1e-6):
            raise ValueError("invalid probability vector")
        prediction = max(range(len(probs)), key=probs.__getitem__)
        correct += int(prediction == target)
        nll -= math.log(max(probs[target], 1e-15))
        brier += sum((p - int(index == target)) ** 2 for index, p in enumerate(probs))
        confidence = probs[prediction]
        bucket = buckets[min(int(confidence * bins), bins - 1)]
        bucket[0] += 1
        bucket[1] += confidence
        bucket[2] += int(prediction == target)
    ece = sum(abs(conf - acc) for count, conf, acc in buckets if count) / len(targets)
    return {"count": len(targets), "accuracy": correct / len(targets), "nll": nll / len(targets),
            "multiclass_brier": brier / len(targets), "top_label_ece": ece, "ece_bins": bins}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-code", type=Path, required=True)
    parser.add_argument("--reference-commit", required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--model-revision", required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    parser.add_argument("--temperature", type=float, default=1.0)
    parser.add_argument("--max-state-tokens", type=int, default=1536)
    args = parser.parse_args()

    for path in (args.reference_code, args.model, args.input):
        if not path.exists():
            raise FileNotFoundError(path)
    if args.output.exists():
        raise FileExistsError(args.output)
    if args.temperature <= 0 or args.max_state_tokens <= 0:
        raise ValueError("temperature and state token limit must be positive")

    sys.path.insert(0, str(args.reference_code.resolve()))
    from thisthat import Question, TypedDecider
    from thisthat.prompt import build
    from transformers import AutoTokenizer
    import torch
    import psutil

    source_rows = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    ids = [row.get("id") for row in source_rows]
    if not source_rows or any(not isinstance(row_id, str) or not row_id for row_id in ids) or len(ids) != len(set(ids)):
        raise ValueError("input rows must have distinct nonempty IDs")
    for row in source_rows:
        if not isinstance(row.get("state"), str) or not isinstance(row.get("question"), str):
            raise ValueError(f"invalid state/question for {row.get('id')}")
        options = row.get("options")
        answer = row.get("answer_index")
        if answer is None and isinstance(row.get("target"), list):
            target = row["target"]
            if target and all(value in (0, 1, 0.0, 1.0) for value in target) and sum(target) == 1:
                answer = target.index(1 if 1 in target else 1.0)
        if not isinstance(options, list) or not 2 <= len(options) <= 255 or type(answer) is not int or not 0 <= answer < len(options):
            raise ValueError(f"invalid options/answer_index for {row.get('id')}")

    tokenizer = AutoTokenizer.from_pretrained(args.model, local_files_only=True)
    lengths = []
    state_lengths = []
    for row in source_rows:
        question = Question(row["question"], tuple(row["options"]))
        rendered = build(tokenizer, row["state"], [question], max_state_tokens=args.max_state_tokens)
        lengths.append(len(rendered["ids"]))
        state_lengths.append(len(tokenizer.encode(row["state"], add_special_tokens=False)))
    truncated = sum(length > args.max_state_tokens for length in state_lengths)
    if truncated:
        raise ValueError(f"{truncated} states exceed the reference's {args.max_state_tokens}-token state limit")
    model_limit = getattr(tokenizer, "model_max_length", None)
    if isinstance(model_limit, int) and model_limit < 1_000_000_000 and max(lengths) > model_limit:
        raise ValueError(f"rendered input length {max(lengths)} exceeds model limit {model_limit}")

    if args.device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable")
    decider = TypedDecider.from_pretrained(str(args.model.resolve()), device=args.device,
                                           local_files_only=True)
    if args.device == "cuda":
        torch.cuda.reset_peak_memory_stats()
    observations = []
    latencies = []
    with torch.inference_mode():
        for index, row in enumerate(source_rows, start=1):
            question = Question(row["question"], tuple(row["options"]))
            decider.backend.synchronize()
            started = time.perf_counter()
            result = decider.decide(row["state"], question, temperature=args.temperature,
                                    max_state_tokens=args.max_state_tokens)
            decider.backend.synchronize()
            elapsed = time.perf_counter() - started
            latencies.append(elapsed)
            if len(result.probabilities) != len(row["options"]):
                raise ValueError(f"option count mismatch for {row['id']}")
            observations.append({"id": row["id"], "family": row["family"], "prediction_index": result.index,
                                 "prediction": result.choice, "probabilities": list(result.probabilities),
                                 "latency_seconds": elapsed})
            if index % 100 == 0:
                print(f"{index}/{len(source_rows)}", flush=True)

    targets = [row["answer_index"] if "answer_index" in row else row["target"].index(1) for row in source_rows]
    vectors = [row["probabilities"] for row in observations]
    by_family = {}
    for row, target, observation in zip(source_rows, targets, observations):
        stat = by_family.setdefault(row["family"], {"correct": 0, "count": 0})
        stat["correct"] += int(observation["prediction_index"] == target)
        stat["count"] += 1
    for stat in by_family.values():
        stat["accuracy"] = stat["correct"] / stat["count"]

    result = {"status": "complete", "model": str(args.model.resolve()), "model_revision": args.model_revision,
              "model_sha256": sha256(args.model / "model.safetensors"),
              "reference_code": str(args.reference_code.resolve()), "reference_commit": args.reference_commit,
              "input": str(args.input.resolve()), "input_sha256": sha256(args.input), "rows": len(source_rows),
              "device": decider.device, "dtype": str(next(decider.model.parameters()).dtype),
              "temperature": args.temperature, "prompt_layout": "official thisthat state_first",
              "max_state_tokens": args.max_state_tokens,
              "token_profile": {"max_state_tokens_observed": max(state_lengths),
                                 "max_rendered_tokens": max(lengths), "truncated_states": truncated},
              "metrics": calibration_metrics(targets, vectors),
              "latency_seconds": {"mean": statistics.mean(latencies), "median": statistics.median(latencies),
                                  "p95": sorted(latencies)[int(0.95 * len(latencies)) - 1]},
              "memory": {"process_peak_working_set_bytes": getattr(psutil.Process().memory_info(), "peak_wset", None),
                         "gpu_allocated_peak_bytes": torch.cuda.max_memory_allocated() if args.device == "cuda" else None,
                         "gpu_reserved_peak_bytes": torch.cuda.max_memory_reserved() if args.device == "cuda" else None},
              "per_family": by_family, "predictions": observations,
              "limitations": ["public task-family-matched diagnostic; not an independent or sealed SOTA test",
                              "same rows as published card, but locally run with pinned code/model and local runtime",
                              "training-overlap with the benchmark's rule-structure families is unverified"]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "rows": len(source_rows), **result["metrics"],
                      "mean_latency_seconds": statistics.mean(latencies),
                      "model_sha256": result["model_sha256"], "input_sha256": result["input_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
