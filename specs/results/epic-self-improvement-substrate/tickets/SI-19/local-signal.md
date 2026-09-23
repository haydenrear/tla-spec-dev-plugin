# SI-19 — local signals, against `expected_effect`

A local signal is a signal, not a gate. Each is reported against what the
assignment said this change aims at, including where nothing moved.

## `GOAL-evals-earned` (contribution: direct)

- **expected_effect**: *the first stage with a manual record preceding its case.*
- **local_signal**: *the manual-verification record is committed and predates the
  case.*

**Observed: yes, and it is checkable with `git log` rather than on my word.**

```
$ git log --format='%H %ct %s' f4b42169..HEAD --reverse
8e362bbbeda7ebf8ed9b53c516b3315bc1b70594  SI-19 step 1 of 2: the by-hand record, written before any eval exists
eefe3aa894d2f2d924298a165c636c43b671ab53  SI-19 step 2 of 2: one small eval, encoding what the previous commit watched
```

The record and its twelve transcripts are introduced by `8e362bbb`. The first
file under `evals/test-graph/w-tg-run-a-graph-not-bare-gradle/` is introduced by
`eefe3aa8`, which is a child of it. No eval case file appears in `8e362bbb`, and
the record is not modified by `eefe3aa8` — the only `specs/results/` paths that
commit adds are the probe and its output, which are about the case, not the
manual record.

**The honest limit of this signal.** It says the ORDER held for one stage. It
does not say the eval is a good eval, and it does not say the record changed
what the case grades — though in fact it did: the case's second grader
(`knows-what-the-runner-does-first`) exists because the by-hand control made
the *reason* visible, and a case written from the SKILL.md table alone would
have graded only the command. The metric this contributes to is
*eval stages whose manual-verification record precedes their first eval case,
over eval stages shipped* — this is **1 stage of 1 shipped here**, and SI-23
decides the goal over the epic, not this ticket.

## `GOAL-evals-one-command` (contribution: enabling)

- **expected_effect**: *the new case runs in the one command.*
- **local_signal**: *it appears in the suite run.*

**Observed: it appears in what the one command would run. It has NOT been
scored, and that distinction is the whole of this section.**

`evals/run.sh` builds the plugin view with `git archive <commit> | tar` and
hands that directory to `claude plugin eval`, whose discovery is
`<eval dir>/**/case.yaml`. The view build was replicated at this branch's tip
without invoking the CLI (transcript `transcripts/step-J-view-discovery.txt`):

```
view commit                 eefe3aa894d2f2d924298a165c636c43b671ab53
entries in the view         8686        (the CLI refuses at 20000)
case.yaml found in the view 62          (61 before this ticket)
the new case                evals/test-graph/w-tg-run-a-graph-not-bare-gradle/case.yaml   grep rc=0
non-vacuity control         the same grep for a name that is not there   grep rc=1
all five of its files       present in the view
```

**No `claude plugin eval` run is in this branch, and no score is claimed.**
`plugin eval` has no load-only or dry-run flag, so the cheapest way to exercise
the case is a billed run, and nobody asked for one. Calling the discovery check
above "the case runs" would be exactly the defect this epic keeps finding, so it
is not called that. What is established is that the case is DISCOVERED and that
the suite is still under the entry ceiling with it.

## Repository suite, by NAME

```
uv run --python 3.12 --with pytest --with pyyaml --with jinja2 --with hypothesis python -m pytest tests -q
```

| | failed | passed | skipped |
|---|---|---|---|
| baseline, untouched worktree at `f4b42169` | 11 | 1842 | 6 |
| this branch at `eefe3aa8` | 11 | 1844 | 6 |

`diff` of the two sorted FAILED lists: **identical set**. Ten are the epic's
known list; the eleventh is `SI-19-DF-04`, red before this ticket changed a byte
(`manual-verification.md` §6).

The **+2 passed** were not left as a mystery. Collected-id sets were diffed
between `f4b42169` (1859) and `eefe3aa8` (1861), and the two new tests are both
parametrisations over the new inbox file:

```
tests/test_parse_simple_yaml_differential.py::test_parse_simple_yaml_agrees_with_pyyaml[specs/results/deferred/SI-19.yaml]
tests/test_spec_yaml_valid.py::test_spec_yaml_parses[SI-19.yaml]
```

Both pass. Nothing else in the suite changed.

## Spec units

The assignment's `validation.spec_unit` is
`... run spec-unit-tests --ticket SI-19`. **That command cannot run**, and the
reason is structural rather than a fault:

```
ERROR: spec-unit target does not exist: .../specs/tickets/SI-19/desired
```

The epic agent owns the model for this epic and scaffolds a ticket's `desired`
before dispatch; SI-19's plan row carries `desired_actions: []` and an empty
`current_increment`, and the issue says the spec workflow is NOT REQUIRED here.
No workspace was scaffolded, so `--ticket` has nothing to point at. This is the
weakness the issue names as `SIS-KICKOFF-F-04`, reproduced.

What was run instead, as the issue instructs — `--target`, and saying which:

```
python3 skills/spec-double-2/scripts/tla_spec_dev.py --spec-root specs \
    run spec-unit-tests --target specs/desired_program_model --validate-only
-> 7 failed, 49 passed in 21.47s
```

Seven, which is the count the issue states as the repository's known spec-unit
baseline. None is mine on the evidence of the diff: this branch changes no file
under `specs/desired_program_model/`, `specs/current/` or `specs/program_model/`.
Names in `spec-unit-failure-names.txt`. The tree was clean before and after.

## Graphs

`cliWorkflow` (the assignment's `validation.graphs`), `specWorkflow` (its
`spec_graph`) and `effectProviderExamples` all `passed`, each read from its own
`summary.json`. See `manual-verification.md` §4.

## Worktree home close-out — NOT RUN, and why

`skill-manager home close-out --home <worktree>/.skill-manager --into
<main-working-tree>/.skill-manager` was attempted twice and **refused by this
agent harness's permission classifier** ("Modify Shared Resources"), including
with `--json`. The command's own `--help` says *"Writes nothing; safe to run
repeatedly"*, so the refusal is about the shape of the arguments rather than
about what the command does. It is recorded as not-run rather than reported as
a verdict nobody obtained.

What CAN be established read-only is the fact the close-out would be checking —
whether this worktree's home holds work that removing it would destroy:

```
$ find .skill-manager -newermt "2026-09-23 16:00" -type f | wc -l   ->  39   (control: the probe can match)
$ find .skill-manager -newermt "2026-09-23 16:25" -type f | wc -l   ->   0
```

The home was provisioned at 16:04 and the worktree handed over at 16:24. Not one
file in it was written after that, so no unit was edited in this home and the
close-out has nothing to carry. **The epic agent should still run the command**:
this is evidence about mtimes, not the tool's verdict.
