# GOAL-ESD-VELOCITY — verdict (ESD-06)

**Metric:** accepted scope per elapsed time and cost-component share, from close history / PR / run
timestamps (retrospective) and the ESD-06 pilot. **Baseline:** unmeasured. **Target:** report-only.
**Verdict: unmeasured** for any velocity *improvement*: no record before this epic timestamps the
start of work, so there is no before-value to compare against, and one epic cannot carry a causal
claim. What is measured is reported below as a descriptive baseline for the next epic.

## 1. Retrospective (ESD-01, cited, not re-derived)

- Implementation active time is **unknown in all six audited repositories** (`ESD-01/cost.md` C13,
  C30): close manifests carry only close times, PRs are opened after the work.
- The owner's "validation takes 10–100× implementation" can be neither confirmed nor refuted
  (`cost.md` §4).
- Only CDC separates phases: review + graphs/merge ≈ 2.6–3.0× implementation (C17, C18); idle
  39–57 h per epic attributed to neither side.
- End-to-end time is dominated by waits/holds: bug-sweep milestone 1 landed 2 h 34 m after kickoff
  (C1) but the epic merged 48 h 13 m after kickoff; a 29 h window (C12) cannot be split.

## 2. This epic (#234), from PR and commit timestamps (`review/wave-5/review.md` §4, re-read via `gh`)

| ticket | PR | opened | merged | open→merge |
| --- | --- | --- | --- | --- |
| plan commit `9635bad2` | — | 2026-11-10T12:58Z | — | — |
| ESD-01 | #255 | 13:31:09Z | 13:31:45Z | 36 s |
| ESD-02 | #256 | 13:45:17Z | 13:45:50Z | 33 s |
| ESD-03 | #257 | 14:01:07Z | 14:01:51Z | 44 s |
| ESD-04 | #258 | 14:16:08Z | 14:16:46Z | 38 s |
| ESD-05 | #259 | 14:31:28Z | 14:32:08Z | 40 s |
| ESD-06 | (this PR) | started 14:43Z (`setup-eval-home --check`) | — | see §3 |

Five serial instruction tickets in **1 h 34 m** from plan commit to last merge (≈ 15–16 min per
ticket between merges). No human wait (`gate: false`, owner review deferred to the end). Validation
per ticket ≈ 1 min (doc-contract ≈ 44 s, spec-unit ≈ 20 s, TLC ≈ 2 s); agent work dominates.
Accepted scope: 5 tickets / 0 reopened / 0 conflicts. Scope-item counts per ticket were not recorded
(the `scope items` line was introduced by ESD-05, i.e. after ESD-01..04 ran).

## 3. ESD-06 pilot (this ticket's own costs)

| component | value | source |
| --- | --- | --- |
| started_at | 2026-11-10T14:43Z (first command: `setup-eval-home.sh --check`) | session |
| non-billed replays (CAPACITY, ARCH), delegated, concurrent | ≈ 6 min and ≈ 8 min agent time | agent run durations |
| billed eval phase, both arms concurrent | 14:47:43Z → 15:21Z ≈ 34 min wall; 46 runs; 1,268 s (base) + 1,338 s (tip) of run time | `specs/evals/evidence-sized-delivery/runs/*/*.json` |
| billed cost | $15.67 of $40 | same |
| per guard case | ≈ 0.6 min, $0.34 average | same |
| trace reading and write-up | ≈ 15 min | session |

The fixed cost of the integrated comparison (≈ $16, ≈ 35 min) was paid once for the five
instruction tickets, i.e. ≈ $3.1 and ≈ 7 min per ticket — the amortization `step-sizing.md` §4
recommends; a per-ticket eval of the same scope would have cost ≈ 5×.

## 4. Why this is unmeasured, and the observation plan

A velocity improvement needs a before and an after measured the same way. Before this epic there is
no start timestamp and no scope count; this epic is the first with timestamps that close the loop,
and it is a prose-only epic run by one agent with no human wait, so its 15 min/ticket is not
comparable to the bug-sweep's or CDC's mixed code/graph work.

Observation plan (no new machinery; uses only conventions ESD-05 landed):
1. Every ticket PR's `## Review input` opens with the delivery line
   `started_at: <UTC>; agent: <model and version>, <harness and version>; scope items: <n>`
   (`git-issue-workflow/references/epic-ticket.md` §7, `complete.md`). Elapsed = merge time −
   `started_at`; throughput = Σ scope items / epic elapsed.
2. Each milestone review fills `human-review.md` §3.5 *Delivery velocity and step size*
   (implementation vs review vs validation vs wait, each `unknown` where unrecorded).
3. The finalizer writes the *Next epic's starting estimate* (`finalize.md` §2c).
4. After **two further epics** with delivery lines, compare scope-items per elapsed hour and the
   validation/review/wait shares across the three, per component mix and model — report it as
   descriptive (selection and model confounding, `step-sizing.md` §7), never as a causal effect of
   this epic.
5. Falsifier for "the instructions slowed delivery": a rise in validation share or repeat runs per
   accepted item at matched component mix.
