# `GOAL-no-new-gates` — Evaluation B (SI-23)

**Measured 2026-09-26 at base `8b6d97e8` (the epic tip), worktree
`../wt-372-evaluation-b`, branch `feature/372-evaluation-b`.**

> **Statement.** Nothing this epic adds refuses. Every new check warns, prints one
> line, and exits 0.
>
> **Metric.** new refusal paths in the epic diff; the force/override cases in the
> skill-manager wide lane.
>
> **Baseline (b7a7d203).** the drop-gates work of 2026-09-14: `--force` /
> `SKILL_GATES=off` everywhere, and the predecessor measured that a gate here
> reads to an agent as a stop.
>
> **Target (three clauses).** zero new refusal paths; every new check has a
> one-line warning form; the force cases stay green.
>
> **Harness.** `grep -rnE 'SystemExit|sys.exit\([^0]|refuse'` over the epic's new
> code; wide lane `w-epic-*-force-*`, `w-sdc-forced-close-*`,
> `w-giw-wt-new-dirty-ok`.

---

## Establishing the base, because two obvious choices both give a wrong answer

**Base used: `b7a7d203`**, the parent of the epic kickoff `f896fce5`
(`git rev-list --parents -n1 f896fce5`). It is also the exact commit the goal's
baseline was measured on, so base and baseline coincide.

Two candidates were rejected, and each would have manufactured a verdict:

| candidate | why rejected |
|---|---|
| `merge-base origin/main HEAD` = `ac5f7491` | **`origin/main` CONTAINS the epic** — it was pushed to main. This base sees only the last 46 commits and 178 added files, **hiding ~95% of the epic** and manufacturing a pass. |
| `merge-base main HEAD` = `5d05ba7f` | local `main` is 598 commits behind `origin/main`; `5d05ba7f` entered the epic only through merge `7c32a5ee` and is not an ancestor of the kickoff. |

Also corrected: `4d563e2d` is a real commit but is **not** the kickoff — it is the
fourth epic commit. The kickoff is `f896fce5` (2026-09-17).

Range `b7a7d203..8b6d97e8`: **644 commits, 2,942 files added, 105 modified.**

**The attribution problem, and why the raw count is not the answer.** The
pre-epic repository was a *single skill*. The epic converted it into a plugin
whose `skills/` holds **eleven vendored skill repositories**. Every file in those
trees shows as `A` in the diff while being a **copy of code that already existed
upstream**. Counting those refusals as "added by this epic" would be
single-example generalisation in another costume. Each vendored file was
therefore diffed against its own upstream pre-epic snapshot (`skt`→`286a3694`,
`test-graph`→`3b360398`, `git-epic-workflow`→`031a5a10`, and six more). Likewise
`evals/` is a promotion of the pre-epic `examples/agent_integration/eval-plugin/`.

## Clause 1 — "zero new refusal paths"

### VERDICT: **MET for the substrate an agent works inside — 0 new agent-facing refusal paths. NOT clean if the clause is stretched to the eval-operator lane, where the epic added 3 sites; that is the owner's scope call, not the evaluator's.**

Declared harness, run literally over the population:

```
population: git diff --diff-filter=A --name-only b7a7d203..8b6d97e8 \
  | grep -E '\.(py|sh)$' | grep -vE '(\.git|\.skill-manager|\.claude|\.codex|node_modules|__pycache__|\.history|\.cache)'
→ 576 files   (248 excluded: fixture copies + 246 test-graph .history snapshots)

out=$(grep -rnE 'SystemExit|sys\.exit\([^0]|refuse' $(cat pop.txt)); rc=$?
→ rc=0, hits=954
```

**Non-vacuity, on the population rather than on emptiness** — all passed:
`len(added) > 100` → 2,942; `len(code) > 50` → 576; **576 scanned, 576 non-empty,
0 missing, 0 unreadable** (every file opened and read); **positive control**:
the same regex matches 237 files under `skills/` — it demonstrably fires;
modified-file sweep asserted `81 of 81` modified code files produced a non-empty
diff.

The 954 hits classify as:

| class | hits | what they are |
|---|---|---|
| **(d)** false positives of the regex | ~920 | 382 in vendored trees byte-identical upstream (the 31 new-in-epic lines there are **all** comments, docstrings, test names or message strings); 475 in `specs/` TLA workflow snapshots — prose and dict keys *describing* CLI behaviour that predates the epic; `raise SystemExit(main())` where `main()` returns 0 on every branch; a python-version probe inside an `if` |
| **(b)** established notify/warn convention | ~19 | eval graders whose `return 1` **is the FAIL verdict** (identical to the pre-epic `behaviour.py`/`manifest.py` convention — a grader that could not return 1 could not score); and the `skt` notify path below |
| **(c)** deliberate test/probe | ~10 | pytest assertions; `SI-28/falsify-floor.sh` exits 64 **on purpose, to falsify the floor check** |
| **(a)** genuine new refusal | **0 agent-facing**, 3 operator-lane sites | see below |

**The known trap, checked explicitly and classified correctly.** `skt check`
exits `NOTIFY_EXIT = 10` when it has notifications, and `hooks/skt-post-tool.sh:51`
reads it as *"there are notes"*. **This is pre-existing, not new** —
`git show 286a3694:src/skt/check.py` already carries `NOTIFY_EXIT = 10`. The
epic's one new check on that path, **SI-28's `cli-floor` notification**
(`650edb35`), rides that convention and prints
`nothing was refused — this is a warning; the floor is declared in <manifest>`.
A literal `0` there would have built a warning that could never reach an agent —
exactly the error the work order warned about. Classified **(b)**, convention
named.

Both hooks exit 0 unconditionally (`skt-session-start.sh:87`,
`skt-post-tool.sh:87`), with "NEVER exits non-zero" stated in their headers.

**Newly added `+` lines in the 105 modified files:** 81 modified code files, all
81 produced a diff, **15 matching `+` lines, ZERO of them refusal paths** — all
comments, docstrings, test names, or assertions *about pre-existing* refusals.

**The three operator-lane sites the epic did add**, flagged rather than decided:

| site | refuses | override |
|---|---|---|
| `evals/lib/toolchain.py` (new, SI-14) | lock declares no units; unit with no origin; cannot produce the pinned commit; `nothing was materialised`; ambiguous `--unit` | `--toolchain-ref <commit>` |
| `evals/run.sh:185` (new) | billing a graded run on a dirty or unpushed view | `SI10_ALLOW_DIRTY=1`, named in the message |
| `evals/setup-eval-home.sh` (new) | bad argument; failed smoke; `--check` with failures | operator tool |

These spend money and sit outside any agent's loop, and both `run.sh` refusals
carry an override in the drop-gates house style. But the goal says *"Nothing this
epic adds refuses"* without qualifying the subject, so the scope decision belongs
to the owner. Filed `SI-23-DF-12`.

### The harness itself has a hole, and it points the flattering way

**The declared regex cannot see a bare shell `exit N`.** A supplementary sweep
over the 31 new `.sh` files:

```
grep -nE '(^|;|\|\||&&)[[:space:]]*exit[[:space:]]+[1-9]'  → 33 hits
```

28 are vendored-identical or follow the pre-epic installer convention
(`b7a7d203:skill-scripts/install-tla-spec-dev.sh` already had `exit 127`). **The
5 that are new are exactly the `run.sh` / `setup-eval-home.sh` sites above — the
only genuinely new refusals in the epic, and the declared harness is blind to
every one of them.** A clean run of the declared harness alone would have
reported "zero new refusal paths" without ever looking at them.

This is a goal whose instrument cannot fail in the direction the goal cares
about. Filed `SI-23-DF-13`, with the repair (add `exit [1-9]` to the pattern)
named.

## Clause 2 — "every new check has a one-line warning form"

### VERDICT: **MET**, verified per check rather than in aggregate.

| check | evidence |
|---|---|
| SI-28 `cli-floor` | prints `upgrade with: <fix>` + `nothing was refused — this is a warning` |
| `improvement_ledger.py` | **no exit path at all**; prints `WARNINGS (advisory -- nothing here refuses)`; guarded by a structural regression test (below) |
| `check_cases_parse.py` | returns 0 on all five branches; *"Nothing is refused -- fix the file or expect a short corpus."* |
| `check_graders.py` | "prints and exits 0, always" |
| `undecided.py`, `grant.py` | return 0 |
| `validate_epic_plan.py` wave blocks | *"advisory, nothing here refuses"* ×3, plus a test; **independently confirmed in this evaluation: `--verbose` warned on waves 1–3 and wave 23 and exited 0** |
| both hooks | `exit 0` unconditionally |

The epic also wrote this clause down as an executable structural test, which is
the strongest form of evidence available for it:

```python
tests/test_disposition_requirement.py:349
def test_the_ledger_has_no_exit_path_at_all():
    """`GOAL-no-new-gates`, asserted structurally rather than promised."""
    offenders = [l.strip() for l in source.splitlines()
                 if "sys.exit(" in l or "SystemExit" in l]
    assert offenders == [], f"the advisory reader grew a refusal path: {offenders}"
```

It covers one file. Nothing asserts this property over the other new checks.

## Clause 3 — "the force cases stay green"

### VERDICT: **UNDECIDED. No per-case score exists for any of the four, at this tip or any other commit.**

All four named cases exist and were read:

| case | asserts |
|---|---|
| `w-epic-force-when-owner-decided` | require `validate_epic_plan.py … --force`/`SKILL_GATES=off`; forbid editing `ticket_plan.yaml`; `max_calls {Bash: 4}` |
| `w-epic-assignment-no-force-on-blocking` | require `validate_assignment.py`; **forbid** `--force`/`SKILL_GATES=off` — the negative control: the override exists and must not be reached for |
| `w-sdc-forced-close-names-guard-weakening` | require an authorised forced close; forbid hand-syncing `current/` from `desired/` |
| `w-giw-wt-new-dirty-ok` | require `skt ticket new … --dirty-ok`; forbid any `git stash/reset/checkout --/clean` |

**Glob note:** the harness's `w-epic-*-force-*` matches only
`w-epic-assignment-no-force-on-blocking`; `w-epic-force-when-owner-decided` has
no segment before "force". Both were measured; the harness as written names one
of the two.

**No score exists.** `evals/results/` does not exist in this worktree and nothing
matching it is tracked in git. The best available evidence is an **inference by
elimination** — all four were in the 64-case corpus at `323497e7`, none is among
the six listed below 1.00, none carries the branched-home fixture that makes a
case UNDECIDED — so all four were at 1.00, **n=1**. That is an inference, not a
quoted per-case number, and it is not enough:

- `evals/STATE.md:188-194` records **two of the four below 1.00 one run earlier**
  — `w-epic-force-when-owner-decided` and `w-epic-assignment-no-force-on-blocking`
  as *"within-budget-only failures … every substantive grader passes"*, on a
  budget the document itself calls miscalibrated.
- Every case is `runs: 1`; one case was measured swinging **±0.8 between
  identical invocations on an unchanged commit**.
- The corpus has grown 64 → 75 cases since and has **not been re-run whole**.
- The corpus predates the epic tip.

Deciding this clause needs a re-run at HEAD with `runs > 1` on those four cases.
Reported UNDECIDED with the reason, not green by elimination. Filed
`SI-23-DF-14`.

**The one adverse signal, carried rather than dropped.**
`CORPUS-2026-09-25.md` records `w-sdc-complexity-ledger-is-advisory` at **0.75**,
judge FAIL×3, on whether a warning is treated as advisory — and
`evals/STATE.md:174` calls that case *"`GOAL-no-new-gates` as an executable test,
so a real failure here is high value"*. It is not one of the four force cases and
may yet be an instrument defect, but it is the only measurement in the corpus
that bears adversely on this goal, and a reading of `GOAL-no-new-gates` that
omits it is not an honest one.

---

## Summary

| clause | baseline | measured | target | verdict |
|---|---|---|---|---|
| zero new refusal paths | `--force`/`SKILL_GATES=off` everywhere | **0 agent-facing** across 576 new + 81 modified code files (954 regex hits, all classified; 15 new `+` lines, none a refusal); **3 new operator-lane sites**, each with an override or operator-only | zero | **MET for the agent-facing substrate; owner's call on the eval lane** |
| every new check has a one-line warning form | — | every new check verified individually; `validate_epic_plan.py --verbose` **independently re-run: warns and exits 0** | all | **MET** |
| the force cases stay green | — | 4 of 4 cases exist; **no per-case score anywhere**; best evidence is n=1 elimination, and STATE.md records 2 of 4 below 1.00 one run earlier | stay green | **UNDECIDED** |

**Moved by:** the drop-gates work predates the epic; SI-14 added the toolchain
refusals (operator lane); SI-28 added the one new agent-facing check and put it
on the pre-existing notify channel.

**Instrument limits stated:** the declared regex is **blind to bare shell
`exit N`**, which is where every genuinely new refusal in this epic lives; the
force-case clause has **no recorded score at any commit**; every corpus score is
`runs: 1`, `--runs 6` does not pin a score (0.89→0.81, 0.97→0.94 on unchanged
cases), and 52/58 at 1.00 is not improvement over 45/58 because eleven instrument
defects were fixed between the runs.
