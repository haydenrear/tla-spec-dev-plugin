# ESD-01: cross-repository attribution and the actual cost of validation

Ticket #235 (epic #234, `evidence-sized-delivery`), audited on 2026-11-10.
**Evidence only.** No script, crawler, schema or validator was written or committed. Ad-hoc
`grep`, `git`, `gh` and one-line `uvx python` read commands were used to read sources. Only these
documents are committed.

| File | What it holds |
|---|---|
| `inventory.yaml` | 117 deduplicated finding/defect rows, with recurrence kept |
| `cost.md` | elapsed and active time reconstruction, denominators, gaps, and the 10-100× assessment |
| `failure-families.md` | 8 ranked families with interventions, counterexamples, uncertainty, and reliable graphs |
| `local-signal.md` | the two local signals named in the assignment's `goals` |
| `spec-unit.txt`, `spec-unit-after-merge.txt` | `validation.spec_unit` output |

## Scope

**This is a SAMPLE, not a census.** The sampling frame for each repository is listed below.
Nothing here should be read as a count over a whole ledger unless it says "census".

| Repository | Revision read | Observation window | Frame |
|---|---|---|---|
| tla-spec-dev-plugin (this repo) | `9635bad2` (`epic/evidence-sized-delivery`, = `a1ff56cf` main + plan) | close history 2026-06-28 → 2026-11-09; issues to 2026-11-10 | Read in full: the bug-sweep epic (#199; `specs/results/bug-sweep/**`, both milestone reviews, merges, owner decisions, the 55-row epic ledger, all ticket evidence directories, `specs/evals/bug-sweep/*`, PR #250 and PRs #176/#204-#232), `RP-07-DF-01`, `deferred/attribution/attribution.yaml` (REACH, BLIND, PRICE), issues #199 #195 #226 #194 #185 #186 #196-#198 #245-#248, and PRs #233 #241. Census of finding IDs: **309 unique ids** across `deferred_findings_final.yaml` (155), `deferred_findings_hexagonal_prompting.yaml` (19), `epic-close/*` (25), `finalization/*` (12), `bug-sweep/deferred-ledger.yaml` (55), `deferred/SI-2x.yaml` (43); the `deferred/BS-*.yaml` inbox rows duplicate the epic ledger and were not counted twice. **Sample**: rows were taken where the summary concerns validation, fixtures, environment, false or vacuous signals, or Test Graph (keyword pass plus `surface.test_graph` non-empty), then read. All 129 close-history manifests were read for timestamps. |
| tla-spec-dev (older `~/IdeaProjects` checkout of this plugin) | `350b9ab4` | — | **Fully deduplicated: 0 additional rows.** `350b9ab4` is an ancestor of `a1ff56cf`, and its `specs/.history` is this repo's minus `bug-sweep`. |
| commit-diff-context-parent (CDC) | `697f255e` (main) | manifests 2026-06-04 → 2026-11-04; issues to 2026-11-10 | All 175 rows of `specs/results/mvp-stabilization/red-attribution.yaml` and all 49 rows of `cdc-index-successor/attribution.yaml` were parsed, and about 25 rows were read closely. Also read: `GOAL-MS-VELOCITY/velocity-retrospective.json`, `evaluation-20261104.md`, issues #262 and #390, 244 manifests, and 17 local graph reports. Counts only: the 204-row deferred ledger. Skipped: per-ticket MS/MB ledgers (already reconciled into the deferred ledger) and the epic #164 attribution file. |
| meta-harness (MH) | `24243a89` (main) | 2026-08-22 → 2026-11-05 | Both closed-snapshot ledgers were parsed (58 + 170 rows) and about 20 rows read closely. All 21 BLIND rows of `results/epic-meta-harness-loop/attribution.yaml` were read, plus `finalization/README.md`, issues #52 and #56, 48 manifests, 42 PRs and 64 local graph reports. |
| polymarket | `9cab5d6a` (main) | 2026-10-29 → 2026-11-10 | `specs/results/deferred_findings_final.yaml` was mostly read. Also read: deferred E02-R1/R2/R4/R5/EVAL/CI-EVAL, `E02-R6/attribution.yaml`, `E02-CI-EVAL/final-assessment.json`, `E02/ci-reliability/audit/baseline-triage.*`, issues #115 #65 #49, 41 manifests and 72 PRs. |
| effectful-learning | `9ac6d4fa` (branch `planning/learning-workspace-handoff`) | 2026-09-30 → 2026-11-10 | A keyword filter was run over 8 ledgers. Read: `epic-10/review/finalization/validation-timing-audit.json`, issues #143 #163 #105 #95 #170, 60 manifests and 102 PRs. |
| skill-manager | `48a07c1d` (main) | 2026-04-24 → 2026-11-09 | Read: `specs/evals/results/attribution.yaml` (rows 1-240), the first eval round `2026-09-07-epic-provisions-a-ticket-worktree.md`, the OHV eval round README, wide-round summaries, filtered OHV/OUN backlogs, and issues #289 #292-#297 #344 #378 #386 #102. Skipped: the 122-row `epic-home-integrity-sync` backlog and all eval trace jsonl. |

**Inaccessible or not read.**

- Graph reports outside main checkouts were not read: CDC's `/Volumes/dev/cdc-test-substrate` and ticket worktrees. Only 17 of the 631 runs CDC's retrospective counts are local.
- Some evidence paths live under `/private/tmp` or `/var/folders` (for example polymarket `OBS-EVAL-MANAGER-LOCK-001`). These are recorded by sha256 only and were not checked.
- CDC epics #164 and #228 have no ledger or run logs (CDC's own `data_gaps`).
- **Agent session transcripts were not read.** They are the only plausible source of implementation active time (`cost.md` §0).
- The LLM model/version is recorded for almost no finding. The single exception: MH finalization names `claude-agent-acp 0.33.1`, `CLAUDE_sonnet`.

**Completeness.**

- Every row cites its primary record.
- Rows 1-45 (this plugin) were read by the ticket author.
- Rows 46-117 were extracted by two delegated **read-only** readers and then spot-checked against primary records. The spot-checks confirmed:
  - the CDC red-attribution row count (175);
  - the retrospective's red split (36/33/35/14) and its phase hours;
  - the MH `DEF-124` quote at the cited line;
  - the skill-manager first-round cost table;
  - the effectful-learning timing-audit totals;
  - the polymarket `profile_seconds` and the line numbers of 6 ledger rows.
- Two delegated evidence paths were wrong and were corrected before commit.
- The second reading in `local-signal.md` covers 10 rows.

## Method

1. Discover each repository's authoritative ledger and report locations (`specs/.history`, `specs/results`, epic ledgers, attribution files, GitHub issues/PRs).
2. Read primary records, not issue titles. Anchor each row to the record's own id, or to `UNMODELED/<bin>` (`bug_attribution.md` §7a/§7c).
3. Keep **origin** (where the defect lived) separate from **channel** (what detected it), using `bug_attribution.md` §4.1 tokens plus `eval`, `ci` and `manual-final-testing`.
4. Deduplicate repeat attempts of one defect into one row. Keep the count in `recurrence`, for example `BS-07-DF-05`: 13 runs across 7 tickets. `bug_attribution.md` §7b conservation is respected in spirit: no finding was dropped to tidy a family.
5. Compute cost only from timestamp-bearing sources. Mark each number primary, derived, inferred or unknown, and never add parallel run time to wall-clock time.
6. Rank families by cross-repo spread, recurrence and cost evidence. Each intervention names concrete row ids.

## Summary findings

1. **No record in any of the six repositories timestamps the start of work.**
   - Close-history manifests carry only the close time.
   - PRs are opened after the work.
   - **Implementation active time is therefore unknown everywhere.** The owner's "validation takes 10-100× implementation" observation can be neither confirmed nor refuted (`cost.md` §4).
2. **Phase-separated evidence exists only in CDC.** Review + graphs/merge took about **2.6-3.0×** the implementation phase, with 39-57 h of idle time attributed to neither side. Graph machine hours were 1.3-1.5× implementation hours.
3. **End-to-end elapsed time is dominated by waits and holds.** The bug-sweep's 19-ticket milestone landed **2 h 34 m** after kickoff, but the epic merged **48 h 13 m** after kickoff. A 29 h window holding the owner gate, the evaluation hold and waves 4-5 cannot be split.
4. **The most widespread failure family is environment identity.** Home, toolchain and version skew (F2) appears in **all six repos**. It includes:
   - the 9-recurrence missing-rung REACH row;
   - CDC's isolation gate, red on 14 of 15 runs in #234;
   - 8 of 12 voided BS-17 eval runs, which trace to `BS-03-DF-01`.

   It is cheap in machine time (CDC environment reds: 2.73 h, against 28.28 h for product reds) but costly in cycles.
5. **Shared-host contention and process lifecycle (F1) produced the plugin's most repeated false red.**
   - `spec.workflow.failure_cleanup_probe` errored in **13 runs across 7 innocent bug-sweep tickets**, and it kept `adapters_resolve` from running at all in milestone 1.
   - Its cause stays **inferred**: the probe passed at kickoff and at load 21-30.
   - `RP-07-DF-01`'s general half is **still not landed**: the executor still reports bare PIDs, and the test-graph skill has no daemon guidance at `9635bad2`.
6. **Vacuous and blind greens (F3) are the most severe family.**
   - In MH, DEF-110 was found against 126,856 green cases, and DEF-124 produced a 6-second green over zero cases.
   - They are found almost only by hand or reading channels, so the family is under-counted by construction.
7. **Instrument defects are a large share of everything found.**
   - skill-manager's first eval round: 4 product defects vs ~12 instrument defects. Its ledger: 11 vs 18.
   - CDC: 69% of 118 attributed reds were not the product by count. By known machine time, however, product reds were 62%.
8. **Reliable graphs share three traits.** They drive real systems or repositories, they demonstrate a red control, and they do not share a host, home or process tree with other runs. Examples: CDC `cdcServerFactPath`, the Beam lifecycle, polymarket epic02Acceptance (14/14 profile), and the plugin's four non-probe graphs.
9. **The seven-class taxonomy mixes origin and effect.** A second reading agreed on origin class in 7 of 10 rows, and all 3 disagreements were on that boundary. Agreement on origin component was 10 of 10, and origin was confused with channel in 0 of 10.

## Model result

**No-op.** `specs/current` and `specs/desired_program_model` are unchanged. This ticket adds
evidence documents only and changes no `Internal.tla` action, variable or invariant. The
`UNMODELED/<bin>` names in the inventory are labels for the epic agent's review. They are not
model proposals.
