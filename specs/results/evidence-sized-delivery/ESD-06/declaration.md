# ESD-06 evaluation declaration (committed before any billed run)

Ticket #240, epic #234 `evidence-sized-delivery`, `role: evaluation`, owns
GOAL-ESD-UPTAKE, GOAL-ESD-CAPACITY, GOAL-ESD-ARCH, GOAL-ESD-VELOCITY.
Declared 2026-11-10T14:55Z. Nothing below is changed after the first billed run;
deviations are appended under "Amendments" with a timestamp and a reason.

## Revisions and environment

| item | value |
| --- | --- |
| BASE arm | `a1ff56cf9ebc` (= `main`), run from a detached scratch checkout `/Volumes/dev/tla-spec-dev-plugin-esd06-base` (ESD-05-DF-02: `evals/run.sh` stages the checkout it runs from) |
| BASE arm, uptake cases only | `a1ff56cf` + ONE local commit that adds only `specs/evals/evidence-sized-delivery/cases/**` (byte-identical copies from the tip). No skill, eval or harness file differs from `a1ff56cf`. The commit is on no remote, so the run uses `SI10_ALLOW_DIRTY=1` and run.sh records it as not reproducible from a remote sha; it is reproducible from `a1ff56cf` + the tip's case directory. |
| TIP arm | the pushed tip of `feature/240-evaluation` that carries this file (epic tip `5404a3c1` + this declaration + the uptake cases), run from `/Volumes/dev/tla-spec-dev-plugin-240-evaluation` |
| Skill delta between arms | `git diff a1ff56cf <tip> -- skills test_graph/README.md` = the epic's 17 skill files + `test_graph/README.md`; nothing under `evals/` differs |
| Runner | `evals/run.sh` unmodified (`claude plugin eval --ablation none --runs 1 --trust-plugin`), Claude Code 2.1.322 |
| Agent model | the harness default for this account (no `model` in settings); the model id is read back from each run's JSON/trace and reported. Judge: the `llm` grader default (haiku) |
| Toolchain pin | `evals/lib/toolchain.lock.toml` skt `365abbf1`, the same file on both arms (single-case runs default to the pin) |
| Eval home | `/Users/hayde/.local/state/tla-spec-dev/evalhome`; `evals/setup-eval-home.sh --check` at 14:43Z: all green except offline uv wheels, which live per checkout in `.toolchain/uv-wheels` (gitignored). Remedy: the 4 wheels were COPIED from `/Volumes/dev/tla-spec-dev-plugin/.toolchain/uv-wheels` into both arm checkouts (no rebuild, no download); `--check` then green on both arms |
| Views | `SI10_VIEW` set per arm (`/private/tmp/esd06-view-base`, `/private/tmp/esd06-view-tip`) so the two arms may run concurrently without sharing a staged view |
| Same day, same home | both arms run on 2026-11-10 with the same eval home |

## Cases

### A. Guard: existing cases of the edited skills (base vs tip, 1 run each, 18 cases = 36 runs)

Selected because the case's skill had a file changed by ESD-01..05 (`git diff --stat a1ff56cf 5404a3c1 -- skills`):

| skill (changed files) | cases |
| --- | --- |
| discovery (`SKILL.md`, `layout.md`) | `start-from-the-spec-not-the-source` |
| git-epic-workflow (`SKILL.md`, `epic-ticket.md`, `finalize.md`, `goals-and-evaluation.md`, `human-review.md`, `plan-and-schedule.md`, `validation-review.md`, new `step-sizing.md`) | `epic-mode-is-not-main`, `w-epic-assignment-no-force-on-blocking`, `w-epic-force-when-owner-decided`, `w-epic-merged-by-is-epic-owner`, `w-epic-plan-free-form-lane`, `w-epic-retire-part-of-goal-warns-only` |
| git-issue-workflow (`complete.md`, `epic-ticket.md`) | `w-giw-epic-ticket-plan-values-win`, `w-giw-epic-ticket-stops-on-wrong-pr-base` |
| git-issue (`issue-template.md`) | `a-work-order-not-a-wish` |
| spec-double-2 (`agent_roles.md`, `bug_attribution.md`) | `w-roles-epic-finds-its-empty-inbox`, `w-roles-propagation-is-checkable`, `w-roles-review-finds-its-destination`, `w-roles-testing-finds-its-destination`, `w-roles-ticket-finds-its-back-channel`, `w-sdc-attribution-before-close` |
| test-graph (`SKILL.md`, new `graph-architecture-review.md`) | `compose-a-behavioural-graph`, `w-tg-run-a-graph-not-bare-gradle` |

Excluded: `epic-provisions-a-ticket-worktree` (UNDECIDED by construction: needs a real home); wt/skt/skill-manager cases (their skills are unchanged).

**Metric:** count of cases that PASS on base and FAIL on tip (pass = the harness's own pass verdict for the case). **Target clause (report-only):** 0.

### B. Uptake: five new declarative cases (base vs tip, 1 run each = 10 runs)

Under `specs/evals/evidence-sized-delivery/cases/` (the UPTAKE `evidence_root`), run with `--eval-dir specs/evals/evidence-sized-delivery/cases`. No prompt names the guidance or the answer.

| case | role | scenario from #240 it distinguishes |
| --- | --- | --- |
| `esd-review-graph-node-change` | review | graph-origin risk in a node change; green but possibly blind oracle; stale saved context / replay |
| `esd-plan-two-capacities` | planning | review vs verification capacity, tighter binds; unstable graph refusing expansion; sparse history |
| `esd-ticket-red-not-mine` | ticket | origin ≠ channel; false red from a shared-host probe; no charge to product |
| `esd-model-change-recalibrate` | wave owner | model-version change → recalibrate, not increase |
| `esd-expensive-eval-checkpoint` | planning (cost) | larger safe batch with expensive stable evals; keep final confirmation |

Graders: one `llm` decision grader (weight 4, response only), one `regex` retrieval grader (weight 1; names a tip-only page/section, so it is green only on the tip by construction and is reported SEPARATELY from the decision), one `tool_used: Skill` (weight 1).

**Harness constraint and how it is handled (no code).** `evals/lib/place.sh` and `lib/verify.sh` dispatch on `EVAL_CASE` and refuse (exit 2) an unknown name, and `tests/test_agent_integration_harness.py` requires every case under `evals/` to have an arm in both. A new case under `evals/` therefore needs new executable dispatch code, which this ticket may not write. The uptake cases therefore live OUTSIDE `evals/` and set `EVAL_CASE: w-sdc-scorecard-tool-needs-a-newer-python`, an existing arm that places no fixture (`place_moved_fixture`, none shipped) and runs `verify_from_expect`, which finds no `expect.json` for the prompt's own `EVAL-CASE:` marker and writes `WHY-NO-VERDICTS`. No grader reads a verdict path. Recorded as a validation finding (deferred).

**Observed beyond the score (from `--keep-temp` traces, both arms):** which skills/files the agent opened (Skill/Read/Grep inputs), lines read, turns, wall time and cost per run. The judgement of decision quality is the `llm` grader's; I additionally read every final response and record disagreements with the judge as false reds/greens of the instrument, without changing the score.

### Not covered by a billed case (reported unmeasured for uptake)

reverse capacity (verification exceeding review); graph-origin defects detected by another channel; attribution conservation through architecture changes (§7b); finalizer carrying the next epic's starting estimate. Some are reached by the non-billed replays below.

## Non-billed instruments

- **GOAL-ESD-CAPACITY:** held-out replay of `step-sizing.md` on the four episodes ESD-04 left unreplayed (polymarket E02 R1-R13, effectful-learning epic-10, meta-harness finalization, CDC #234), by a delegated reader instructed NOT to open `specs/results/evidence-sized-delivery/**` and to write each decision before reading the outcome. Bias: the ESD-06 author has read ESD-01's outcomes; the delegated reader has not, but may meet outcomes while finding records — it states leakage per episode. Evidence: `specs/results/evidence-sized-delivery/goals/GOAL-ESD-CAPACITY/`.
- **GOAL-ESD-ARCH:** `graph-architecture-review.md` applied to ESD-01 validation-origin rows ESD-03 did NOT use (hold-out), plus an independent re-score of a fixed 12-row sample of ESD-03's table (every third row: #1,4,7,...,34), by a delegated reader instructed NOT to open ESD-03's files. Evidence: `.../goals/GOAL-ESD-ARCH/`.
- **GOAL-ESD-VELOCITY:** retrospective only — this epic's timeline (`review/wave-5/review.md` §4) and ESD-01 `cost.md`; plus this ticket's own timings. Evidence: `.../goals/GOAL-ESD-VELOCITY/`.

## Stopping conditions and budget accounting

- Budget: **≤ 48 billed case-runs and ≤ $40** (assignment). Planned: 36 guard + 10 uptake = **46**. The 2 spare runs are NOT reserved for re-runs.
- Every run is billed once and counted, including environment failures. `--max-cost-usd 3` per invocation as a ceiling.
- **No re-runs to improve a score.** A run is repeated only if the harness refused it before an agent started (cost $0, e.g. view over the entry limit), and the refusal is recorded.
- Stop immediately when the running total reaches 48 runs or $40; remaining cases are reported `unmeasured`.
- If the first billed run of an arm shows an environment failure (fixture not placed, hook exit ≠ 0, toolchain unresolved), stop that arm, record it as a validation finding, and do not count its score as instruction pass/fail.
- Evaluator/environment failures (max-turns, UNDECIDED markers, judge errors) are validation findings, not instruction verdicts.

## Evidence paths

- Run JSON per case per arm: `specs/evals/evidence-sized-delivery/runs/<arm>/<case>.json`; console logs beside them.
- Trace-derived reading cost: `specs/evals/evidence-sized-delivery/reading-cost.md`.
- Results: `specs/evals/evidence-sized-delivery/README.md` (UPTAKE evidence_root), goal folders under `specs/results/evidence-sized-delivery/goals/GOAL-*`, summary `specs/results/evidence-sized-delivery/ESD-06/README.md`.

## Amendments

(none yet)
