# Closing out self-improvement-substrate

**Written 2026-09-26 by the epic agent.** Epic #333. Successor filed as **#393**.

**29 of 29 tickets delivered across 23 waves.** Evaluation B (SI-23) reported
**six MET, four NOT MET, four UNDECIDED, two split by ref**.

---

## What closed cleanly

**The three-substrate gap is closed.** This was Evaluation B's deepest finding —
that the epic measured a different artifact than it shipped:

| | before | after |
| --- | --- | --- |
| committed | `e7a20e3d` | `e7a20e3d` |
| released (`main`) | `ac5f7491` (−47) | **`e7a20e3d`** |
| loaded (both homes) | `a3761e30` (−86) | **`e7a20e3d`** |

Cutover `ac5f7491..e7a20e3d` under owner authorisation, then
`skill-manager sync tla-spec-dev --git-latest` in the project home and the root
home. Both now load the tip and carry `bootstrap-floor.toml` and the `ROLE`
routing — **neither of which existed in anything anyone ran** until this step.

A side effect worth recording: **both syncs exited 0.** When `#388` was closed,
the sync path was *inferred* to be fixed by v0.28.2 rather than measured,
because the standing rule forbids syncing a home without say-so. It is now
measured.

**Repository state at close.** Suite 10 failed / 1742 passed / 6 skipped, failure
names identical to the epic baseline throughout. All five graphs green:
specWorkflow 74/74, cliWorkflow 41/41, effectProviderExamples 8/8,
sktSurface 318/318, sktHooks 167/167 — the first of those only after a
regression the epic agent introduced the same day and Evaluation B caught.

---

## What did NOT close, and will not be forced

**The shared spec workflow cannot be promoted, and `specs/desired_program_model`
cannot be removed, without fabricating history.**

`close_tickets.py --dry-run` refuses, and its reason is structural rather than
incidental:

```
ticket SI-08 must have exactly one successful close receipt under
  specs/.history/self-improvement-substrate, found 0
… the same for SI-09, SI-13..SI-29 — nineteen tickets
```

`specs/.history/self-improvement-substrate/` **does not exist**. Every previous
epic in this repository carries one `ticket-NNN-<ID>/manifest.json` per ticket —
`cut-the-apparatus-epic` has ten. This epic has none.

**Why, precisely.** `planning_rules.model_ownership_rule` reversed the normal
division: ticket agents were forbidden from running `open ticket` / `close
ticket`, and **the epic agent was to scaffold each ticket's `desired` and close
the spec ticket at wave merge**. The first half was honoured — no ticket PR
touched `specs/` outside `results/`, verified across 14 PRs with zero
violations. **The second half was never exercised.** Most tickets had
`desired_actions: []` and no model delta, so no workspace was scaffolded and no
close was run, and nothing in the loop reported the omission for 23 waves.

This is the same gap Evaluation B recorded against `GOAL-epic-owns-the-model`
clause 1 — no `.tla` change across waves 19–22 while five findings accumulated
in `UNMODELED/install-pipeline`. **The epic agent owned the model and largely
did not exercise that ownership.** The missing receipts are the same fact
measured from the other side.

**The model itself is converged**, which is what makes this a bookkeeping
failure rather than a modelling one: `TlaSpecDevCli.tla` and `MC.cfg` are
**byte-identical** across `current/`, `desired_program_model/` and
`program_model/`. Only `spec_manifest.yaml` and `README.md` differ, plus the two
planning files the close script ignores by design.

**Three ways to finish, and the epic agent chose none of them unilaterally:**

1. **Retroactively run the spec workflow per ticket.** Produces 29 receipts
   describing closes that never happened. **Refused** — it is inventing the
   history the close script exists to verify.
2. **`--accept-new`.** `references/finalize.md` §4 says to run the close
   "without `--accept-new`", and it is on the epic agent's standing
   prohibition list. It also would not help: the script still requires the
   tickets to be closed, which still requires the receipts.
3. **The owner decides this epic closes by cutover**, which the plan already
   half-says: *"The epic branch does NOT merge into tla-spec-dev's default
   branch… The epic's result reaches users through tla-spec-dev-plugin instead,
   by cutover once the epic closes."* The cutover is done. Under this reading
   the spec-workflow promotion is a `tla-spec-dev` repository operation that
   this epic never entered, and `specs/desired_program_model` stays until a
   ticket in the successor epic promotes it properly.

**OPTION 3 WAS TAKEN, by the owner, 2026-09-26.** Recorded as
`planning_rules.close_mode: cutover` with the reasoning beside it, so the
contradiction this plan carried all epic is now written down as a decision
rather than left as two rules that were both true.

And the owner named the real gap rather than accepting the workaround:

> It sounds like we are missing a knob here… In the future it should be obvious
> what to do here. Maybe it should just go through?

Filed as **#394** and added to #393 as section H. Two defects: an epic cannot
declare how it closes, and — the sharper one — **the receipt check asks for one
receipt per DELIVERED ticket when it should ask for one per ticket that actually
OPENED a spec workspace.** A receipt for a ticket with `desired_actions: []` and
no workspace certifies nothing. Scoped that way, this epic passes honestly: the
set is empty, the model is converged, no fabrication and no `--accept-new`. And
a ticket that did open a workspace and skipped its close is still caught.

`close_mode` is in this plan today as a field with **no reader**. Making it real
is #394's work.
`finalize.md` is explicit that accepted state is never hand-edited on an epic
branch, so deleting `specs/desired_program_model` by hand — the literal request —
is the one thing that must not happen quietly.

---

## Carried to #393

The successor issue carries the whole picture: the three-substrate discipline
that this close-out partly discharged, the defective goal, the instruments that
could not decide, the judged round SI-08 asked for and SI-23 did not run, the
packaging question in **#392**, and the open findings **#384**, **#385**,
**#387**.

**This close-out itself is now the first entry**: an epic whose own close path
requires artifacts its own design never produced.

---

## The honest summary

The substrate works. The suite never regressed across 29 tickets, the graphs are
green, one plugin provides eleven units, and the eval ladder's ordering is
provable in git rather than asserted.

What repeatedly failed was the **measurement and the bookkeeping around it** —
and the most useful thing this epic produced is the evidence of that, most of it
found by the agents it dispatched, pointed at the agent that dispatched them.
