# Qev general-purpose family — experimental acceptance

**Disposition (2026-11-07): accepted for local experimental use and handoff.** This closes the requested 0.8B / 2B / 4B training work at the current research-prototype level. It does not certify production readiness, a frozen/licensed training corpus, or parity with Jev. No new training was started for this closeout.

## Delivered family

The accepted family is the separate general-purpose typed-decision adapter family. It does not replace the Shunt routing adapter. Each checkpoint consists of a LoRA adapter, decision head, temperature, and model metadata; it requires the matching pinned Qwen3.5 base weights and is not a merged standalone model.

| Qev tier | Pinned Qwen3.5 revision | Training artifact | Adapter SHA-256 | Calibration temperature | Reload max error |
| --- | --- | --- | --- | ---: | ---: |
| 0.8B | `2fc06364715b967f1860aea9cf38778875588b17` | [checkpoint](../../artifacts/qev-general-08b-hybrid1000-v2-pilot/checkpoint/) | `bd09ea687b558560da1e57d5fd3ed4d22543d91b6720df82034ae9ed6c5b6f3e` | 0.93348 | 0.0 |
| 2B | `15852e8c16360a2fea060d615a32b45270f8a8fc` | [checkpoint](../../artifacts/qev-general-2b-hybrid1000-v2-pilot/checkpoint/) | `6ce886c3c3b1f31923c300d2d5b548005fa5cd2031d9fdf3d1676fa5cb313230` | 0.95286 | 0.0 |
| 4B | `851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a` | [checkpoint](../../artifacts/qev-general-4b-hybrid1000-v2-pilot/checkpoint/) | `26a4aa8e928020308329cf7f24b0158938ce9ccb578087ca4c7dbb471c3d6d30` | 1.60643 | 0.0 |

All three runs report `complete`, 250 optimizer steps, 1,000 consumed training rows, rank 8, and zero calibration-reload error. Their `run.json` files bind the same training SHA-256 `a7f4c474442e8f577765630649e893324cd09257420c3a3b11f6c98d28939c25` and calibration SHA-256 `75aaecaa180e58d0c03539296da8a94b29d4c8d17332d31c2e6f743ec72a3197`. The training data is 400 Choice / 300 Noul / 300 Score, capped at 2,048 tokens. Validation, test, and OOD calls were deferred during training; the separate OpenDecisions validation below was run after training.

Training summaries: [0.8B](../../artifacts/qev-general-08b-hybrid1000-v2-pilot/summary.json), [2B](../../artifacts/qev-general-2b-hybrid1000-v2-pilot/summary.json), and [4B](../../artifacts/qev-general-4b-hybrid1000-v2-pilot/summary.json). The 4B summary is the actual training run; the separate `qev-general-4b-curated1000-finalize250-v1` directory is only a later finalization artifact and is not the family path accepted here.

## Data and public recipe research

The accepted training file is [`qev-hybrid-1000-v2/train.jsonl`](../../data/general-decision/qev-hybrid-1000-v2/train.jsonl). It contains 1,000 rows and preserves the 400/300/300 Choice/Noul/Score balance instead of using a full upstream corpus. Its manifest still says `candidate_not_frozen`; this closeout accepts the resulting checkpoints as experiments, not the source mix as rights-cleared or independently adjudicated gold data. The manifest and source notes retain provenance caveats.

The public-data and recipe review is in [Qev training-data landscape](../qev-training-data-landscape.md). It compares Open-Jev, InnerJev, decider, and Kev, including their data scale, supervision types, training recipes, evaluation protocols, and limits on transferring their results to this small Qev sample. The Qev rows include public human-rated or crowd-labeled examples and generated controls; detailed source counts and licensing notes remain in the data manifest and landscape document.

## OpenDecisions validation readout

Saved predictions cover all 2,352 OpenDecisions validation items with 2,352 unique IDs for each tier. The scorer outputs are linked below. These are validation results, not a fresh final test/OOD estimate.

| Tier | Capability | Intelligence | Calibration | Choice accuracy | Noul accuracy | Score accuracy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.8B | 46.8511 | 19.1705 | 74.5317 | 46.94% | 62.29% | 32.31% |
| 2B | 55.2254 | 30.6553 | 79.7955 | 54.67% | 72.01% | 46.43% |
| 4B | 65.9847 | 44.8740 | 87.0954 | 68.25% | 77.30% | 56.46% |

Scorer results: [0.8B](../../tmp/qev-general/opendecisions-qev-08b-hybrid1000-v2-score-v1.json), [2B](../../tmp/qev-general/opendecisions-qev-2b-hybrid1000-v2-score-v1.json), [4B](../../tmp/qev-general/opendecisions-qev-4b-hybrid1000-v2-score-v1.json). The complete predictions and evaluation details are recorded in [Qev training status](qev-training-status.md).

The larger tiers score higher on this validation set, but this does not establish Jev equivalence. A directly comparable local Jev run was not available, and the benchmark has already informed prior development decisions. Do not present these scores as a clean generalization estimate or use the report to claim benchmark parity.

## Acceptance boundary

| Requirement | Disposition |
| --- | --- |
| Research public data sources and other teams' recipes | **Complete.** See the linked landscape review. |
| Train a separate, balanced Qev family at 0.8B / 2B / 4B | **Complete as experimental adapters.** All three checkpoints exist, reload from disk, and bind to pinned base revisions and the same 1,000-row training hash. |
| Keep the sample bounded rather than training on full source corpora | **Complete.** 1,000 rows, 400/300/300 across the three decision kinds. |
| Establish high-quality frozen labels and downstream redistribution rights | **Not established.** The data manifest is not frozen; source/licensing and human-adjudication work remains open. |
| Establish fresh held-out quality, production readiness, or Jev parity | **Not established.** Test/OOD were not used for final acceptance; no comparable local Jev result exists. |

For this user-directed wrap-up, the first three items are accepted as the delivered research prototype. The last two remain explicit limits, not reasons to mislabel the trained artifacts as incomplete or to claim stronger performance than measured. Keep the adapters local/internal until data rights are reviewed. The separate one-pass 0.8B/2B runs and the untrained v13 data-review candidate are not part of this accepted family; their status remains documented in [Qev training status](qev-training-status.md) and [next training tasks](../qev-next-training-tasks.md).

## Reproduction and use

Use the corresponding pinned base revision with the adapter directory and checkpoint metadata above. The repository's safe training/evaluation entry points are [`qev_general_train.py`](../../scripts/qev_general_train.py) and [`qev_general_eval.py`](../../scripts/qev_general_eval.py); the immutable model revisions and resource configuration are in [`qev-general.json`](../../configs/qev-general.json). Do not point the general decision adapter at the Shunt routing path.
