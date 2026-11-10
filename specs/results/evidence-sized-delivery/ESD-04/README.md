# ESD-04: model-conditioned review and verification step sizing

Ticket #238 (epic #234, `evidence-sized-delivery`), wave 4, based on `847aa4a9`
(the epic tip, which contains merged ESD-01..03 and the waves 1-3 review). This
ticket changes instructions and evidence only. It adds no script, controller,
schema, validator or gate.

## What changed

Line counts are from `git diff --numstat` against `847aa4a9`.

| File | +/- | What |
|---|---|---|
| `skills/git-epic-workflow/references/step-sizing.md` | +301 / -0 | New page, in nine sections: (1) starting-revision summary; (2) separate review and verification capacity; (3) provisional batch within the tighter estimate; (4) cost per accepted increment, with a cadence/check-tier table; (5) the decision mapped onto existing plan fields; (6) observations, overrides and hold/increase/decrease with bounded steps; (7) cold start and optional regression with its limits; (8) final confirmation and evidence invalidation; (9) five worked decisions. |
| `skills/git-epic-workflow/references/validation-review.md` | +21 / -0 | A short "Step size: two capacities, one batch" section that links to the new page. |
| `skills/git-epic-workflow/references/plan-and-schedule.md` | +13 / -0 | One paragraph each in §3a (size waves from the two estimates and record them in plan fields) and §4b (cadence is a step-size control; evals keep their own checkpoint). Nothing outside §3a/§4b changed. |
| `skills/git-epic-workflow/references/goals-and-evaluation.md` | +4 / -0 | A pointer, plus "velocity is never claimed from fewer checks". |
| `specs/results/deferred/ESD-04.yaml` | +96 / -0 | Three deferred findings (budget 5), all routed to ESD-05. |
| `specs/results/evidence-sized-delivery/ESD-04/*` | — | This README, `local-signal.md`, and the validation outputs. |

## Decisions

- **One new page.** The worked decisions and the policy live in `step-sizing.md`.
  `validation-review.md` grows by 21 lines (150 → 171), so its existing contract
  sections are untouched.
- **Capacity unit = scope item.** A scope item is one behavior change at one
  boundary. Each pair of items that shares state, a host or an interface counts
  as one more item. There is no LOC or ticket-count rule.
- **Decisions go to existing fields only:** `wave`, `depends_on`,
  `tickets[].validation`, `planning_rules.validation_acceleration_rule` (prose,
  with the bug-sweep and this epic as precedent), `review_policy`, the
  evaluation ticket, and `eval_budget` (present in this epic's plan). Rationale
  goes in the review artifact's delivery-velocity section. No new plan key.
- **Bounded update.** Increase only after two consecutive clean review points,
  by one step of at most about 50% more items. Decrease by halving on any
  override. Otherwise hold. A single instrument red does not move the batch.

## Model result

**No-op.** `specs/current`, `specs/desired_program_model` and
`specs/program_model` are unchanged. The ticket edits prose and evidence and
changes no action, variable or invariant. Under `bug_attribution.md` §7d, prose
guidance is a no-op. The epic agent owns the spec close.

## Validation

| Entry | Result | File |
|---|---|---|
| `validation.repository_unit` | 407 passed, 1 skipped | `repository-unit.txt` |
| `validation.spec_unit` | 2 failed, 54 passed: the same two known base failures (`baseline/spec-unit.txt`), none new | `spec-unit.txt` |
| tlc, graphs | N/A per the assignment | — |
