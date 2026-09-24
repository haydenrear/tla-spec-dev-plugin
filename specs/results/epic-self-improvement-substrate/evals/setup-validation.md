# Validating the eval setup itself

Recorded 2026-09-24 at `5ec49a58`. This file is the evidence that
`evals/setup-eval-home.sh` does something — because a checker nobody falsified
is a checker nobody has tested, and this session shipped two things that looked
correct and did nothing (a fixture that was never tracked, a hook that returned
zero bytes).

## Why the script exists

Four prerequisites, each of which was discovered by hitting it rather than by
reading anything. The Docker one was rediscovered twice in one day, at the cost
of reading three files each time.

| prerequisite | symptom without it |
| --- | --- |
| scratch `HOME` with a symlink-free `.docker` | **60 of 64 cases score 0.00**, with a credential-store message that reads like a broken substrate |
| `Library/Keychains` linked into that home | every run fails to authenticate |
| JDK 21+ | `skill-manager` never starts; its cases grade an agent that cannot run it, **silently, at 1.00 in five of six** |
| python 3.11+ | skt's SessionStart hook injects nothing; the session loses the line naming the next command |

Every one of those symptoms is a plausible number rather than an error. That is
the whole reason the checks are code.

## `HOME` is the only lever, and the two obvious alternatives were tried

* **`DOCKER_CONFIG` pointed elsewhere does nothing.** The check reads
  `~/.docker` regardless; the refusal message is byte-identical. Measured twice,
  once before reading the README that already said so.
* **`SKILL_MANAGER_HOME` is a different question.** It selects which
  skill-manager home a run uses and has no bearing on the sandbox's
  credential-store scan.

Overriding `HOME` fixes the sandbox and **breaks authentication**, because the
login credential is in the keychain and the keychain path is HOME-relative. The
two constraints are only satisfiable together: a scratch home that also links
`Library/Keychains`. That pairing is the design, not an implementation detail.

## The controls

`--check` inspects the shape of the setup. Falsified three ways:

```
inject a symlink under .docker    MISS, exit 1   removed   -> exit 0
move Library/Keychains away       MISS, exit 1   restored  -> exit 0
point at a nonexistent home       6 MISS, exit 1
```

**The third control found a vacuous pass in the checker itself.** `find` on a
path that does not exist reports zero symlinks, so "no home at all" was printing
`ok .docker holds no symlinks`. Absence was reading as cleanliness, on the one
check standing between a run and 60 zeros. An empty result is not a passing
result. Closed, and that control now prints `MISS .docker does not exist --
nothing to check, which is not the same as clean`.

## The smoke test, and the control that makes it mean something

`--smoke` bills one case and **asserts a 1.00**. It does not check that the
command ran: a run that fails to place its fixture, or whose tool grant is
wrong, still exits 0 with a score of 0.00.

Working lane:

```
all checks passed.
eval: SKT_PYTHON=/opt/homebrew/bin/python3.14
eval: java -- java version "21" 2023-09-19 LTS
eval:   the CLI starts: skill-manager 0.28.1+g7941f4e1dd9e
  w-harness-smoke run 1/1: score 1.00  $0.10
smoke: PASSED -- w-harness-smoke scored 1.00, so the lane is real
exit 0
```

Deliberately broken lane (`EVAL_HOME` pointed at a path that does not exist):

```
6 x MISS
  w-harness-smoke run 1/1: score 0.00  $0.00
    error: the Docker (~/.docker, DOCKER_CONFIG) credential store ... holds a
    symbolic link inside it, so the Bash sandbox cannot reliably exclude it
smoke: FAILED -- w-harness-smoke did not score 1.00.
exit 1
```

**So the smoke passes when the lane works and fails when it does not**, which is
the only property that makes it worth running. Note the cost of the failing
arm: **$0.00**, because the sandbox refuses in two seconds. Detecting a broken
lane is free; discovering it 60 cases later is not.

Those four `eval:` lines are also the receipt for the day's fixes — the scratch
home (no refusal), the orientation interpreter, the JDK, and the CLI starting on
its pinned commit rather than the operator's brew install.

## What a future session has to remember

Nothing. `run.sh` defaults `EVAL_HOME` to `.toolchain/evalhome` and says which
home it took. The whole eval toolchain — pinned checkout, jbang cache, scratch
home — lives under `.toolchain/`, which is gitignored, so `rm -rf .toolchain`
is the reset button and `evals/setup-eval-home.sh --smoke` rebuilds and reproves
it in about ten cents.

Run `--smoke` after any change to `run.sh`, `lib/place.sh`, `lib/verify.sh` or
the hooks. All four were changed today and each one could have silently voided
the suite.
