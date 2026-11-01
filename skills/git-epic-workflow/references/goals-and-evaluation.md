# Goals and evaluation

An epic exists to move something measurable. Tickets that only reference their
own slice optimize local correctness and leave the epic's actual outcome
unmeasured — every ticket passes, the epic ships, and nobody can say whether the
thing got faster, more accurate, or more reliable.

The fix is one primitive: an epic declares **goals**, one or more terminal
**evaluation tickets** own the harness that decides them, and **every ticket
declares how it relates to at least one goal**. That relation is load-bearing
context: it tells the ticket agent what result its change is supposed to
produce, which cheap local signal predicts it, and which final measurement it
will be judged by.

Goals are agreed with the user at epic creation, alongside the deferment policy
(`deferment.md`). Do not infer them from the codebase and do not default them.

## One epic, one bounded product increment

A **goal** is the outcome to decide; an **epic** is the bounded delivery unit
that achieves one meaningful MVP increment toward it. A larger product goal
may span several epics. An epic may carry several supporting measurable goals,
but they must serve the same increment, not collect unrelated improvements.
Describe the user, the usable end-to-end behavior they gain, the acceptance
scenario, and what is explicitly deferred. A bug epic may instead restore a
named product behavior or reliability property; state the affected user impact.

Size the epic so its interacting changes can be reviewed, isolated and validated
as one useful increment. During planning, identify scope likely to sustain a
repair-and-revalidate loop: coupled surfaces changing together, unrelated user
journeys, or faults visible only in slow final integration. Use prior bug
attribution to inform that judgment. When asked for an overly broad increment,
recommend a smaller first epic and a second epic, with useful acceptance
scenarios, clear boundaries and an order that reduces the interactions under
test. Reassess when scope grows or repairs keep introducing new failures.
Review and validation are sources of acceleration: improve failure isolation,
rerun from the broken node where valid, and add faster intermediate assertions.
Do not split into technical fragments that provide no meaningful outcome.

Ticket validation covers the affected slice and its dependency closure. The
integrated full graph and one manual product-testing phase belong at the end
of the epic (`finalize.md` §2–2c). A passing ticket is evidence for that slice;
the final graph plus manual acceptance decides the delivered increment.

Right-sizing includes the cost of reaching validated acceptance, not just the
first full run. Use `validation-review.md` for loop diagnosis, review
triggers, architectural alternatives and delivery-velocity trends across epics.

## What counts as a goal

An epic goal is a specific, falsifiable claim about the program after this
increment, with a named instrument that decides it. Write goals as outcomes, not as work.

| Not a goal | Goal |
| --- | --- |
| "Refactor the ingest path" | "p99 ingest latency ≤ 250ms at 5k rps, throughput not regressed" |
| "Improve retrieval" | "Answer-match eval ≥ 0.82 on `evals/retrieval_v3.jsonl`, from 0.71" |
| "Add integration tests" | "The `epicIntegration` graph passes end to end with no skipped nodes" |

Goal kinds:

- **`perf`** — latency, throughput, memory, cost; needs a baseline run and a
  target expressed against it.
- **`eval`** — accuracy/quality judged against a fixed artifact set; needs a
  pinned dataset and scorer version, or — for a judged instrument — a pinned
  rubric version and a stated judging setup.
- **`integration`** — a named end-to-end Test Graph or system path passing under
  realistic composition, not per-ticket units.
- **`quality`** — an invariant/coverage/robustness property with a deciding
  command (TLC model, fuzz budget, conformance suite).

Every goal names one deciding instrument. A goal nobody can decide is a slogan;
either find the harness, schedule a wave-1 ticket that builds it, or drop the
goal.

### The instrument does not have to be a command

For a long time this file said "one deciding command", and its only worked
example was a benchmark script. That framing is too narrow, and the project's
own flagship consumer already runs outside it: `tla-spec-dev`'s
`ports-as-adapters` epic declares goals whose harness reads

> the HP-01-shaped seeded catalogue extended with adapter-internal faults, run
> against real and fake wirings, **scored by two blind judges**

which is a procedure, not a command line. That repository moved to judged
scoring deliberately and on evidence, and states the reason itself: *"A number
computed from the artifact can be optimized by editing the artifact. A
judgement that must cite the artifact can only be satisfied by changing what
the artifact is"* (`tla-spec-dev/references/eval_scorecard.md`). That file is
the worked example of a judged instrument and **the sole authority on its own
dimensions, anchors, scoring rules, judging protocol, storage, sealing and
history rules**. This file cites it and restates none of them.

So a `harness` is whatever **decides the goal reproducibly and independently of
the person hoping it passed**. Three shapes all qualify:

- **a command** — a benchmark, an eval scorer, a graph run. Write the exact
  invocation;
- **a judged procedure** — an artifact scored against a versioned rubric by
  judges who cite the artifact, blind to arm where arms exist. Write what is
  scored, by how many judges, under which rubric version, and where the
  evidence lands;
- **a mixed instrument** — measured figures recorded beside a judged score, read
  together rather than combined. How the two are reconciled is the instrument's
  rule to state, not this file's.

What is still forbidden is an instrument nobody can execute at all. "The design
feels cleaner" names no instrument; "scored against `<rubric>` version N by two
blind judges, results under `<evidence_root>`" names one, and the fact that a
human runs it does not make it unfalsifiable.

**Name the instrument; do not copy it.** Write which rubric, which version, how
many judges, and where the evidence lands — and then link the rubric. Never
restate its dimensions, its anchors, its scoring rules or its comparability
rules here. A rubric's own repository versions those and executes checks over
them; a copy in this file is covered by nothing and will drift. `tla-spec-dev`
learned this by measurement: a charter there restated a table of judged results
and two of its rows were wrong, read forward across a change to the instrument
before anyone noticed.

**A round that calls itself blind must say what its judges received.** Blindness
to the packet is not blindness to the operator's conclusions. An agent harness
can inject persistent memory, the repository's recent commit subjects, session
hooks and an installed-tooling listing into a dispatched judge *before it makes
any tool call*, so no forbidden-reading list written inside the dispatch can
reach them. Measured on Claude Code: judges dispatched from the repository
received the auto-memory index verbatim and the five most recent commit
subjects; one, asked before opening any packet, reported that it arrived
carrying not only the expected answer but the expected *distribution*, and named
the temptation to reproduce it.

**It is fixable, and the fix is two halves — neither sufficient alone.** On that
harness, `--safe-mode` removes auto-memory, hooks, project skills and MCP but
**not** the repository status block, so a judge run at the repository still
receives the commit subjects; dispatching from a directory outside any git
repository removes those but leaves the session hook and skill listing standing.
Both together measured clean. Do not read that as a settled recipe: the flag's
own help does not name auto-memory, so a round leaning on it leans on
undocumented behaviour, and the honest practice is to **verify rather than trust
it** — record the digest of whatever memory file the round was supposed to
exclude, and ask each judge to report what it received before it opens anything.

So, beside the scores, record which dispatch path was used and what the judges
reported receiving. Where a round could not be made blind, print the
contamination note next to the number: withdrawing the number or dropping the
word *blind* silently both destroy the record of what was actually measured.
This is a disclosure obligation a reader can check, deliberately not a gate.

### Not every target is a number

A target states what counts as success. Usually that is a threshold, but two
legitimate shapes are not:

- **A multi-clause target.** `GOAL-port-reach` targets "the same adapter-internal
  fault dies on at least one generated instrument, **and** no positive control is
  red" — two independent clauses that can settle differently, and did.
- **A goal with deliberately no numeric target**, where the epic is building the
  instrument itself. `GOAL-complexity-measurable` says it outright: *"NO TARGET
  ON THE NUMBER ITSELF — a threshold before anything can produce a number would
  be inventing the answer."* Its baseline is "no such instrument exists". A
  first-measurement goal is decided by whether the instrument runs and
  discriminates, not by a figure chosen before anything could produce one.

Write either plainly in `target`. Do not manufacture a threshold to make the
field look conventional — an invented number is the failure this whole primitive
exists to prevent, and it is worse than an honest "no target on the number".

## Ask the user at epic creation

Ask before scaffolding the workflow, and ask concretely:

> What should be measurably better when this epic is done? For each outcome I
> need: the metric, the instrument that decides it — a command, or a judged
> procedure with its rubric — its value today, and the
> threshold that counts as success. If a harness does not exist yet, I will
> schedule a wave-1 ticket to build it and measure the baseline before the
> tickets that change behavior.
>
> I will add a final evaluation ticket that runs those measurements on the
> integrated epic branch, and every other ticket will declare how it moves each
> metric so its agent knows what result it is aiming at.

Push back on unmeasurable answers once, offering the nearest measurable form.
If the user genuinely has no measurable outcome (pure refactor, docs, plumbing),
record that decision explicitly rather than inventing a metric:

```yaml
epic_goals: []
goals_waived: "<user's reason: no behavioral delta; correctness held by existing suites>"
```

The validator warns on a waived or missing goal set; it does not block. A waived
epic still runs its normal ticket validation matrices.

## Baselines

A target without a baseline cannot be evaluated — "p99 ≤ 250ms" is unfalsifiable
if nobody knows today's number.

- **Harness exists** — measure at epic kickoff on the freshly created epic
  branch, before any ticket lands. Commit the measurement under the epic
  evidence root and record its value and commit SHA in the goal.
- **Harness does not exist** — schedule a wave-1 ticket whose slice is the
  harness plus the baseline run. Every behavior-changing ticket depends on it.
  Until it merges, the goal's `baseline.value` stays `unmeasured` and the
  validator warns.
- **Harness is judged and this subject has never been scored under it** — the
  instrument existing is not a baseline. Run it at epic kickoff on the epic
  branch, before any ticket lands, exactly as for a command harness; seal that
  run and record its card as the baseline. A judged instrument that has been
  run on other subjects, or in other epics, has measured something else. If a
  kickoff round is not affordable, `unmeasured` with the reason is the honest
  answer and the goal stays legal — a goal that cannot be scored is not a goal
  that fails.

Never take the baseline after the first behavioral ticket has merged; that
measures the epic against itself.

**A judged baseline is a prior scored run, not a recollection.** Where the
instrument is a judged one, `baseline.value` cites the sealed card that produced
the number and `baseline.evidence` points at it, so the comparison is against a
record that cannot be edited afterwards. Two consequences follow, both learned
the hard way in `ports-as-adapters`:

- **A baseline can be superseded before the epic starts.** A wider or repaired
  instrument may have re-measured the same thing since. Move the bar to the
  newer number, say which run it came from, and leave the superseded run sealed
  and unedited on the record — measuring divergence against a weaker instrument
  credits movement the better one absorbs.
- **A number measured on one instrument is not comparable across a repair of
  that instrument.** If the instrument changed between baseline and measurement,
  say so and treat the movement as a fact about the instrument until proven
  otherwise. `tla-spec-dev` executes this as a rule and an audit; the general
  point is that "the number moved" and "the thing got better" are different
  claims.

**For a judged goal, `baseline.evidence` is the card, not the folder it sits
in.** Point it at the sealed card that produced the number, or — where the
number is a figure over several cards — at the exact list of them. A directory
is not a card and neither is a results summary: the evaluation ticket has to
re-open the same cards, and it cannot pick them out of a folder.

A baseline of `unmeasured` is honest and warns; a baseline of "no such
instrument exists" is the normal state of a goal whose epic is building the
instrument, and it belongs in the field verbatim rather than as a guess.

## Plan schema

`epic_goals` sits at the root of
`specs/desired_program_model/ticket_plan.yaml`, next to `deferment_policy`:

```yaml
epic_goals:
  - id: GOAL-ingest-p99            # stable, never reused, never renamed
    kind: perf                     # perf | eval | integration | quality
    statement: "Batched ingest cuts tail latency without losing throughput."
    metric: "p99 ingest latency (ms) at 5k rps; throughput (events/s)"
    harness: "uv run scripts/bench_ingest.py --profile epic --out <evidence>"
    baseline:
      value: "p99 412ms, 5.1k events/s"     # or: unmeasured
      measured_at: "<commit sha the baseline ran on>"
      evidence: "results/epic-<slug>/baseline/ingest.json"
    target: "p99 <= 250ms and throughput >= 5.0k events/s"
    evaluation_ticket: "EPIC-9"     # ticket with role: evaluation that decides it
    evidence_root: "results/epic-<slug>/goals/GOAL-ingest-p99"
```

Each ticket gains a `goals` list, and evaluation tickets gain `role` and
`owns_goals`:

```yaml
tickets:
  - id: EPIC-3
    # ...existing scheduling fields...
    goals:
      - goal: GOAL-ingest-p99
        contribution: direct            # direct | enabling | guard
        expected_effect: "-120ms p99 from write batching; throughput unchanged"
        local_signal: "uv run scripts/bench_ingest.py --profile ticket --quick"

  - id: EPIC-9
    role: evaluation                    # omit or use `implementation` elsewhere
    owns_goals: ["GOAL-ingest-p99"]
    goals:
      - goal: GOAL-ingest-p99
        contribution: guard
        expected_effect: "decides the goal; adds no behavioral delta"
        local_signal: "N/A: this ticket is the measurement"
```

Contribution kinds:

- **`direct`** — this ticket's change is expected to move the metric. Requires a
  numeric or directional `expected_effect` and, wherever possible, a
  `local_signal` the agent can run inside its own worktree.
- **`enabling`** — no expected movement on its own; it unblocks a `direct`
  ticket (harness, refactor, plumbing, fixture). `expected_effect` states
  `none — enabling only` plus what it unblocks.
- **`guard`** — the ticket must not regress this metric even though it targets
  another goal. `local_signal` is the regression check.

## Scheduling rules the validator enforces

When `epic_goals` is non-empty:

- every goal is referenced by at least one non-evaluation ticket — a goal no
  ticket contributes to is a goal nobody is working on;
- every ticket declares at least one goal entry;
- each goal's `evaluation_ticket` exists and carries `role: evaluation`;
- every contributing ticket **reaches its goal's evaluation ticket** through
  `depends_on`, so the evaluation cannot start before the work it evaluates;
- every contributing ticket promotes **before** that evaluation ticket in the
  promotion lane.

Mirror those `depends_on` edges into GitHub with `--add-blocked-by` like any
other dependency, so the tracker shows the evaluation ticket blocked by its
contributors.

Missing goals, a missing evaluation ticket, an `unmeasured` baseline, and a
`direct` contribution with no local signal are **warnings**: the plan still
validates, and the epic owner decides. Inconsistencies inside a declared goal
set (unknown goal IDs, an evaluation ticket that promotes before its
contributors, a goal with no contributor) are **errors**.

## Goal disposition when scope is retired

A ticket retirement never silently deletes its goal relation. Every goal the
ticket contributes to, owns, or evaluates is copied into
`retirement.affected_goals` with one explicit owner-approved disposition:

- `accepted_missed` — the outcome is known not to meet its target, and the
  owner accepts that miss for this epic with a recorded reason;
- `accepted_unmeasured` — the outcome will not be measured in this epic, and
  the owner accepts that gap with a recorded reason;
- `carried` — deciding the goal moves to a named `successor_issue` and
  `successor_workflow`.

These are dispositions, not flattering verdicts. Preserve the original goal,
baseline, target, and evaluation-ticket identity so the receipt explains what
the epic stopped promising. When more than one retired ticket touches a goal,
all receipts must use the same disposition and, for `carried`, the same
successor pair.

The ticket decision and goal dispositions are uniform. A ticket with
`retirement.resolution: carried` carries every affected goal to the exact same
ticket-level successor issue/workflow. A ticket resolved as `superseded` or
`abandoned` cannot carry a goal, and neither the ticket nor its non-carried goal
entries may contain successor fields.

Retiring one ticket while other tickets still serve the same goal is allowed.
The validator warns that the goal's evaluation ticket or other active tickets
remain associated with a disposed goal; decide with the owner whether the
evaluator still measures something meaningful, and note it in the epic PR. Do
not re-scope a ticket just to satisfy that warning. The canonical schema and
transaction are in `plan-and-schedule.md` §5a.

## What the ticket agent does with it

The assignment block carries the goal context, and the ticket agent:

1. reads its goal entries **before** implementing, and treats
   `expected_effect` as the result it is aiming at, not decoration;
2. runs `local_signal` before close and records the number under the ticket
   evidence root — this is a signal, not a gate: a missed local signal is
   reported, not hidden, and never justifies weakening the REQUIRED matrix;
3. reports the measured local signal against `expected_effect` in the PR body's
   `## Goal contribution` section, including "no measurable movement" outcomes;
4. files a deferred finding (`deferment.md`) when it discovers the goal is
   unreachable by the planned slice, rather than expanding scope to chase the
   metric.

A ticket whose local signal moves the wrong way is not automatically a failed
ticket — the integrated evaluation decides. It is, however, always reported.

## What the evaluation ticket does

An evaluation ticket is a real ticket: it has a slice, a spec ticket, and a
close record. Its slice is the measurement, not the behavior. It:

- promotes last among the contributors to the goals it owns;
- runs each owned goal's `harness` on the integrated epic tip, from a fresh
  start, and writes results under the goal's `evidence_root`;
- reports **baseline → measured → target** and a verdict per goal — **one
  verdict per clause** where the target has more than one (see below);
- files deferred findings for regressions it uncovers instead of fixing them;
- never edits the target to match the result, and never re-runs selectively
  until a number passes. Report the run that happened.

An evaluation ticket that finds a goal missed does not fail the epic on its own.
It hands the epic owner a decision: add a ticket, accept the shortfall with a
recorded reason, or re-scope the goal — all at finalization.

## Finalization

The epic PR reports every goal as a row — and every **clause** of a goal as its
own row:

| Goal | Clause | Kind | Baseline | Measured | Target | Verdict |
| --- | --- | --- | --- | --- | --- | --- |

Delivered-goal verdicts are `met`, `missed`, or `unmeasured` (with a reason). An
epic may close with a missed goal only when the user has explicitly accepted it
and the reason is recorded in the PR body. A goal covered by a verified
retirement receipt is reported instead as `missed (accepted via retirement)`,
`unmeasured (accepted via retirement)`, or `carried`, with its receipt and
successor where applicable. Never label those goals `met`, and never omit them
from the table.

**A goal verdict is not always one word.** Where a target has several clauses,
each is measured and reported separately; `GOAL-port-reach` settled as *clause 1
met, clause 2 not met*, and a single token could not have carried that. The
reason to insist is not tidiness — a ledger that stores one verdict per
multi-clause goal has to choose which clause the word refers to, **and it will
choose the flattering one**. Use `—` in the Clause column for a single-clause
goal so the shape stays uniform.

A goal whose target is deliberately not a number (an instrument-building goal)
is still reported here: `Measured` is what the instrument produced on its first
real run, `Target` restates the no-threshold decision, and the verdict says
whether the instrument ran and discriminated.
