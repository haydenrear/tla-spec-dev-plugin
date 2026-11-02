---
skill-imports: []
---

# Retiring an epic's worktrees

Moved out of `SKILL.md` by SI-29 (#391). Open it when an epic is finished and
its ticket worktrees are still standing, or when you are about to hand-roll a
`git worktree remove --force` loop.

## Retiring an epic's worktrees at the end: `list` and `sweep`

An epic keeps every ticket worktree standing until integration is done
and then retires them all at once. **Do not hand-loop
`git worktree remove --force`** — that is `rm -rf` with extra steps: it
deletes each worktree's Skill Manager home, which is gitignored, so the
loss appears in no diff, no PR and no fan-out.

```bash
skt ticket list                       # read-only: what is standing, and what blocks it
skt ticket sweep                      # the plan. Changes NOTHING without --yes
skt ticket sweep --target origin/main --yes  # retire every worktree that passes its own gate
skt ticket sweep --epic <slug> --yes  # one epic's worktrees only
```

Run it **from the primary checkout**. `sweep` refuses the worktree it is
running in and never touches the primary.

`--epic <slug>` resolves `epic/<slug>` (local or remote) and refuses if it
cannot. Which worktrees count as its tickets:

- **When `epic/<slug>` carries a `ticket_plan.yaml`, the plan decides.** A
  worktree belongs to the epic only if the plan declares it: its branch is
  `feature/<spec-id>`, or `feature/<issue>-<slug>` where `<issue>` matches the
  plan's `github_issue` (a URL, `#N` or `owner/repo#N`). A worktree the plan
  doesn't declare is excluded, whatever its history. Close it with `skt ticket
  close <ticket>`. A plan with no entries declares nothing. If git can't read
  the plan, the sweep refuses and selects nothing; it never falls back to
  history.
- **With no plan,** a worktree's tip must be the epic's ticket work: reachable
  from the epic branch, on none of the default-branch refs as they stood
  before the epic merged (`origin/HEAD`'s target plus whichever of `main`,
  `master`, `develop` and `trunk` exist, local and `origin/`), and not one of the epic's own
  first-parent commits. That still works after finalize merges the epic with
  `--no-ff`. Nothing else selects a worktree: not a slug in a branch or
  directory name, not descending from the epic tip, and not being cut from the
  epic without any commits of its own. If git can't answer, the default branch
  can't be resolved, or the epic was fast-forwarded onto it, the worktree is
  left standing: run `git remote set-head origin --auto`, or remove it with
  `skt ticket close <ticket>`. The same applies to a ticket from an epic's
  earlier merge round once the epic has moved on.

Shared Git ancestry alone never makes a worktree a ticket (#157). A feature
worktree cut from `main`, or one whose work reached the epic only because
`main` was merged into it, is "contained" in the epic without belonging to it.
An epic's owner or planning worktree (on `epic/<slug>` or on the
`feature/epic-<slug>` branch that `skt ticket new epic-<slug>` creates) is
never a ticket of another epic, and `--epic` never sweeps its own epic's owner
worktree either; remove that separately once the epic is finalized.

`--yes` needs a containment target. With no `--epic`, no `--target` and no
single discoverable `epic/*` branch, the dry run still lists every worktree
(noting that containment was not checked), but `--yes` refuses and removes
nothing: pass `--epic <slug>` or `--target <ref>` (e.g. `--target origin/main`).

Each worktree is measured *again* immediately before it is removed, and
any one of these makes it **skipped, not removed** — reported, with the
pass carrying on:

- uncommitted changes, or a stash entry made on that worktree's branch;
- commits not pushed, or not contained in the epic/target branch;
- a non-clean `skill-manager home close-out --home <worktree-home>
  --into <primary-home>` verdict — the same gate `skt ticket close` runs.

Removal is `git worktree remove`; `--force` is never passed. Exit `0`
means the pass completed (skips included — a skip is the gate working),
`1` means something failed, `9` means the destination home is `frozen`
and the pass was abandoned.

The summary reports a **free-space delta**, measured with `statvfs`
before and after, and no per-worktree size. These homes are cloned
copy-on-write, so `du` bills every shared block to every copy and
over-reports by roughly 30x — a home `du` called 1.1 GB cost 33.7 MB of
real space.
