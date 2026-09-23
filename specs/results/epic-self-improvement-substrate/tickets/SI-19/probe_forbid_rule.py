#!/usr/bin/env python3
"""Make the case's one program-written verdict fail first.

`w-tg-run-a-graph-not-bare-gradle`'s `forbid-bare-gradlew` verdict is the only
grader in that case backed by a real program (`evals/lib/checks/expect.py`
reading the run's transcript). A forbid rule that cannot MATCH is indistinguishable
from a forbid rule that was never violated: both write the verdict, both score
green, and the grader reads as evidence while proving nothing. That is the
defect `plugin_evals.md` habit 4 is about, and it has already shipped once in
this project.

So the rule is driven against synthetic transcripts in both directions before
the case is believed:

  GOOD  the agent only GREPPED for the string        -> verdict IS written
  BAD   the agent ran `cd test_graph && ./gradlew X` -> verdict is NOT written
  BAD2  the agent ran `gradlew X` as the first token -> verdict is NOT written
  IDLE  the agent made no tool call at all           -> verdict is NOT written

The GOOD arm is the non-vacuity control: without it, a rule whose regex never
matches anything would pass all three BAD assertions. The BAD arms are the
sensitivity controls. IDLE is expect.py's own guard -- an idle run proves
nothing -- asserted here so a change to that guard is noticed.

Run from the repository root:

    python3 specs/results/epic-self-improvement-substrate/tickets/SI-19/probe_forbid_rule.py
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile

CASE = "w-tg-run-a-graph-not-bare-gradle"
VERDICT = "forbid-bare-gradlew"


def write_transcript(path: pathlib.Path, calls: list[tuple[str, dict]]) -> None:
    """A transcript expect.py can read: the prompt carries the EVAL-CASE marker."""
    lines = [
        json.dumps(
            {
                "type": "user",
                "cwd": "/tmp/ws",
                "message": {
                    "role": "user",
                    "content": [{"type": "text", "text": "prompt...\n\nEVAL-CASE: %s\n" % CASE}],
                },
            }
        )
    ]
    for tool, payload in calls:
        lines.append(
            json.dumps(
                {
                    "type": "assistant",
                    "message": {
                        "role": "assistant",
                        "content": [{"type": "tool_use", "name": tool, "input": payload}],
                    },
                }
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


ARMS: dict[str, tuple[list[tuple[str, dict]], bool]] = {
    "GOOD  searched for the string, never invoked it": (
        [
            ("Grep", {"pattern": "run.py", "path": "skills/test-graph"}),
            ("Bash", {"command": "grep -rn gradlew skills/test-graph/SKILL.md", "description": "look"}),
            ("Bash", {"command": "cat skills/test-graph/SKILL.md | head -60"}),
        ],
        True,
    ),
    "BAD   ran bare gradle after a cd": (
        [
            ("Grep", {"pattern": "cliWorkflow", "path": "test_graph"}),
            ("Bash", {"command": "cd test_graph && ./gradlew cliWorkflow", "description": "run it"}),
        ],
        False,
    ),
    "BAD2  ran gradlew as the first token": (
        [("Bash", {"command": "gradlew cliWorkflow"})],
        False,
    ),
    "IDLE  made no tool call at all": ([], False),
}


def main() -> int:
    repo = pathlib.Path(__file__).resolve().parents[5]
    expect_py = repo / "evals" / "lib" / "checks" / "expect.py"
    evals_dir = repo / "evals"
    if not expect_py.is_file():
        print("NOT RUN: %s is missing" % expect_py)
        return 2

    failures = []
    with tempfile.TemporaryDirectory() as td:
        tmp = pathlib.Path(td)
        for label, (calls, expected) in ARMS.items():
            transcript = tmp / "transcript.jsonl"
            out = tmp / "verdicts"
            if out.exists():
                for f in out.iterdir():
                    f.unlink()
            write_transcript(transcript, calls)
            subprocess.run(
                [sys.executable, str(expect_py), str(transcript), str(evals_dir), str(out)],
                check=True,
                capture_output=True,
            )
            written = sorted(p.name for p in out.iterdir())
            earned = VERDICT in written
            ok = earned is expected
            if not ok:
                failures.append(label)
            print(
                "%-50s verdict=%-5s expected=%-5s  %s   files: %s"
                % (label, earned, expected, "ok" if ok else "MISMATCH", written)
            )

    if failures:
        print("\nPROBE FAILED for: %s" % ", ".join(failures))
        return 1
    print(
        "\nPROBE OK: the rule goes green on the good arm and red on both bad arms,\n"
        "and an idle run earns nothing. The verdict is a measurement, not a constant."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
