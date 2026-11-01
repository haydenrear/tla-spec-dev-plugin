# Review validation convergence and delivery velocity

Right-sizing an epic is a delivery constraint. An increment that can be built
but cannot be validated and repaired within a practical budget is too large.
Count diagnosis, fixtures, environments, automated runs, manual testing, repairs
and revalidation in that budget. A single final manual phase can still loop
forever; calling it one phase does not bound its cost.

The epic owner owns this outer review loop. Ticket agents report evidence and
escalate triggers; they do not expand scope or start architectural rewrites.
Use existing run reports, attribution rows and wave artifacts. These reviews
require no new test suite, scoring harness or mandatory reviewer agent.

## Before dispatch: price the smallest useful increment

Record the MVP acceptance boundary, ticket-local graph scopes, final integrated
scope, measured or estimated run costs, and a cumulative validation/repair
budget. Include a bounded repair allowance and the point at which the next run
would exceed it. Unknown costs require a bounded discovery measurement before
committing to a large delivery plan. Preserve these estimates beside actuals;
a larger estimate after every failure is not evidence of convergence.

Recommend splitting when independent user journeys, coupled changes or the
expected repair cost make that budget implausible. Each successor epic needs a
useful acceptance scenario. Shared setup that makes even a small increment
expensive is itself evidence to investigate the architecture or test harness.

## Short review: before each repair/rerun and at ticket handoff

Use a few lines in the existing evidence record. Ask: **How can we accelerate
reliable delivery of the next user-value increment here?** Record:

- What changed or what hypothesis will this run discriminate? Link the failure,
  fix and attribution. An unchanged retry needs a concrete transient-failure
  hypothesis and a bounded retry allowance.
- What is the smallest valid rerun? Use Test Graph's saved-context rerun for an
  isolated node when its inputs/environment remain valid; rerun downstream
  dependents when published outputs change and rebuild stale prerequisites.
  Name why a full fresh run is necessary when choosing one. Keep the required
  final integrated confirmation.
- Are we converging? Record cumulative elapsed validation/repair time, cycles,
  remaining acceptance failures, recurring defect families and new escapes.
  Compare with the budget and the previous run. More tests executed or more
  bugs found does not by itself establish progress toward acceptance.

Do not add a human approval round for an ordinary scoped rerun within the agreed
plan. The short review is a routing decision, not another validation campaign.

## Deeper review: wave boundary, before final validation, and on a trigger

At wave boundaries, add a concise delivery-velocity section to the existing
review artifact. Before starting final full validation/manual acceptance, check
that the remaining work and repair allowance still fit. Escalate immediately,
without waiting for either boundary, when:

- the next run would exceed the agreed cumulative budget or repair allowance;
- two consecutive repair/rerun cycles fail to reduce the known acceptance
  failures, or replace them with new failures so acceptance is no closer;
- the same attributed defect family returns after a purported root-cause fix;
- one repair repeatedly breaks other surfaces, or manual testing keeps finding
  defects in areas the graph reports green.

These are default review triggers, not automatic verdicts that architecture is
bad. A project can agree tighter or better-supported thresholds at kickoff.
Changing cadence to `finalization-only` or making wave reviews non-gating does
not waive these triggers. Suspend further automatic repair/rerun cycles at a
trigger; finish collecting the current run's evidence, then make a decision.
A new ticket, wave or “manual phase” does not reset the cumulative accounting.

Review the attribution across this epic and comparable earlier increments:
where do CATCHes cluster, what remains BLIND, and which fixes actually reduced
recurrence? Missing attribution is uncertainty, not proof of sound design.
Distinguish product architecture, model mismatch, inadequate assertions,
fixture/environment defects and unnecessarily broad graph execution. High bug
counts alone do not establish a flawed architecture or justify a rewrite.

Compare concrete options using the evidence:

| Option | Required argument |
| --- | --- |
| Continue a scoped repair | Root-cause hypothesis, smallest discriminating run, remaining cost and explicit stop condition |
| Split or defer | Useful MVP retained, acceptance impact, successor scope and findings preserved |
| Simplify/refactor | Fault-prone boundary or coupling removed, affected contracts, migration and validation cost |
| Replace/rewrite a bounded component | Why repeated repair is inferior, preserved external contract, bounded prototype/comparison, migration/rollback and total validation cost |

A rewrite is a legitimate option, never an automatic reaction or an unbounded
new epic hidden inside a repair. Price its validation as carefully as its code.
Use a successor epic when it exceeds the current increment. Keep the original
failures as regression cases; re-anchor findings if the model changes, following
spec-double-2's bug-attribution carry-through rules.

Record a decision, owner, next action, expected improvement, remaining allowance
and next review trigger. The epic owner may adjust rerun selection within the
agreed scope. Scope changes, revised budgets, accepted shortfalls or architectural
replacement require the user's explicit decision before dependent work resumes.
If a trigger fires again, bring new evidence and compare alternatives again;
do not silently renew the same allowance. Never turn a budget exhaustion into
PASS or weaken assertions to finish.

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
