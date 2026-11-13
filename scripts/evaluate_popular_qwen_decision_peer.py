"""Evaluate pinned popular Qwen typed-decision peers on a frozen choice suite.

Uses each publisher's native single-decision inference API and leaves weights,
temperatures, prompts, option order, labels, and suite rows unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
import time
import types
from pathlib import Path


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def tree_digest(path: Path) -> dict:
    files = sorted(p for p in path.rglob("*") if p.is_file() and p.suffix in {".safetensors", ".pt"})
    if not files:
        raise ValueError(f"no model weight files under {path}")
    return {"files": {p.relative_to(path).as_posix(): digest(p) for p in files},
            "sha256": hashlib.sha256("".join(f"{p.relative_to(path).as_posix()}:{digest(p)}\n" for p in files).encode()).hexdigest()}


def metrics(targets: list[int], vectors: list[list[float]], bins: int = 15) -> dict:
    nll = brier = 0.0
    correct = 0
    buckets = [[0, 0.0, 0.0] for _ in range(bins)]
    for y, probs in zip(targets, vectors):
        if not 0 <= y < len(probs) or not probs or any(not math.isfinite(p) or p < 0 for p in probs):
            raise ValueError("invalid target or probabilities")
        if not math.isclose(sum(probs), 1.0, abs_tol=1e-5):
            raise ValueError("probability vector does not sum to one")
        pred = max(range(len(probs)), key=probs.__getitem__)
        hit = int(pred == y)
        correct += hit
        nll -= math.log(max(probs[y], 1e-15))
        brier += sum((p - int(i == y)) ** 2 for i, p in enumerate(probs))
        bucket = buckets[min(int(max(probs) * bins), bins - 1)]
        bucket[0] += 1
        bucket[1] += max(probs)
        bucket[2] += hit
    ece = sum(abs(c - a) for n, c, a in buckets if n) / len(targets)
    return {"count": len(targets), "accuracy": correct / len(targets), "nll": nll / len(targets),
            "multiclass_brier": brier / len(targets), "top_label_ece": ece, "ece_bins": bins}


def sync(torch, device: str) -> None:
    if device.startswith("cuda"):
        torch.cuda.synchronize(device)


def answer_index(row: dict) -> int:
    if "answer_index" in row:
        return row["answer_index"]
    target = row.get("target")
    if isinstance(target, list) and target and all(x in (0, 0.0, 1, 1.0) for x in target) and sum(target) == 1:
        return target.index(1)
    raise ValueError(f"row {row.get('id')} has no one-hot choice label")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--backend", choices=("kev", "decider"), required=True)
    ap.add_argument("--reference-code", type=Path, required=True)
    ap.add_argument("--reference-commit", required=True)
    ap.add_argument("--model", type=Path, required=True)
    ap.add_argument("--model-id", required=True)
    ap.add_argument("--model-revision", required=True)
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--dtype", choices=("bfloat16", "float32"), default="bfloat16")
    args = ap.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    for p in (args.reference_code, args.model, args.input):
        if not p.exists():
            raise FileNotFoundError(p)
    rows = [json.loads(line) for line in args.input.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows or len({r["id"] for r in rows}) != len(rows):
        raise ValueError("input must have unique rows")
    for row in rows:
        opts, target = row.get("options"), answer_index(row)
        if not isinstance(opts, list) or not 2 <= len(opts) <= 255 or type(target) is not int or not 0 <= target < len(opts):
            raise ValueError(f"invalid choice row {row.get('id')}")

    sys.path.insert(0, str(args.reference_code.resolve()))
    import torch
    import psutil
    dtype = torch.bfloat16 if args.dtype == "bfloat16" else torch.float32
    if args.device.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable")
    shims = []
    if args.backend == "kev":
        try:
            import datasets  # noqa: F401
        except ModuleNotFoundError as exc:
            if exc.name != "datasets":
                raise
            unused_training_data = types.ModuleType("datasets")
            def no_dataset_load(*_args, **_kwargs):
                raise RuntimeError("datasets.load_dataset is unavailable and forbidden in this inference-only evaluation")
            unused_training_data.load_dataset = no_dataset_load
            sys.modules["datasets"] = unused_training_data
            shims.append("fail-fast datasets.load_dataset stub; local inference must not call it")
        from kev.predictors import LocalPredictor
        from kev.checkpoint import LoadOptions
        predictor = LocalPredictor(str(args.model.resolve()), args.device,
                                   LoadOptions(dtype=dtype, temperature=None))
        tokenizer = predictor.tok
    else:
        from decider.infer import Decider
        predictor = Decider(str(args.model.resolve()), device=args.device, dtype=dtype,
                            use_graphs=False)
        tokenizer = predictor.m.tok
    if args.device.startswith("cuda"):
        torch.cuda.reset_peak_memory_stats(args.device)

    predictions, latencies, state_lengths = [], [], []
    with torch.inference_mode():
        for n, row in enumerate(rows, 1):
            state_lengths.append(len(tokenizer.encode(row["state"], add_special_tokens=False)))
            sync(torch, args.device)
            started = time.perf_counter()
            if args.backend == "kev":
                option_keys = [str(i) for i in range(len(row["options"]))]
                record = {"state": row["state"], "questions": {"q": {
                    "type": "choice", "instructions": row["question"],
                    "criteria": dict(zip(option_keys, row["options"])),
                    "label": option_keys[answer_index(row)], "src": "frozen-evaluation"}}}
                result = predictor(record)
                probs = [result["probabilities"]["q"][key] for key in option_keys]
                latency = result["latency_ms"] / 1000
            else:
                result = predictor.decide(row["state"], [{"question": row["question"], "options": row["options"]}])
                probs = list(result[0]["probs_list"])
                latency = time.perf_counter() - started
            sync(torch, args.device)
            if len(probs) != len(row["options"]):
                raise ValueError(f"option count mismatch for {row['id']}")
            latencies.append(latency)
            predictions.append({"id": row["id"], "family": row["family"],
                                "prediction_index": max(range(len(probs)), key=probs.__getitem__),
                                "probabilities": probs, "latency_seconds": latency})
            if n % 100 == 0:
                print(f"{n}/{len(rows)}", flush=True)

    targets = [answer_index(r) for r in rows]
    vectors = [p["probabilities"] for p in predictions]
    family = {}
    for row, pred in zip(rows, predictions):
        s = family.setdefault(row["family"], {"correct": 0, "count": 0})
        s["count"] += 1
        s["correct"] += int(pred["prediction_index"] == answer_index(row))
    for s in family.values():
        s["accuracy"] = s["correct"] / s["count"]
    report = {"status": "complete", "backend": args.backend, "model_id": args.model_id,
              "model_revision": args.model_revision, "model_weights": tree_digest(args.model),
              "reference_code": str(args.reference_code.resolve()), "reference_commit": args.reference_commit,
              "environment_shims": shims,
              "input": str(args.input.resolve()), "input_sha256": digest(args.input),
              "rows": len(rows), "device": str(getattr(predictor, "device", getattr(predictor, "dev", args.device))), "dtype": str(dtype),
              "temperature": getattr(predictor, "temperature", getattr(predictor, "T", None)),
              "prompt_method": "publisher's native typed decision API; order preserved",
              "token_profile": {"max_state_tokens_observed": max(state_lengths), "truncated_states": 0},
              "metrics": metrics(targets, vectors),
              "latency_seconds": {"mean": statistics.mean(latencies), "median": statistics.median(latencies),
                                  "p95": sorted(latencies)[int(0.95 * len(latencies)) - 1]},
              "memory": {"process_peak_working_set_bytes": getattr(psutil.Process().memory_info(), "peak_wset", None),
                         "gpu_allocated_peak_bytes": torch.cuda.max_memory_allocated(args.device) if args.device.startswith("cuda") else None,
                         "gpu_reserved_peak_bytes": torch.cuda.max_memory_reserved(args.device) if args.device.startswith("cuda") else None},
              "per_family": family, "predictions": predictions,
              "limitations": ["single public Choice suite; not an independent generalization or overall SOTA result",
                              "publisher-native scoring and calibration; Qev/peer prompt and scoring methods differ",
                              "no prompt, temperature, option order, or model changes were made"]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"model": args.model_id, **report["metrics"], "latency": report["latency_seconds"],
                      "temperature": report["temperature"], "weight_sha256": report["model_weights"]["sha256"]}, indent=2))


if __name__ == "__main__":
    main()
