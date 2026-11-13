# Qev vs Valen 2B on OpenDecisions

This bundle reproduces the paired profile reported in [`docs/qev-comparison.md`](../../qev-comparison.md). It contains the retained row-level probability outputs for Qev and Valen, a hash-bound metrics receipt, and the family-cluster bootstrap script.

Run from the repository root with the project's Python environment:

```powershell
.venv\Scripts\python.exe -X utf8 docs\evals\qev-valen-2b-opendecisions-2026-11-13\bootstrap.py
```

The script reads the pinned OpenDecisions 1.0.1 data and unchanged official scorer at `data/general-decision-eval/open-decisions/`, checks that both prediction files cover the same 2,352 unique IDs, recomputes official Capability/Intelligence/Calibration and per-type accuracy/competence/calibration/TVD, and reports supplementary hard-label NLL and multiclass Brier. It then resamples the 11 observed benchmark families with replacement for 5,000 paired draws using seed `20261113`. Percentile endpoints use linearly interpolated empirical 2.5th and 97.5th percentiles.

The receipt records dataset and prediction SHA-256 hashes, point metrics, uncertainty intervals, model revision, and limitations. Valen's model revision is pinned, but its weights were not hashed independently at both run boundaries. The runs use different native prompt and serving paths; training-source overlap and scorer parity remain unverified. OpenDecisions is public development data, so these results do not establish unseen-task generalization or justify training on its rows.
