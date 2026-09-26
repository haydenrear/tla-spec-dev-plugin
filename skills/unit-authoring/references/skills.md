# Skills

A skill is the default unit shape: one agent-facing capability plus
tooling metadata.

Use a skill when:

- The agent should load a focused set of instructions for one
  capability.
- The unit does not need plugin hooks/commands/agents.
- The content is not project-bound markdown for `CLAUDE.md` / `AGENTS.md`
  and does not need to compose a full project agent profile.

## Layout

```
my-skill/
├── SKILL.md
└── skill-manager.toml
```

`SKILL.md` is read by the agent runtime. `skill-manager.toml` is read by
skill-manager only.

## SKILL.md frontmatter

```markdown
---
name: my-skill
description: Use when the user asks to do the specific thing this skill supports.
skill-imports: []
---

# my-skill

Agent-facing instructions go here.
```

Rules:

- `name` is a single slug-like token.
- `description` is the activation hook. It should state when the agent
  should use the skill, not just what the repo contains.

  **A description is a TRIGGER, not a summary, and there is a measured reason.**
  Every description in a bundle loads at every session start, so their total is
  a fixed tax on every task. Measured on the `tla-spec-dev` plugin: SI-09 cut
  eleven descriptions to exactly 600 words, and nesting three more units put the
  total back to **1005** — because each new description restated which kinds of
  agent need the unit and what for. SI-29 brought it to 588 by moving that
  material out, and the only thing that stops the next unit undoing it again is
  this rule:

  - say **when to reach for the unit**, and stop;
  - "when you are a *<role>*, use this for *<thing>*" belongs on the role's
    reading path, not here — for this plugin that is
    `skills/spec-double-2/references/agent_roles.md`;
  - a list of subcommands, flags, caveats or exceptions belongs in the card or a
    reference page, which are read on demand rather than always.

  Nothing enforces this and nothing should (`GOAL-no-new-gates`). The instrument
  that measures it is the YAML-parsed `description` scalar of each
  `skills/*/SKILL.md`, word-counted, and the card-body companion is
  `awk 'BEGIN{fm=0} /^---$/{fm++; next} fm>=2' <card> | wc -w`.
- `skill-imports` is optional but recommended on starter markdown so
  imports can be filled in without changing file shape. See
  `references/skill-imports.md`.
- Frontmatter `name` must match `[skill].name`.

Quote the YAML description when it contains `:` or other YAML-sensitive
characters:

```yaml
description: 'Use when authoring installable units: skills, plugins, doc-repos, and harnesses.'
```

## skill-manager.toml

Keep `[skill]` at the bottom. TOML scoping means arrays placed after
`[skill]` become fields inside `[skill]`, which is usually wrong.

```toml
skill_references = [
  "github:owner/base-skill",
  "file:./local-helper",
]

[[cli_dependencies]]
spec = "pip:my-tool==1.4.0"
on_path = "my-tool"

[[mcp_dependencies]]
name = "my-mcp"
display_name = "My MCP"
description = "What this MCP server does."
default_scope = "global-sticky"
load = { type = "docker", image = "ghcr.io/me/my-mcp:latest", args = ["--stdio"] }

[skill]
name = "my-skill"
version = "0.1.0"
description = "Short tooling-side description."
```

Supported top-level sections:

- `skill_references`: transitive unit refs. See
  `references/coords-and-distribution.md`. Add one only when the
  referenced unit must be installed transitively; markdown
  `skill-imports` alone are semantic links to installed units.

  **Always use a git coord — `github:owner/repo` (or `git+https://…`,
  `file:…`). Never use `skill:name`.** There is **no registry configured**
  in this environment, so `skill:name` (a registry/name lookup) has no way
  to resolve — it will fail and abort the whole install. A transitive
  reference is fetched and installed before the top-level install commits,
  so it must point at bytes the resolver can clone. Git coords always
  resolve; registry-name coords are simply not an option here.

  **Find the coord with `gh repo list`, don't guess it.** The coord is the
  **repo**, not the installed `[skill].name` — the resolver clones the repo
  root and reads the name from there, and the two often differ. List the
  owner's repos to get the exact repo name, then comment the mapping so the
  next author isn't misled:

  ```bash
  gh repo list <owner> --limit 400   # find the repo that hosts the skill
  ```

  ```toml
  skill_references = [
    "github:owner/test_graph_skill",  # installs skill "test-graph"
    "github:owner/tla-spec-dev",      # installs skill "spec-double-compiler"
    "github:owner/deploy-cdc",        # installs skill "deploy-helm"
  ]
  ```
- `[[cli_dependencies]]`: CLI tools installed into
  `$SKILL_MANAGER_HOME/bin/cli/`. See `references/dependencies.md`.
- `[[mcp_dependencies]]`: MCP servers registered with the virtual
  gateway. See `references/dependencies.md`.
- `[skill]`: unit identity and version.

## Versioning and distribution

Put the skill at the root of its own git repo. Users install from the
git/local source:

```bash
skill-manager install github:owner/my-skill
skill-manager install git+https://host/org/my-skill.git
skill-manager install file:///abs/path/to/my-skill
```

Registry publish is optional metadata/search for supported unit kinds.
The git repo remains the source of truth.

## Validation

```bash
skill-manager install file:///abs/path/to/my-skill --dry-run
skill-manager install file:///abs/path/to/my-skill --yes
skill-manager show my-skill
skill-manager publish /abs/path/to/my-skill --dry-run
```

For a local starter, see `examples/skill/`.
