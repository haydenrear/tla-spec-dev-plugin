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

   Tell the agent what you know with `--instructions "<text>"` (or
   `--instructions-file`): what the step's tickets changed, which nodes are
   flaky, where a failure is likely. It cannot be used to relax the brief's
   rules.

   Use `adopt` when the graphs need a skill home, an index or other local
   setup: a fresh worktree has none, and the agent may not create it. Never
   let a regression run build a new index base or start services.

   Name the affected graphs and their dependency closure from the plan's
   `testgraph_bindings`, plus the graphs the batch added. `--fix` needs the
   isolation statement; see below. Run it in the background: it can take hours.
3. **Check on it about every half hour.** Start the run as a background
   command, then end your turn and sleep. Set a backup timer for 20 minutes
   before you do, so that you wake even if the run never reports back. Do not
   poll in a loop and do not do the agent's work while you wait. At each check:

   - `skt regress list`: is it still `RUNNING`?
   - The newest report under `<test graph>/build/validation-reports/`: is a
     graph still producing output, and has any graph finished?
   You do not have to watch for an idle agent. `skt regress` sends the wait
   tools (`ScheduleWakeup`, `CronCreate`, `Monitor`) as the episode's deny
   list, so the agent cannot wait on a timer, and passes `--stall-timeout` as
   the episode's idle timeout, so meta-harness itself ends an agent that has
   gone quiet. Stop a run by hand (signal the `skt regress run` process; it
   cancels the episode on the server) only when a GRAPH is stuck, not the agent.
4. **Read what came back** (table below), absorb the attribution, and either go
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

**Trust the verdict, check the diagnosis.** Which graphs are green and which
are red is read from the reports and has been reliable. The agent's account of
WHY a graph is red has often been wrong: a node bug called a product defect, a
gate's plain message turned into a theory about a recent change. Before you act
on an attribution row, read the line it quotes. When the agent got something
right that was not obvious, or you had to throw its fix away or correct its row,
add a case to the OK / NO GO list the brief shows it
(`skt` skill, `references/regression-agent.md`, *Teaching the agent*). That
list is the first thing to change after a disappointing lap.

**Copy a lap's results before `skt regress close`.** `close` deletes them
unless you pass `--keep-state`, and the boundary review and the attribution
ledger are written from them.

**While a long corpus holds the build directory**, write and smoke-test the
next ticket against a second build directory (for Rust,
`CARGO_TARGET_DIR=<worktree>/target-next`) instead of waiting.

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
