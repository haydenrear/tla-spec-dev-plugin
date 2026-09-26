# Handoff to the next epic

**Written 2026-09-26.** Predecessor: `self-improvement-substrate`, **closed**.
Successor epic issue: **`haydenrear/tla-spec-dev-plugin#45`**.

Read this first, then #45, then `REVIEW-BEFORE-SI-23.md`, then `CLOSE-OUT.md`.

---

## 0. Where everything now lives — this changed today

| | |
| --- | --- |
| **code + issues** | `haydenrear/tla-spec-dev-plugin` |
| `haydenrear/tla-spec-dev` | **ARCHIVED**, read-only |
| epic branch / `main` | both at the same tip; the epic branch is done |
| both Skill Manager homes | load the tip — `committed == released == loaded` |

**114 issues moved** and were renumbered. Every artifact in this directory cites
the **old** numbers. `ISSUE-MAP.md` is the table. The four you will want:

| what | old | **new** |
| --- | --- | --- |
| **the next epic** | #393 | **#45** |
| the close-mode knob | #394 | **#46** |
| packaging question | #392 | **#44** |
| the closed epic | #333 | **#8** |

Three stale PRs (#324, #129, #50, all from epics closed months ago) and 108
closed issues stayed behind and are frozen. Nothing open was left there.

---

## 1. Start here, in this order

**1. `#46` — the close-mode knob.** Do it first, because the predecessor could
not close itself without it and the next epic will hit the same wall. It is also
small, and finishing it pays a debt this handoff is standing on: **the
predecessor's close was done by hand.**

**2. `#45` §D — the judged round for `GOAL-blockers-propose`.** SI-08 asked
SI-23 for it, SI-23 did not run it and said so. That goal has stood on a
**frozen NOT MET with a known confound** since wave 10, and SI-23 argues the
confound has now lifted for the first time. It is the highest-value single
measurement available and it gets stale, not safer, with age.

**3. `#45` §A — the cutover discipline.** The one-off is done; the discipline is
not. Nothing stops the three substrates drifting apart again next week.

---

## 2. What the predecessor actually established

Do not re-derive these:

- **One plugin, eleven units.** Zero standalone copies in any home.
- **A five-rung eval ladder whose ordering is provable in git** —
  `merge-base --is-ancestor` rc=0 on every rung, no record commit containing a
  `case.yaml`. The only goal decided by a check nobody can argue with.
- **Role-routed disclosure**, references only, no detection code, with a
  propagation destination per role and three new inboxes.
- **75 eval cases, all parsing, one command.**
- **skill-manager v0.28.2 released**, ending a six-day window in which a
  successful install exited 11 because the fix existed and had never shipped.

---

## 3. What is open, and its real state

| | |
| --- | --- |
| **#46** | close-mode knob — and the receipt check counts the wrong tickets |
| **#44** | do `git-integration-repo` and `unit-authoring` belong here? Measured; **not symmetric** |
| **#36** | adapter bindings — residual hand-edit hole, no check |
| **#37** | SessionStart hook exits 0 silently when it cannot resolve an interpreter |
| **#39** | `skill-manager uninstall` and `skt status` resolve different homes |
| ledger | 23 SI-23 findings in `specs/results/deferred/SI-23.yaml`, 5 high |
| — | **the scorecard still has no eval case**, open since wave 4 |
| — | `install-pipeline` holds six findings and no model |
| — | `specs/tickets/SI-01…SI-17` still exist; `finalize.md` §1 says they must not |
| — | `specs/program_model/spec_manifest.yaml` is **stale** — still names `active_ticket: CM-01` |

---

## 4. Three traps that will cost you a day each

**The interpreter.** `python3` is a **zsh alias** here resolving to a
PyYAML-less Homebrew 3.14; inside a bash script it resolves to
`/usr/bin/python3`, which **has** PyYAML. `SI-21-DF-01` recorded this. SI-29
then read that row and hit it inverted, filing a false high-severity finding.
The epic agent repeated the claim to the owner before checking. **Print
`sys.executable` whenever you shell out to measure.**

**Scores do not pin.** `runs: 1` on the corpus; and `--runs 6` does **not** fix
it — measured 0.89→0.81 and 0.97→0.94 on *unchanged* cases at one commit. State
sample count and spread, never a bare mean. And **52/58 is not an improvement on
45/58**: eleven instrument defects were fixed between those runs.

**Graph verdicts lie if you read the exit code.** `run-graphs.py` always exits
0, and `build/validation-reports/` keeps passing reports from earlier runs, so a
graph that never executed looks green. Read each run's **own fresh
`summary.json`**. `sktSurface` and `sktHooks` are **opt-in** and are skipped
silently by the bare command.

---

## 5. The two practices that actually worked

**Independent verification of every ticket report against the repository.** Four
of the last five tickets corrected an error in the work order they were given,
and two corrected claims the epic agent had already made to the owner. One
caught a `specWorkflow` regression the epic agent had introduced through its own
review note and then reported green.

**Falsify both ways.** A check that cannot be shown to fire is the defect it
exists to catch. Mutation-tested twice here; both times the test discriminated.

---

## 6. The thing to carry, stated plainly

The substrate was never the problem. The suite held at the same ten failure
names across 29 tickets and every graph is green. **What repeatedly failed was
the measurement and the bookkeeping around it**, and the single recurring cause
was reporting *the step performed* instead of *the outcome*.

The predecessor's sharpest evidence about its own thesis is not a success. It is
that `SI-21-DF-01` was filed, read two waves later by another agent, and then
**re-committed by its reader** — and then repeated a third time by the epic
agent. The same shell-quoting error recurred **six times in one session**
against a rule written after the first occurrence.

**A lesson recorded is not a lesson applied.** Every check this epic added
exists because something that was already written down failed to stop the thing
it described. That is what #45 is for.
