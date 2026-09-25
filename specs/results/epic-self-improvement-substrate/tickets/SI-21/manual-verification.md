# SI-21 — every `tla-spec-dev` CLI verb, driven by hand, before any eval case existed

Measured 2026-09-25 in the ticket worktree
`/Users/hayde/IdeaProjects/wt-370-eval-ladder-cli`, branched from
`epic/self-improvement-substrate` at `ac5f749184ee906e7a194644cd567a17a542659b`.
Every block below is captured output, in `transcripts/`, not a summary written
afterwards.

This file is committed **before** the eval cases, and that order is the
deliverable: `GOAL-evals-earned` says no eval is written for behaviour nobody
has watched work, and the two commit shas are the check
(`git merge-base --is-ancestor <record> <first case>`). This commit contains no
`case.yaml`.

---

## 0. Which CLI, exactly — and one environment fact that invalidated six runs

The CLI under review is `skills/spec-double-2/scripts/tla_spec_dev.py` **in this
worktree**, invoked by path. No installed `tla-spec-dev` wrapper was used, so
"the code under review" and "the code that ran" are the same sentence here. That
is the trap SI-20 §0 had to work around for `skt`; it does not arise for a
script invoked by path.

**But a different one did, and it is worth more than the verb gamut.**

```
$ python3          -c 'import sys; print(sys.executable, sys.version.split()[0])'
  /opt/homebrew/opt/python@3.14/bin/python3.14 3.14.6
$ timeout 20 python3 -c 'import sys; print(sys.executable, sys.version.split()[0])'
  /Applications/Xcode.app/Contents/Developer/usr/bin/python3 3.9.6
$ type python3
  python3 is an alias for python
```

**`python3` is a zsh alias. `timeout python3` bypasses it and gets macOS's
3.9.6.** Six of my first measurements were wrapped in `timeout` for safety and
therefore ran under a *different interpreter than the one I believed*, silently,
with no error and plausible output. Nothing announced it.

Two consequences, both recorded rather than tidied away:

- Every load-bearing number in §2 was **re-run under an explicit
  `/opt/homebrew/opt/python@3.14/bin/python3.14`** (`step-14`). The numbers
  held: 9/47 and 7/46 both times. So the finding did not change the result — but
  I could not have known that without re-running, and the interpreter is not
  visible in any transcript that does not print it.
- It is the same class as `EA-DF-12/14/15` in `STATE.md` (*a tool could not
  start, the run scored anyway*), reached by a new route: not an empty `HOME`,
  but a shell alias that a wrapper binary does not inherit.

**Anything in this repository that measures by shelling out to `python3` should
print `sys.executable` and `sys.version`, or it is not saying which code ran.**
Filed as `SI-21-DF-01`.

---

## 1. What was driven by hand

All seven verbs, and both targets of each multi-target verb.

| # | verb / target | transcript | outcome |
|---|---|---|---|
| A | `scaffold project --full` | `step-04`, §6 | exit 0, 35 files, un-rooting seam fired and said so |
| B | `scaffold workflow FX-1` | §6 | exit 0, `current` + `desired_program_model` seeded |
| C | `open ticket FX-1` | §3 | exit 0, 21 files, **bare** bindings, no un-rooting needed |
| D | `run spec-unit-tests --ticket <absent>` | `step-01` | **exit 2**, names `.../SI-21/desired` — see §2 |
| E | `run spec-unit-tests --ticket SI-17` | `step-02`, `step-14` | exit 1, **two targets listed, one executed** — §2 |
| F | `run spec-unit-tests --target <ticket view>` | `step-03`, `step-14` | exit 1, 7 failed / 46 passed — §2 |
| G | `run effect-conformance --target specs/current` | `step-06` | **exit 1, `dead_surface`, 15 accusations, nothing ran** — §4 |
| H | `analyze complexity` | `step-05` | exit 0 **with a WARNING** — the advisory contract, §5 |
| I | `analyze corpus` (real package) | `step-12` | exit 0, `corpus gate PASS`, 148 cases |
| J | `analyze corpus` (empty dir) | `step-12` | **exit 1, refuses** — no vacuous verdict, §5 |
| K | `generate cases` | `step-11` | exit 0, 85 states → 148 cases, `--out` trap named, §7 |
| L | `close ticket` (status `next`) | `step-08` | exit 1, refusal names the remedy |
| M | `close ticket` (status `delivered`) | `step-09` | **exit 0 — `delivered` IS terminal here**, §8 |
| N | `close ticket` (second time) | `step-09` | exit 1, append-only history refuses overwrite |
| O | `retire ticket` (not marked retired) | `step-10` | exit 1, clean refusal |
| P | `retire ticket --force` | `step-10` | **uncaught `KeyError: 'retirement'`**, §9 |
| Q | `score_tools.py audit --root` | `step-13` | exit 0, 0 violations — under 3.14; **crashes under 3.9.6**, §10 |

C, L–P ran in a **throwaway fixture** at
`<scratch>/fixture-cli`, a fresh `git init` repo with its own scaffolded
workflow. **No `open ticket`, `close ticket`, `retire ticket` or
`close_tickets.py` was run against this repository's real spec workflow**, per
`planning_rules.model_ownership_rule`. D–J and Q are read-only and ran against
this repository.

---

## 2. `run spec-unit-tests --ticket` — the known-weak verb, and it is not weak the way it is documented

`SIS-KICKOFF-F-04` records it as *"resolves two targets, executes one, lists
both."* All three clauses are observable. **The mechanism is not the one the
phrasing implies, and the difference decides what an eval can assert.**

### What it does

`spec_unit_target_dirs` (`skills/spec-double-2/scripts/tla_spec_dev.py:288`)
returns **two** paths for `--ticket X`: the project's spec dir *and* the
ticket's.

```python
if args.ticket:
    return unique_paths([project_current, ticket_model_dir(specs_dir / "tickets" / args.ticket)])
```

Both are printed, **before anything runs**:

```
spec-unit target: .../specs/current
spec-unit target: .../specs/tickets/SI-17/desired
running pytest:.../specs/current: uv run --with pytest -m pytest .../specs/current/tests -q
9 failed, 47 passed in 19.27s
rc=1
```

One `running` line. The second target is never reached — **not because no
command was built for it**, but because the execution loop is fail-fast
(`tla_spec_dev.py:457`):

```python
for label, command, env in commands:
    print(f"running {label}: ...")
    result = subprocess.run(command, cwd=repo_root, env=env)
    if result.returncode != 0:
        return result.returncode
```

### Why that distinction has teeth

`specs/current` carries **9 failures on this branch, permanently**. So on this
branch `--ticket <anything>` can **never** execute the ticket's own tests: the
project target always runs first and always fails.

And the two targets do not agree:

| invocation | what executed | result |
|---|---|---|
| `--ticket SI-17` | `specs/current` only | **9 failed, 47 passed** |
| `--target specs/tickets/SI-17/desired` | the ticket view only | **7 failed, 46 passed** |

Both re-measured under an explicit interpreter (`step-14`); both stable.

**An agent that runs `--ticket SI-17` and reads `9 failed` believes it has
measured SI-17. It has measured the project baseline.** Nothing in the output
says the second target did not run — there is no "1 of 2 targets not executed"
line, and the only success-path line,
`spec-unit validation passed for {len(target_dirs)} target(s)`, counts *targets
resolved*, not commands executed. On the failure path it is never printed at
all.

The 7 failures from the ticket view are the assignment's stated
"7 spec-unit failures that are not yours" — recorded by name in
`spec-unit-failure-names.txt`. The project's 9 are those 7 plus
`test_the_model_has_the_expected_command_actions` and
`test_every_model_action_is_bound`, which fail in `specs/current` because it
carries 18 actions to SI-17's 15.

### The absent workspace (amendment item 5)

There is no `specs/tickets/SI-21`, deliberately. What the verb does:

```
$ ... run spec-unit-tests --ticket SI-21
ERROR: spec-unit target does not exist: .../specs/tickets/SI-21/desired
rc=2
```

Two things worth having:

- It resolves the ticket target to **`desired`**, while `--ticket`'s own help
  string says *"Run ticket-local **current** spec-unit tests for this ticket."*
  The resolver (`ticket_model_dir`, `:405`) prefers `current/` and falls back to
  `desired/`, and since 2026-09-14 the scaffold emits `desired/` only — so the
  help describes the older two-directory loop. Minor, but it is the difference
  between "the flag is broken" and "the help is stale", and an agent debugging
  the rc=2 will read the help first. Filed as `SI-21-DF-02`.
- The error names **only `missing_targets[0]`** (`:349`), so when both targets
  are missing you are told about one. Not reachable in this repository (the
  project target always exists); recorded because the eval fixture in §11 can
  reach it.

`--target` is the form that answers the question you asked. It is the form the
assignment tells you to use, and §2 is why.

---

## 3. Issue #384 — both remaining parts, measured

The correction comment is right on both counts and I verified each rather than
reading it forward.

### The copy seam does un-root, and it says so

`scaffold workflow` copying `program_model` → `current`:

```
copied .../program_model/case_adapters.toml -> .../current/case_adapters.toml
  (un-rooted 1 view-qualified module reference(s) so this view executes its OWN adapters; see G-10)
copied .../program_model/testgraph_bindings.yml -> .../current/testgraph_bindings.yml
  (un-rooted 1 view-qualified module reference(s) so this view executes its OWN adapters; see G-10)
```

`open ticket FX-1` printed **no** un-rooting line — correctly, because its
source was already bare by then. So the seam is load-bearing exactly once, at
the first copy out of `program_model`.

### What `open ticket` actually hands a ticket view

```
$ grep -v '^\s*#' specs/tickets/FX-1/desired/case_adapters.toml
[adapters.RegisterActor]
adapter = "adapters:RegisterActorInternalAdapter"
...
qualified entries: 0
```

Zero. Plus a **20-line comment block** at the top of the file whose first line
is `# ADAPTER MODULES ARE NAMED BARE, AND THAT IS LOAD-BEARING.`

**So the eval case's claim is false against the current product**, measured, not
inferred. The fixture at
`evals/spec-double-2/w-sdc-ticket-binding-bare-adapter-module/fixture/specs/tickets/T-4/desired/case_adapters.toml`
holds two `specs.program_model.adapters:X` entries; `open ticket` emits none and
teaches against them. §11 says what I did about it.

### (a) The residual hole is real — proven, not argued

Hand-edited **one** binding in the FX-1 ticket view to the qualified form after
seeding, which is exactly the post-seeding edit the seam cannot see. Then asked
whether anything catches it:

```
$ ... run spec-unit-tests --target specs/tickets/FX-1/desired
spec-unit validation passed for 1 target(s)
rc=0
$ <grep the output for un-root|qualified|G-10|baseline>
NOTHING SAID ABOUT IT
```

And the consequence, resolved directly through the import-root pair the loaders
establish, with non-vacuity asserts on both arms (`step-07`):

```
bare  'adapters:X'                     -> <FX>/specs/tickets/FX-1/desired/adapters.py -> TICKETVIEW
qual  'specs.program_model.adapters:X' -> <FX>/specs/program_model/adapters.py        -> BASELINE
```

**A qualified binding hand-edited into a ticket view executes the baseline's
adapters. The view's own `adapters.py` never runs, the run exits 0, and nothing
mentions it.** That is `EA-DF-17` reduced to its true size and confirmed.

---

## 4. `run effect-conformance` — an empty observation set rendered as fifteen accusations

```
$ ... run effect-conformance --target specs/current
effect declarations: 15 port(s) from specs/current/spec_manifest.yaml
effect conformance dead_surface: 0 observed effect(s) over 0 case(s), 15 declared port(s),
    0 gap(s), 15 dead port(s), 0 unobservable target(s)
  - DEAD MODEL SURFACE: port TlaSpecDevCliPort.case_program_process ... declared but never observed
  [... 14 more ...]

Model the effect (declare the port), or change the program so it no longer emits it.
Remove the dead port, or add a case that exercises it. There is no third option.

NOTE: no --cases-dir supplied, so no adapter was executed and nothing was observed.
The dead-surface finding above reflects an empty observation set. Supply --cases-dir
to diff against a real corpus.
rc=1
```

**"An empty result is not a passing result" — in its dual form.** Nothing ran,
and the verdict, the fifteen findings, the imperative ("There is no third
option") and `rc=1` all read as a substantive failure. The honest `NOTE` is
real mitigation and it is genuine credit to whoever wrote it — but it arrives
*after* the verdict, in prose, and it is the only thing distinguishing "your
ports are dead" from "I measured nothing".

Compare `analyze corpus` on an empty directory in §5, which refuses. **Two verbs
in the same CLI, opposite answers to the same question.** That contrast is the
sharpest thing in this record.

Worse for this repository specifically: **`specs/generated/` does not exist
here**, so there is no `--cases-dir` to supply and the verb cannot produce a
non-vacuous answer on this checkout at all. Filed as `SI-21-DF-03`.

---

## 5. `analyze` — the advisory contract, done right, twice

`analyze complexity` on `specs/current/TlaSpecDevCli.tla`: a full descriptor —
dimension table, `bound = 277,830 [INCOMPLETE: product over 6 of 9 declared
variables]`, an R/W matrix over 19 actions — then:

```
WARNING: component C1 is touched by 18 actions (...), exceeding max_component_actions 8

`analyze complexity` exits 0 whenever it can analyze the model -- a complex model
is a finding, not a failure. It exits nonzero ONLY when the model cannot be
analyzed at all ...; that is 'I could not measure this', which is distinct from
'this is complex'.
rc=0
```

This is `GOAL-no-new-gates` as shipped behaviour, and the verb **states its own
exit-code contract in its output**. Three further things it does right, each of
which the rest of this record shows something else getting wrong: it labels
every figure `[MEASURED]`; it names the bound `INCOMPLETE` and says which three
variables were excluded and why; and it refuses to convert that bound into a
percentage of the cap.

`analyze corpus` on the package `generate cases` had just written: `corpus gate
PASS: 148 internal case(s)`, a stratum distribution, `Strata that are STARVED:
(none)`, and `No case was dropped, filtered, sampled, or truncated.`

On an **empty directory**:

```
ERROR: no generated cases or trace JSON files in /private/tmp/emptycorpus-si21
rc=1
```

It refuses. It does not report `PASS: 0 cases`.

---

## 6. `scaffold` — both targets

`scaffold project --full FixtureProg` then `scaffold workflow FX-1`: 35 files,
exit 0. The budgets block is written to the manifest with every default
annotated, followed by a paragraph stating that **budgets are advisory
thresholds, not gates** and that `analyze complexity` "never blocks promotion or
changes its exit code" — the same contract §5 then demonstrates. The scaffold
teaches it and the analyzer honours it; that pairing is worth recording because
this epic has repeatedly found documentation and behaviour disagreeing.

`next: tla-spec-dev --spec-root specs open ticket FX-1` — each verb names the
next one. `open ticket` likewise prints six numbered steps ending at `close
ticket`, including step 6 on giving every finding a
`skill_change: applied|proposed|declined`.

---

## 7. `generate cases` — and a trap it names on itself

85 distinct states → 148 cases, exit 0, with per-action coverage, a parameter
recovery audit (`148/148 cases carry arguments`), and the corpus gate inline.

The one thing worth encoding:

```
note: --out specs/generated/spec-unit resolved to <FX>/specs/current/specs/generated/spec-unit
  -- a relative --out is resolved against the SPEC DIRECTORY (<FX>/specs/current), not the
  current directory (<FX>). Pass an absolute path to control it.
```

I passed a path relative to the repo root and got one relative to the spec
directory — the nested `specs/current/specs/generated/` above. The CLI **told me
so, unprompted, naming both interpretations and the remedy**. There is already a
case for this (`w-sdc-out-path-is-absolute`), which is why it is recorded here
and not encoded again.

---

## 8. `close ticket` — and `delivered` IS terminal, here

Three arms, one fixture:

| plan `tickets[0].status` | result |
|---|---|
| `next` | `ERROR: ticket FX-1 is not closed in ticket_plan.yaml: status=next (mark it done/delivered, or pass --force)` rc=1 |
| `delivered` | **rc=0** — close proceeds, promotes, writes the ledger and the feedback template |
| `done` (second run) | `ERROR: refusing to overwrite existing history entry: .../ticket-000-FX-1` rc=1 |

The memory note that *"the epic skill and the spec compiler disagree on what
'done' is spelled"* — **the disagreement is not in this CLI.** `close ticket`
accepts `delivered` and `done` equally, and its refusal message names both. Any
remaining disagreement is on the epic-skill side. Recorded because the opposite
is easy to assume from the memory line alone, and a case already exists
(`w-sdc-close-ticket-delivered-status`) whose subject this confirms.

The successful close is loud and does four separable things: a complexity-ledger
entry, promotion into `specs/current`, the ledger delta, and a skill-feedback
template. Note its first line:

```
WARNING: complexity ledger input rejected (2 issue(s)); recorded as rejected, the close proceeds.
```

Advisory, recorded, proceeds — and it **says** it proceeds, which is the exact
wording the ledger-warning commit on `main` (`d9327fe7`) went in to fix. It
holds here.

The second-run refusal is correct and valuable: history is append-only and the
close will not overwrite a receipt.

---

## 9. `retire ticket --force` crashes

```
$ ... retire ticket FX-1            # plan does not mark it retired
ERROR: cannot retire ticket:
- ticket FX-1 is not marked retired: status=done
rc=1                                                    <- clean, correct

$ ... retire ticket FX-1 --force
WARNING (forced): ticket FX-1 is not marked retired: status=done
WARNING (forced): ticket FX-1 already has a successful close receipt: ...
Traceback (most recent call last):
  ...
  File ".../spec_evolution.py", line 586, in _retirement_manifest_contract
    "retirement": ticket["retirement"],
KeyError: 'retirement'
rc=1
```

`--force`'s own help says it *"Warn instead of refusing on
retirement-declaration and receipt gates."* It does exactly that — and then
`_retirement_manifest_contract` unconditionally indexes `ticket["retirement"]`,
**the key the gate it just bypassed existed to guarantee**. So `--force` is a
guaranteed crash on precisely the input it was built for.

Both arms exit 1, so this does not change a verdict — but a raw traceback is not
a refusal, and the operator cannot tell "you may not do this" from "I broke".
Outside my conflict keys (`skills/spec-double-2/scripts/**`): **deferred, not
fixed.** `SI-21-DF-04`.

---

## 10. The scorecard, and `score_tools.py`

`score_tools.py` is **not** at `scripts/score_tools.py` as the issue's
References section says. It is at
`examples/validation/scorecards/score_tools.py`, and its own module docstring
explains why: `scripts/**` is in-model per the plan's `representation_scope`, so
putting the harness there would change the model's surface. The issue's citation
is stale; the file's reasoning is sound.

`audit` takes `--root`, not a positional, as the issue warns. Under 3.14:

```
$ python3 examples/validation/scorecards/score_tools.py audit --root specs/results/scorecards --quiet-ok
## R-I2 packet: what the judge received is recorded, and absent is not withheld.
## R-I3 contamination: a blindness claim is the dispatch's, not the author's.
0 violation(s)
rc=0
```

**Under macOS's stock `/usr/bin/python3` (3.9.6) it does not start at all:**

```
Traceback (most recent call last):
  File ".../score_tools.py", line 110, in <module>
    import tomllib
ModuleNotFoundError: No module named 'tomllib'
```

`tomllib` is 3.11+. The script declares no interpreter floor, has no `# /// script`
header, and fails with a bare traceback rather than "needs Python 3.11+". This
is the `STATE.md` class again — *the tool could not start* — and it is how I
found §0. `SI-21-DF-05`.

### The gap itself

**There is still no eval case covering the scorecard.** Counted, not assumed:

```
$ grep -rln "scorecard" evals/
evals/git-issue/w-misc-issue-names-rubric-not-copies/fixture/rubric.md
```

One hit, a fixture file inside a case about issue-writing, not about the
scorecard instrument. **0 of 64 cases** have the scorecard as their subject. The
gap filed at the wave-4 gate is **still open**, and §11 says what this ticket
did about it.

---

## 11. What this record is allowed to be used for

- The cases in the next commit encode §2 (what `--ticket` executes versus what
  it lists) and §4/§5 (a verb that gives a verdict on nothing, beside one that
  refuses to). Nothing else here is encoded.
- §0, §9 and §10 were observed and are **findings**, not cases. Turning each
  into a case on the day it was found is the volume this ticket exists to avoid.
- No `claude plugin eval` score is in this record. Nothing here is evidence
  about the eval suite's numbers; the scores are measured separately, after
  this commit, and reported in `local-signal.md`.
- The `--force` crash in §9 and the `dead_surface` verdict in §4 are both
  outside `evals/**`. They are deferred, not fixed.

## 12. Unexercised, with the reason

- **`open ticket`, `close ticket`, `retire ticket` against THIS repository's
  workflow** — forbidden by `planning_rules.model_ownership_rule`. Exercised in
  a throwaway fixture only, which the issue explicitly permits, and §1 says
  which is which.
- **`close_tickets.py` and `--accept-new`** — forbidden outright. Not run in any
  form, including the fixture.
- **`run spec-unit-tests` without `--validate-only` across both targets to
  completion** — unreachable on this branch: the fail-fast loop returns on the
  project target's 9 failures. That unreachability *is* the §2 observation.
- **`analyze complexity --out`** — writes a report; the `--out` path semantics
  are already covered by `w-sdc-out-path-is-absolute` and writing one adds
  nothing.
- **`generate cases` against this repository's model** — it would write into
  `specs/`, which is the epic agent's surface. Run in the fixture only.
