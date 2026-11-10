# GOAL-ESD-UPTAKE — evidence root (ESD-06)

Declaration: `specs/results/evidence-sized-delivery/ESD-06/declaration.md` (committed in `4f323cc6`
before any billed run). Arms: BASE = `a1ff56cf` (main) from a detached scratch checkout; for the
uptake cases `a1ff56cf` + local commit `14e3247c` adding only `cases/**`. TIP = `4f323cc6`
(epic tip `5404a3c1` + declaration + cases). Same eval home, same day (2026-11-10 14:48–15:21Z),
model `claude-opus-5-5`, Claude Code 2.1.322, toolchain pin skt `365abbf1`, 1 run per case per arm.

Files: `cases/` (five uptake cases), `runs/<arm>/<case>.json|.log` (harness JSON and console log
per run), `runs/analysis.tsv` (per-run score, graders, turns, cost, reads), `reading-cost.md`.

**Metric / baseline / target.** Matched base-vs-tip scores on uptake cases, reading cost, and
regressions on existing affected cases. Baseline unmeasured. Target report-only; guard clause:
0 existing affected cases that pass on base fail on tip.

## A. Guard: 18 existing cases of the edited skills

| case | base | tip | |
| --- | --- | --- | --- |
| start-from-the-spec-not-the-source | 1.00 | 1.00 | |
| epic-mode-is-not-main | 1.00 | **0.33** | instrument false red (below) |
| w-epic-assignment-no-force-on-blocking | 1.00 | **0.88** | instrument false red (below) |
| w-epic-force-when-owner-decided | 1.00 | 1.00 | |
| w-epic-merged-by-is-epic-owner | 1.00 | 1.00 | |
| w-epic-plan-free-form-lane | 1.00 | 1.00 | |
| w-epic-retire-part-of-goal-warns-only | 1.00 | 1.00 | |
| w-giw-epic-ticket-plan-values-win | 1.00 | 1.00 | |
| w-giw-epic-ticket-stops-on-wrong-pr-base | 1.00 | 1.00 | |
| a-work-order-not-a-wish | 1.00 | 1.00 | |
| w-roles-epic-finds-its-empty-inbox | 1.00 | 1.00 | |
| w-roles-propagation-is-checkable | 0.92 | 1.00 | base missed `tool_used: Skill` |
| w-roles-review-finds-its-destination | 1.00 | 1.00 | |
| w-roles-testing-finds-its-destination | 1.00 | 1.00 | |
| w-roles-ticket-finds-its-back-channel | 1.00 | 1.00 | |
| w-sdc-attribution-before-close | 1.00 | 1.00 | |
| compose-a-behavioural-graph | 1.00 | **0.33** | instrument false red (below) |
| w-tg-run-a-graph-not-bare-gradle | 0.71 | 0.71 | same grader red on both arms |

**Raw guard count: 3 cases pass on base and fail on tip. After reading every trace: 0 attributable
to the instructions; all 3 are instrument false reds** (validation findings, `ESD-06-DF-04`):

1. `compose-a-behavioural-graph` (tip): the agent scaffolded `test_graph/`, wrote five nodes and
   wired the graph, then left its shell in `test_graph/sources`. `verify.sh` ran from that Stop-hook
   cwd and logged `no test_graph/ directory`, so `.eval/graph` was never written. The base agent
   ended in the workspace root. Grader red, work present (`/private/tmp/e-uqJN40`, kept).
2. `w-epic-assignment-no-force-on-blocking` (tip): 3 Bash calls (budget 3), but the session
   transcript records the first Skill and Bash `tool_use` twice with the SAME id (the Skill call
   carried `args`); `expect.py` counts entries, not ids, and saw 4 → `within-budget` red.
3. `epic-mode-is-not-main` (tip): `epic_plan.py` read `self-merge: True` from the PLAN's
   "I will **not**: run `gh pr merge` or self-merge" list — a prohibition read as a proposal. Same
   grader false-negative shape BS-17 recorded for this case on main. The plan names the epic base,
   `Refs`, no `Closes`, stop at PR open: the behaviour is correct.

Guard verdict: **met on the attributed count (0), with the raw count 3 stated**; n = 1 per arm, so
an instruction effect of the size of the harness noise cannot be excluded.

## B. Uptake: five new cases, no answer in the prompt

| case | role | base decision (llm) | tip decision (llm) | retrieval regex base / tip | score base → tip |
| --- | --- | --- | --- | --- | --- |
| esd-review-graph-node-change | review | PASS | PASS | ✗ / ✓ | 0.83 → 1.00 |
| esd-plan-two-capacities | planning | **FAIL** | PASS | ✗ / ✓ | 0.17 → 1.00 |
| esd-ticket-red-not-mine | ticket | PASS | PASS | ✓ / ✓ | 1.00 → 1.00 |
| esd-model-change-recalibrate | wave owner | PASS | PASS | ✗ / ✓ | 0.83 → 1.00 |
| esd-expensive-eval-checkpoint | planning (cost) | PASS | PASS | ✗ / ✓ | 0.83 → 1.00 |

Score differences are dominated by the retrieval regex, which is tip-only by construction. **On
the decision grader alone: base 4/5, tip 5/5.** The one difference (plan-two-capacities) is in
*reasoning shape*: the base agent made the same practical decision (6 independent tickets, no
billing ticket in wave 1, an instrument ticket) but without separate review and verification
estimates, which the rubric scores 0.5 and the binary judge records as FAIL (the `llm` grader has
no half vote — instrument limitation, `ESD-06-DF-04`). Read of every final response: no judge
error found (no false greens/reds of the judge on these 10 runs).

**What the tip changed that the decision score does not show** (`reading-cost.md`): every tip run
opened the canonical page first and cited it; two base runs said the plugin had no guidance for
the question and improvised the right answer from general sections. Reading cost fell (lines
−23 %, searches 30 → 10, turns −41 %, $ −22 %).

**Uptake verdict: measured; report-only target.** Retrieval through existing entry points: 5/5 on
tip vs 0/4 tip-only pages on base. Decision quality: indistinguishable on 4 of 5 at n = 1; the
model already reaches these decisions without the guidance (ceiling effect), so these cases do not
show that the guidance changes outcomes, only that roles find and use it cheaply.

## Scenarios from #240 and coverage

| scenario | covered by | result |
| --- | --- | --- |
| larger safe batch with expensive stable evals | esd-expensive-eval-checkpoint | base & tip pass |
| unstable graph refusing expansion | esd-plan-two-capacities | base & tip refuse expansion |
| review capacity exceeding verification capacity | esd-plan-two-capacities | tip only states both |
| the reverse (verification exceeding review) | — | **unmeasured** |
| sparse / biased history | esd-plan-two-capacities (one prior epic) | tip names cold start |
| model-version change | esd-model-change-recalibrate | base & tip hold at 4 |
| stale saved context | esd-review-graph-node-change | base & tip flag replay |
| graph-origin defects detected by another channel | — | **unmeasured** |
| green but blind oracle | esd-review-graph-node-change | base & tip ask for a red control |
| attribution conservation through architecture changes | — | **unmeasured** |
| roles retrieving guidance without the answer in the prompt | all five | tip 5/5 first-read canonical page |
