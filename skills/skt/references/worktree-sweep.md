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
cannot. A worktree is one of its tickets when its ticket id is in the epic's
`ticket_plan.yaml`, or its tip is contained in the epic branch. The epic's
own worktree is never swept by `--epic`; remove it on its own once the
epic is finalized.

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
