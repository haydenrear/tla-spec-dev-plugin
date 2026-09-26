# `GOAL-evals-one-command` — Evaluation B (SI-23)

**Measured 2026-09-26 at base `8b6d97e8` (the epic tip), worktree
`../wt-372-evaluation-b`, branch `feature/372-evaluation-b`.**

> **Statement.** Every eval this development loop runs lives in one place — the
> plugin's `evals/` — and runs in one command, without a shim plugin, a
> units-override file, or a second harness in another repository.
>
> **Baseline (b7a7d203).** 2 cases, reachable only through
> `examples/agent_integration/eval-plugin` (a symlink shim built because plugin
> eval refuses a directory over 20,000 entries and `specs/` alone is 20,493); the
> wide lane needs `units-override.txt`.
>
> **Target (four clauses).** all of the loop's cases under the plugin's `evals/`,
> runnable in one command; **at least one case per nested skill**; every case
> green or explicitly UNDECIDED with a reason; no units-override file and no
> second harness.
>
> **Harness.** `claude plugin eval <plugin dir>` over the plugin's own `evals/`,
> each case reported green, red, or UNDECIDED.

---

## Clause 1 — "all of the loop's cases under the plugin's `evals/`, runnable in one command"

### VERDICT: **MET**, with the harness as literally declared noted as still unrunnable.

**75 `case.yaml` files, all under `evals/`** (`find evals -name case.yaml` → 75),
all parse. 2 → 75 against the baseline.

One command: `evals/run.sh`, present and executable.

**The declared harness `claude plugin eval <plugin dir>` still cannot be pointed
at the plugin directory.** The ceiling that forced the baseline's shim has not
gone away — it has been outgrown:

```
specs/ alone            25,604 entries   (baseline recorded 20,493; ceiling is 20,000)
evals/ alone               810
repo (excl. .git, homes) 121,087
```

`run.sh` resolves this by **constructing a view** and invoking
`claude plugin eval "$view"` against it (`evals/run.sh:591`), one invocation per
selector (`:575`, SI-21). So the one command exists and works; the harness string
in the plan describes an invocation that would be refused if anyone typed it.
That is a stale harness declaration, not a broken substrate. Filed
`SI-23-DF-17`.

## Clause 2 — "at least one case per nested skill"

### VERDICT: **NOT MET — 2 of the 11 contained units have zero cases.**

Independently reproduced; this confirms the amendment and the review.

| unit | cases | | unit | cases |
|---|---|---|---|---|
| spec-double-2 | 20 | | git-issue | 3 |
| skt | 17 | | plugin-repository | 2 |
| skill-manager | 11 | | test-graph | 2 |
| git-issue-workflow | 9 | | discovery | 1 |
| git-epic-workflow | 7 | | **git-integration-repo** | **0** |
| | | | **unit-authoring** | **0** |

**72 of the 75 sit under a unit name.** The remaining three are
`evals/harness/` (1) and `evals/unnested/` (2), which belong to no contained
unit.

**75 cases is not per-skill coverage**, and the two units with none are exactly
the two that were nested latest and never got a rung of the ladder. Tracked as
`#392` and deliberately not started by this ticket.

## Clause 3 — "every case green or explicitly UNDECIDED with a reason"

### VERDICT: **NOT MET on the only reading available, and UNDECIDED at this tip.**

At the last whole-corpus run (`CORPUS-2026-09-25.md`, commit `323497e7`,
2026-09-25, 64 cases, $16.23, 43 minutes):

- 58 of 64 decidable; **6 UNDECIDED with a stated reason** (a ~41,000-entry
  branched Skill Manager home against the CLI's 20,000 ceiling) — that half of
  the clause is met, and the UNDECIDED verdicts are named on screen rather than
  scored 0, which is `EA-DF-08` fixed;
- **52 of 58 at 1.00**, mean 0.959 — so **6 cases were not green**, including
  `w-sdc-ticket-binding-bare-adapter-module` at **0.17**, which
  `CORPUS-2026-09-25.md` calls *"the only confirmed substrate defect of the
  session"* (issue `#384`).

Six not-green cases with neither a green verdict nor an UNDECIDED reason means
the clause is **NOT MET** on that run.

**And at this tip it is UNDECIDED**, because:

- the corpus is **11 cases short** of the tip (64 at `323497e7`, 75 at
  `8b6d97e8`) and has not been re-run whole;
- `evals/results/` is gitignored and empty here — no scored run exists at this
  commit;
- **every case is `runs: 1`** (verified: all 75 declare it), and the instrument's
  own recorded spread is 0.89→0.81 and 0.97→0.94 on *unchanged* cases at one
  commit, with one case swinging **±0.8** between identical invocations.

I did not re-run the corpus. A single additional `runs: 1` sweep would have cost
real money and produced numbers that, by the instrument's own record, cannot
support a claim — and re-running only the failures biases the result (measured: 3
of 11 returned 1.00 with nothing fixed for them, and one fell 0.86→0.43). Stated
rather than papered over. Filed `SI-23-DF-18`.

**52/58 is not an improvement on 45/58.** Eleven instrument defects were fixed
between those two runs; the earlier number was wrong and the substrate did not
move. No trend may be drawn from two points across an instrument change.

## Clause 4 — "no units-override file and no second harness"

### VERDICT: **MET**, on a sweep that names what it looked for.

```
find . -name 'units-override*'  (excluding homes and plugin caches)  → none
test -e examples/agent_integration/eval-plugin                        → ABSENT
```

The baseline's symlink shim plugin is gone, and the wide lane no longer needs
`units-override.txt`. The view `run.sh` constructs is not a second harness: it is
built by the one command, inside this repository, and is destroyed with the run.

---

## Regression evidence recorded under this goal

Run in this worktree at `8b6d97e8`, each with the command beside it.

**Repository suite** — `uv run --python 3.12 --with pytest --with pyyaml --with
jinja2 --with hypothesis python -m pytest tests -q
--ignore=tests/test_score_tools.py`:

```
10 failed, 1742 passed, 6 skipped in 327.31s
```

**Compared by NAME against `SI-29/final-failure-names.txt`: identical sets, all
ten, zero diff.** Names in `evidence/repository-suite-failure-names.txt`.

**`tests/test_score_tools.py` once** (this ticket reads the scorecards):
`127 passed in 766.45s`, zero failures.

*Arithmetic note:* the work order quotes the without-`--ignore` figure as
10 failed / 1853 passed. My two runs sum to 1,742 + 127 = **1,869** passed, 16
more than the quoted 1,853. I did not run the combined command, so I am not
asserting the quoted figure is wrong — only that it does not reconcile with the
two runs I did make, and the combined baseline should be re-taken before it is
quoted again. Filed `SI-23-DF-19`.

**Spec-unit tests** — the assignment's `--ticket SI-23` form is known-weak
(`SIS-KICKOFF-F-04`), so **`--target specs/current`** was run and is named here:
`uv run --python 3.12 … tla_spec_dev.py --spec-root specs run spec-unit-tests
--target specs/current` → **9 failed, 47 passed**. Compared by NAME against
`SI-29/spec-unit-failure-names.txt`: **identical, all nine, zero diff.**
*The issue's "7 spec-unit failures that are not yours" is stale — the recorded
baseline and this run both hold nine.* Filed `SI-23-DF-20`.

**Test graphs** — `python3 skills/test-graph/scripts/run.py <graphs>`, verdicts
read from **each run's own fresh `summary.json`**, never from the runner's exit
code:

| graph | runId | status | assertions | verdict |
|---|---|---|---|---|
| `specWorkflow` | `20260926-172628` | **errored**, `complete: false` | 69, **64 passed / 5 failed** | **RED** |
| `cliWorkflow` | `20260926-172739` | passed | 41 / 41 | green |
| `effectProviderExamples` | `20260926-172754` | passed | 8 / 8 | green |
| `sktSurface` | `20260926-173503` | passed | 318 / 318 | green |
| `sktHooks` | `20260926-173600` | passed | 167 / 167 | green |

Four of five reproduce `REVIEW-BEFORE-SI-23.md` §1 exactly (41 · 8 · 318 · 167).
**`specWorkflow` does not**, and the regression is documented under
`SI-23-DF-21` — see the PR body. It is **RED, not UNDECIDED**: it did not end on
a turn ceiling, it failed five named assertions in
`spec.workflow.failure_cleanup_probe`, taking `spec.reference.adapters_resolve`
down as skipped collateral.

---

## Summary

| clause | baseline | measured | target | verdict |
|---|---|---|---|---|
| all cases under `evals/`, one command | 2 cases behind a symlink shim | **75 cases**, all under `evals/`, all parse; `evals/run.sh` runs them | all, one command | **MET** (declared harness string stale: `specs/` is 25,604 entries vs a 20,000 ceiling) |
| at least one case per nested skill | — | **9 of 11 units covered; `git-integration-repo` 0, `unit-authoring` 0**; 72 of 75 under a unit name | 11 of 11 | **NOT MET** |
| every case green or explicitly UNDECIDED with a reason | — | last whole run: 6 UNDECIDED **with reasons**, but **6 not green** incl. 0.17; at this tip **no scored run exists** and the corpus is 11 cases short | all | **NOT MET on the last run; UNDECIDED at this tip** |
| no units-override, no second harness | shim + `units-override.txt` | both **absent** | absent | **MET** |

**Moved by:** SI-15 (suite moved to `evals/`), SI-10/SI-14 (the runner and the
pin), SI-19–SI-22 and SI-29 (the ladder's 14 cases), SI-21 (one invocation per
selector).

**Instrument limits stated:** `runs: 1` on all 75 cases; `--runs 6` does not pin
a score; 52/58 is not improvement on 45/58 across an instrument repair; the
corpus predates this tip by 11 cases and one day; **the scorecard — the
instrument this epic uses to decide its own goals — still has no eval case**,
open since wave 4, narrowed by SI-21, and restated open here.
