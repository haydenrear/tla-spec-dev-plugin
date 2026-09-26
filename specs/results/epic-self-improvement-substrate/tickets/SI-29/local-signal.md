# SI-29 — local signals, one per goal

Base `59370837de8e25353f10ea146e9db4e9361d1cda`. Every figure here is measured
in the ticket worktree and the command that produced it is quoted beside it.
Verdicts on the goals themselves belong to SI-23 and SI-08; this file records
what this ticket's slice measured.

---

## GOAL-progressive-disclosure — both clauses met, by routing

Instrument, pinned by the epic owner in SI-09 and reproduced here before use:

```
bodies:        awk 'BEGIN{fm=0} /^---$/{fm++; next} fm>=2' skills/<u>/SKILL.md | wc -w
descriptions:  the YAML-parsed `description` scalar of skills/<u>/SKILL.md, .split()
```

**Control.** At `7ba79bee` — the commit the issue's baseline names — the
instrument reproduces the issue's table exactly: 1005 description words, 6 of 11
bodies over 1500, and every named figure (skt 2242, git-epic-workflow 1820,
unit-authoring 1797, git-issue-workflow 1788, skill-manager 1648, spec-double-2
1567). The method was pinned against that before it was used on anything.

| | base `59370837` | this branch | target | verdict |
|---|---|---|---|---|
| descriptions, 11 units | **1005** | **592** | ≤ 600 | **MET**, 8 words of headroom |
| card bodies over 1500 | **6 of 11** | **0 of 11** | 0 | **MET** |
| body total | 17738 | 15370 | — | −2368 |

Per card:

| card | desc base → now | body base → now |
|---|---|---|
| discovery | 60 → 59 | 996 → 996 |
| git-epic-workflow | 71 → 44 | 1820 → 1498 |
| git-integration-repo | 75 → 38 | 1349 → 1349 |
| git-issue | 82 → 47 | 1499 → 1499 |
| git-issue-workflow | 95 → 55 | 1788 → 1497 |
| plugin-repository | 86 → 39 | 1472 → 1472 |
| skill-manager | 104 → 77 | 1648 → 1481 |
| skt | 200 → 80 | 2470 → 1460 |
| spec-double-2 | 73 → 49 | 1567 → 1484 |
| test-graph | 51 → 40 | 1332 → 1332 |
| unit-authoring | 108 → 64 | 1797 → 1332 |
| **total** | **1005 → 592** | **17738 → 15370** |

**The issue's baseline is `7ba79bee`, not this ticket's base.** They differ on
exactly one figure: `skt`'s body is 2242 there and **2470** at `59370837`. Every
number above is measured at this ticket's own base, and both readings are in
`transcripts/step-01-descriptions.txt`.

### Why this is routing and not trimming, stated as what is checkable

Every clause removed from a card was appended to a reference page the card now
points at, in the same commit: twelve relocations, listed in
`manual-verification.md` §6. The check is that the phrase still exists in the
repository and the card names the page — not that the total went down.

### Activation vocabulary — added at review, and it found two real regressions

The first pass hit 588 words and **lost activation vocabulary**, which the epic
agent measured at review. A description is what the harness matches an intent
against, so a word count that improves while activation degrades is a worse
description, not a better one. Measured per unit, base vs now — a `Use when` /
`Trigger on` clause, and every quoted user phrase:

| unit | base → now | use-when | trigger-on | quoted user phrases |
|---|---|---|---|---|
| discovery | 60 → 59 | kept | kept | 5 → **5** |
| git-epic-workflow | 71 → 44 | kept | kept | 5 → **5** |
| git-integration-repo | 75 → 38 | kept | — | *(0; base's one quote is the defined term)* |
| git-issue | 82 → 47 | kept | kept | 3 → **3** |
| git-issue-workflow | 95 → 55 | kept | kept | 5 → **5** |
| plugin-repository | 86 → 39 | kept | — | *(0; base's one quote is the defined term)* |
| skill-manager | 104 → **77** | **RESTORED** | **ADDED** | 0 → **5** |
| skt | 200 → **80** | kept | kept | 10 → **10** |
| spec-double-2 | 73 → 49 | kept | — | 0 → 0 |
| test-graph | 51 → 40 | — | kept | 4 → **4** |
| unit-authoring | 108 → **64** | **RESTORED** | — | 0 → 0 |

The two regressions that mattered:

- **`skill-manager` at 44 words had no activation condition at all.** It had lost
  *"Use when the user asks to find, add, remove, inspect, bind, unbind,
  instantiate, sync, upgrade, or resolve one of those surfaces"* and carried no
  trigger phrases, so nothing in it said *when* to invoke the skill. Restored, and
  it now carries **five** quoted trigger phrases where base carried none — the one
  unit whose activation surface is better than it was.
- **`skt` had lost five of its ten quoted phrases** (the review flagged four; the
  fifth is *"please sync with root to publish changes globally"*). Sweep, retire
  and disk-reclaim intents had vanished — the verbs an epic agent needs at exactly
  the moment nobody remembers they exist. **All ten restored.**

`unit-authoring` also lost `Use when`; judged worth restoring and restored.

**Where the words came from — redistribution, not addition.** Every word funding
the restorations came from *capability* prose the reference pages already carry,
never from an activation clause: the definition sentences in
`git-integration-repo` (−9 from the first pass) and `plugin-repository` (−9),
`git-issue`'s three-clause work-order list (−13), `spec-double-2`'s role-map
clause (−6, keeping `ROLE MAP` and all four role names because that is the
cold-session entry point), `test-graph`'s six-verb capability list (−9),
`git-epic-workflow`'s duplicated assignment-marker clause (−7), and
`git-issue-workflow`'s "Owns the worktree lifecycle" (−4).

**Does the 600 target hold both clauses? YES — at 592, with 8 words spare.** The
first redistribution landed at 612, over target; compressing three further
capability lists brought it to 592 with every activation clause and all 42 quoted
user phrases intact. So the target did *not* have to be relaxed, and the epic
agent's offer to take 615 to the owner is not needed. The honest floor is not
588: that number was only reachable by deleting activation vocabulary, and **588
was a worse description set than 592**.

**What is NOT evidenced: that 592 holds.** SI-09 reached exactly 600 and three
nested units put it back to 1005. This ticket adds a *place* for the prose that
regrew it (each role's reading path) and writes the convention where the next
author reads it (`skills/unit-authoring/references/skills.md`, SI-29-DF-05).
Whether the next unit's author uses it is unmeasured, and an eval on it would be
measuring my own intent rather than the substrate.

---

## GOAL-findings-become-changes — four of four roles now have a destination

Baseline: **one** of four roles had a channel; `EPIC-AGENT.yaml` held **zero**
rows; the strings `review agent` and `testing agent` appeared **nowhere** under
`skills/` (`grep -rn`, both empty).

| role | reading path | propagation destination | return leg |
|---|---|---|---|
| ticket | `git-issue-workflow/SKILL.md` → `references/epic-ticket.md` → `complete.md` | PR `## Skill changes proposed` + `specs/results/deferred/<ticket>.yaml` | the bounded `awk` over the ledger, then `git show <sha>` |
| epic | `git-epic-workflow/SKILL.md` → one reference-map row → `deferment.md` → run `improvement_ledger.py` | `specs/results/deferred/EPIC-AGENT.yaml`; absorbs others into the ledger | it *writes* the terminal verb; its own rows return by the same `awk` |
| review | `git-epic-workflow/references/human-review.md` §3 → PR `## Review input` → `blind_dispatch.md` | wave `review.md` §3.4 for others' dispositions; `deferred/REVIEW-AGENT.yaml` for substrate findings | the `awk`, plus §3.4 carried forward next wave |
| testing | `evals/README.md` → `plugin_evals.md` §0 then one numbered section → `check_graders.py`/`check_cases_parse.py` | `plugin_evals.md` itself (preferred); `deferred/TESTING-AGENT.yaml` (fallback) | the `awk`, plus `git log --diff-filter=A` on the case it added |

Each path is reached by **one** `skill-imports` edge whose `reason` begins
`ROLE <name>`. All 140 `skill-imports` edges in the repository resolve (0
dangling); the only three YAML-frontmatter failures are the deliberately-broken
`w-giw-exit6-is-unreadable-frontmatter` fixture and its two plugin caches
(`SI-22-DF-01`, open).

### The measurement that shaped the design

Over the 151 rows of `specs/results/deferred_findings_final.yaml`:

| | rows |
|---|---|
| filed | 151 |
| parseable `skill_change` | **71** (47%) |
| no `skill_change` field at all | 79 |
| malformed | 1 (`SI-19-DF-01`, two verbs in one value) |
| `proposed(...)` | 40 |
| `applied(...)` | 10 |
| `declined(...)` | 9 |
| `none` | 12 |

Of the 10 `applied(...)`: **3** begin with a commit sha; **4** resolve under
`git cat-file -t`, the extra one only because a git *remote* named `test-graph`
exists. A check on resolvability scores that row a pass and points a reader at an
unrelated commit — which is why the documented form constrains **shape**.

**First evidence the form is writable**: all five rows of
`specs/results/deferred/SI-29.yaml` satisfy it, checked with
`improvement_ledger.py`'s own parser plus a unit-name and sha-shape assert, and
both `applied()` shas resolve to commits in this repository.

---

## GOAL-evals-earned — fifth rung

`f8a3994e` (the by-hand record of all four roles, **0 case.yaml**) →
`b929e07c` (the five cases). `git merge-base --is-ancestor f8a3994e b929e07c`
succeeds. The four rungs before: `8e362bbb→eefe3aa8`, `70549f90→7daa8e18`,
`bec1934b→c96de147`, `679f76f1→3dc106fb`.

The walk found a defect in this ticket's own deliverable before any case encoded
it — the return-leg command as first written could not reach the field it was
for. `manual-verification.md` §4.

---

## GOAL-no-new-gates — held

`improvement_ledger.py` exits **0** and gained no `sys.exit`. `BACKLOGS` is
unchanged, so the two new inboxes are deliberately *not* read as a population —
`EPIC-AGENT.yaml`'s own header warns that adding
`specs/results/deferred/*.yaml` to it double-counts every absorbed id. No
validator, linter or check was added: the documented slot form is prose plus a
one-line command a reader may run.

---

## GOAL-evals-one-command — see `eval-scores.md`

Five cases under `evals/spec-double-2/w-roles-*`, selectable as one glob
(`evals/run.sh --case 'w-roles-*'`). Scores, run counts and spread are in
`eval-scores.md`; they are deliberately not in this file or in
`manual-verification.md`.
