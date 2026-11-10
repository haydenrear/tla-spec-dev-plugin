# ESD-04 local signals

Two signals from the assignment's `goals`:

- **GOAL-ESD-CAPACITY:** replay the policy on audited episodes using only
  decision-time information, then compare with the holdout outcome.
- **GOAL-ESD-VELOCITY:** a worked cost comparison for the five scenarios that
  cites ESD-01 cost rows or marks inputs unknown.

These are signals, not gates. ESD-06 decides both goals.

Row ids (`C*`, `F*`, `BS-07-DF-05` and so on) refer to
`specs/results/evidence-sized-delivery/ESD-01/`. The policy is
`skills/git-epic-workflow/references/step-sizing.md`, cited below as `§n`.

## Honesty note: the replay is not blind

I wrote the policy after reading ESD-01, and ESD-01 contains these episodes'
outcomes. So the four replayed episodes are **not held out from the author**.
They test whether the policy can be operated on decision-time inputs and
whether its binding constraint points the same way as the outcome. They do not
test the policy's predictive skill.

Two safeguards apply:

1. **No numeric threshold was fitted to an episode.** The policy's only numeric
   bounds are these:
   - two consecutive review points before an increase;
   - an increase of one step, about 50% more items at most;
   - a halving on decrease;
   - a cold start below two comparable review points.

   None of these four episodes ran long enough to exercise them.
2. **Episodes were left untouched for ESD-06's blind replay:**
   - polymarket E02's R1-R13 repair series (C27);
   - effectful-learning epic-10 (C26, `E10-*`);
   - meta-harness finalization (`DEF-110`, C24);
   - CDC #234 (C19).

   I used two of them (C27 and `M2B-BEAM-02`) only as illustrations in
   step-sizing.md §9, not as replays.

## Signal 1: replay on four audited episodes

The columns are:

- **Known then:** only what the records show existed at the decision point.
- **Policy decision:** the two estimates, the binding constraint and the
  controls (§2-§5).
- **Holdout outcome:** what the records say happened next.
- **Read:** whether the outcome agrees with the binding constraint the policy
  chose.

### R1. Bug-sweep kickoff (this plugin, `df48724c`, 2026-11-07 17:09Z)

**Known then.** I checked the following by `git show df48724c:<path>`:

- The plan had 22 tickets, 12 of them in wave 1. Eight tickets named
  `specWorkflow` in `validation.graphs`, four of them in wave 1 (`BS-01`,
  `BS-02`, `BS-07`, `BS-08`).
- `review_policy` was `milestone [3, 6]` with `gate: true`.
- `validation_acceleration_rule`: affected graphs only, resume from the failing
  node, two laps per layer.
- `RP-07-DF-01` was present in `specs/results/deferred_findings_final.yaml`. It
  records that a node in `specWorkflow`, `failure_cleanup_probe`, leaves
  surviving daemons from a nested Gradle build, and that the general half of the
  fix had not landed.
- The specWorkflow baseline passed in 2 m 15 s on a quiet host (C15).
- One 10-core host. The eval lane already had instrument defects on record
  (`EA-DF-15`, `SI-15-DF-05 / EA-DF-08`).
- Reviewer and verifier model: **unknown**.

**Policy decision.**

- **Review capacity: high.** The items are independent bug fixes, and each must
  show red on the base and green on the branch, so each carries its own proof.
  The estimate is 12 or more items per review point. Confidence is low to
  moderate: the prior epics' review artifacts were smaller.
- **Verification capacity: split by tier.** Doc and unit checks are
  unconstrained. Graph checks are not. `specWorkflow` contains a node with an
  open process-ownership defect, and it would run on one host under about a
  dozen concurrent agents. That is the F1 pattern, so the estimate is 1-2
  concurrent specWorkflow tickets per host. Confidence is low: the defect was
  known, but its load sensitivity had not been measured.
- **Binding constraint: verification**, for the specWorkflow tickets.
- **Controls:**
  - keep wave 1 wide for tickets that do not run a graph;
  - chain the four wave-1 specWorkflow tickets with `depends_on`, or spread
    them across waves;
  - before fan-out, run the probe once on the base under concurrent load, as
    the §6a control;
  - declare a single eval checkpoint, with a wheels and home-tier preflight
    (F2, F7).
- **Falsified if:** the probe passes under concurrent load on the base. Then the
  graph constraint was too tight.

**Holdout outcome.**

- The milestone landed in 2 h 34 m wall (C1). All 19 tickets showed red on the
  base and green on the branch.
- `specWorkflow` errored in **13 runs across 7 innocent tickets**, at least
  1,281 s with 6 runs untimed (C5, `BS-07-DF-05`).
  `spec.reference.adapters_resolve` never ran.
- 12 eval runs were voided for environment reasons: 666 s, $2.71 (C10).
- Wait dominated the elapsed time: 29 h between the milestone and the first eval
  case (C12).

**Read: agrees in direction.** The repeat cost landed on the constraint the
policy would have bound. The review side was not where the cost went. Two
things stay unknown:

- whether serializing would have prevented the reds, because the cause is still
  `inferred` and the probe later passed at load 21-30 (F1 counterexamples);
- what serializing would have cost in wall time (untimed).

### R2. Meta-harness concurrent wave dispatch (`DEF-154`)

**Known then.** From the row:

- `spec_unit` took about 70 minutes alone;
- there was one shared host;
- a wave had two concurrent tickets, each running `spec_unit`.

ESD-01 did not record the dispatch revision, so decision-time knowledge comes
from this one row. Model: **unknown**.

**Policy decision.**

- **Review capacity: at least 2 items.** Nothing in the records shows review
  strain.
- **Verification capacity: 1 full `spec_unit` run per host at a time.** The
  shared host is a §2 shared resource. Confidence is moderate: the 70-minute
  time was measured.
- **Binding constraint: verification.**
- **Controls:** `depends_on` between the two tickets, or give each ticket only
  its affected `spec_unit` subset in `tickets[].validation`.
- **Falsified if:** two concurrent runs finish within about twice the single-run
  time.

**Holdout outcome.** `DEF-154` was `major`: about 20 h projected under
contention (C25, inferred). It was promoted with a "serial dispatch rule".

**Read: agrees.** The adopted remedy is the control the policy selects before
dispatch. Caveat: the 20 h is a projection, not a measurement.

### R3. CDC: planning #462 after #394

**Known then.** These records existed when #462 was planned:

- #394's PR and commit timestamps, and its graph runs: 64.9 graph machine hours,
  25.2 h of them red (C19);
- `cdcWorktreeOverlayIsolation` was red in 14 of 15 runs (#234) and 13 of 26
  (#394), attributed to upstream `skill-manager#402`, which was still open
  (`SM402-ISOLATION family`).

The phase split (review 81.5 h against implementation 44.0 h, C17) was
**derivable** from those timestamps. The retrospective that computed it was
written later, so whether anyone had it at decision time is unknown. Model:
**unknown**.

**Policy decision.**

- **Override: repeated validation faults.** The same instrument kept failing
  from an environment origin. That forbids an increase (§6).
- **Verification capacity: reduced** until the isolation gate's reds stop being
  charged to the change.
- **Review capacity: the larger measured cost.** Review plus graphs/merge was
  3.0× implementation (C17, §4 of `cost.md`).
- **Decision: hold the batch size.** Give the isolation gate its own
  instrument-fix dependency, or treat its red as environment-origin under §6a
  until `#402` lands.
- **Falsified if:** reds per batch on that gate fall without an instrument fix.

**Holdout outcome.**

- #462 ran in 11 batches, against #394's 20.
- Summed review hours rose to 87.4 h, with implementation at 36.8 h (C18). Per
  batch, review rose from about 4.1 h to about 7.9 h (derived).
- Graphs plus merge fell from 50.3 h to 6.5 h.
- The isolation gate was still red in 6 of 10 runs (C19, SM402 row).

**Read: UNDECIDED.**

- The repeated fault persisted, which is consistent with "do not increase".
- Batches were roughly half as many with nearly double the review time per
  batch. That is consistent with review binding, but each batch's item count is
  **unknown**, so this cannot be read as a capacity measurement.
- Phase definitions overlap (`cost.md` §4 caveats). The fall in graph hours has
  no recorded cause.

### R4. Skill-manager eval: first round, then wide rounds

**Known then.**

- The first round (2026-09-07, one case, 14 runs, $13.06) produced 4 product
  defects and about 12 instrument defects. Eight consecutive runs died on an
  unset `TMPDIR` (C29; `SM eval round` rows).
- The ledger for 09-07 to 09-10 shows 11 product and 18 instrument defects.
- Whether leaked temp homes (`DEF-OHV-010 / #294`) were known before wide
  round 1: **unknown**.
- Model: **unknown**. The harness was Claude Code 2.1.263.

**Policy decision.**

- **Override: repeated validation faults.** Instrument findings outnumbered
  product findings in the last round, so expanding is out (§9 scenario 2).
- **Verification capacity: small.** The eval lane was the instrument, and it
  was failing.
- **Decision: hold width.** Add a sandbox, disk and toolchain preflight. Run a
  calibration round at about the first round's width, and widen only when a
  round's reds are mostly product.
- **Falsified if:** a wide round's failures are mostly product.

**Holdout outcome.**

- Wide round 1: **27 of 46 runs died on ENOSPC** at $0. The cause was the leaked
  temp homes, a validation-origin fault (F5).
- The wide rounds cost $163.36 in total (C29).

**Read: agrees.** The binding constraint, verification by the eval instrument,
is where the waste landed. The dollar cost of the voided runs was $0. Their
elapsed cost is **unknown**.

### Summary for GOAL-ESD-CAPACITY

| Episode | Both estimates produced from decision-time info? | Batch decision defensible and written as existing controls? | Agrees with holdout? |
|---|---|---|---|
| R1 bug-sweep kickoff | yes (model unknown) | yes: `depends_on`/`wave`, eval checkpoint | direction agrees; magnitude unknown |
| R2 MH `DEF-154` | yes, from one row | yes: `depends_on` or `validation` subset | agrees |
| R3 CDC #462 | partly: the phase split was derivable, not then summarized | yes: hold, plus instrument dependency | UNDECIDED (no item counts) |
| R4 SM eval width | yes (temp-home leak timing unknown) | yes: evaluation scope, preflight | agrees |

**Against `expected_effect`.** All four episodes produced two estimates, a
provisional batch within the tighter one, and a hold/increase/decrease rule.
Three agree with the outcome in direction, and one is UNDECIDED.

The reviewer/verifier model was `unknown` in all four, so the policy's model
recalibration was never exercised by history.

In every agreeing episode, verification bound, not review. This sample is
selected, and I knew the outcomes, so read it as consistency, not evidence of
skill.

## Signal 2: worked cost comparison for the five scenarios

`cost(b)` is fixed + variable + expected repair, repeat and delay (§4). Each
entry cites a row or says `unknown`. Implementation active time is `unknown`
everywhere (C13, C30), so no entry divides by it.

| Scenario | Candidate A | Candidate B | Fixed | Variable / repeat | Delay | Per accepted increment | Choice |
|---|---|---|---|---|---|---|---|
| 1 Stable expensive eval | full eval per ticket (19 tickets) | one predeclared checkpoint | one round $30.50, 5,308 agent-s for 74 cases (C8, C11); A = 19 × $30.50 = $579.50 (**derived, hypothetical**) | B: 12 voided runs, $2.71 (C10); the cost of late-found defects is **unknown** (BS-17: 15 failed cases, 7 explained) | B waits for the checkpoint; the 29 h hold is mostly owner wait (C12) | B: $30.50 / 19 = **$1.61 per accepted ticket** (derived); A: $30.50 | **B** |
| 2 Flaky validation | expand with the flaky probe | fix or isolate the probe first | A: none extra; B: one instrument ticket, duration **unknown** | A: ≥ 1,281 s of repeats over 7 tickets, 6 more runs untimed (C5), plus `adapters_resolve` skipped | B: serial wait for the fix, **unknown** | A's repeats grow with the number of graph-running tickets; B's cost is one-off | **B**, then expand |
| 3 Coupled high-risk | many small batches (CDC #394: 20) | fewer larger batches (#462: 11) | per-batch review **derived**: #394 ≈ 4.1 h, #462 ≈ 7.9 h (C17, C18) | graphs+merge 50.3 h vs 6.5 h (C17, C18); red machine hours 25.2 h vs 20.0 h (C19) | idle 39.2 h vs 56.7 h | **unknown**: item counts per batch not recorded | isolate the coupled boundary in its own wave; the batch count alone cannot be chosen from these rows |
| 4 Sparse history | small calibration wave | full-width first wave | per ticket ≈ 44 s doc contracts + ≈ 20 s spec-unit + ≈ 2 s TLC; ≈ 16k history lines per no-op close (wave-3 review improvement card and hot spot 6) | **unknown** (no history is the premise) | one extra review point; review active time **unknown** (C14) | A pays one review round for calibration; B risks an un-attributable loop, cost **unknown** | **A** |
| 5 Model upgrade | calibration batch at or below the old size | assume the new model allows a larger batch | a matched base vs tip comparison: 8 cases × 3 runs × 2 sides = $10.03 (C9) is the price of one calibration measurement | **unknown**: no audited record names its model (ESD-01 README) | one wave | **unknown** | **A** |

**Against `expected_effect`.** The comparison amortizes fixed costs where the
evidence supports it (scenario 1). It refuses an increase where repeat cost or
missing data dominates (scenarios 2-5). No row claims a speed gain from running
fewer checks: scenario 1's checkpoint is the same eval, run once rather than
per ticket.
