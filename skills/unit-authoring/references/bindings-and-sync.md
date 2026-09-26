# Bindings and sync

Install and bind are separate operations.

- **Install** copies unit bytes into the skill-manager store and runs
  dependency side effects such as CLI installation and MCP registration.
- **Bind** projects an installed unit into a target root and records the
  exact filesystem projections in
  `$SKILL_MANAGER_HOME/installed/<unit>.projections.json`.
- **Sync** refreshes installed bytes and reconciles the side effects and
  binding records that belong to those bytes.

This split matters because a unit can be installed once and projected
into multiple targets: default agent dirs, explicit project roots, or
harness instances.

## Projection ledger

Each binding records:

- Binding id.
- Unit name and kind.
- Optional sub-element, such as one doc-repo source id.
- Target root.
- Conflict policy.
- Owner source: explicit user bind, default-agent bind, or harness bind.
- Projections to reverse later.

Inspect:

```bash
skill-manager bindings list
skill-manager bindings list --unit <unit>
skill-manager bindings list --root <path-fragment>
skill-manager bindings show <bindingId>
```

Remove:

```bash
skill-manager unbind <bindingId>
```

Move a whole-unit skill/plugin binding:

```bash
skill-manager rebind <bindingId> --to <newRoot>
```

Sub-element rebinds, such as doc-repo source bindings, should be handled
as unbind + bind.

## Binding shapes

Skills and plugins:

```bash
skill-manager bind skill:reviewer --to /path/to/root
skill-manager bind plugin:repo-tools --to /path/to/root
```

Result: symlink at `/path/to/root/<name>`.

Doc-repos:

```bash
skill-manager bind doc:team-prompts --to /path/to/project
skill-manager bind doc:team-prompts/review-stance --to /path/to/project
```

Result: tracked copies under `/path/to/project/docs/agents/` plus
managed imports in `CLAUDE.md` and/or `AGENTS.md`.

Harnesses:

```bash
skill-manager harness instantiate code-reviewer --id repo-review
```

Result: multiple harness-owned bindings, each with an id prefixed by
`harness:<instanceId>:`.

## Conflict policies

`skill-manager bind` accepts:

- `--policy error`: fail if the destination exists.
- `--policy rename`: move an existing destination to a backup path before
  writing the projection.
- `--policy skip`: keep the existing destination and record no
  replacement write.
- `--policy overwrite`: overwrite the destination.

Defaults:

- Skills/plugins default to `error`.
- Doc-repos default to `rename`, because a project often already has
  `CLAUDE.md` or `AGENTS.md`.

## Sync by kind

No-arg sync walks every installed unit:

```bash
skill-manager sync
```

Skill/plugin sync:

- Updates from the installed source or registry/git ref.
- Re-runs CLI/MCP/plugin marketplace side effects.
- Reconciles default-agent bindings.

Doc-repo sync:

```bash
skill-manager sync team-prompts
skill-manager sync team-prompts --force
```

- Refreshes managed copies for each doc binding.
- Preserves local edits by default.
- Uses `--force` to clobber local edits with upstream bytes.
- Reports stale bindings when a source was removed upstream.

Harness sync:

```bash
skill-manager sync harness:code-reviewer
```

- Finds live harness instances by `harness:<instanceId>:` binding ids.
- Reuses `.harness-instance.json` lock paths.
- Re-plans the instance bindings using current installed units.

## Authoring implications

- Do not assume install makes docs visible in a project. Doc-repos must
  be bound or included in a harness.
- Do not assume a harness uninstall removes projected instance files.
  Remove instances with `skill-manager harness rm <id>`.
- Use explicit `--to`, `--project-dir`, `--claude-config-dir`, and
  `--codex-home` in validation so test outputs are deterministic.
- When writing docs for a unit, distinguish installation validation from
  projection validation.

## Shipping Edits to an Installed Unit

Agents read units from the **store**
(`$SKILL_MANAGER_HOME/skills/<name>/`, `plugins/<name>/`,
`docs/<name>/`, `harnesses/<name>/`), not from the source repo you just
edited. Editing the source repo changes nothing an agent can see until
the bytes reach the store. A finished edit means synced, not saved.

The store copy for a git-backed unit is a checkout of a **remote** ref.
`skill-manager show <unit>` prints its store path, and
`$SKILL_MANAGER_HOME/installed/<unit>.json` records the `origin`,
`gitRef`, and `gitHash` that sync pulls from. So the loop is:

```bash
cd <unit-repo>
# ...edit SKILL.md / manifest / references...
git add -A && git commit -m "docs: ..."
git push origin main                    # sync pulls from the REMOTE
skill-manager sync <unit> --git-latest  # fetch gitRef, re-run side effects
```

Then confirm the store actually moved — do not assume sync succeeded:

```bash
skill-manager list          # SHA column should match the pushed commit
git rev-parse --short HEAD  # ...this one
```

Notes that trip agents up:

- **Push before sync — and check, because sync will not tell you.**
  Sync fetches the remembered `origin` at `gitRef`. A local commit that
  was never pushed is not upstream, so sync leaves the store on the old
  bytes. It still **exits 0 and prints a normal success report**,
  including MCP/CLI side effects, so a green sync is *not* evidence the
  bytes moved. The only proof is `gitHash` in
  `$SKILL_MANAGER_HOME/installed/<unit>.json` (or the SHA column of
  `skill-manager list`) matching your pushed `HEAD`.
- **The unit name is not the repo name.** Sync takes the installed unit
  name (`skill-manager sync skt` for the plugin published from
  `github:haydenrear/skill-publisher-skill`), while the remote is
  `github:owner/<repo>` — often spelled differently. `skill-manager
  list` gives the unit names.
- **Nested repos need two pushes.** When a unit repo lives inside a
  parent repo's tree, push the unit repo first; the parent commit only
  records the unit's files, and sync never reads the parent.
- **`--git-latest` when no registry is configured.** Plain
  `sync <unit>` may consult the registry for a published `git_sha`.
  `--git-latest` skips it and fetches the install-time `gitRef`
  directly, which is what you want for an unpublished edit. See the
  registry caution in `references/coords-and-distribution.md`.
- **Never edit the store copy in place** *as a way of authoring*. The
  next sync overwrites it, and its provenance no longer matches
  `origin`. This is a rule about where work should START, not a claim
  that an in-home edit is unrecoverable: an agent that improved a unit
  mid-ticket has already made one, and `skt publish` — `home sync` one
  tier up, then `unit publish` — exists precisely to rescue it. Author
  from the unit's own checkout; rescue from the store when the edit is
  already there.
- **Sync re-projects the agent symlinks.** A successful sync reports
  `✓ claude: synced <unit>` per configured agent, which is how the new
  frontmatter reaches each agent's skill directory. Claude Code re-reads
  a changed `description` in the running session; other agents may cache
  the skill list until restart. If a description change does not seem to
  take, restart the session before suspecting the manifest.

To iterate without pushing on every keystroke, use a working-tree sync
(`skill-manager sync <unit> --from <dir> --merge --yes`) or the
`skill-dev` worktree flow, then finish with a real commit + push + sync
so the store's provenance points at the remote again. Full semantics are
in `references/bindings-and-sync.md` and the "Git versioning and sync"
section of `references/coords-and-distribution.md`.
