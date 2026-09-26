---
skill-imports: []
---

# What `skt check` is telling you

Moved out of `SKILL.md` by SI-29 (#391). The card's own blockquote says
everything below the orientation line is reference; this is that reference.
Open it when `skt check` said something you did not expect, or when a `skt`
command relayed a failure you cannot place.

## Two different things `skt check` says about skill-manager itself

They answer different questions and they can disagree, so read which one
fired before acting:

- **`cli-version`** — *a newer release exists.* Asks brew. Informational; a
  local build never triggers it, because a branch build's base version says
  nothing about which commits it carries.
- **`cli-floor`** — *the installed CLI is OLDER THAN THIS PLUGIN REQUIRES.*
  Asks nothing: it compares the installed version against a number the plugin
  declares, in one file, `bootstrap-floor.toml` at the plugin root. Move the
  floor there and nowhere else.

The floor exists because `cli-version` could not see the case that cost six
days. skill-manager 0.28.1 predated a fix this plugin depended on, brew's own
formula cache was equally stale, and so brew answered "you are current" — a
CLI six days older than the fix it depended on was indistinguishable from a
current one at every surface an agent can see (SI-22-DF-01). A comparison
against a declared number cannot be made to agree by any cache.

**`cli-floor` WARNS. It refuses nothing** — not an install, not a session, not
a command (`GOAL-no-new-gates`). Like every other notification it makes
`skt check` exit `10`, which is skt's *notify* code rather than a failure:
`hooks/skt-session-start.sh` translates it into printed session context and
itself exits `0`. Nothing else in the substrate reads that exit code.

## When `skt check` says a unit is NOT stale

**A project or worktree home tracks the repository's pin, not the unit's
trunk.** When the checkout's `skill-project.toml` gives a unit a
`revision`, `skt check` in that home compares against the pin, never the
remote tip: at the pin it lists the unit under `pinned by
skill-project.toml (nothing to pull)`; off the pin it emits `pin-drift`
with `restore the pin with: … project resolve --project-dir <repo>`. Do
not `skt sync` a pinned unit there — that pulls trunk and breaks the
repository that pinned it. The root home ignores pins and tracks trunk.

A unit whose installed hash disagrees with its remote tip is usually
behind it. Sometimes the home already knows better: the installer
records `errors[*].kind` when it leaves a store in a state it could not
finish, and for `MERGE_CONFLICT`, `NO_GIT_REMOTE` and
`NEEDS_GIT_MIGRATION` that record *is* the explanation for the
disagreement. `skt check` reads it first and emits a `unit-error`
notification in place of the pull prompt:

```
deploy-helm is not stale — its store is mid-merge (MERGE_CONFLICT):
unmerged paths remain. Local work is preserved at stash@{0}.
Syncing re-runs the merge that made them.
  resolve with: git -C <home>/skills/deploy-helm status
```

**Do not answer this with `skt sync` or `skill-manager sync --merge`.**
`--merge` is documented as the flag that *sets* `MERGE_CONFLICT`, and
the state clears only when the store has no unmerged files left. The
stash the message names is somebody's uncommitted work and any reset of
the store destroys it. Resolve in the store directory, `git add` +
`git commit`, and the next command clears the error by itself.

## When a skt command relays a failure

`skt ticket new`, `skt publish` and `skt sync` all shell out — to
`bootstrap-home.sh`, or to this home's own `bin/cli/skill-manager` — and
when one of those fails you get the child's own words, not a summary of
them:

```
error: home bootstrap failed (exit 1); worktree and branch rolled back
cause: skill-manager: refusing to run against a home you did not name.
         you named:  /repo/wt-3/.skill-manager
         this shim would have edited: /Users/x/.skill-manager
fix:   skill-manager home shims --root /repo/wt-3/.skill-manager   # ...
log:   /tmp/bootstrap-home-A3Uj8x.log
--- bootstrap-home.sh said ---
  <the whole output, or its head and tail with the elision counted>
```

Read it in this order and believe the `cause:` block over everything
else — it is the child's text, lifted out so a long log cannot bury it.

**Exit 79 is a cross-home refusal and is never a version problem.** A
`bin/cli` shim binds the home it LIVES in and refuses when
`SKILL_MANAGER_HOME` names a different one, rather than editing the
other home silently. Upgrading anything changes nothing. Either the pin
serves a home that is not the one it lives in — regenerate it with
`skill-manager home shims --root <home>` — or the environment names a
home this pin does not serve, and the environment is what moves. The
refusal names both homes; the `fix:` line picks the right one of the two.

Before skt 0.8.0 this printed only the child's LAST line, so a
provisioning failure read as a dangling sentence fragment
(skill-manager#264) and the diagnosis was only reachable by re-running
the bootstrap by hand.
