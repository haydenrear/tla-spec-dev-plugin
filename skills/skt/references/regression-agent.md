---
skill-imports: []
---

# The test-graph regression agent: `skt regress`

Open this when a wave or an epic's code is written and its test graphs have to
be run until they pass, or when you are about to run a graph for the third time
yourself.

Running graphs, waiting on them, repairing the small things that break and
running them again is most of what validation costs. None of it needs a large
model. `skt regress` hands it to a small one, driven through
[meta-harness](https://github.com/haydenrear/meta-harness), in a worktree of the
commit you name. You get back a verdict, the agent's small fixes as commits, an
attribution row for every red it met, and an escalation when the fix is bigger
than it is allowed to make.

```bash
skt regress new <ref>                  # worktree of that commit on branch regress/<id>; prints the id
skt regress run <id> <graph>...        # report-only: run, retry environment failures, report
skt regress run <id> --all --fix --isolated "<statement>" [--env KUBECONFIG=...]
                                       # fix mode: small fixes, rerun until green, or escalate
skt regress run <id> --all --dry-run   # write the brief and the episode request, start nothing
skt regress info <id> | list
skt regress close <id>                 # remove the worktree; a branch holding fix commits is kept
```

## Two modes

| | report-only (default) | `--fix` |
| --- | --- | --- |
| edits files | never | small fixes, one commit each, on `regress/<id>` |
| reruns | once, by resume, for an `environment` failure | until green, up to `--max-runs` per graph (default 5) |
| needs `--isolated` | no | **yes, refused without it** |
| a bigger fix is needed | says so in `escalation` | stops at once and says so in `escalation` |

## Fix mode needs an isolation statement

An agent that edits and reruns until green will run a graph many times and will
poke at whatever the graph touches. So `--fix` is refused without `--isolated`:
one sentence saying what these graphs touch and why nobody else is on it.

```bash
skt regress run 4f2a91c0de --all --fix \
    --isolated "k3d cluster regress-4f2a91c0de, created for this run; otherwise local temp" \
    --env KUBECONFIG=$PWD/.regress/kubeconfig
```

What `skt` does about isolation, and what it leaves to you:

- It sets `TEST_GRAPH_FEATURE_BRANCH=regress-<id>` for the agent. Nodes that use
  the environment-repository contract key their environment on that, so they
  provision a private one instead of reusing the feature branch's.
- `--env KEY=VALUE` (repeatable) reaches the agent's shell. Use it to point the
  graphs at the private cluster, namespace or account.
- It reads the `side_effects(...)` the graphs' nodes declare, prints the ones
  that leave this machine, and puts the list in the brief and the result. That
  is a reading aid for writing the statement. It proves nothing: a node can do
  more than it declares.
- It does **not** create the cluster and cannot check that your statement is
  true. Making a graph isolatable is test-graph's
  `references/isolation-for-agent-runs.md`.

## What a small fix is, and what is escalated

The agent is told a small fix is one that is obviously right from the report and
the log: a wrong path, a missing import, a typo, a stale fixture, a short
timeout, a node script that crashes for a reason unrelated to what it asserts.
It is told never to weaken a check to get a green.

It must stop, change nothing more, run nothing more and write an `escalation`
(graph, node, reason, what is needed, files, quoted evidence) when the fix would
exceed the budget, needs a new file or dependency, changes an interface, schema,
spec or model, requires deciding what correct behaviour is, was tried once and
did not work, or has an unknown cause.

The budget is measured by `skt` from git, not taken from the agent:
`--max-fix-lines` (default 60 changed lines in total) and `--max-fix-files`
(default 4). A run over it is `escalated` even when every graph is green. So is
any change to the tree in a report-only run.

## The verdict is not the agent's

`run` reads each graph's `summary.json` under `build/validation-reports/`, and
only reports written after the run started.

| exit | verdict | meaning |
| --- | --- | --- |
| 0 | green | every requested graph's latest report is `passed`, and nothing is uncommitted |
| 1 | red | a graph's latest report is `failed` or `errored`, with no escalation |
| 3 | incomplete | a graph has no fresh report, or is `needs_full_run` |
| 4 | escalated | the agent escalated, or its changes are over budget |
| 2 | | usage, including `--fix` without `--isolated` |

`needs_full_run`: once the agent has changed the tree, a pass counts only if it
is a full run that finished after the last fix commit. A resume proves only the
nodes from the failed one onward.

## What comes back

Each run is a numbered attempt under `<git common dir>/skt-regress/<id>/`:

| file | what it is |
| --- | --- |
| `result.json` | the verdict, per-graph status, escalation, budget, attribution gaps |
| `fixes.patch` | everything the agent changed against the commit under test |
| `attribution.yaml` | one candidate CATCH row per red the agent met |
| `agent-report.json` | the agent's own report |
| `brief.md`, `request.json`, `episode.json` | the exact prompt, the episode request, meta-harness's result |
| `.meta-harness/evidence/` | the agent's full trace |

**Attribution.** A red the agent fixed and then ran green leaves no trace in the
final reports, so its row is the only record it happened. Each row carries
`graph`, `node`, `origin` (product, instrument, environment, unknown: where the
fix belongs), `area` in prose, `effect` (faithful or false red), `observed`
(quoted), `fix` (a commit, `escalated` or `none`), `pinned_by`, and `introduced_by` (the
ticket whose commit caused it, when the commit under test holds several
tickets and `git log` shows which). The file is
shaped for the ledger (spec-double-2 `references/bug_attribution.md` §4, §4.3,
§6a) with `channel: test-graph`. `skt` compares the rows against the reds it saw
in the reports and prints every `ATTRIBUTION GAP`: a red with no row, or a row
missing a field. Gaps do not change the verdict. They are yours to fill.

**The rows and the fixes are a small model's.** Read `fixes.patch` before you
merge `regress/<id>`, in particular for a check that was loosened, and read each
attribution row against its report before it goes in the ledger.

## Choosing the model and the binaries

- `--model` or `$SKT_REGRESS_MODEL`: a meta-harness model id, the provider
  prefix followed by the model the provider should select. The default is
  `CLAUDE_haiku`. `meta-harness providers` lists the prefixes.
- `--meta-harness` or `$META_HARNESS_BIN`, else `meta-harness` on `PATH`.
- `--runner` or `$SKT_REGRESS_RUNNER`: the test-graph `run.py`. By default the
  copy inside the worktree under test is used when the repository ships one,
  then this session's homes.
- `--base-url` drives an already running `meta-harness serve` instead of
  starting one. Evidence then lives wherever that server keeps it.
- `--timeout` bounds the whole episode in seconds (default four hours).

meta-harness answers the agent's permission requests with the first option
offered, which is how an unattended agent gets to run shell commands. That is
the other reason fix mode asks for isolation.
