# `GOAL-one-plugin` — Evaluation B (SI-23)

**Measured 2026-09-26 at base `8b6d97e8` (the epic tip), worktree
`../wt-372-evaluation-b`, branch `feature/372-evaluation-b`.**

> **Statement.** The substrate is ONE installed plugin. skt ships inside it, wt
> ships inside skt, and the only thing installed separately is the skill-manager
> CLI, which comes from Homebrew.
>
> **Baseline (73867de9).** 2 installed units plus a brew formula: the
> `tla-spec-dev` plugin AND the `skt` plugin, separately versioned and separately
> synced; `wt` lives in `git-issue-workflow/scripts/wt` inside the bundle while
> the tool that calls it sits outside.
>
> **Target.** one installed plugin provides the substrate; the front door
> resolves with skt contained; no standalone skt unit in root or project home;
> the CLI comes from brew.
>
> **Harness.** a fresh home: brew install the CLI, install the plugin, then run
> the front door (`skt ticket new`) and `skill-manager list`.

---

## Clause 1 — "one installed plugin provides the substrate"

### VERDICT: **MET on unit count at every ref. But *which* substrate it provides has THREE different answers, and only one of them is the thing this epic built.**

This is the clause the epic agent flagged as the trap in this ticket, and it is
worse than the amendment states — there are three refs in play, not two.

**The repository is public and the bootstrap works.** Re-verified independently,
not taken from the amendment:

```
GIT_TERMINAL_PROMPT=0 GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null \
GIT_ASKPASS=/bin/false git clone --depth 1 \
  https://github.com/haydenrear/tla-spec-dev-plugin.git
→ rc=0, 11 units under skills/, default branch main at ac5f7491
```

SI-22's `SI-22-DF-02` (`rc=128`, *could not read Username*) was **correct when
taken** and is **resolved by owner action on 2026-09-26, not by code**. Nothing
in the epic's diff closed it.

**But the three refs disagree about what the substrate is:**

| | ref | what it is | desc words | bodies > 1500 | `bootstrap-floor.toml` | eval cases | role routing |
|---|---|---|---|---|---|---|---|
| **A** | `8b6d97e8` | the epic tip — what this evaluation measures | **592** | **0 of 11** | present | 75 | 4 roles |
| **B** | `ac5f7491` | `origin/main`, what a fresh clone gets | 1,005 | 6 of 11 | **absent** | 64 | **none** |
| **C** | `a3761e30` | **what is actually installed in all three homes today** | 1,005 | 6 of 11 | **absent** | 64 | **none** |

- **B is 46 commits behind A.** `git rev-list --count origin/main..8b6d97e8` = 46.
- **C is 82 commits behind A and 36 behind B.** `a3761e30` is
  *"graphs green after the skt fixes; record what they decided"*, 2026-09-24.
  Every one of the three homes' `installed/tla-spec-dev.json` reads
  `"gitRef": "main", "gitHash": "a3761e309a9c..."`.

So: a fresh machine gets the substrate as of four waves ago, and **the machine
this epic was built on is running something older still**. The 592-word
disclosure that `GOAL-progressive-disclosure` reports MET is **not what any home
currently loads** — every home loads the 1,005-word version, without the CLI
floor, without the role-routed reading paths, and eleven eval cases short.

Reported both ways, as instructed, plus the third nobody had named. Filed
`SI-23-DF-05` (C, the installed-vs-source gap) and `SI-23-DF-06` (B, the
default-branch gap).

**What is true at all three refs:** the substrate is **one** plugin containing
**eleven** units — `discovery`, `git-epic-workflow`, `git-integration-repo`,
`git-issue`, `git-issue-workflow`, `plugin-repository`, `skill-manager`, `skt`,
`spec-double-2`, `test-graph`, `unit-authoring`. Against the baseline's *two*
separately versioned units, that half of the clause is met and is not in doubt.

## Clause 2 — "the front door resolves with skt contained"

### VERDICT: **MET, exercised rather than read.**

`skt ticket new 372-evaluation-b --base 8b6d97e8... --path <declared>` → rc=0,
and — per `SI-11-DF-04`, testing the **path** and not the exit code —
`test -d /Users/hayde/IdeaProjects/wt-372-evaluation-b` succeeds. The worktree
was not rolled back. Per `SI-09-DF-02` the branch name was checked against the
declared one and **matched** (`feature/372-evaluation-b`); no rename was needed
this run, which is a change from the five-of-five failure the issue records.

`skt status` in the worktree home → rc=0, reports tier `worktree`, its parent
home, the active workflow `self-improvement-substrate`, and **19 installed units
(11 change-managed)**.

`skt` is contained in all three homes at exactly one path each:

```
/Users/hayde/.skill-manager/plugins/tla-spec-dev/skills/skt
/Users/hayde/IdeaProjects/tla-spec-dev/.skill-manager/plugins/tla-spec-dev/skills/skt
/Users/hayde/IdeaProjects/wt-372-evaluation-b/.skill-manager/plugins/tla-spec-dev/skills/skt
```

I reached `skt` by the resolved path, not the by-hand pair — stating which case I
was in, as the issue asks.

## Clause 3 — "no standalone skt unit in root or project home"

### VERDICT: **MET in all three homes**, and this is the clause that moved.

Read-only sweep, `evidence/home_sweep.py`, over all 11 contained unit names plus
the pre-rename spelling `spec-double-compiler`, against `<home>/skills/*`,
`<home>/plugins/*` and `<home>/installed/*.json`:

| home | skill dirs | install records | standalone substrate dirs | standalone substrate records | plugin installed |
|---|---|---|---|---|---|
| root `~/.skill-manager` | 8 | 19 | **0** | **0** | yes |
| project `tla-spec-dev/.skill-manager` | 10 | 32 | **0** | **0** | yes |
| worktree `wt-372-evaluation-b/.skill-manager` | 10 | 32 | **0** | **0** | yes |

**A zero from a detector nobody has seen fire is not a measurement.** SI-08 had a
positive control for free — the root home's 8 hits. There is no such control now,
so one was built: `evidence/poscontrol.py` runs the identical predicate against a
synthetic home in scratch space carrying two planted standalone copies, and
reports `standalone_substrate_dirs = 2 ['skt','spec-double-2']`,
`standalone_substrate_records = 2`. **The detector fires.** No real home was
written to.

## Clause 4 — "the CLI comes from brew"

### VERDICT: **MET at the machine level. The review's stronger claim — "pinned at every tier" — is NOT true of the root home, and the `skt` wrapper does not resolve the brew CLI at all.**

MET: `/opt/homebrew/bin/skill-manager -> ../Cellar/skill-manager/0.28.2/bin/skill-manager`,
self-reporting `skill-manager 0.28.2`, `artifact 03c0143ec45e`. It is a Homebrew
formula and nothing else installs it.

**Correction to `REVIEW-BEFORE-SI-23.md` §2.** That file states the brew CLI is
*"pinned at every tier (`cli="${SKILL_MANAGER_CLI:-/opt/homebrew/bin/skill-manager}"`)"*.
Measured:

```
grep -rln 'homebrew/bin/skill-manager\|SKILL_MANAGER_CLI' <home>/bin/
  root      ~/.skill-manager                     -> NO HITS
  project   tla-spec-dev/.skill-manager          -> bin/cli/skill-manager, bin/launch/{claude,codex,gemini}
  worktree  wt-372-evaluation-b/.skill-manager   -> bin/cli/skill-manager, bin/launch/{claude,codex,gemini}
```

The pin is present in **two of three** tiers. The root home has no such file
under `bin/`. "Every tier" is not supported.

Two further facts about the front door, neither of which breaks the clause but
both of which bear on it:

- `~/.skill-manager/bin/cli/skt` hardcodes `py="/opt/homebrew/bin/python3.14"` —
  an absolute Homebrew **python**, not the brew skill-manager CLI. That
  interpreter is the one **without PyYAML** on this machine (see the interpreter
  note in the PR body).
- `~/.skill-manager/bin/cli/tla-spec-dev` execs a bare `python3`, so it resolves
  to whatever the caller's PATH supplies — Homebrew 3.14 (no PyYAML) from a zsh
  session, the Xcode 3.9.6 shim (PyYAML 6.0) from a bash script. This is the
  exact mechanism behind `SI-21-DF-01` and its inverted recurrence in
  `SI-29-DF-03`, still live in the shipped wrapper.

Filed `SI-23-DF-07`.

---

## Summary

| clause | baseline | measured | target | verdict |
|---|---|---|---|---|
| one installed plugin provides the substrate | 2 units + brew formula | **1 plugin, 11 units** at all refs — but the substrate differs by ref: epic tip `8b6d97e8` vs `origin/main` `ac5f7491` (−46) vs **installed `a3761e30` (−82)** | one plugin | **MET on unit count; the substrate a fresh machine or this machine actually gets is four-to-six waves old** |
| front door resolves with skt contained | wt outside the tool that calls it | `skt ticket new` rc=0 **and path verified**; `skt status` rc=0, 19 units; skt contained at exactly one path in each of three homes | resolves, contained | **MET** (exercised) |
| no standalone skt in root or project home | 8 standalone substrate copies in root (SI-08) | **0 / 0 / 0** across root, project, worktree — with a **firing positive control** | zero | **MET** |
| the CLI comes from brew | resolved from the operator's home | brew formula 0.28.2 is the only installer | from brew | **MET**; the review's "pinned at every tier" is **NOT supported** — 2 of 3 tiers |

**Moved by:** SI-16 (skt demoted to a contained skill), SI-17 (wt into skt),
SI-24 + `EA-DF-05` + `EA-DF-06` (root home rebuilt, 46 duplicate `plugins/skt`
directories cleared, 74 source manifests swept), and the **owner's 2026-09-26
action making the repository public** — which resolved the bootstrap clause SI-22
could not demonstrate, by permission rather than by code.

**Instrument limits stated:** the harness says *"a fresh home: brew install the
CLI, install the plugin"*. A genuinely fresh home was **not** provisioned by this
ticket — installing one would have written a real home, which the work order
forbids. What was measured instead is (a) an anonymous clone from a machine with
no credential, which is the part SI-22 could not reach, and (b) the three live
homes read-only. The claim supported is *"a machine that has nothing can obtain
the plugin"*, **not** *"a machine that has nothing was taken end-to-end through
install and the front door"*. That remains unexecuted, and after the public flip
it is now cheap to run; recommended to the owner as the one measurement that
would close this clause outright.
