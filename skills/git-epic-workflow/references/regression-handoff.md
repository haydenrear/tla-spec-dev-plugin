# Handing graph regression to a small-model agent

Read this when a batch's code is complete (a wave, or the whole epic, as
`step-sizing.md` sized it) and its test graphs have to be run until they pass.

Graph regression is the long, expensive part of validation: a graph is run,
something small breaks, it is repaired and the graph is run again, often many
times. Done by the epic agent or a ticket agent, every lap is paid for at a
large model's price. `skt regress` gives the laps to a small model and returns
to you only the result. A larger batch then pays for review and for graph
regression once, which is what makes the larger batch worth taking.

## The loop

1. **Write the step.** Every ticket in the step lands its code, its unit tests
   and its new or changed graph nodes, and runs only the cheap local checks
   (`step-sizing.md` §0). Nobody runs a graph. Commits carry their ticket id.
2. **Branch and hand off.** From the pushed batch tip:

   ```bash
   skt regress new <epic tip sha>          # or: skt regress adopt <a set-up worktree at that tip>
   skt regress run <id> <affected graphs>... --fix --isolated "<statement>" [--env KUBECONFIG=...]
   ```

   Use `adopt` when the graphs need a skill home, an index or other local
   setup: a fresh worktree has none, and the agent may not create it. Never
   let a regression run build a new index base or start services.

   Name the affected graphs and their dependency closure from the plan's
   `testgraph_bindings`, plus the graphs the batch added. `--fix` needs the
   isolation statement; see below. Run it in the background: it can take hours.
3. **Read what came back** (table below), absorb the attribution, and either go
   on to manual testing and the merge, or repair and hand off again.

## What came back, and what you do

| exit | verdict | you |
| --- | --- | --- |
| 0 | green | review `fixes.patch`, merge `regress/<id>` into the epic branch, absorb `attribution.yaml`, go on to the manual pass |
| 4 | escalated | read the escalation; make the fix yourself or dispatch it to a ticket agent; push; `skt regress new <new tip>` and run again |
| 1 | red | the agent ran out of laps without escalating; treat it as an escalation and read the last report |
| 3 | incomplete | a graph was not decided (timeout, episode failure, or `needs_full_run`); run again with the same id, naming those graphs |
| 3 | `AGENT STOPPED WITHOUT REPORTING` | it started, ran tools and ended with no report (stalled, or used a wait tool). Read the trace the output names, check nothing it started is still running, then decide: rerun, or run the graphs as background jobs yourself |
| 3 | `AGENT DID NOT START` | the small model never ran, usually because its CLI is not logged in on this machine. Do not rerun and do not run the graphs yourself instead: tell the user, and wait |

**An escalation is the agent doing its job.** It is told to stop and return
anything that is not a small, obvious fix: a change over the line budget, a new
file or dependency, a change to an interface, schema, spec or model, a decision
about what correct behaviour is, a fix that did not work the first time, an
unknown cause. `skt` also measures the agent's diff and escalates a run that
went over budget whatever the agent said.

**Review the fixes before merging them.** `fixes.patch` is a small model's work.
Read it for a check that was loosened to get a green, and for edits outside the
test graph, which the result lists separately. Reject by not merging
`regress/<id>`.

## Isolation is yours to arrange

Fix mode reruns graphs repeatedly and unattended, so it is refused unless you
state that what the graphs touch is private to the run: `--isolated "k3d cluster
regress-<id>, created for this run"`. A graph that deploys to Kubernetes gets
its own cluster, not a namespace in a shared one. How to arrange that, and what
to do with a graph that cannot be isolated (run it report-only, without
`--fix`), is test-graph's `references/isolation-for-agent-runs.md`.

**One regression run at a time, unless every one is isolated.** Before `skt
regress run`, look at `skt regress list` for a run marked `RUNNING`, and make
sure no ticket agent is running the same graphs by hand. A second run is refused
unless both carry `--isolated`, report-only runs included. Do not split a
step's graphs across parallel runs to save time unless each has its own
cluster, ports and output directories.

Plan for it: a graph the regression agent will repair needs its isolation
named in the plan, on the tickets whose `validation.graphs` include it.

## Attribution comes back with every run

Every red the agent met has a row in `attribution.yaml`, including the ones it
fixed, which leave no trace in the final green reports. Rows are shaped for the
ledger (`bug_attribution.md` §4): `origin`, `area`, `channel: test-graph`,
`effect`, `observed`, `fix`, `pinned_by`.

- Each row's `introduced_by` names the ticket whose commit caused the red,
  where the agent could tell from `git log`. Fill it in yourself where it is
  null: a step of several tickets is only measurable per ticket.
- Absorb them at the step boundary, before the next step starts, as you absorb a ticket's inbox
  (`deferment.md`). Check each against its report first: origin and area are a
  small model's reading.
- `ATTRIBUTION GAP` lines name reds that came back with no usable row. Fill
  those yourself from the report they point to. Do not drop them.
- Rows with `origin: instrument` or `environment` and `effect: false red` are
  the validation-origin faults `step-sizing.md` §6 reads. They are charged to
  the instrument and never shrink the batch. Rows with `origin: product` that
  were escalated are the product escapes that do.

## What this does not replace

The final integrated confirmation and the manual acceptance pass
(`finalize.md`) still run, after a green. A regression agent's green is the
graphs passing on that commit plus its fixes. It is not a review.
