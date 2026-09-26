---
skill-imports:
  - unit: tla-spec-dev
    path: skills/git-issue-workflow/SKILL.md
    reason: "ROLE ticket — the worktree lifecycle, the epic-mode switch, and the PR body that carries `## Skill changes proposed`."
    section: ticket
  - unit: tla-spec-dev
    path: skills/git-epic-workflow/references/deferment.md
    reason: "ROLE epic — the per-ticket inboxes this role absorbs from, and what absorbing one at wave close means."
    section: epic
  - unit: tla-spec-dev
    path: skills/git-epic-workflow/references/human-review.md
    reason: "ROLE review — what the wave artifact carries, and §3.4 is where a proposal's disposition is written back."
    section: review
  - unit: tla-spec-dev
    path: skills/spec-double-2/references/plugin_evals.md
    reason: "ROLE testing — how a case is written, run and kept honest, and the rule for adding a measured correction back into it."
    section: testing
---

# Which agent are you, and where does what you learn go

This plugin works because agents improve it while using it to improve their
projects. That is a **loop**, and it has two legs: you read a path sized to your
job, and you hand back what the path cost you. A reading path with no return leg
is unfinished — an agent that reports friction and never sees the substrate
change stops reporting, and then the plugin only degrades.

So every section below has four parts, always in this order:

1. **How you know you are this role** — from what is already in front of you.
2. **What you read** — in order, and nothing else.
3. **Where you write what you learned** — in the `skill_change` grammar.
4. **The return leg** — the command that shows you what became of it.

**You reach this page by reading.** There is no role marker, no environment
variable, no detection script, and nothing inspects you. Each role's entry point
carries a `skill-imports` edge whose `reason` starts with `ROLE <name>` — that is
the whole routing mechanism, and it is the same documentary idiom the rest of the
plugin already uses.

## How you know which one you are

Read the row whose right-hand column describes what you can already see. Do not
look for a file that names you; none exists.

| you are the… | because in front of you there is |
| --- | --- |
| **ticket agent** | one issue to implement, a feature branch and worktree of your own, and a PR you will open |
| **epic agent** | an epic plan and its schedule; you dispatch tickets, merge waves and own the model — you open no ticket PR |
| **review agent** | a PR, or a wave of them, that you did not write, and a review artifact to produce |
| **testing agent** | an eval case, suite or harness — you are measuring the substrate, not changing a product |

Two agents can be the same process at different moments. Read the section for
what you are doing **now**.

**These four are not `TICKET_ROLES`.** `validate_epic_plan.py` has
`TICKET_ROLES = (implementation, evaluation)`; that is a *plan* vocabulary the
schema validator reads, describing what a scheduled ticket is for. It is not an
agent vocabulary and the two must not be conflated — an evaluation ticket is
still worked by a **ticket** agent.

---

## ticket

### You read

1. `skills/git-issue-workflow/SKILL.md` — the card. Its first section is the
   worktree front door; that is the only part you need before you have a
   checkout.
2. **If the issue carries `<!-- git-epic-workflow:assignment:start -->`**:
   `skills/git-issue-workflow/references/epic-ticket.md`, and stop — it
   overrides the ordinary provisioning path. Otherwise
   `references/provision.md`.
3. The one row of `skills/spec-double-2/SKILL.md`'s **Reference map** that
   matches the task you were given. Not the rest of it.
4. `skills/git-issue-workflow/references/complete.md` — at close-out, for the
   PR body.

### You write

- **`## Skill changes proposed`** in your PR body: one row per blocker you met
  in the substrate — unit, what you hit, and the `skill_change` value. Write
  `none met` when you met none; an absent section is read as absent, which is
  not the same claim.
- **`specs/results/deferred/<YOUR-TICKET-ID>.yaml`** — your own inbox, for
  findings that are not blockers. One file per ticket; never the final ledger.

### The return leg

After the wave merges, the epic agent absorbs your inbox. Your finding is then a
row in the ledger and you can read its fate:

```bash
awk -v id=<YOUR-FINDING-ID> '
  $0 == "  - id: " id {f=1; next}
  f && /^  - id: / {exit}
  f && /^    skill_change:/ {print; found=1; exit}
  END {if (!f) print "no such finding id in the ledger"
       else if (!found) print "that row carries no skill_change -- nobody has been asked"}
' specs/results/deferred_findings_final.yaml
```

**Use this, not `grep -A<n>`.** A ledger row is long — `skill_change` sits 58
lines below `id` on `SI-27-DF-06` — so a small `-A` window silently prints
nothing and a large one runs into the *next* finding's field and answers about
somebody else's. The `awk` is bounded at the next `- id:` and distinguishes all
four outcomes: a verb, a row that was never asked, a row still `proposed`, and
an id that is not there.

`applied(<sha>)` means `git show <sha>` is the change your finding caused. Still
`proposed(...)` means nobody has consumed it yet, and that wave's `review.md`
§3.4 says so in as many words.

---

## epic

### You read

1. `skills/git-epic-workflow/SKILL.md` — the card, then **one** of its
   reference-map rows for the move you are making:
   `references/plan-and-schedule.md` (planning),
   `references/worktree-lifecycle.md` (dispatch),
   `references/human-review.md` (merging a wave),
   `references/finalize.md` (closing the epic).
2. `skills/git-epic-workflow/references/deferment.md` — the per-ticket inboxes
   and what absorbing one means.
3. `skills/spec-double-2/scripts/improvement_ledger.py` — **run it**, do not
   read it. It is the only reader of the `skill_change` field across all four
   record files, and it never refuses.

### You write

You open no ticket PR, so `## Skill changes proposed` is not available to you.
Your two destinations:

- **`specs/results/deferred/EPIC-AGENT.yaml`** — your own inbox, the same shape
  as a ticket's, for friction *you* hit while running the epic. It holds **zero
  rows today**, and exactly **one** has ever been filed in it — `EA-DF-01`, which
  SI-27 absorbed into the ledger. One, against 151 findings filed by everybody
  else: the role that *consumes* findings has almost no record of ever having
  been in the loop, and that is the single most likely way this loop dies.
- **`specs/results/deferred_findings_final.yaml`** — where you absorb everyone
  else's inbox at wave close, each row keeping its fields byte-for-byte and
  gaining a disposition plus `absorbed_from:`. A row lives in exactly one of the
  two places, never both.

### The return leg

Yours is the step everyone else's return leg depends on, so it runs the other
way: **you write the terminal verb on other roles' rows.** Measured over the 151
rows of the ledger — 40 `proposed(...)` against 10 `applied(...)`. The funnel
narrows hardest here, at your step, and a `proposed` row with no disposition is
invisible to the agent that filed it.

Your own findings return by the same absorption as anyone's — the `awk` in
§ ticket, against your own id.

---

## review

### You read

1. `skills/git-epic-workflow/references/human-review.md` — §3 is what the
   artifact carries, and §3.4 is the part that closes other people's loops.
2. The PR bodies of the wave, `## Review input` first — a ticket agent is
   required to have named its own hot spots, its unasked-for decisions, and
   where it would look for bugs in its own change. Start there rather than
   re-deriving it.
3. `skills/spec-double-2/references/blind_dispatch.md` — only when you are
   reviewing work you also wrote.

### You write

- **`<artifact_root>/wave-<n>/review.md`** — the wave artifact. §3.4 is *what
  the epic agent applied, and what it still owes*: one row per
  `## Skill changes proposed` row in the wave, carrying `applied(<sha>)` or
  `declined(<reason>)`. **A proposal with no disposition is a finding that was
  routed rather than consumed**, and saying so is this section's whole job.
- **`specs/results/deferred/REVIEW-AGENT.yaml`** — when what you hit is the
  *substrate* rather than the diff: the review instructions were wrong, the
  artifact template asked for something unobtainable, the PR body gave you no
  way to check a claim. That is a skill change, not a review comment.

### The return leg

Two, because you write in two places:

the `awk` in § ticket, against your own id — and for the dispositions you
recorded on behalf of others,
the next wave's `review.md` §3.4 carries forward anything still owed — so a row
you wrote as `proposed` and see again is a row nobody consumed.

---

## testing

### You read

1. `evals/README.md` — where cases live and the one command that runs them.
2. `skills/spec-double-2/references/plugin_evals.md` — §0 first (the six habits,
   in the order they pay), then only the numbered section for what you are
   doing: §1 what a case can observe, §2 running one, §3 adding a skill and
   placing a fixture, §4 keeping the score honest.
3. `evals/lib/check_graders.py` and `evals/lib/check_cases_parse.py` — **run
   both before billing anything.** Graders compile in a JavaScript regex engine,
   not Python, and an unparseable `case.yaml` drops out of the corpus.

### You write

- **`skills/spec-double-2/references/plugin_evals.md` itself** — this is the one
  role whose primary propagation destination is a *reference page*, because a
  measured fact about the harness is exactly what that page is for. Its
  §*The rule for adding to this file* governs: name the observation that would
  differ if the claim were false, or mark it as a belief. Carry the change in
  your PR's `## Skill changes proposed` as
  `proposed(spec-double-2, <what you measured>)`.
- **`specs/results/deferred/TESTING-AGENT.yaml`** — when you are not opening a
  PR, or the finding is about a unit you are not touching.

### The return leg

The `awk` in § ticket, plus one specific to this role: a case you added
because of a finding is itself the evidence that the finding was consumed.

```bash
git log --oneline --diff-filter=A -- evals/**/<your-case-name>/case.yaml
```

---

## The slots, and why a well-formed value is not enough

The grammar is unchanged and this page does not widen it:

```
skill_change: none
            | proposed(<unit>, <what>)
            | applied(<commit>)
            | declined(<reason>)
```

Four roles are about to write what one role wrote. Before that multiplies, the
**slots** need a documented form, because the grammar constrains arity and
nothing else.

| slot | write | do not write |
| --- | --- | --- |
| `proposed`'s first | a unit name — something `ls skills/` prints, or `tla-spec-dev` for the plugin root | a sentence, a file path, or "no unit change: …" |
| `proposed`'s second | what you hit, free prose | — |
| `applied`'s only | a commit sha, ≥7 hex characters, **and nothing else in the slot** | `this PR`, a file list, a branch name |
| `declined`'s only | a reason, free prose | a sha — a reason is not meant to be checkable |

**Measured on the 151-row ledger, 2026-09-26.** Of the 10 `applied(...)` rows,
**3** begin with a commit sha (`4caab479`, `d09d8326`, `f212cbe3`); the other
seven name "this PR", a file list or a branch, and a reader a month later can
resolve none of them. One more, `applied(test-graph, …)`, *does* resolve under
`git cat-file -t` — but only because this repository has a git **remote** named
`test-graph`, so the token silently resolves to `refs/remotes/test-graph/main`, a
commit with nothing to do with the finding.

**That is the lesson, and it is why the rule above is about shape and not about
resolvability**: an unconstrained slot can accidentally look valid. Checking
`git cat-file -t` alone would score that row a pass.

The same drift reaches the unit slot: `proposed(the defect is in the issue body
and the epic plan, …)` and `proposed(no unit change: this is repository content,
…)` put prose where a unit name goes, and the ledger's `.unit` property reads
that prose as the unit name.

And the grammar has no delimiter rule, so a value can carry two verbs:
`SI-19-DF-01` reads `none applied; proposed(test-graph, …)`. The reader calls
that `malformed` and reports it — correctly — but it was written by someone who
believed they had said two things.

**Nothing here refuses.** `GOAL-no-new-gates` is live: this is a documented form
and a one-line command a reader can run, not a validator, a linter or a check.
`improvement_ledger.py` has no exit-code path and gains none.

## What this page is not

- It is **not** a place to restate what each unit does. That is each card's own
  job and its reference map's; this page routes to them and never duplicates
  them.
- It does **not** detect anything. If you found it by being told which role you
  are, that is the routing working, not a mechanism.
- It adds **no unit**. A twelfth unit would add a description to what loads every
  session, which is the quantity progressive disclosure exists to reduce.
