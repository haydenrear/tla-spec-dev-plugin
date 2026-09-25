"""Do the regex graders COMPILE in the engine that will run them? Warn if not.

WHY THIS EXISTS (SI-21). A `type: regex` grader body is compiled by the eval
harness's own JavaScript engine, not by Python's `re`. Three graders written
with Python inline flags -- `(?is)` -- were syntactically fine to every tool
that touched them on the way in, and produced this at scoring time:

    x names-tomllib-as-stdlib-from-311 (weight 4): grader threw:
      Invalid regular expression: unrecognized character after (?

Every grader in the case threw, the case scored **0.00**, and the run was
billed. The failure is indistinguishable at a glance from an agent that
answered badly: it is a red row with a score, not an error. Nothing checks a
grader pattern before a run spends money on it, and nothing did until this file.

WHAT IT IS NOT. It is not a gate. `GOAL-no-new-gates` is live and this file
predates nothing: it **prints and exits 0**, always, including when it finds
broken patterns and including when it cannot run at all. A grader that will
throw is worth a loud line before the bill, and worth nothing as a refusal --
the operator may be running a different case entirely.

HOW IT DECIDES. `node` compiles each pattern with `new RegExp(...)`. When node
is absent the check says so and exits 0; a missing checker must not read as a
clean bill of health, which is this epic's most repeated defect. The count of
patterns examined is printed either way, so a run that scanned NOTHING cannot
look like a run that found nothing wrong.
"""

from __future__ import annotations

import json
import pathlib
import re
import shutil
import subprocess
import sys

_NODE_SRC = r"""
const pats = JSON.parse(require("fs").readFileSync(0, "utf8"));
const bad = [];
for (const p of pats) {
  try { new RegExp(p.pattern); }
  catch (e) { bad.push({file: p.file, error: e.message}); }
}
process.stdout.write(JSON.stringify(bad));
"""


def _patterns(root: pathlib.Path) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    for grader in sorted(root.rglob("graders/*.md")):
        text = grader.read_text(encoding="utf-8", errors="replace")
        # Only `type: regex` graders are compiled as regexes. An `llm` or
        # `file_exists` grader has no pattern to check and must not be counted
        # as one, or the total below overstates the coverage.
        if not re.search(r"^type:\s*regex\s*$", text, re.M):
            continue
        match = re.search(r"^pattern:\s*(.*)$", text, re.M)
        if not match:
            continue
        raw = match.group(1).strip()
        if len(raw) >= 2 and raw[0] == raw[-1] == "'":
            raw = raw[1:-1].replace("''", "'")
        elif len(raw) >= 2 and raw[0] == raw[-1] == '"':
            raw = raw[1:-1]
        found.append({"file": str(grader), "pattern": raw})
    return found


def main() -> int:
    root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "evals")
    pats = _patterns(root)

    if not pats:
        print(f"graders: no `type: regex` graders found under {root} -- nothing checked")
        return 0

    node = shutil.which("node")
    if node is None:
        print(f"graders: {len(pats)} regex grader(s) NOT CHECKED -- no `node` on PATH.")
        print("graders:   This is 'could not check', not 'checked and clean'.")
        return 0

    try:
        proc = subprocess.run(
            [node, "-e", _NODE_SRC],
            input=json.dumps(pats),
            capture_output=True,
            text=True,
            timeout=30,
        )
        bad = json.loads(proc.stdout or "[]")
    except Exception as exc:  # noqa: BLE001 - a checker must never be the failure
        print(f"graders: {len(pats)} regex grader(s) NOT CHECKED -- {type(exc).__name__}: {exc}")
        print("graders:   This is 'could not check', not 'checked and clean'.")
        return 0

    if not bad:
        print(f"graders: {len(pats)} regex grader(s) compile under the JS engine")
        return 0

    print(f"graders: WARNING -- {len(bad)} of {len(pats)} regex grader(s) WILL THROW when scored.")
    print("graders:   A grader that throws scores the case 0.00 and reads as a bad answer.")
    for entry in bad:
        print(f"graders:   {entry['file']}")
        print(f"graders:     {entry['error']}")
    print("graders:   JavaScript RegExp has no inline flags: `(?i)`, `(?s)`, `(?is)`.")
    print("graders:   Spell it out instead -- `[Ff]oo`, and `[\\s\\S]` for dot-matches-newline.")
    # Deliberately 0. See the module docstring.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
