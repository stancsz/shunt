# Qev 后续训练与验收任务单

记录日期：2026-11-07。范围：通用 Choice / Noul / Score 决策模型的 0.8B、2B、4B 候选。下方任务表是原始执行计划；状态快照补记实际进展，不代表模型已验收或上线。

## 2026-11-07 wrap-up disposition

The user-directed experimental training objective is closed for the existing hybrid-v2 0.8B / 2B / 4B adapter family. See [Qev experimental acceptance](evals/qev-training-acceptance.md) for the bound training data, checkpoint identities, reload receipts, and OpenDecisions validation results. The older v13 refill and T0–T6 tasks below remain follow-up data-quality and evaluation work; they are not prerequisites for this local experimental handoff and are not included in the accepted family. Source/license adjudication, a frozen development panel, fresh test/OOD evidence, and a comparable Jev result remain open. No further training is authorized by this wrap-up.

## 2026-11-07 v13 same-cell blind refill packet (prepared, not adjudicated)

- `scripts/prepare_qev_v13_refill_options.py` builds a deterministic blind comparison packet bound to v13 train SHA-256 `f67735272ea2892275836db23182ae288db8dbe611930c5f99eaae25b480edf1`, the 300-row review SHA-256 `e09299045ffaacfaa910484be840bb3c0aacba1bcc25d3f94d63cbb224785fc4`, and pinned HelpSteer v1 source/card hashes.
- Output `tmp/qev-general/qev-v13-helpsteer1-refill-options-v2/`: 126 comparison groups, each containing the current row plus three deterministic unused same-attribute/same-rating-cell alternatives (504 blind items total). Any one-for-one replacement preserves the original five-attribute × 0–4, 12-per-cell quota. All 22 cells containing flags had enough eligible source rows; the other three cells had no flags. The builder excludes all discovered exact visible-input overlaps and current HelpSteer source rows, then enforces unique source records/prompts. No alternative is automatically selected.
- `blind-options.jsonl` hides the current-row flag, record IDs, source row/index and target rating. `targets.jsonl` is the separate adjudicator key. Hashes: manifest `d02b99f112d56c11f7bdba96df8036193981c44e4c71e273b4a00493a09c3fe7`, builder `405e49c843b5da3c5fb5ad068763759ce21370eb697cb2914401b0e49a9b98b3`, blind packet `284acc17cb40a032a036e236f35a53873247fced5e4df26eeeeca12608f71688`, key `3e97d14e842a13958eaf8f2692ea70c7882dfa09f537fc13b5f441f661f34c39`.
- Parent acceptance: 126 unique groups, exactly four unique blind option IDs per group, 126 current rows + 378 alternatives, no target/source identifiers in the blind file, all 22 flagged cells complete, and packet/key hashes match the manifest. `scripts/profile_qev_v13_refill_options.py` reconstructed the source-bound Qev Score rows and measured all 504 entries using the exact pinned `candidate_prompts` rendering and each local Qwen tokenizer: 0.8B/2B/4B max 1,991/2,048, over-cap 0. Profile report SHA-256: `27b0c328d0f623dbdfd934beedca514178a287881552387e5c910c7c777034cf`. This covers only flagged originals and alternatives, not the entire 1,000-row candidate. Semantic near-duplicate review remains open; the packet is not adjudication, not train-approved, and does not resolve rights. No training was run.
- Next: have a human reviewer compare each original with its three shuffled alternatives using the pinned rubric; record keep/replace/uncertain with rationale in a separate decision file. Only then rebuild a candidate with the same 12-per-cell balance and rerun tokenizer, overlap, source and rights gates.

## 2026-11-07 HelpSteer v1 balanced Score replacement v13 (screened, not train-approved)

- Candidate: `data/general-decision/qev-general-1000-v13-helpsteer1-score300/` replaces all 300 Score rows in v11 with 300 pinned HelpSteer v1 train-split rows. It retains the exact 700 non-Score v11 rows and preserves 1,000 total at 400/300/300. There are exactly 12 additions in each of five attributes × five 0–4 rating cells, with 300 unique source records and prompts. Candidate train SHA-256: `f67735272ea2892275836db23182ae288db8dbe611930c5f99eaae25b480edf1`.
- Source and mapping: source revision `3ca5d59c1bc1080af195b4254e7407db60b6f450`; train SHA-256 `f0fa6f240622691ee2f2e9777f7d3dacf1b9f035223e6edf611dd4278a5cf519`; card SHA-256 `1780b67ca4c9aafc102f6e3298da8fe5089d2bc9bf633601c9c687263fb7e835`. The card declares CC-BY-4.0. Each original 0–4 human rating maps directly to the matching Qev Score class with its source attribute as rubric. This establishes row/label lineage, not downstream rights clearance or label correctness.
- Selection and reproducibility: `scripts/prepare_qev_helpsteer1_all_score.py` records the 300 removed v11 Score rows, 700 retained rows, and 300 additions in `selection.jsonl`. Parent verification confirmed exact retained-row identity, all source-row hashes and target mappings, 12-per-cell balance, and 1,000 unique IDs/groups/visible inputs. Candidate manifest SHA-256: `d0f41fbb310f202c31115eff0c683215f4662960bf83d1d949d125f826607c73`; selection SHA-256: `0b32edefbbfdd680953e432acc06d64bafecf3c5fe11defbb1ff9ec64d42b0f3`; builder SHA-256: `41e67c0b36dc3be9bdfeb8f554d78859a334b16454ff29bad2d9f508bb838a62`.
- Screening: exact full-input overlap is 392 with official hybrid-v2 training and 550 with the separate one-pass training file; overlap is zero with the discovered calibration, development, and OpenDecisions inputs. This is incremental source replacement, not an independent-data comparison. One-pass local tokenizer profiles for all three model sizes bind the candidate hash, show no truncation, median 263, p95 1,221, max 2,029 / 2,048 (19-token margin). Receipts: `tmp/qev-general/qev-v13-helpsteer1-score300-overlap-v1.json` and `tmp/qev-general/qev-v13-helpsteer1-score300-onepass-{0.8B,2B,4B}-profile-v1.json`.
- Selection quality limitation: selection is a deterministic hash sample within each of the 25 attribute/rating cells; it is balanced and source-distinct, but **not quality-ranked cherry-picking**. The old v9/v10 review covered zero v13 source-row/attribute pairs. Do not transfer its findings to v13.
- Blind-review packet and result: `scripts/prepare_qev_v13_blind_review.py` generated v1 (50-row shards) and a verified v2 packet (30 deterministic 10-row shards), all bound to candidate SHA-256 `f67735272ea2892275836db23182ae288db8dbe611930c5f99eaae25b480edf1`. Each v2 row exposes only ID, attribute, rubric, prompt, and response; source rating, target, options, source row index/hash, and selection metadata are withheld. Parent verified all 300 unique IDs and shard hashes. The complete comparison is `tmp/qev-general/qev-v13-helpsteer1-blind-review-v2/parent-full-comparison-v1.json` (SHA-256 `e09299045ffaacfaa910484be840bb3c0aacba1bcc25d3f94d63cbb224785fc4`).
- Triage outcome (advisory, not human adjudication): exact agreement 113/300, within one point 225/300, MAE 1.00, and 75 disagreements of at least two points. The reviewer tagged 37 off-topic, 13 unverifiable, and 5 unclear. The follow-up rule flags 126 rows; counts are not deletions. Verbosity had 14/60 exact agreement and MAE 1.48; Complexity had 15/60 and MAE 1.17. Helpfulness was strongest at 34/60 exact and MAE 0.52. The first seven shards used bounded CLI review; shards 08–30 used the local `http://127.0.0.1:4000/v1/chat/completions` `default` alias. Reproducible request runner: `scripts/run_qev_v13_blind_review_api.py`; aggregator: `scripts/aggregate_qev_v13_blind_review.py`.
- Discarded CLI logs: a few earlier review attempts used `Get-Content -Raw` on the user-global memory file and wrote unrelated memory content into task event logs. Those exact event logs were deleted and no conclusions from them were used; the status and cleanup are recorded in `tmp/qev-general/qev-v13-helpsteer1-blind-review-v2/discarded-worker-log-receipt.md`. This was a reviewer/logging issue, not a training or model-route failure.
- Status/next: no v13 training has been run; the point-in-time process query found no Qev training process. v13 remains `NOT_FROZEN / NOT_FOR_TRAINING`. Adjudicate the 126 follow-up flags, build same-cell refill options from unused pinned HelpSteer v1 training rows, resolve weight/source rights, and freeze a leakage-safe development panel before a controlled 0.8B pilot.

## 2026-11-07 Prometheus Score v12 candidate and corrected overlap audit

- Candidate: `data/general-decision/qev-general-1000-v12-prometheus-score100/` has 1,000 rows at Choice/Noul/Score = 400/300/300 and 60 rows per Score class. It deterministically removes four HelpSteer2 rows per attribute×score cell (100 total) and adds 100 Prometheus Feedback Collection rows (20 per source score 1–5; each selected row has a distinct instruction and rubric). Candidate train SHA-256: `729613bdab0fcbbbd4b59a61f2de67372535d7e7240dbf3d0622aabe6f1491db`.
- Labels and rights: all 100 new labels are GPT-4-generated rubric-conditioned scores, not human judgments. The [pinned Prometheus dataset card](https://huggingface.co/datasets/prometheus-eval/Feedback-Collection) declares CC-BY-4.0; underlying prompt/response provenance and redistribution fitness still require review. Inputs expose the reference answer and rubric; transfer to rubric-free scoring is unknown. Keep the manifest status `NOT_FROZEN_NOT_FOR_TRAINING`.
- Exact tokenizer profile: the combined file was measured with the one-pass Qev renderer and pinned 0.8B/2B/4B tokenizers. All 1,000 examples fit without truncation; each profile reports min 71, median 328.5, p95 1,059, max 1,809 / 2,048 tokens. Receipts: `tmp/qev-general/qev-v12-prometheus-onepass-{0.8B,2B,4B}-profile-v1.json`.
- Corrected overlap audit: `scripts/audit_qev_candidate_overlap.py` binds both candidate and protected data by path, SHA-256, and row count. Exact full-input matches (`kind`, `state`, `question`, ordered `options`) are 444 with official `data/general-decision/qev-hybrid-1000-v2/train.jsonl` and 550 with the distinct one-pass `tmp/qev-general/curated-1000-run-v2/train.jsonl`. Calibration and development have zero exact matches, including after sorting option order; OpenDecisions has zero exact input or template-only matches. The prior 16 calibration / 26 development counts were distinct `kind/question/options` template keys with `state` omitted (290 candidate rows participate in calibration template keys and 73 in development keys), so those figures are not identical model inputs and are not by themselves leakage evidence. Full path/hash-bound report: `tmp/qev-general/qev-v12-overlap-corrected-v1.json`.
- Independent review: the routed read-only CLI reviewer exited 0 but did not complete the requested per-key examination; treat independent acceptance as `UNVERIFIED`. Parent reproduced the complete exact-input counts with the report generator. No training or inference was run.
- Adjacent source screen: STS-B provides human 0–5 semantic-similarity ratings and is used by other decision-model recipes, but GLUE defers to each component source's original terms and its published training projection lacks row-level source identity. No STS-B examples were selected. It remains research-only until source/rights lineage can be reconstructed; even if cleared, its rubric must remain explicitly semantic similarity rather than generic response quality.
- Remaining before training: human-review the candidate source/labels and the development panel; resolve the source and weight redistribution rights; assess whether rubric-conditioned synthetic labels fit the intended Score task; and freeze an independent development panel. The candidate also intentionally reuses prior hybrid-v2 material, so it cannot establish independent data gains. Do not train v12 or use final test/OOD for selection.

## 2026-11-07 NVIDIA HelpSteer v1 Score swap (screened, not frozen)

- Source pin: `nvidia/HelpSteer` revision `3ca5d59c1bc1080af195b4254e7407db60b6f450`; train SHA-256 `f0fa6f240622691ee2f2e9777f7d3dacfb1f9f035223e6edf611dd4278a5cf519`; card SHA-256 `1780b67ca4c9aafc102f6e3298da8fe5089d2bc9bf633601c9c687263fb7e835`. Only the pinned train file was downloaded and used; validation was not opened. The card declares CC-BY-4.0, documents a mix of human-created and template prompts, NVIDIA model-generated responses, and five human ratings on separate 0–4 rubrics.
- Candidate: `data/general-decision/qev-human-1000-v9-hs1-score-v2/`, train SHA-256 `2b431f12993d5bc7e4cbd98e80f396edb321d4c58877d201003ad97db6e2fe65`. It retains 900 rows from the v6 base and replaces 100 HelpSteer2 Score rows (four per attribute×rating cell) with 100 HelpSteer v1 rows (four per cell), leaving 1,000 total and 400/300/300. Added prompts are unique; each attribute uses its own rubric and the original rating maps directly to the same Qev level.
- Screening: no exact visible-input overlap against the retained base, all discovered Qev training JSONLs, calibration, the 300-row development panel, or the 2,352 OpenDecisions inputs. Lexical near-duplicate review is limited to additions versus additions/base/calibration/dev/OpenDecisions, not every historical training row; zero pairs were flagged in that limited scope. The three pinned tokenizers report a maximum of 1,766 tokens and zero truncation/over-cap rows. The screen is construction evidence only; it does not prove human label quality, representativeness, or license compatibility.
- Verification: four focused tests pass. A separate read-only CLI review returned READY for screening construction with no must-fix findings. Parent recomputed candidate/source/selection hashes, all 100 source line identities and target mappings, per-cell balance, manifest input hashes, and label-blind visible-input overlap counts. Candidate is `NOT_FROZEN / NOT_FOR_TRAINING` pending human source/rubric and license review. Evidence: `scripts/prepare_qev_helpsteer1_score_swap.py`, `tests/test_prepare_qev_helpsteer1_score_swap.py`, `tmp/qev-general/qev-human-1000-v9-hs1-score-screening-v2/screening-report.json`, and worker receipt `tmp/qev-general/workers/helpsteer1-score-swap-independent-qa-20261107/events.jsonl`.
- Content triage (advisory): 100/100 additions have a label-blind model estimate; exact agreement 27%, within one point 81%, MAE 0.99, and 14 high-confidence two-or-more-point disagreements. Inspect these rows manually; do not auto-delete or treat model estimates as human labels. Full results: `tmp/qev-general/helpsteer1-content-review-v1/summary-v1.md` and `results-v1.json`. Candidate stays `NOT_FROZEN / NOT_FOR_TRAINING`.
- Next: compare the 100-row source sample’s rubric/coverage with current HelpSteer2 and obtain human review before any 0.8B pilot. Do not launch 2B/4B runs or use the provisional panel for a final quality claim.

## 2026-11-07 HelpSteer v1 reviewed-repair candidate v10 (not frozen)

- Builder: `scripts/prepare_qev_helpsteer1_reviewed_candidate.py`; candidate `data/general-decision/qev-human-1000-v10-hs1-reviewed-repair/`; train SHA-256 `4da5e6b4a4e1baa29ea01f2a4263a08e8d016ba517682f3c3ed5c5296aa5c4cd`; selection SHA-256 `37820c8ee123674e3b1fe69bf10ebf4df0a38a0e6b0e66ad0de2ab812319d4d0`. It derives from v9, replaces nine confirmed-flag rows with same attribute/rating alternatives passing the provisional two-blind-reviewer rule, and restores one original HelpSteer2 `complexity|4` row where no replacement passed. The three `mixed_or_still_ambiguous` rows were left untouched. All 25 Score attribute×rating cells remain at 12; total kinds remain 400/300/300.
- Parent acceptance rechecked candidate hashes, 1,000 unique IDs/groups/visible inputs, row-level changed IDs and same-cell mapping, all 25 cells, and that ambiguous IDs were untouched. Parent also parsed all 2,352 OpenDecisions records by physical LF (preserving its single valid U+2028 inside a JSON string), recomputed changed-row exact overlap against calibration/development/OpenDecisions (zero), and reran the three local tokenizers on the entire candidate (max 1,766, no truncation or over-cap rows).
- Nonauthor CLI review attempt 2 returned a partial pass and incorrectly reported the v3 results file missing. Parent verified that `tmp/qev-general/helpsteer1-content-review-v3-parallel-retry1/results-v3.json` exists and its SHA-256 matches the builder-bound input, then independently matched all nine accepted alternatives and the restored base row, reran exact overlap and tokenizer checks, and recorded the reconciliation at `tmp/qev-general/workers/helpsteer1-reviewed-candidate-qa-20261107-attempt2/parent-reconciliation.md`. The CLI review event stream completed with exit 0; its false missing-file finding is preserved at `tmp/qev-general/workers/helpsteer1-reviewed-candidate-qa-20261107-attempt2/review.md`. Structural screening does not validate human labels.
- Source/license boundary: the pinned NVIDIA HelpSteer card declares CC-BY-4.0 and says prompts mix Scale AI human-created/template content, responses are NVIDIA model-generated, and five attributes are separately human-rated 0–4. Preserve attribution; license compatibility and the three unresolved label flags still need human review. See the [official HelpSteer card](https://huggingface.co/datasets/nvidia/HelpSteer/blob/3ca5d59c1bc1080af195b4254e7407db60b6f450/README.md).
- Status: `NOT_FROZEN / NOT_FOR_TRAINING`. This repair improves the candidate audit trail but does not establish label truth, generalization, or a reason to train. Do not replace any 0.8B/2B/4B weight family from this artifact.

## v10 general-purpose fit and source-license audit (2026-11-07)

The v10 row review is a useful Score-label repair only; the candidate is not suitable as the general-purpose training mix. Its exact source counts are:

| Decision kind | Source mix in v10 |
|---|---|
| Choice (400) | WANLI 200; CommonsenseQA 100; Anthropic HH-RLHF helpful-base 100 |
| Noul (300) | Measuring Hate Speech votes 300 |
| Score (300) | HelpSteer2 201; HelpSteer v1 99 |

The 300/300 Noul concentration on hate-speech detection is too narrow for the stated general-purpose use. By comparison, current hybrid-v2 Noul is split 150 hate-speech votes / 150 diverse Open-Jev control tasks. Do not train v10 as the next general-purpose family; make a source-capped Noul mixture spanning broad decision domains first.

The official source cards declare WANLI CC-BY-4.0, CommonsenseQA MIT, Anthropic HH-RLHF MIT, Measuring Hate Speech votes CC-BY-4.0, NVIDIA HelpSteer2 CC-BY-4.0, and NVIDIA HelpSteer v1 CC-BY-4.0. CommonsenseQA's original maintainer confirmed MIT in [issue #5](https://github.com/jonathanherzig/commonsenseqa/issues/5), also reflected on its [official dataset card](https://huggingface.co/datasets/tau/commonsense_qa). [HelpSteer2's card](https://huggingface.co/datasets/nvidia/HelpSteer2/blob/990b271/README.md) says its prompts are mostly ShareGPT, while the rows retained here lack dependable per-row prompt origins. [HelpSteer v1's pinned card](https://huggingface.co/datasets/nvidia/HelpSteer/blob/3ca5d59c1bc1080af195b4254e7407db60b6f450/README.md) says prompts mix Scale AI human-created and template-generated text, responses are NVIDIA model generations, and ratings are five separate human attributes. The [Measuring Hate Speech project](https://hatespeech.berkeley.edu/) describes comments collected from YouTube, Reddit, and Twitter; the dataset card's CC-BY declaration does not independently establish rights for every underlying post.

CC-BY 4.0 requires appropriate credit, a license link, and an indication of modifications when material is shared; see the [official deed](https://creativecommons.org/licenses/by/4.0/deed.en). The row metadata preserves source/license URLs, but this audit is not a legal clearance of upstream user text or trained-weight redistribution. Keep notices and source provenance with any later checkpoint package.

Next data action: build a balanced 1,000-row candidate with 400/300/300 kinds, a multi-domain Noul source mix, source caps, exact held-out isolation, and no truncation. Keep training stopped until a leakage-safe development panel and source/label review are accepted.

## 2026-11-07 source-capped broad Noul candidate v11 (not frozen / not for training)

- Candidate: `data/general-decision/qev-general-1000-v11-sourcecapped/`; builder `scripts/prepare_qev_sourcecapped_candidate.py`. It retains 400 Choice and 300 Score rows from the screened v10 candidate, then builds Noul from two sources: 50 high-agreement Measuring Hate Speech vote rows (25 per dominant class, published vote agreement >=0.8) and 250 multi-domain Noul controls from the v5 curated pool. The v5 Noul selection is 139 no / 111 yes; combined Noul target mass is 164 no / 136 yes.
- Balance and provenance: 1,000 rows total, Choice/Noul/Score = 400/300/300; 49 Noul sources and 13 recorded Noul domains, source cap 100 and domain cap 90. The broad controls are synthetic and not independently human-reviewed. Original row metadata, target bases, source revisions, license declarations, and source URLs remain in `selection.jsonl` and `manifest.json`. HelpSteer v1's pinned source card declares CC-BY-4.0, five separate human 0..4 ratings, and NVIDIA model-generated responses. These declarations do not settle rights in upstream text or model-weight redistribution.
- Screening: parent verified 34 input hashes, zero ID/group/visible-input overlap against calibration (128), the unfrozen dev panel (300), and all OpenDecisions validation inputs (2,352). All three pinned tokenizers were independently rerun without truncation: 43 / 268 / 1,095 / 1,766 min/median/p95/max and zero rows over 2,048 for 0.8B, 2B, and 4B.
- Reuse caveat: exact overlap with the already-trained hybrid-v2 train set is 490/1,000: 240 Choice, 152 Noul, 98 Score. This is prior-training reuse, not held-out leakage, but weakens the value of treating v11 as a novel training recipe. Do not start another run from this candidate until that reuse and the source/label gates are resolved.
- Hashes: train `de70f0a5b35d4b161e293f49b66cc46bbb0ad24aea3677bee32c2e010f3c1883`; selection `058f2f89560be9326bd12aa4887a31026eaddbe4efd848eabc04dfc003c777fe`; manifest `e8dbdab8ce49c851dda556c0ed70c21583d42cf7af48ba346da6285c282120db`; builder `2b9029fae432c2717b5ff95bea10907a2332eeb0128746184fa7a1eec9005486`. Run receipt: `tmp/qev-general/workers/qev-general-sourcecap-candidate-20261107-attempt2/builder-report.json`. Nonauthor audit: `tmp/qev-general/workers/qev-sourcecap-nonauthor-audit-20261107/events.jsonl`; reviewer independently passed protected-set overlap, but left overall status PARTIAL for tokenizer/provenance limits. Parent then independently reproduced the tokenizer lengths and bound the pinned HelpSteer v1 card declaration. Candidate remains `NOT_FROZEN / NOT_FOR_TRAINING`.
- Adjudication packet: `data/general-decision/qev-general-1000-v11-sourcecapped/adjudication-packet.json` and `adjudication-review-items.jsonl`; reproducible builder `scripts/prepare_qev_v11_adjudication_packet.py`. Packet SHA-256 `b1599b9ec20f6c52011dc4803bda4d2c71337e2be720f6f3396538ed68a37ad0`. It binds the candidate and lineage hashes, maps all 1,000 source/label records, leaves human and rights decisions blank, and carries forward the three unresolved HelpSteer v1 flags. Its source-label groups are 300 HelpSteer human ratings, 200 published human-reviewed upstream labels, 150 crowdsourced labels/votes, 100 human-derived pairwise preferences over model-generated responses, and 250 synthetic controls; these categories describe source evidence and are not independent human adjudication.
- Nonauthor review: `tmp/qev-general/workers/qev-v11-adjudication-nonauthor-qa-20261107/events.jsonl` reports PASS for packet structure and consistency. It independently checked the candidate/review hashes, all 1,000 rows, three unresolved items with blank review fields, and all 490 exact hybrid-v2 mappings (240 Choice / 152 Noul / 98 Score). It found no label-category misclassification. Upstream text rights remain unverified; the review did not rerun the mapping algorithm or establish external license/redistribution rights.
- Remaining: human-adjudicate the dev panel and source/label sample; resolve upstream source and license compatibility; decide whether the 490 repeated hybrid-v2 rows should be removed from a future candidate; freeze an independent leakage-safe dev panel. No v11 training was run; the candidate remains `NOT_FROZEN / NOT_FOR_TRAINING`.

## 2026-11-07 OASST1 Choice candidate update

- Done (Verified)：新增独立的 v8 1,000-row 候选 `data/general-decision/qev-human-1000-v8-oasst-choice-v1/`，SHA-256 `afb688052936cf97557b77cae46886cee3b7fefd2c659dff0ae2917020693ac3`。保持 Choice/Noul/Score=400/300/300；从 v5 精确保留 900 行，将 100 个狭窄 Banking77 Choice 替换为 OASST1 train split 的人类 rank-0/rank-1 response pair。新增语言配额 en/es/ru/fr=40/30/15/15，首选项位置 50/50。
- Source/quality filter：Apache-2.0 OASST1 revision `fdf72ae0827c1cda404aff25b6603abec9e3399b`；只用 official train Parquet；要求 prompt/replies `review_result=true`、review_count 至少 2、rank 0 与 1 同父节点、rank-0 quality 至少 2/3、rank-1 至少 1/3，并排除发布标签中 PII、spam、toxicity 等非零记录。选择是在过滤后的候选池内按确定性 hash 排序，不是人工质量排名。
- Verified：单独的源重建筛查脚本核对 100/100 additions，重算 442 个源行 hash；官方 train/validation tree overlap=0。对 hybrid-v2 train、calibration、临时 dev panel 和 raw OpenDecisions inputs 的 exact visible-input overlap 都为 0。新增行三个 Qwen tokenizer 最大 1,108 tokens；全候选最大 1,708/2,048，无静默截断。回执：`tmp/qev-general/qev-human-1000-v8-oasst-choice-v1-screening/screening-report.json` 和 `exact-overlap-report.json`。
- Remaining：人工审核 pairwise 标签清晰度、难度和代表性；重新冻结无泄漏 dev panel；检查保留的 HelpSteer2 Score 行之 prompt-origin limitation（论文称 >95% prompt 来自 ShareGPT，但当前选中行无逐条来源字段）。候选仍为 `NOT_FROZEN_NOT_FOR_TRAINING`，未用它训练任何尺寸。
- Next Action：完成上述数据/面板 gate 后，再由预先冻结的质量门槛决定是否训练一个受控的 0.8B 对照；不要自动扩展到 2B/4B，也不要把新的 100-row source 当作增训全部尺寸的充分理由。

## 后续执行快照 — 2026-11-07

### 最新状态：VerQen 0.8B 有界试点完成；现行家族仍为 hybrid-v2

- Done (Verified)：hybrid-v2 1,000 行配方的 0.8B/2B/4B 均完成 250 步；另外，VerQen hybrid 候选也完成了一个 0.8B、250 步、1,000 行试点。后者温度 0.792761，calibration reload max error=0，训练期间 validation/test/OOD calls=0。摘要和诊断见 `artifacts/qev-general-08b-verqen-hybrid1000-v1-pilot-cuda/summary.json` 与 `docs/evals/qev-training-status.md`。
- Same-panel diagnostic：VerQen 与同尺寸 base、hybrid-v2、human-signal-v5 在相同 provisional 300 行面板上以 T=1 比较。相对 hybrid-v2 的 equal-kind macro NLL 差为 +0.049（95% group-bootstrap CI [+0.018,+0.081]）；相对 base 为 -0.160 [-0.220,-0.101]。面板已经用于选择，尚未冻结；这不是 Jev 竞争力或独立最终评估。
- 决定：保持 hybrid-v2 为当前 0.8B/2B/4B 家族，不启动 VerQen 2B/4B，也不增加轮数。这个 0.8B 结果不支持替换现有配方。
- Remaining：人工审核 VerQen 来源声明标签、原始来源许可兼容性和语义覆盖；复核开发面板来源/重复项并冻结新的 leakage-safe panel 与事前质量门槛。最终 test/OOD 仍保留一次性验收。
- Next Action：先完成候选与新面板的来源/标签审阅，再根据冻结门槛决定是否重训；不要用已看过的 300-row panel 或 OpenDecisions validation 作最终晋级证据。

### 2026-11-07 数据进展：HH-RLHF Choice 替换候选（未冻结、未训练）

- Added: `data/general-decision/qev-human-1000-v6-hh-choice-v3/` replaces 100 narrow Banking77 Choice rows in human-signal-v5 with 100 pinned Anthropic HH-RLHF `helpful-base/train` pairs. Total remains 1,000 and 400/300/300. Dataset revision, source/card hashes, per-row source line, deterministic selection, target position balance, and tokenizer lengths are recorded in its manifest and selection file.
- Verified: all 100 mapped back to their exact source pairs; target option position is 50/50; deterministic rebuild matched train and selection hashes. The train file is `2e67cfb9e086c9f7db6d5fe6a1b7ae7c98507346ca19351265aa14d111dc417c`. All 1,000 examples fit the 2,048 token cap for 0.8B/2B/4B without truncation (max 1,708). The 100 new rows have zero exact visible-input overlap with hybrid-v2 training, calibration, the current 300-row dev panel, or OpenDecisions. These exact checks do not rule out semantic or pretraining overlap.
- Facts vs unknowns: HH responses were model-generated and preference labels human-derived. The stable hash-ranked sample is not a human quality ranking; human clarity, representativeness and difficulty review remain open. The nonauthor CLI review at `tmp/qev-general/workers/hh100-choice-independent-qa-20261107-attempt2/review.md` returned NOT READY for the full verification scope: source mapping, target order, quotas, uniqueness, label-free inputs and JSONL safety passed, but its own tokenizer/overlap reproductions were unverified. Parent checks separately verified those items; full independent technical acceptance remains open. The earlier `v6-hh-choice` and `v2` drafts carry `NOT_FOR_TRAINING.txt`; use only v3 for further review.
- Next Action: human-review the selected 100 preference pairs, while separately screening a license-clear, broad ordinal Score source. Do not start a new training run until the reviewed source mix and a fresh leakage-safe development gate justify it.

### 2026-11-07 HelpSteer3 Score candidate status (not frozen)

- Done (Verified)：生成 v3 的 1,000 行候选：400/300/300 Choice/Noul/Score；保留 900 条 v6 行，并用 100 条 HelpSteer3 偏好强度行替换 100 条 HelpSteer2 Score。新增行按四个来源域各 25 条、全局 −3…+3 配额 14/14/14/16/14/14/14，域×标签单元各 3–4 条；84 条为三位标注者一致，16 条为两票一致。三个 pinned tokenizer 最大长度 2,007/2,048，无截断。准确的 source-line/row-hash、方向映射、现有 train/calibration/dev 和 raw OpenDecisions 输入 screen 见候选 manifest、`screen-report-raw-input-v1.json` 和 `source-hash-reconciliation-v1.json`。
- Facts vs Unknowns：OpenDecisions 2,352 行输入上 exact full-input 与忽略选项顺序的 kind/question/options 重叠均为 0；selected 100 的 3-gram Jaccard 0.72 近似对为 0。这些仅是精确/词汇 screen，不证明语义或预训练独立。父执行者按 builder 的 `ensure_ascii=False` 规范复核 100/100 source-row hash；独立 reviewer 的 ASCII-escaped 算法导致 23/40 的伪 mismatch。该 reviewer 仍将候选评为 NOT READY，因为尚无人审质量，且 ShareGPT/WildChat 上游 prompt 权限未解决。HelpSteer3 标签是两条生成回答之间的相对偏好强度，不能称为绝对质量分。
- Remaining：审阅上游许可/权限、标签可读性与代表性，决定是否冻结此候选；现有 hybrid-v2 三尺寸权重继续为当前 family。候选未训练，不做 2B/4B 新训练；通过人工/来源 gate 后，才考虑一次受控 0.8B 对照试点，并继续保留 final test/OOD。
- Artifacts：候选 `tmp/qev-general/qev-human-1000-v7-hs3-score-replacement-v3-20261107/train.jsonl`，SHA-256 `92289b78f8bf51595de56d1d955157d45a7aa35fba1804cac9ea5062a57c80ec`。这仍是 NOT_FROZEN/NOT_FOR_TRAINING 草稿，不是被采用的数据集或权重。

## 2026-11-06 baseline snapshot (historical)

### 最新状态：hybrid v2 三尺寸完成（2026-11-06）

- Done (Verified)：按精选、平衡的 1,000 行 hybrid-v2（Choice/Noul/Score=400/300/300）完成 0.8B、2B、4B，各 250 optimizer steps。摘要均报告 1,000 行、calibration reload max error=0、训练阶段 validation/test/OOD calls=0；产物分别位于 `artifacts/qev-general-08b-hybrid1000-v2-pilot/summary.json`、`artifacts/qev-general-2b-hybrid1000-v2-pilot/summary.json`、`artifacts/qev-general-4b-hybrid1000-v2-pilot/summary.json`。训练数据 hash 为 `a7f4c474442e8f577765630649e893324cd09257420c3a3b11f6c98d28939c25`。
- Same-panel diagnostic：三尺寸均在同一 provisional 300 行 panel（每 kind 100 行）与各自 base 做了 uncalibrated 比较；5,000 次 group bootstrap 的 macro NLL 差为 0.8B -0.209 [-0.282,-0.139]、2B -0.175 [-0.243,-0.104]、4B -0.230 [-0.321,-0.136]。逐 kind 差值依 Choice/Noul/Score 为 0.8B -0.368/-0.156/-0.103，2B -0.080/-0.066/-0.380，4B -0.079/-0.260/-0.350。原始报告见 `tmp/qev-general/hybrid1000-v2-{08b,2b,4b}-dev300-v1.json` 及对应 group-bootstrap 报告。
- OpenDecisions 全量验证：同一 pinned 2,352 行文件上三尺寸均完成 100% predictions，并由官方 scorer 打分：0.8B Capability 46.85、2B 55.23、4B 65.98。独立 CLI reviewer 复核 ID 覆盖、hash、label-free 输入及 scorer 结果（差异 <1e-12）；证据与限制见 `docs/evals/qev-training-status.md`。4B 只比榜单中的 Jeff-1.0-Qwen-4B（67.7）低 1.72 分，但比 Jev（80.1）低 14.12 分；差异低于 2 分在卡片的比较说明中不显著。OpenDecisions 是 validation 集且不含 JevBench items，因此不等于 Jev parity。
- Facts vs. Unknowns：300-row panel 尚未冻结；OpenDecisions 来源完整性未独立认证，且不是真正 JevBench 项目。通用分数中 Score 仍弱：0.8B 32.31%、2B 46.43%、4B 56.46% accuracy。三尺寸训练都完成且 evaluation 未用 OpenDecisions 标签作为输入；最终 test/OOD 仍未使用。训练、验证不等于发布就绪或 Jev 竞争力。
- Error analysis：`tmp/qev-general/opendecisions-error-analysis-v1.json` 显示 4B hard-Score accuracy 42.53%（mean normalized absolute error .2556），0.8B hard-Score accuracy 20.36%（error .3030）。4B Score 的 `usecase` family 42.31%（78 行）、`jaggedness` 26.19%（42 行）；Choice `usecase` 43.53%（85 行）。这些分组是诊断信号，小样本不能单独作为显著差异结论。
- Remaining：针对 hard/contextual Score 重做最多 1,000 行的来源组合，维持 400/300/300 type balance，避免 OpenDecisions/benchmark 泄漏；先冻结 300-row dev panel 与筛选候选，再只跑 bounded 0.8B 受控试点。若固定、独立开发证据不改善，再停用该训练方向，不把更多步数当成数据质量修复。保留本地 JevBench/final test/OOD 作为一次性验收。

### 2026-11-06 状态补记

- Done (Verified)：在 v2 候选审核后，按用户要求只训练一个 0.8B 的 1,000 行 v5 人类信号试点，没有重训 2B/4B。训练摘要在 `artifacts/qev-general-08b-human1000-v5-pilot-v1/summary.json`：250 步、1,000 行、calibration temperature=1.967464、校准集 reload max error=0、validation/test/OOD model calls=0。数据、配置和摘要哈希及复核在 `tmp/qev-general/workers/eval-review-v5-independent/qa.json`。
- Same-panel diagnostic：v5 0.8B 与 base 的 macro NLL 差为 -0.0549，262-group bootstrap 95% CI [-0.1391, 0.0314]，跨 0；旧 v4 0.8B 的区间为 [-0.2769, -0.0585]。2B/4B v4 comparison 的 macro CI 均跨 0，且有明显按 kind 的 tradeoff。原始预测和报告见 `tmp/qev-general/qev-family-v5-group-bootstrap-v1.json`。
- Independent review：`tmp/qev-general/workers/eval-review-v5-independent/qa.json` 为 pass；核对 13 个输入哈希、七份预测与同一 300 行 panel 的 ID/label-free 输入对齐，并独立重算行级指标与 group bootstrap。此复核不证明上游运行来源，也不把开发 panel 变成冻结验收集。
- Facts vs. Unknowns：v5 候选仍未冻结；300 行开发 panel 未冻结，重复审阅仅为 advisory。v5 结果不支持把该配方扩展到 2B/4B；当前 provisional panel 上旧 v4 0.8B 更强。Jev 不可用，尚无 Jev 竞争力证据；未调用最终 test/OOD。
- Remaining：人工审核并冻结训练候选与开发 panel；基于冻结 panel 重做尺寸/配方比较；只有开发证据支持时才决定下一轮小型实验；最终 test/OOD 仍保留一次性验收。
- Next Action：优先完成 300 行开发 panel 与 v5 数据候选的人工筛查/冻结。现阶段不追加训练、不将 v5 扩展到 2B/4B。

- Ask (Locked)：完成通用 Qev 0.8B / 2B / 4B 权重，并以可信的通用决策数据训练；保留“精选约 1,000 条、平衡且低工作量”的约束，不训练整个公开语料。参考数据集和训练配方见 [公开数据与配方盘点](qev-training-data-landscape.md)。
- Done (Verified)：Qev 0.8B、2B、4B 各自完成 250 步、1,000 行训练，最终 summary 均为 complete 且 checkpoint reload error=0。4B calibration/finalization 已由 step-250 snapshot 完成；heldout calls=0。2B/4B 未训练基线已建立；三种尺寸的基线与候选均完成同一 24 行 validation 子集的 uncalibrated CUDA 比较，报告见 `docs/evals/qev-validation24-diagnostic.md`。已生成并筛查两版可追溯的人类信号训练候选；v2 在同一 400/300/300 配额下使用 deterministic Banking77 same-intent lexical filter 取代近重复候选。
- Facts vs. Unknowns：4B finalization 记录在 `artifacts/qev-general-4b-curated1000-finalize250-v1/summary.json`：temperature=2.3274、reload error=0、heldout validation/test/OOD calls=0；校准耗时 1,771 秒，故“权重已完成”不代表质量已验证。24 题比较中，各尺寸候选的每种 kind 均呈现更低 NLL/Brier，但每类仅 8 题、没有置信区间，不能得出通用提升或 Jev 竞争结论；ECE 有几类恶化。2B CPU 24-row diagnostic 的较慢时延为历史路径，现有 GPU evaluator 在 RTX 5070 Ti 上的中位调用延迟为 0.20–0.37 秒。v1 与 v2 人类信号候选均来源于 WANLI 200 + CommonsenseQA 100（从旧精选集精确复用）、Banking77 100、Measuring Hate Speech Votes 300、HelpSteer2 300；源 revision、CC-BY-4.0 卡片和训练文件哈希、逐行选择理由及 tokenizer 长度均已存档。v2 的 1,000 行具唯一 ID/group/可见输入，最大输入 1,708 tokens；screening 在 OpenDecisions 2,352 行中发现 0 exact overlap、在 calibration 中发现 0 可见输入重叠、与旧 train 有 300 行预期复用；14 对剩余 lexical near-duplicate 均跨 Banking77 intent。v1 的 42 对已获 CLI advisory triage：13 对疑似同 intent 近重复、29 对不同 intent；该建议不是人工标签审定。v2 仍未冻结，尚需人审标签、代表性和跨源语义重叠；HelpSteer2 回复由模型生成、由人评分。开发面板仍未冻结。
- External evidence：InnerJev 的公开训练池为 417,825 条并以 400 步 LoRA 训练；decider 公布约 95 个公开数据集、1.47M 例的一轮 recipe 和 0.8B 结果。当前 Qev 1,000 条为低成本试点，并非据此已具竞争力。外部结果与本地分数不可直接互换。
- Remaining：人审并冻结 v2 训练候选与 300 行开发面板；在该冻结面板上做三尺寸的公平比较和 group 配对不确定性分析；再决定是否以新人类信号集做受控小规模训练。OpenDecisions 仅供验证，禁止训练；最终测试/OOD 不用于选择训练参数。
- Next Action：完成 v2 的 14 对跨意图近似对与标签质量审阅，以及 300 行开发面板来源/近重复/标签复核；未冻结前不对 v2 加训。完成同一冻结开发面板比较后再规划一次性 test/OOD 验收。

## 当前状态与目标

- Ask (Locked)：把接下来的训练任务写好，明确下一步、执行顺序、产物、验收和失败处理。
- Done (Verified)：核对现有摘要、配置、日志、恢复目录和评估脚本；完成本任务单。
- Remaining：执行下表 T0–T6；训练、质量、部署分别验收。
- Facts vs. Unknowns：0.8B、2B、4B 训练和 reload 摘要完整；24 行未校准 validation 比较在 `docs/evals/qev-validation24-diagnostic.md`；大样本质量、独立泛化与 Jev 对比未验证。
- Failed / Ruled Out：不能用 12 题结果证明泛化；不能用训练 loss、进程存在或恢复快照证明最终模型完成。
- Next Action (historical)：按 T2 完成人工开发集审阅，再运行 T3 冻结开发集比较；不要追加训练轮数来替代质量分析。

本轮沿用已有的 1,000 条、单轮、小规模试验方向。下文新增样本数、质量阈值和停滞时限是本计划建议的默认执行标准，不是既有测量结果；必须在查看新评估结果前冻结。扩大训练量或追加轮次需另立实验，不能自动恢复旧的 36,785 步全量配置。

| 候选 | 当前证据 | 尚缺什么 |
| --- | --- | --- |
| 0.8B | `artifacts/qev-general-08b-curated1000-v1/summary.json`：complete，250 steps，1,000 rows，reload error 0，训练期间 heldout calls 0；24 行 GPU diagnostic 已与同尺寸基线比较 | 冻结 300 行开发面板、group 置信区间及 broader quality evidence |
| 2B | `artifacts/qev-general-2b-curated1000-v1/summary.json`：complete，250 steps / 1,000 rows，reload error 0；同尺寸基线和 24 行 GPU diagnostic 已完成 | 冻结 300 行开发面板、group 置信区间及 broader quality evidence |
| 4B | `artifacts/qev-general-4b-curated1000-finalize250-v1/summary.json`：complete，250 steps / 1,000 rows，temperature 2.3274，reload error 0，heldout calls 0；同尺寸基线和 24 行 GPU diagnostic 已完成 | 冻结 300 行开发面板、group 置信区间及 broader quality evidence |

运行配置为 `tmp/qev-general/curated-1000-run-v2/config.json`：训练 1,000 条、校准 128 条、accumulation 4、rank 8、max_length 2048、seed 42、每 50 步快照、defer_heldout true。训练文件 SHA256 为 `a584c1e456e9e6acee575492f40c4769075af9d7bd41b0ec15d48d91e16a396b`，校准为 `75aaecaa180e58d0c03539296da8a94b29d4c8d17332d31c2e6f743ec72a3197`。实际运行仍须与各自 run.json 对照。v5 候选目录的存在不证明现有模型使用了 v5；不能按目录新旧推定训练身份。

## 任务与验收

### T0 — 固定运行身份，检查 4B（最高优先级）

执行者：训练执行者。读取两个 4B 目录的 run.json、training.jsonl、stdout/stderr、PID 和快照元数据；对比实际配置、训练/校准哈希、基座 revision、trainer hash、恢复起点。建立 `docs/evals/qev-training-status.md`，每个候选记录来源、最后有效步数、最终产物是否齐全及证据路径。

验收：三个尺寸的数据身份明确；没有重复启动同一实验；4B 被明确标为 running / failed / complete / stalled，而非猜测。进程存在还需日志步数推进证据。若 15 分钟没有新步数，先对照最近长样本步耗时、进程活动和错误日志；只标记疑似停滞，不自动杀进程。OOM、NaN 或异常退出则保存证据，检查最近完整快照。不得停止现有 Shunt、Ollama、Bifrost 服务腾显存。

### T1 — 收尾 4B 单轮训练（依赖 T0）

已有进程正常推进时继续等待，无需另起训练。只有确认原进程退出、快照完整且恢复身份一致后，才从最近完整快照恢复到**总步数 250**，输出到新的目录；不是再训练 250 步。保留中断前后日志，记录恢复造成的重放更新；不要把累计消费次数误称为互异训练样本数。恢复命令必须显式传入 curated 配置，先运行不带 `--execute` 的预览。现有 launcher 支持 `--config`、`--resume` 和新的 `--output`；不能直接用默认全量配置。

产物：最终 summary、推理 checkpoint、temperature.json、运行配置、训练日志及哈希清单。恢复快照不等于推理 checkpoint。

验收：summary.status=complete；最终 step=250，逻辑单轮消费 1,000 条且恢复轨迹可解释；训练期间 heldout model_calls=0；所有 loss/权重/输出有限；最终 checkpoint 可重新载入，reload max error ≤1e-5；Choice、Noul、Score 各有一条固定软件探针通过，概率有限、和为 1、选项顺序正确。记录完整运行耗时、CUDA allocated/reserved 峰值，不把 allocator 峰值写成最低显存要求。失败时不进入该尺寸质量排名；0.8B/2B 的后续评测可继续。

### T2 — 冻结开发集和公平基线（可与 4B 等待交错，资源不足则串行）

从 validation 构建固定 300 条开发集，每类 100 条，seed=42；仅依据输入与来源选样，不能依据模型表现或答案挑样。排除 train/calibration 的 group 和标准化可见输入重复，检查近重复及来源关系，保留筛查结果和人工裁决。不能为了凑数放松隔离；不足时记录实际数量和缺口。记录来源、语言、长度、选项数分布；上游标签质量不等于已重新人工核验。

`prepare_qev_dev_panel.py` 已支持可配置规模，默认 12 题的 ID 保持不变。首个 300 题候选在 `tmp/qev-general/worker-dev-panel-size/dev-panel-300-v1`，筛查为 225 个不同 group、553 个词汇近重复对。第二个不覆盖旧候选的 300 题候选位于 `tmp/qev-general/dev-panel-300-unique-groups-v1`：每类 100、seed 42、每类 source cap 10、每类 group cap 1；共 262 个 group，其中 33 个跨 kind、12 个 source label 跨 kind。当前 `screening-t2-final-2026-11-07.json` 绑定此候选和 manifest 哈希，记录 178 个词汇近重复对（Choice 86、Noul 49、Score 43），均仅标记、未自动删除；三种 tokenizer 的最大长度为 1,419，没有超过 2,048 的输入。早期 `report-t2.json` 指向首个候选，其 553 对及重复/隔离结果不得套用到第二个候选。默认命令此前生成的候选报告为 `report-t2-current-v2.json`，SHA-256 `037c33b2c3e220b5b5e1e808e3e3e3ca63f073d19db5d20fdc6a1cefde798e91`；报告与 candidate、manifest、train、calibration 的四个哈希均匹配。`screen_qev_dev_panel.py` 默认现已对齐第二个候选和 v2 train/calibration。`scripts/audit_qev_dev_panel_provenance.py` 生成的当前输出 `provenance-crosswalk-v2.json` SHA-256 `1abc44afa836cc0b72a993f0f6b1b7ea37de1c0829c5cf9fed35ef37109f99c9`，独立确认 candidate/train/calibration 的 ID、group 与可见输入零重叠；同时发现 9 个 source label 与训练/校准共有，且 candidate 300 行都缺少完整 `(source_url, revision, original_id)` 上游行身份。该面板是 group-disjoint 的混合来源开发集，不是 source-held-out 泛化集，也无法证明完整 upstream-row 独立。标签盲 triage 总结见 `tmp/qev-general/workers/qev-dev-panel-triage-20261107-attempt2/triage.md`。另对全部 178 个词汇近重复对完成逐对模型审阅：135 个 Choice/Noul 对的输入 SHA 为 `a02807418bb9b29790538fb509e6ab9a701cf08c9bc9960f0ee91d81a1189c3b`，报告 `tmp/qev-general/workers/dev-panel-choice-noul-review-20261107-attempt3/report.md` SHA-256 `e8b703d0922b9978f90f6d37032410d45d8e546c502e13f4654782f958fce84e`；43 个 Score 对的输入 SHA 为 `99f019b460ccd88f0d6873d58027ccb01bb5e92c7253ad026581f7afab31d848`，报告 `tmp/qev-general/workers/dev-panel-score-review-20261107/report.md` SHA-256 `146d1a83185d3b4d517216068baf31c3791f047166895320edea4b5c2c4a5977`。两份报告均覆盖全部 pair ID，未发现明显相同语义实例；Choice/Noul 审阅将 15 对标为不确定。审阅仅使用可见输入，是模型建议而非人工裁决或标签正确性复核；不据此删行。candidate 仍不冻结，人工代表性判断、上游来源身份和标签质量仍未解决。两个候选均未冻结。任何 test/OOD 已被试跑的 ID 应登记为开发暴露；无法找回时披露未知范围，不能声称完全未见。

2026-11-07 metadata correction: `screen_qev_dev_panel.py` had described padding and tensor output that its tokenizer code did not use. The source now records the actual per-row prompt-list call with padding, truncation, attention-mask output, and tensor conversion all disabled. Fresh report `tmp/qev-general/dev-panel-300-unique-groups-v1/report-t2-current-v3.json` (SHA-256 `e448e667eb3580b421565c7b47ed6ad3b5348cce04197b281004c1f5226aecad`) was regenerated and parent-checked against candidate, manifest, validation, train and calibration hashes. It retains 300 rows (100 per kind), zero ID/group/input overlaps with train and calibration, 178 lexical flags, and max length 1,419 across all three tokenizers with no truncation or over-cap rows. This repairs audit metadata only; the panel remains `NOT_FROZEN` pending source/provenance and label-quality adjudication.

2026-11-07 release-lineage crosswalk: `scripts/audit_qev_dev_panel_release_lineage.py` regenerated `tmp/qev-general/dev-panel-300-unique-groups-v1/release-lineage-v2.json` (SHA-256 `af0827e2d6dd7ab7c5a41fdf4f646a973b0a4749ff22894e0f553e074bfe06f7`; script SHA-256 `6b1819fdb645c393454ca65173b66464fe22009394855ff460629a98851ebe17`). All 300 panel IDs match the pinned validation Parquet by ID and full decoded record; line numbers are unique within this panel. The curated hybrid-v2 training JSONL maps 900/1,000 rows to the pinned train Parquet; the other 100 are CommonsenseQA. All 128 calibration rows map exactly. The Parquet `original_line_number` repeats across splits (3 raw integer collisions with curated train and 2 with calibration), while exact `record_json` hashes show zero cross-split identity overlap. Although the v1.1 README describes the field as a complete-mixture position, observed split-level collisions mean the integer alone is not a safe cross-split identity; the report records this limitation and uses exact hashes. The nonauthor CLI review was `READY` for this release-record lineage scope, with no must-fix findings; receipt `tmp/qev-general/workers/dev-panel-release-lineage-qa-20261107/review.md` (SHA-256 `b9718fdf35dd74f4d4aed1e4c66a289e039f0857590a6723ed651b6c9416c73e`). This strengthens release-level row traceability but still does not recover upstream corpus identities for generated/control rows or establish semantic independence or label correctness. The separate [target-basis audit](../tmp/qev-general/dev-panel-300-unique-groups-v1/target-basis-audit-v1.json) (SHA-256 `0af4885f9775dcd563fa10d9d61e075eeb9a772a0d5db4126ae9851d2c189ea9`) found 31 rows without declared `target_basis`; 283/300 are marked synthetic, all 100 Noul items synthetic, and missing basis metadata is not treated as proof of an incorrect label. Keep the panel unfrozen.

为 2B、4B 建立与 0.8B 相同方法的未训练 checkpoint：相同基座 revision、初始 head、无 LoRA，保留创建脚本/命令和 metadata。不要拿 0.8B 基线替代 2B/4B 基线。

验收：300 条且三类各 100，ID 唯一、已知 group/输入重叠为零，输入长度经过实际 tokenizer 检查且没有静默截断；来源和近重复限制可追溯；六个候选/基线身份明确。最终 test/OOD/OpenDecisions 不参与此阶段选样、调参或选 checkpoint。

### T3 — 三尺寸开发验收与选择（依赖 T1 对应尺寸、T2）

先让同尺寸基线和候选都以 temperature=1 在同一 panel 上评估，使用现有 `qev_general_eval.py --uncalibrated` 和 `compare_qev_development.py`。先执行 12 题软件烟测，再执行 300 题。现有评估器是 CPU 路径：记录实际设备，串行运行，先测吞吐再估时；CPU 时延不能写成 GPU 或线上性能。300 题比较器输出仍带 tiny diagnostic 文案，正式汇总应说明实际样本数，不能把它当最终统计验收器。

产物：六份逐条预测、三份同尺寸比较，以及 `docs/evals/qev-development-comparison.md`。表内列出每类样本数、唯一硬标签 accuracy、软标签 expected accuracy、NLL、multiclass Brier、ECE、错误样例、调用时延 p50/p95、峰值内存。软标签不得伪造为唯一正确答案；三类宏平均与按样本汇总分开。

建议的开发晋级标准（评估前冻结）：三类等权平均 NLL 相对同尺寸基线下降至少 2%；任一类 NLL 不恶化超过 5%；三类平均 Brier 不恶化；有唯一硬标签的类 accuracy 不下降超过 2 个百分点。输出必须全量有效，漏题、重复 ID、非有限值或错位选项一律不通过。同时报告按 group 配对 bootstrap 的 95% 区间；区间跨零时结论写“改善未获充分证据”，不宣称显著提升。这些是本轮筛选门槛，不代表通用行业标准。

未达门槛：定位错误类型、标注问题和输入格式，保留基线可用结论；不自动增加 epoch。若多个尺寸合格，优先较小者；较大者只有在宏平均 NLL 再改善至少 2% 且资源代价可接受时晋级，否则保留较小模型。不强求三个尺寸全合格。

### T4 — 独立校准与最终冻结（依赖 T3）

仅使用既有独立 calibration 数据拟合温度。复用已有 temperature 时核验它的来源 hash、split=calibration、值为有限正数。对晋级模型在开发集分别报告 T=1 与 calibration 温度的 NLL/Brier/ECE；不要把候选校准值套给未训练基线。如果比较校准后的基线，必须在同一 calibration 集独立拟合。

验收：校准数据无训练/开发污染、温度和 checkpoint 哈希绑定；开发 NLL/Brier 不恶化方可选择校准版本，否则保留 T=1 并如实标为 uncalibrated。ECE 仅辅助判断，不能单靠调 bin 获得通过。冻结最终 checkpoint、温度、输入处理、评估代码和阈值后进入 T5。

### T5 — 一次性最终质量验收（依赖 T4）

先固定 test/OOD 评估清单和污染排除清单：建议各 600 条、三类各 200，seed=42；不足时暂停该结论并记录缺口。只比较已冻结的晋级模型和对应基线，不能用这些结果挑选新训练设置。报告同源 test 与 OOD 分开，沿用 T3 的改善/退化门槛；通过门槛且主要 NLL 改善的配对 95% 区间不跨零，才称“本评估集上改善已验证”。其余状态分别写不通过或证据不足。

OpenDecisions 单独进行：先完成来源/近重复筛查，再用 `qev_opendecisions_run.py` 生成预测，核对完整原始输入的 2,352 个唯一 ID、概率和 manifest，并用随数据保存的官方 scorer 评分。该 runner 仅有 complete_input 不足以证明完整 benchmark。OpenDecisions 禁止用于训练；已看过结果的题不能回填到训练再重测宣称独立。

Jev 对比只有在版本、输入、官方评分和执行条件可比时报告；作者公布的 Jev 1.13.0 分数只列为外部参考，不能代替本地复测。缺少可用基线就标“Jev 对比未验证”，不阻碍交付诚实的 Qev 报告。失败后修正得到的是新实验；已用最终集降级为开发证据，需要新的独立验收集。

### T6 — 归档和交接（依赖 T5；部分完成也要列缺口）

交付 `docs/evals/qev-training-acceptance.md`：各任务状态、候选对比、采用/拒绝原因、输入/输出哈希、复现命令、已知污染与未验证项。将需要长期保留的配置、清单和报告移出仅有 tmp 的位置；大权重按仓库策略保存并提供路径/哈希，不自动加入 Git。

执行者负责产物；独立验收者复核 split、原始预测与汇总一致性、checkpoint reload 和通过标准。若委派，只用既定 `subroute-subagents` Codex CLI 路由、进程级 `http://127.0.0.1:4000/v1`、环境中的 GATEWAY_MASTER_KEY、model=default；不打印密钥，不退回 native subagent。只读审查限定上述文件，回执绑定文件哈希；路由不可用则标“独立复核未验证”，作者检查不冒充独立验收。

训练完成、质量通过与上线是三个状态。本计划不启动部署；通用 Qev checkpoint 不直接覆盖现有 Shunt 路由 LoRA。Bifrost 转发、scope、计费上限和真实任务 soak 仍按原目标另行验收，不能由通用决策分数替代。

## 可直接复用的开发评估命令

从仓库根目录执行。下例使用已存在的 0.8B checkpoint 和 12 题 panel，输出必须尚不存在；它验证执行路径，不是 T3 的 300 题验收。T2 完成后改为冻结的 300 题目录与 `--count 300`，并为每个尺寸指定自己的基线/候选路径。

```powershell
$env:PYTHONPATH = 'C:/Users/stanc/github/shunt/tmp/qev-general/python-deps'
$env:CUDA_VISIBLE_DEVICES = ''
$env:PYTHONUTF8 = '1'
.venv/Scripts/python.exe scripts/qev_general_eval.py --checkpoint artifacts/qev-general-08b-curated1000-v1/checkpoint --data tmp/qev-general/dev-panel --split validation --count 12 --seed 42 --stratified-by-kind --uncalibrated --output tmp/qev-general/next-08b-dev12.json
.venv/Scripts/python.exe scripts/qev_general_eval.py --checkpoint artifacts/qev-general-08b-baseline-v1 --data tmp/qev-general/dev-panel --split validation --count 12 --seed 42 --stratified-by-kind --uncalibrated --output tmp/qev-general/next-08b-base12.json
.venv/Scripts/python.exe scripts/compare_qev_development.py --baseline tmp/qev-general/next-08b-base12.json --candidate tmp/qev-general/next-08b-dev12.json --output tmp/qev-general/next-08b-compare12.json
```

此 shell 将 CUDA 隐藏，后续 GPU 训练请使用独立 shell 或恢复原环境；不要从这里直接启动 GPU 训练。建议顺序：T0 → T1，同时准备 T2 → T3 → T4 → T5 → T6。当前最有价值的下一步是拿齐可评估产物并做公平对比，而不是扩大数据或追加训练轮数。
