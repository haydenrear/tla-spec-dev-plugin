#!/usr/bin/env python3
"""Line citations, checked against the line they cite -- and repaired.

`G-11`: seventeen lines of docstring added to `default_import_roots_for` moved
an anchor from 1413 to 1430, and `scripts/effect_conformance.py` cited it by
number. Nothing about behaviour changed, so every behavioural check stayed
green; only the citation check saw it.

**The class is eliminated by making the ANCHOR authoritative and the number
derived**, which the checker was already halfway to doing: it reported *"the
anchor is at ...:1430"* and then made a human retype it. When a tool knows the
right answer and asks a person to copy it across, the copying is the defect
source, and this had already produced findings in three consecutive tickets
before the check existed at all.

So: `--fix` rewrites the number when the anchor resolves to exactly ONE line,
and refuses when it resolves to none or several -- those are a real question
about what was meant, and a repair that guesses is worse than a red test.

    python3 scripts/check_citations.py            # report, exit 1 if stale
    python3 scripts/check_citations.py --fix      # repair what is unambiguous

The convention is `path/to/FILE.EXT:LINE[-LINE] (ANCHOR)`. Both halves are
required: a bare line number cannot be resolved by a reader or a checker, and a line
number with no anchor goes stale in silence, which is the whole defect.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

#: The skill surface, now at `skills/spec-double-2/` inside this plugin repo.
SKILL_ROOT = Path(__file__).resolve().parents[1]
#: The repository root, which still carries `specs/`. SI-01 moved the skill
#: surface two levels down; citations are resolved against the REPOSITORY, so
#: this must stay the root and not follow the surface.
REPO_ROOT = SKILL_ROOT.parents[1]

#: The surface whose citations are checked. Globs, resolved against the repo.
#:
#: `tests/`, `references/`, `specs/results/` and planning YAML are deliberately
#: OUT: results and history are append-only records of what was true when
#: written, and rewriting them to satisfy a checker is the opposite of the point.
CITATION_SCOPE = (
    "skills/spec-double-2/scripts/*.py",
    "specs/current/spec_manifest.yaml",
    "specs/desired_program_model/spec_manifest.yaml",
    "specs/program_model/spec_manifest.yaml",
    "specs/current/TlaSpecDevCli.tla",
    "specs/desired_program_model/TlaSpecDevCli.tla",
    "specs/program_model/TlaSpecDevCli.tla",
)

CITED_SUFFIXES = "py|sh|tla|yaml|yml|toml|cfg|kts|md"

CITATION = re.compile(
    rf"(?P<file>[A-Za-z_][\w./-]*\.(?:{CITED_SUFFIXES}))"
    r":(?P<start>\d+)(?:-(?P<end>\d+))?"
    r"(?:\s*\((?P<anchor>[^()\n]{1,80})\))?"
)

#: A `:<line>` with no file in front of it. Python slices (`errors[:20]`) are
#: the dominant false positive and are excluded by the `[` in the lookbehind.
BARE_CITATION = re.compile(r"(?<![\w.:/\[\d])(?<!\.\.)\:(\d{2,4})\b")

#: Directories that are not this repository's source. `.skill-manager` is a real
#: COPY of every installed skill -- ~15k .py files including copies of scripts
#: cited here by name. It is gitignored, so a plain clone has none and a
#: basename resolver looked correct, but `wt new` creates one in every ticket
#: worktree, which is the only place ticket agents ever run (HP-01-DF-01).
#:
#: `build` is the SAME CLASS, found again by SI-27: `test_graph` materialises
#: whole plugin trees as fixtures under `test_graph/build/validation-reports/`,
#: so running the test graphs and then this checker made five citations
#: "ambiguous" that name exactly one source file. Nothing tracked lives under a
#: `build/` (`.gitignore:3` ignores it repo-wide), so the name is safe to prune,
#: and pruning by NAME rather than by asking git is deliberate: this checker
#: also runs in staged copies with no repository around them, where
#: `git check-ignore` decides nothing.
EXCLUDED_DIRS = {".git", "generated", "build",
                 ".skill-manager", ".claude", ".codex", ".gemini"}


@dataclass(frozen=True)
class Problem:
    """One stale or uncheckable citation, and whether it can be repaired."""

    where: str
    message: str
    #: Byte span of the citation in the citing file, for `--fix`.
    span: tuple[int, int] | None = None
    #: The replacement citation text, only when the anchor is unambiguous.
    replacement: str | None = None

    @property
    def repairable(self) -> bool:
        return self.span is not None and self.replacement is not None


def scoped_files(root: Path = REPO_ROOT) -> list[Path]:
    found: list[Path] = []
    for pattern in CITATION_SCOPE:
        found.extend(sorted(root.glob(pattern)))
    return found


#: basename -> source files carrying it, built once per root. See `_index`.
_INDEX_CACHE: dict[Path, dict[str, list[Path]]] = {}


def _index(root: Path) -> dict[str, list[Path]]:
    """Every source file under `root`, by basename, pruning as it descends.

    Two things here are load-bearing, and both were measured rather than
    assumed (SI-27):

    1. **The prune happens DURING the walk, not after it.** `rglob` filtered by
       `EXCLUDED_DIRS` still descends into every excluded tree. With
       `test_graph/build/validation-reports/` present -- whole plugin trees
       materialised as fixtures -- that is ~360k entries to walk past.
    2. **The index is built once per root, not once per citation.** The
       previous resolver called `rglob` for EVERY citation, so the cost was
       (citations x tree), and on a polluted tree the shipped checker exceeded
       a 300s timeout without ever reporting a result. A checker too slow to
       finish reports nothing, which is worse than reporting wrongly.
    """
    cached = _INDEX_CACHE.get(root)
    if cached is not None:
        return cached
    index: dict[str, list[Path]] = {}
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            children = list(current.iterdir())
        except OSError:
            continue
        for child in children:
            if child.name in EXCLUDED_DIRS:
                continue
            if child.is_symlink():
                continue
            if child.is_dir():
                stack.append(child)
            elif child.is_file():
                index.setdefault(child.name, []).append(child)
    _INDEX_CACHE[root] = index
    return index


def resolve_cited(name: str, root: Path = REPO_ROOT) -> Path | None:
    """A cited path, resolved from the repo root or by unique basename."""
    direct = root / name
    if direct.is_file():
        return direct
    matches = _index(root).get(Path(name).name, [])
    return matches[0] if len(matches) == 1 else None


def problems_in(path: Path, root: Path = REPO_ROOT) -> list[Problem]:
    """Every stale or uncheckable citation in one file."""
    text = path.read_text(encoding="utf-8")
    found: list[Problem] = []

    for match in CITATION.finditer(text):
        source_line = text[: match.start()].count("\n") + 1
        where = f"{path.relative_to(root)}:{source_line}"
        cited_name = match.group("file")
        start = int(match.group("start"))
        end = int(match.group("end") or start)
        anchor = match.group("anchor")
        span_text = match.group("end")

        if anchor is None:
            found.append(
                Problem(
                    where,
                    f"citation `{cited_name}:{match.group('start')}"
                    f"{'-' + span_text if span_text else ''}` has no (anchor). Write "
                    "`FILE.EXT:LINE (some_token_on_that_line)` -- an unanchored line "
                    "number cannot be checked and goes stale silently.",
                )
            )
            continue

        cited = resolve_cited(cited_name, root)
        if cited is None:
            found.append(
                Problem(where, f"cited file {cited_name!r} does not resolve to one file")
            )
            continue

        lines = cited.read_text(encoding="utf-8").splitlines()
        if not 1 <= start <= end <= len(lines):
            found.append(
                Problem(where, f"{cited_name}:{start}-{end} is outside the file ({len(lines)} lines)")
            )
            continue

        if any(anchor in line for line in lines[start - 1 : end]):
            continue

        hits = [index + 1 for index, line in enumerate(lines) if anchor in line]
        cited_span = f"{start}" + (f"-{end}" if end != start else "")
        if len(hits) == 1:
            # The one case a repair can be certain about. The replacement keeps
            # the citation's own spelling of file and anchor and changes only
            # the digits, so a `--fix` diff is one number per line.
            replacement = f"{cited_name}:{hits[0]}"
            tail = match.group(0)[match.end("start") - match.start() :]
            if span_text:
                tail = tail[len(span_text) + 1 :]
            found.append(
                Problem(
                    where,
                    f"{cited_name}:{cited_span} does not contain the anchor "
                    f"{anchor!r} -- the anchor is at {cited_name}:{hits[0]}",
                    span=(match.start(), match.end()),
                    replacement=replacement + tail,
                )
            )
        else:
            found.append(
                Problem(
                    where,
                    f"{cited_name}:{cited_span} does not contain the anchor "
                    f"{anchor!r}, and that anchor appears on "
                    f"{len(hits)} lines -- a repair would have to guess which was meant",
                )
            )
    return found


def bare_citations_in(path: Path, root: Path = REPO_ROOT) -> list[Problem]:
    """A line number with no file in front of it, which no reader can resolve."""
    text = path.read_text(encoding="utf-8")
    found: list[Problem] = []
    for match in BARE_CITATION.finditer(text):
        before = text[: match.start()]
        if CITATION.search(text[max(0, match.start() - 120) : match.end()]):
            continue
        found.append(
            Problem(
                f"{path.relative_to(root)}:{before.count(chr(10)) + 1}",
                f"bare citation `:{match.group(1)}` names no file",
            )
        )
    return found


def fix_file(path: Path, root: Path = REPO_ROOT) -> int:
    """Rewrite every unambiguously stale citation in one file. Returns the count."""
    repairs = [p for p in problems_in(path, root) if p.repairable]
    if not repairs:
        return 0
    text = path.read_text(encoding="utf-8")
    # Back to front, so each span stays valid while the earlier ones are rewritten.
    for problem in sorted(repairs, key=lambda p: p.span[0], reverse=True):  # type: ignore[index]
        start, end = problem.span  # type: ignore[misc]
        text = text[:start] + problem.replacement + text[end:]  # type: ignore[operator]
    path.write_text(text, encoding="utf-8")
    return len(repairs)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fix", action="store_true",
        help="Rewrite citations whose anchor resolves to exactly ONE line. "
             "Ambiguous ones are reported and left alone.",
    )
    args = parser.parse_args()

    files = scoped_files()
    if not files:
        print("ERROR: citation scope matched no files", file=sys.stderr)
        return 2

    repaired = 0
    if args.fix:
        for path in files:
            count = fix_file(path)
            if count:
                repaired += count
                print(f"fixed {count} citation(s) in {path.relative_to(REPO_ROOT)}")

    remaining: list[Problem] = []
    for path in files:
        remaining.extend(problems_in(path))
        remaining.extend(bare_citations_in(path))

    if repaired:
        print(f"\nrepaired {repaired} citation(s)")
    if not remaining:
        print(f"every citation in {len(files)} scoped file(s) resolves to the line it cites")
        return 0

    fixable = sum(1 for p in remaining if p.repairable)
    print(f"\n{len(remaining)} stale or uncheckable citation(s):", file=sys.stderr)
    for problem in remaining:
        print(f"  {problem.where}: {problem.message}", file=sys.stderr)
    if fixable:
        print(f"\n{fixable} of these are unambiguous; `--fix` repairs them.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
