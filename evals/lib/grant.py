"""Which gated tools do the selected cases declare? Prints them for `--allow-tools`.

A tool named in a case's `allowed_tools:` is still refused unless the operator
ALSO grants it on the command line. `--allow-tools Bash` against a case
declaring `[Bash, Write, Edit]` produced

    not granted (missing --allow-tools grant, or a malformed entry): Write, Edit

and a score of 0 -- an agent that could read the program and could not write one
line of the spec, reported as a failure to model. The note appeared once, per
case; the summary line said nothing.

A README cannot keep a grant in step with seven cases, so `run.sh` asks this.

It is a FILE rather than a heredoc inside `$( )`, and that is not tidiness: the
first version was `grant=$(python3 - <<'PY' ... PY)`, and bash's scan for the
closing paren is confused by quotes in the heredoc body -- `.strip('"\'')` is
enough -- so the whole script died with `unexpected EOF while looking for
matching '"'` at its last line, pointing nowhere near the cause.

Usage: grant.py <evals-dir> [<case-glob> ...]   ->   e.g. "Bash Edit Write"

SEVERAL GLOBS, because `--case` is repeatable (SI-21). `run.sh` used to keep
only the LAST `--case` for this derivation while passing every one of them
through to the CLI, so a multi-case run derived its grant from one case and the
others could be handed a short grant -- which is the exact 0.00-reported-as-a-
skill-failure this file exists to prevent. A case matching ANY glob is selected.
"""

from __future__ import annotations

import fnmatch
import pathlib
import re
import sys

GATED = {"Bash", "Write", "Edit", "WebFetch"}


def main() -> int:
    root = pathlib.Path(sys.argv[1])
    globs = sys.argv[2:] or ["*"]

    wanted: set[str] = set()
    selected: list[str] = []
    for case in sorted(root.rglob("case.yaml")):
        text = case.read_text(encoding="utf-8", errors="replace")
        match = re.search(r"^name:\s*(\S+)", text, re.M)
        name = match.group(1).strip("\"'") if match else case.parent.name
        if not any(fnmatch.fnmatch(name, g) for g in globs):
            continue
        selected.append(name)
        declared = re.search(r"allowed_tools:\s*\[([^\]]*)\]", text)
        if declared:
            wanted |= {t.strip() for t in declared.group(1).split(",") if t.strip()} & GATED

    print(" ".join(sorted(wanted)))
    print(f"cases selected: {', '.join(selected) or '(none)'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
