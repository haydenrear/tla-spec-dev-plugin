# Step sizing: review capacity, verification capacity and the batch between them

Read this when planning an epic (`plan-and-schedule.md` §3a, §4b), at each review
point `review_policy` names, and whenever a `validation-review.md` trigger fires.
It turns that page's convergence criteria into a feedback policy the planning or
epic agent operates by hand. It adds no script, controller, schema or gate.
Every decision is written into fields the plan and the review artifact already
have (§5).

**The question.** What is the largest batch of change that reviewers can examine
and instruments can verify, so that failures stay attributable and repairs
converge? The answer is two estimates and a choice. A batch is never larger than
the tighter estimate. Speed is never claimed from running fewer checks.

**Evidence ids.** `C1`-`C30` are cost rows in
`specs/results/evidence-sized-delivery/ESD-01/cost.md`. `F1`-`F8` are families
in `failure-families.md` beside it. Other row ids (`BS-07-DF-05`, `DEF-154`) are
rows of `inventory.yaml` there. All are in the tla-spec-dev-plugin repository.

## 1. Summarize the starting revision

Do this once per epic, at the revision the epic branch starts from, and again
when a §6 override fires. Write a few lines per input in the planning
conversation and the first review artifact. **Unknown is a valid answer and is
written as `unknown`.** It is never filled with a default.

| Input | Where to read it | What it changes |
|---|---|---|
| Affected components | the plan's `conflict_keys`, `desired_actions`, `testgraph_bindings` | which instruments and reviewers are involved |
| Historical attribution | earlier ledgers and `attribution.yaml`, filed by origin, channel and effect (`bug_attribution.md` §4.3) | where defects cluster, by **origin** |
| Severity and escapes | ledger `severity`, manual-final-testing and post-merge CATCHes | what review or verification missed before |
| Coverage | REACH and BLIND rows (`bug_attribution.md` §5, §6) for the affected components | how much a green actually proves |
| Validation-origin faults and their cost | instrument CATCHes and false reds (`bug_attribution.md` §6a), cost rows (C5, C10, C19, C20) | how many reds will not be about the change |
| Coupling | shared state, shared host or output tree, interfaces changed together, nodes flagged by `test-graph`'s `graph-architecture-review.md` | how many interactions a batch creates |
| Reviewer and verifier identity | model name and version, harness version (`claude-agent-acp`, Claude Code), skill pins, test-graph copy | whether history applies at all |

Charge an instrument fault to the instrument, never to product risk
(`bug_attribution.md` §6a). A red the instrument produced lowers
**verification** capacity. It says nothing about how risky the product change
is.

The reviewer/verifier identity is `unknown` in almost every audited row. ESD-01
found a named model in one record only (meta-harness finalization). So history
from an unnamed model calibrates a prior, not the current agent.

## 2. Two capacities, estimated separately

Count capacity in **scope items**, never in lines of code or ticket count. A
scope item is one behavior change at one boundary. Write each item as
*behavior, boundary, graph nodes affected*. A pair of items that share state, a
host resource or an interface is an **interacting effect**. Count each such pair
as one more item: a reviewer and an instrument must each check the interaction
as well as the parts.

**REVIEW capacity** is the number of scope items one review point can examine
and still catch what it should. Estimate it from:

- earlier review artifacts: how many hot spots each held, and how many defects
  in reviewed areas escaped to a later channel;
- whether each item carries its own red-on-base to green-on-branch proof. Items
  with proof are cheaper to review. In the bug-sweep, 19 of 19 milestone-1
  tickets carried one (`review/wave-3/review.md` in that epic);
- reviewer identity and attention: an owner reviewing at `milestone` cadence
  reads a larger batch than at `wave` cadence, so expect less depth per item;
- measured review time where it exists. It mostly does not (C14, C30). CDC is
  the one phase-separated record: review plus graphs/merge took 2.6-3.0 times
  the implementation phase (C17, C18).

**VERIFICATION capacity** is the number of scope items the available
instruments can discriminate **and attribute** within one validation cycle.
Estimate it from:

- faithful instruments per item: an instrument that has shown red on a planted
  wrong answer (F3). An item with no faithful instrument costs manual reach;
- validation-origin fault rate on the affected graphs (F1, F2, F4, F5, F7). Each
  false red costs a diagnosis, and diagnoses do not parallelize well;
- shared resources: one host, one output tree, one eval budget. Concurrent runs
  on one host can turn a 70-minute suite into a projected 20 hours (`DEF-154`,
  C25);
- cost per run: cold setup (F6, C26, C28), and expensive evals (C8-C11);
- **manual-testing reach**: how many scenarios a manual pass can cover in one
  session. Items reachable only by hand use up this capacity. The final manual
  pass is the only channel that caught `DEF-110` (blocking; 123,132 green
  spec-unit cases).

Write each estimate as a **range with a confidence and the evidence behind it**.
For example: *"review 4-6 independent items or 2 coupled; low confidence, one
prior review."*

When the reviewer or verifier model or version changes, **recalibrate**. A
stronger model may support a larger batch, but that is a hypothesis to test
(§9, scenario 5). It is not an assumed gain.

## 3. Choose a provisional batch within the tighter estimate

1. Take the smaller of the two ranges. With low confidence, use its lower bound.
2. Fill the batch with items in dependency order. Put coupled high-risk items
   alone or in a small batch, and group independent items with proof.
3. State the binding constraint, the evidence, the uncertainty, and what would
   move it (§6).

The batch is **provisional**. It holds until the next review point, not for the
whole epic.

## 4. Compare candidate batches by total cost per accepted increment

For each candidate size `b`, write rough components with sources, or `unknown`:

```text
cost(b) = fixed (setup + review round + expensive eval checkpoint)
        + variable checking (affected graphs, unit subsets: per item)
        + expected repair + repeat + delay (rises faster than b once items couple)
value(b) = accepted useful increments (tickets that pass review AND final confirmation)
compare cost(b) / value(b), and the critical path, not the summed hours
```

- **Fixed costs amortize** over larger batches: an eval round (C11 measured
  $30.50), a review round, per-close bookkeeping (the wave-3 review measured
  about 16k lines of history snapshot per no-op close).
- **Repair and repeat costs grow** with coupling and with the validation-origin
  fault rate. False reds cost runs on innocent tickets (C5: 13 runs, at least
  1,281 s) and voided evals (C10: 12 runs, $2.71).
- **Delay usually dominates elapsed time.** It is waiting on owners and holds,
  not run time (C2 against C1, C12). A smaller batch that waits for the same
  owner gate is not faster.
- **Parallel work counts on the critical path, not as summed hours.** Bug-sweep
  milestone 1 summed 3.09 h of instrument time inside a 2.57 h wall window
  (C1, C3).
- Implementation time is unknown everywhere (C13). Mark it `unknown`. Do not
  divide by it.

**Distinct cadences, each with its own check tier.** Do not run the expensive
check at the cheaper cadence.

| Cadence | Check tier | Plan field |
|---|---|---|
| per change, inside a ticket | cheap local and contract checks: unit subset, doc contracts | `tickets[].validation.repository_unit`, `spec_unit` |
| per ticket that touches a contract | affected graphs and their dependency closure, from `testgraph_bindings` | `tickets[].validation.graphs` |
| integration (wave merge) | the affected graphs once on the merged epic tip | `wave`, `review_policy` |
| review | owner or agent review artifact | `review_policy.cadence`, `.milestones`, `.gate` |
| expensive eval | predeclared, budgeted checkpoints: never per ticket or per deploy | evaluation ticket (`role: evaluation`), `eval_budget` |
| deployment (epic to `main`, release) | the full integrated graph plus one manual acceptance pass (`finalize.md` §2-2c) | finalization |

## 5. Write the decision into existing controls

| Decision | Field(s) |
|---|---|
| Batch size per step | `tickets[].wave`: how many tickets share a wave |
| Serialize coupled or host-sharing items | `tickets[].depends_on`, or split across waves; `conflict_keys` name the shared surface |
| When review happens and whether it blocks | `review_policy.cadence`, `.milestones`, `.gate`, `.walkthrough` |
| What each ticket runs | `tickets[].validation` (graphs, unit subset); one line in `planning_rules.validation_acceleration_rule` |
| Where expensive evals run, and their budget | the evaluation ticket and its `owns_goals`; `eval_budget` |
| The estimate, its evidence and the next review | the review artifact's delivery-velocity section (`validation-review.md`, *Deeper review*) |

A change to these after dispatch is a reschedule. Follow `plan-and-schedule.md`
for schedule revision and assignments.

## 6. Feedback: hold, increase or decrease

At each review point, record these **observations** in the review artifact:

- defects that escaped review or verification, with their severity;
- reds by origin: product or instrument (§6a);
- fix laps per layer, and whether known failures were replaced by new ones;
- recurrence of an attributed family after a fix;
- REACH and BLIND changes on the affected components;
- review time, wait time and run time, each `unknown` where it was not recorded;
- any change of model, toolchain, scope or coupling.

**Overrides come first.** Any one of these decreases the batch or holds it,
however good the aggregate trend looks:

- a high-severity escape (`blocking` or `major`) in a reviewed or verified area;
- repeated validation-origin faults on the same instrument;
- evidence invalidated by a change to code, inputs, graph, model, toolchain or
  environment (§8);
- a scope or coupling change since the estimate;
- a changed reviewer or verifier model or version.

**Decrease** when an override fires, or a `validation-review.md` deep-review
trigger fires: halve the next batch, and put coupled items alone. **Fix or
isolate the instrument** before expanding when the cause is validation-origin.

**Increase** only when two consecutive review points show no override, faithful
instruments on the new items, and converging repairs (at most two laps per
layer). Raise the batch by **one step**: one more wave-sized group, or about 50%
more items, whichever is smaller.

**Otherwise hold.**

These bounds keep one noisy run from moving the batch. A single red attributed
to the instrument goes to the instrument's ledger. It does not move the batch
size.

## 7. Sparse history: an uncertainty-aware cold start

With fewer than two comparable prior review points, or reviewer/verifier
identity `unknown`, both estimates are low-confidence. Start at the lower bound,
review at the first wave (`cadence: wave` or `milestones: [1, …]`), and treat
the first batch as calibration.

**Low detected bug counts with weak coverage do not justify a larger step.** If
BLIND rows or missing red controls cover the affected area, zero catches mean
"not looked at", not "safe". A blind green is found only when somebody looks
(F3).

**Regression is an optional retrospective, not a deliverable.** Fit
defects-per-item or cost against batch size only when you have:

- exposure (items, runs) and severity recorded;
- component, repository, model and time recorded for each point;
- enough points for the claim being made.

Report validation instability and detection effort beside each point. State the
limits: correlation, not cause; batches were chosen, not randomized (selection);
model, host load and owner availability move together (confounding). No script
is written for it.

## 8. Keep final confirmation; record evidence invalidation

Every step-size decision keeps the required final integrated confirmation and
the manual acceptance pass (`finalize.md`). A larger batch never removes them.
Record a piece of evidence as **invalidated**, and do not reuse it, when any of
these change after it was produced:

- the code under test;
- the instrument's inputs or the graph;
- the reviewer or verifier model or version;
- the toolchain (home, pins, runner copy);
- the environment (host, load, disk).

Rerun the affected checks (`validation-review.md`, *A changed contract reruns
every instrument that asserts it*).

## 9. Worked decisions

Each decision gives the selected controls, the expected effect, the observation
that would falsify it, and the next review.

**1. Stable expensive evals: amortize.** Polymarket's `E02-CI-EVAL` reached
14/14 in 934.87 s after the R1-R13 repairs (C27). The BS-17 eval round cost
$30.50 measured, against $66 declared (C11).

- **Controls:** one evaluation ticket after the last contributing wave;
  `eval_budget` set before any billed run; tickets run only affected graphs.
- **Expected effect:** one eval cost spread over every ticket in the batch.
- **Falsified if:** the checkpoint finds a defect that a ticket-local check
  could have caught. Then move that assertion earlier.
- **Next review:** the evaluation ticket's report.

**2. Flaky validation: diagnose and isolate before expanding.** The bug-sweep
probe errored 13 times across 7 innocent tickets (`BS-07-DF-05`, C5). The
skill-manager eval round produced about 12 instrument defects to 4 product
defects (F7).

- **Controls:** hold the batch. Give the instrument fix its own ticket or
  `depends_on` edge ahead of the dependents. Run the instrument on the
  untouched base first, as the §6a control.
- **Expected effect:** reds become attributable, and verification capacity
  recovers.
- **Falsified if:** the instrument is green on the base and red on the branch.
  The red was the product.
- **Next review:** after the instrument fix merges.

**3. Coupled high-risk change.** CDC's isolation gate was red in 14 of 15 runs
on an upstream home fault (`SM402-ISOLATION family`). A memory-recycling defect
surfaced only in the real-repository manual run, behind a gate that was a false
green for it (`M2B-BEAM-02`).

- **Controls:** the coupled items go in a wave of their own, with `depends_on`
  serializing them. Review at `cadence: wave` with `gate: true`. Add one
  intermediate contract assertion per boundary. Reserve manual reach for the
  real-system scenario.
- **Expected effect:** each failure points at one boundary.
- **Falsified if:** repairs keep reopening the other boundary. That is a
  `validation-review.md` split trigger.
- **Next review:** the end of that wave.

**4. Sparse history.** A new repository has no ledger, no REACH and no BLIND.
The model is `unknown`.

- **Controls:** §7 cold start: a small first wave, `milestones: [1, …]`, and
  instruments shown red before they are trusted.
- **Expected effect:** a calibrated second estimate after one review point.
- **Falsified if:** the first wave has an escape that its instruments could not
  have caught. Then lower verification capacity and add coverage.
- **Next review:** wave 1.

**5. Model upgrade.** History recorded no model for almost any row (ESD-01
README). That is the case this decision covers.

- **Controls:** record the new reviewer and verifier identity. Treat earlier
  evidence as a prior. Run one calibration batch **at or below** the previous
  size, with `cadence: wave`. Compare escapes and fix laps per item against the
  prior.
- **Expected effect:** either a measured reason to increase at the next review,
  or none.
- **Falsified if:** escapes or validation faults per item rise on the new model.
  Then decrease, and keep the old size as the ceiling.
- **Next review:** after two review points on the new model, the earliest an
  increase is allowed (§6).
