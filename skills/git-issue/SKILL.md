---
name: git-issue
description: >-
  Use when creating a tracker issue an agent will pick up and implement, via the
  `gh` CLI. Drives a discovery-first work order: scan first, then name the
  measurable goal and the instrument that decides it. Trigger on "file an
  issue", "create a ticket", "open a GitHub issue".
skill-imports:
  - unit: tla-spec-dev
    path: skills/spec-double-2/SKILL.md
    reason: When an issue needs a spec workflow, it drives Internal.tla/External.tla spec doubles and spec unit tests via the tla-spec-dev CLI.
  - unit: tla-spec-dev
    path: skills/test-graph/SKILL.md
    reason: The issue's regression section names test_graph graphs to run for regression, including tla-spec-dev spec-graph integrations.
  - unit: deploy-helm
    path: SKILL.md
    reason: Issues that touch deployable surfaces reference deploy-helm environments for validation.
  - unit: tla-spec-dev
    path: skills/skill-manager/references/workflows.md
    reason: This skill is installed and synced as a skill-manager unit.
---

# git-issue

Create issues another agent can pick up and implement end-to-end without
re-discovering the repository. An issue produced here is a **work order**: it
carries the discovery you already did, points the implementer at a
worktree/branch, names the measurable outcome, decides whether the change needs a
TLA+ spec workflow, and lists exactly which tests close it out.

An issue that says what it changes but not what should be measurably better
hands the implementer no result to aim at, and produces a PR whose only claim is
"tests pass". So goal linkage is part of every work order, not only epic ones: a
metric with a named instrument, never an adjective. An issue with no measurable
outcome says so explicitly (`N/A: <reason>`). The canonical contract for goal
kinds, baselines, contribution kinds and the evaluation-ticket role is
`<git-epic-workflow-skill>/references/goals-and-evaluation.md`.

**An issue names a rubric; it never copies one.** Write which rubric, which
version, how many judges, and where the evidence lands, then link it. Do not
paste its dimensions, anchors or scoring rules: the rubric's own repository
versions those and runs checks over them, and a copy in a tracker has nothing
behind it. Measured, not hypothetical — a charter here restated a table of judged
results and two rows were wrong before anyone caught them.

An issue may instead be one scheduled slice of an existing epic. In that mode
keep the ordinary sections and add the marker-delimited assignment from
`references/epic-assignment.md`, which takes precedence over ordinary
default-branch worktree, PR-target and issue-close instructions.

The core workflow is **tracker-agnostic**: GitHub via `gh` is the only wired
adapter (`references/github-gh.md`). For another tracker, swap only the
create/comment/close commands.

## The six moves

1. **Discover before you write.** Never open an issue from the title alone. Scan
   the repo to locate the code, specs, tests and docs the change will touch —
   **and the measurement surface** that could decide whether it worked:
   benchmarks, eval datasets and scorers, perf-marked suites, end-to-end graphs,
   recorded baselines. `references/discovery.md`.
2. **Capture the goal and what decides it.** Ask the user what should be
   measurably better, which instrument decides it — a command, or a judged
   procedure with its rubric — what it reports today, and which threshold counts
   as success (or that there deliberately is none). Then state this issue's
   relation (`direct`, `enabling`, `guard`) with the expected effect and a cheap
   local signal; a judged instrument is rarely the right one, because its noise
   can swamp one ticket's movement. Never invent a metric, baseline or target the
   user did not agree to. In epic mode these are copied from the plan.
3. **Write the issue with a References section** — the discovery output as a
   *starting point*, concrete files, symbols, specs and docs, each as
   `path:line` where possible. `references/github-gh.md`.
4. **Instruct a worktree + feature branch.** Embed **one command** that creates
   the worktree and its own Skill Manager home together, spelled as a path that
   resolves without the reader looking anything up, plus what to do about that
   home: a skill edit inside it is in no diff, and teardown is gated. Never
   instruct a bare `git worktree add`. An epic assignment instead names the exact
   worktree and branch created from the epic branch, and is the one case that
   branches by hand. `references/worktree-branch.md`,
   `references/epic-assignment.md`.
5. **Decide the spec workflow.** If the change alters observable/internal
   state-machine behavior, the issue names the Internal.tla / External.tla edits,
   the test-graph and unit-test adapter updates, and tells the implementer to
   open the workflow with **spec-double-compiler + tla-spec-dev** at
   branch-creation time. For an epic the owner scaffolds one shared workflow and
   each issue opens exactly its one planned ticket — and where the plan reserves
   the model to the epic agent, the issue says the ticket agent opens and closes
   no spec ticket at all. `references/spec-workflow.md`.
6. **Spell out close-out.** Which test graphs run for regression, attaching their
   reports to the spec ticket, closing it, running spec and unit tests,
   **reporting the goal contribution** and **any substrate blocker as a proposed
   skill change** in the PR body, then commit and push. An epic work order
   supplies exact validation commands and evidence paths, targets the epic
   branch, and stops for external review (`references/regression-close.md`).

## Before you create the issue

Run discovery and answer these, because they change what the body must contain:

- **What does this touch?** The file/symbol list becomes the References section.
- **What should be measurably better, and what decides it?** Becomes
  `## Goals & evaluation`. Ask the user; do not derive a target from the
  codebase. `N/A: <reason>` is a recorded decision, not a skipped question.
- **Does it change a named model element?** Decides the spec-workflow section.
  Default NOT REQUIRED; mark REQUIRED only when you can name the `Internal.tla`
  action, variable or invariant that changes.
- **What could it regress?** The affected test graphs become the close-out list.
- **Ordinary issue or epic assignment?** Epic mode is valid only after the owner
  pushed the epic branch, scaffolded the workflow once, and planned this issue's
  one stable spec ticket. Do not scaffold a second workflow.

## One issue, or an epic?

The goal question is also the routing question. One issue carries one goal it
decides itself or contributes to. When the request is several slices that only
make sense together, route to **`git-epic-workflow`**. Signals: the outcome is
only measurable after several slices land; one slice builds the harness or
baseline the others are judged by; the instrument must run on an integrated
branch; or `## Goals & evaluation` would name a "decided by" ticket that does not
exist yet. Do not let one issue silently become an unscheduled epic — a goal
nothing is scheduled to measure is a goal nobody will decide.

## The issue body

The full body template and the rules for filling `## Goals & evaluation` — what
each bullet means, why a target needs both halves, the two shapes that
legitimately are not a threshold, and how epic mode renders the section from the
assignment — are `references/issue-template.md`. Fill every section; omit one
only when it is genuinely N/A, and say so explicitly rather than deleting it,
because the implementer relies on the shape.

For epic mode, retain every standard section and insert the rendered
marker-delimited block from `references/epic-assignment.md` between Summary and
`## Goals & evaluation`, so the order is Summary → assignment → Goals &
evaluation → References.

## Operating order

1. Confirm `gh` is authenticated and the repo is right (`references/github-gh.md`).
2. Discover (`references/discovery.md`) → References, measurement inventory,
   regression scope.
3. Settle the goal: metric, deciding instrument, today's value, success
   threshold, contribution and local signal — asked of the user for an ordinary
   issue, copied from the assignment in epic mode, or `N/A: <reason>`. If the
   outcome needs several slices, route to `git-epic-workflow`.
4. Decide the spec workflow (`references/spec-workflow.md`). If the owner
   supplied a planned ticket, select epic mode and validate its assignment.
5. Render the template, create the issue with `gh issue create`, capture the
   number/URL. For a new epic issue, use that number to finalize the branch and
   worktree fields, then edit the body with the complete assignment. For an
   existing issue, preserve its body and replace only the bounded assignment
   region.
6. For an ordinary required spec workflow, note that the implementer opens the
   in-repo ticket on branch creation. For an epic, verify the issue maps to one
   existing planned ticket.

## Boundaries

- This skill **creates and structures** issues; it does not implement them.
- It does not run test graphs or the spec workflow, and does not close issues —
  it names them; the mechanics live in `test-graph`, `spec-double-compiler` and
  `deploy-helm`, and close-out is the implementer's.
- **It does not invent goals, baselines or targets.** Ask; if there is no
  measurable outcome, record `N/A: <reason>` rather than manufacturing a metric
  later reported as if agreed. In epic mode values are copied from the plan. It
  does not run the harness either; a goal with an unmeasured baseline says so.
- It does not schedule an epic's goals or its evaluation ticket, and does not
  create an epic branch or scaffold a shared workflow. The owner supplies those
  before this skill writes an epic assignment.
- An epic ticket PR uses `Refs #<issue>`, targets the declared epic branch, and
  stops for external review. It does not close the issue or merge into either
  branch: the epic-owner agent merges at wave close, and issue close is
  finalization's.

## Reference map

| Task | Read |
| --- | --- |
| Scan the repo and build the measurement inventory | `references/discovery.md` |
| The issue body template and filling `## Goals & evaluation` | `references/issue-template.md` |
| Creating, labelling and closing the issue with `gh` | `references/github-gh.md` |
| Author one shared-workflow ticket in an epic | `references/epic-assignment.md` |
| Decide REQUIRED vs NOT REQUIRED, and what to embed | `references/spec-workflow.md` |
| The worktree/branch instruction to embed | `references/worktree-branch.md` |
| The regression and close-out checklist | `references/regression-close.md` |
