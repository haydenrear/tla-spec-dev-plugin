---
name: git-integration-repo
description: >-
  Create and operate integration repositories — a parent git repo holding
  constituent repos as tracked files, never submodules. Use to onboard repos
  into one parent, propagate a merged change out as branches and MRs, or refresh
  from upstream.
skill-imports:
  - unit: tla-spec-dev
    path: skills/spec-double-2/SKILL.md
    reason: Integration features use tla-spec-dev spec doubles and spec unit tests across all constituents.
  - unit: tla-spec-dev
    path: skills/test-graph/SKILL.md
    reason: Integration features are validated with test_graph spec/validation graphs spanning constituents.
  - unit: deploy-helm
    path: SKILL.md
    reason: Optional environment-repo composition deploys the constituents together to a test cluster.
  - unit: tla-spec-dev
    path: skills/skill-manager/references/workflows.md
    reason: This skill is installed and synced as a skill-manager unit.
---

# git-integration-repo

An **integration repository** is a single parent git repo whose working tree
contains several other repositories' files. The parent tracks those files as
**ordinary blobs** — it does not know, and must never be told, that the content
came from nested git repos. There are **no git submodules and no gitlinks**. Each
constituent still has its own real `.git` (with its own remote) inside the parent
working tree, but the parent ignores it.

That gives two things at once: **one place to make a cross-repo change** (create
a parent worktree, edit files spanning many constituents, commit once, review
once), and **clean fan-out on the way back** (when the change merges into the
parent, each constituent's real `.git` sees exactly its slice of the diff, so you
branch, commit and push per constituent, open an MR each, and file one tracking
issue).

## The load-bearing invariant

The whole scheme rests on **committing constituent files to the parent BEFORE the
constituent `.git` exists**. Order matters:

1. Clone a constituent into `constituents/<name>/`.
2. **Delete its `.git`** so it is just files.
3. `git add` + commit those files to the parent. The parent index now holds real
   file blobs (mode `100644`), not a gitlink (`160000`).
4. **Only now** re-create the constituent's `.git`: `git init`, add the remote,
   `git fetch --all`, `git reset --hard origin/<branch>`.
5. Verify the parent working tree is **clean** — `reset --hard` restores
   byte-identical content, so there is no diff.

If you ever `git add` a directory while it already contains a `.git`, git turns
it into a gitlink/embedded-repo and the model breaks. Never do that. The
empirical proof is `references/git-model.md`.

## When to use this skill

- "Onboard these N repos into one integration repo."
- "I merged the integration change — push it out to the underlying repos."
- "Scaffold tla-spec-dev / test_graph / deploy support across all of them."
- "Refresh the integration repo from upstream."

Not this skill: **"make a change across service-a, service-b and the shared lib
on ticket X."** That is a ticket, and a ticket is `git-issue-workflow` — the
worktree and its Skill Manager home are one `skt ticket new` there, whatever
shape the repo is. Come back here for the fan-out afterwards.

## Repository markers

Every integration repo carries two markers at its root (scaffolded by this
skill's `assets/`):

- **`INTEGRATION.md`** — the human/agent-facing note: "this is an integration
  repository, here is how to manage worktrees and push the constituents." An
  agent that opens the repo reads this first.
- **`integration.toml`** — the machine-readable manifest: the constituents (path,
  remote, default branch), the git host (`gitlab`/`github` → `glab`/`gh`), and
  which compositions (`spec_double_compiler`, `test_graph`, `deploy_helm`) are
  enabled. Every script reads this.

The **ignore file lives at the parent root** (`assets/gitignore.scaffold` →
`.gitignore`), with path-scoped rules like `constituents/*/target/`. It must
never be placed inside a constituent directory, because `git reset --hard` on a
constituent would clobber it.

## Workflows

| Task | Read | Scripts |
|---|---|---|
| Create / onboard an integration repo | `references/onboarding.md` | `scripts/init-integration.sh`, `scripts/add-constituent.sh`, `scripts/finalize-constituents.sh`, `scripts/verify.sh` |
| Make a ticketed change (multi-repo or not) | nothing — `git-issue-workflow` owns it | *(not here)* |
| Give a checkout its own skill-manager home | `git-issue-workflow`'s `references/skill-homes.md` | *(not here)* |
| Fan a merged change out to constituents | `references/propagation.md` | `scripts/propagate.sh` |
| Scaffold spec / test-graph / deploy | `references/composition.md` | (invokes the composed skills) |
| Refresh from upstream (destructive) | `references/git-model.md` | `scripts/refresh.sh` |
| Understand *why* the git model works | `references/git-model.md` | — |
| Why worktrees are not here, and what this skill still contributes to a ticket | `references/worktrees-not-here.md` | — |

## Worktrees are not here: `git-issue-workflow` owns them

**`new-change.sh`, `close-change.sh`, `bootstrap-home.sh`, `agent-home.sh` and
the shared `lib.sh` are shipped by `git-issue-workflow`, and `wt` by `skt` —
none of them by this skill.**
Nothing on this page creates or removes a worktree, and you do not need to read
this page to make one:

```bash
skt ticket new   TICKET-123   # preferred: on PATH in skt-carrying homes
skt ticket close TICKET-123
```

skt is a **plugin**, so it is never under a home's `skills/` — listing that
directory reports it absent from a home that has it. Test by path:
`test -x "${SKILL_MANAGER_HOME:-$HOME/.skill-manager}/bin/cli/skt"`. If it does
not resolve, the `wt` fallback in `references/worktrees-not-here.md` is correct
and there is nothing to report. If it resolves and you used the fallback anyway
— or replayed a script's steps by hand — that is a front-door defect, not a fact
about this repository, and it is invisible unless you say so. Name which case on
the PR and file it against the skill that owns the door. Full statement of the
rule: `git-issue-workflow`'s `SKILL.md`, §*Reaching a by-hand route is itself a
finding*.

That is the same lifecycle in an integration repo, in a constituent of one, and
in an ordinary repo with no constituents — it detects which it is standing in.
Why the machinery lives there rather than here, and the one key and one script
this skill still contributes to a ticket (the `PROPAGATE` key and
`propagate.sh`), are `references/worktrees-not-here.md`.

Every script left here sources `die`/`info`/`step`/`help_guard` and the checkout
predicates from `git-issue-workflow`'s `lib.sh`, through the single resolver in
`scripts/integration-lib.sh`. One definition, one home, one resolved path; there
is no second copy of `lib.sh` here and there must never be one. Both skills ship
in the `tla-spec-dev` plugin, so installing that bundle guarantees the file, and
`skill-manager.toml` no longer names a git coord for it — a coord would install a
duplicate standalone copy alongside the contained one. `integration-lib.sh`
refuses at source time, naming the `skill-manager sync` that fixes it, when the
installed copy is older than this skill needs.

## Quick reference

```bash
# scripts read integration.toml from the repo root; run them from anywhere in the repo.
# Two rungs: this skill is itself a CONTAINED SKILL of the tla-spec-dev plugin.
S="$(for d in "${SKILL_MANAGER_HOME:-$HOME/.skill-manager}"/skills/git-integration-repo "${SKILL_MANAGER_HOME:-$HOME/.skill-manager}"/plugins/*/skills/git-integration-repo; do [ -d "$d" ] && { printf %s "$d"; break; }; done)/scripts"

# --- create ---
$S/init-integration.sh my-integration            # scaffold markers, .gitignore, git init
$S/add-constituent.sh service-a git@host:org/service-a.git main
git add -A && git commit -m "onboard constituents"   # commit BEFORE finalize
$S/finalize-constituents.sh                      # re-init .git + remote + fetch + reset --hard
$S/verify.sh                                     # assert parent clean + every constituent wired

# --- refresh (destructive) ---
$S/refresh.sh                                    # fetch + reset --hard every constituent

# --- fan out ---
$S/propagate.sh TICKET-123                       # per-constituent: branch, commit, push, MR + tracking issue
$S/propagate.sh TICKET-123 --push                # also push feature/TICKET-123 to each origin
$S/propagate.sh TICKET-123 --push --mr           # also open a PR/MR each + one tracking issue

# --- prove the above (from a CHECKOUT of this skill, not the installed copy:
#     two of its checks sweep this unit's git index, which an install has none of) ---
bash <checkout-of-git-integration-skill>/scripts/selftest.sh   # needs no skill-manager CLI

# --- the worktree the change is MADE in: NOT here ---
skt ticket new TICKET-123                        # see references/worktrees-not-here.md for the fallback
#   ...edit across constituent files in the one parent worktree, commit...
git -C <repo-root> merge --no-ff feature/TICKET-123
$S/verify.sh                                     # then fan out with propagate.sh, above
skt ticket close TICKET-123
```

Every entry point here answers `-h/--help` before doing anything, and refuses a
first positional beginning with `-`. That is not politeness: `propagate.sh
--help` once consumed `--help` as the TICKET and ran a real fan-out, and
`init-integration.sh --help` scaffolded an integration repo called `--help` into
the operator's own working directory. The guard is `help_guard` in
`git-issue-workflow`'s `lib.sh`, called first by every script here, and
`scripts/selftest.sh` sweeps this directory to keep it that way.

`propagate.sh` fans a **parent** change out to constituents. Sending a **skill**
edit an agent made inside its own home back to that skill's repo is a different
flow (push-back) that `propagate.sh` cannot do, because the home is gitignored
and never in the parent diff. `git-issue-workflow`'s `references/skill-homes.md`
has the comparison; confusing the two silently loses the skill edit at worktree
teardown.

Always finish an onboarding or a propagation by running `scripts/verify.sh` and
confirming the parent tree is clean.
