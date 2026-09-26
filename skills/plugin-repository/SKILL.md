---
name: plugin-repository
description: >-
  Create and operate plugin repositories — a skill-manager PLUGIN whose
  `skills/` directory holds several skill repos as tracked files, so a bundle
  versions, installs, syncs and improves as ONE unit. Use when several skills
  always ship together, or a change spans more than one. A specialization of
  `git-integration-repo`.
skill-imports:
  - unit: tla-spec-dev
    path: skills/git-integration-repo/SKILL.md
    reason: >-
      A plugin repository IS an integration repository. The git model, the
      onboarding order, propagation and refresh are that skill's and are never
      restated here.
  - unit: tla-spec-dev
    path: skills/git-integration-repo/references/git-model.md
    reason: Why committing constituent files before restoring .git is load-bearing.
  - unit: tla-spec-dev
    path: skills/git-integration-repo/references/propagation.md
    reason: Fan-out of a merged parent change back to each skill repo.
  - unit: tla-spec-dev
    path: skills/unit-authoring/references/plugins.md
    reason: >-
      Authority on plugin layout, .claude-plugin/plugin.json,
      skill-manager-plugin.toml, contained-skill semantics and plugin install.
  - unit: tla-spec-dev
    path: skills/unit-authoring/SKILL.md
    reason: Authoring and shipping edits to any installable unit.
  - unit: tla-spec-dev
    path: skills/git-issue-workflow/SKILL.md
    reason: Worktrees, per-checkout Skill Manager homes and the ticket lifecycle.
---

# plugin-repository

A **plugin repository** is one git repo that is two things at once:

```
my-plugin-repo/                      # ONE repo, ONE remote, ONE version
├── .claude-plugin/plugin.json       #   <- it is a skill-manager PLUGIN
├── skill-manager-plugin.toml
├── integration.toml                 #   <- it is an INTEGRATION REPO
├── INTEGRATION.md  PLUGIN-REPO.md
├── skills/
│   ├── alpha-skill/                 # plain files here; its own .git and its
│   │   └── SKILL.md                 # own remote in a DEV checkout only
│   └── beta-skill/
│       └── SKILL.md
├── hooks/ commands/ agents/         # optional harness runtime surface
└── README.md
```

Downstream it installs as **one unit at one version**: `skill-manager install
github:owner/my-plugin-repo` brings every contained skill in together, `skt
check` notifies about it once, one `sync` moves all of them, and improving it is
**one PR**. Upstream each skill is still its own repo with its own history,
independently useful to other bundles, and a change made in the parent fans back
out to those repos as branches and MRs.

That is the whole idea: **a plugin repository is a self-improvement substrate.**
An agent that consumes it has one thing to reason about, one thing to change, and
one thing to pull. `references/why.md` is the argument in full — read it before
designing a bundle, because which skills belong in one plugin repo is the only
decision here that is expensive to reverse.

## This skill owns the plugin half. It owns nothing else.

`git-integration-repo` is a **hard dependency**, declared in
`skill-manager.toml`, and every script here sources its `integration-lib.sh`
(which sources `git-issue-workflow`'s `lib.sh`). The division is exact:

| Question | Owner |
|---|---|
| Constituents as plain files, never submodules; strip `.git` → commit → restore | `git-integration-repo` (`references/git-model.md`) |
| Pull every skill repo to its upstream tip at once | `git-integration-repo` — `scripts/refresh.sh` |
| Fan a merged parent change back out to each skill repo | `git-integration-repo` — `scripts/propagate.sh` |
| Worktree + its own Skill Manager home for a ticket | `skt` — `skt ticket new` / `scripts/wt`; the lifecycle it drives is `git-issue-workflow`'s |
| `plugin.json`, `skill-manager-plugin.toml`, contained-skill semantics, deps | `skt` — `references/plugins.md`, `skills/unit-authoring` |
| **The parent being a valid plugin AND a valid integration repo at once** | **here** |
| **Why a bundle, which skills belong in one, and who watches it** | **here** — `references/why.md` |

Nothing in those rows is restated on this page. When a step is theirs, run their
script.

## Not this skill

An agent picks a skill by its description, and four neighbours own jobs that
sound adjacent. Take the narrowest one that fits:

| The task | The skill |
|---|---|
| Ship an edit I made to one skill in my home | `skt` — `skt publish` |
| A deliberate editing session on one installed unit | `skill-dev` |
| Author or fix a unit's SKILL.md / manifests / deps | `skt:unit-authoring` |
| Onboard several repos into one parent, no plugin involved | `git-integration-repo` |
| A ticket, a worktree, a per-checkout home | `git-issue-workflow` — `skt ticket new` |
| **Bundle existing skill repos into one installable, improvable unit** | **here** |

The trap worth naming: "put these skill repos into one repo" also matches
`git-integration-repo`'s description, and running its `add-constituent.sh` gives
you `constituents/<name>/` — a repo that is not a plugin and cannot become one
without moving every directory. That is the same failure mode that skill records
for `wt`: an agent that never opens a page cannot learn the rule inside it. The
companion edit — a row in *its* workflow table pointing here — is listed in this
repo's README under "Companion edits".

## The four rules that are only true here

1. **Constituents live at `skills/<name>/`, not `constituents/<name>/`** — that
   is where skill-manager and the plugin runtime look. `verify.sh`, `refresh.sh`
   and `propagate.sh` read the path from `integration.toml` and are indifferent;
   **two dependency scripts are not**, and both are wrapped here:
   `add-constituent.sh` hardcodes the directory (use `scripts/add-skill.sh`), and
   `finalize-constituents.sh` guards the commit-before-`.git` invariant with the
   pathspec `-- constituents`, which in a plugin repo matches nothing and
   therefore **never fires** — so finalizing early silently produces gitlinks.
   Use `scripts/finalize.sh`, which re-asks against the manifest's real paths.

2. **The plugin is a unit; the skills inside it are not.** Change management
   works at plugin granularity and on purpose — `skt` sees one unit, one
   `gitHash`, one notification, and `skt publish` on a home-edited contained
   skill pushes to the **plugin repo**. What breaks is anything that addressed
   the skill by its *old* identity: a `skill-imports: unit: <skill>` now fails
   validation (measured), a git-coord reference silently installs a duplicate
   standalone copy, and a hardcoded `$SKILL_MANAGER_HOME/skills/<unit>/…` stops
   existing because the bytes are at `plugins/<plugin>/skills/<unit>/`. All
   three, with evidence, rewrites, and one real skill-manager bug about
   intra-bundle imports: **`references/imports.md`**. `scripts/verify.sh` greps
   for the first and third inside the bundle.

3. **A contained skill is invoked `plugin:skill`.** `skt:unit-authoring`, not
   `unit-authoring`. Cross-references in prose, harness `units = [...]` lists and
   `skill-project.toml` entries move to the plugin coord —
   `references/migration.md`.

4. **Propagate before you refresh — because refresh SKIPS, not clobbers.** The
   plugin repo is also a cache of the upstream skill repos, so an edit that
   landed in the parent reaches `alpha-skill`'s own repo only through
   `propagate.sh`. Until it does, that constituent's tree is dirty and
   `refresh.sh` prints `has local changes — … SKIPPING` and leaves it alone
   (measured; it does **not** destroy the edit). The cost is subtler than data
   loss: the pull you thought was atomic silently covered a subset, and you cut a
   version on it. Read refresh's SKIPPING lines.
   `references/lifecycle.md` sequences both directions.

## Workflows

| Task | Read | Run |
|---|---|---|
| Decide whether a bundle is right, and which skills | `references/why.md` | — |
| Create a plugin repo | `references/layout.md` | `scripts/init-plugin-repo.sh`, then `scripts/add-skill.sh` per skill |
| Add a skill to an existing bundle | `references/layout.md` | `scripts/add-skill.sh` → commit → `scripts/finalize.sh` → `scripts/verify.sh` |
| Pull every skill's upstream changes in, atomically | `references/lifecycle.md` | `refresh.sh` (dependency) → commit → `scripts/release.sh` |
| Change several skills at once and push it back out | `references/lifecycle.md` | `skt ticket new` → edit → merge → `propagate.sh` (dependency) |
| Cut a version consumers will be notified about | `references/lifecycle.md` | `scripts/release.sh` |
| Check the repo is a valid plugin *and* a valid integration repo | — | `scripts/verify.sh` |
| Move today's standalone skills or a harness into a bundle | `references/migration.md` | — |
| An import, reference or path that names a bundled skill | `references/imports.md` | `scripts/verify.sh` |

## Quick reference

```bash
# Both rungs, because both of these skills ARE bundled now: they are contained
# skills of the tla-spec-dev plugin, so their bytes are under plugins/<plugin>/skills/.
P="$(for d in "${SKILL_MANAGER_HOME:-$HOME/.skill-manager}"/skills/plugin-repository "${SKILL_MANAGER_HOME:-$HOME/.skill-manager}"/plugins/*/skills/plugin-repository; do [ -d "$d" ] && { printf %s "$d"; break; }; done)/scripts"
S="$(for d in "${SKILL_MANAGER_HOME:-$HOME/.skill-manager}"/skills/git-integration-repo "${SKILL_MANAGER_HOME:-$HOME/.skill-manager}"/plugins/*/skills/git-integration-repo; do [ -d "$d" ] && { printf %s "$d"; break; }; done)/scripts"   # the dependency

# --- create ---
$P/init-plugin-repo.sh my-plugin ~/IdeaProjects/my-plugin-repo
cd ~/IdeaProjects/my-plugin-repo
$P/add-skill.sh alpha-skill git@github.com:owner/alpha-skill.git main
git add -A && git commit -m "bundle alpha-skill"     # BEFORE finalize — the invariant
$P/finalize.sh                                       # guard the invariant, restore each .git
$P/verify.sh                                         # plugin checks + the dependency's

# --- pull every skill's upstream in, as one change ---
git checkout -b feature/pull-upstream
$S/refresh.sh                                        # READ its SKIPPING lines
git add -A && git commit -m "pull skills to upstream tips"
$P/release.sh minor                                  # bumps both manifests; does NOT commit
git add -A && git commit -m "release <version>" && $P/verify.sh
#   ...PR, merge, then consumers: skill-manager sync my-plugin --git-latest

# --- change several skills at once, then fan out ---
skt ticket new PLUG-12                               # worktree + its own home
#   ...edit across skills/, commit, merge back to the parent main tree...
$S/propagate.sh PLUG-12 --push --mr                  # per-skill branches, MRs, tracking issue
$P/verify.sh

# --- prove this skill itself ---
bash <checkout-of-this-skill>/scripts/selftest.sh
```

Every script here answers `-h/--help` before doing anything and refuses a first
positional beginning with `-`; that guard is `help_guard` from the dependency
chain, and `scripts/selftest.sh` sweeps this directory to keep it true for
scripts added later. The reason it is not politeness is in
`git-integration-repo`'s SKILL.md.

## Plugin repos and harnesses

A harness's `units = [...]` is a *list of coords resolved at install time*; a
plugin repo is *the bundle itself*, versioned. When a harness exists only to name
a set of skills that always travel together, that set wants to be a plugin repo —
and then the harness either disappears or shrinks to the part a plugin cannot do:
binding doc-repo sources into a project root and managing named instances. A
plugin repo also carries `hooks/`, `commands/` and `agents/`, which no bare skill
can. `references/why.md` § *Plugin repo or harness* decides it.
