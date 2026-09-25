# SI-21 — local signal

Measured 2026-09-25 in `/Users/hayde/IdeaProjects/wt-370-eval-ladder-cli`,
branched from `epic/self-improvement-substrate` at `ac5f7491`.
**A local signal is a signal, not a gate.** SI-23 decides both goals.

---

## `GOAL-evals-earned` — expected effect: "third stage, manual record first"

`local_signal`: *the record covers each CLI verb.*

**Met, and checkable in git rather than asserted.**

| | |
|---|---|
| manual record commit | **`bec1934b`** |
| first eval-case commit | **`c96de147`** |
| `git merge-base --is-ancestor bec1934b c96de147` | **rc=0** |
| `case.yaml` files in the record commit | **0** |

That is the same check the two shipped rungs pass (`8e362bbb→eefe3aa8`,
`70549f90→7daa8e18`), performed the same way.

**Verb coverage.** All seven, and both targets of each multi-target verb —
`scaffold` (project, workflow), `open` (ticket), `run` (spec-unit-tests,
effect-conformance), `analyze` (complexity, corpus), `generate` (cases),
`retire` (ticket), `close` (ticket). Seventeen captured transcripts in
`transcripts/`. The table in `manual-verification.md` §1 maps each to its
transcript and outcome, and §12 names what was deliberately NOT exercised and
why.

Three cases were written, and each encodes something in the record:

| case | record | measured |
|---|---|---|
| `w-sdc-spec-unit-ticket-runs-only-the-first-target` | §2 | **1.00**, 6 runs |
| `w-sdc-effect-conformance-observed-nothing` | §4, §5 | **0.89**, 6 runs |
| `w-sdc-scorecard-tool-needs-a-newer-python` | §0, §10 | **1.00**, 6 runs |

Nothing else in the record became a case. Five observations became **findings**
instead (`specs/results/deferred/SI-21.yaml`), which is the rung-2 convention:
turning every finding into a case on the day it is found is the volume this
ladder exists to avoid.

---

## `GOAL-evals-one-command` — expected effect: "at least one case per nested skill becomes reachable"

`local_signal`: *per-skill coverage counted.*

Counted, not estimated, with a non-vacuity assert on the enumeration:

| nested skill | cases |
|---|---|
| `skt` | 16 |
| **`spec-double-2`** | **15** (12 + 3 from this ticket) |
| `git-issue-workflow` | 9 |
| `skill-manager` | 9 |
| `git-epic-workflow` | 7 |
| `git-issue` | 3 |
| `plugin-repository` | 2 |
| `test-graph` | 2 |
| `discovery` | 1 |
| `git-integration-repo` | **0** |
| `unit-authoring` | **0** |

Plus `harness` and `unnested`, which are not skills. **Total 67 cases**, up from
64.

**Movement against the expected effect is honest but small: this stage added no
newly-covered skill.** All three of its cases are `spec-double-2`, which already
had twelve. **Nine of eleven nested skills have at least one case; two still
have none**, and naming them is more useful than the total:
`git-integration-repo` and `unit-authoring`. Neither is this rung's subject.
SI-22 covers the skill-manager CLI; nothing in the plan currently covers those
two, and SI-23 should treat that as the remaining gap for this goal rather than
reading 67 as coverage.

One command still runs all of it: `evals/run.sh`. No units-override file, no
second harness, no shim plugin.

---

## The scorecard gap — covered in part, and the rest restated as OPEN

The plan's acceptance was explicit: **cover it, or restate it as still open.**
Doing both, with the boundary drawn precisely, because a partial answer reported
as a whole one is the error this epic keeps finding.

**Before this ticket, counted:**

```
$ grep -rln "scorecard" evals/
evals/git-issue/w-misc-issue-names-rubric-not-copies/fixture/rubric.md
```

One hit, a fixture file inside a case about writing issues. **0 of 64 cases had
the scorecard as their subject.**

**What is now covered.** `w-sdc-scorecard-tool-needs-a-newer-python` — 1.00 over
6 runs — is the first case in the suite whose subject is the scorecard surface.
It grades whether an agent reads `score_tools.py`'s startup failure as an
interpreter floor rather than a missing package.

**What is still open, and it is the larger half.** That case is about the
tool **starting**, not about the instrument **judging**. Nothing in the suite
exercises what the wave-4 gate actually filed: the scorecard's own rules —
`contested` (rule 5, a spread greater than 1 across two blind judges),
the tier split, `audit`'s R-I2/R-I3 checks, or whether an agent reads
`0 violation(s)` as "the cards are sound" rather than "no rule fired".

**I did not write those cases, and the reason is `GOAL-evals-earned` itself.** I
drove `score_tools.py --help`, `check --help`, `audit --help` and
`audit --root specs/results/scorecards` by hand (record §10), and that is the
extent of what I watched work. I did not exercise `contested`, `index`,
`history` or `seal`, and writing cases for them would be writing evals for
behaviour nobody has watched — the exact thing this rung exists to stop.
`tests/test_score_tools.py` is a 13-minute lock on the card files, which makes
casual exploration of that surface expensive, and it is not in my conflict keys.

**So: the gap is narrowed, not closed, and it stays open.** It should be
assigned deliberately rather than absorbed into a rung that was about the CLI.

---

## Measurement notes, so the numbers above are read correctly

- **Every score is 6 runs, not 1.** `runs: 1` is the corpus default and the
  issue is right that it cannot support a claim. The binding case was
  reproduced at 6 runs specifically because its `runs: 1` could not.
- **`w-sdc-effect-conformance-observed-nothing` is 0.89, 50% pass, and the cause
  is known.** The two heavy graders — `says-nothing-was-observed` (weight 4) and
  `refuses-the-deletion` (weight 3) — passed **6 of 6**. The miss is
  `names-the-cases-dir-remedy` (weight 2), which passed 3 of 6, giving 1.00 and
  0.78 runs and a 0.89 mean.
  **That grader asks for something the prompt does not request.** The prompt
  asks "tell me what this run actually measured"; the grader wants the
  `--cases-dir` remedy named as well. This is the README's
  *over-specifies the means* class, in a grader I wrote.
  **I have deliberately not tuned it after seeing the score.** Lowering a
  weight or loosening a pattern once the number is known is how four changes
  were made to one case reading noise as signal earlier in this epic. The
  measured value is 0.89; the defect is documented in the case file and left for
  SI-23 to decide.
- **`w-sdc-ticket-binding-bare-adapter-module` reproduces at 0.17 on 6 of 6
  runs** — identical every time, with the same two graders red
  (`bare-module` weight 3, `no-qualified-module` weight 2) and `binds-refund`
  green. So the 0.17 is **stable, not a single-sample artefact**, and the
  question the issue posed about it is a question about what the case measures,
  not about variance. Record §3 and the case's restated description answer it.
- **The first measured run of these cases was void and is kept rather than
  hidden.** Every grader threw (`Invalid regular expression`) because I wrote
  Python inline flags into a JavaScript engine, and the case scored 0.00 and was
  billed. `evals/lib/check_graders.py` now catches that before the money; it
  warns and exits 0.
- **The eval lane was proved before and after.** `setup-eval-home.sh --smoke`
  passed at 1.00, and `w-harness-smoke` scored 1.00 again after my `run.sh`
  changes, which is the README's requirement for touching `run.sh`.
