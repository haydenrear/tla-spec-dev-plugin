# SI-29 — all four agent roles walked by hand, before any eval case existed

Measured 2026-09-26 in the ticket worktree
`/Users/hayde/IdeaProjects/wt-391-role-routed-disclosure`, branched from
`epic/self-improvement-substrate` at
`59370837de8e25353f10ea146e9db4e9361d1cda`. Every block below is captured
output, in `transcripts/`, not a summary written afterwards.

This file is committed **before** the eval cases, and that order is the
deliverable. `GOAL-evals-earned` says no eval is written for behaviour nobody
has watched work, and the two commit shas are the check
(`git merge-base --is-ancestor <record> <first case>`). **This commit contains
no `case.yaml`.** It is the fifth rung of the ladder; the four before it are
`8e362bbb→eefe3aa8`, `70549f90→7daa8e18`, `bec1934b→c96de147`,
`679f76f1→3dc106fb`.

The subject is new: the four rungs before this one walked a **product** (graph
scaffold, `skt`, the `tla-spec-dev` CLI, the brew→skill-manager→plugin chain).
This one walks a **reading path** — four of them — so "walked by hand" means
something different and it is worth saying what. It means: starting from what
each role can already see, following each hop the routing names, and asking at
every hop whether the next thing exists and says what the previous thing
promised. Where a hop did not deliver, §4 says so.

---

## 0. What is under review, and the one thing it must not be

The change routes disclosure by **agent role** using nothing but
`skill-imports:` entries whose `reason` begins `ROLE <name>`. That is the
constraint the owner set and it is the one an eval cannot check for me, so it is
stated first and checked in §5: **no marker file, no environment variable, no
role-detection code, no hook change, no twelfth unit.**

The walk uses only what an agent has: the text of the files, `grep`, `awk`,
`git`. Nothing was run that inspects an agent or tells it what it is.

---

## 1. What a cold session sees before it opens anything (`step-01`, `step-05`)

The session-start cost, by the epic owner's pinned instrument
(`awk 'BEGIN{fm=0} /^---$/{fm++; next} fm>=2' <card> | wc -w` for bodies, the
YAML-parsed `description` scalar for descriptions):

| | base `59370837` | this branch | target |
|---|---|---|---|
| descriptions, 11 units | **1005** | **592** | ≤ 600 |
| card bodies over 1500 | **6 of 11** | **0 of 11** | 0 |
| body total | 17738 | 15370 | — |

(Descriptions read **588** when this record was first written. The epic agent's
review measured activation vocabulary, found that `skill-manager` had lost its
activation condition entirely and `skt` five of its ten quoted trigger phrases,
and the restoration brought the total to **592** — still under target, with every
activation clause and all 42 quoted user phrases at or above base. `local-signal.md`
carries the per-unit audit. 588 was the *worse* number: it was only reachable by
deleting vocabulary a harness matches on.)

Per card, body, base → now: skt 2470→1430, unit-authoring 1797→1332,
git-epic-workflow 1820→1498, git-issue-workflow 1788→1497, skill-manager
1648→1481, spec-double-2 1567→1484, and the five already under budget unchanged
but for spec-double-2's own new Role map.

**The issue's baseline is `7ba79bee`, not this ticket's base**, and the two
differ on exactly one figure: `skt`'s body is **2242** at `7ba79bee` and
**2470** at `59370837`. The instrument reproduces the issue's table exactly at
`7ba79bee` — 1005, 6 of 11, and every named figure — which is how the method was
pinned before it was used. Every number above is measured at this ticket's own
base.

**And the reduction is routing, not trimming, in the only sense I can
evidence**: every clause removed from a card was appended to a reference page
that the card now points at, in the same commit. §6 lists each relocation and
where it landed. I cannot evidence the stronger claim — that it *holds* against
the next nested unit — and §7 says why not.

### The cold entry, by hand

Of 592 description words, **one** description names the role map
(`spec-double-2`). A session that has read nothing else can get from there to a
four-row table and from the table to its own section. That is the whole
mechanism and it is one hop deep on purpose.

---

## 2. The four walks (`step-03`)

Each role, four hops: the entry point it already has → the `ROLE` edge → the
page → the section → the destination the section names.

| role | entry point it already has | `ROLE` edge? | § reached | destination | exists? |
|---|---|---|---|---|---|
| ticket | `skills/git-issue-workflow/SKILL.md` | 1 | `## ticket` :65 | PR `## Skill changes proposed` + `specs/results/deferred/<ticket>.yaml` | yes |
| epic | `skills/git-epic-workflow/SKILL.md` | 1 | `## epic` :105 | `specs/results/deferred/EPIC-AGENT.yaml` | yes, 33 lines, **0 findings** |
| review | `skills/git-epic-workflow/references/human-review.md` | 1 | `## review` :148 | `specs/results/deferred/REVIEW-AGENT.yaml` + wave `review.md` §3.4 | yes, new |
| testing | `skills/spec-double-2/references/plugin_evals.md` | 1 | `## testing` :~190 | `references/plugin_evals.md` itself + `specs/results/deferred/TESTING-AGENT.yaml` | yes, new |

Every hop resolved. `skill-imports` validation requires each target path to
exist inside the unit; swept over all **140** edges in the repository, **0
dangle** (`step-02`). Three files fail YAML frontmatter parsing and all three
are the same deliberately-broken eval fixture
(`w-giw-exit6-is-unreadable-frontmatter`, plus its two plugin-cache copies) —
that invalid frontmatter *is* the fixture, and it is `SI-22-DF-01`.

**The two entry points that had no frontmatter at all** — `human-review.md` and
`plugin_evals.md` — gained some. That is how the review and testing roles, which
were **not named as roles anywhere in the plugin** before this ticket (`grep -rn
"review agent"` and `"testing agent"` over `skills/` returned **nothing**),
acquired an entry point without a new unit or a new idiom.

---

## 3. The return leg, walked against real findings (`step-04`)

This is the half that decides whether the loop is a loop, so it was walked
against the actual ledger rather than described.

### It closes, for the findings that were consumed

```
$ awk -v id=SI-27-DF-06 '…' specs/results/deferred_findings_final.yaml
    skill_change: "applied(d09d8326)"
$ git show --stat --oneline d09d8326
d09d8326 checkers read this repository, not copies of it — and index once
 skills/spec-double-2/scripts/check_citations.py | 62 ++++++++++++++++++++++---
```

A ticket agent that filed `SI-27-DF-06` can reach the commit its finding caused.
That is the return leg working, end to end, on real data.

### It says "not consumed" honestly

40 of 151 rows are still `proposed(...)`. For each of those the command answers
`proposed(...)`, which is a real answer and not a silence.

### `applied(x)` is mostly not checkable — and the naive check is WORSE than useless

| | count |
|---|---|
| `applied(...)` rows | 10 |
| whose argument **begins with a commit sha** | **3** (`4caab479`, `d09d8326`, `f212cbe3`) |
| which **resolve** under `git cat-file -t` | **4** |

The extra one is `EA-DF-18`, `applied(test-graph, match a node stem …)`. Its
first token resolves — to `refs/remotes/test-graph/main` — because **this
repository has a git remote named `test-graph`**. It is a commit with nothing to
do with the finding.

**So a check that tests resolvability scores that row a PASS.** That is why the
documented form in `agent_roles.md` is about the **shape** of the slot and not
about whether git can resolve it, and it is the sharpest thing in this record.

The work order's addendum says **2** of ten name something checkable; the
measured figure is **3**. The addendum counted only arguments that are *nothing
but* a sha, and `SI-16-DF-02` is `applied(4caab479 -- the false comment at
evals/run.sh:34 is replaced …)` — a sha followed by prose, which a
first-token read resolves. Flagged rather than quietly adopted.

---

## 4. Where a hop did NOT deliver — the defect this walk found in its own deliverable

The first version of the return-leg command, written before it was walked, was:

```bash
grep -n -A8 '<FINDING-ID>' specs/results/deferred_findings_final.yaml
```

**It does not work.** On `SI-27-DF-06`, `id` is at line 7081 and `skill_change`
at line **7139** — 58 lines apart. An `-A8` window prints nothing and reads as
"there is no disposition". Widening it is worse: an unbounded window runs past
the end of the row and prints the **next finding's** `skill_change`, answering
confidently about somebody else's finding. `CM-01-DF-01` — one of the 79 rows
carrying no `skill_change` at all — is exactly the input that produces that
false answer.

Replaced with a bounded `awk` that stops at the next `- id:` and distinguishes
four outcomes, each verified by hand:

| input | answer |
|---|---|
| `SI-27-DF-06` | `skill_change: "applied(d09d8326)"` |
| `SI-04-DF-01` | `skill_change: proposed(spec-double-2, …)` |
| `CM-01-DF-01` (no field) | `that row carries no skill_change -- nobody has been asked` |
| `SI-99-DF-99` (absent) | `no such finding id in the ledger` |

**This is what the ladder is for.** A documented return leg that silently
answers "nothing happened" for every finding would have shipped, and the eval
written for it would have encoded the broken command. The record is committed
before the cases precisely so the cases encode what was watched working, and
what was watched working here is the second command, not the first.

---

## 5. The constraint, checked rather than asserted

| forbidden | swept | result |
|---|---|---|
| a script that detects a role | `git show --stat` of the implementation commit | 0 files added under `scripts/`, `*.py`, `*.sh` |
| an environment variable | `grep -rn 'ROLE'` over the change | only `skill-imports` `reason:` prose |
| a marker file | the two files added under `specs/results/deferred/` | YAML inboxes with `findings: []`, written by hand by a role, read by no code |
| a hook change | `evals/hooks/hooks.json`, `hooks/` | untouched |
| a twelfth unit | `ls skills/` | **11**, unchanged |
| a new gate | `improvement_ledger.py` | **rc=0**, no `sys.exit` added; `BACKLOGS` unchanged, so the two new inboxes are *not* read as a population — EPIC-AGENT.yaml's own standing warning |

The new inboxes are deliberately **not** wired into `improvement_ledger.py`.
`EPIC-AGENT.yaml`'s header states that adding `specs/results/deferred/*.yaml` to
`BACKLOGS` double-counts every absorbed id, and `SI-08-DF-11` proposes exactly
that. Honouring the warning was a decision, not an omission.

---

## 6. What was relocated, and to where

Routing means the words moved, not that they went away.

| from | words | to |
|---|---|---|
| `skt` §check/staleness ×3 | 760 | `skills/skt/references/check-and-staleness.md` (new) |
| `skt` §sweep | 392 | `skills/skt/references/worktree-sweep.md` (new) |
| `unit-authoring` §Shipping Edits | 565 | `references/bindings-and-sync.md` |
| `git-epic-workflow` rules 3, 12 | — | `references/plan-and-schedule.md` |
| `git-epic-workflow` rule 5 | — | `references/epic-ticket.md` |
| `git-epic-workflow` rules 10, 11, 14 | — | `references/worktree-lifecycle.md` |
| `git-epic-workflow` rule 13 | — | `references/human-review.md` |
| `git-issue-workflow` §by-hand route | 213 | `references/provision.md` |
| `git-issue-workflow` §homes | 167 | `references/skill-homes.md` |
| `git-issue-workflow` §lifecycle rationale | — | `references/worktrees.md` |
| `skill-manager` §MCP and CLI detail | 276 | `references/cli.md` |
| `spec-double-2` §TLC discovery pass | ~110 | `references/architecture_tractability.md` |

Each card keeps the rule and the pointer; each reference page carries the
reasons under a heading that says it was moved by SI-29.

---

## 7. What this record is allowed to be used for

- The cases in the next commit encode §2 (a cold reader reaching its own role's
  section and naming its destination) and §3 (a role stating a **checkable**
  propagation). Nothing else here is encoded.
- §3's `applied(x)` measurement and §4's broken command are **findings**, not
  cases. Turning each into a case on the day it was found is the volume the
  ladder exists to avoid.
- **No `claude plugin eval` score is in this record.** Nothing here is evidence
  about the suite's numbers; the scores are measured after this commit and
  reported in `eval-scores.md`.
- **The reduction in §1 is not evidence that it holds.** SI-09 reached exactly
  600 and the next nested unit put it back to 1005. What this ticket adds
  against that is a *place* for role-specific prose other than the description,
  so the next unit's description can be a trigger. Whether the next author uses
  it is unmeasured, and an eval here would be measuring my own intent.

## 8. Unexercised, with the reason

- **An agent actually behaving as a review or testing agent in a real wave** —
  neither role exists as a dispatched identity in this epic today; the walk
  establishes the path resolves, and the eval cases in the next commit are the
  first time a reader is put on it.
- **Writing a row into `REVIEW-AGENT.yaml` or `TESTING-AGENT.yaml`** — both ship
  empty on purpose. Filling one to demonstrate the schema would put a fabricated
  finding in the record, which is the opposite of the point.
- **`open ticket`, `close ticket`, `close_tickets.py`, `--accept-new`** —
  forbidden by `planning_rules.model_ownership_rule`. Not run in any form,
  including in a fixture.
- **`skill-manager install` of this branch** — the installer walks
  `evals/**/fixture/**/SKILL.md` and exits 11 on the deliberately-broken
  fixtures (`SI-22-DF-01`, still open). Running it would measure that known
  defect again and nothing about this ticket.
