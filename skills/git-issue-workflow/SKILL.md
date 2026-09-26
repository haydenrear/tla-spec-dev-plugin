---
name: git-issue-workflow
description: >-
  Use when handed a GitHub issue to implement, or asked to start, complete or
  close out a ticket — including one assigned from a shared epic. Read before
  touching the repo. Trigger on "implement this issue", "complete this ticket",
  "work this epic ticket", "run the evaluation ticket", "open the MR", or
  receiving an agent-tagged PR.
skill-imports:
  - unit: tla-spec-dev
    path: skills/spec-double-2/references/agent_roles.md
    reason: "ROLE ticket — you are the ticket agent. This is your reading path and, at the end of it, where you hand back what you learned: the PR's `## Skill changes proposed` and your per-ticket inbox."
    section: ticket
  - unit: tla-spec-dev
    path: skills/git-issue/SKILL.md
    reason: This skill executes the worktree/spec/close-out moves that a git-issue work order names; the issue body is the input to provisioning.
  - unit: tla-spec-dev
    path: skills/git-epic-workflow/references/goals-and-evaluation.md
    reason: Source of truth for goal field names and semantics — goal kinds, contribution kinds, baselines, and the evaluation-ticket contract this skill consumes from the assignment's `goals:` block.
  - unit: tla-spec-dev
    path: skills/spec-double-2/SKILL.md
    reason: The spec workflow — open/close ticket, spec-unit-tests, current→desired promotion — runs through the tla-spec-dev CLI this skill installs.
  - unit: tla-spec-dev
    path: skills/test-graph/SKILL.md
    reason: The validation loop runs named test_graph graphs (incl. the spec graph) via the test-graph scripts and its smart failure loop.
  - unit: deploy-helm
    path: SKILL.md
    reason: Tickets touching deployable surfaces validate against deploy-helm environments inside the test graph.
  - unit: tla-spec-dev
    path: skills/skill-manager/references/workflows.md
    reason: This skill is installed and synced as a skill-manager unit.
---

# git-issue-workflow

The **implementer side** of `git-issue`. A work order names the moves — worktree,
spec workflow, regression graphs, close-out; this skill runs them. An epic
assignment stops at a PR into its shared epic branch; an ordinary ticket runs end
to end, and an integration repo fans out to every constituent.

## The one command: `wt`

First and last thing every ticket does. Ask the shell, do not look around:

```bash
command -v skt    # prints a path -> use `skt ticket new|close <ticket>` and stop looking
```

`skt` is a **plugin**, so it is never under a home's `skills/` — an agent
listing that directory concludes it is absent from a home that has it. Its whole
surface: `skt ticket new <ticket> [<base>] [--base <ref>] [--path <dir>]` and
`skt ticket close <ticket>`. Only when `command -v skt` prints nothing, resolve
`wt` by path (`references/worktrees.md`).

**`cd` to the path `new` printed** — `<parent>/<repo>-<ticket>`, not
`../wt-<ticket>`, so do not guess it. **Do not substitute `git worktree add`**:
it produces a worktree with no Skill Manager home, and an agent launched there
writes the operator's global `~/.skill-manager`. Do not substitute `git worktree
remove` either — it deletes the home, and every unpushed skill edit in it,
without a word.

A failure is three lines and the second runs **as printed** (`fix:`). What each
provisioning exit means — **3**, **7**, **1**, **79** — is
`references/worktrees.md` § *The exit codes `wt new` refuses with*. Never stash,
commit or discard someone's edits to get past exit 1, and never upgrade
skill-manager to get past 79.

## Reaching a by-hand route is itself a finding

`wt`/`skt ticket` is the front door. If you ended up provisioning by hand,
**say which of the five miss cases you were in** and file it against the unit
owning the door — a by-hand route that works silently is how a broken front door
survives. The five cases and what each one owes the PR are in
`references/provision.md` § *The five miss cases*.

## A blocker you met is a change you propose

Whenever something in the substrate blocked you — this skill, a script, the CLI,
a validator, an unrunnable instruction — the PR body carries a `## Skill changes
proposed` section: one row per blocker you actually met, three columns (the unit,
what you hit, the proposed change as a diff or the commit that applied it).

`none met` is legitimate and common, and it is written rather than left out. Run
nothing new for it — every row already happened while you did the ticket. Apply
the change where the unit is a file in this repository and inside your conflict
keys; otherwise put the diff in the row. Being blocked from fixing it is still a
row. Nothing blocks on it. Worked examples: `references/complete.md` §5a for an
ordinary ticket, `references/epic-ticket.md` §7 for an epic ticket.

## Select epic mode before any provisioning

Read the complete issue body before choosing a branch, worktree, repository mode
or spec command. Search for `<!-- git-epic-workflow:assignment:start -->`.

- **Marker present:** epic ticket mode. Follow `references/epic-ticket.md`
  instead of Role 2, Role 3, the ordinary close-out, or integration fan-out. The
  assignment's declared branch, worktree, ticket, validation, promotion and PR
  base are authoritative, even when the checkout also has integration markers. A
  `ticket.role` of `evaluation` decides goals rather than producing a behavioral
  delta — read `references/goal-signal.md` too. Where the plan carries
  `planning_rules.model_ownership_rule` the **epic owns the model**: you run
  neither `open ticket` nor `close ticket` nor `--accept-new`, you move `current`
  toward `desired`, correct `desired` only in small ways, and return structural
  changes in the PR.
- **Marker absent:** continue with the PLAIN/INTEGRATION detection below.

Do not scaffold a workflow, create a default-branch worktree, or run an
integration provisioning script until this check is complete.

## Three load-bearing rules for ordinary and integration tickets

1. **Operate specs and the test graph only from the parent.** When the ticket
   spans sub-repos, run the TLA+ workflow and the `test_graph` graphs **once, at
   the integration parent**. Constituents re-run their own loops after fan-out.
2. **Same branch name everywhere** — one ticket id drives `feature/<ticket>` on
   the parent and every constituent.
3. **A ticket lives in a worktree, never the primary checkout.**

## Your Skill Manager home IS the worktree's

Every ticket worktree has its own gitignored `.skill-manager`. A skill edit you
make in it is in **no git diff**, reaches no PR, and is deleted with the
directory. Run `home close-out` before the worktree goes, never `home sync` into
a home you do not own, and never write a real home by hand.
`references/skill-homes.md` has the tiers, the scripts, the CLI pin and the exit
ladder.

## Is this an integration repo?

```bash
test -f INTEGRATION.md && test -f integration.toml && echo INTEGRATION || echo PLAIN
```

**PLAIN** → one worktree, one feature branch, one PR via `gh`. **INTEGRATION** →
one parent worktree spanning constituents, the spec/graph loop at the parent
only, then fan-out. The worktree command is the same in both; this fork decides
spec/graph scope and whether there is a fan-out.

## Ordinary close-out sequence

An unmarked ticket is done when these five moves have happened, **in order** — no
exceptions, no leaving a PR "ready for someone to merge later". Epic tickets do
not run this sequence. Each step in full, including the INTEGRATION variant, is
`references/complete.md`.

1. **Close every open spec ticket, then the workflow** with the `tla-spec-dev`
   CLI — each ticket still open in `ticket_plan.yaml` by id, not just the last —
   then `close_tickets.py` to promote.
2. **Commit and push** implementation, spec changes and evidence together.
3. **Rebase-merge the PR into `main` with `gh`** — land it yourself. A declared
   goal also puts `## Goal contribution` in the PR body.
4. **Close out the worktree's home, THEN remove the worktree, then sync the root.**
   The gate runs *before* the removal — after it there is nothing left to save.
   `"$WT" close <ticket>` does both and removes only on a clean verdict; two
   commands on separate lines would run the removal whatever the gate returned.
   Exit 0 is the only "proceed".
5. **Close the GitHub issue with `gh`** — confirm a `Closes #<n>` merge did it,
   do not assume.

**INTEGRATION repos** skip step 3's `gh pr merge` — land it with `git merge
--no-ff` and `verify.sh` — but still run 1, 2, 4 and 5 at the parent, then fan
out (`references/integration-fanout.md`).

## Role map

**Before the task map, the role map.** You are the **ticket agent** — the one
role that already had a way to hand something back, in this PR's
`## Skill changes proposed` and in `specs/results/deferred/<ticket>.yaml`. What
the other three roles do, and the one command that shows you what the epic agent
did with your finding, are in the spec-double-2 skill's
`references/agent_roles.md` § ticket. Nothing detects your role; you arrive by
reading.

## Reference map

| You are… | Read |
|---|---|
| Assigned one ticket from a shared epic workflow | `references/epic-ticket.md` |
| Kicking off a ticket (Role 2: provisioning, index-base pinning, opening the workflow) | `references/provision.md` |
| Completing a ticket (Role 3), or reading a `wt close` exit | `references/complete.md` |
| Running the green loop — at most two laps per layer, then record what stayed red | `references/validation-loop.md` |
| Fanning out to sub-repos | `references/integration-fanout.md` |
| Handed an agent-tagged PR | `references/agent-tag-pr.md` |
| A ticket that declares a goal, or whose slice **is** the measurement | `references/goal-signal.md` |
| Resolving `wt`, or reading a `wt new` refusal | `references/worktrees.md` |
| Working on, or debugging, a per-checkout Skill Manager home | `references/skill-homes.md` |

## Boundaries

- This skill **executes** a ticket; it does not author the issue. Issue creation,
  the References section and the spec-required decision are `git-issue`'s.
- It does not create or amend an epic assignment. In epic mode it consumes the
  assignment, stops only when the PR base or branch would be wrong, and otherwise
  proceeds on the plan's values, listing any mismatch in the PR. `SKILL_GATES=off`
  lets `wt new` proceed from a dirty parent tree and forces the tla-spec-dev
  close gates; `wt close` still takes an explicit `--force`.
- It does not reimplement the spec, test-graph or fan-out mechanics — it
  **sequences** them.
- The **worktree lifecycle it does own**: `new-change.sh`, `close-change.sh`,
  `bootstrap-home.sh`, `agent-home.sh` and `lib.sh`. The front door `wt` is
  `skt`'s and holds no policy. The dependency runs specialized → general:
  `git-integration-repo` → `git-issue-workflow` → `git-issue`; why these moved
  out of `git-integration-repo` is `references/worktrees.md`.
- It never runs per-constituent specs/graphs during a ticket.
- It does not invent goals, baselines or targets, and never edits one to match a
  result. **It does not tune to a metric**: the local signal is measured,
  recorded and reported — never gated on, never re-run for a better number, never
  a reason to widen scope or weaken a REQUIRED validation entry. A goal
  unreachable from this slice is a deferred finding for the plan owner.
