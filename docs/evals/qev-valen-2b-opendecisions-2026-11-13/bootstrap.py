"""Reproduce the paired family-cluster profile from adjacent prediction files."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import random
from collections import defaultdict
from pathlib import Path

ARTIFACTS = Path(__file__).resolve().parent
ROOT = ARTIFACTS.parents[2]
SCORER = ROOT / "data/general-decision-eval/open-decisions/score.py"
DATA = ROOT / "data/general-decision-eval/open-decisions/opendecisions.jsonl"
QEV = ARTIFACTS / "qev-predictions.jsonl"
VALEN = ARTIFACTS / "valen-predictions.jsonl"
OUT = ARTIFACTS / "receipt.json"
N = 5000
SEED = 20261113

spec = importlib.util.spec_from_file_location("odscore", SCORER)
od = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(od)


def read(path: Path):
    # Match the pinned scorer's physical JSONL framing; str.splitlines() also
    # treats Unicode separators inside serialized strings as record boundaries.
    return [json.loads(line) for line in path.read_text(encoding="utf-8").split("\n") if line.strip()]


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


tasks = read(DATA)
qev_rows = {x["id"]: x["probs"] for x in read(QEV)}
valen_rows = {x["id"]: x["probs"] for x in read(VALEN)}
assert len(tasks) == len(qev_rows) == len(valen_rows) == 2352
assert {t["id"] for t in tasks} == set(qev_rows) == set(valen_rows)

outcomes = {}
probabilities = {}
for task in tasks:
    tid = task["id"]
    qp = od.normalized(task, qev_rows[tid])
    vp = od.normalized(task, valen_rows[tid])
    outcomes[tid] = (od.item_outcome(task, qp), od.item_outcome(task, vp))
    probabilities[tid] = (qp, vp)


def metrics(sample):
    result = []
    for mi in (0, 1):
        os_ = [outcomes[tid][mi] for tid in sample]
        summary = od.summary(os_)
        nll, brier = [], []
        for tid in sample:
            task = next_by_id[tid]
            probs = probabilities[tid][mi]
            labels = task["labels"]
            expected = task["expected"]
            if task["question"]["type"] == "score":
                expected = str(int(expected))
            nll.append(-math.log(max(probs[expected], 1e-15)))
            brier.append(sum((probs[label] - (1.0 if label == expected else 0.0)) ** 2 for label in labels))
        result.append({
            "capability": summary["capability"],
            "intelligence": summary["intelligence"],
            "calibration": summary["calibration"],
            "accuracy_choice": summary["accuracy_per_type"]["choice"],
            "accuracy_noul": summary["accuracy_per_type"]["noul"],
            "accuracy_score": summary["accuracy_per_type"]["score"],
            "competence_choice": summary["competence_per_type"]["choice"],
            "competence_noul": summary["competence_per_type"]["noul"],
            "competence_score": summary["competence_per_type"]["score"],
            "calibration_choice": summary["calibration_per_type"]["choice"],
            "calibration_noul": summary["calibration_per_type"]["noul"],
            "calibration_score": summary["calibration_per_type"]["score"],
            "nll": sum(nll) / len(nll),
            "brier": sum(brier) / len(brier),
            "coverage": 100.0 * summary["predicted"] / summary["items"],
            "tvd": summary["calibration_items_tvd"],
        })
    return result


next_by_id = {t["id"]: t for t in tasks}
families = defaultdict(list)
for task in tasks:
    families[task["family"]].append(task["id"])
family_names = sorted(families)
family_metrics = metrics([t["id"] for t in tasks])
point_delta = {k: (None if family_metrics[0][k] is None or family_metrics[1][k] is None else family_metrics[0][k] - family_metrics[1][k]) for k in family_metrics[0]}

rng = random.Random(SEED)
draws = defaultdict(list)
for _ in range(N):
    chosen = [rng.choice(family_names) for _ in family_names]
    sample = [tid for fam in chosen for tid in families[fam]]
    m = metrics(sample)
    for key in m[0]:
        if m[0][key] is not None and m[1][key] is not None:
            draws[key].append(m[0][key] - m[1][key])

intervals = {}
for key, values in draws.items():
    values.sort()
    # Linear-interpolated empirical quantiles (the common type-7 convention).
    def quantile(p):
        position = (len(values) - 1) * p
        lower = math.floor(position)
        upper = math.ceil(position)
        weight = position - lower
        return values[lower] * (1.0 - weight) + values[upper] * weight

    intervals[key] = {"valid_draws": len(values), "lower_95": quantile(0.025), "upper_95": quantile(0.975)}

payload = {
    "schema": "qev-valen-opendecisions-family-paired-bootstrap-v1",
    "dataset": {"name": "OpenDecisions 1.0.1 public development set", "sha256": sha(DATA), "rows": len(tasks)},
    "scorer": "data/general-decision-eval/open-decisions/score.py",
    "qev": {"predictions": QEV.relative_to(ROOT).as_posix(), "sha256": sha(QEV), "model": "Qev 1.0 2B hybrid-v2"},
    "peer": {"predictions": VALEN.relative_to(ROOT).as_posix(), "sha256": sha(VALEN), "model": "Valen Decision 1.5 2B", "revision": "1b890606578ba0f40bb70ed46891ab65f778e76d", "model_hash_at_run": False},
    "paired": True,
    "matching_ids": len(tasks),
    "families": len(families),
    "bootstrap": {"unit": "family cluster sampled with replacement", "draws": N, "seed": SEED, "interval": "percentile 95%, linearly interpolated empirical quantiles (type 7)", "reported_delta": "Qev minus Valen; positive favors Qev except lower-is-better metrics"},
    "limitations": ["public development benchmark; not independent final-test evidence", "native prompts and inference paths differ", "Valen model weights were not independently hashed at run time", "family bootstrap captures sampling variability only, not protocol/source-overlap uncertainty"],
    "point_estimates": {"qev": family_metrics[0], "valen": family_metrics[1], "delta_qev_minus_valen": point_delta},
    "paired_family_cluster_95_ci": intervals,
}
OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps({"output": str(OUT), "sha256": sha(OUT), "families": len(families), "point": payload["point_estimates"], "ci": intervals}, indent=2, ensure_ascii=False))
