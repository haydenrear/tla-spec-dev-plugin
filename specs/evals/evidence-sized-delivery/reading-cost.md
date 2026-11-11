# Reading cost and retrieval, uptake cases (from `--keep-temp` traces)

Derived by reading each run's `trace.jsonl` (tool_use inputs; lines = newline count of the Read
tool results). Skill-tool bodies (SKILL.md text injected by the Skill tool) are NOT counted in
"lines", so lines are a lower bound on context read. One run per cell. Model `claude-opus-5-5` in
all 46 runs; Claude Code 2.1.322. Ad-hoc read commands, nothing committed.

| case | arm | Skill units opened | files Read (canonical page in **bold**) | Read lines | Grep/Glob | turns | wall s | agent $ |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| review-graph-node-change | base | spec-double-2, test-graph | agent_roles §(150+90), human-review ×2, failure-loop | 392 | 2 | 11 | 51 | 0.306 |
| | tip | test-graph, spec-double-2 | **graph-architecture-review.md** (first read), agent_roles ×2, validation-review, human-review ×2 | 678 | 3 | 14 | 58 | 0.414 |
| plan-two-capacities | base | git-epic-workflow | validation-review, plan-and-schedule, agent_roles, goals-and-evaluation, human-review, bug_attribution | 680 | 8 | 17 | 72 | 0.470 |
| | tip | git-epic-workflow | **step-sizing.md** (first read), plan-and-schedule ×2 | 511 | 1 | 7 | 76 | 0.338 |
| ticket-red-not-mine | base | git-issue-workflow, spec-double-2 | epic-ticket, validation-loop, **bug_attribution.md** (whole), workflows, validation-review, deferment | 1949 | 4 | 15 | 65 | 0.652 |
| | tip | git-issue-workflow | **bug_attribution.md** (whole, first read), epic-ticket, validation-review | 1206 | 5 | 11 | 56 | 0.510 |
| model-change-recalibrate | base | git-epic-workflow | validation-review, goals-and-evaluation, eval_scorecard | 243 | 11 | 17 | 60 | 0.416 |
| | tip | git-epic-workflow | **step-sizing.md** (only read) | 301 | 0 | 4 | 31 | 0.194 |
| expensive-eval-checkpoint | base | git-epic-workflow | validation-review, goals-and-evaluation, human-review | 670 | 5 | 11 | 50 | 0.384 |
| | tip | git-epic-workflow | **step-sizing.md** (first read), plan-and-schedule | 320 | 1 | 6 | 33 | 0.287 |
| **total** | base | | | **3,934** | **30** | **71** | **298** | **2.228** |
| | tip | | | **3,016** | **10** | **42** | **254** | **1.743** |

**Reading.** On the tip the role reached the canonical page **as its first file read in 5 of 5
runs** (graph-architecture-review ×1, step-sizing ×3, bug_attribution ×1), routed from the Skill
body or the `agent_roles.md` Evidence-routing table. Search effort fell 30 → 10 Grep/Glob calls,
lines read −23 %, turns −41 %, agent cost −22 %, wall −15 %. The base agents searched and, in two
runs, said explicitly that the plugin had no guidance for the question ("no section that talks about
two capacities"; "no section about switching agent models"). This contradicts the wave-5 suspicion
that real agents would read *more* than ESD-05's +3.2–6.3 % mandatory-path estimate: on these five
tasks they read less, because the routing replaced search. n = 1 per cell; ±0.8 score movement
between identical invocations is documented for this harness (`evals/README.md`), and cost/turn
counts vary run to run, so treat the direction, not the percentages, as the finding.

No run opened `specs/evals/evidence-sized-delivery/**` (the graders) or any
`specs/results/evidence-sized-delivery/**` file; tip skill text cites those result paths, but no
tool call read them.
