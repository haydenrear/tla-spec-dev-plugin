# The issue body template, and filling `## Goals & evaluation`

Moved here from `SKILL.md` by SI-09 (progressive disclosure). The card carries
the six moves and the rule that every section is filled or explicitly `N/A`;
this page is the template itself and the per-bullet rules for the goals section.

Fill every section. Omit a section only when it is genuinely N/A, and say so
explicitly rather than deleting it — the implementer relies on the shape.

## Template

```markdown
## Summary
<one paragraph: the change and why it matters>

## Goals & evaluation
- **Goal**: <what should be measurably better after this issue>
- **Metric / harness**: <the instrument that decides it: an exact command, or a judged procedure and its rubric>
- **Baseline → target**: <today's value> → <threshold that counts as success>
- **This issue's contribution**: direct | enabling | guard — <expected effect>
- **Local signal**: <cheap command the implementer runs in its own worktree, or N/A: reason>
- **Decided by**: <final eval/perf/integration ticket or issue, or "this issue's own harness run">

## References  <!-- discovery starting point; not exhaustive -->
- `path/to/file.ext:LINE` — <why it's relevant>
- `path/to/Spec.tla` — <state machine this touches, if any>
- <doc / ADR / prior issue / PR links>

## Discovery notes
<what you learned scanning the repo: entry points, invariants, adjacent code,
open questions the implementer should resolve first>
Risk evidence: <findings already anchored to the touched actions/bins and graph
nodes, by ID; graph nodes this change must not trust blindly; or "none found">
(spec-double-2 `references/agent_roles.md` § *Evidence routing*)

## Worktree & branch
Create the worktree AND its own Skill Manager home with ONE command, from the
repo root. It is the same command for a plain repo and an integration repo:
`WT="$(for d in "${SKILL_MANAGER_HOME:-$HOME/.skill-manager}"/skills/skt "${SKILL_MANAGER_HOME:-$HOME/.skill-manager}"/plugins/*/skills/skt; do [ -d "$d" ] && { printf %s "$d"; break; }; done)/scripts/wt"`
`"$WT" new <issue-number>-<slug>`
It prints one line — `created worktree <path>`. **cd to the path it printed.**
That path is `<parent>/<repo-name>-<issue-number>-<slug>`, not `../wt-...`, so
do not guess it.
If it exits 3 saying "no project home yet", this repository has never been given
a home. Run the absolute `fix:` line it printed — a one-time, per-repository
step — then run the same `wt new` again.
If it exits 7 saying the base is **behind** its remote, the branch you named is a
local ref that has fallen behind `origin/<base>` — usual on an `epic/*` branch
whose ticket PRs were merged server-side. Run the `fix:` line, which branches
from the published tip; `--stale-base-ok` takes the local ref deliberately.
Do **not** substitute `git worktree add`: that produces a worktree with no home,
and an agent launched in it writes the operator's global `~/.skill-manager`.
Launch through `<worktree>/.skill-manager/bin/launch/{claude,codex,gemini}`.
Any skill edit you make inside that home is in no diff and is deleted with the
worktree — publish it with
`skill-manager unit publish <unit> --ticket <issue-number>`.
(see references/worktree-branch.md)

## Spec workflow — REQUIRED | NOT REQUIRED
<!-- Default NOT REQUIRED: state why in one line. REQUIRED only when the model element below is named. -->
On feature-branch creation, open the spec workflow with spec-double-compiler +
tla-spec-dev. Expected changes:
- **Internal.tla**: <state/vars/actions to add or change>
- **External.tla**: <observable behavior / interface to add or change>
- **Test graph**: <spec-graph nodes/cases to add or update>
- **Unit-test adapters**: <adapter conformance tests to add or update>

## Regression & close-out
Run these to close the issue:
- **Test graphs**: <named graphs>, including the tla-spec-dev spec-graph integration graph
- Attach the test-graph reports to the spec ticket that closes out in the repo
- Close the spec ticket via spec-double-compiler + tla-spec-dev
- Run spec unit tests and unit tests
- Commit and push to `feature/<issue-number>-<slug>`
- Report the goal contribution in the PR body (`## Goal contribution`): expected
  effect, measured local signal or `N/A: reason`, and what decides the goal
- Report the substrate blockers in the PR body (`## Skill changes proposed`):
  three columns, one row per blocker met — the unit, what was hit, and the
  proposed change as a diff or a link to the commit that applied it — or
  `none met`. It asks for no new run and is never a gate on merge
- Tear the worktree down with `"$WT" close <issue-number>-<slug>` — one command,
  same in both repo shapes. It runs the home close-out gate first and **refuses**
  while the worktree still holds skill work that removing it would destroy, then
  removes the worktree. Clear every blocker it names and re-run; never fall back
  to `git worktree remove`, which deletes the home without a word. Run it from
  inside any git repository (it resolves the ticket by search, so it need not be
  the repo that opened the worktree — but it must be *a* repo).
```

## Filling `## Goals & evaluation`

- Every bullet is filled or explicitly `N/A: <reason>`. Never delete the section
  and never leave a placeholder: an omitted section reads as "no goal was
  considered", which is exactly what this section exists to rule out.
- **Metric / harness** names the instrument that decides the goal. Usually that
  is a command someone can run; it may instead be a **judged procedure** — an
  artifact scored against a versioned rubric by judges who cite the artifact —
  or a mechanical block read beside a judged one. Write which, concretely. A goal
  nobody can decide is a slogan; a goal decided by judgement is not a slogan just
  because a human runs it. Either find the instrument in the measurement
  inventory (`references/discovery.md`), scope the issue to build it, or record
  the goal as `N/A: <reason>`.
- **Baseline → target** needs both halves. A target with no baseline is
  unfalsifiable; if the number has not been measured, write
  `unmeasured — <how the implementer measures it first>` rather than guessing.
  Two shapes are legitimately not a threshold, and both are written plainly
  rather than dressed up as one: a **multi-clause target**, whose clauses can
  settle differently and are reported one verdict each; and a goal that is
  **building the instrument**, whose target says there is deliberately no
  threshold on the number, because choosing one before anything can produce a
  number is inventing the answer. Where the instrument is a judged one, the
  baseline cites the prior scored run rather than a recollection.
- **Contribution** is one of `direct` (this change is expected to move the metric
  — give a directional or numeric effect), `enabling` (`none — enabling only`,
  plus what it unblocks), or `guard` (must not regress this metric while
  targeting something else — the local signal is the regression check).
- **Local signal** is a *signal, not a gate*. The implementer runs it, records
  the number, and reports it even when it moves the wrong way. It never justifies
  weakening a required test, tuning to the metric, or widening scope.
- **Decided by** names the run that settles the goal — this issue's own harness
  run for an ordinary issue, or the epic's evaluation ticket in epic mode.

## Epic mode

Keep the `## Goals & evaluation` section and render it **from the assignment's
`goals:` entries**, not from a fresh conversation with the user: the epic already
agreed those goals and recorded them in its canonical plan, so the prose section
restates them for a human reader and must not introduce a metric, baseline,
target or contribution the assignment does not carry. Where the two disagree, the
assignment wins and the mismatch is a dispatch error to fix before the issue is
worked (`references/epic-assignment.md`).
