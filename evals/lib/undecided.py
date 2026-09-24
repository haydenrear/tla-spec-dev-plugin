"""Which of the selected cases cannot be decided in this view? Prints them.

WHY THIS EXISTS (EA-DF-08). Six cases have a REAL branched Skill Manager home as
their fixture. A home is ~41,000 entries and `claude plugin eval` refuses a
plugin directory over 20,000, so the fixture cannot be staged. That was handled
with care on the writing side: `place.sh` prints the reason into the run's own
trace and `verify.sh` writes `.eval/UNDECIDED-needs-home` next to the verdicts.

Neither reaches the operator. `claude plugin eval` prints one summary table, it
knows nothing about `.eval/`, and the sandbox holding that file is deleted
unless the run was started with `--keep-temp`. So the screen says

    ✗ ticket-agent-opens-a-ticket  score 0.27  (1 run)

and the reason the score is meaningless is three layers away. Measured on
2026-09-24, on this epic's first billed rung: the epic agent read those scores
as substrate failures, wrote them up as "the agent never issued the front door",
and called them the highest-value cases in the corpus. Every safeguard the
design put in place had fired correctly and none of them was on the screen where
the number was.

`place.sh` is the single source of truth and is PARSED rather than copied: a
second list here would go stale the first time a seventh case needs a home, and
a stale list in an instrument that exists to prevent misreading is worse than no
list at all.

THIS NEVER REFUSES. It prints and returns 0 even when it can read nothing --
`GOAL-no-new-gates`, and an eval that blocks is a gate wearing a lab coat. A
case being UNDECIDED is a fact about the view, not a fault in the work.

Usage: undecided.py <evals-dir> <case-glob>
"""

from __future__ import annotations

import fnmatch
import pathlib
import re
import sys

#: The shell function in `place.sh` whose callers are the cases that cannot run.
MARKER = "undecided_needs_home"


def needs_home(place_sh: pathlib.Path) -> list[str]:
    """Case labels in `place.sh` whose arm calls `undecided_needs_home`.

    Parses the `case "$case_name" in` arms: a label line `  some-case)` opens an
    arm and `;;` closes it. An arm naming the marker anywhere inside counts.
    Returns [] rather than raising if the file is unreadable — a missing
    source of truth must not take the run down with it.
    """
    try:
        text = place_sh.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    found: list[str] = []
    label: str | None = None
    body: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        # A label line is `<name>)` — one token, no spaces, not a glob arm we
        # care about. `*)` and `esac` end the interesting region harmlessly.
        opened = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)\)\s*$", stripped)
        if opened:
            label, body = opened.group(1), []
            continue
        if label is None:
            continue
        if stripped == ";;":
            if any(MARKER in entry for entry in body):
                found.append(label)
            label, body = None, []
            continue
        body.append(stripped)
    return found


def main() -> int:
    root = pathlib.Path(sys.argv[1])
    glob = sys.argv[2] if len(sys.argv) > 2 else "*"

    selected = []
    for case in sorted(root.rglob("case.yaml")):
        text = case.read_text(encoding="utf-8", errors="replace")
        match = re.search(r"^name:\s*(\S+)", text, re.M)
        name = match.group(1).strip("\"'") if match else case.parent.name
        if fnmatch.fnmatch(name, glob):
            selected.append(name)

    blocked = sorted(set(needs_home(root / "lib" / "place.sh")) & set(selected))
    if not blocked:
        return 0

    total = len(selected)
    print("")
    print(f"UNDECIDED: {len(blocked)} of {total} selected case(s) could not be "
          f"decided in this view.")
    print("Their scores above are NOT a verdict on the work and must not be "
          "averaged with the rest.")
    for name in blocked:
        print(f"  {name}")
    print("")
    print("  Reason: the fixture is a real branched Skill Manager home "
          "(~41,000 entries);")
    print("          `claude plugin eval` refuses a plugin directory over "
          "20,000, so it")
    print("          cannot be staged. See evals/README.md, 'The six that need "
          "a home'.")
    print("  The run wrote `.eval/UNDECIDED-needs-home` inside each sandbox; "
          "re-run with")
    print("  --keep-temp to read it, along with any UNDECIDED verdict raised "
          "at run time")
    print("  (toolchain, unconfined, notranscript), which this line cannot "
          "know in advance.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
