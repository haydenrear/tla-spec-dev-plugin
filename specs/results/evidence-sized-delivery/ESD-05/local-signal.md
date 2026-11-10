# ESD-05 local signal: one finding walked through every role, and the reading cost

`GOAL-ESD-UPTAKE` local signal: *walk one finding through planning, ticket PR,
review disposition and next-epic reuse; record the exact entry-point links
followed and the added line count per role path.*
`expected_effect`: *each role reaches the bounded ESD-02/03/04 guidance from
its existing entry point; incremental mandatory reading kept small and
measured.*

The walk was done by reading, at this branch's tip, the way each role would. It
was not run by independent agents. ESD-06 runs the blind version (base vs tip
eval cases). This is a signal, not a gate.

## 1. The finding

`ESD-03-DF-01` (major, pending): `spec.workflow.cleanup` deletes
`Path(ctx.get("spec.workflow.repo", "repoPath") or "")`. With no published
`repoPath` that is `Path(".")`, the node's working directory, which is
`test_graph/` (`test_graph/sources/spec_workflow_cleanup.py:29-32`; ledger
`specs/results/evidence-sized-delivery/deferred-ledger.yaml`, row
`ESD-03-DF-01`). The wave-3 review anchored it to `UNMODELED/test-graph-nodes`
(`review/wave-3/review.md` §4) and recommended promoting it outside the epic.

It was chosen because it crosses every role: it is a graph-node defect (the
ESD-03 checklist), a validation-origin finding (ESD-02 §4.3, §6a, §7d), and it
lowers verification capacity for any batch that runs `specWorkflow` (ESD-04).

## 2. The walk

"Added text" counts only lines this ticket added on that role's path, so it
measures what ESD-05 cost, not the canonical sections the role then reads.

| step | role | entry point and the links followed | what the role does with `ESD-03-DF-01` | added text it needed |
| --- | --- | --- | --- | --- |
| 1 | epic: planning (next epic that touches `specWorkflow`) | `git-epic-workflow/SKILL.md` reference map → `plan-and-schedule.md` §3 *bounded evidence slice* → spec-double-2 `agent_roles.md` § *Evidence routing*, row *epic: planning* → `bug_attribution.md` §7d (anchor `UNMODELED/test-graph-nodes`), `graph-architecture-review.md` §E (cleanup path from an absent value) and the previous epic's *Next epic's starting estimate* (`finalize.md` §2c) | names `spec.workflow.cleanup` as a **dangerous validation boundary**; verification capacity for any batch running `specWorkflow` is lowered until the guard lands (`step-sizing.md` §1 *validation-origin faults*); writes the boundary into the touching ticket's *Evidence slice* bullet | `plan-and-schedule.md` +9 (§3 paragraph), +6 (§7 estimate lines); routing table 21; SKILL.md map +2 rows |
| 2 | ticket (e.g. the promoted fix, or any ticket whose matrix runs `specWorkflow`) | issue body → rendered assignment bullet **Evidence slice** (`epic-ticket.md`) → `graph-architecture-review.md` *A graph change is a product change* (5 questions) → `bug_attribution.md` §4.3 for the record | reads the one row instead of the 394-line ledger; if it edits the node, answers *effect scope* and *recovery behavior* in `## Review input`; files any red it meets with origin `test_graph node` (validation), channel, effect kept apart; reports that `specWorkflow` cannot be a valid targeted rerun from a checkout without `repoPath`, rather than dropping it | assignment block +13 (evidence slice 9, delivery line 4); `agent_roles.md` § ticket +2 |
| 3 | review (the wave holding that ticket) | `agent_roles.md` § review step 4 → row *review* → `human-review.md` §3.1 rank 6, §3.3 *validation-specific bugs* → `graph-architecture-review.md` §E, §G | lists the node as a hot spot beside the product change; checks the PR's evidence came from this tip's home and runner copy; asks whether a green `specWorkflow` exercised the absent-`repoPath` path at all (it does not: a green there is not evidence the guard holds); states whether review coverage supported the batch | `human-review.md` ≈+11 (§3.1, §3.3); `agent_roles.md` § review +2 |
| 4 | epic: wave owner | row *epic: wave owner* → `human-review.md` §3.4 *recommendations that remain* (now with owner and disposition) and §3.5 *Delivery velocity and step size* → `step-sizing.md` §6 | records the recommendation as `promote → new issue → owner: epic owner → disposition: scheduled as <issue>` instead of an ownerless row; in §3.5 charges any red it caused to validation repair, not product; an unguarded destructive finalizer is a "repeated validation-origin fault" candidate, so hold or decrease the batch (§6 overrides) | `human-review.md` ≈+10 (§3.4 owner/disposition, §3.5 block) |
| 5 | epic: finalizer → next epic | row *epic: finalizer* → `finalize.md` §2c *Next epic's starting estimate* (+ §5 bullet) | writes: component `test_graph nodes` / repo `tla-spec-dev-plugin` / model `<as recorded>`: verification estimate reduced while `ESD-03-DF-01` is open; uncertainty: not reproduced (reproducing deletes the checkout). The next epic's planning (step 1) reads exactly this block | `finalize.md` +11 |

**Result.** Every role reached the finding and the canonical section it needed
from its existing entry point, in at most three links, and none of them loaded
the whole ledger or a whole canonical page. The loop closes: step 5's output is
step 1's input, through records that already existed (the epic PR, the review
artifact, the assignment). No role, approval round, script or artifact was added.

**What the walk exposed that ESD-05 did not fix.** Before this ticket, steps 1,
4 and 5 had no instruction at all: the wave-3 review left `ESD-03-DF-01` with a
recommended disposition and "owner decision pending" and no owner field, and no
record carried a starting estimate between epics. Step 2 depends on the epic
owner actually filling the *Evidence slice*; a `none found` there is honest, a
missing bullet is not checkable by anything (deliberately: no validator). The
ticket-side copy of the PR-body contract in `git-issue-workflow` does not carry
the delivery line (`ESD-05-DF-01`).

## 3. Reading burden per role path

Mandatory path = the files each role's *You read* list in `agent_roles.md`
sends it to, plus its own section of that page and the new routing section.
Measured by `wc -l` on `git show <rev>:<path>` at main `a1ff56cf`, the epic
base `54241b36`, and this branch's tip. The commands are in `README.md`.

| role path | files counted | main `a1ff56cf` | epic base `54241b36` | tip | Δ vs base | Δ % |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| ticket (epic) | git-issue-workflow `SKILL.md`, rendered assignment block, git-issue-workflow `epic-ticket.md`, `agent_roles` § ticket + routing | 957 | 957 | 993 | +36 | +3.8% |
| ticket (ordinary) | git-issue-workflow `SKILL.md`, `provision.md`, `complete.md`, issue template, `agent_roles` § ticket + routing | 960 | 960 | 993 | +33 | +3.4% |
| epic: planning | git-epic-workflow `SKILL.md`, `plan-and-schedule.md`, `goals-and-evaluation.md`, `agent_roles` § epic + routing | 1376 | 1393 | 1437 | +44 | +3.2% |
| review | `human-review.md`, `agent_roles` § review + routing | 701 | 701 | 745 | +44 | +6.3% |
| epic: wave owner | git-epic-workflow `SKILL.md`, `human-review.md`, `deferment.md`, `agent_roles` § epic + routing | 1193 | 1193 | 1242 | +49 | +4.1% |
| epic: finalizer | git-epic-workflow `SKILL.md`, `finalize.md`, `deferment.md`, `agent_roles` § epic + routing | 1044 | 1044 | 1083 | +39 | +3.7% |

The routing section (21 lines) is counted in every row although a role reads
it only when its trigger fires, so the deltas are an upper bound.

**On-trigger reads** (not mandatory; read only when the row's trigger fires).
Before ESD-05 these were reachable only from `plan-and-schedule.md` §3a/§4b,
`validation-review.md` and test-graph `SKILL.md`. After, each role is sent to
one section, never the whole page:

| canonical section | lines | whole page | sent there by |
| --- | ---: | ---: | --- |
| `graph-architecture-review.md` *A graph change is a product change* | 27 | 399 | ticket, review |
| `graph-architecture-review.md` §E (one checklist section, typical) | 23 | 399 | review |
| `bug_attribution.md` §4.3 | 32 | 943 | ticket |
| `bug_attribution.md` §7d | 56 | 943 | planning |
| `step-sizing.md` §1–§5 | 138 | 301 | planning |
| `step-sizing.md` §6 | 37 | 301 | wave owner |
| `step-sizing.md` §8 | 16 | 301 | ticket |

**Duplicated prose replaced.** None removed in this ticket. The one duplicate
found that would shorten a role path (the ticket-side copy of the PR-body
contract, ~50 lines) is outside the conflict keys and is deferred as
`ESD-05-DF-01`. The new text points at canonical sections instead of restating
them: the review artifact's *Delivery velocity and step size* block reuses the
section `validation-review.md` *Deeper review* already required, rather than
adding a second one.

## 4. Against `expected_effect`

- *Each role reaches the bounded guidance from its existing entry point*:
  **met in the walk** (5 of 5 roles; at most 3 links; no whole-corpus load).
  Not yet measured blind: ESD-06.
- *Incremental mandatory reading kept small and measured*: **measured**,
  +33 to +49 lines per role path (+3.2% to +6.3%) over the epic base. No numeric
  threshold was set (owner instruction, report-only).
