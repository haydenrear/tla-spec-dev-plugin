#!/usr/bin/env python3
"""FI-02. Run every shipped instrument against a DEMONSTRATED FAILING INPUT.

    python3 examples/validation/instruments/demonstrate.py
    python3 examples/validation/instruments/demonstrate.py --tier fast
    python3 examples/validation/instruments/demonstrate.py --only corpus-runner
    python3 examples/validation/instruments/demonstrate.py --format json --out FILE

`references/architecture_advice.md` **S2**: *"Every criterion must have a
demonstrated failing input and a demonstrated passing input."* It was written
for a scanner that has since been deleted, and until FI-01 it had never been
turned on an instrument this repository kept. FI-01 turned it on one -- the
control-property probe -- and the result justified the epic: against the parent
probe exactly as it shipped, three of four deliberately broken controls reported
`HOLDS`. Every `HOLDS` that probe had ever printed was uninformative.

This file turns it on everything else.

WHAT A ROW MEANS. For each instrument the registry declares up to three
demonstrations, each of which is RE-RUNNABLE and each of which STAGES ITS OWN
TREE in a temporary directory, so nothing here edits the repository:

    failing      the thing the instrument watches is GENUINELY BROKEN, and the
                 instrument must report it. Not a test that the instrument
                 runs; a demonstration that it goes red.
    passing      the same instrument on an unbroken subject, which must stay
                 green. S2 asks for both, and an instrument that reported
                 everything broken would be as useless as one that reported
                 everything fine.
    blind_spot   a genuine break the instrument demonstrably does NOT report.
                 This slot exists because R2 says a control that cannot fail is
                 reported, never patched into looking fine -- and because the
                 count of things our instruments cannot see is the honest
                 product of this ticket.

WHERE A SLOT IS ABSENT the registry must say why in `no_failing_demonstration`
or `no_passing_demonstration`, and the reason is printed in the table. THE COUNT
OF INSTRUMENTS WITH NO DEMONSTRATED FAILING INPUT IS THIS COMMAND'S PRODUCT. A
high count is the honest outcome. There is no target on the ratio; setting one
before anything had ever been demonstrated would be inventing the answer.

THIS IS NOT A GATE. It refuses nothing about the repository's design and no
close path consults it. It exits non-zero for exactly one reason: a DECLARED
demonstration did not reproduce -- which means either the instrument changed or
the demonstration went stale, and both are things a reader must be told rather
than left to discover.

SM-03: THE EXECUTABLE COUNT, AND WHY IT IS NOT OPTIONAL
-------------------------------------------------------

Every pytest demonstration in this file used to be judged on `expect_exit = 0`
and nothing else, and `FI-06` called those twelve slots hollow on the ground
that *"pytest returns 0 for a passing run and a fully skipped one"*. `SM-01`
seeded both skip shapes and measured the sentence:

    pytestmark = pytest.mark.skip(...)          items COLLECTED then skipped,
                                                pytest exits 0, slot says `ok`
    pytest.skip(..., allow_module_level=True)   NOTHING collected, pytest exits
                                                5, slot goes red

So the hole is **not** a demonstration that DISAPPEARS -- that one is already
caught. It is a demonstration that goes **VACUOUS**: still there, still
collected, still exit 0, asserting nothing. `SM-GM-I1` is that mutant and it
survived the registry unchanged.

The repair is the same one `SM-01-DF-01` asked for one layer down, where the
port-swap driver's suite columns carry no executable count and are therefore
structurally exempt from control checking: **a slot that cannot say how many
tests it ran cannot say that anything ran.** Every pytest slot now declares

    expect_passed             an EXACT count -- the slot cites node ids, so the
                              number is the number of nodes and does not drift
    expect_passed_at_least    a FLOOR -- the slot cites a whole file on purpose,
                              so an exact count would break every time a test is
                              added to it, which is a demonstration going stale
                              for a reason that has nothing to do with the
                              instrument

and `expect_skipped` defaults to **0** for every pytest slot, declared or not. A
skip inside a demonstration is a demonstration that did not happen. Both counts
are read out of pytest's own summary line, so they are the subprocess's report
of what it executed rather than this file's belief about it.

`tests/test_instrument_demonstrations.py::test_every_pytest_slot_declares_an_executable_count`
makes the declaration mandatory, so a new slot cannot arrive uncounted.

SM-03: STAGE-AWARE PYTEST
-------------------------

`run_pytest` used to run at `REPO_ROOT` unconditionally. Four rows were
classified `no-demonstration-constructible` with the reason *"not without
breaking a shipped file"* -- and `SM-01` (`SM-GM-I4`) showed that reason is a
fact about THIS RUNNER, not about those instruments: break the shipped file in a
throwaway tree and the tripwire goes red in 23 executed tests. So a pytest slot
that declares `stage` is now staged exactly like a `cli` slot and run inside the
staged tree, and those rows get real failing demonstrations instead of an
excuse.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "skills" / "spec-double-2" / "scripts"))
import verdict  # noqa: E402

REPO_ROOT = HERE.parents[2]
REGISTRY = HERE / "instruments.toml"

SLOTS = ("failing", "passing", "blind_spot")

#: A demonstration is either run as a command line, or it is a pytest node that
#: performs the break-and-check in process. `declared` carries no executable
#: form and must carry a `reason`.
KINDS = ("cli", "pytest", "declared")


class DemonstrationError(RuntimeError):
    """The demonstration itself is malformed -- distinct from a red instrument."""


# ---------------------------------------------------------------------------
# staging
# ---------------------------------------------------------------------------


def stage(spec: dict[str, Any], tree: Path) -> None:
    """Copy the declared inputs into `tree`, then break them as declared.

    Everything an instrument reads is staged, so the demonstration never edits
    the repository and two demonstrations of the same instrument cannot
    interfere. `check_catalogue.py` and `make_blind_copies.py` both WRITE to the
    tree they measure; that is why this is not optional.
    """

    for entry in spec.get("stage", []):
        source = REPO_ROOT / entry["from"]
        destination = tree / entry["to"]
        if not source.exists():
            raise DemonstrationError(f"stage source does not exist: {entry['from']}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        # BS-08: entries apply in order and a later one REPLACES what an earlier
        # one put at its destination (a fixture staged over an example's
        # gitignored, possibly locally-generated, directory).
        if destination.is_dir() and source.is_dir():
            shutil.rmtree(destination)
        if source.is_dir():
            shutil.copytree(source, destination, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            shutil.copy2(source, destination)

    for entry in spec.get("mutate", []):
        target = tree / entry["file"]
        if not target.is_file():
            raise DemonstrationError(f"mutate target is not a file: {entry['file']}")
        text = target.read_text(encoding="utf-8")
        if "append" in entry:
            target.write_text(text + entry["append"], encoding="utf-8")
            continue
        find, replace = entry["find"], entry["replace"]
        occurrences = text.count(find)
        if occurrences != 1:
            # The same rule `check_catalogue.py` applies to a seeded fault:
            # zero seeds nothing and reports a false green, more than one seeds
            # several faults and reports them as one.
            raise DemonstrationError(
                f"{entry['file']}: `find` occurs {occurrences} time(s), must be exactly 1"
            )
        if find == replace:
            raise DemonstrationError(f"{entry['file']}: find and replace are identical")
        target.write_text(text.replace(find, replace), encoding="utf-8")


def expand(value: str, tree: Path) -> str:
    return (
        value.replace("{repo}", str(REPO_ROOT))
        .replace("{tree}", str(tree))
        .replace("{python}", sys.executable)
    )


# ---------------------------------------------------------------------------
# running
# ---------------------------------------------------------------------------


def run_cli(spec: dict[str, Any], tree: Path) -> dict[str, Any]:
    """Run one command-line demonstration, and read its verdict if it wrote one.

    `{verdict}` in an `argv` expands to a per-run temp path. A gate handed
    `--verdict-json {verdict}` writes `{verdict, reason, detail}` there, and the
    slot can then assert `expect_reason` instead of `expect_output`.

    **That is the whole point.** 41 of this registry's 103 slots assert on
    literal output strings, and 13 of the failures it reports today are prose
    drift: `corpus_diagnostics.py` moved from "Every component is within cap" to
    "Every {scope} is within cap" when the cap became per-action, and a correct
    demonstration began reporting a working instrument broken. A `reason` code
    survives every rewording of the sentence beside it.
    """
    with tempfile.TemporaryDirectory(prefix="verdict-") as scratch:
        verdict_path = Path(scratch) / "verdict.json"
        argv = [expand(part, tree).replace("{verdict}", str(verdict_path)) for part in spec["argv"]]
        cwd = expand(spec.get("cwd", "{tree}"), tree)
        completed = subprocess.run(
            argv, cwd=cwd, capture_output=True, text=True, timeout=spec.get("timeout", 900)
        )
        observed_verdict: dict[str, Any] | None = None
        verdict_error: str | None = None
        if verdict_path.is_file():
            try:
                observed_verdict = verdict.read(verdict_path)
            except (ValueError, json.JSONDecodeError) as exc:
                verdict_error = str(exc)
    return {
        "exit": completed.returncode,
        "output": completed.stdout + completed.stderr,
        "argv": argv,
        "verdict": observed_verdict,
        "verdict_error": verdict_error,
    }


#: pytest's own summary line: `1 failed, 4 passed, 2 skipped in 0.31s`. Read
#: from the subprocess rather than inferred, because the whole point of the
#: count is that it is the runner's report of what it executed.
_OUTCOME = re.compile(
    r"(\d+) (passed|failed|skipped|error|errors|deselected|xfailed|xpassed|warning|warnings)"
)


def pytest_counts(output: str) -> dict[str, int]:
    """How many tests actually ran, by outcome.

    `expect_exit = 0` is satisfied by a run that executed NOTHING. This is the
    number that distinguishes the two, and `SM-GM-I1` is the mutant that proves
    the distinction is not academic.
    """

    counts: dict[str, int] = {}
    for number, outcome in _OUTCOME.findall(output):
        if outcome in ("errors", "warnings"):
            outcome = outcome[:-1]
        counts[outcome] = int(number)
    return counts


def run_pytest(spec: dict[str, Any], tree: Path) -> dict[str, Any]:
    """Run the cited nodes, in the STAGED tree when the slot declares one.

    `SM-GM-I4`: the four `no-demonstration-constructible` rows were declared
    unconstructible because a demonstration would have to break a shipped file
    -- which is true only while this function ignores the tree it was handed.
    """

    staged = bool(spec.get("stage"))
    if staged:
        stage(spec, tree)
    argv = [
        "uv", "run", "--with", "pytest", "--with", "pyyaml",
        "python", "-m", "pytest", "-q",
        *[expand(node, tree) for node in spec["nodes"]],
    ]
    completed = subprocess.run(
        argv,
        cwd=tree if staged else REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=spec.get("timeout", 900),
    )
    output = completed.stdout + completed.stderr
    return {
        "exit": completed.returncode,
        "output": output,
        "argv": argv,
        "counts": pytest_counts(output),
        "staged": staged,
    }


def judge(spec: dict[str, Any], observed: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    expected_exit = spec.get("expect_exit")
    if expected_exit is not None and observed["exit"] != expected_exit:
        problems.append(f"exit {observed['exit']}, declared {expected_exit}")
    for needle in spec.get("expect_output", []):
        if needle not in observed["output"]:
            problems.append(f"output does not contain {needle!r}")
    for needle in spec.get("expect_absent", []):
        if needle in observed["output"]:
            problems.append(f"output contains {needle!r}, which it must not")
    problems.extend(judge_verdict(spec, observed))
    problems.extend(judge_counts(spec, observed))
    return problems


def judge_verdict(spec: dict[str, Any], observed: dict[str, Any]) -> list[str]:
    """Assert on the gate's stated reason, not on the sentence beside it.

    A slot declaring `expect_reason` is asserting against a stable code the gate
    chose deliberately. A slot that declares it and gets NO verdict file is a
    louder failure than a wording mismatch, because it means the gate did not
    write one at all -- and a consumer that treated a missing verdict as absent
    would turn a broken gate into a quiet pass.
    """
    expected = spec.get("expect_reason")
    if expected is None:
        return []
    if observed.get("verdict_error"):
        return [f"verdict file is not a verdict document: {observed['verdict_error']}"]
    found = observed.get("verdict")
    if found is None:
        return [
            f"declared expect_reason={expected!r} and the command wrote no verdict "
            "-- pass `--verdict-json {verdict}` in argv, or drop the declaration"
        ]
    problems: list[str] = []
    if found["reason"] != expected:
        problems.append(f"verdict reason {found['reason']!r}, declared {expected!r}")
    wanted_outcome = spec.get("expect_verdict")
    if wanted_outcome is not None and found["verdict"] != wanted_outcome:
        problems.append(f"verdict {found['verdict']!r}, declared {wanted_outcome!r}")
    return problems


def judge_counts(spec: dict[str, Any], observed: dict[str, Any]) -> list[str]:
    """SM-03. The half of the verdict `expect_exit` cannot carry.

    A demonstration reports what it OBSERVED, and until this ticket a pytest
    slot observed one integer that a fully-skipped run also produces. Three
    checks, in the order a reader should think about them:

      1. `expect_passed` -- an exact count, for slots citing node ids.
      2. `expect_passed_at_least` -- a floor, for slots citing a whole file,
         where an exact count would go stale on an unrelated new test.
      3. `expect_skipped`, DEFAULT 0 -- applied whether or not the slot asks
         for it, because a skipped demonstration is not a demonstration and no
         slot should have to remember to say so.
    """

    counts = observed.get("counts")
    if counts is None:
        return []

    problems: list[str] = []
    passed = counts.get("passed", 0)

    exact = spec.get("expect_passed")
    if exact is not None and passed != exact:
        problems.append(
            f"{passed} test(s) passed, declared exactly {exact} "
            f"-- a demonstration that did not execute what it claims to"
        )
    floor = spec.get("expect_passed_at_least")
    if floor is not None and passed < floor:
        problems.append(
            f"{passed} test(s) passed, declared at least {floor} "
            f"-- a demonstration that did not execute what it claims to"
        )

    allowed_skips = spec.get("expect_skipped", 0)
    skipped = counts.get("skipped", 0)
    if skipped != allowed_skips:
        problems.append(
            f"{skipped} test(s) SKIPPED, declared {allowed_skips} -- pytest exits 0 for a "
            f"collected-and-skipped run, so this slot would otherwise report `ok` on a "
            f"demonstration that asserted nothing (SM-GM-I1)"
        )
    deselected = counts.get("deselected", 0)
    if deselected:
        problems.append(f"{deselected} test(s) DESELECTED; a filtered demonstration is vacuous")
    return problems


def demonstrate(spec: dict[str, Any]) -> dict[str, Any]:
    kind = spec.get("kind", "cli")
    if kind not in KINDS:
        raise DemonstrationError(f"unknown demonstration kind {kind!r}")
    if kind == "declared":
        return {"kind": kind, "ran": False, "problems": [], "reason": spec.get("reason", "")}

    workspace = Path(tempfile.mkdtemp(prefix="fi02-demo-"))
    try:
        tree = workspace / "tree"
        tree.mkdir()
        if kind == "cli":
            stage(spec, tree)
            observed = run_cli(spec, tree)
        else:
            observed = run_pytest(spec, tree)
        return {
            "kind": kind,
            "ran": True,
            "exit": observed["exit"],
            "problems": judge(spec, observed),
            "argv": observed["argv"],
            # SM-03: the executable count travels into the artifact, so a
            # future reader can see what a cell ran instead of inferring it
            # from an exit code that a fully-skipped run also produces.
            "counts": observed.get("counts"),
            "tail": "\n".join(observed["output"].splitlines()[-6:]),
        }
    finally:
        shutil.rmtree(workspace, ignore_errors=True)


# ---------------------------------------------------------------------------
# SM-03: the omission the enumeration could not see
# ---------------------------------------------------------------------------
#
# `test_the_named_instruments_are_all_enumerated` asserted `required <=
# enumerated` against a literal set of thirteen paths. That relation is
# ONE-DIRECTIONAL: a new instrument is not in `required`, so the subset stays
# true whether or not anyone registered it. It catches a RENAME and it cannot
# catch an OMISSION, its own docstring conceded so, and `FI-04-DF-04` was
# confirmed four times -- including by FI-04 itself, which shipped
# `run_arm_swap.py` in the same reconcile as the finding.
#
# The obvious repair is to add the missing paths to `required`. That is the
# shape rejected at `EVAL-RERUN-DF-01` and again at `ARM_MODULE_PREFIXES`: a
# literal that must be edited by the same person who forgot to register the
# instrument is not a check, it is a second thing to forget.
#
# So the set is DERIVED FROM THE TREE instead. `roots` declares WHERE the
# obligation applies -- a scope, one line, whose MEMBERS are discovered -- and
# every discovered candidate must appear in some row's `paths`. A new
# executable under a declared root is unregistered the moment it lands, and
# nothing anyone forgets to edit can make it register itself.
#
# WHAT IT CANNOT SEE, stated rather than left for the next sweep to find:
# the predicate is a `__main__` guard plus a nonzero exit path, so a repo
# tripwire that is a pytest FILE (the thermometer scan, the citation scan and
# their three siblings under `tests/`) has neither and is invisible to it.
# Those rows are added by hand and this check does not pretend otherwise. They
# are named in the registry's `[registry.enumeration]` comment and in
# `tests/test_instrument_demonstrations.py`; they are NOT named here, because
# `test_produced_code_prompt.py` refuses a Python file under `examples/` that
# names the produced-code instrument -- a mention is how a consumer arrives,
# and that tripwire went red on this very comment. Fixed by not naming it,
# never by widening the exemption; the same call SM-01 made one ticket ago.


def _has_nonzero_exit(tree: ast.AST) -> bool:
    """A verdict surface: some path out of this file that is not success."""

    def nonzero(args: list[ast.expr]) -> bool:
        if not args:
            return False
        return any(
            not (isinstance(arg, ast.Constant) and arg.value in (0, None)) for arg in args
        )

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, (ast.Name, ast.Attribute)):
            name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr
            if name in ("exit", "_exit", "SystemExit") and nonzero(node.args):
                return True
        if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
            func = node.exc.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
            if name == "SystemExit" and nonzero(node.exc.args):
                return True
    return False


def is_instrument_candidate(path: Path) -> bool:
    """The registry's own definition of a thing that owes it a row.

    Executable (a `__main__` guard) and able to return a verdict (a nonzero
    exit path). This is exactly what `SM-GM-I3` seeds -- an argparse surface, a
    `__main__`, a `return 1` -- and it is deliberately structural, so it cannot
    be satisfied by naming a file somewhere.
    """

    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    if "__main__" not in text:
        return False
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return False
    guarded = any(
        isinstance(node, ast.If)
        and "__main__" in ast.dump(node.test)
        for node in ast.walk(tree)
    )
    return guarded and _has_nonzero_exit(tree)


def discover_candidates(root: Path, enumeration: dict[str, Any]) -> list[str]:
    """Every executable under the declared roots, found by walking the tree."""

    excluded = tuple(entry["path"] for entry in enumeration.get("exclude", []))
    found: list[str] = []
    for declared in enumeration.get("roots", []):
        base = root / declared
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            relative = path.relative_to(root).as_posix()
            if any(relative.startswith(f"{prefix}/") for prefix in excluded):
                continue
            if is_instrument_candidate(path):
                found.append(relative)
    return found


def unregistered(root: Path, registry: dict[str, Any]) -> list[str]:
    enumeration = registry.get("registry", {}).get("enumeration")
    if not enumeration:
        raise DemonstrationError("the registry declares no [registry.enumeration] roots")
    declared = {path for entry in registry["instrument"] for path in entry.get("paths", [])}
    return [path for path in discover_candidates(root, enumeration) if path not in declared]


def check_enumeration(root: Path, registry: dict[str, Any]) -> int:
    enumeration = registry["registry"]["enumeration"]
    missing = unregistered(root, registry)
    print("SM-03 -- executables under a declared root with no row in the registry")
    print("=" * 78)
    print(f"root            {root}")
    print(f"declared roots  {', '.join(enumeration.get('roots', []))}")
    for entry in enumeration.get("exclude", []):
        print(f"  excluded      {entry['path']} -- {entry['reason']}")
    print("")
    if not missing:
        print("Every discovered executable has a row.")
        return 0
    print(f"UNREGISTERED INSTRUMENTS: {len(missing)}")
    print("-" * 78)
    for path in missing:
        print(f"  {path}")
    print("")
    print("  Each of these is executable and has a nonzero exit path, which is the")
    print("  registry's own definition of something that owes it a row. Add the row --")
    print("  `family = \"not-an-instrument\"` with a reason is a valid answer and is how")
    print("  a checked-and-rejected candidate stays on the record instead of going")
    print("  silent. What is not available is leaving it out.")
    return 1


# ---------------------------------------------------------------------------
# the enumeration
# ---------------------------------------------------------------------------


def load_registry(path: Path) -> dict[str, Any]:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def selected(instrument: dict[str, Any], only: list[str], tier: str) -> bool:
    if only and instrument["id"] not in only:
        return False
    return True


def slot_runnable(spec: dict[str, Any] | None, tier: str) -> bool:
    if spec is None:
        return False
    if spec.get("kind", "cli") == "declared":
        return False
    if tier == "fast" and spec.get("tier", "fast") != "fast":
        return False
    return True


def run(args: argparse.Namespace) -> int:
    registry = load_registry(args.registry)
    instruments = registry["instrument"]

    if args.check_enumeration:
        # Measured against `--root`, never against wherever this file happens
        # to live: SM-01 found the gap-mutant runner detecting itself because
        # its catalogue check read anchors out of the MUTATED tree. Anything
        # that measures the registry has to be told which tree to measure.
        return check_enumeration(args.root.resolve(), registry)

    if args.list:
        for entry in instruments:
            print(f"{entry['id']:<34} {entry['classification']}")
        return 0

    rows: list[dict[str, Any]] = []
    failures: list[str] = []

    for entry in instruments:
        if not selected(entry, args.only, args.tier):
            continue
        row: dict[str, Any] = {
            "id": entry["id"],
            "name": entry["name"],
            "paths": entry.get("paths", []),
            "family": entry["family"],
            "classification": entry["classification"],
            "watches": entry["watches"],
            "verdict_surface": entry["verdict_surface"],
            "has_failing_demonstration": "failing" in entry,
            "has_passing_demonstration": "passing" in entry,
            "no_failing_demonstration": entry.get("no_failing_demonstration"),
            "no_passing_demonstration": entry.get("no_passing_demonstration"),
            "slots": {},
        }
        for slot in SLOTS:
            spec = entry.get(slot)
            if spec is None:
                continue
            if not slot_runnable(spec, args.tier):
                row["slots"][slot] = {"ran": False, "skipped": True,
                                      "summary": spec.get("summary", ""),
                                      "reason": spec.get("reason", "")}
                continue
            try:
                result = demonstrate(spec)
            except DemonstrationError as exc:
                result = {"kind": spec.get("kind", "cli"), "ran": False,
                          "problems": [f"MALFORMED DEMONSTRATION: {exc}"]}
            except subprocess.TimeoutExpired:
                result = {"kind": spec.get("kind", "cli"), "ran": False,
                          "problems": ["TIMED OUT"]}
            result["summary"] = spec.get("summary", "")
            row["slots"][slot] = result
            for problem in result["problems"]:
                failures.append(f"{entry['id']} / {slot}: {problem}")
        rows.append(row)

    report = {
        "registry": registry["registry"],
        "tier": args.tier,
        "rows": rows,
        "counts": counts(rows),
        "reproduction_failures": failures,
    }

    if args.format == "json":
        payload = json.dumps(report, indent=2, sort_keys=True)
    else:
        payload = render(report)
    print(payload)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        print(f"\nwrote {args.out}")
    return 1 if failures else 0


def counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    instruments = [r for r in rows if r["family"] != "not-an-instrument"]
    return {
        "enumerated": len(rows),
        "instruments": len(instruments),
        "not_an_instrument": len(rows) - len(instruments),
        "with_failing_demonstration": sum(1 for r in instruments if r["has_failing_demonstration"]),
        "without_failing_demonstration": sum(
            1 for r in instruments if not r["has_failing_demonstration"]
        ),
        "with_passing_demonstration": sum(1 for r in instruments if r["has_passing_demonstration"]),
        "with_a_demonstrated_blind_spot": sum(1 for r in rows if "blind_spot" in r["slots"]),
    }


def render(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("FI-02 -- every shipped instrument, and whether it can be shown to fail")
    lines.append("=" * 78)
    lines.append("")
    lines.append(f"{'instrument':<34} {'fail':<6} {'pass':<6} {'blind':<6} classification")
    lines.append("-" * 78)

    def mark(row: dict[str, Any], slot: str) -> str:
        result = row["slots"].get(slot)
        if result is None:
            return "-"
        if result.get("skipped"):
            return "skip"
        if result["problems"]:
            return "MISS"
        if not result.get("ran"):
            return "decl"
        return "ok"

    for row in report["rows"]:
        lines.append(
            f"{row['id']:<34} {mark(row, 'failing'):<6} {mark(row, 'passing'):<6} "
            f"{mark(row, 'blind_spot'):<6} {row['classification']}"
        )

    lines.append("")
    lines.append("THE COUNT -- this command's product")
    lines.append("-" * 78)
    counted = report["counts"]
    lines.append(f"  enumerated                              {counted['enumerated']}")
    lines.append(f"  of which classified NOT an instrument   {counted['not_an_instrument']}")
    lines.append(f"  instruments                             {counted['instruments']}")
    lines.append(f"  WITH a demonstrated failing input       {counted['with_failing_demonstration']}")
    lines.append(f"  WITHOUT one, and why, below             {counted['without_failing_demonstration']}")
    lines.append(f"  with a demonstrated BLIND SPOT          {counted['with_a_demonstrated_blind_spot']}")
    lines.append("")
    lines.append("  No target is set on that ratio. A high count in the fifth row is the")
    lines.append("  honest outcome and the epic prefers it to a flattering one.")

    without = [r for r in report["rows"]
               if r["family"] != "not-an-instrument" and not r["has_failing_demonstration"]]
    if without:
        lines.append("")
        lines.append("INSTRUMENTS THAT CANNOT BE SHOWN TO FAIL, with the reason")
        lines.append("-" * 78)
        for row in without:
            lines.append(f"  {row['id']}")
            lines.append(f"      {row['no_failing_demonstration']}")

    blind = [r for r in report["rows"] if "blind_spot" in r["slots"]]
    if blind:
        lines.append("")
        lines.append("DEMONSTRATED BLIND SPOTS -- a genuine break each one does NOT report")
        lines.append("-" * 78)
        for row in blind:
            lines.append(f"  {row['id']}")
            lines.append(f"      {row['slots']['blind_spot'].get('summary', '')}")

    if report["reproduction_failures"]:
        lines.append("")
        lines.append("A DECLARED DEMONSTRATION DID NOT REPRODUCE")
        lines.append("-" * 78)
        for problem in report["reproduction_failures"]:
            lines.append(f"  {problem}")
        lines.append("")
        lines.append("  Either the instrument changed or the demonstration went stale.")
        lines.append("  Both are things a reader has to be told.")
    else:
        lines.append("")
        lines.append("Every declared demonstration reproduced.")
    return "\n".join(lines)


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    parser.add_argument("--only", action="append", default=[])
    parser.add_argument("--tier", choices=("fast", "all"), default="all")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--list", action="store_true")
    parser.add_argument(
        "--check-enumeration",
        action="store_true",
        help="report executables under a declared root that have no registry row",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=REPO_ROOT,
        help="the tree to scan for --check-enumeration; never assumed",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    add_arguments(parser)
    return run(parser.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
