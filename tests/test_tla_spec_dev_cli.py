import os
import subprocess
import sys
from pathlib import Path

from conftest import write_ticket_ledger_input


ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "skills" / "spec-double-2"
sys.path.insert(0, str(ROOT))

from scripts import tla_spec_dev
from scripts.generate_cases_from_tlc_dump import ActionMetadata, Edge, render_python_package


def run_cli(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SKILL_ROOT / "scripts" / "tla_spec_dev.py"), *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def test_cli_version_uses_skill_manifest_version() -> None:
    result = run_cli("--version")

    assert result.returncode == 0
    assert result.stdout.strip() == f"tla-spec-dev {tla_spec_dev.skill_version()}"


def test_cli_root_help_progressively_exposes_workflow_commands() -> None:
    result = run_cli("--help")

    assert result.returncode == 0
    assert "--spec-root" in result.stdout
    assert "scaffold" in result.stdout
    assert "open" in result.stdout
    assert "run" in result.stdout
    assert "close" in result.stdout
    assert "retire" in result.stdout
    assert "scaffold project -> scaffold workflow -> open ticket" in result.stdout


def test_cli_subcommand_help_documents_external_command_surface() -> None:
    commands = [
        ("scaffold", "--help", "project", "workflow"),
        ("scaffold", "project", "--help", "program_model", "baseline"),
        ("scaffold", "workflow", "--help", "current", "desired_program_model"),
        ("open", "ticket", "--help", "ticket_name", "desired-first"),
        ("run", "spec-unit-tests", "--help", "generated/adapted", "spec root"),
        ("retire", "ticket", "--help", "no validation", "ticket_name"),
        ("close", "ticket", "--help", "append-only history", "ticket_name"),
    ]

    for args in commands:
        *argv, first_expected, second_expected = args
        result = run_cli(*argv)
        assert result.returncode == 0
        assert first_expected in result.stdout
        assert second_expected in result.stdout


def test_run_spec_unit_tests_fails_when_no_spec_tests_exist(tmp_path: Path) -> None:
    result = run_cli("--spec-root", "project_specs", "run", "spec-unit-tests", cwd=tmp_path)

    assert result.returncode == 2
    assert "spec-unit target does not exist" in result.stderr


def test_incomplete_parent_commands_fail_with_next_step_guidance() -> None:
    for command in ["scaffold", "open", "run", "retire", "close"]:
        result = run_cli(command)

        assert result.returncode == 2
        assert f"incomplete command: tla-spec-dev {command}" in result.stderr
        assert "next:" in result.stderr


def test_cli_scaffold_project_and_workflow_use_spec_root(tmp_path: Path) -> None:
    result_project = run_cli(
        "--spec-root",
        "project_specs",
        "scaffold",
        "project",
        "--name",
        "CliProject",
        "--full",
        cwd=tmp_path,
    )
    result_workflow = run_cli(
        "--spec-root",
        "project_specs",
        "scaffold",
        "workflow",
        "CLI-123",
        "CLI scaffold ticket",
        cwd=tmp_path,
    )

    assert result_project.returncode == 0, result_project.stderr
    assert result_workflow.returncode == 0, result_workflow.stderr
    for view_file in (
        "Core.tla",
        "Internal.tla",
        "External.tla",
        "adapters.py",
        "providers.py",
        "testgraph_bindings.yml",
    ):
        assert (tmp_path / "project_specs/program_model" / view_file).exists()
        assert (tmp_path / "project_specs/current" / view_file).exists()
        assert (tmp_path / "project_specs/desired_program_model" / view_file).exists()
    # The three-module baseline must not leave a single-module stand-in behind.
    assert not (tmp_path / "project_specs/current/CliProject.tla").exists()
    assert not (tmp_path / "project_specs/current/MC.cfg").exists()
    assert not (tmp_path / "project_specs/current/tests/test_program_model_onboarding.py").exists()
    assert not (tmp_path / "project_specs/desired_program_model/tests/test_program_model_onboarding.py").exists()
    assert "CLI-123" in (tmp_path / "project_specs/desired_program_model/ticket_plan.yaml").read_text(encoding="utf-8")


def test_cli_run_spec_unit_tests_uses_project_current_tests(tmp_path: Path) -> None:
    run_cli("--spec-root", "project_specs", "scaffold", "project", "--name", "CliProject", cwd=tmp_path)
    run_cli("--spec-root", "project_specs", "scaffold", "workflow", "CLI-201", "CLI unit tests", cwd=tmp_path)

    result = run_cli("--spec-root", "project_specs", "run", "spec-unit-tests", "--scope", "project", cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    assert "spec-unit validation passed" in result.stdout
    assert "project_specs/current" in result.stdout


def test_cli_run_spec_unit_tests_targets_active_ticket_current(tmp_path: Path) -> None:
    ticket_id = "CLI-202"
    run_cli("--spec-root", "project_specs", "scaffold", "project", "--name", "CliProject", cwd=tmp_path)
    run_cli("--spec-root", "project_specs", "scaffold", "workflow", ticket_id, "CLI ticket unit tests", cwd=tmp_path)
    run_cli("--spec-root", "project_specs", "open", "ticket", ticket_id, "--with-current", cwd=tmp_path)
    ticket_test = tmp_path / "project_specs" / "tickets" / ticket_id / "current" / "tests" / "test_ticket_unit.py"
    ticket_test.parent.mkdir(parents=True, exist_ok=True)
    ticket_test.write_text("def test_ticket_unit():\n    assert True\n", encoding="utf-8")

    result = run_cli("--spec-root", "project_specs", "run", "spec-unit-tests", cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    assert "project_specs/current" in result.stdout
    assert f"project_specs/tickets/{ticket_id}/current" in result.stdout


def test_cli_run_spec_unit_tests_targets_a_desired_only_ticket(tmp_path: Path) -> None:
    ticket_id = "CLI-203"
    run_cli("--spec-root", "project_specs", "scaffold", "project", "--name", "CliProject", cwd=tmp_path)
    run_cli("--spec-root", "project_specs", "scaffold", "workflow", ticket_id, "CLI desired-only", cwd=tmp_path)
    run_cli("--spec-root", "project_specs", "open", "ticket", ticket_id, cwd=tmp_path)
    ticket_test = tmp_path / "project_specs" / "tickets" / ticket_id / "desired" / "tests" / "test_ticket_unit.py"
    ticket_test.parent.mkdir(parents=True, exist_ok=True)
    ticket_test.write_text("def test_ticket_unit():\n    assert True\n", encoding="utf-8")

    result = run_cli("--spec-root", "project_specs", "run", "spec-unit-tests", "--ticket", ticket_id, cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    assert f"project_specs/tickets/{ticket_id}/desired" in result.stdout


def test_cli_run_spec_unit_tests_auto_includes_project_current_tests(tmp_path: Path) -> None:
    ticket_id = "CLI-204"
    run_cli("--spec-root", "project_specs", "scaffold", "project", "--name", "CliProject", cwd=tmp_path)
    run_cli("--spec-root", "project_specs", "scaffold", "workflow", ticket_id, "CLI active ticket tests", cwd=tmp_path)
    run_cli("--spec-root", "project_specs", "open", "ticket", ticket_id, "--with-current", cwd=tmp_path)
    project_test = tmp_path / "project_specs" / "current" / "tests" / "test_project_current_failure.py"
    project_test.parent.mkdir(parents=True, exist_ok=True)
    project_test.write_text("def test_project_current_failure():\n    assert False\n", encoding="utf-8")
    ticket_test = tmp_path / "project_specs" / "tickets" / ticket_id / "current" / "tests" / "test_ticket_unit.py"
    ticket_test.parent.mkdir(parents=True, exist_ok=True)
    ticket_test.write_text("def test_ticket_unit():\n    assert True\n", encoding="utf-8")

    result = run_cli("--spec-root", "project_specs", "run", "spec-unit-tests", cwd=tmp_path)

    assert result.returncode != 0
    assert "project_specs/current" in result.stdout
    assert f"project_specs/tickets/{ticket_id}/current" in result.stdout
    assert "test_project_current_failure" in result.stdout


def test_cli_run_spec_unit_tests_fails_when_any_selected_target_has_no_validations(tmp_path: Path) -> None:
    ticket_id = "CLI-205"
    spec_root = tmp_path / "project_specs"
    (spec_root / "current").mkdir(parents=True)
    plan = spec_root / "desired_program_model" / "ticket_plan.yaml"
    plan.parent.mkdir(parents=True)
    plan.write_text(
        f"""status:
  active_ticket: {ticket_id}
tickets:
  - id: {ticket_id}
    status: next
""",
        encoding="utf-8",
    )
    ticket_test = spec_root / "tickets" / ticket_id / "current" / "tests" / "test_ticket_unit.py"
    ticket_test.parent.mkdir(parents=True)
    ticket_test.write_text("def test_ticket_unit():\n    assert True\n", encoding="utf-8")

    result = run_cli("--spec-root", "project_specs", "run", "spec-unit-tests", cwd=tmp_path)

    assert result.returncode == 2
    assert "project_specs/current" in result.stderr
    assert "no spec-unit pytest tests or generated case packages found" in result.stderr


def test_cli_run_spec_unit_tests_runs_generated_case_adapters(tmp_path: Path) -> None:
    spec_root = tmp_path / "project_specs"
    current = spec_root / "current"
    generated = spec_root / "generated" / "spec-unit" / "sample_cases"
    current.mkdir(parents=True)
    render_python_package(
        module="CliProject",
        states={"0": {"items": frozenset()}, "1": {"items": frozenset({"a"})}},
        edges=[Edge("0", "1", "Create")],
        package_dir=generated,
        view="internal",
        action_metadata={"Create": ActionMetadata("Create", "internal", "unit_direct", ("spec_unit",))},
    )
    (current / "case_adapters.toml").write_text(
        '[adapters.Create]\nadapter = "production_adapters:CreateAdapter"\n',
        encoding="utf-8",
    )
    (current / "production_adapters.py").write_text(
        """from spec_double_compiler.runtime import CaseRunResult


class CreateAdapter:
    def run(self, case, work_dir=None):
        return CaseRunResult(after=case.after, output=case.output)
""",
        encoding="utf-8",
    )

    result = run_cli("--spec-root", "project_specs", "run", "spec-unit-tests", "--scope", "project", cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    assert "executed 1 cases in batch" in result.stdout


def test_cli_open_ticket_and_close_ticket_use_spec_root(tmp_path: Path) -> None:
    ticket_id = "CLI-200"
    result_project = run_cli(
        "--spec-root",
        "project_specs",
        "scaffold",
        "project",
        "--name",
        "CliProject",
        "--full",
        cwd=tmp_path,
    )
    result_workflow = run_cli(
        "--spec-root",
        "project_specs",
        "scaffold",
        "workflow",
        ticket_id,
        "CLI ticket lifecycle",
        cwd=tmp_path,
    )
    result_open = run_cli(
        "--spec-root",
        "project_specs",
        "open",
        "ticket",
        ticket_id,
        cwd=tmp_path,
    )

    assert result_project.returncode == 0, result_project.stderr
    assert result_workflow.returncode == 0, result_workflow.stderr
    assert result_open.returncode == 0, result_open.stderr
    assert "Edit" in result_open.stdout
    assert "desired" in result_open.stdout
    ticket_dir = tmp_path / "project_specs" / "tickets" / ticket_id
    assert (ticket_dir / "desired" / "External.tla").exists()
    # Desired-only by default (2026-09-14): no ticket current/, no convergence.
    assert not (ticket_dir / "current").exists()
    assert (ticket_dir / "desired" / "testgraph_bindings.yml").exists()

    # MF-019: `open ticket` scaffolds the complexity-ledger input with TODO
    # sentinels that fail the close gate. Filling it in is a required close-out
    # step, so the end-to-end lifecycle exercises it here.
    assert (ticket_dir / "results" / "complexity_ledger.yaml").exists()
    write_ticket_ledger_input(ticket_dir)

    plan_path = tmp_path / "project_specs" / "desired_program_model" / "ticket_plan.yaml"
    plan_path.write_text(plan_path.read_text(encoding="utf-8").replace("status: next", "status: done", 1), encoding="utf-8")
    result_close = run_cli(
        "--spec-root",
        "project_specs",
        "close",
        "ticket",
        ticket_id,
        "--summary",
        "closed from CLI test",
        cwd=tmp_path,
    )

    history_dir = tmp_path / "project_specs" / ".history" / "desired-ticket-workflow" / f"ticket-000-{ticket_id}"
    assert result_close.returncode == 0, result_close.stderr
    assert "recorded spec history entry" in result_close.stdout
    assert not ticket_dir.exists()
    assert (history_dir / "manifest.json").exists()
    assert (history_dir / "ticket" / "desired" / "External.tla").exists()
    assert (tmp_path / "project_specs" / "current" / "External.tla").exists()
    # MF-019: the close recorded a complexity ledger entry, and the delta is
    # stored jointly with its retention evidence in the history manifest.
    assert "complexity ledger" in result_close.stdout
    ledger = tmp_path / "project_specs" / "results" / "complexity_ledger.json"
    assert ledger.exists()
    import json as _json
    manifest = _json.loads((history_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["complexity_delta"] is not None
    assert manifest["retention_evidence"]["effect_conformance"]["classification"] == "retained"
    assert manifest["refinement_record"]["outcome"] == "none"


def test_cli_open_ticket_records_custom_ticket_root_in_close_guidance(tmp_path: Path) -> None:
    ticket_id = "CLI-203"
    run_cli("--spec-root", "project_specs", "scaffold", "project", "--name", "CliProject", cwd=tmp_path)
    run_cli("--spec-root", "project_specs", "scaffold", "workflow", ticket_id, "Custom ticket root", cwd=tmp_path)

    result_open = run_cli(
        "--spec-root",
        "project_specs",
        "open",
        "ticket",
        ticket_id,
        "--ticket-root",
        "work/items",
        cwd=tmp_path,
    )

    ticket_state = (tmp_path / "project_specs" / "work" / "items" / ticket_id / "ticket.yaml").read_text(
        encoding="utf-8"
    )
    assert result_open.returncode == 0, result_open.stderr
    assert "close ticket CLI-203 --ticket-root work/items" in result_open.stdout
    assert "tla-spec-dev --spec-root project_specs close ticket CLI-203 --ticket-root work/items" in ticket_state


def test_skill_script_installs_tla_spec_dev_wrapper(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    cache_dir = tmp_path / "cache"
    env = {
        **os.environ,
        "SKILL_MANAGER_BIN_DIR": str(bin_dir),
        "SKILL_MANAGER_CACHE_DIR": str(cache_dir),
        # SI-11: the skill-script deps moved to the PLUGIN manifest, so the
        # installer lives at the plugin root and skill-manager hands it the
        # PLUGIN's dir and name. A `skill-script:` dep is resolved by the
        # installed unit's name and a contained skill's name never reaches the
        # resolver, so `spec-double-2` was never a value this script could be
        # invoked with in production (SIS-W2-F-05). This reproduces the
        # environment a real install actually creates.
        "SKILL_DIR": str(ROOT),
        "SKILL_NAME": "tla-spec-dev",
    }

    install = subprocess.run(
        ["bash", str(ROOT / "skill-scripts" / "install-tla-spec-dev.sh")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    wrapper = bin_dir / "tla-spec-dev"
    installed = subprocess.run(
        [str(wrapper), "--version"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )

    assert install.returncode == 0, install.stderr
    assert wrapper.exists()
    assert os.access(wrapper, os.X_OK)
    assert installed.returncode == 0
    assert installed.stdout.strip() == f"tla-spec-dev {tla_spec_dev.skill_version()}"


# ---------------------------------------------------------------------------
# RC-01 (MF-026 G-6): case generation is reachable from the shipped parser
# ---------------------------------------------------------------------------


def _import_closure(entry: Path) -> set[str]:
    """Modules under scripts/ reachable from `entry` by import, transitively.

    The same walk the coverage audit used to establish that
    `generate_cases_from_tlc_dump` and `case_modules` were reachable only by
    running their files. Imports inside function bodies count -- the shipped CLI
    defers almost every import to its handler -- so this reads the AST rather
    than importing.
    """
    import ast

    scripts_dir = SKILL_ROOT / "scripts"
    known = {path.stem for path in scripts_dir.glob("*.py")}
    seen: set[str] = set()
    queue = [entry.stem]
    while queue:
        name = queue.pop()
        if name in seen or name not in known:
            continue
        seen.add(name)
        tree = ast.parse((scripts_dir / f"{name}.py").read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                queue.extend(alias.name.split(".")[-1] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    queue.append(node.module.split(".")[-1])
                queue.extend(alias.name for alias in node.names)
    return seen


def test_case_generation_is_reachable_from_the_shipped_parser() -> None:
    """MF-026 G-6, the headline gap, asserted so it cannot silently reopen.

    Case-module generation is this epic's flagship feature and the CLI had no
    subcommand for it: `generate_cases_from_tlc_dump.py` and `case_modules.py`
    were reachable only by running the files. Because every oracle in this
    toolchain is bounded to what is already modeled, that surface was never
    generated into a case, never adapted and never mutated -- and CM-01 and
    RP-03 both closed "zero model delta" against it while all four oracles
    reported green.
    """
    closure = _import_closure(SKILL_ROOT / "scripts" / "tla_spec_dev.py")
    assert "generate_cases_from_tlc_dump" in closure
    assert "case_modules" in closure
    assert "infer_action_params" in closure


def test_generate_cases_is_a_shipped_subcommand() -> None:
    result = run_cli("generate", "cases", "--help")
    assert result.returncode == 0
    assert "--coverage-json" in result.stdout

    incomplete = run_cli("generate")
    assert incomplete.returncode == 2
    assert "tla-spec-dev generate cases" in incomplete.stderr


# ---------------------------------------------------------------------------
# RC-01 (MF-026 G-2/G-3): --out is constrained to the declared port's target
# ---------------------------------------------------------------------------


def _tiny_model(directory: Path) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    tla = directory / "Tiny.tla"
    cfg = directory / "MC.cfg"
    tla.write_text(
        "---- MODULE Tiny ----\nEXTENDS Naturals\n\nVARIABLES x\n\nvars == << x >>\n\n"
        "Init == x = 0\nStep == x' = (x + 1) % 3\n\nNext == Step\n\n"
        "TypeInvariant == x \\in 0..2\n\nSpec == Init /\\ [][Next]_vars\n"
        "=====================\n",
        encoding="utf-8",
    )
    cfg.write_text("SPECIFICATION Spec\n\nINVARIANTS\n  TypeInvariant\n", encoding="utf-8")
    return tla, cfg


def test_analyze_out_refuses_a_path_the_evidence_port_does_not_cover(tmp_path: Path) -> None:
    """G-2/G-3: an evidence write that lands outside `**/results/**` is undeclared.

    Both scans took a bare string and did `mkdir(parents=True); write_text(...)`
    on it, so the file could land anywhere while the only port that could have
    covered it targets `**/results/**`. The audit's remedy was "declare the port
    and constrain the path, or drop --out"; the path is constrained, and it is
    REFUSED rather than silently relocated -- rewriting the operator's path
    would make the flag lie about where the file went.

    Two of the three `--out` flags G-2/G-3 constrained belonged to the
    architecture scanners and went with them on 2026-08-04. `analyze complexity`
    keeps its flag and keeps the constraint, which is the half that matters: the
    constraint lives in one place (`scripts/spec_paths.py resolve_evidence_out`)
    so the `evidence_report` declaration is true of every caller.
    """
    tla, cfg = _tiny_model(tmp_path / "spec")
    stray = tmp_path / "anywhere" / "report.txt"
    declared = tmp_path / "results" / "report.txt"

    command = ("analyze", "complexity")
    refused = run_cli(*command, str(tla), str(cfg), "--out", str(stray), cwd=tmp_path)
    assert refused.returncode == 2, f"{command}: {refused.stdout}"
    assert "results/" in refused.stderr
    assert "evidence_report" in refused.stderr
    assert not stray.exists()

    accepted = run_cli(*command, str(tla), str(cfg), "--out", str(declared), cwd=tmp_path)
    assert accepted.returncode == 0, accepted.stderr
    assert declared.is_file()


def test_generate_cases_out_is_constrained_to_the_declared_spec_tree(tmp_path: Path) -> None:
    """N-2: the class G-2/G-3 closed, shipped again on the new command path.

    RC-01 fixed three `--out` flags and shipped a fourth unconstrained one in
    the same commit. `generate cases --out` was `required=True` with no
    location constraint, and `--dot` beside it decides where the TLC metadir
    `shutil.rmtree` lands -- a DESTRUCTIVE delete at a caller-chosen path, on a
    newly modeled action, declared by ports that target `**/specs/**`.

    Refused before anything expensive runs: no TLC spawn, no directory created,
    no delete. The refusal is checked at the CLI so it covers the modeled
    `GenerateCases` path, not just the module function.
    """
    tla, cfg = _tiny_model(tmp_path / "spec")
    stray = tmp_path / "anywhere"

    refused = run_cli(
        "generate", "cases", str(tla), str(cfg), "--out", str(stray), cwd=tmp_path
    )
    assert refused.returncode == 2, refused.stdout
    assert "specs/" in refused.stderr
    assert "spec_tree" in refused.stderr
    assert not stray.exists()

    # --dot is refused for the same reason even when --out is fine, because the
    # metadir the run deletes is derived from it.
    declared_out = tmp_path / "specs" / "generated"
    stray_dot = tmp_path / "elsewhere" / "Tiny.dot"
    refused_dot = run_cli(
        "generate", "cases", str(tla), str(cfg),
        "--out", str(declared_out), "--dot", str(stray_dot), cwd=tmp_path,
    )
    assert refused_dot.returncode == 2, refused_dot.stdout
    assert "spec_tree_delete" in refused_dot.stderr
    assert not stray_dot.parent.exists()


def test_generate_cases_metadir_delete_stays_inside_the_declared_tree(tmp_path: Path) -> None:
    """The rmtree is constrained BY CONSTRUCTION, not by a second check.

    `run_tlc_dump` derives `metadir = dot_path.parent / ".tlc-states" / stem`
    and `shutil.rmtree`s it in its finally branch. Constraining `--dot` is what
    constrains the delete, so the property worth asserting is the derivation:
    every path this action deletes is under the `spec_tree_delete` target.
    """
    from scripts.spec_paths import SPEC_TREE_DIR_NAME, resolve_spec_tree_out

    spec_dir = tmp_path / "specs" / "program_model"
    spec_dir.mkdir(parents=True)
    resolved = resolve_spec_tree_out(
        tmp_path / "specs" / "generated" / "Tiny.dot", spec_dir, is_file=True
    )
    metadir = resolved.parent / ".tlc-states" / "Tiny"
    assert SPEC_TREE_DIR_NAME in metadir.parts


# REMOVED 2026-08-04: test_reflexion_out_is_constrained_the_same_way. The
# reflexion report it constrained no longer exists -- scripts/architecture_reflexion.py
# went with the static architecture scanners. The constraint itself is unchanged
# and is exercised above through `analyze complexity`, which is the point: the
# refusal lives in resolve_evidence_out, not in each caller.


def test_uv_project_and_extra_dependencies_keep_pytest(tmp_path, monkeypatch):
    target = tmp_path / "specs" / "current"
    (target / "tests").mkdir(parents=True)
    (target / "tests" / "test_example.py").write_text("def test_ok(): pass\n")
    calls = []
    monkeypatch.setenv("TLA_SPEC_DEV_UV_PROJECT", "fallback")
    monkeypatch.setattr(tla_spec_dev.subprocess, "run", lambda cmd, **kw: (
        calls.append((cmd, kw)) or subprocess.CompletedProcess(cmd, 0)))
    parser = tla_spec_dev.build_parser()
    for options, project in [([], "fallback"), (["--uv-project", "ml", "--uv-with", "pyyaml"], "ml")]:
        args = parser.parse_args(["--repo-root", str(tmp_path), "run", "spec-unit-tests", "--scope", "project", *options])
        assert tla_spec_dev.run_spec_unit_tests(args) == 0
        cmd, kwargs = calls[-1]
        assert cmd[cmd.index("--project") + 1] == project
        assert ["--with", "pytest"] == cmd[cmd.index("--with"):cmd.index("--with")+2]
        assert kwargs["cwd"] == tmp_path
    assert "pyyaml" in calls[-1][0]
