#!/usr/bin/env python3
"""SI-04. One improvement record, and ONE reader for it.

A finding in this project is written down in four places, and they have never
been able to answer the same question:

  * `specs/results/skill_feedback.md`                       -- `SF-NNN` blocks
  * `specs/results/deferred_findings_final.yaml`            -- the epic backlog
  * `specs/results/epic-close/deferred_findings_next.yaml`  -- an older backlog
  * `examples/validation/agent_rounds/SELF-IMPROVEMENT-MATRIX.md` -- the bins

Every one of them records where a finding WENT. Not one of them records whether
the substrate CHANGED. `skill_change` is that field -- one grammar, carried by
all four -- and this script is its reader.

    skill_change: none
                | proposed(<unit>, <diff or issue>)
                | applied(<commit>)
                | declined(<reason>)
                | UNDECIDED

WHY THIS WRAPS `disposition.py` RATHER THAN REPLACING IT
--------------------------------------------------------
`disposition.py` owns the backlog rows: the duplicate-key structural guard, the
D1/D2/D3 clauses and their deliberately closed vocabulary. Re-implementing any
of that here would put a second opinion about the same bytes in the same
repository -- which is exactly the class `CA-05-DF-06` cost an epic to find,
where a parser silently kept the wrong one of two duplicate keys and the check
certified the result clean. So this file imports that one and adds a single
clause on top:

    D4  a finding anchored to a SKILL is consumed only by a change to that skill

D4 lives here and NOT in `disposition.py`, on purpose and for two reasons.
`disposition.py` refuses (exit 1); this script never does. And `skill_change`
did not exist when any sealed epic closed, so adding D4 to the refusing
instrument would retroactively refuse the whole record on a field nobody could
have filled -- an instrument changed after seeing its own data, which is
`MF-020`, the error this programme has paid for most often.

ADVISORY, AND STRUCTURALLY SO
-----------------------------
There is no exit-code path in this file. `main()` returns None, `__main__`
calls it and falls off the end, and the process exits 0. Not "we remembered to
return 0 on every branch" -- there is no branch that can return anything else,
and no flag that makes it refuse. `GOAL-no-new-gates` is a guard on the ticket
that shipped this, and the cheapest way to keep a guarantee is to make it
unrepresentable to break.

**AND THAT WAS NOT ENOUGH, MEASURED ON THE FIRST RUN.** Having no `sys.exit`
does not make a script exit 0: the first invocation of this file died with
`ModuleNotFoundError: No module named 'yaml'` and returned 1, because a bare
`python3` here carries no PyYAML (`SF-105`, still open). An uncaught exception
is an exit code like any other. So every source is read through `_guarded`
below, which turns any failure to read one into a printed line and keeps
going -- a ledger that cannot read the matrix still reports the backlogs, and
says which one it lost. The guarantee is "this process exits 0", and an
advisory instrument that crashes on a missing dependency has broken it just as
surely as one that refuses.

    python3 skills/spec-double-2/scripts/improvement_ledger.py
    python3 skills/spec-double-2/scripts/improvement_ledger.py --verbose
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys
from dataclasses import dataclass, field

_HERE = pathlib.Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import disposition as D  # noqa: E402  -- the backlog reader; this adds no second one
import skill_feedback as SF  # noqa: E402  -- the SF-block parser; likewise

# -- where the record lives ------------------------------------------------

SKILL_FEEDBACK = "specs/results/skill_feedback.md"
BACKLOGS = (
    "specs/results/deferred_findings_final.yaml",
    "specs/results/epic-close/deferred_findings_next.yaml",
    # The path `disposition.py` reads, i.e. every CONSUMER repository's live
    # ledger (#163). Without it this reader reports "0 records" in any
    # repository but this one -- an advisory instrument that is silent
    # everywhere it is used. `--ledger` replaces this whole list.
    D.LEDGER,
)
MATRIX = "examples/validation/agent_rounds/SELF-IMPROVEMENT-MATRIX.md"

#: SI-01 moved the skill surface under `skills/spec-double-2/`. Findings filed
#: before that move name the OLD spellings, and `SI-01-DF-01` is the standing
#: record of what happens when a resolver learns only one of the two: sealed
#: analysis scripts stopped resolving and a `rm -f` silently removed nothing.
#: Both spellings are recognised here for that reason, not for tidiness.
LEGACY_SKILL_DIRS = (
    "scripts/",
    "references/",
    "prompts/",
    "templates/",
    "skill-scripts/",
    "spec_double_compiler/",
)
LEGACY_UNIT = "spec-double-2"

#: An `UNMODELED/<bin>` whose substrate really is a skill-manager unit. Left
#: deliberately short: `agent-harness` is `examples/agent_integration/` and
#: `record-keeping` is this repository's own bookkeeping -- neither is a unit,
#: and mapping them to one to raise the skill-anchored count would be the
#: `A1` attack `architecture_tags.md` names (choose the token that flatters the
#: number). An unmapped bin is reported as unmapped.
BIN_UNITS = {
    "skill-manager-home": "skill-manager",
    "skill-composition": "skill-manager",
}

# -- the field -------------------------------------------------------------

VERBS = ("none", "proposed", "applied", "declined")
#: How many comma-separated arguments each verb takes.
ARITY = {"none": 0, "proposed": 2, "applied": 1, "declined": 1}
#: The two that say the loop actually closed.
TERMINAL_VERBS = ("applied", "declined")

#: Section 3's answer to an absent input, spelled the way the page spells it.
#: Recorded but not a verb of the call grammar, and never terminal.
UNDECIDED = "UNDECIDED"

_CALL = re.compile(r"^(?P<verb>[a-z][a-z-]*)\s*(?:\((?P<args>.*)\))?$", re.S)


@dataclass(frozen=True)
class SkillChange:
    """A parsed `skill_change` value.

    `absent` is its own verb and is NOT `none`. `bug_attribution.md` §3: the
    correct answer to an absent input is UNDECIDED or a refusal, never a PASS.
    `none` is a claim somebody made ("no skill change was needed here");
    `absent` is nobody having been asked. Collapsing them would report the
    entire pre-SI-04 record as having decided something.
    """

    verb: str
    args: tuple[str, ...] = ()
    raw: str = ""

    @property
    def recorded(self) -> bool:
        return self.verb in VERBS or self.verb == "undecided"

    @property
    def terminal(self) -> bool:
        return self.verb in TERMINAL_VERBS

    @property
    def unit(self) -> str:
        """The unit a `proposed` change names, if it named one."""
        return self.args[0] if self.verb == "proposed" and self.args else ""

    def __str__(self) -> str:
        if self.verb == "absent":
            return "(absent)"
        if self.verb == "undecided":
            return self.raw or UNDECIDED
        if not self.args:
            return self.verb
        return f"{self.verb}({', '.join(self.args)})"


#: How a human writes "absent" in a markdown cell, which cannot be blank without
#: becoming invisible to a reader. `(absent)` is this module's own rendering of
#: `SkillChange("absent")`, so the table and the reader round-trip -- and an
#: empty cell means the same thing. Anything ELSE that fails to parse stays
#: `malformed`: the point is to name what nobody can read, not to widen the
#: grammar until nothing is ever wrong.
ABSENT_SPELLINGS = {"", "(absent)", "absent", "-", "--", "—", "n/a", "tbd"}


def parse_skill_change(value: str | None) -> SkillChange:
    """Parse the one-line grammar. Never raises: a bad value is `malformed`."""
    raw = str(value or "").strip().strip("`").strip()
    if raw.lower() in ABSENT_SPELLINGS:
        return SkillChange("absent")
    # `bug_attribution.md` section 3 (#165): UNDECIDED is the recorded answer
    # "asked, not yet answered". It is neither `none` (a claim) nor absent
    # (never asked) nor malformed, and it is counted on its own line.
    if raw == UNDECIDED or raw.startswith(UNDECIDED + "("):
        return SkillChange("undecided", raw=raw)
    match = _CALL.match(raw)
    if not match:
        return SkillChange("malformed", raw=raw)
    verb = match.group("verb")
    if verb not in VERBS:
        return SkillChange("malformed", raw=raw)
    argtext = match.group("args")
    arity = ARITY[verb]
    if arity == 0:
        # `none(anything)` is not `none`; say so rather than dropping the text.
        return SkillChange(verb, (), raw) if not argtext else SkillChange("malformed", raw=raw)
    if argtext is None:
        return SkillChange("malformed", raw=raw)
    args = tuple(part.strip() for part in argtext.split(",", arity - 1))
    if len(args) != arity or not all(args):
        return SkillChange("malformed", raw=raw)
    return SkillChange(verb, args, raw)


# -- the unified record ----------------------------------------------------


@dataclass
class Record:
    """One finding, from whichever of the four files it was written in.

    This is the schema SI-04 unifies: the attribution anchor, the disposition,
    the skill-change verb and the goal link on one object, so that a reader
    does not have to join four formats by hand to ask whether anything changed.
    """

    id: str
    source: str
    kind: str = "CATCH"
    anchor: str = ""
    disposition: str = ""
    skill_change: SkillChange = field(default_factory=lambda: SkillChange("absent"))
    goal: str = ""
    surfaces: tuple[str, ...] = ()
    unit: str = ""

    @property
    def skill_anchored(self) -> bool:
        return bool(self.unit)

    @property
    def stuck(self) -> bool:
        """`recorded-local` is the status the 13 stuck findings have.

        It means: written down in this repository, and filed nowhere. The
        target of `GOAL-findings-become-changes` is that it cannot be terminal.
        """
        return self.disposition == "recorded-local"


def units_in(root: pathlib.Path) -> tuple[str, ...]:
    """Skill units this repository carries, read from disk rather than listed.

    A hardcoded list is a second place for the truth to live, and SI-02 moved
    five units in one ticket.
    """
    skills = root / "skills"
    if not skills.is_dir():
        return ()
    return tuple(sorted(p.name for p in skills.iterdir() if p.is_dir()))


def unit_for(surfaces: tuple[str, ...], known: tuple[str, ...]) -> str:
    """The skill unit a finding is anchored to, or "" when it is not."""
    for surface in surfaces:
        text = str(surface or "").strip().strip("`")
        for unit in known:
            if text.startswith(f"skills/{unit}/") or f"skills/{unit}/" in text:
                return unit
        for legacy in LEGACY_SKILL_DIRS:
            if text.startswith(legacy):
                return LEGACY_UNIT
    return ""


# -- markdown tables, read by header name ----------------------------------


def md_tables(text: str) -> list[tuple[list[str], list[dict[str, str]]]]:
    """Every pipe table in a markdown document, as (headers, rows-as-dicts).

    Keyed BY HEADER NAME rather than by column index, so that adding the
    `skill change` column this ticket adds does not silently shift every
    reading by one -- which is the same class as `CA-05-DF-06`, a parser
    quietly reading a different value than the author wrote.
    """
    tables: list[tuple[list[str], list[dict[str, str]]]] = []
    headers: list[str] = []
    rows: list[dict[str, str]] = []

    def cells(line: str) -> list[str]:
        return [c.strip() for c in line.strip().strip("|").split("|")]

    def flush() -> None:
        if headers and rows:
            tables.append((headers, rows))

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            flush()
            headers, rows = [], []
            continue
        parts = cells(stripped)
        if all(set(p) <= set("-: ") and p for p in parts):
            continue  # the --- separator row
        if not headers:
            headers = [p.lower() for p in parts]
            rows = []
            continue
        rows.append({headers[i]: parts[i] for i in range(min(len(headers), len(parts)))})
    flush()
    return tables


# -- reading each of the four files ----------------------------------------


def read_skill_feedback(path: pathlib.Path, known: tuple[str, ...],
                        problems: list[str]) -> list[Record]:
    """SF-NNN blocks, through `skill_feedback.parse_findings`.

    Deliberately NOT through `filing_status`: that reports the LATEST close-out
    scope only, which is right for a close (an old filed finding must not make
    a new unreviewed close look resolved) and wrong for a ledger, which is
    asking about the whole record.
    """
    if not path.is_file():
        problems.append(f"{path}: absent -- no skill-feedback findings read")
        return []
    findings = SF.parse_findings(path.read_text(encoding="utf-8"))
    out: list[Record] = []
    for item in findings:
        surfaces = tuple(
            v for v in (item.fields.get("target"), item.fields.get("surface")) if v
        )
        out.append(
            Record(
                id=item.id,
                source="skill_feedback.md",
                anchor=item.fields.get("anchor", ""),
                disposition=item.status or "open",
                skill_change=parse_skill_change(item.fields.get("skill_change")),
                goal=item.fields.get("goal", ""),
                surfaces=surfaces,
                unit=unit_for(surfaces, known),
            )
        )
    return out


def read_backlog(path: pathlib.Path, known: tuple[str, ...],
                 problems: list[str]) -> list[Record]:
    """Backlog rows, through `disposition.read_rows` -- the one backlog reader."""
    if not path.is_file():
        problems.append(f"{path}: absent -- no backlog rows read")
        return []
    rows, faults = D.read_rows(path)
    problems.extend(faults)
    out: list[Record] = []
    for row in rows:
        surface = row.get("surface") or {}
        surfaces: list[str] = []
        if isinstance(surface, dict):
            for value in surface.values():
                if isinstance(value, list):
                    surfaces.extend(str(v) for v in value)
                elif value:
                    surfaces.append(str(value))
        out.append(
            Record(
                id=str(row.get("id", "?")),
                source=path.name,
                anchor=str(row.get("anchor") or ""),
                disposition=str(row.get("disposition") or ""),
                skill_change=parse_skill_change(row.get("skill_change")),
                goal=str(row.get("goal") or ""),
                surfaces=tuple(surfaces),
                unit=unit_for(tuple(surfaces), known),
            )
        )
    return out


def read_matrix(path: pathlib.Path, problems: list[str]) -> list[Record]:
    """The `UNMODELED/<bin>` rows of the self-improvement matrix.

    The matrix is maintained by prompting and has ONE writer, the epic agent
    (`bug_attribution.md` §7a). This reads it; it never writes it.
    """
    if not path.is_file():
        problems.append(f"{path}: absent -- no matrix bins read")
        return []
    out: list[Record] = []
    seen: set[str] = set()
    for headers, rows in md_tables(path.read_text(encoding="utf-8")):
        if "bin" not in headers:
            continue
        for row in rows:
            name = row.get("bin", "").strip().strip("*").strip("`")
            if not name.startswith("UNMODELED/") or name in seen:
                continue
            seen.add(name)
            bin_name = name.split("/", 1)[1]
            out.append(
                Record(
                    id=name,
                    source="SELF-IMPROVEMENT-MATRIX.md",
                    kind="BIN",
                    anchor=name,
                    disposition=row.get("disposition", "").strip().strip("*").strip("`").lower(),
                    skill_change=parse_skill_change(row.get("skill change")),
                    unit=BIN_UNITS.get(bin_name, ""),
                )
            )
    if not out:
        problems.append(f"{path}: no `UNMODELED/<bin>` rows found -- the parser may have drifted")
    return out


# -- the report ------------------------------------------------------------


def repo_root(explicit: str | None) -> pathlib.Path:
    """Where the record lives: the given root, else cwd, else the skill's repo."""
    if explicit:
        return pathlib.Path(explicit).resolve()
    for candidate in (pathlib.Path.cwd(), *pathlib.Path.cwd().parents, _HERE.parents[2]):
        if (candidate / SKILL_FEEDBACK).is_file():
            return candidate
    return pathlib.Path.cwd()


def _table(title: str, headers: list[str], rows: list[list[str]]) -> None:
    if not rows:
        return
    widths = [max(len(str(r[i])) for r in [headers] + rows) for i in range(len(headers))]
    print(f"\n{title}")
    print("  " + "  ".join(str(h).ljust(widths[i]) for i, h in enumerate(headers)).rstrip())
    print("  " + "  ".join("-" * widths[i] for i in range(len(headers))))
    for row in rows:
        print("  " + "  ".join(str(c).ljust(widths[i]) for i, c in enumerate(row)).rstrip())


def report(records: list[Record], problems: list[str], verbose: bool) -> None:
    """Print the ledger. Returns nothing: there is no verdict to return."""
    print(f"improvement ledger -- {len(records)} record(s) across "
          f"{len(set(r.source for r in records))} file(s)")

    for problem in problems:
        print(f"  ! {problem}")

    # The headline the goal names: findings by disposition.
    dispositions: dict[str, list[Record]] = {}
    for record in records:
        dispositions.setdefault(record.disposition or "(none)", []).append(record)
    rows = []
    for name in sorted(dispositions):
        group = dispositions[name]
        rows.append([
            name,
            len(group),
            sum(1 for r in group if r.skill_anchored),
            sum(1 for r in group if r.skill_change.recorded),
            sum(1 for r in group if r.skill_change.terminal),
        ])
    _table("findings by disposition",
           ["disposition", "total", "skill-anchored", "skill_change", "applied/declined"],
           rows)

    # Where each verb stands, including the two that are not answers.
    verbs: dict[str, int] = {}
    for record in records:
        verbs[record.skill_change.verb] = verbs.get(record.skill_change.verb, 0) + 1
    _table("skill_change verbs", ["verb", "records"],
           [[v, verbs[v]] for v in sorted(verbs)])

    _table("by source", ["source", "records", "skill-anchored", "skill_change recorded"],
           [[s,
             sum(1 for r in records if r.source == s),
             sum(1 for r in records if r.source == s and r.skill_anchored),
             sum(1 for r in records if r.source == s and r.skill_change.recorded)]
            for s in sorted(set(r.source for r in records))])

    # -- the warnings. One line each, and every one of them is advisory. --
    stuck = [r for r in records if r.stuck]
    undecided = [r for r in records if r.skill_change.verb == "undecided"]
    missing = [r for r in records if r.skill_change.verb == "absent"]
    malformed = [r for r in records if r.skill_change.verb == "malformed"]
    # D4: a skill-anchored finding is consumed only by a change to that skill.
    d4 = [r for r in records if r.skill_anchored and not r.skill_change.terminal]

    print(f"\nWARNINGS (advisory -- nothing here refuses)")
    print(f"  recorded-local, filed nowhere .......... {len(stuck)}")
    print(f"  no skill_change field at all ........... {len(missing)}")
    print(f"  skill_change UNDECIDED (asked, open) ... {len(undecided)}")
    print(f"  skill_change present but unparseable ... {len(malformed)}")
    print(f"  D4: skill-anchored, not applied/declined {len(d4)}")

    def show(label: str, items: list[Record], render) -> None:
        if not items:
            return
        shown = items if verbose else items[:8]
        print(f"\n  {label}:")
        for item in shown:
            print(f"    {render(item)}")
        if len(shown) < len(items):
            print(f"    ... and {len(items) - len(shown)} more (use --verbose)")

    show("recorded-local", stuck,
         lambda r: f"{r.id} [{r.source}] unit={r.unit or '-'} skill_change={r.skill_change}")
    show("no skill_change", missing,
         lambda r: f"{r.id} [{r.source}] disposition={r.disposition or '(none)'}")
    show("unparseable skill_change", malformed,
         lambda r: f"{r.id} [{r.source}] {r.skill_change.raw!r}")
    show("D4 -- anchored to a skill, no change to that skill", d4,
         lambda r: f"{r.id} [{r.source}] unit={r.unit} skill_change={r.skill_change}")

    print("\nThe rule: a finding anchored to a skill is consumed only by a change")
    print("to that skill. `references/consumption.md` D4. This reader reports it;")
    print("nothing in this repository refuses on it.")


def _guarded(label: str, read, problems: list[str]) -> list[Record]:
    """Read one source; turn ANY failure into a printed line and carry on.

    Deliberately broad. This is an advisory reader over four hand-maintained
    files, and the failure this catches is not hypothetical: the first run of
    this script exited 1 on a missing PyYAML. A reader that dies on one source
    reports nothing about the other three, which is strictly worse than
    reporting three and naming the fourth.

    `BaseException` is NOT caught: a KeyboardInterrupt should still stop it.
    """
    try:
        return read()
    except Exception as exc:  # noqa: BLE001 -- see the docstring
        problems.append(f"{label}: NOT read ({type(exc).__name__}: {exc})")
        return []


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", default=None,
                        help="repository root (default: the tree the record is in)")
    parser.add_argument("--ledger", action="append", default=None, metavar="PATH",
                        help="backlog file to read, relative to --repo-root or absolute "
                             "(repeatable); replaces the default BACKLOGS")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="list every warned record instead of the first eight")
    args = parser.parse_args(argv)

    root = repo_root(args.repo_root)
    known = units_in(root)
    problems: list[str] = []

    records = _guarded(
        SKILL_FEEDBACK,
        lambda: read_skill_feedback(root / SKILL_FEEDBACK, known, problems),
        problems,
    )
    for backlog in (args.ledger or BACKLOGS):
        records += _guarded(
            backlog,
            lambda b=backlog: read_backlog(root / b, known, problems),
            problems,
        )
    records += _guarded(MATRIX, lambda: read_matrix(root / MATRIX, problems), problems)

    report(records, problems, args.verbose)


if __name__ == "__main__":
    # No exit code. `main` returns None, this falls off the end, the process
    # exits 0. There is deliberately no branch that can do anything else.
    main()
