"""BS-07 regressions: TLC config invariant lists (#155, #159) and the emitted
TLC command (#143 SF-041).

There is ONE invariant parser (`analyze_complexity.parse_cfg_invariants`);
`spec_evolution.validate_model_pair` and the close-time complexity ledger read
the cfg through it. Every reader is still tested against the SAME fixture set
below, so a second parser growing back would be caught by the shared table.
"""

from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import analyze_complexity, onboard_program_model, scaffold_spec
from scripts.spec_evolution import (
    record_complexity_ledger,
    select_model_files,
    validate_model_pair,
)
from conftest import write_ticket_ledger_input


COUNTER_TLA = """---- MODULE Counter ----
EXTENDS Naturals
VARIABLE x
vars == <<x>>
Init == x = 0
Step == x' = 1 - x
Next == Step
Spec == Init /\\ [][Next]_vars
TypeOK == x \\in 0..1
Bounded == x <= 1
NonNeg == x >= 0
Live == <>(x = 1)
====
"""

#: (id, invariant section of the cfg, the names TLC checks). Each is a
#: config TLC accepts and checks in full.
VALID_INVARIANT_SECTIONS = [
    ("singular-one-per-line", "INVARIANT TypeOK\nINVARIANT Bounded\nINVARIANT NonNeg", ["TypeOK", "Bounded", "NonNeg"]),
    ("plural-on-keyword-line", "INVARIANTS TypeOK Bounded NonNeg", ["TypeOK", "Bounded", "NonNeg"]),
    ("singular-with-a-list", "INVARIANT TypeOK Bounded NonNeg", ["TypeOK", "Bounded", "NonNeg"]),
    ("plural-continuation-one-line", "INVARIANTS\n  TypeOK Bounded NonNeg", ["TypeOK", "Bounded", "NonNeg"]),
    ("plural-one-per-line", "INVARIANTS\n  TypeOK\n  Bounded\n  NonNeg", ["TypeOK", "Bounded", "NonNeg"]),
    ("mixed-newline-and-space", "INVARIANTS TypeOK\n  Bounded NonNeg", ["TypeOK", "Bounded", "NonNeg"]),
    ("tabs-and-trailing-comment", "INVARIANTS\tTypeOK \\* typing\n\tBounded\t NonNeg", ["TypeOK", "Bounded", "NonNeg"]),
    # The #155 shape: a plural list plus further singular INVARIANT and
    # PROPERTY declarations in the same config.
    ("issue-155-plural-plus-singular-and-property", "INVARIANTS TypeOK Bounded\nINVARIANT NonNeg\nPROPERTY Live", ["TypeOK", "Bounded", "NonNeg"]),
]


def cfg_text(section: str) -> str:
    return "SPECIFICATION Spec\n" + section + "\nCHECK_DEADLOCK FALSE\n"


def counter_model(directory: Path, section: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "Counter.tla").write_text(COUNTER_TLA, encoding="utf-8")
    (directory / "Counter.cfg").write_text(cfg_text(section), encoding="utf-8")
    return directory


@pytest.mark.parametrize(
    "section,expected", [(s, e) for _, s, e in VALID_INVARIANT_SECTIONS],
    ids=[i for i, _, _ in VALID_INVARIANT_SECTIONS],
)
def test_bs07_cfg_parser_reads_every_invariant_name(section: str, expected: list[str]) -> None:
    assert analyze_complexity.parse_cfg_invariants(cfg_text(section)) == expected


@pytest.mark.parametrize(
    "section", [s for _, s, _ in VALID_INVARIANT_SECTIONS],
    ids=[i for i, _, _ in VALID_INVARIANT_SECTIONS],
)
def test_bs07_cfg_model_pair_accepts_every_legal_invariant_list(tmp_path: Path, section: str) -> None:
    selection = select_model_files(counter_model(tmp_path / "model", section))
    assert selection is not None
    assert validate_model_pair(selection) == []


@pytest.mark.parametrize(
    "section", [s for _, s, _ in VALID_INVARIANT_SECTIONS],
    ids=[i for i, _, _ in VALID_INVARIANT_SECTIONS],
)
def test_bs07_cfg_complexity_ledger_is_not_skipped(tmp_path: Path, capsys, section: str) -> None:
    """#155: close-time ledger skipped on a valid multi-invariant config."""
    specs_dir = tmp_path / "specs"
    ticket_dir = specs_dir / "tickets" / "T-1"
    model_dir = counter_model(ticket_dir / "current", section)
    record = record_complexity_ledger(
        specs_dir,
        scope="ticket",
        scope_id="T-1",
        workflow="fixture",
        model_dir=model_dir,
        input_path=write_ticket_ledger_input(ticket_dir),
    )
    err = capsys.readouterr().err
    assert "complexity ledger skipped" not in err, err
    assert record is not None


def test_bs07_cfg_unknown_invariant_in_a_list_is_still_a_mismatch(tmp_path: Path) -> None:
    """Negative control: tokenising must not make a real typo pass."""
    selection = select_model_files(
        counter_model(tmp_path / "model", "INVARIANTS TypeOK Missing Bounded")
    )
    problems = validate_model_pair(selection)
    assert len(problems) == 1
    assert "INVARIANT Missing," in problems[0]


def test_bs07_cfg_a_section_keyword_mid_line_still_ends_the_list() -> None:
    assert analyze_complexity.parse_cfg_invariants(
        "INVARIANTS TypeOK Bounded CONSTANTS N = 3\nPROPERTY Live\n"
    ) == ["TypeOK", "Bounded"]


# ---------------------------------------------------------------------------
# #143 SF-041: the TLC command the scaffolders emit must run from the project
# with what skill-manager installs (tlc2 on PATH) -- no project-local script,
# no Python interpreter for a preflight to refuse.
# ---------------------------------------------------------------------------


def _fake_tlc2(bin_dir: Path, log: Path) -> None:
    bin_dir.mkdir(parents=True, exist_ok=True)
    script = bin_dir / "tlc2"
    script.write_text(
        "#!/usr/bin/env bash\n"
        f'printf "%s\\n" "$PWD" "$@" > "{log}"\n'
        'cfg=""; tla=""\n'
        'while [ $# -gt 0 ]; do case "$1" in -config) cfg="$2"; shift 2;; -metadir) shift 2;; *) tla="$1"; shift;; esac; done\n'
        'test -f "$cfg" && test -f "$tla"\n',
        encoding="utf-8",
    )
    script.chmod(0o755)


def _run_emitted(command: str, cwd: Path, tmp_path: Path) -> tuple[int, list[str], str]:
    log = tmp_path / "tlc2-invocation.txt"
    bin_dir = tmp_path / "fakebin"
    _fake_tlc2(bin_dir, log)
    env = dict(os.environ)
    # Only the fake tlc2 and the basic system tools: no project scripts/ dir,
    # and no python3 the command could be relying on.
    env["PATH"] = f"{bin_dir}:/usr/bin:/bin"
    result = subprocess.run(
        ["bash", "-c", command], cwd=cwd, env=env, capture_output=True, text=True
    )
    lines = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    return result.returncode, lines, result.stderr


def _onboarded_project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    model = project / "specs" / "program_model"
    model.mkdir(parents=True)
    (model / "Internal.tla").write_text("---- MODULE Internal ----\n====\n", encoding="utf-8")
    (model / "Internal.cfg").write_text("SPECIFICATION Spec\n", encoding="utf-8")
    (model / "External.tla").write_text("---- MODULE External ----\n====\n", encoding="utf-8")
    (model / "External.cfg").write_text("SPECIFICATION Spec\n", encoding="utf-8")
    return project


def _readme_validate_commands(readme: str) -> list[str]:
    block = readme.split("```bash", 1)[1].split("```", 1)[0]
    return [line.strip() for line in block.splitlines() if line.strip() and not line.strip().startswith("tla-spec-dev")]


@pytest.mark.parametrize("full", [False, True], ids=["minimal", "full"])
def test_bs07_tlc_command_in_onboarded_manifest_runs_from_the_project_root(tmp_path: Path, full: bool) -> None:
    project = _onboarded_project(tmp_path)
    text = onboard_program_model.manifest("Program", "program", "specs", full=full)
    commands = re.findall(r"- Run TLC[^\n]*? - (.+)$", text, flags=re.MULTILINE)
    assert commands, text
    for command in commands:
        assert "python" not in command, command
        code, invocation, err = _run_emitted(command, project, tmp_path)
        assert code == 0, (command, err)
        assert Path(invocation[0]).resolve() == (project / "specs" / "program_model").resolve()


@pytest.mark.parametrize("full", [False, True], ids=["minimal", "full"])
def test_bs07_tlc_command_in_onboarded_readme_runs_from_the_project_root(tmp_path: Path, full: bool) -> None:
    project = _onboarded_project(tmp_path)
    commands = _readme_validate_commands(onboard_program_model.readme("Program", "specs", full=full))
    assert commands
    for command in commands:
        assert "python" not in command, command
        code, _, err = _run_emitted(command, project, tmp_path)
        assert code == 0, (command, err)


def test_bs07_tlc_command_in_tutorial_readme_runs_from_the_spec_dir(tmp_path: Path) -> None:
    spec_dir = _onboarded_project(tmp_path) / "specs" / "program_model"
    commands = _readme_validate_commands(scaffold_spec.readme("Counter"))
    assert len(commands) == 2
    for command in commands:
        assert "python" not in command, command
        code, _, err = _run_emitted(command, spec_dir, tmp_path)
        assert code == 0, (command, err)
