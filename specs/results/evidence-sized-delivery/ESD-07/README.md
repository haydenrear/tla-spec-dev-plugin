# ESD-07 — batch-favoring step sizing, advisory checks, pre-run graph review (#270)

Owner final-review amendment to epic #234 (schedule revision 2). Prose only: no script, gate, field or
schema. No-op model result.

## What changed

| Page | Change |
| --- | --- |
| `git-epic-workflow/references/step-sizing.md` | *Nothing on this page blocks* (override once with `--force` / `SKILL_GATES=off`, record why; never edit a plan status to pass a refusal). The default leans to batching. §3: upper bound for independent items with proof; irreducible groups go in whole; instrument repairs batch with dependent work; batch unit defined; tie-break favors batching, up to the review estimate when failures attribute per item. §6: only product escapes halve; invalidation, scope or model change hold; instrument faults never shrink the batch; increase after **one** clean review, by up to double. New §6a: each recurring validation family gets a `skill_change`, an instrument ticket, or a written decline. §7: cold start keeps the §3 batch and reviews early. §9.2 rewritten (fix the instrument inside the batch; E2 evidence). §9.5: model change holds, never shrinks. §9 marked as non-held-out. |
| `test-graph/references/graph-architecture-review.md` | *Nothing on this page blocks*. Scope widened to every instrument (graders, sandboxes, suites, CLIs, resolvers, CI), answering the 0-of-27 non-node gap by scope. Question → checklist section map. New *pre-run review*: at planning, apply the five questions to unchanged nodes and instruments the affected graphs execute. Each flag is fixed ahead (major: instrument ticket in the same wave, ahead in promotion order, without holding the product batch), routed around (Evidence slice), or accepted with a reason. New G0: resuming from the failed node is the default loop; a full fresh run needs a stated reason, and the final containing-graph run is kept. |
| `git-epic-workflow/references/validation-review.md` | Short review: resume from the failed node by default. Step-size summary aligned with the new §3/§6. Sparse history gets an early review, not a small batch. |
| `git-epic-workflow/references/plan-and-schedule.md` | §3: how to find the previous epic's starting estimate (`gh pr list --state merged --search …`), and to run the pre-run review and schedule its fix-ahead tickets. §3a: the cold start keeps the §3 batch. |
| `spec-double-2/references/agent_roles.md` | MAN-06: the review row uses full paths and the real `human-review.md` section names, and points at the five questions. Planning row: pre-run review, upper-bound default, fix-ahead tickets. Wave-owner row: decrease only on product escapes; §6a dispositions. |

## Local signals (not a goal verdict)

**GOAL-ESD-CAPACITY.** Re-deriving the four held-out decisions (`../goals/GOAL-ESD-CAPACITY/holdout-replay.md`) by the amended rules alone gives these results:

| Episode | Recorded outcome | Before (ESD-06 replay) | After (amended rules) |
| --- | --- | --- | --- |
| E1 polymarket R1+R2 | batch of 2 worked | agree (lenient), strict reading over-serializes | agree: upper bound; irreducible group goes in whole |
| E2 effectful-learning rev72 | batch of 3 instrument fixes worked | **disagree** (hold at 1) | agree: instrument repairs batch; per-site attribution allows up to the review estimate (4–6) |
| E3 meta-harness finalization | one bundled repair; split unnecessary | partly | agree: instrument fix in the same batch |
| E4 CDC MS-017 | bundle of 3; BEAM-02 recurred | partly | partly (unchanged): BEAM-02 is coupled with no faithful instrument, so it goes alone and the rest batch |

Result: 1 agree, 2 partly, 1 disagree → 3 agree, 1 partly. **This is calibration, not validation.** The
rules were amended after reading these outcomes, and two episodes are also §9 examples. No blind
re-measurement was run: the epic's eval run budget is 46/48 spent, and ESD-06 (the evaluation ticket)
measured the tip before this amendment. Under `step-sizing.md` §8, the CAPACITY and ARCH verdicts are
**invalidated for the sections this ticket changed**. A blind held-out replay on new episodes is the
next measurement.

**GOAL-ESD-ARCH.** Of the 27 hold-out defects outside a graph node
(`../goals/GOAL-ESD-ARCH/holdout-application.md`), the page's stated scope covered 0 before and covers
27 after. That is a scope count, not a flag rate. Whether a reader then flags them is unmeasured.

## Validation

| Entry | Result |
| --- | --- |
| `repository_unit` (doc-contract subset) | 407 passed, 1 skipped (same as base): `repository-unit.txt` |
| `spec_unit`, TLC | run by the epic agent at close (no model delta) |

## Deferred findings

None new. This ticket consumes #264 items 1 (step-sizing ambiguities) and 2 (graph-review reach) and
MAN-06. #264 keeps MAN-01 (docs half) and MAN-03.
