# ESD-06: integrated evaluation of the evidence-sized-delivery instructions

Ticket #240 (epic #234), `role: evaluation`, wave 6. Owns GOAL-ESD-UPTAKE, GOAL-ESD-CAPACITY,
GOAL-ESD-ARCH, GOAL-ESD-VELOCITY. Declaration committed before any billed run: `declaration.md`
(with post-run amendments). No script, grader code, runner or harness change; five declarative
cases (data) and evidence documents only. No skill instruction edited.

## Verdicts

All four targets are report-only (owner, 2026-11-10: no numeric threshold). Targets were not edited.

| goal / clause | baseline | measured | target | verdict |
| --- | --- | --- | --- | --- |
| UPTAKE — guard: existing affected cases passing on base and failing on tip | unmeasured | raw **3 / 18**; attributed to instructions **0 / 18** (all 3 instrument false reds, traces read) | 0 | **met** (attributed); raw count stated; n = 1/arm |
| UPTAKE — uptake cases, decision grader | unmeasured | base **4/5**, tip **5/5** (one reasoning-shape difference) | report-only | **measured**: no outcome difference shown beyond one case (ceiling effect) |
| UPTAKE — retrieval and reading cost | ESD-05 estimate +3.2–6.3 % mandatory lines | tip opened the canonical page first in 5/5; base searched (30 vs 10 Grep/Glob), lines read −23 %, turns −41 %, $ −22 % | report-only | **measured** |
| CAPACITY — held-out episodes with both estimates + defensible decision | unmeasured | **4/4**; outcome agreement 1 agree / 2 partly / 1 disagree | report-only | **measured** (operable; predictive skill weak and leakage-contaminated) |
| ARCH — hold-out validation-origin rows flagged/partial/missed | ESD-03 self-applied 17 F / 13 P / 6 M of 36 | blind hold-out **10 F / 24 P / 14 M of 48**; 0 F of 27 non-node defects; re-score of 12 author rows agrees 8/12, author F 5 → blind 2 | report-only | **measured**; "flags most" does **not** hold blind |
| VELOCITY — accepted scope per elapsed time, improvement | unmeasured (no start timestamps anywhere) | this epic: 5 tickets in 1 h 34 m, no human wait; ESD-06 ≈ 40 min, $15.67 | report-only | **unmeasured** for improvement: no before-value; observation plan in the goal file |

Details: `specs/evals/evidence-sized-delivery/README.md`, `.../reading-cost.md`,
`../goals/GOAL-ESD-{CAPACITY,ARCH,VELOCITY}/`.

## Budget

| | runs | agent $ | judge $ |
| --- | --- | --- | --- |
| base (`a1ff56cf`; uptake on `a1ff56cf`+`14e3247c` cases) | 23 | 7.71 | 0.013 |
| tip (`4f323cc6`) | 23 | 7.93 | 0.013 |
| **total** | **46 / 48** | **15.64** | **0.03** → **$15.67 / $40** |

No re-run, no refusal, no `error_max_turns`. Model `claude-opus-5-5` in all runs; Claude Code
2.1.322; judge = harness default (haiku).

## False reds / greens, escapes, uncertainty

- Instrument false reds: 3 (guard; ESD-06-DF-04). Judge disagreements with my reading of the 10
  uptake responses: 0; one rubric half-tier collapsed to FAIL by the binary judge.
- ARCH: author's F on EA-DF-15, DEF-503, DEF-124 are false greens of the self-applied table.
- Escapes: none measurable (no new delivery under these instructions yet).
- Uncertainty: every eval cell is n = 1 (±0.8 between identical invocations documented);
  CAPACITY n = 4 with leakage (the page's own §9 describes two of the episodes); ARCH one blind
  reader, 8/12 inter-rater agreement.

## Not measured

Reverse capacity (verification > review); graph-origin defects caught by another channel;
attribution conservation through an architecture change (§7b); finalizer → next-epic estimate;
longitudinal velocity; any real-repository pilot beyond this ticket's own timings.

## Validation

| entry | result | file |
| --- | --- | --- |
| `validation.spec_unit` | 2 failed, 54 passed — the same two known base failures, none new | `spec-unit.txt` |
| `validation.repository_unit` | N/A (assignment: eval lane via `evals/run.sh`) | — |
| eval-home check | `setup-eval-home.sh --check` green on both arms after copying the 4 offline wheels | `declaration.md` |

## Model result

**No-op.** `specs/current`, `specs/desired_program_model` and `specs/program_model` are unchanged:
this ticket measures and adds evidence/case data; it changes no action, variable or invariant
(`bug_attribution.md` §7d: evaluation evidence is not a model change).

## Scratch artifacts for the epic agent's sweep

- Detached measurement checkout `/Volumes/dev/tla-spec-dev-plugin-esd06-base` (worktree of the main
  checkout at `a1ff56cf`, plus local commit `14e3247c`). Remove at the sweep.
- Staged views `/private/tmp/esd06-view-{base,tip}` and kept sandboxes `/private/tmp/e-*`
  (paths in `runs/*/*.json`).
