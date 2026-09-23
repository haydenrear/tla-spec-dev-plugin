# SI-19 — the by-hand record, written before any eval case existed

Measured 2026-09-23 in the ticket worktree
`/Users/hayde/IdeaProjects/wt-368-eval-ladder-graph-scaffold`, branched from
`epic/self-improvement-substrate` at `f4b42169da046ed1e44ff6136f81e4f2c4c5649f`
on `haydenrear/tla-spec-dev-plugin`. Every block below is captured output, in
`transcripts/`, not a summary written afterwards. Where a graph ran, the verdict
is read from that run's own `summary.json`; **no graph here is called green
because a command returned 0.**

This file is committed **before** the eval case. That order is the deliverable:
`GOAL-evals-earned` says no eval is written for behaviour nobody has watched
work, and the two commit shas are the check.

---

## 0. What was driven by hand

| # | command | transcript | outcome |
|---|---|---|---|
| A | `cd test_graph && ./gradlew cliWorkflow` (the CONTROL) | `transcripts/step-A-bare-gradlew-control.txt` | **BUILD FAILED in 2s**, exit 1 |
| B | `python3 skills/test-graph/scripts/prepare-bindings.py` | `transcripts/step-B-prepare-bindings.txt` | exit 0, three symlinks materialised, tree still clean |
| C | `python3 skills/test-graph/scripts/discover.py` | `transcripts/step-C-discover-list.txt` | exit 0, **five** graphs listed |
| D | `python3 skills/test-graph/scripts/discover.py cliWorkflow` | `transcripts/step-D-discover-cliworkflow.txt` | exit 0, plan + DAG rendered, tree still clean |
| E | `python3 skills/test-graph/scripts/run.py cliWorkflow` | `transcripts/step-E-run-cliworkflow.txt`, verdict in `step-E2-cliworkflow-verdict.txt` | `summary.json` `"status":"passed"`, 2/2 nodes |
| F | `python3 skills/test-graph/scripts/scaffold.py <fresh dir>` | `transcripts/step-F-scaffold.txt` | exit 0, a new `test_graph/` project |
| G | `discover.py --test-graph-root <scaffolded>` | `transcripts/step-G-scaffold-discover.txt` | exit 0, five example graphs listed |
| H | `run.py smoke --test-graph-root <scaffolded>` | `transcripts/step-H-scaffold-run-smoke.txt`, verdict in `step-H2-smoke-verdict.txt` | **`summary.json` `"status":"errored"`** — see §5 |
| I | `run.py specWorkflow effectProviderExamples` (sweep) | `transcripts/step-I-run-sweep.txt`, verdicts in `step-I2-sweep-verdicts.txt` | both `"status":"passed"`; sweep ledger 2/2 |

---

## 1. The control, and why it is a control

The worktree was fresh: `test_graph/sdk`, `test_graph/build-logic` and
`test_graph/standard-nodes` were all **ABSENT** before anything ran. Bare Gradle
was driven first, deliberately, because any of the other commands would have
materialised the bindings and destroyed the control.

```
$ ./gradlew cliWorkflow
* What went wrong:
Included build '/Users/hayde/IdeaProjects/wt-368-eval-ladder-graph-scaffold/test_graph/build-logic' does not exist.
BUILD FAILED in 2s
exit=1
```

That reproduces `SI-13-DF-01` exactly — the same message, the same 2s, in a
worktree at a different base four days later. It is not folklore.

The skill runner does not fail, and the reason is one call:
`run_gradle()` calls `prepare_provider_bindings_or_warn(root)` before it invokes
Gradle — `skills/test-graph/scripts/_common.py:680
(prepare_provider_bindings_or_warn)`, defined at
`skills/test-graph/scripts/_common.py:594 (prepare_provider_bindings_or_warn)`.

**This pair is what the eval case in the next commit encodes**: the front door
for running a registered graph in a fresh checkout is
`skills/test-graph/scripts/run.py` (or the repository's own
`test_graph/run-graphs.py`), never `cd test_graph && ./gradlew`, and the reason
is the managed provider bindings rather than anything about Gradle.

## 2. `prepare-bindings.py` — the one-command remedy, observed

No required arguments, as the issue says. It printed the resolved manifest and
exited 0:

```
"provider": { "kind": "workspace-relative",
              "root": ".../wt-368-eval-ladder-graph-scaffold/skills/test-graph" }
```

and left three **relative** symlinks:

```
test_graph/build-logic -> ../skills/test-graph/project_sdk_sources/build-logic
test_graph/sdk         -> ../skills/test-graph/project_sdk_sources/sdk
test_graph/standard-nodes -> ../skills/test-graph/project_sdk_sources/standard-nodes
```

`git status --short` after it named **only** the untracked evidence directory
this record lives in. The materialised links do not dirty the tree — they are
ignored by the `TEST-GRAPH-MANAGED-BINDINGS` block the scaffold writes. That is
the property commit `175f5c7c` bought and it still holds.

## 3. `discover.py` — five graphs, not three

```
graph: specWorkflow            (9 nodes)
graph: cliWorkflow             (2 nodes)
graph: effectProviderExamples  (1 node)
graph: sktSurface              (5 nodes)
graph: sktHooks                (3 nodes)
```

**SI-13's classification table lists three.** `sktSurface` and `sktHooks` were
registered after it (SI-16 nested `skt` here), so the classification at
`specs/results/epic-self-improvement-substrate/tickets/SI-13/classification.md`
is now incomplete for this repository — not wrong about the three it names, but
no longer the whole registry. Recorded, not fixed: SI-13's table is another
ticket's evidence. `SI-19-DF-03`.

Neither new graph was run here. They are the units SI-16 nested and running them
is not this ticket's slice; they are **UNDECIDED here**, which is different from
green.

`discover.py cliWorkflow` additionally wrote `test_graph/docs/cliWorkflow.dot`
and `.png`. Both are **tracked** files, and `git status` stayed clean after the
write, so the render is byte-reproducible at this commit. Worth knowing before
someone reads a dirty tree as a defect: a discovery command does write into the
working tree.

## 4. The three declared graphs, read from their own reports

| graph | run dir | `summary.json` `status` | nodes |
|---|---|---|---|
| `cliWorkflow` | `build/validation-reports/20260923-202608` | `passed` | 2/2 passed |
| `specWorkflow` | `build/validation-reports/20260923-202809` | `passed` | 9/9 passed |
| `effectProviderExamples` | `build/validation-reports/20260923-203027` | `passed` | 1/1 passed |

The two-graph invocation also exercised the sweep ledger, and its record
(`build/validation-sweeps/20260923-202758/sweep.json`) agrees with the two
`summary.json` files: `graphs_selected=2 graphs_executed=2 graphs_passed=2
graphs_failed=0 graphs_not_run=0`.

### The unglamorous part

Every one of these runs emitted **14+ OpenTelemetry exporter stack traces** —
`java.net.ConnectException` against `http://localhost:4318/` — because no OTLP
collector is listening. The traces are interleaved with the node output and they
look exactly like a failure. They are not: all three graphs are `passed`. A
reader skimming `run.py` output for red text will mis-read a green run, and an
agent doing the same will report one. That is the reading hazard this surface
carries today.

## 5. The finding: a fresh scaffold's own next step is red

`scaffold.py` succeeded into an empty directory and printed, at
`skills/test-graph/scripts/scaffold.py:154 (next steps)`:

```
next steps:
  cd <repo-root>
  .../skills/test-graph/scripts/discover.py
  .../skills/test-graph/scripts/discover.py smoke
  .../skills/test-graph/scripts/run.py smoke
  .../skills/test-graph/scripts/run.py --all
```

Following that list verbatim:

- `discover.py` → exit 0, five example graphs.
- `run.py smoke` → **`summary.json` `"status":"errored"`**, `BUILD FAILED`,
  exit 1. The first node `app.running` errored with `java.net.ConnectException`;
  the remaining **five nodes were skipped**.

The cause is a precondition, not a bug in the scaffold's wiring:
`skills/test-graph/project_sdk_sources/sources/AppRunning.java:46
(http://localhost:8080)` defaults `baseUrl` to `http://localhost:8080` and HEADs
it. Nothing is listening in a fresh scaffold, and the scaffolded `README.md`
says nothing about it (grepped for `app.running`, `8080`, `start the app`,
`prereq` — no match).

So a first-time user of `test-graph` runs the command the tool just told them to
run and gets a red whose reason is "you have no demo app", reported in a shape
indistinguishable from "the scaffold is broken". This is the epic's own recurring
defect one layer out: **an environment that could not run the task and a tool
that could not do the task produce the same output.** Filed as `SI-19-DF-01`.

Also observed, and smaller: the scaffolded project's symlinks are **absolute**
(`/Users/hayde/IdeaProjects/...`) when the target is outside the skill's tree,
where an in-tree `prepare-bindings.py` produced relative ones. They are
gitignored, so nothing absolute is committed — the class of defect `175f5c7c`
removed does not return — but a copied scaffold directory will carry dead links.
`SI-19-DF-02`.

## 6. The repository suite, compared by NAME

Command, exactly as the epic requires (a bare `pytest` from the repository root
returns `401 errors` and `0 FAILED`, which is not a pass):

```
uv run --python 3.12 --with pytest --with pyyaml --with jinja2 --with hypothesis python -m pytest tests -q
```

Result on the **untouched** worktree at `f4b42169`: `11 failed, 1842 passed,
6 skipped in 1082.04s`. Full output in `baseline-repository-suite.txt`, names in
`baseline-failure-names.txt`.

Ten of the eleven are the epic's known list. **The eleventh is new and is not
mine** — it was already red before this ticket changed a byte:

```
tests/test_eval_toolchain_pin.py::test_the_view_excludes_the_materialised_toolchain
```

It asserts `git check-ignore -q .toolchain` succeeds —
`tests/test_eval_toolchain_pin.py:180 (.toolchain is not gitignored)`. The
ignore rule **is** present, at `.gitignore:45 (.toolchain/)`, with a trailing
slash, so it matches directories only, and `git check-ignore` cannot match a
path that does not exist on disk. `.toolchain/` is created by
`evals/lib/toolchain.py` on the first eval run, so the test is green on any
machine that has run one and red in every fresh checkout.

Falsified rather than asserted:

```
$ git check-ignore -v .toolchain        -> rc=1        (fresh worktree)
$ mkdir -p .toolchain
$ git check-ignore -v .toolchain        -> .gitignore:45:.toolchain/  rc=0
$ pytest tests/test_eval_toolchain_pin.py -q -> 10 passed in 7.56s
$ rmdir .toolchain                       (restored; tree clean)
```

So the failure is a statement about the machine, not about the repository.
`tests/**` is outside this ticket's `conflict_keys.production` (`evals/**`), so
it is deferred, not fixed: `SI-19-DF-04`.

---

## What this record is allowed to be used for

- The eval case in the next commit encodes §1 and nothing else. §3, §5 and §6
  were observed and are **not** encoded — they are findings, and turning each
  into a case on the day it was found is the volume this ticket exists to avoid.
- Nothing here measures `sktSurface` or `sktHooks`; they were listed, not run.
- Nothing here is evidence about the eval suite's scores. No `claude plugin eval`
  run is in this record.
