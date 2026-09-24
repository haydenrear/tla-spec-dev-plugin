# SI-20 — local signals, against `expected_effect`

A local signal is a signal, not a gate. Each is reported against what the
assignment said this change aims at, including where nothing moved.

## `GOAL-evals-earned` (contribution: direct)

- **expected_effect**: *second stage with a manual record preceding its cases.*
- **local_signal**: *the record names each verb and what it did.*

**Observed: yes, and it is checkable with `git log` rather than on my word.**

```
$ git log --format='%H %s' 1cb00be7..HEAD --reverse
70549f901d0540ec060e6155c477e4979a2f1041  SI-20: every skt verb driven by hand, before a single eval case exists
7daa8e18dc8f1e0483b1107fbb609bf63087708f  SI-20 step 2 of 2: two small evals, encoding what the previous commit watched
f602cb36…                                  sktSurface: assert where a worktree goes, in BOTH classifications…

$ git merge-base --is-ancestor 70549f90 7daa8e18   ; echo $?
0
$ git show --name-only --pretty=format: 70549f90 | grep -c '^evals/'
0
$ git show --name-only --pretty=format: 7daa8e18 | grep -c 'manual-verification.md'
0
```

The record and its ten transcripts are introduced by `70549f90`. The first file
under either `evals/skt/w-skt-*` case is introduced by `7daa8e18`, a child of
it. **No eval case file appears in the record commit, and the cases commit does
not modify the record.**

**The record names each verb.** Fifteen `skt` invocations across nine verbs
(`--version`, `status`, `check`, `sync`, `build`, `publish --check`,
`ticket list`, `ticket sweep`, `ticket new|info|close`), plus
`skill-manager home close-out`, each with its exit code and its output, in
`transcripts/step-02-verb-gamut.txt` and §3–§7 of the record. Five verbs are
recorded as **unexercised with the reason**, which is the other half of "names
each verb".

**The honest limit of this signal.** It says the ORDER held for a second stage.
It does not say the two cases are good cases — no `claude plugin eval` run is in
this branch. It also does not say the record *changed* what the cases grade,
though in fact it did twice: the first case exists only because the by-hand
two-arm falsification showed the reds were about the fixture and not about
`skt`, and the second exists only because I was caught by the wrapper myself and
had to build a home to get the bytes under review under test. The metric this
contributes to is *eval stages whose manual-verification record precedes their
first eval case, over eval stages shipped* — **2 of 2 shipped so far across
SI-19 and SI-20**, and SI-23 decides the goal over the integrated epic, not this
ticket.

## `GOAL-one-plugin` (contribution: guard)

- **expected_effect**: *skt works from inside the bundle.*
- **local_signal**: *every verb exercised against the contained copy.*

**Observed: yes, with one correction that is itself the guard's finding.**

Every invocation resolved `plugins/tla-spec-dev/skills/skt/src/skt/cli.py`
through a generated wrapper; no standalone `skt` unit was installed in, or
reached from, any home used here. `skt status --json` reports
`"plugins": ["tla-spec-dev"]` and no `skt` unit record.

The correction: **contained is not the same as under review.** The worktree's
own home carries a clone of the plugin pinned at `1efa0b4b`, and its
`skt/src/skt/status.py` differs from the source beside it, so
`<worktree>/.skill-manager/bin/cli/skt` is the contained copy *of a different
commit*. The gamut was therefore re-driven against a home built by hand from
this worktree with `install-skt.sh`. That is the wrapper contract working, not a
defect — and it is a trap that cost this ticket a false start, which is why it
became the second eval case.

**No measurable movement on the goal itself**, and that is expected: this
ticket is a guard, not a change. What it adds is evidence that the front door
resolves with skt contained across nine verbs and two interpreter pins, where
before it had been exercised for `ticket new` and `status` only.

## Regression, by NAME

- Repository suite: **10 failures, identical by name to SI-19's ten** (SI-19's
  eleventh, `test_eval_toolchain_pin.py::test_the_view_excludes_the_materialised_toolchain`,
  is repaired and green here). No new name, no disappeared name.
  `baseline-failure-names.txt` / `final-failure-names.txt`.
- Spec-unit: **7 failures, identical by name to SI-19's seven**, run with
  `--target` on both `specs/current` and `specs/desired_program_model` because
  `--ticket` is known-weak (`SIS-KICKOFF-F-04`). Same seven test ids under both
  targets.
- Graphs, read from each run's own `summary.json`:
  `specWorkflow` 9/9, `cliWorkflow` 2/2, `effectProviderExamples` 1/1,
  `sktSurface` **5/5 with 51 assertions and 0 red** (was 4/5 with 13 red).
  `sktHooks` not run here.
