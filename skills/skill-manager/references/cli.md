---
skill-imports: []
---

# CLI dependencies

Use this reference when a skill or plugin declares CLI tools in
`skill-manager.toml` or `skill-manager-plugin.toml`.

## Authoring

Declare CLI tools in `[[cli_dependencies]]`. The `spec` prefix chooses
the installer backend:

- `pip:<package>[==version]` installs with bundled `uv`.
- `npm:<package>[@version]` installs with bundled Node/npm.
- `brew:<formula>` installs through Homebrew and links into the
  skill-manager CLI bin.
- `tar:<name>` downloads and extracts a pinned per-platform archive.
- `skill-script:<name>` runs a bundled private install script.

Always set `on_path` to the command that proves the tool is available.
Pin versions and hashes whenever the backend supports it.

## Runtime

Do not assume a declared CLI dependency is on the user's shell `PATH`.
Resolve skill-manager managed binaries with:

```bash
<skill-manager>/scripts/env.sh --pretty
<skill-manager>/scripts/env.sh --skills <unit-or-skill-name>
```

Use the returned path directly in commands. If a binary is missing,
sync or reinstall the owning unit before falling back to a system copy.
For `skill-script:` deps, `install --force-scripts` and
`sync --force-scripts` rerun the bundled script even when the saved
fingerprint matches and the declared binary already exists. Named sync
scopes replay to the named unit: `sync <unit> --force-scripts` does not
force scripts owned only by unrelated installed units. No-name
`sync --force-scripts` applies to all installed units. These flags do
not bypass policy approval for CLI installers. Script stdout/stderr is
written under `$SKILL_MANAGER_HOME/logs/skill-scripts/`; the CLI prints
the log path and includes a recent output tail when a script fails.

`skill-manager uninstall <unit>` removes managed CLI binaries and
`cli-lock.toml` rows only when they are orphaned. If another installed
skill or plugin still claims the same backend/tool, uninstall preserves
the artifact and rewrites ownership for the surviving claim.

When the current directory is inside a skill project, the same helper
also reports passive project context: the manifest path, project name,
declared envs, project child Skill Manager home, and child-local agent
homes that already exist. Use that to choose `SKILL_MANAGER_HOME`,
`CODEX_HOME`, `CLAUDE_HOME`, and `GEMINI_HOME` for project-local agent
launches.

## Validation

Run install with a dry run first to inspect planned CLI actions:

```bash
skill-manager install file:///abs/path/to/unit --dry-run
skill-manager install file:///abs/path/to/unit --yes
skill-manager install --force-scripts file:///abs/path/to/unit --yes
skill-manager sync <unit-name> --from /abs/path/to/unit --dry-run
skill-manager sync <unit-name> --force-scripts --yes
```

Policy may require explicit approval for CLI installers. Do not bypass a
blocked plan without user instruction.

## MCP and CLI Tools

When a unit is installed, declared tools are resolved transitively:

- CLI dependencies land under `$SKILL_MANAGER_HOME/bin/cli/`.
- MCP dependencies register with the `virtual-mcp-gateway`.
- Plugins contribute deps from both `skill-manager-plugin.toml` and
  contained skill manifests.
- Harnesses install the referenced skills/plugins/doc-repos before
  materializing an instance.
- `skill-script:` CLI deps are fingerprinted. Normal install/sync skips
  an unchanged script when the declared binary still exists;
  `install --force-scripts` explicitly reruns script deps in the install
  graph. `sync <unit> --force-scripts` reruns script deps only for the
  named sync target; no-name `sync --force-scripts` applies to all
  installed units. Script stdout/stderr is written under
  `$SKILL_MANAGER_HOME/logs/skill-scripts/`, with the log path shown in
  CLI output and a recent tail included on failure.
- `uninstall` prunes managed CLI artifacts and `cli-lock.toml` rows only
  when no surviving installed unit still claims the same dependency.

For CLI dependencies, do not rely on the user's `PATH`. Ask the helper
for absolute paths:

```bash
<skill-manager>/scripts/env.sh --pretty
<skill-manager>/scripts/env.sh --skills <name> --for claude
```

The helper reports installed skill paths, agent symlinks, bundled
package-manager paths, installed CLI binaries, missing declared tools,
and passive project context when run inside a skill project. It never
mutates shell state.

For MCP dependencies, there is no CLI equivalent for discovering,
deploying, describing, or invoking downstream tools. Use the
`virtual-mcp-gateway` MCP server's virtual tools. The short rule:

1. `skill-manager list` confirms which units are skill-manager-managed.
2. `browse_mcp_servers` shows registered downstream servers.
3. `deploy_mcp_server` starts a registered server when needed.
4. `browse_active_tools` or `search_tools` finds callable tools.
5. `describe_tool` discloses schema and satisfies the per-session gate.
6. `invoke_tool` calls the downstream tool.

See `references/virtual-mcp-gateway.md` for parameters, scopes, failure
modes, and the disclosure gate.
