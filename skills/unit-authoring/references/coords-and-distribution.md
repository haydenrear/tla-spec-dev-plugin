# Coordinates and distribution

## Source of truth

Units are distributed as git repositories, and installed from git
coords.

Default distribution model — favor this unless the user asks for
something different:

1. Put exactly one installable unit at the git repo root.
2. Add a `LICENSE` file so the unit can be shared and reused.
3. Commit the unit files.
4. Create a GitHub repository (or another git host) and push.
5. Install the durable copy from the pushed git source:
   `skill-manager install github:owner/repo`,
   `skill-manager install git+https://...`, or
   `skill-manager install git+ssh://...`.

Do not leave a `file://` install as the distributed result. A
`file:///abs/path` install is for local dry-run and validation only
(see "Minimal validation" in `references/scaffolding.md`); the copy a
user actually keeps should resolve to a pushed git source so `sync`,
provenance, and sharing all work. Only fall back to a file-only or
local install when the user explicitly asks for one.

The root of the repo must contain the marker for the unit kind:

| Kind | Required root marker |
|---|---|
| Skill | `SKILL.md` and `skill-manager.toml` with `[skill]` |
| Plugin | `.claude-plugin/plugin.json` and optional `skill-manager-plugin.toml` |
| Doc-repo | `skill-manager.toml` with `[doc-repo]` |
| Harness | `harness.toml` with `[harness]` |

Do not put multiple top-level units in one repo today. The resolver
detects one unit from the source root, and nested unit files can confuse
local shape detection. If units must ship together, use a plugin or a
harness, or put each unit in its own repo and reference the others by
coord.

## Coord forms

The same coordinate grammar is used for install sources and transitive
references.

| Coord | Meaning |
|---|---|
| `github:owner/repo` | Clone `https://github.com/owner/repo.git`; kind detected from the root. |
| `github:owner/repo#branch-or-tag` | GitHub repo with an explicit ref. |
| `git+https://host/org/repo.git` | Direct git URL; kind detected from the root. |
| `git+ssh://git@host/org/repo.git` | SSH git URL; uses the host `git` CLI and user credentials. |
| `file:///abs/path/to/unit` | Local absolute path. |
| `file:./relative/path` | Local path relative to the referencing unit's root when used transitively. |
| `./relative/path` / `../relative/path` | Local path shorthand. |
| `doc:name` | Installed doc-repo coord; bindable after install. |
| `doc:name/source-id` | One doc-repo source sub-element of an already-installed doc-repo. |

**Only git coords resolve.** Bare-name and kind-pinned coords —
`skill:name`, `plugin:name`, `harness:name`, bare `name`/`name@version`
— are not install sources and fail the install, naming the github:/git:/
file: forms. **Always use git coords (`github:owner/repo`, `git+...`,
`file:...`)** for both distribution and transitive references. The only
name-coord that is safe is `doc:<repo>/<id>` selecting a source of a
doc-repo that is *already installed* — that targets the installed unit.

Find the right `github:` coord with the GitHub CLI rather than guessing —
the repo name is usually not the installed unit name:

```bash
gh repo list <owner> --limit 400
```

Manifest references are install-time dependencies. They are separate
from markdown `skill-imports`, which are semantic links to a file inside
an already installed unit. Do not add a manifest reference solely to
mirror a markdown import.

## References in manifests

Skills use `skill_references`. Always use git coords (`github:owner/repo`,
`git+…`, `file:…`) for transitive deps. **Never `skill:name`** — only
git coords resolve (see the caution below):

```toml
skill_references = [
  "github:owner/base-skill",
  "git+ssh://git@github.com/org/private-skill.git#main",
  "file:./local-helper",
]
```

> **Transitive resolution caution.** A `skill_reference` is cloned and
> installed *before* the top-level install commits, so it must point at
> fetchable bytes. Two things bite authors:
>
> 1. **`skill:name` does not resolve.** It is not an "already installed
>    locally" lookup either, so the install aborts. Never use it.
>    Git coords (`github:owner/repo`) always resolve — use them.
> 2. **The coord is the repo, not the `[skill].name`.** The resolver
>    reads the unit kind and name from the *repo root*, and the repo is
>    frequently named differently from the skill it installs (e.g.
>    `github:owner/tla-spec-dev` installs skill `spec-double-compiler`).
>    Verify the repo with `gh repo list <owner>` and comment the mapping
>    next to each coord.

Plugins use `references` in `skill-manager-plugin.toml`:

```toml
references = [
  "github:owner/shared-skill",
  "github:owner/shared-plugin-repo",
]
```

Harnesses use `units` and `docs` in `harness.toml`:

```toml
[harness]
name = "repo-review"
version = "0.1.0"

units = [
  "github:owner/reviewer-skill",
  "github:owner/repo-tools-plugin",
]

docs = [
  "github:owner/team-prompts",
  "doc:team-prompts/review-stance",
]
```

Doc-repo source sub-elements are used at bind/instantiate time. A
doc-repo manifest declares source ids; references select them with
`doc:<repo>/<id>`.

## Git versioning and sync

For git-backed installs, the installed record remembers origin/ref/SHA.
`skill-manager sync <name>` pulls upstream and re-runs install side
effects. When the source was a branch, sync can advance to the latest
commit on that branch. `--git-latest` fetches the install-time git ref
directly.

Implications for authors:

- Commit before validating a git install.
- Tag or pin refs when you need reproducibility.
- Expect `sync` to update from the remembered git source, then re-run
  CLI/MCP/plugin marketplace/agent projection side effects.
- Keep one unit per repo root so sync can update the unit deterministically.

### The edit → store loop

Sync pulls from the **remote**, never from your working tree. Editing a
unit repo — even committing — changes nothing that agents load until the
commit is pushed and synced:

```bash
git -C <unit-repo> add -A && git commit -m "..."
git -C <unit-repo> push origin main
skill-manager sync <unit-name> --git-latest
```

Read `origin`, `gitRef`, and `gitHash` from
`$SKILL_MANAGER_HOME/installed/<unit>.json` to see exactly what sync
will fetch. Two failure modes to know:

1. **Sync over an unpushed commit is a silent no-op.** It exits 0 and
   prints a full success report — CLI installs, MCP registration, agent
   projection all re-run — while the store stays on the old `gitHash`.
   Verify the SHA, don't trust the exit code.
2. **`sync <unit-name>` takes the unit name, not the repo name.** They
   frequently differ (`github:haydenrear/skill-publisher-skill` installs
   the unit `skill-publisher`). Use `skill-manager list` for unit names
   and `gh repo list <owner>` for repo names.

Prefer `--git-latest` so sync fetches the install-time `gitRef`
directly.

To iterate before you are ready to push, sync straight from the working
tree with `skill-manager sync <unit> --from <dir> --merge --yes`, or use
the `skill-dev` worktree flow. Both leave the store's provenance pointing
at a local tree, so finish with a real push + `sync --git-latest`.
