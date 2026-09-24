#!/usr/bin/env python3
"""Drive SI-20's two expect.json rule sets BOTH WAYS against synthetic calls.

A rule that cannot match looks exactly like a rule nobody violated: both write
the verdict, both score green. So each rule is driven against a transcript that
must earn it and one that must not, and the assertion is on BOTH directions.

Nothing here executes anything from a transcript; `expect.verdicts` is pure.

    python3 specs/results/.../SI-20/probe_expect_rules.py
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[5]
assert (ROOT / "evals" / "lib" / "checks" / "expect.py").is_file(), f"repo root wrong: {ROOT}"
sys.path.insert(0, str(ROOT / "evals" / "lib" / "checks"))
import expect  # noqa: E402


def call(tool: str, payload: dict) -> tuple[str, str]:
    return (tool, json.dumps(payload))


def load(case: str) -> dict:
    return json.loads((ROOT / "evals" / "skt" / case / "expect.json").read_text())


CHECKS: list[tuple[str, str, dict, list[tuple[str, str]], dict]] = []

A = "w-skt-worktree-leaves-the-integration-repo"
CHECKS += [
    (A, "read lib.sh with Read -> earned", load(A),
     [call("Read", {"file_path": "skills/git-issue-workflow/scripts/lib.sh"})],
     {"require-read-the-lifecycle-source": True, "forbid-made-a-worktree": True}),
    (A, "grepped lib.sh -> earned", load(A),
     [call("Grep", {"pattern": "worktree_parent_dir", "path": "skills/git-issue-workflow/scripts/lib.sh"})],
     {"require-read-the-lifecycle-source": True, "forbid-made-a-worktree": True}),
    (A, "only read the python copy -> NOT earned", load(A),
     [call("Read", {"file_path": "skills/skt/src/skt/wt.py"})],
     {"require-read-the-lifecycle-source": False, "forbid-made-a-worktree": True}),
    (A, "ran `git worktree add` -> forbid RED", load(A),
     [call("Read", {"file_path": "skills/git-issue-workflow/scripts/lib.sh"}),
      call("Bash", {"command": "git worktree add ../x -b feature/y", "description": "reproduce"})],
     {"require-read-the-lifecycle-source": True, "forbid-made-a-worktree": False}),
    (A, "ran `skt ticket new` -> forbid RED", load(A),
     [call("Bash", {"command": "skt ticket new TG-1", "description": "reproduce"})],
     {"require-read-the-lifecycle-source": False, "forbid-made-a-worktree": False}),
    (A, "grepped FOR the phrase -> forbid still GREEN", load(A),
     [call("Bash", {"command": "grep -rn 'worktree add' skills/", "description": "find the rule"})],
     {"require-read-the-lifecycle-source": False, "forbid-made-a-worktree": True}),
    (A, "idle run earns nothing", load(A), [],
     {"require-read-the-lifecycle-source": False, "forbid-made-a-worktree": False}),
]

B = "w-skt-which-copy-of-skt-ran"
CHECKS += [
    (B, "read the generated wrapper -> earned", load(B),
     [call("Read", {"file_path": ".skill-manager/bin/cli/skt"})],
     {"require-read-the-wrapper-or-its-installer": True}),
    (B, "read the installer -> earned", load(B),
     [call("Read", {"file_path": "skill-scripts/install-skt.sh"})],
     {"require-read-the-wrapper-or-its-installer": True}),
    (B, "read only cli.py -> NOT earned", load(B),
     [call("Read", {"file_path": "skills/skt/src/skt/cli.py"})],
     {"require-read-the-wrapper-or-its-installer": False}),
    (B, "idle run earns nothing", load(B), [],
     {"require-read-the-wrapper-or-its-installer": False}),
]

fails = 0
for case, label, rules, calls, want in CHECKS:
    got = expect.verdicts(rules, calls)
    for key, expected in want.items():
        ok = got.get(key) is expected
        fails += 0 if ok else 1
        print(f"{'ok  ' if ok else 'FAIL'}  {case}  [{label}]  {key} = {got.get(key)} (want {expected})")

assert len(CHECKS) == 11, f"non-vacuity: the probe drove {len(CHECKS)} transcripts, not 11"
print(f"\nNON-VACUITY: {len(CHECKS)} synthetic transcripts, "
      f"{sum(len(w) for *_, w in CHECKS)} verdict assertions")

# ---------------------------------------------------------------- the response
# graders, driven the same way. A regex that cannot fail scores every answer
# green; a regex that cannot pass scores every answer red. Neither is visible
# from reading it, so each pattern gets an answer it must match and an answer it
# must not -- and the BAD arms are the wrong answers actually worth separating
# out, not strawmen: "this is a bug in skt", "PATH / clear the cache",
# "skill-manager sync skt" for a unit that is not standalone any more.
import re  # noqa: E402

RESPONSE = [
    ("names-the-marker", A, r"integration\.toml",
     ["The location was decided by an `integration.toml` in an ancestor directory.",
      "Because integration.toml sits at the repo root, the fixture is a constituent."],
     ["This is a bug in skt ticket new; it put the worktree in the wrong place."]),
    ("names-the-rule-and-its-reason", A,
     r"worktree_parent_dir|outermost|gitlink|160000",
     ["worktree_parent_dir() returns dirname of the outermost integration root.",
      "A parent `git add -A` would stage it as a gitlink (mode 160000).",
      "It goes beside the outermost enclosing integration repo."],
     ["skt classified the repo as a constituent, so the path differs."]),
    ("names-what-the-wrapper-resolves", B,
     r"plugins/\S*skills/skt|home (it|this wrapper|the wrapper|the shim|this shim) lives in",
     ["It runs .skill-manager/plugins/tla-spec-dev/skills/skt/src/skt/cli.py",
      "The wrapper resolves skt from the home it lives in, not from the checkout."],
     ["Your PATH is picking up a different skt; clear the cache."]),
    ("gives-a-command-that-runs-the-edit", B,
     r"install-skt\.sh|src/skt/cli\.py",
     ["Run `python3 skills/skt/src/skt/cli.py status`.",
      "Re-run skill-scripts/install-skt.sh against a home holding your copy."],
     ["Run `skill-manager sync skt` and try again."]),
]

print()
strings = 0
for name, case, pattern, good, bad in RESPONSE:
    # The pattern is read back OUT OF THE COMMITTED GRADER, not retyped here --
    # a probe that tests its own copy of a regex proves nothing about the file
    # the CLI will load.
    grader = pathlib.Path("evals/skt") / case / "graders" / f"{name}.md"
    body = grader.read_text()
    committed = [ln.split("pattern:", 1)[1].strip().strip("'\"")
                 for ln in body.splitlines() if ln.startswith("pattern:")]
    assert len(committed) == 1, f"{grader}: expected one pattern line, got {committed}"
    rx = re.compile(committed[0])
    for text in good:
        strings += 1
        ok = bool(rx.search(text))
        fails += 0 if ok else 1
        print(f"{'ok  ' if ok else 'FAIL'}  GOOD {name}: {text[:64]}")
    for text in bad:
        strings += 1
        ok = not rx.search(text)
        fails += 0 if ok else 1
        print(f"{'ok  ' if ok else 'FAIL'}  BAD  {name}: {text[:64]}")

assert strings == 13, f"non-vacuity: the probe drove {strings} strings, not 13"
print(f"\nNON-VACUITY: {strings} strings against 4 committed grader patterns, both arms")

if fails:
    print(f"{fails} FAILED")
    raise SystemExit(1)
print("both directions hold for every rule and every response grader")
