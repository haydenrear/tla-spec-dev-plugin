# Review validation convergence and delivery velocity

Right-sizing an epic means choosing a useful increment whose changes can be
reviewed, isolated and validated together. Too many interacting changes can
produce a self-renewing validation loop: repairing one failure exposes or causes
another, manual testing keeps discovering new defect families, and acceptance
never stabilizes. Review and validation are the bottleneck and therefore a
primary source of development acceleration.

The planning agent and epic owner both own this concern. Ticket agents report
failure evidence and attribution; the epic owner reviews the combined pattern.
Use existing reports and review artifacts to improve the delivery path.

## During planning: choose an increment that can converge

Assess loop risk whenever an epic is proposed, expanded or split, before turning
the requested outcome into tickets. Inspect the affected user journeys, changed
interfaces, shared state, environment dependencies and existing tests. Ask
whether failures will be attributable to a small change and whether fixes can
be checked without repeatedly exercising every changed surface.

Warning signs include several independent journeys, simultaneous changes across
coupled layers, large migrations mixed with new behavior, and basic contracts
observable only in the final end-to-end run. Use prior bug attribution and run
reports to identify where earlier increments repeatedly needed repairs.

When a requested increment is too broad, the planning or epic agent recommends
a smaller first epic and a second epic before dispatch. Explain which changes
interact to create loop risk, what useful behavior the first epic delivers,
what moves to the second, and how each can be independently accepted. Preserve
the larger product goal across the sequence. Discuss this throughout planning,
including revisions that add scope; do not wait for final validation to discover
that the chosen increment cannot stabilize.

For each proposed increment, identify ticket-local feedback, the final integrated
acceptance path and the likely blind spots. Add fast intermediate contract,
component or integration assertions where faults would otherwise first appear
in the slow full graph. Shared setup that makes even a small change expensive
is a candidate for improvement in the harness or architecture.

## A changed contract reruns every instrument that asserts it

A ticket's own graph list is not the blast radius of its change. When a
ticket's desired actions or production conflict keys touch an action, its
validation matrix includes every graph whose nodes bind that action, derived
from `testgraph_bindings`, not from the list the ticket was dispatched with.
When it changes how a downstream request is answered (a refusal, a restart or
re-attach path, a provider route), it also reruns the repository's image/host
episode, or the CI job that drives it, before the PR opens. An instrument still
asserting the old contract is red whether or not anyone runs it.

## Short review: before each repair/rerun and at ticket handoff

Use a few lines in the existing evidence record. Ask: **How can we accelerate
reliable delivery of the next user-value increment here?** Record:

- What changed or what hypothesis will this run discriminate? Link the failure,
  fix and attribution. An unchanged retry needs a concrete transient-failure
  hypothesis and evidence that repeating it can distinguish that cause.
- What is the smallest valid rerun? **By default, resume from the failed node**
  (test-graph `graph-architecture-review.md` G0). Use Test Graph's saved-context
  rerun for an isolated node when its inputs/environment remain valid; rerun downstream
  dependents when published outputs change and rebuild stale prerequisites.
  Name why a full fresh run is necessary when choosing one. Keep the required
  final integrated confirmation. Follow test-graph's `references/workflows.md`
  smart failure loop, including fresh execution when context is stale and the
  containing-graph confirmation after the targeted repair passes.
- Can feedback move earlier? Promote the reproduction into a fast intermediate
  assertion that exercises the relevant production contract and runs in the
  ticket graph. Establish red before the fix and green after it; retain the
  final end-to-end coverage.
- Are we converging? Record cumulative elapsed validation/repair time, cycles,
  remaining acceptance failures, recurring defect families and new escapes.
  Compare the failure pattern with the previous run. More tests executed or more
  bugs found does not by itself establish progress toward acceptance.

Do not add a human approval round for an ordinary scoped rerun within the agreed
plan. The short review is a routing decision, not another validation campaign.

## Deeper review: wave boundary, before final validation, and on a trigger

At wave boundaries, add a concise delivery-velocity section to the existing
review artifact. Before starting final full validation/manual acceptance, check
whether the combined increment is stabilizing and failures remain isolatable. Escalate immediately,
without waiting for either boundary, when:

- repairs repeatedly replace known acceptance failures with new failures, so
  the delivered behavior is not stabilizing;
- failures span many newly changed surfaces and fixing one repeatedly requires
  reopening others;
- the same attributed defect family returns after a purported root-cause fix;
- one repair repeatedly breaks other surfaces, or manual testing keeps finding
  defects in areas the graph reports green.

These patterns call for diagnosis of scope, architecture and feedback quality.
A long but steadily converging run is different from a self-renewing loop.
Changing cadence to `finalization-only` or making wave reviews non-gating does
not waive these triggers. Suspend further automatic repair/rerun cycles at a
trigger; finish collecting the current run's evidence, then make a decision.
When excessive interacting changes are sustaining the loop, recommend splitting
out a second epic now. Name the coherent MVP that can stabilize first, the work
that moves, dependency/interface boundaries and the acceptance evidence each
needs. Already integrated changes need an explicit isolation or reconciliation
plan; relabeling tickets alone does not reduce coupling.

Review the attribution across this epic and comparable earlier increments:
where do CATCHes cluster, what remains BLIND, and which fixes actually reduced
recurrence? Missing attribution is uncertainty, not proof of sound design.
Distinguish product architecture, model mismatch, inadequate assertions,
fixture/environment defects and unnecessarily broad graph execution. High bug
counts alone do not establish a flawed architecture or justify a rewrite.

Compare concrete options using the evidence:

| Option | Required argument |
| --- | --- |
| Continue a scoped repair | Root-cause hypothesis, smallest discriminating run, expected failure reduction and the evidence that would refute the hypothesis |
| Split or defer | Useful MVP retained, acceptance impact, successor scope and findings preserved |
| Simplify/refactor | Fault-prone boundary or coupling removed, affected contracts, migration and validation cost |
| Replace/rewrite a bounded component | Why repeated repair is inferior, preserved external contract, bounded prototype/comparison, migration/rollback and total validation cost |

A rewrite is a legitimate option, never an automatic reaction or an unbounded
new epic hidden inside a repair. Price its validation as carefully as its code.
Use a successor epic when it exceeds the current increment. Keep the original
failures as regression cases; re-anchor findings if the model changes, following
spec-double-2's bug-attribution carry-through rules.

Record a decision, owner, next action, expected improvement in feedback or
convergence, and the evidence to inspect at the next review. The epic owner may
adjust rerun selection within the agreed scope. Scope changes, accepted shortfalls or architectural
replacement require the user's explicit decision before dependent work resumes.
If a trigger fires again, bring new evidence and compare alternatives again;
check whether the chosen intervention changed the failure pattern. Keep
acceptance criteria intact and preserve unresolved findings through a split.

## Step size: two capacities, one batch

The criteria above say when an increment is not converging. To size the next
batch, use `references/step-sizing.md`, which turns them into a feedback policy:

1. Summarize the starting revision: components, attribution, escapes, coverage,
   validation-origin faults, coupling, and reviewer/verifier model and version.
2. Estimate **review capacity** and **verification capacity** (including manual
   reach) separately, as scope items, not lines or tickets.
3. Choose a provisional batch at the upper end of the tighter estimate for
   independent items with proof, batching instrument repairs with the work they
   unblock, and compare candidate batches by total cost per accepted increment,
   on distinct cadences. When amortization and caution disagree, batch.
4. Write the decision into existing plan fields: `wave`, `depends_on`,
   `validation`, `review_policy`, the evaluation ticket and `eval_budget`.
5. At each review, **hold, increase by one step, or decrease**. Only a
   high-severity product escape or non-converging product repairs decrease the
   batch. Invalidated evidence, a scope or coupling change, or a model change
   holds it. Instrument faults never shrink it: they schedule an instrument
   fix inside the next batch. One clean review allows an increase.

Record each decision in the deeper review's delivery-velocity section. Sparse
history gets an early review, not a small batch. A model change triggers
recalibration at the same size, not an assumed gain. None of this is a gate
(`step-sizing.md`, *Nothing on this page blocks*).

## Across epics: user value and improving delivery capability

At close, carry a short trend into the next epic's planning: accepted user
outcome, elapsed time to validated acceptance, validation/repair time, full-run
count, manual escapes and recurrence by attributed area. Compare similar work
and state differences in scope/environment; neither raw ticket throughput nor
fewer checks is a reliable velocity measure. Unknown baselines stay unknown.

Name the most expensive recurring obstacle and the smallest change expected to
make the next increment cheaper or faster to validate. Link its evidence and
owner; at the next review, check whether the improvement happened. It may be
better rerun selection, an assertion, reusable setup, a simpler boundary, or a
bounded replacement. This is part of delivering product over time, not permission
for speculative framework work. Report flat or worsening velocity honestly;
do not demand an artificial improvement on every epic or optimize speed by
reducing user value or confidence in acceptance.
