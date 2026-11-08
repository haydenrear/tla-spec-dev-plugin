# Lifecycle: the four flows, and the ordering that keeps them honest

A plugin repository sits between N upstream skill repos and M downstream
consumers, so changes move in both directions. Keeping them straight is most of
the operational work.

```
   skill repos  ──(A) refresh ──▶  PLUGIN REPO  ──(D) install/sync ──▶  consumers
        ▲                          ▲   │                                    │
        └──(C) propagate ──────────┘   └──(B) edit in a ticket worktree     │
                                                                            │
                     (E) an edit made in a consumer's home ──── skt publish ┘
```

## A. Pull upstream skill changes in, atomically

The skills' own repos moved (someone published from a home, or a fan-out was
merged). Bring them into the bundle as **one** change:

```bash
# Both rungs: these two skills are contained skills of the tla-spec-dev plugin.
S="$(for d in "${SKILL_MANAGER_HOME:-$HOME/.skill-manager}"/skills/git-integration-repo "${SKILL_MANAGER_HOME:-$HOME/.skill-manager}"/plugins/*/skills/git-integration-repo; do [ -d "$d" ] && { printf %s "$d"; break; }; done)/scripts"  # dependency
P="$(for d in "${SKILL_MANAGER_HOME:-$HOME/.skill-manager}"/skills/plugin-repository "${SKILL_MANAGER_HOME:-$HOME/.skill-manager}"/plugins/*/skills/plugin-repository; do [ -d "$d" ] && { printf %s "$d"; break; }; done)/scripts"     # here
git checkout -b feature/pull-upstream

# PRE-FLIGHT. refresh.sh will skip a dirty constituent and hard-reset a clean
# one, so ask both questions first — there is no other moment at which the
# answer is visible:
for d in skills/*/; do
  printf '%s: ' "$d"
  git -C "$d" status --porcelain | head -1
  git -C "$d" log --oneline "origin/$(git -C "$d" rev-parse --abbrev-ref HEAD)..HEAD" | head -3
done

$S/refresh.sh                    # fetch + reset --hard per constituent; SKIPS any that is dirty
git status                       # the parent now shows exactly what moved upstream
git add -A && git commit -m "pull skills to upstream tips"
$P/release.sh minor              # bump plugin.json + skill-manager-plugin.toml together
git add -A && git commit -m "release <version>"   # release.sh does NOT commit
$P/verify.sh                     # would FAIL on the uncommitted bump above
# PR → review the whole cross-skill delta in one place → merge
```

**What `refresh.sh` actually does with local work — read this before trusting
the word "atomically" above.** It `reset --hard`s each constituent to its
upstream tip, but it **skips** any constituent whose tree is dirty, printing:

```
  <name>: has local changes — propagate/push before refreshing. SKIPPING.
```

So an unpropagated parent edit is *not* destroyed (its files differ from the
constituent's HEAD, which is exactly what makes the tree dirty). The real cost
is quieter: that skill is **not pulled**, the "pull everything at once" you
believe you performed covered a subset, and `release.sh` then cuts a version on
it. Nothing downstream can tell. So: read every SKIPPING line refresh prints,
run flow C for each one, and refresh again — do not skim past them.

**And the hazard that is genuinely destructive**, which the "dirty is safe"
rule does *not* cover: after `propagate.sh` the constituent is **clean** — its
work is a commit on a local `feature/<T>` branch. `refresh.sh` then checks out
the default branch and resets it, so the parent tree shows those files as
modified, indistinguishable from upstream drift — and the next line of this flow
tells you to `git add -A && git commit`. That commits the revert. It is
recoverable (the commit is still on `feature/<T>` inside the constituent), but
only if you know to look. The pre-flight above is what tells you: a constituent
with commits not on `origin/<branch>` is propagated-but-unmerged, so let the MR
merge before refreshing.

Refresh one skill rather than the whole bundle with the same script, which keeps
the dirty-tree guard and resolves the branch from origin's HEAD:

```bash
$S/refresh.sh alpha-skill
```

Do **not** hand-roll that as `git -C skills/<name> reset --hard origin/<branch>`:
it has no dirty-tree guard and destroys an unpropagated edit silently. Measured.

## B. Change several skills at once, in the parent

This is the flow the bundle exists for.

```bash
skt ticket new PLUG-12          # worktree + its own Skill Manager home
#   ...in the worktree: edit across skills/alpha-skill, skills/beta-skill, hooks/…
#      the worktree holds plain files — no constituent .git — which is what makes
#      one commit able to span skills at all
git add -A && git commit -m "PLUG-12: unify the vocabulary across the bundle"
```

Then merge back into the parent main tree and cut a version:

```bash
git -C <repo-root> merge --no-ff feature/PLUG-12
$P/release.sh patch && git commit -am "release <version>"
$P/verify.sh
```

Review happened once, over the whole change. Consumers get it whole.

## C. Fan the merged change back out to the skill repos

Now each skill's own repo needs its slice, or the bundle and the upstreams
diverge — and the next refresh will skip that skill rather than pull it, so the
divergence compounds quietly.

```bash
$S/propagate.sh PLUG-12                 # dry run: branch + commit per changed skill, no network
$S/propagate.sh PLUG-12 --push --mr     # push, open an MR each, file ONE tracking issue
```

Semantics — per-skill `feature/PLUG-12`, skipping unchanged constituents,
idempotent on re-run, the tracking issue for a downstream agent to test and
merge — are `git-integration-repo`'s `references/propagation.md` and are not
restated here. Two things are specific to a plugin repo:

- **Propagation is not optional maintenance, it is how the bundle stays a
  cache.** The skill repo is the skill's identity; a bundle that stops fanning
  out has forked its members silently.
- **Order: propagate, then refresh.** After the MRs merge, flow A brings the
  merge commits back and the parent tree should end up clean — that round trip
  is the evidence the fan-out was complete.
- **`verify.sh` cannot witness a fan-out.** It reports each constituent against
  the *manifest* branch, so it exits 0 whether propagate ran or not. Its
  "Constituent state" step prints the evidence (branch, commits not on origin,
  dirty) but never judges it. The three questions that actually answer it:

  ```bash
  git -C skills/<n> rev-parse --abbrev-ref HEAD          # on feature/<T>?
  git -C skills/<n> log --oneline origin/<branch>..HEAD  # pushed? merged?
  git -C skills/<n> status --porcelain                   # anything left uncommitted?
  ```

## D. Consumers

```bash
skill-manager install github:owner/my-plugin-repo --yes
skt check                       # ONE notification for the whole bundle
skill-manager sync my-plugin --git-latest
skill-manager list              # SHA column must match the pushed parent HEAD
```

**`SKILL_MANAGER_HOME` does not sandbox the CLI.** Every path in these pages is
written `${SKILL_MANAGER_HOME:-$HOME/.skill-manager}/…`, which invites the
assumption that exporting it redirects `skill-manager install` too. It does not:
an install run that way still writes the real home's `plugins/`, `installed/`,
`units.lock.toml` and the harness's `enabledPlugins`. Measured twice, once
during authoring and once during review. To rehearse flow D, use a throwaway
checkout home created by `git-issue-workflow`'s `bootstrap-home.sh` and the
launch shims it writes — or accept that you are installing for real, and know
that `skill-manager remove <name>` is the undo.

A sync that exits 0 is not evidence the bytes moved — the store pulls from the
**remote**, so an unpushed commit leaves it on the old bytes with a green
report. The only proof is `gitHash` in
`$SKILL_MANAGER_HOME/installed/<plugin>.json` matching the pushed `HEAD`.
(`skt`'s `unit-authoring`, § *Shipping edits to an installed unit*.)

Consumers address contained skills as `<plugin>:<skill>`. A consumer's
`skill-project.toml` or `harness.toml` names **the plugin repo's coord**, once,
instead of one entry per skill — that collapse is most of the win at the
consuming end.

## E. An edit made inside a consumer's home

An agent edits `plugins/my-plugin/skills/alpha-skill/SKILL.md` in its own home
and wants it to survive. `skt publish` moves the home edit one tier up and then
publishes the **unit** — and the unit here is the *plugin*, whose store copy is
a checkout of the **plugin repo**. So the edit lands on the plugin repo.

**That is the design working, not a gap.** Change management is at plugin
granularity throughout: `skt`'s `_store_dir` resolves `skills|plugins|docs|
harnesses`, so a plugin is a first-class unit with one origin, one `gitHash` and
one notification, and a self-improvement PR against the substrate is a PR
against this one repo. Nothing about that wants to be per-contained-skill.

Two details worth stating exactly, because both were overstated in an earlier
draft of this page:

- `skt publish` runs `skill-manager unit publish`, which commits to a
  `skill/<ticket>-<unit>` branch, pushes, and **opens a PR** against the unit's
  trunk. So the edit is on a PR branch of the plugin repo, not on its trunk —
  and flow C reads the merged parent tree, so propagation waits for that PR.
- It only considers units that carry an `origin` *and* a `gitHash`. A plugin
  installed from a local file (`skill-manager install file://…`) has neither and
  is invisible to `skt publish`; publish it by pushing the plugin repo yourself.

What the edit has *not* done is reach `alpha-skill`'s own repo — the plugin repo
is also a cache of the upstreams, and only flow C empties that queue. Until it
does, `refresh.sh` will report that constituent as `SKIPPING` rather than
pulling it (flow A). Treat unpropagated skill edits as work in progress and look
for them before flow A — the same "propagate first, then refresh" ordering any
integration repo has, for the same reason.

## Releases

`scripts/release.sh <patch|minor|major|X.Y.Z>` writes the same version into
`.claude-plugin/plugin.json` and `skill-manager-plugin.toml`, because they must
agree and hand-editing one is the standard way to make them not. Guidance:

- **patch** — one skill's wording, a fix inside a skill.
- **minor** — a skill **joins** the bundle, new hooks/commands, a routine
  upstream pull.
- **major** — a skill **leaves** the bundle, or a contained skill's `name`
  changes. Both change what consumers can invoke, and a caller of
  `<plugin>:<skill>` gets nothing afterwards.

Tags: a git-coord install or `sync --git-latest` never needs one. Tag when you
want a pinnable ref (`github:owner/repo#v1.0.0`). `release.sh` prints the line
and does not run it.

## Removing a skill from the bundle

Not scripted, because it is three deletions and a version, and a script that
deleted a skill's directory on one argument is a worse trade than a checklist:

The half-finished version is the dangerous one, and it **passes** the
integration checks: drop the `[[constituent]]` block but leave the directory,
and the skill keeps shipping to every consumer forever while receiving no
refresh and no fan-out. `verify.sh`'s "Constituent state" step calls it out —
an unregistered `skills/<n>/` that still has its own `.git` is a half-removal,
because a genuinely bundle-owned skill never had one.

```bash
git rm -r --cached skills/<name> && rm -rf skills/<name>   # includes its .git
# then delete the [[constituent]] block for <name> from integration.toml by hand
#   (_manifest.py has `constituents`, `get` and `add` — `rm` is "unknown command")
# .claude-plugin/plugin.json needs NO edit: it carries no list of skills
$P/release.sh major          # consumers lose <plugin>:<name> — that is a major
$P/verify.sh                 # asserts nothing still points at the removed skill
git add -A && git commit -m "drop <name> from the bundle"
```

Then the consumer side, which the parent cannot do for you: anyone who invoked
`<plugin>:<name>` now has nothing, so either they install the skill standalone
from its own repo again (it still exists — `migration.md` § 4 is why you never
archive it) or the calls go. Say which in the release.

## Another route in: `skill-dev`

`skill-dev` opens installed **skills and plugins** in project-local worktrees
(`skill-dev open <plugin>` → edit → `close --merge`), so it is a second way a
consumer-side edit reaches the store copy — with the same consequence as flow E
and one difference: it merges back rather than opening a PR. Everything above
about propagation applies unchanged; the edit is in the plugin repo and nowhere
else until flow C runs. Use `skill-dev` for a deliberate editing session on the
bundle, `skt publish` for an edit you already made in a home.

## The integrating agent

The loop that becomes possible once bundles exist. Give an agent the plugin
repos and their upstream skill repos, and have it run:

1. **Watch.** For each bundle, which constituents' remotes are ahead of the
   parent's copy? (`git -C skills/<n> fetch && git -C skills/<n> rev-list --count HEAD..origin/<b>`)
2. **Judge coherence.** Do the pending upstream changes across the bundle *fit
   together*, and with what consumers currently expect? A rename that landed in
   one skill and not its caller is a reason to wait, not to pull.
3. **Pull and cut** — flow A — when they do, one PR, one version.
4. **Sweep the other direction.** Any skill edits sitting in a plugin repo
   unpropagated (flow E)? Fan them out — flow C.
5. **Report.** Which bundles moved, which consumers should sync, what was held
   back and why.

Step 2 is the judgment that has no home under one-repo-per-skill: there, every
skill publishes independently and "when does this reach consumers" is decided by
whenever each consumer happens to sync. Here it is a decision with an owner.
