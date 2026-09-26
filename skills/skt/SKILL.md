---
name: skt
description: >-
  The `skt` CLI: orientation and change management for skill-manager homes. Use
  at SESSION START for what is loaded, which home tier this session writes,
  whether you are in an epic or a ticket, and what is stale. Trigger on "what
  skills are loaded", "am I in a ticket/epic", "update this skill", "new
  version", "sync skills", "publish my skill edit", "please sync with root to
  publish changes globally", "start/finish a ticket", "clean up/retire/sweep
  worktrees", "reclaim disk space from worktrees", session startup.
---

# skt

One CLI for the questions every session has and nobody used to answer:
*what is loaded, where am I standing, is anything stale, and how does my
skill edit survive this worktree?*

> **Orienting yourself? Run `skt status` and stop reading.** It answers all
> four of the questions a session starts with — which home tier you are in,
> what is above it, the exact command that carries an edit out of this home,
> and which homes you must never write — in about 360 tokens. **Everything
> below this line is reference, and reading it to orient yourself costs
> roughly forty times more than running the command.**
>
> That number is measured, not asserted. Fresh agents inheriting nothing were
> asked those four questions against a real home: they answered the tier from
> `skt status` and then went hunting for the other three, spending 10,879
> tokens at the worktree tier and 21,186 at the root tier — reading a
> 13,000-token reference page and, at root, skt's own Python source. The
> command already knew every answer. It just did not say the last three out
> loud, and this page did not tell anyone to stop.

```bash
skt status            # startup report: units, plugins, home tier, epic/ticket state, CLI version
skt check             # new-version-available, unit errors, stale artifacts, a stale OR too-old skill-manager
skt sync <unit>       # pull a unit to its latest pushed source
skt ticket new <T>    # ticket worktree + its own Skill Manager home, one command
skt ticket close <T>  # teardown through the close-out gate
skt ticket list       # every ticket worktree here, and what blocks retiring it
skt ticket sweep      # retire many at once — dry run unless you pass --yes
skt publish [<unit>]  # a home-edited skill -> up one tier -> its own git repo
skt build [<id>]      # rebuild a derived artifact whose inputs you changed
skill-manager home drift --ack --home=<home>   # clear the launch gate a sync warns about; the home is a flag, never positional
```

`skt` is on `PATH` in every home **that installed this plugin**
(`<home>/bin/cli/skt`). `skt --help` is authoritative for syntax.

- `skt check` reporting `unverifiable (remote unreachable)` means currency could
  NOT be established for those units — say so; do not rebuild the check from
  `git ls-remote` or the lockfile.
- A unit absent from `skill-manager list` is not installed, so it cannot be
  synced — install it: `skill-manager install github:<owner>/<repo>` (the coord
  names the repo, e.g. `github:haydenrear/git-issue-workflow-skill`). `sync`
  only refreshes a unit that is already installed.

**A home does not inherit it.** Project and worktree homes are copies of the
home above them, so a home cloned from one that never installed `skt` has no
`bin/cli/skt` and no `plugins/tla-spec-dev/` — and then none of this page is loaded in
that session either, which is why you are unlikely to be reading this when it
matters.

That is not hypothetical, and the fix is one command. **As measured on
2026-08-24**, the skill-manager repository's project home and a ticket worktree
cloned from it each held four skills, no plugins and no `skt` — while the
`skill-project.toml` that home is meant to realize declared the plugin. A single
`skill-manager project resolve` against the worktree home installed `skt` and
`skill-manager` into it and the gap closed. **So if you are reading this from a
home that has `skt`, that measurement is history and not a description of where
you are standing** — which is the whole shape of the problem: a home is a copy
taken at an instant, and a sentence about one home is not a sentence about
another.

If `skt` is not there, nothing is broken and nothing is lost — you are simply
one tier down from where it was installed. Every `skt` verb is a wrapper:

| instead of | run |
| --- | --- |
| `skt status` / `skt check` | `skill-manager list`, `skill-manager home describe --json` |
| `skt sync <unit>` | `skill-manager sync <unit> --git-latest` |
| `skt publish <unit>` | `skill-manager home sync` then `skill-manager unit publish` (the two legs below) |
| `skt ticket new/close` | `<home>/skills/skt/scripts/wt new\|close <TICKET>` — this plugin's own script, so a home without skt has neither |

To get the plugin itself into this checkout's home, declare it in the
checkout's `skill-project.toml` and run `skill-manager project resolve`
against **that** home.

## Derived artifacts — read this before deciding a home is broken

`skt status` and `skt check` report artifact state into your opening context, so
every session is told artifacts exist. **What they are, what a clone inherits
versus merely declares, and when to rebuild is in
`references/derived-artifacts.md`.**

Go there if you are asking any of:

- what is a derived artifact, and what names them?
- what did my worktree home inherit from its parent, and what did it only
  declare?
- **a command on my `PATH` refused instead of running — `exit 86`** — or is
  simply not there at all;
- is this home broken, or is this what a healthy clone looks like?
- should I rebuild something, and with what command?

Read it rather than the source. The last two agents who read the source instead
got the root cause wrong, in opposite directions, and the page names both.

## When `skt check` surprises you

`skt check` has three answers that read as failures and are not: two about
skill-manager itself, one about a unit it calls NOT stale, and a fourth shape
where a `skt` command relays somebody else's failure as if it were its own.
Each is in `references/check-and-staleness.md` — read it before concluding a
home is broken.

## Startup disclosure

In Claude Code this plugin's `SessionStart` hook injects `skt status`
into every session automatically and performs the one bounded live
refresh of the check cache; the `PostToolUse` hook is cache-only — it
surfaces "new version available" notifications from that cached result
and never runs a check itself (every hook injection appends a line to
`<home>/logs/skt/hook.log`).
Harnesses without a hook runtime (codex, gemini) get the projected skt
skill plus an instruction snippet instead — the honest per-harness
matrix is `../unit-authoring/references/harness-capabilities.md`.

`skt ticket new/close` wraps `wt`, **this plugin's own script**. The raw
path form still works and is the fallback when `skt` is not on `PATH`:

```bash
"${SKILL_MANAGER_HOME:-$HOME/.skill-manager}/skills/skt/scripts/wt" new <TICKET>
```

`wt` is the door; the lifecycle behind it is `git-issue-workflow`'s and
`wt` resolves that unit at run time, refusing in one line when it cannot
(`$GIT_ISSUE_WORKFLOW_SCRIPTS` overrides).

## Retiring an epic's worktrees

When an epic finishes, `skt ticket list <epic>` enumerates its ticket worktrees
and `skt ticket sweep <epic>` retires them in one safety-gated pass — never a
hand-rolled `git worktree remove --force` loop. The gates, the dry run, and what
sweep refuses to remove are in `references/worktree-sweep.md`.

## The three-tier home model, in one table

| Tier | Path | Updated by | Your obligation |
| --- | --- | --- | --- |
| root | `~/.skill-manager` | operator installs; `skt sync` | publish local edits globally (`skt check` prompts here) |
| project | `<repo>/.skill-manager` | cloned from root; refreshed via `wt`/`skt ticket` imports | pull-side by default — but an edit made *here* owes the same two legs as any other |
| worktree | `<worktree>/.skill-manager` | cloned from project at `ticket new` | get edits OUT before teardown (`skt publish`; the close gate refuses otherwise) |

Homes are real copies, never symlinks. An edit inside one is **in no git
diff** — `skt publish` is how it survives: `home sync` moves it one tier
up (and no further), `unit publish` is the only route to the skill's own
repository and to other machines.

A copy of a home is not a copy of everything the home can *do*: the derived
artifacts it holds are inherited or declared rather than rebuilt, which is
`references/derived-artifacts.md`.

## This skill's reference pages

| Question | Page |
| --- | --- |
| What is an artifact, what does a clone inherit versus declare, when do I rebuild? | `references/derived-artifacts.md` |
| `skt check` said something surprising, or a command relayed a failure | `references/check-and-staleness.md` |
| The epic is over and its ticket worktrees are still standing | `references/worktree-sweep.md` |
| Which harnesses get hooks, and which get a projected skill instead? | `../unit-authoring/references/harness-capabilities.md` |
| The deep unit-authoring schemas | `../unit-authoring/references/` (see the `unit-authoring` skill) |

## Related skills in this plugin

- `unit-authoring` (sibling skill): authoring installable units —
  SKILL.md frontmatter, `skill-manager.toml`, `plugin.json`,
  dependencies, distribution. The deep schemas live in this plugin's
  `../unit-authoring/references/` pages.
- `skill-manager` (separate unit): install/bind/project/home plumbing;
  its CLI help is authoritative for those.
