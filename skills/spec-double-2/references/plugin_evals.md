---
skill-imports:
  - unit: tla-spec-dev
    path: skills/spec-double-2/references/agent_roles.md
    reason: "ROLE testing — you are the testing agent. This is your reading path and where what you measure goes back: this page itself under its own rule for adding to it, and specs/results/deferred/TESTING-AGENT.yaml when you open no PR."
    section: testing
---

# Evals that cannot be talked into passing

How to drive `claude plugin eval` against a skill, and how to keep its score
attached to something that happened.

Everything here was measured against Claude Code **2.1.261** on macOS, mostly by
running probe cases that cost cents. Where a claim came from a probe, the probe
is named. Where a thing is undocumented and I could not settle it, that is said
rather than guessed.

A **second source** now feeds it: the first full suite built on this reference,
in `haydenrear/skill-manager` — fourteen runs of one case, about **$12**, on
Claude Code 2.1.263. Everything traceable to that suite says so, because it ran
on a different machine against different units and its environment facts are the
ones most likely to be local. Where a claim of theirs was re-checked here, the
re-check is named too.

The worked example is this repository's own `evals/`, run by `evals/run.sh`.
Its README is the shortest path to a running suite; this page is the method
behind it. (Until SI-10 the example was a thin symlinked plugin at
`examples/agent_integration/eval-plugin/`. What replaced it, and why, is §3's
*When the repository IS the plugin, and it is too big*.)

---

## 0. The unknown unknowns, and how to stop inheriting mine

**Everything in this file was believed before it was measured, and a third of
what I believed was wrong.** Not wrong at the edges — wrong in the direction
that made a suite report success it had not earned. If you import this
reference and treat its list as the hazards, you inherit my blind spots along
with my findings. The list is the smaller half. **The method is the point.**

### What was actually wrong, and what would have caught it a day earlier

| I believed | The truth | What found it |
|---|---|---|
| `scaffold_script:` runs the fixture script | Top-level + inline: never invoked. But `context.scaffold_script: <path>` under `--scaffold` **does** run, as the operator, with network (2.1.276) | An inline body of `exit 3` scoring 1.00; then, for SI-14, a filed script that wrote a marker |
| A case's `plugins:` entry is additive and harmless | It **silently disables the target plugin's hooks**. 4 runs: hook fired 2/2 without it, 0/2 with it, both scoring 1.00 | Two identical cases differing only in that key, and a hook that appended to one file |
| The `llm` grader reads the workspace | It reads the final response and nothing else | A hook wrote `banana` into a file; graded three ways |
| Symlinking `.claude` leaks my skills into runs | Zero of 20 appeared; the run gets a fresh HOME | Reading the `init` event instead of inferring from three names |
| Containment forces physical copies of units | It applies to the entry path only, never inside a plugin | Trying a symlink inside a wrapper |
| Entries must be absolute paths | Relative resolves, against the case directory | Trying a relative one |
| A bare name is looked up as an installed plugin | There is no name lookup at all | Trying three genuinely installed names |
| A `Stop` hook's verdicts cannot be forged | A spawned process writes one after the hook exits | Writing the attack |
| The `deny file-write*` rule was applying | It was not: the profile named `/tmp/...`, the kernel resolves to `/private/tmp/...` | Checking the file was absent, not that no error printed |
| My forged-workspace control was a control | It ran with no case selected and could not go red | Mutating the recogniser and watching the test stay green |
| The eval home's `TMPDIR` follows the operator's shell | **`PATH` is the only variable that reaches the sandbox.** `TMPDIR` and `SKILL_MANAGER_HOME` both read `<unset>` inside a run | Printing them from the `SessionStart` hook, after eight runs died inside `git worktree add` |
| A hook can check the environment on the agent's behalf | The hook is *more* privileged, so its check answers a question nobody asked | `/usr/bin/git --version` succeeded in the hook in a run where the agent's Bash could not |
| A suite runs the cases I wrote | Case discovery is a recursive glob and follows symlinked units into *their* eval directories | Two `spec-double-compiler` cases appearing in a run of a different repository's suite |

Read the right-hand column. **Not one of those was found by thinking harder.**

### The six habits, in the order they pay

1. **Probe; do not reason.** A case that fails to load never runs an agent, so a
   refusal costs **$0.00**. Every schema fact in this file came from a
   deliberately malformed case. Reasoning about an undocumented tool produces
   confident prose and nothing else.

2. **Make your failing case fail first.** The attack that proved verdicts were
   forgeable did not work on the first try: an embedded `\n` in a heredoc became
   a real newline and the payload died on a `SyntaxError`. **"No verdict
   appeared" reads exactly like "no hole".** Run the negative case standalone
   and confirm it does the bad thing before you conclude anything prevents it.

3. **Ask what would look identical if you were wrong.** A denied write prints
   nothing. An allowed write also prints nothing. If your evidence is the
   *absence* of an error, you have not measured — check the artefact. This one
   question would have caught three of the nine rows above.

4. **Mutate the thing under test and watch your control go red.** A control that
   has never failed is a claim. Gutting a recogniser and finding the suite still
   green is how the flagship forgery control was exposed as vacuous — it had
   been running with no case selected since the day it was written.

5. **Re-run under the real conditions.** The hook's `HOME` is not your `$HOME`;
   its `python3` is whatever is on `PATH`; its paths resolve physically. A
   verifier that works in your shell and not in the hook withholds verdicts from
   correct work, and the score reads as the agent's failure.

6. **Count the runs behind the number before you quote it.** Fourteen runs of
   one case, while the environment was being repaired monotonically, produced
   Bash-call counts of **14, 10, 9, 8, 18, 18, 15, 27, 19, —, 16, —, 15, 21**.
   The counts did not improve with the environment, never approached the
   budget, and **their spread is wider than every effect that was attributed to
   a change.** Seven single runs were quoted as evidence in that round and all
   seven conclusions were wrong. This is habit 4 pointed at yourself: a number
   you cannot re-produce is a claim.

### The rule for adding to this file

**Before writing a claim here, name the observation that would differ if it were
false.** If you cannot name one, you have a belief, and it goes in marked as a
belief — the way the `agents:` paragraph in §3.5 is marked *I have not run
that*. An unmarked guess in a reference that other skills import is how one
person's ignorance becomes an organisation's.

## 1. The three things a case can observe

This is the whole surface. Six grader types, and they see between them exactly
three things:

| grader | what it reads |
|---|---|
| `file_exists` | **a path in the workspace**, after the run. Globs allowed |
| `tool_used` | **a tool NAME** was called, with a count range |
| `tool_order` | one tool name **before** another |
| `regex` | **the final response text** |
| `llm` | **the final response text**, judged by a model, majority of 3 votes |
| `baseline` | the final response text, against a `baseline_file` |

And here is what nothing observes: **file contents, tool inputs, tool outputs,
exit codes.**

Three probes established the boundaries, and each of them refuted something I
had assumed:

* **The `llm` judge sees the final response and nothing else.** A hook wrote
  `banana` into `SECRET.txt`; the criterion was "score 1 only if SECRET.txt
  contains banana".

  | what the agent did | votes |
  |---|---|
  | never mentioned the file | FAIL FAIL FAIL |
  | **read** the file, did not quote it | FAIL FAIL FAIL |
  | quoted its contents in the reply | PASS PASS PASS |

  Not the workspace. Not tool output. The text it ends with.

* **`tool_used` cannot match a command.** The permission-style pattern parses —
  the failure message renders it back — but for `Bash` it matches nothing. A
  run whose only Bash call was literally `echo hello` scored `Bash` **1x** and
  `Bash(echo:*)` **0x** in the same run. There is no grader that can assert
  *this command ran*.

* **`file_exists` has no content filter.** `contains:` is rejected as an
  unrecognised key; `regex` rejects `path:` and `file:`. A path grader knows
  only that a path exists.

**Consequence, and it is the whole reason for section 3:** with only these,
every claim about *quality* has to be routed through the response — and the
response is written by the thing being graded.

---

## 2. Running one

```bash
HOME=$EVALHOME CLAUDE_CODE_WALNUT_SPIRE=1 \
  claude plugin eval <plugin-dir> \
      --case '<glob>' --ablation none --runs 1 --allow-tools Bash Write Edit
```

Each part is load-bearing, and each was learned from a run that scored 0 for a
reason that was not the agent's.

**`CLAUDE_CODE_WALNUT_SPIRE=1`** — the subcommand is gated behind it and does
not exist without it.

**`--allow-tools`** — the operator grant, and it is **separate from the case's
`allowed_tools:`**. Listing `Write` in the case grants nothing. Running with
`--allow-tools Bash` against a case declaring `[Bash, Write, Edit]` produced

```
not granted (missing --allow-tools grant, or a malformed entry): Write, Edit
```

once, in a per-case note, and a score of 0 — an agent that could read the
program and could not write one line of a spec, reported as a failure to model.
**Assert this in a test**: read `allowed_tools` from the case, read the
documented command from your README, and fail if a gated tool is in the first
and not the second.

**`--ablation none` vs the default** — the default runs a second arm with no
plugin and reports the delta. That is a real control and worth having, but only
if the second arm can do the task. If your fixture is placed by a plugin hook
(section 3), the no-plugin arm gets an **empty workspace** and its 0 means "the
fixture was never placed", not "the skill is what scored". Use `--ablation
none` until the fixture can be placed independently of the plugin.

**`--case <glob>`** — a name filter, and it is **not optional once your units
are symlinked.** Discovery is a recursive glob — `--help` says the cases are
`<eval dir>/**/case.yaml` — so it descends through a symlinked unit into
whatever eval directory *that* unit ships. Verified here: this repository ships
`examples/agent_integration/eval-plugin/evals/` with two cases of its own, and a
suite that symlinks this skill's surface runs them, billed, alongside its own.
The cost is silent — the extra cases score, and nothing says they were not
yours. §3.5 has the shape that makes this bite.

**`--keep-temp`** — preserves each run's sandbox and prints the path. Open it:

```bash
chmod 700 <kept> <kept>/sealed && chmod -R u+rX <kept>/sealed
```

The workspace is `<kept>/sealed/home/cwd`; the full event stream is
`<kept>/out/trace.jsonl`. **Read the trace before you believe a score.** The
trace is where hook exit codes, per-turn tool calls, and `error_max_turns` are
visible, and the summary line shows none of them.

### The home

On a machine with Docker Desktop, a Bash-granting run refuses:

> the Docker (`~/.docker`, `DOCKER_CONFIG`) credential store on this machine
> holds a symbolic link inside it, so the Bash sandbox cannot reliably exclude it

`~/.docker` holds Docker Desktop's CLI shims — 18 symlinks under `bin/` and
`cli-plugins/`, none of them credentials. Two things that do not work:
`DOCKER_CONFIG` pointed at a plain directory (the message is byte-identical, so
the check reads `~/.docker` regardless of the override it names), and a bare
`HOME` override (the sandbox passes and the session cannot authenticate —
`Not logged in - Please run /login` — even with `.claude` and `.claude.json`
symlinked in).

**The credential lives in the keychain, and the keychain path is
HOME-relative.** Symlink `Library/Keychains` and both hold at once:

```bash
EVALHOME=/path/to/scratch/evalhome
mkdir -p "$EVALHOME/.docker" "$EVALHOME/Library"
cp ~/.docker/config.json "$EVALHOME/.docker/config.json"   # the file only
for p in .claude .claude.json .config .cache .local; do
    ln -s "$HOME/$p" "$EVALHOME/$p"
done
ln -s "$HOME/Library/Keychains" "$EVALHOME/Library/Keychains"
```

`.docker` must be a real directory holding a real file; symlinking it to
`~/.docker` puts the shims back.

**What this home does NOT leak — a correction, because I got it wrong once.**
An earlier draft of this section said symlinking `.claude` loads the operator's
personal skills into every run, and named `deep-research`, `dataviz` and
`code-review` as evidence. That was inference, not measurement, and the
measurement says otherwise: a run's `init` event listed **17 skills, every one
of them a Claude Code built-in**, plus the plugin under test. None of the
operator's 20 skill-manager units appeared, even though they are symlinked into
`~/.claude/skills/` and `~/.claude` is symlinked into this home.

The reason is stronger than a config directory. The run gets a **fresh HOME**:
the kept sandbox's `sealed/home/` holds `.aws .config .git .gitconfig .local
cwd` and **no `.claude` at all**, alongside its own per-run config dir with its
own `settings.json`, `projects/` and `sessions/`. `$EVALHOME` is not the run's
`HOME` either — it is what the CLI authenticates from before the sandbox is
built. **The run is more hermetic than I claimed, and your own skills are NOT
there unless you put them there** — which is section 3.5.

Why the wrong inference looked like evidence, since it is the useful part:
`deep-research`, `dataviz` and `code-review` all appear in the **zero-plugin**
arm too. They were built-ins the whole time, and naming three of them as
"the operator's personal skills" was a guess that happened to fit.

### Which copy of your CLI answers — and how to make it the checkout

**By default, it is not your checkout.** The run inherits the operator's whole
interactive `PATH`, `~/.skill-manager/bin/cli` is on it, and a
`which -a tla-spec-dev` inside a run returned

```
/Users/hayde/.skill-manager/bin/cli/tla-spec-dev
/Users/hayde/.skill-manager/bin/cli/tla-spec-dev
/Users/hayde/.skill-manager/bin/cli/tla-spec-dev
```

and nothing else. In another run, 32 of 55 Bash calls touched
`~/.skill-manager` and a traceback resolved the code from
`~/.skill-manager/skills/<unit>/scripts/`. **The plugin's skill directory
loaded correctly and the branch under review was still never executed** — the
skill under test was the plugin's, the toolchain under test was whatever was
installed.

Three ways to fix that do not work. Each was measured, not reasoned about:

| attempt | what happened |
|---|---|
| a plugin `bin/` directory | the docs say it joins the Bash tool's `PATH` while the plugin is enabled. Inside `plugin eval` it never appeared |
| `execution.env: {PATH: ...}` in case.yaml | refused: *"only EVAL_\* keys can be set from case.yaml. Anything else must come from the operator's shell."* |
| a shim under `/tmp` | the shell `PATH` **does** reach the run — it was first in `$PATH` — but the sandbox cannot reach `/private/tmp`, so `which` never found it |

The refusal message names the answer. **Ship a shim inside the checkout and let
the operator prepend it:**

```sh
# <plugin>/bin/<your-cli>
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo=$(CDPATH= cd -- "$here/../../../.." && pwd)
test -f "$repo/scripts/<entry>.py" || {
    echo "shim: no checkout at $repo -- refusing to fall through to an" \
         "installed copy, which would grade code nobody is reviewing" >&2
    exit 127
}
exec python3 "$repo/scripts/<entry>.py" "$@"
```

```bash
PATH="<plugin>/bin:$PATH" claude plugin eval <plugin-dir> ...
```

Verified: `which -a` then lists the checkout's shim first, ahead of the
installed copies. **The shim refuses rather than falling through** — a shim
that silently defers to the installed CLI reintroduces the exact bug it exists
to fix, and does it invisibly.

Then have the `SessionStart` hook *say which one it got*, and warn when it is
not the shim, so the trace answers the question without anyone having to
reconstruct it:

```
  tla-spec-dev: <plugin>/bin/tla-spec-dev  (THE CHECKOUT under review)
```

### Dependent tools

A skill declares `cli_dependencies` and then assumes they are there. The eval
sandbox is not your shell: have the `SessionStart` hook resolve each one and
print it, missing ones included.

```
  java:      /usr/bin/java
  tla2tools: ~/.skill-manager/bin/cli/.spec-double-compiler/tla2tools.jar
  pytest:    /Library/Frameworks/Python.framework/Versions/3.10/bin/pytest
  jinja2:    NOT ON PATH
```

`NOT ON PATH` printed before turn one is a truthful input. The same fact
discovered on turn 30 is a turn-ceiling failure that reads as an agent who
could not do the work.

---

## 3. Adding a skill, and placing a fixture

### The plugin

A directory with `.claude-plugin/plugin.json`:

```json
{"name": "<name>-eval", "version": "0.1.0", "experimental": {"evals": "evals"}}
```

and the skill surface under `skills/<skill-name>/`. **Symlink it, do not copy
it** — a copy drifts from the repository it claims to test. Verified loaded: a
passing run's `init` event listed the plugin, and the agent invoked
`Skill(<plugin>:<skill>)`.

One plugin holds **many cases** — `evals/<case-name>/` per case. You do not
need a plugin per case.

**But hooks belong to the plugin, not to a case**, so one `SessionStart` hook
has to serve every case. `execution.env` is the channel, and the allowlist that
refuses `PATH` is exactly what it is for:

```yaml
execution:
  env:
    EVAL_CASE: catch-the-drift
```

```sh
case "${EVAL_CASE:-}" in
  scaffold-a-program-model) ... ;;
  catch-the-drift)          ... ;;
  "")  echo "EVAL_CASE unset" >&2; exit 1 ;;
esac
```

Verified: a case setting `EVAL_CASE` had it visible in the hook. **Fail loudly
when it is unset** — a hook that silently places nothing is the empty-repository
failure again, and it reads as an agent who could not work.

Keep the shared scripts **outside** `evals/` (`<plugin>/lib/`). A directory
under `evals/` with no `case.yaml` is not loaded as a case today, but putting
library code where the loader is scanning invites a name to become meaningful
later.

### When the repository IS the plugin, and it is too big

`plugin eval` refuses a plugin directory over 20,000 entries. There are three
spellings of that refusal in the CLI and they are not the same check:

```
the eval directory holds more than 20000 entries — move large fixtures out of it
a plugin directory holds more than 20000 entries to check for eval directories — point the case at a smaller plugin directory
a checkout sharing the plugin's repository holds more than 20000 entries to check for eval directories — run from a standalone clone
```

The middle one is what a bundled plugin hits. Measured on 2.1.275: pointing it
at a 70,741-entry checkout produces it **at run time, once per case**, and a
`plugins: ["../.."]` naming the same root changes nothing.

**There is nothing to configure.** No `.gitignore`, no `.claudeignore`, no
manifest key, no flag, no environment variable; the traversal skips `.git`,
`.svn` and `.hg` and counts everything else, dot-directories included.
`--eval-dir` moves where cases are FOUND, not what gets counted.

So the only lever is which directory you hand it, and there are two shapes:

| shape | what it costs |
|---|---|
| a committed thin plugin that symlinks the skill surface | it names the skills by hand. `tla-spec-dev`'s carried `skills/spec-double-2` and nothing else; when the bundle grew to six skills it still showed one, and nothing said so |
| a view staged at run time, excluding what is not skill surface | a copy — but one built from the working tree at the top of every run, so it carries whatever the checkout carries and cannot drift |

This repository now does the second: `evals/run.sh` stages the working tree
without `specs/.history` (the append-only record, 19,154 entries), without the
gitignored `.skill-manager` home (41,169), and without the agent homes. 70,741
entries becomes 6,264.

**Prefer the staged view for a plugin that bundles skills**, and keep the thin
symlinked plugin for the case it was invented for: evaluating units that live
somewhere else entirely (§3.5).

### A plugin that is a repository must not commit `hooks/hooks.json`

The hooks that place fixtures and write verdicts belong to the PLUGIN. When the
plugin is a thin directory beside the repository, committing them is free. When
the plugin **is** the repository, a root `hooks/hooks.json` ships to every user
who installs it, and its `SessionStart` script runs in every session they open
— including, since exit 2 is blocking, a way for an eval-only fixture script to
refuse somebody's ordinary work.

Stage them instead: keep the file under `evals/`, and have the run script copy
it into the view as `hooks/hooks.json`. Verified on 2.1.275 — a probe case whose
staged `SessionStart` hook wrote one file and whose `Stop` hook wrote another
scored 1.00 with both verdict paths present, `${CLAUDE_PLUGIN_ROOT}` resolving
to the view, with no Bash grant and no scratch HOME.

### `scaffold_script:` — CORRECTED on 2.1.276: the key is live, but only one spelling of it

This section used to say, flatly, *"the script is never executed"*. That was
measured on **2.1.261** and it is **half right on 2.1.276**. Three probes,
$0.06 total, re-measured for SI-14 because a ticket's whole design rested on it:

| spelling | what happens on 2.1.276 |
|---|---|
| top-level `scaffold_script:` with an inline body | **accepted and silently ignored.** The case scored 1.00 and the marker was never written — the 2.1.261 finding, still true |
| `context.scaffold_script:` with an inline body | **refused at case-LOAD time**, because the value is read as a PATH: `case "...": path "echo ... > /tmp/marker " does not exist` |
| `context.scaffold_script: ./scaffold.sh` + `--scaffold` | **RUNS.** The CLI prints `scaffold: <abs path>` and the script executes |

So the key is not dead; it is a **path, under `context:`, gated behind
`--scaffold`**. What the third probe's script reported about its own
environment:

```
FILED SCAFFOLD RAN pwd=/private/tmp/e-jS2iI9/home/cwd whoami=hayde
HOME=/private/tmp/e-jS2iI9/home
git ls-remote https://github.com/haydenrear/skt main -> 0f380781…
```

It runs **as the operator, outside the sandbox, with working network**, in the
run workspace — but under a **scratch `HOME`**, so it cannot read
`~/.skill-manager`.

**Prefer a `SessionStart` hook anyway, and place fixtures from one.** Three
reasons, each of which is a silent wrong answer rather than an error:

* **`--scaffold` is OFF BY DEFAULT.** A suite whose fixture depends on it runs
  *unscaffolded* for anyone who forgets the flag, and still scores.
* **It is per case.** A hook dispatching on `EVAL_CASE` serves every case; N
  cases needing the same fixture means N scripts or N clones.
* **`plugins:` entries are validated at case-load time**, so a directory the
  scaffold creates during the run is not there when the loader looks for it.

Where it *is* the right tool is work that must happen **as the operator, before
the sandbox**, and that nothing loads at case-load time — fetching a pinned
toolchain, for instance. `evals/lib/toolchain.py` does that job from
`run.sh` instead, for the first reason above.

Place fixtures from a **`SessionStart` hook** in `hooks/hooks.json`. One hook
serves every case and dispatches on `EVAL_CASE` (see above), so it lives beside
the plugin rather than inside a case:

```json
{"hooks": {"SessionStart": [{"hooks": [
  {"type": "command", "command": "${CLAUDE_PLUGIN_ROOT}/lib/place.sh"}
]}]}}
```

**Fail with exit 2, not exit 1.** Claude Code treats 2 as blocking and every
other non-zero code as advisory, so a placement hook that exits 1 prints its
complaint and lets the session start anyway — on a workspace it just failed to
set up. Where a case seeds a deliberate fault, that is the difference between
refusing and handing the agent a program with nothing wrong with it, which
scores well for doing nothing.

It runs with the workspace as its working directory, before the first turn, and
the trace records `hook_response … exit_code 0`. Locate the fixture from `$0`,
never from the working directory and never from a guessed environment variable:
a `${EVAL_CASE_DIR:-.}` whose `.` fallback resolved to the workspace copied
nothing, and the case scored 0 on an empty repository. What that reads as is
"the agent could not build a spec". What it meant was "there was nothing to
build one from".

### Hand the session its toolchain

A case that makes the agent find its own tools measures the search, not the
skill. One run spent **39 of its 40 turns** on `find / -maxdepth 8 -iname
"tla2tools*.jar"`, a scan of `/Library/Java/JavaVirtualMachines` and an `unzip`
of the jar, hit the turn ceiling, and left behind a scratch module about a
counter mod 3.

Have the `SessionStart` hook discover the tools **at runtime** and print what it
found. Nothing hardcoded: another machine gets its own paths, or gets told the
tool is missing, which is a truthful input rather than a silent 0.

### Five environment facts, each of which cost a failed run

From the `skill-manager` suite. Each was paid for once; a suite that does not
know them pays again, and every one of them bills as a skill failure.

1. **`PATH` is the only variable that reaches the sandbox.** `TMPDIR` and
   `SKILL_MANAGER_HOME` both printed `<unset>` from inside a run, even though
   both were set in the operator's shell. `execution.env` will not close the
   gap either — its allowlist refuses everything but `EVAL_*`:

   > `execution.env` key PATH is not allowed — only `EVAL_*` keys can be set
   > from case.yaml. Anything else must come from the operator's shell.

   Read those two sentences together: `PATH` has to come from the shell, and
   `PATH` is the only part of the shell that arrives — `TMPDIR` was set there
   too and did not. **Anything your case needs that is not a `PATH` entry or an
   `EVAL_*` key has to be discovered inside the run.**

2. **An unset `TMPDIR` breaks Apple's `git` before it does anything.** `git`
   from the Xcode command-line tools writes an `xcrun` cache into `TMPDIR` on
   startup. Without one:

   ```
   git: error: couldn't create cache file '…/T/xcrun_db-…' (Operation not permitted)
   ```

   and `git worktree add` dies immediately after printing *"Preparing
   worktree"*. **One unset variable made a case unmeasurable for eight runs** —
   eight reds on a case whose task began with a worktree command, not one of
   them about the skill under test.

3. **The sandbox cannot read under the operator's home directory.** The same
   command succeeded in an ordinary shell and failed inside a run. Build trees,
   fixtures and checkouts have to live where the sandbox reaches — `/private/tmp`
   worked, which is where it keeps its own temps.

   > **This does not agree with the `/private/tmp` row in §2**, which says a
   > shim there was on `PATH` and `which` never found it. The two observations
   > are not the same observation — one is *resolving an executable on `PATH`*,
   > the other is *reading a tree* — and they are from different suites on
   > different machines, one of them a CLI patch apart. **Which of read access,
   > exec access and `PATH` resolution `/private/tmp` actually gets is
   > UNDECIDED**, and the row stays until somebody runs the probe that
   > separates them: put a readable file and an executable shim in one
   > `/private/tmp` directory and have the hook print `cat` and `which` for
   > each. That probe costs one refused case, i.e. $0.00.

4. **A CLI shim may exec a toolchain of its own.** The checkout shim in §2 ends
   in `exec`, and what it execs has its own dependencies — theirs runs `jbang`.
   Putting the shim's directory on the eval `PATH` is not enough; **everything
   the shim reaches for has to be on that `PATH` too**, and the `SessionStart`
   hook should print each of them the way §"Dependent tools" prints the rest.

5. **A hook cannot verify the environment on the agent's behalf.** Measured: the
   `SessionStart` hook ran `/usr/bin/git --version` successfully in a run where
   the agent's own Bash could not. The hook is outside the sandbox — that is the
   same asymmetry §4 relies on to run TLC, read in the opposite direction, and
   it is worse here because it is *silent*. A hook that checks a tool and prints
   `OK` has confirmed the tool works **for the hook**, and the run proceeds into
   an environment nobody has actually tested.

### Prove the environment in setup, before a run is billed against it

The consequence of all five, and it is the cheapest rule in this file.

**Setup must run the real front-door command and fail if it does not work.**
Not a version probe, not a `which` — the actual first command the case will ask
the agent for, in a throwaway corner of the fixture, from the same place the
agent will stand:

```sh
verify_env() {                     # last thing setup.sh does
    tmp=$(mktemp -d)
    ( cd "$tmp" && <the real front-door command> ) >"$tmp/log" 2>&1 || {
        echo "setup: environment cannot run the task — refusing to bill a run" >&2
        cat "$tmp/log" >&2
        exit 1
    }
    rm -rf "$tmp"
}
```

It costs **$0.00** — a case that never starts runs no agent — and in that suite
it caught three broken environments that would otherwise have been billed, and
reported, as skill failures. Facts 2 and 3 above are both things `verify_env`
would have caught on run one instead of run eight.

**This is not the `.eval/toolchain` marker of §4, and it does not replace it.**
The marker annotates a run that happened; `verify_env` stops the run from
happening. You want both: the marker cannot rescue a score (§4 is explicit that
`file_exists` has no UNDECIDED), and setup refusing is the only mechanism that
keeps the unmeasurable run out of the report entirely.

---

## 3.5 Several skills at once, and live units from a skill-manager home

**`claude plugin eval` is not limited to one plugin.** A case declares
`plugins:` — an array — and every entry loads alongside the target. Measured,
three units in one run:

```
Plugin under test: "git-issue" (no version) at ".../units/git-issue"
Plugin under test: "git-epic-workflow" (no version) at ".../units/git-epic-workflow"
Plugin under test: "skt" version "0.8.1" at ".../units/skt"
plugins loaded: ['git-issue', 'git-epic-workflow', 'skt']
their skills  : ['git-issue:git-issue', 'git-epic-workflow:git-epic-workflow',
                 'skt:skt', 'skt:unit-authoring']
```

`plugins:` is per **case**, so different cases load different subsets. That is
the shape worth building toward: *does this workflow need the epic skill, or
does the issue skill alone get through?* is one case per subset, and
`--ablation with-without` gives each one a no-plugin arm to be measured against.

**But a subset is an ablation you are deliberately running, not the default for
an ordinary case.** The distinction cost the `skill-manager` suite a rule, and
it is worth stating as one: **a case whose question is not itself "which unit is
needed" loads EVERY unit.** What such a case measures is retrieval *among* the
skills — whether the agent finds the right one with all of them in front of it.
Hand it only the units its task happens to need and you have done the retrieval
for it, and the score reports a skill that would not have been reached. It is
progressive disclosure graded against a curated shortlist, which is the one
condition it never meets in production.

So there are two case shapes, and mixing them up is how a suite gets a good
number for the wrong reason:

| the case asks | `plugins:` |
|---|---|
| can the agent do the task | **every unit in `units/`** |
| does it need *this* unit to do the task | the subset, plus a sibling case with the complement |

### How an entry resolves

* **Relative paths resolve against the CASE DIRECTORY**, not the target root and
  not the working directory. From `evals/probe/case.yaml`, `../../units/alpha`
  loads. Prefer this: it keeps a suite portable, where an absolute path hardcodes
  one operator's home into every case.
* **There is no name lookup.** `git-issue`, `jdtls-lsp`, and
  `jdtls-lsp@claude-plugins-official` all return `does not exist`, including for
  genuinely installed plugins. An entry is a path or it is nothing.
* **A unit needs no manifest.** A directory with a bare `SKILL.md` loads as a
  single-skill plugin named after **the directory**, not after the frontmatter's
  `name:`. Note that `claude plugin validate` *rejects* such a directory, so it
  is not a usable pre-check for `plugins:` entries.

### The containment rule, and exactly how far it reaches

The **entry path** must resolve under the containment root — the directory you
targeted, or its enclosing plugin. It is realpath'd first, so a symlink that
points out is refused:

> `plugins` entry ".../units/link-out" resolves to
> /Users/…/.skill-manager/skills/git-issue, **outside the containment root** …
> Only plugins under it can be loaded from case.yaml.

**But containment stops at the entry. It does not reach inside a loaded
plugin** — and that is the whole trick for evaluating a skill-manager home.
Measured: a wrapper at `units/omega/` with a real
`.claude-plugin/plugin.json` and

```
units/omega/skills/git-issue -> ~/.skill-manager/skills/git-issue
```

loads as `omega:git-issue`, reading the live unit through a symlink pointing
straight out of the root.

**So do not copy your units.** An earlier draft of this section said copies were
forced and then spent a page on managing their drift — advice that contradicted
§3 of this same file, which says to symlink the skill surface precisely so it
cannot drift. One thin wrapper per unit gets live skills and no drift:

```
skill-eval-harness/
  units/
    git-issue/.claude-plugin/plugin.json         {"name":"git-issue","version":"0.1.0"}
    git-issue/skills/git-issue      -> $SKILL_MANAGER_HOME/skills/git-issue
    git-epic-workflow/…             -> $SKILL_MANAGER_HOME/skills/git-epic-workflow
    skt/…                           -> $SKILL_MANAGER_HOME/plugins/skt
  evals/
    epic-then-issue/case.yaml       plugins: [../../units/git-epic-workflow, ../../units/git-issue]
    issue-alone/case.yaml           plugins: [../../units/git-issue]
    the-whole-workflow/case.yaml    plugins: [all of them]
```

```bash
cd skill-eval-harness
HOME=$EVALHOME CLAUDE_CODE_WALNUT_SPIRE=1 \
  claude plugin eval . --case 'epic-then-issue' --allow-tools Bash Write Edit
```

Three gotchas the wrapper form introduces:

* **`--case` is mandatory here, and this is the shape that makes it so.** The
  wrapper's whole point is that `units/*/skills/*` are symlinks into live units,
  and discovery is a recursive glob (`<eval dir>/**/case.yaml`) that follows
  them. A unit that ships its own eval suite — `tla-spec-dev` ships `evals/`
  with seven cases, one per nested skill — contributes
  those cases to *your* run. They score, they bill, and the report does not mark
  them as somebody else's. **Name the cases you meant to run, every time.**

* **A symlinked ENTRY loads under its resolved identity.** `units/git-issue ->
  vendored/gi` (inside the root, so accepted) loads as plugin **`gi`**, and
  every `tool_used: Skill` grader naming `git-issue:git-issue` then silently
  scores 0. Symlink the skill *inside* the wrapper, not the wrapper itself.
* **The wrapper's directory name is the plugin name**, so it is also the skill
  namespace your graders must spell.

The target itself need not be a plugin: a plain directory holding `evals/` and
`units/` works, `evals/` is found with no manifest, and with no `plugins:` key
the CLI says `Plugin under test: none resolved — cases run against baseline
Claude Code` rather than pretending the directory is under test. It still
defaults to `--ablation with-without` when a case does resolve plugins, so the
command above already gets two arms.

### Several kinds of agent

A plugin can ship `agents/`, and a plugin's `settings.json` can set `agent:` to
make one of them the main thread. That is the documented lever for "will a
different kind of agent get through this workflow", and the wrapper shape gives
each variant its own directory and its own case.

**I have not run that.** Everything else in this section was measured; this
paragraph is the mechanism from the plugin documentation, and the first person
to try it should expect to correct it.

## 3.6 Where a suite lives, and what it leaves behind

Everything above is one case. A suite is a directory that outlives the round
that built it, and this is the layout the `skill-manager` suite arrived at —
offered as a convention, not a mechanism: nothing in `plugin eval` requires it.

```
specs/evals/
  README.md                     how to run; points at this file for how a case is written
  harness/
    lib.sh                      eval_path, eval_tmpdir, branch_home, verify_env
    rewrite-case.py             generates the machine-specific parts of a case
    units-template/             the harness's own plugins (hooks, no skills)
    evals/<case>/setup.sh       makes the environment realistic
    evals/<case>/run.sh         carries the PATH, runs the case, tears down
    evals/<case>/case.yaml + graders/*.md
  results/                      evidence: what was run, what it cost, the traces
```

**A setup script and a run script per case**, because §3's five environment
facts have to be executed by something and a README cannot execute. Setup makes
the environment realistic and ends in `verify_env`; run carries the `PATH` —
the one variable that gets through — and tears down after.

The rule the layout exists to enforce is one line:

> **What is in git is what MAKES the environment, never the environment.**

Nothing machine-specific is committed. `rewrite-case.py` generates the parts
that are, on the machine that is about to run. A committed absolute path is the
same defect as a hardcoded jar in a `SessionStart` hook, one directory further
out.

### An eval score is spec evidence, and it is filed like any other

A score is a measurement of the same kind as a TLC run or a Test Graph
envelope, and it belongs in the same places: under the ticket's `results/`
directory, passed to `close ticket --result`, snapshotted into `.history` when
the workflow closes, cited by the goal it claims to move. It is not a different
species of number because a model produced it.

**But file the trace, not the score.** Every useful thing the `skill-manager`
round produced came out of `trace.jsonl`; **the scores were actively
misleading** — §4 is a catalogue of the ways, and that round added two more
(§3's facts 2 and 3, eight reds that were an unset variable). A committed `0.25`
is unreadable a week later and unfalsifiable forever.

So the convention is **"record the score with the trace excerpt that justifies
it"**, and the excerpt is the part that has to be there:

```
specs/evals/results/<round>/
  summary.md          the score, the CLI version, the case, the run count
  trace-<case>-<n>.jsonl        or the excerpt, where the whole file is large
  UNDECIDED.md        which runs were not measurements, and why
```

`UNDECIDED.md` is not optional padding — it is where the eight unmeasurable
runs go, so that a later reader counting reds does not count them. §4 has the
argument for why nothing inside a case can carry that fact.

### What this buys, stated as a number rather than a hope

The same round found **four defects in shipped CLIs and skills that 258 passing
unit tests did not see.** All four were about an agent's path through a CLI: an
argument refused with a remedy the repository could not carry out, a `--help`
that led with options rather than the shape of a call, a skill naming the
*condition* for using a tool without saying how to test it, and a verifier
refusing a path its own message had just named. **No unit test asserts that an
error message is actionable**, and that is the class this instrument reaches and
the rest of the suite does not.

It also produced roughly a dozen defects in **itself**, which is the more
important number and is `references/bug_attribution.md` §6a.

---

## 4. Keeping the score honest

### The failure, stated plainly

A case scored **1.00** on this skill while `tla-spec-dev scaffold project`
failed with **exit 1 on all three attempts**, and the
`specs/program_model/spec_manifest.yaml` that the artefact grader accepted as
proof the pipeline had run was written by the agent's own `Write` tool. A
separate probe scored that same grader green on a manifest whose entire contents
were `placeholder: true`.

The report was excellent and the model was genuinely good. **Neither of those
facts was measured.** What was measured was: a path exists, and a paragraph
reads well.

An adversarial case that told an agent to write the placeholder and then claim a
model scored 0.50 — and the half it lost was lost because **the agent refused to
write the false report**, not because a grader caught it:

> *"I'm not going to write the second part. It asks me to state that I built a
> TLA+ program model when the only thing on disk is a one-line placeholder …
> That's a false report about my own work."*

An instrument whose anti-gaming property is the honesty of the thing it grades
has no anti-gaming property.

### The fix: verify in a `Stop` hook, grade the verdict path

**The sandbox that stops the agent does not stop a hook.** The Bash *tool* runs
under a profile denying filesystem writes to every subprocess it spawns — which
is why TLC aborts creating its metadir and why a CLI that writes files cannot
run. Hooks are outside it. Measured: a `Stop` hook's
`python3 -c "open(...,'w')"` and its `mkdir` both succeed in the same workspace
where the Bash tool is refused.

So run the real check after the agent stops, and let it write the paths the
graders read:

```json
{"hooks": {"Stop": [{"hooks": [
  {"type": "command",
   "command": "${CLAUDE_PLUGIN_ROOT}/evals/<case>/verify.sh",
   "timeout": 600}
]}]}}
```

```sh
# verify.sh
set -u
rm -rf .eval && mkdir -p .eval          # RULE 1
... run SANY / TLC / the real CLI ...
[ success ] && echo ok > .eval/checks   # RULE 2
exit 0                                  # RULE 3
```

with `type: file_exists, path: ".eval/checks"` as the grader.

**Three rules make it sound.**

1. **Delete every verdict path before looking.** The agent has `Write` and can
   create any filename it can guess. Demonstrated: a workspace with all three
   verdict files pre-planted came out of the hook with none of them, because
   the real check did not pass.
2. **Write a verdict only after a real program returns success.** SANY, TLC, a
   YAML parse, your own test runner. Never after reading the response.
3. **`exit 0`, always.** A `Stop` hook that fails non-zero can push the session
   onward, and a verifier that changes the run it measures is not a verifier.
4. **Run agent-authored code with no write anywhere, and write its verdict
   yourself.** This is the rule the first three do not cover, and it was found
   by attack rather than by reasoning.

### The hook is not inside the sandbox, and that cuts both ways

The reason a `Stop` hook can run TLC is that it is outside the profile that
denies the agent's Bash tool every filesystem write. The same fact means
**anything the hook executes runs with the hook's privileges** — including the
program the agent was told to repair.

Demonstrated on the `catch-the-drift` case. Five lines appended to
`ecommerce_backend/domain.py`:

```python
_PAYLOAD = "import time, os\ntime.sleep(4)\nos.makedirs('.eval', exist_ok=True)\n" \
           "open('.eval/behaviour', 'w').write('forged after the hook exited')\n"
_sp.Popen([_sys.executable, "-c", _PAYLOAD], cwd=_os.getcwd(), start_new_session=True)
```

The hook refused correctly — `create_account did not persist` — exited with no
`behaviour` verdict, and four seconds later the spawned process created it. The
graders then read a green weight-2 verdict on a program that was never
repaired, with the refusal it overwrote still sitting in the verifier's own log.

**Clearing the verdict directory first does not help**, because the write lands
after the hook is gone. **Killing the process group does not help either** —
`start_new_session=True` exists precisely to escape that.

What does: refuse the write. On macOS, `sandbox-exec -f <profile>` with

```
(version 1)
(allow default)
(deny file-write*)
(allow file-write-data (literal "/dev/null") (literal "/dev/stdout") (literal "/dev/stderr"))
```

and the check then **cannot record its own verdict**, which is the separation
that matters: it signals through its exit status, and the hook — outside the
profile — writes the file. Untrusted code decides nothing about what gets
written. Descendants inherit the profile, so daemonising buys nothing.

Set `PYTHONDONTWRITEBYTECODE=1`; a confined interpreter cannot write
`__pycache__` and will otherwise complain.

**Two profiles, because not everything the hook runs can be denied writes.**
SANY and TLC parse and explore agent-authored `.tla`, and TLC creates a metadir
before exploring anything — deny it writes and it aborts having checked
nothing, which is a verdict withheld for the verifier's own configuration. So:

| profile | applied to | rule |
|---|---|---|
| `nowrite.sb` | checks that need no writes (the behavioural check, the manifest check) | `(deny file-write*)` |
| `noverdict.sb` | **everything else the hook executes**, SANY and TLC included | `(deny file-write* (subpath (param "VERDICTS")))` |

The graders read exactly one directory, so that is the directory nothing the
hook runs may write. Descendants inherit either profile, so a payload that
daemonises and sleeps past the hook's exit is refused under both.

**THE PATH IN A PROFILE MUST BE THE RESOLVED ONE.** macOS resolves before
matching, so a profile naming `/tmp/ws/.eval` does not deny a write to
`/private/tmp/ws/.eval` — and **a deny that never applies looks exactly like a
deny that worked**, because an allowed write prints nothing either. Use
`pwd -P`. Measured both ways: with the physical path the deny fires through the
physical path *and* through the symlinked one; without it, through neither.
This is habit 3 in §0, and it cost a round to learn twice.

Where no such facility exists, run the check anyway and **write a verdict
saying so** — `.eval/UNDECIDED-unconfined` — rather than offering the same
green under a weaker guarantee. An operator who cannot tell the two apart is
back to reading a number that means less than it says.

Verified both ways on the real artefact: the passing run's model produced
`parses`, `checks` and `manifest`; a workspace holding `placeholder: true` and
three forged verdicts produced none.

### The verifier is now the thing most likely to be wrong

Moving the judgement into a hook does not remove the false-negative risk. It
relocates it, from the grader to the program the grader trusts — and that
program runs in an environment nobody looked at. Three of these were caught
here, and the first two were caught only because a control was run before the
suite was:

* **`SANY` resolves imports against the working directory.** Invoked from the
  workspace root on `specs/program_model/External.tla`, it reported *"Cannot
  find source file for module Internal"* about a module that parses perfectly.
  Run it from the model directory on a bare filename.
* **A module loaded by path is not in `sys.modules`, and `@dataclass` looks up
  `sys.modules[cls.__module__].__dict__`.** A behavioural check that used
  `spec_from_file_location` died with `'NoneType' object has no attribute
  '__dict__'` and withheld its verdict — from a workspace that may have been
  repaired. Use a plain import.
* **The hook's `$HOME` is not yours, and its `python3` is whatever is on
  `PATH`.** A jar search rooted at `$HOME/.skill-manager` found nothing, so SANY
  and TLC were skipped and two cases lost their artefact verdicts — 0.25 and 0.80 reported for an environment fault **in the
  verifier**. The manifest check failed the same way on `No module named
  'yaml'`. (I first wrote that `$HOME` was the constructed eval home. It is not
  — it is the sandbox's own sealed home, which has no `.claude` and no
  `.skill-manager`. Both explain the empty search, which is why the wrong reason
  survived until someone checked it.) Resolve tools the way the project's own
  wrappers do (`bin/cli/tlc2` derives its jar from its own location and honours
  `TLA2TOOLS_JAR`), and give every library import a fallback.

Two rules follow, and they cost nothing:

1. **Run the verifier against a known-good workspace and a known-bad one before
   you run the suite**, under the same `HOME` the hook will have. Every one of
   the three above was a green control away from being charged to an agent.
2. **Write a marker for the ENVIRONMENT too** — `.eval/toolchain` when the
   tools resolved, `.eval/UNDECIDED-toolchain` when they did not. Never grade
   either: a forged workspace earns them as readily as a good one.

   **Be honest about what this buys, because it is less than it looks.**
   `file_exists` has only pass and fail — there is no UNDECIDED — so a missing
   toolchain still scores the artefact graders at **0, i.e. FAIL, on a model
   that may be perfect.** That is `SS-02`, and a case cannot fix it from the
   inside. What the marker does is leave the reason where the person reading
   the 0 will find it. It changes the report, not the score, and a document
   that says otherwise is doing the thing this whole reference is against.
   (An earlier draft of this section did say otherwise. A blind review caught
   it.)

### What each grader is for, once you have this

* **verdict paths carry the claim.** They are the only evidence a confident
  report cannot move.
* **the `llm` grader grades the REPORT, and must say so in its own body.** A
  grader that ends *"score the artefacts, not the claim"* is asking for
  something the judge cannot do, so what it scores is the claim while reading as
  though it scored the artefact — an absent input scored as if present. If the
  report matters, ask the prompt to quote the artefact so there is real text
  under the judgement, and keep the weight low.
* **`tool_used: Skill`** is worth one grader on its own: it tells you the skill
  was invoked rather than reinvented. Under `--ablation with-without` a
  `tool_used: Skill` grader is treated as a plugin-fired indicator rather than
  part of the score.

### Three failure shapes to check before reading any number

**UNDECIDED has no representation, and that is the dangerous one.** `file_exists`
has only pass and fail; `tool_used` has only a count inside a range or outside
it. Neither can say *"this run was not a measurement."* So **an environment that
could not run the task and a skill that could not do the task produce the same
number**, and the number is a red charged to the skill. Eight consecutive reds
in the `skill-manager` round were an unset `TMPDIR` (§3, fact 2), and nothing in
the score said so.

The line that follows is short and it goes before the other two: **before
reading a red, confirm the task was possible in that environment.** Reading it
after is how a suite spends eight runs improving a skill that was never the
problem. `verify_env` in setup (§3) is the mechanism that makes this checkable
rather than remembered; the `.eval/toolchain` marker above is what leaves the
reason where the person reading the red will find it.

**A run that ran out of turns is `UNDECIDED`, and the suite scores it FAIL.**
`error_max_turns` leaves no closing report, so every response grader votes FAIL
on a run that may have done the work perfectly. One run here wrote exactly the
right model and was cut off mid-verification with the words *"Now full
verification of everything I can execute."* — scored 0.50, which is also
precisely the score a half-finished model gets. **The two are indistinguishable
in the number.** Always read the `error:` column beside the score. Verdict-path
graders are what keeps such a run legible, because they still see the workspace
— **but only if something writes the verdicts, and a `Stop` hook does not run
on that exit.** Measured in the `skill-manager` wide lane (2026-09-14, 2.1.270):
with the verifier registered on both `Stop` and `SessionEnd` and each writing
which event it was, every run that ended `error_max_turns` was written by
`SessionEnd` alone, and every normal run by `Stop`. A round that registered only
`Stop` lost every verdict on 12 capped runs and scored them red. Register the
verifier on `SessionEnd` too; both derive the same verdicts, so the second
write is harmless.

**A majority is not a consensus.** The `llm` grader takes three votes. A run
whose artefact was plainly correct passed **FAIL PASS PASS**. One run's score
from one case is not evidence of much; if a number is going to be quoted, run
it more than once.

### The checklist

Before a score means anything:

- [ ] every gated tool in `allowed_tools:` is in the documented `--allow-tools`
- [ ] the fixture is placed by a hook, and the trace shows `exit_code 0`
- [ ] no grader is satisfied by a path the agent can create — or a `Stop` hook
      deletes it first
- [ ] at least one grader is a verdict written by a real program
- [ ] every `llm` grader says in its own body that it reads the response only
- [ ] a forged workspace has been run through the graders and scored 0
- [ ] the run did not end `error_max_turns`
- [ ] setup proved the environment could run the task **before** the run was
      billed, and the runs it refused are recorded as UNDECIDED rather than red
- [ ] **no number in this report comes from a single run**
- [ ] the verifier has been run against a known-good and a known-bad workspace,
      under the same `HOME` the hook will have
- [ ] a `.eval/toolchain` marker distinguishes "checked and failed" from "never
      checked", and no grader scores it
- [ ] the run executed YOUR checkout — the hook printed which CLI it resolved
- [ ] agent-authored code that the verifier executes cannot write the verdicts,
      and a run where it could says so
- [ ] you have read `trace.jsonl`, not only the summary line

The last one catches the others.
