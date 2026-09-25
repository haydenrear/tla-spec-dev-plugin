# SI-22 — the brew → skill-manager → plugin chain, walked by hand from a fresh home, before any eval case existed

Measured 2026-09-25 in the ticket worktree
`/Users/hayde/IdeaProjects/wt-371-eval-ladder-skill-manager`, branched from
`epic/self-improvement-substrate` at
`68b7e63b34917659680fc937702cae534704d8b8`. Every block below is captured
output, in `transcripts/`, not a summary written afterwards.

This file is committed **before** the eval cases, and that order is the
deliverable. `GOAL-evals-earned` says no eval is written for behaviour nobody
has watched work, and the two commit shas are the check
(`git merge-base --is-ancestor <record> <first case>`). **This commit contains
no `case.yaml`.** It is the fourth and last rung of the ladder; the three before
it are `8e362bbb→eefe3aa8`, `70549f90→7daa8e18`, `bec1934b→c96de147`.

---

## 0. Where the fresh home lived, and why that sentence is the first one here

The amendment to the work order is unambiguous: a scratch home is mostly
symlinks into the operator's home, so it must never live inside the checkout.
One did this week, `shutil.copytree` dereferenced the links, a fixture reached
57 GB and a 926 GB disk fell to 532 MB free.

Everything below ran under

```
HOME              = <scratchpad>/freshmachine/home
SKILL_MANAGER_HOME = <scratchpad>/freshmachine/home/.skill-manager
```

where `<scratchpad>` is this session's scratch directory on `/private/tmp`,
**outside every checkout**. The fresh home began as one empty directory and
acquired exactly **one** symlink for the whole ticket
(`Library/Keychains`, §3). Nothing was copied into or out of the checkout.

**No real home was written by hand at any point.** `$HOME/.skill-manager` was
read with `skill-manager list` and `skill-manager show` only, and the check for
that is in §6: zero paths under it newer than twenty minutes, before and after.

Free space, `df` and never `du`, on `/System/Volumes/Data`:

| moment | avail |
|---|---|
| before anything | **49 Gi** |
| after the fresh-home plugin install | **45 Gi** |
| after `skt ticket new` in the fresh home | **45 Gi** |
| after remove + reinstall | **45 Gi** |

About 3–4 GB for a complete fresh substrate: the plugin checkout, two
transitive skills, a bundled uv, and a 31,063-entry plugin cache in the agent's
home (§8). Nothing here approached the failure mode above.

---

## 1. What was driven by hand

| # | interaction | transcript | outcome |
|---|---|---|---|
| A | `skill-manager --version` under a fresh HOME | `step-04` | exit 0 — **brew's jar starts with an empty HOME**; the `EA-DF-12` jbang/JDK class does not arise on this path |
| B | `skill-manager list`, empty fresh home | `step-03` | exit 0, `(no units installed — use skill-manager install <source>)` — names the next command |
| C | `skill-manager list --home <path>` | `step-01` | **exit 2 — there is no `--home` flag.** The home is selected by env only |
| D | `skill-manager list`, root / project / worktree homes | `step-01` | **no standalone `skt` unit in any of the three** — §7 |
| E | `skill-manager install <git coord> --dry-run` | `step-03` | exit 0, prints 10 effects — **and writes `policy.toml` into the home** (§10, `SI-22-DF-04`) |
| F | `skill-manager install <git coord> -y`, fresh HOME | `step-04` | **exit 9 — clone refused.** The first walk failed, §3 |
| G | `git clone` by hand, fresh HOME vs operator HOME | `step-04` | `could not read Username` vs rc=0 — **the plugin repo is PRIVATE**, §3 |
| H | `skill-manager install <git coord> -y`, seeded home | `step-04` | **installed, and exit 11** — §4, `SI-22-DF-01` |
| I | `skt status` in the fresh home | `step-06` | exit 0, tier `root`, 3 units, names `skt check` next |
| J | `skt ticket new`, no project home | `step-07` | **exit 3, clean refusal naming the remedy**, nothing left behind — §5 |
| K | `bootstrap-home.sh --root <repo>` | `step-07` | exit 0, `projected: 2 of 2` |
| L | `skt ticket new`, after the remedy | `step-07` | **exit 0, worktree created with its own home** — the front door resolves |
| M | the shipped `SessionStart` hook, 3 locations | `step-09` | exit 0 in all three; output varies by **home tier and branch**, never by agent type — §9 |
| N | `skill-manager install` over an installed plugin | `step-11` | **exit 4**, halts, names the remedy — `SI-12-DF-06` reproduced |
| O | `skill-manager remove <plugin> --yes` | `step-11` | **exit 2 — `Unknown option: '--yes'`** — the flag asymmetry, reproduced |
| P | `skill-manager remove <plugin>` | `step-11` | exit 0 — but **leaves `bin/cli/skt` behind** (§11, `SI-22-DF-06`) |
| Q | the orphaned `skt` wrapper | `step-11` | **exit 127, refuses cleanly**, names the exact missing path |
| R | `skill-manager project resolve` | `step-14` | exit 1, names the missing manifest |
| S | `evals/setup-eval-home.sh --check` then build | `step-10` | `MISS` → **all checks passed** (§12) |
| T | every conditional in both shipped hooks | `step-15` | **zero** role / agent-type branches, with a non-vacuity control — §9 |

F–H, J–L, N–Q ran in the **disposable fresh home**. Nothing in this table
mutated `$HOME/.skill-manager`, the project home, or the epic worktree's home.

---

## 2. The chain, stated as what actually happened

```
brew  ──────────────►  skill-manager 0.28.1  (/opt/homebrew/bin/skill-manager)
                       artifact 641625cd3baf, built 2026-09-17
   │
   │  the ONLY thing installed separately.  ✓ demonstrated
   ▼
skill-manager install git+https://github.com/haydenrear/tla-spec-dev-plugin.git
   │
   │  ✗ FAILS on a genuinely fresh home — the repo is PRIVATE (§3)
   │  ✓ succeeds with one seeded credential … AND EXITS 11 (§4)
   ▼
one installed plugin: tla-spec-dev, 11 contained skills
   + 2 transitive skills it pulls in (deploy-helm, tracing-observability)
   │
   ▼
bin/cli/skt   ✓   and wt inside it at plugins/tla-spec-dev/skills/skt/scripts/wt
   │
   │  ✗ `skt ticket new` REFUSES until the repo has a project home (§5)
   ▼
skt ticket new  ✓  worktree + its own home. THE FRONT DOOR RESOLVES.
```

**Four of the five hops worked first time. Two hops needed something the
`GOAL-one-plugin` target sentence does not mention, and both are recorded
below rather than smoothed over.**

---

## 3. The first walk failed, and the failure is the best thing in this ticket

`step-04`, verbatim:

```
$ HOME=<fresh> SKILL_MANAGER_HOME=<fresh>/.skill-manager \
    skill-manager install git+https://github.com/haydenrear/tla-spec-dev-plugin.git --ref main -y
→ cloning https://github.com/haydenrear/tla-spec-dev-plugin.git
✗ × BuildResolveGraphFromSource: 1 coord(s) failed to resolve
! transitive: git+https://…#main [(top-level)] — git clone … refused: Cloning into '/private/…/cache/sta…
! install rolled back 0 effect(s) — no partial state retained
INSTALL rc=9
```

The diagnostic is **truncated at about 200 characters** — it ends mid-path at
`sta…` and the actual git error is not in it. Diagnosing this required
reproducing the clone by hand (`SI-22-DF-03`):

```
$ HOME=<fresh> GIT_TERMINAL_PROMPT=0 git clone --depth 1 <plugin repo> …
fatal: could not read Username for 'https://github.com': terminal prompts disabled
rc=128

$ (control: operator HOME, same command)   rc=0

$ gh repo view haydenrear/tla-spec-dev-plugin --json isPrivate
{"isPrivate":true,"visibility":"PRIVATE"}
```

### Two separate facts, and the second is the interesting one

**First: the plugin repository is private.** The chain `brew install … → the
CLI → installs the plugin` therefore **cannot be completed by a machine that
has nothing**, which is the exact scope sentence of this ticket. It completes
for a machine that already holds a GitHub credential for this account. That is
not a defect in the substrate's code; it is a gap between the
`GOAL-one-plugin` target sentence and what a fresh machine can actually do,
and `SI-23` should read it as such. Filed as `SI-22-DF-02`.

**Second: the failure mode is the one the eval lane already documented, reached
by a different route.** `credential.helper = osxkeychain` comes from the
**system** gitconfig —

```
file:/Applications/Xcode.app/…/git-core/gitconfig   credential.helper=osxkeychain
```

— which is **not** HOME-relative, so the helper is found under a fresh HOME. The
keychain it reads is at `$HOME/Library/Keychains`, which **is**. `evals/README.md`
states exactly this constraint for the eval sandbox ("overriding HOME fixes the
sandbox and breaks authentication, because the login credential is in the
keychain and the keychain path is HOME-relative"). The same constraint governs
the bootstrap chain, and nothing in the install path says so.

The minimum seed is therefore **one symlink**, the same one
`setup-eval-home.sh` makes:

```
$ ln -s $HOME/Library/Keychains <fresh>/Library/Keychains
$ HOME=<fresh> git clone --depth 1 <plugin repo>     rc=0
```

The fresh home held two entries at that point: `Library` and `.skill-manager`.

---

## 4. The install succeeds and exits 11, on every run, and this is the ticket's real find

`step-04` and again `step-11`, reproduced twice:

```
✓ resolve: 3 unit(s)
✓ installed tla-spec-dev
✓ installed deploy-helm
✓ installed tracing-observability
✓ units.lock.toml: wrote 3 unit(s)
✓ agents: 2 unit(s) linked into claude, codex, gemini
✓ cli: 17 installed
markdown skill-import violations (2) — fix these references:
✗   - tla-spec-dev (plugin): evals/skt/w-skt-migration-no-import-edits/fixture/my-skill/SKILL.md
✗     skill-imports[0] is missing required `reason`; explain why the import exists
✗   - tla-spec-dev (plugin): evals/git-issue-workflow/w-giw-exit6-is-unreadable-frontmatter/fixture/demo-skill/SKILL.md
✗     invalid YAML frontmatter: mapping values are not allowed here
INSTALL rc=11
```

Everything installed. The front door works. **The exit code says failure.**

### Both offending files are deliberately broken eval fixtures

`step-12` reads them and reads the cases that own them. They are not mistakes:

* `evals/git-issue-workflow/w-giw-exit6-is-unreadable-frontmatter/` — the case's
  own description says *"one unit's SKILL.md frontmatter is invalid YAML, so no
  sync can ever project it … The question is whether the agent fixes the
  frontmatter or chases the links."* **The invalid frontmatter IS the fixture.**
* `evals/skt/w-skt-migration-no-import-edits/` — a `skill-imports` entry without
  a `reason`, the subject of a migration case.

So the installer walks `evals/**/fixture/**/SKILL.md`, validates those files as
if they were shippable units, and **makes every install of this substrate exit
non-zero**. The eval suite this same epic built is what breaks the install of
the thing it evaluates.

**Why it matters beyond tidiness.** A fresh-machine bootstrap is a script, and
a script reads `$?`. Any `set -e` bootstrap, any CI step, any agent that checks
the exit code of the one command this goal is about, concludes the substrate
failed to install — when it installed correctly. It also lands squarely against
`GOAL-no-new-gates`: nothing here should block, and this blocks by exit code
while printing `✓` on every line that matters.

I did **not** fix it. It is outside my conflict keys (`evals/**` is mine, but
the validator that walks them is `skill-manager`'s, and the honest fix is on the
installer side — a fixture is not a unit). Filed as `SI-22-DF-01` with both
halves named. Exit 11 reproduced on two independent installs.

---

## 5. `skt ticket new` from a fresh home: the bootstrap ordering this rung exists to surface

`step-07`. First call, in a plain repo with no project home:

```
$ HOME=<fresh> <fresh home>/bin/cli/skt ticket new demo-1
error: no Skill Manager home could be created for this worktree
       (usually: …/plainrepo has no project home yet)
fix:   …/plugins/tla-spec-dev/skills/git-issue-workflow/scripts/bootstrap-home.sh --root …/plainrepo
log:   /var/folders/…/wt-ww47VW-run.log
rc=3
```

**Tested by path, not by exit code** (`SI-11-DF-04`): `find <scratch> -maxdepth 1
-name '*demo-1*'` returned **0**. The refusal is clean — it is not the
rolled-back-but-exited-0 shape that cost five agents this epic. rc=3 and no
worktree.

The remedy runs verbatim and works:

```
$ bootstrap-home.sh --root <plainrepo>
home:      …/plainrepo/.skill-manager
projected: 2 of 2 into each of .claude .codex .gemini
verified:  2 skill(s) servable …
rc=0
```

and the second call succeeds, creating `plainrepo-demo-1` on `feature/demo-1`
with its own `.skill-manager`.

**So the chain has a hop the target sentence omits.** "One installed plugin
provides the substrate; the front door resolves" is true — *after* one more
command per repository. The front door is `skt ticket new`, and on a fresh
machine `skt ticket new` is not the first thing you can run. It refuses well,
which is the difference between a finding and a defect, and I am recording it
as the former.

---

## 6. Nothing real was written, and here is the check rather than the claim

```
$ find $HOME/.skill-manager -maxdepth 2 -newermt '-20 minutes' | wc -l
       0                      (before the install, and after it)
```

`~/.claude.json` needed a second look, because its mtime **did** sit inside the
install window. It is not the installer:

* the install's own `ADDED` lines name `<fresh>/.claude.json`,
  `<fresh>/.codex/config.toml`, `<fresh>/.gemini/settings.json` — the fresh
  paths, and those files exist there;
* **positive control**: its mtime advanced again, 17:38:34 → 17:40, across turns
  with no install running. This Claude Code session rewrites it;
* its only gateway key is `/mcpServers/virtual-mcp-gateway/url` → `:51717`, one
  occurrence — the pre-existing entry `STATE.md` already describes as
  outstanding.

The root home was **not** rebuilt, touched or repaired. SI-24 already did that
on 2026-09-20 under the owner's say-so and this ticket did not revisit it.

---

## 7. `GOAL-one-plugin`, measured rather than asserted

SI-08's baseline: **2 installed units plus a brew formula**, root home NOT MET,
project home MET.

### On this machine now (`step-01`, read-only `skill-manager list`)

| home | substrate units | standalone `skt`? |
|---|---|---|
| `~/.skill-manager` (root) | `tla-spec-dev` plugin | **none** |
| `<repo>/.skill-manager` (project) | `tla-spec-dev` plugin | **none** |
| `<worktree>/.skill-manager` | `tla-spec-dev` plugin | **none** |

`skill-manager show tla-spec-dev` reports 11 contained skills, `skt` among
them, and `skt` also as a **plugin-level CLI dependency**. So skt ships inside
the plugin by both routes. **The root-home half that SI-08 measured NOT MET is
now MET**, consistent with the EA-DF-05/06 sweep.

### On a fresh home (`step-04`, `step-06`)

```
$ skill-manager list            (fresh home, after installing ONE coordinate)
deploy-helm             skill    0.1.0   git
tla-spec-dev            plugin   0.1.0   git     ← ac5f7491
tracing-observability   skill    0.3.0   git
```

**One plugin installed, three units present.** `deploy-helm` and
`tracing-observability` are transitive references of the plugin, resolved and
installed automatically; the operator names one coordinate. Whether "units a
fresh machine installs" means *one named* or *three present* is SI-23's to
decide — I am reporting both numbers rather than picking the flattering one.

### "the CLI comes from brew" — holds at every tier, and here is the mechanism

`step-08`. There is **no** `skill-manager` in `bin/cli/` of either root home.
There **is** one in project and worktree homes, 10,609 bytes, and it is not a
second CLI:

```
# skill-manager:cli-pin — generated by `skill-manager home shims`, do not edit.
…
209:  cli="${SKILL_MANAGER_CLI:-/opt/homebrew/bin/skill-manager}"
224:  exec "$cli" "$@"
```

It is a *pin* that binds the home and `exec`s brew's binary, and running it
prints `cli: /opt/homebrew/Cellar/skill-manager/0.28.1/…`. The claim survives.

---

## 8. What a fresh machine's agent actually receives

`step-13`. Two different delivery mechanisms, and only one of them is visible
where people look:

| unit | reaches the agent as | where |
|---|---|---|
| `deploy-helm`, `tracing-observability` | symlinks | `<HOME>/.claude/skills/` |
| **`tla-spec-dev` (all 11 skills)** | a **plugin via a generated marketplace** | `<home>/plugin-marketplace/` → `<HOME>/.claude/plugins/` |

That is what `bootstrap-home.sh`'s `projected: 2 of 2` counts — the two
standalone skills. It is **not** saying 2 of 11; the plugin simply is not
projected by that route, and the line reads like a shortfall until you check.

Registration is real and complete:

```
$ cat <fresh HOME>/.claude/plugins/installed_plugins.json
"tla-spec-dev@skill-manager-0e9368fa": [{ "scope": "user",
   "installPath": "…/cache/skill-manager-0e9368fa/tla-spec-dev/0.1.0",
   "version": "0.1.0", "installedAt": "2026-09-25T21:48:12.212Z" }]

$ ls …/tla-spec-dev/0.1.0/skills/      → all 11
```

**And the number that belongs to the progressive-disclosure question:**

```
$ find <agent cache>/tla-spec-dev/0.1.0 | wc -l
   31063
```

**31,063 entries land in the agent's plugin cache to deliver 11 skills** — the
whole repository, `evals/`, `examples/`, every `*-EPIC.md`. For scale, the eval
runner refuses a plugin directory over 20,000 entries, which is why `run.sh`
stages a 6,264-entry view. Every agent type receives all 31,063.

---

## 9. Per agent type — named, and covered or deferred by name

The plan says "epic agent, ticket agent, and whatever else the substrate
serves", and calls that an invitation to establish the list. Established by
sweep over `skills/`, `hooks/` and the epic's own plan, then **re-verified by
me** (`step-15`) because the sweep was a subagent's report and a report is not
evidence.

### Two senses of "agent type", and they must not be blended

**Sense 1 — the workflow role a dispatched session wears.**

| # | agent type | named at | what loads for it at session start | covered? |
|---|---|---|---|---|
| 1 | **epic agent** | `git-epic-workflow/SKILL.md:61`; `references/human-review.md:25` ("Epic agent (this skill)") | the same `skt status` + `skt check`; §9 measured in the epic worktree | **covered** — `step-09` |
| 2 | **ticket agent** | `git-epic-workflow/SKILL.md:61,66,70`; `git-issue-workflow/references/epic-ticket.md:217` | the same report; branch `feature/*` makes `skt status` add a `ticket <id>` line | **covered** — `step-09`, measured in two ticket worktrees |
| 3 | **evaluation ticket** (`role: evaluation`) | `epic-ticket.md:33`; `validate_epic_plan.py:155,1039` | **the same report.** `role:` never reaches a hook | **covered by the negative result** — §9b |
| 4 | **constituent / agent-tagged-PR agent** | `git-issue-workflow/references/agent-tag-pr.md:1,5` | not measured here | **DEFERRED BY NAME** — §9c |
| 5 | **judge** (scorecard / blind dispatch) | `spec-double-2/references/eval_scorecard.md:79,233` | **nothing** — dispatched via `claude --safe-mode -p`, which is designed to strip hooks, MCP and the skill listing | **covered by exclusion** — §9c |
| 6 | **`Explore` harness tier** | `blind_dispatch.md:34-36,62-65` | harness-internal; the substrate explicitly refuses to rely on it | **DEFERRED BY NAME** — not substrate-defined |

**Sense 2 — which coding CLI hosts the session.** `claude`, `codex`, `gemini`.
All three are real here: the install linked units "into claude, codex, gemini"
and wrote `.claude.json`, `.codex/config.toml`, `.gemini/settings.json` in the
fresh home. **Covered** for the projection surface (`step-13`, all three
written). **Deferred** for in-session behaviour: I ran the shipped hook by hand
and did not launch a codex or gemini session.

That is **six workflow roles and three harnesses, each covered or deferred by
name.** None silently skipped.

### 9b. The measurement itself: session-start disclosure does not branch on agent type

This is the evidence `SI-23` needs, and it is a negative result stated as one.

`step-15`, both shipped hooks (87 lines each):

```
$ grep -nEi 'role|agent.type|AGENT_TYPE|subagent|CLAUDE_AGENT' hooks/skt-session-start.sh hooks/skt-post-tool.sh
grep rc=1          ← genuinely no matches
```

Every conditional in `skt-session-start.sh` is environment- or state-derived —
`SKT_PYTHON`, a Python ≥3.11 probe, `SKILL_MANAGER_HOME`, `command -v skt`,
`CLAUDE_PLUGIN_ROOT`, "is the report empty", cache freshness, `rc == 10`.
**None is identity-derived.** `hooks.json` registers one `SessionStart` and one
`PostToolUse` with matcher `"*"`, no role parameter.

Same for the implementation underneath, with a non-vacuity control so an empty
result cannot read as a passing one:

```
$ out=$(grep -rnE '\brole\b|agent_type|AGENT_TYPE' skills/skt/src/skt/); rc=$?
grep rc=1   matches: 0
$ out=$(grep -rn 'def ' skills/skt/src/skt/);          rc=0   matches: 203
```

`role:` exists, and only in the plan:

```
$ grep -rhoE 'role: [a-z-]+' skills/git-epic-workflow/ | sort | uniq -c
  10 role: evaluation
   2 role: implementation
   1 role: str
```

Exactly two values, read by `validate_epic_plan.py`, **never by a hook**.

`step-09` shows what does vary — three runs of the shipped hook, three places:

| cwd | what the report added |
|---|---|
| fresh project repo | `tier: project`, parent home, 3 units |
| fresh ticket worktree | `tier: worktree`, `ticket demo-1`, `base in sync with parent` |
| this ticket worktree | `integration repo`, `ticket SI-22`, `spec workflow … active`, 19 units, **and a `skt check` block** |

**The axis is home tier and checkout state. There is no agent-type axis.** An
epic agent and a ticket agent standing in the same directory receive byte-identical
disclosure. Whether that is the right design is `SI-23`'s call; that it is the
current design is now measured rather than assumed.

### 9c. The two deferrals, stated plainly

* **constituent / agent-tagged-PR agent** (#4). Its workflow needs a second
  repository and a fan-out PR to exercise honestly. Out of my conflict keys
  (`evals/**`), and faking it with a single-repo fixture would measure the
  fixture. **Deferred, not skipped.**
* **`Explore` harness tier** (#6). `blind_dispatch.md:62-65` says it is
  undocumented, internal to the harness's per-agent-type prompt assembly, and
  "not relied on here". Measuring it would be measuring Claude Code, not this
  substrate. **Deferred by the substrate's own stated position.**

---

## 10. `SI-12-DF-06` re-verified, and sharpened in two places

`step-11`, in the disposable home. The recorded claim holds:

```
$ skill-manager install <coord> --ref main -y          # already installed
✓ resolve: 3 unit(s)
✗ ✋ halted: unit 'tla-spec-dev' is already installed at … — remove it first (skill-manager remove tla-spec-dev)
rc=4

$ skill-manager remove tla-spec-dev --yes
Unknown option: '--yes'
rc=2
```

Two things the existing record does not say:

1. **The refusal's own printed remedy is correct.** It prints
   `skill-manager remove tla-spec-dev`, without `--yes`. The asymmetry bites
   only an agent that adds `--yes` by reflex — which is precisely what a
   non-interactive agent does, so the finding stands, but the CLI is not
   contradicting itself.
2. **The refusal is late, not cheap.** Effect `[3]` ("reject if top-level
   resolved unit already installed") runs after effect `[1]` ("resolve graph
   from source"). All **three** repositories were cloned before the refusal
   fired. On a slow link a re-install attempt costs a full fetch to learn it
   was never going to proceed. Filed as `SI-22-DF-05`.

Remove-then-install closes the loop: `remove` → exit 0, `list` shows 2 units,
re-`install` → installed, and rc=**11** again for the §4 reason.

And `--dry-run`, which announces `DRY RUN — no changes will be made`, leaves
`policy.toml` in a previously empty home (`step-03`). One file, harmless, and
the sentence is still false. `SI-22-DF-04`.

---

## 11. The orphaned front door, which behaves well

After `remove`, `bin/cli/skt` is still there and still on PATH (`step-11`):

```
$ <fresh home>/bin/cli/skt status
skt: the home at …/.skill-manager holds no copy of skt (plugins/tla-spec-dev/skills/skt/src/skt/cli.py),
  and this wrapper is not a link into a home that does.
  Install skt into this home, or run the home that owns it.
rc=127
```

`skt ticket new` gives the same refusal and creates nothing (path test: 0). The
wrapper names the exact file it looked for and offers two remedies. **This is
the good version of the failure** — it is the `w-skt-which-copy-of-skt-ran`
shape with the answer printed. Recorded as `SI-22-DF-06` for the leftover shim,
with the refusal quality noted, because the shim outliving its unit is still a
surface an agent can trip on.

---

## 12. Eval lane readiness — and one thing that is per-checkout

`step-10`. `--check` in this new worktree:

```
MISS  no offline uv wheels -- every 'uv run --script' skill script fails in a sandboxed run
rc=1
```

`.toolchain/` is gitignored and therefore **per checkout**, so every new ticket
worktree starts without the wheels even though the scratch home at
`~/.local/state/tla-spec-dev/evalhome` is shared and already correct. Building:

```
downloaded 4 wheel(s) for offline uv: PyYAML>=6.0.2,<7
…
ok    uv resolves offline from 4 wheel(s) (a validator really ran)
all checks passed.   rc=0
```

Not filed as a finding — it is the documented design (`rm -rf .toolchain` is
the reset button) and the script's own `--check` names it precisely. Recorded
so the next rung does not read the `MISS` as a regression.

---

## 13. What this rung did NOT establish

Stated here rather than left to inference:

* **The chain was not walked on a machine with no GitHub credential**, because
  the repository is private and no such walk can succeed. What was walked is
  "fresh home, operator's credential, seeded by one symlink". §3.
* **No codex or gemini session was launched.** Their config files were written
  and verified; their in-session behaviour was not observed. §9.
* **The constituent-agent workflow was not exercised.** §9c.
* **`skt ticket close` / `wt close` were not run in the fresh home.** I created
  `demo-1` and left it; the fresh home is disposable scratch and teardown of it
  proves nothing about teardown in a real repository.
* **No brew install was performed.** `skill-manager 0.28.1` was already on this
  machine from brew and is the CLI every step used; re-installing it would have
  tested Homebrew, not the substrate.
* **`exit 11` was not fixed**, only characterised and filed. §4.
