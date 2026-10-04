#!/usr/bin/env python3
"""Progressive CLI entrypoint for the spec-double-compiler workflow."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11 fallback
    tomllib = None  # type: ignore[assignment]


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VERSION = "0.1.0"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def skill_version() -> str:
    manifest = ROOT / "skill-manager.toml"
    if tomllib is None or not manifest.exists():
        return DEFAULT_VERSION
    try:
        parsed = tomllib.loads(manifest.read_text(encoding="utf-8"))
    except Exception:
        return DEFAULT_VERSION
    skill = parsed.get("skill")
    if not isinstance(skill, dict):
        return DEFAULT_VERSION
    version = skill.get("version")
    return str(version) if version else DEFAULT_VERSION


class TlaSpecDevParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {message}\n\nRun '{self.prog} --help' to see the next supported workflow step.\n")


def planned_command(args: argparse.Namespace) -> int:
    print(
        f"{args.command_path} is part of the modeled tla-spec-dev workflow, "
        "but its execution is scheduled for a later implementation ticket.",
        file=sys.stderr,
    )
    print(f"spec root: {args.spec_root}", file=sys.stderr)
    print(f"next: {args.next_step}", file=sys.stderr)
    return 2


def incomplete_command(args: argparse.Namespace) -> int:
    print(f"incomplete command: {args.command_path}", file=sys.stderr)
    print(f"spec root: {args.spec_root}", file=sys.stderr)
    print(f"next: {args.next_step}", file=sys.stderr)
    return 2


def run_scaffold_project(args: argparse.Namespace) -> int:
    from scripts import onboard_program_model

    repo_root = Path(args.repo_root).resolve()
    full = bool(getattr(args, "full", False))
    written = onboard_program_model.scaffold(
        repo_root=repo_root,
        name=args.name,
        force=args.force,
        dry_run=args.dry_run,
        spec_root=Path(args.spec_root),
        full=full,
    )
    spec_root = args.spec_root
    print(f"scaffolded program model files: {len(written)}")
    print(
        "\nThese are placeholders: replace the scaffolded state, actions and invariants\n"
        "with this repository's real ones. The baseline is\n"
        f"  - {spec_root}/program_model/Core.tla + Internal.tla + Internal.cfg  -> the model TLC checks\n"
        f"  - {spec_root}/program_model/spec_manifest.yaml                     -> ports, invariants, budgets\n"
        + (
            f"  - {spec_root}/program_model/External.tla + External.cfg          -> Test Graph cases (optional layer)\n"
            f"  - {spec_root}/program_model/adapters.py, providers.py, *.toml/yml  -> generated-case adapters (optional layer)\n"
            if full
            else "Optional later: `scaffold project --full` adds the External view, adapters and providers.\n"
        )
    )
    from scripts.budgets import budget_prompt

    print(budget_prompt(f"{spec_root}/program_model/spec_manifest.yaml"))
    print("next:")
    print("  1. Replace the placeholder semantics with this repository's real behavior.")
    print(f"  2. scripts/run_tlc.sh {spec_root}/program_model/Internal.tla {spec_root}/program_model/Internal.cfg")
    if full:
        print(f"  3. scripts/run_tlc.sh {spec_root}/program_model/External.tla {spec_root}/program_model/External.cfg")
        print(f"  4. tla-spec-dev --spec-root {spec_root} scaffold workflow")
    else:
        print(f"  3. tla-spec-dev --spec-root {spec_root} scaffold workflow")
    return 0


def run_scaffold_workflow(args: argparse.Namespace) -> int:
    from scripts import new_ticket_workflow

    repo_root = Path(args.repo_root).resolve()
    ticket_id = args.ticket_id or "TICKET-001"
    title = args.title or "Initial spec workflow"
    written = new_ticket_workflow.scaffold(
        repo_root=repo_root,
        ticket_id=ticket_id,
        title=title,
        force=args.force,
        dry_run=args.dry_run,
        spec_root=Path(args.spec_root),
    )
    from scripts.budgets import budget_prompt

    print(f"scaffolded ticket workflow files: {len(written)}")
    print(budget_prompt(f"{args.spec_root}/current/spec_manifest.yaml"))
    print(f"next: tla-spec-dev --spec-root {args.spec_root} open ticket {ticket_id}")
    return 0


def run_open_ticket(args: argparse.Namespace) -> int:
    from scripts.new_ticket_workflow import scaffold_ticket_directory

    repo_root = Path(args.repo_root).resolve()
    written = scaffold_ticket_directory(
        repo_root=repo_root,
        ticket_ref=args.ticket_name,
        force=args.force,
        dry_run=args.dry_run,
        spec_root=Path(args.spec_root),
        ticket_root=args.ticket_root,
        print_next_steps=True,
        with_current=bool(getattr(args, "with_current", False)),
    )
    print(f"scaffolded ticket-local workflow files: {len(written)}")
    return 0


def run_analyze_complexity(args: argparse.Namespace) -> int:
    from scripts import analyze_complexity

    return analyze_complexity.run(args)


def run_analyze_corpus(args: argparse.Namespace) -> int:
    from scripts import corpus_diagnostics

    return corpus_diagnostics.run(args)


# REMOVED 2026-08-04 (owner direction): `analyze architecture`, and with it
# scripts/analyze_architecture.py (1,192 lines) and
# scripts/architecture_reflexion.py (2,325). The static architecture scanners
# were ad hoc, and every check they shipped was defeated cheaply: a 41-line
# re-export file erased every divergence, a module that took a collaborator as
# a parameter was reported as dead architecture, and the decomposition rule
# `modularity_q > 0` was met on this very repository only because the scanner's
# OWN two state variables formed the second component. What they measured is
# now written down as instructions rather than executed as a check:
# references/architecture_advice.md. A future scanner may earn this subcommand
# back by satisfying the specification on that page.


def run_generate_cases(args: argparse.Namespace) -> int:
    """RC-01 (MF-026 G-6): case-module generation, reachable from the CLI.

    The flagship feature of the architectural-coherence epic had no CLI
    subcommand, no model action and no declared port. `scripts/case_modules.py`
    and `scripts/generate_cases_from_tlc_dump.py` were reachable only by running
    the files directly, so an import-closure walk of `build_parser` never saw
    them -- which is why CM-01 and RP-03 could both close "zero model delta"
    against surface the model does not contain, and why all four oracles
    reported green over it. Every oracle in this toolchain is bounded to what is
    already modeled; unmodeled surface is never generated into a case, never
    adapted and never mutated.

    The modeled action is `GenerateCases` (TlaSpecDevCli.tla), declaring
    `corpus_process` (the java/TLC spawn), `spec_tree` (the generated package,
    the per-action coverage record, and the parameter-recovery audit) and
    `spec_tree_delete` (the TLC metadir `rmtree`).
    """
    from scripts import generate_cases_from_tlc_dump

    return generate_cases_from_tlc_dump.run(args)


def run_effect_conformance_cmd(args: argparse.Namespace) -> int:
    """MF-013: report the declared-vs-observed effect diff.

    Exits nonzero on any finding. A gap and dead model surface are both
    failures -- the report is written either way, because recording a finding
    is evidence, never a substitute for failing on it.
    """
    from scripts import effect_conformance_report

    return effect_conformance_report.run(args)


# CA-04 removed `run kill-test` (oracle 4, MF-016). It seeded one fault per
# declared port and one per model invariant and gated the resulting kill rate
# against `kill_rate_floor` -- the last hard static gate in this repository.
# The finding is `RM-03-DF-05`, which identified this exact cut, declined it as
# a model delta its own ticket forbade, and asked for "its own ticket against
# the CLI model". The standing evidence for the lever is "static gates catch
# nothing -- seven epics, zero bugs caught by a static check".
#
# The catalogue parser and the suppression scanner survive in
# `scripts/kill_test.py` because the A/B evaluation instruments import them.


def run_close_ticket(args: argparse.Namespace) -> int:
    from scripts.spec_evolution import create_ticket_history_entry, print_commit_recommendation

    result = create_ticket_history_entry(
        repo_root=Path(args.repo_root).resolve(),
        spec_root=Path(args.spec_root),
        ticket_ref=args.ticket_name,
        summary=args.summary,
        result_paths=args.result,
        workflow=args.workflow_name,
        entry_name=args.entry_name,
        allow_open=args.allow_open,
        ticket_root=args.ticket_root,
        promote_current=not args.no_promote_current,
        accept_new=args.accept_new,
        force=args.force,
    )
    print_commit_recommendation(result)
    return 0


def run_retire_ticket(args: argparse.Namespace) -> int:
    from scripts.spec_evolution import (
        create_ticket_retirement_entry,
        print_commit_recommendation,
    )

    result = create_ticket_retirement_entry(
        repo_root=Path(args.repo_root).resolve(),
        spec_root=Path(args.spec_root),
        ticket_ref=args.ticket_name,
        workflow=args.workflow_name,
        ticket_root=args.ticket_root,
        force=args.force,
    )
    print_commit_recommendation(result)
    return 0


def resolved_spec_root(repo_root: Path, spec_root: str) -> Path:
    path = Path(spec_root)
    return path if path.is_absolute() else repo_root / path


def active_ticket_id(specs_dir: Path) -> str | None:
    from scripts.extract_spec_manifest import load_manifest

    plan_path = specs_dir / "desired_program_model" / "ticket_plan.yaml"
    if not plan_path.exists():
        return None
    plan = load_manifest(plan_path)
    status = plan.get("status")
    if isinstance(status, dict) and status.get("active_ticket"):
        return str(status["active_ticket"])
    return None


def project_spec_dir(specs_dir: Path) -> Path:
    """`current` while a workflow is open, `program_model` once it closes.

    `close_tickets.py` REMOVES `specs/current` at workflow close -- that is the
    documented end of the desired/current loop, not an accident -- so a resolver
    that names `current` unconditionally works only between a workflow opening
    and closing, and reports `ERROR: spec-unit target does not exist` on every
    repository sitting between epics. `new_ticket_workflow.project_current_source`
    has had this fallback for as long as the close has removed the directory;
    the two resolvers below did not, and closing an epic took the CLI's own
    `run spec-unit-tests` and `run effect-conformance` down with it.
    """
    current = specs_dir / "current"
    return current if current.exists() else specs_dir / "program_model"


def spec_unit_target_dirs(args: argparse.Namespace, specs_dir: Path) -> list[Path]:
    project_current = project_spec_dir(specs_dir)
    if args.target is not None:
        target = Path(args.target)
        return [target if target.is_absolute() else (Path(args.repo_root).resolve() / target)]
    if args.scope == "project":
        return [project_current]
    if args.ticket:
        return unique_paths([project_current, ticket_model_dir(specs_dir / "tickets" / args.ticket)])
    ticket_id = active_ticket_id(specs_dir)
    if ticket_id:
        ticket_model = ticket_model_dir(specs_dir / "tickets" / ticket_id)
        if ticket_model.exists():
            return unique_paths([project_current, ticket_model])
    return [project_current]


def ticket_model_dir(ticket_dir: Path) -> Path:
    """The ticket's executable model: `current/` when the ticket was opened
    with --with-current, otherwise `desired/` (the default since 2026-09-14)."""
    current = ticket_dir / "current"
    return current if current.exists() else ticket_dir / "desired"


def unique_paths(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(path)
    return unique


def has_pytest_tests(path: Path) -> bool:
    return path.exists() and any(path.rglob("test_*.py"))


def spec_unit_cases_dirs(args: argparse.Namespace, specs_dir: Path) -> list[Path]:
    if args.cases_dir:
        return [Path(value) for value in args.cases_dir]
    discovered: list[Path] = []
    for root in [
        specs_dir / "generated" / "spec-unit",
        specs_dir / "generated" / "spec_unit",
    ]:
        if not root.exists():
            continue
        discovered.extend(sorted(path for path in root.iterdir() if (path / "cases.py").is_file()))
    return discovered


def run_spec_unit_tests(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    specs_dir = resolved_spec_root(repo_root, args.spec_root).resolve()
    target_dirs = [target.resolve() for target in spec_unit_target_dirs(args, specs_dir)]
    missing_targets = [target for target in target_dirs if not target.exists()]
    if missing_targets:
        print(f"ERROR: spec-unit target does not exist: {missing_targets[0]}", file=sys.stderr)
        return 2

    base_env = os.environ.copy()

    def command_env(target_dir: Path) -> dict[str, str]:
        env = base_env.copy()
        # ROOT carries spec_double_compiler, which the scaffolded adapters.py
        # imports (CaseRunResult). Without it, pytest collection of a spec dir in
        # a user repo dies on ModuleNotFoundError before running a single test.
        python_path = [str(target_dir), str(repo_root), str(ROOT), env.get("PYTHONPATH", "")]
        env["PYTHONPATH"] = os.pathsep.join(part for part in python_path if part)
        return env

    # A spec dir in a user repo is usually NOT importable from a bare
    # interpreter: its adapters import the repository's own package, which lives
    # in that repo's uv project (`ml/` here, not the repo root). The historical
    # command was a fixed `uv run --with pytest`, with no project and no knob, so
    # every such repo hit ModuleNotFoundError and worked around it per-invocation
    # with ad-hoc PYTHONPATH and UV_PYTHON. Name the project instead. Default is
    # unchanged, so this is additive.
    uv_project = getattr(args, "uv_project", None) or base_env.get("TLA_SPEC_DEV_UV_PROJECT") or ""
    uv_project_args = ["--project", uv_project] if uv_project else []
    uv_with_args: list[str] = []
    for dependency in getattr(args, "uv_with", None) or ["pytest"]:
        uv_with_args.extend(["--with", dependency])

    cases_dirs = spec_unit_cases_dirs(args, specs_dir)
    commands: list[tuple[str, list[str], dict[str, str]]] = []
    empty_targets: list[Path] = []
    for target_dir in target_dirs:
        target_command_count = 0
        tests_dir = Path(args.tests_dir) if args.tests_dir else target_dir / "tests"
        if not tests_dir.is_absolute():
            tests_dir = target_dir / tests_dir
        if has_pytest_tests(tests_dir):
            target_command_count += 1
            commands.append(
                (
                    f"pytest:{target_dir}",
                    [
                        "uv",
                        "run",
                        *uv_project_args,
                        *uv_with_args,
                        "-m",
                        "pytest",
                        str(tests_dir),
                        *args.pytest_arg,
                    ],
                    command_env(target_dir),
                )
            )

        mapping = Path(args.mapping) if args.mapping else target_dir / "case_adapters.toml"
        for cases_dir in cases_dirs:
            target_command_count += 1
            command = [
                sys.executable,
                str(ROOT / "scripts" / "run_generated_case_adapters.py"),
                str(cases_dir),
                "--mapping",
                str(mapping),
                "--spec-dir",
                str(target_dir),
                "--view",
                "internal",
                "--import-root",
                str(target_dir),
            ]
            for label in args.label:
                command.extend(["--label", label])
            for case_name in args.case:
                command.extend(["--case", case_name])
            if args.limit is not None:
                command.extend(["--limit", str(args.limit)])
            if args.work_dir is not None:
                command.extend(["--work-dir", str(args.work_dir)])
            if args.validate_only:
                command.append("--validate-only")
            if args.validate_capabilities:
                command.append("--validate-capabilities")
            # CA-06-DF-03: `--no-batch` selected the per-case-program execution
            # mode, which CA-06 deleted. Both sides of this branch now produce
            # the same behaviour -- `--batch` is accepted and inert -- so the
            # flag is a NO-OP rather than a choice. The branch is KEPT so the
            # emitted command line still matches the sealed reproduction
            # commands that captured it, and the flag is tombstoned in its help
            # rather than removed, because removing it would break every caller
            # that passes it. An untombstoned silent no-op is exactly the
            # CA-04-DF-06 interface class, and a reviewer of PR #268 caught it.
            if not args.no_batch:
                command.append("--batch")
            command.extend(
                [
                    "--fuzz-runs",
                    str(getattr(args, "fuzz_runs", 1)),
                    "--seed",
                    str(getattr(args, "seed", 0)),
                ]
            )
            fuzz_iteration = getattr(args, "fuzz_iteration", None)
            if fuzz_iteration is not None:
                command.extend(["--fuzz-iteration", str(fuzz_iteration)])
            commands.append((f"case-adapters:{target_dir}:{cases_dir.name}", command, command_env(target_dir)))
        if target_command_count == 0:
            empty_targets.append(target_dir)

    if empty_targets:
        for target_dir in empty_targets:
            print(f"ERROR: no spec-unit pytest tests or generated case packages found for {target_dir}", file=sys.stderr)
        return 2

    if not commands:
        targets = ", ".join(str(target) for target in target_dirs)
        print(f"ERROR: no spec-unit pytest tests or generated case packages found for {targets}", file=sys.stderr)
        return 2

    print(f"spec root: {specs_dir}")
    for target_dir in target_dirs:
        print(f"spec-unit target: {target_dir}")
    for label, command, env in commands:
        print(f"running {label}: {' '.join(command)}")
        result = subprocess.run(command, cwd=repo_root, env=env)
        if result.returncode != 0:
            return result.returncode
    print(f"spec-unit validation passed for {len(target_dirs)} target(s)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = TlaSpecDevParser(
        prog="tla-spec-dev",
        description="Work with a spec-double-compiler project through the modeled spec workflow.",
        epilog=(
            "Typical order: scaffold project -> scaffold workflow -> open ticket -> "
            "analyze complexity -> run spec-unit-tests -> close ticket. When the owner "
            "withdraws a dispatched ticket, record that separately with retire ticket."
        ),
        allow_abbrev=False,
    )
    parser.add_argument(
        "--spec-root",
        default="specs",
        help="Spec root under the repository. Defaults to %(default)s.",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root. Defaults to the current directory.",
    )
    parser.add_argument("--version", action="version", version=f"tla-spec-dev {skill_version()}")

    subparsers = parser.add_subparsers(dest="command", metavar="command")

    scaffold = subparsers.add_parser(
        "scaffold",
        help="Create spec workflow directories.",
        description="Create the modeled spec-double-compiler project or ticket workflow directories.",
        allow_abbrev=False,
    )
    scaffold.set_defaults(
        func=incomplete_command,
        command_path="tla-spec-dev scaffold",
        next_step="Choose a target: tla-spec-dev scaffold project or tla-spec-dev scaffold workflow.",
    )
    scaffold_sub = scaffold.add_subparsers(dest="scaffold_target", metavar="target")
    scaffold_project = scaffold_sub.add_parser(
        "project",
        help="Create the accepted program_model baseline.",
        description="Create specs/program_model as the accepted whole-program semantic baseline.",
        allow_abbrev=False,
    )
    scaffold_project.add_argument("--name", help="Program/module name. Defaults to the repository directory name.")
    scaffold_project.add_argument("--force", action="store_true", help="Overwrite existing program-model files.")
    scaffold_project.add_argument("--dry-run", action="store_true", help="Print planned writes without changing files.")
    scaffold_project.add_argument(
        "--full",
        action="store_true",
        help="Also emit the optional layer: External view, generated-case adapters, effect providers, Test Graph bindings, TLC projection.",
    )
    scaffold_project.set_defaults(
        func=run_scaffold_project,
        command_path="tla-spec-dev scaffold project",
        next_step="tla-spec-dev scaffold workflow",
    )
    scaffold_workflow = scaffold_sub.add_parser(
        "workflow",
        help="Create current and desired workflow directories.",
        description="Create specs/current and specs/desired_program_model from an accepted baseline.",
        allow_abbrev=False,
    )
    scaffold_workflow.add_argument("ticket_id", nargs="?", help="Initial ticket id. Defaults to TICKET-001.")
    scaffold_workflow.add_argument("title", nargs="?", help="Initial ticket title. Defaults to 'Initial spec workflow'.")
    scaffold_workflow.add_argument("--force", action="store_true", help="Overwrite existing workflow files.")
    scaffold_workflow.add_argument("--dry-run", action="store_true", help="Print planned writes without changing files.")
    scaffold_workflow.set_defaults(
        func=run_scaffold_workflow,
        command_path="tla-spec-dev scaffold workflow",
        next_step="tla-spec-dev open ticket <ticket>",
    )

    open_parser = subparsers.add_parser(
        "open",
        help="Open a ticket-local spec workflow.",
        description="Open a ticket workspace with ticket-local current, desired, results, and Test Graph files.",
        allow_abbrev=False,
    )
    open_parser.set_defaults(
        func=incomplete_command,
        command_path="tla-spec-dev open",
        next_step="Choose a target: tla-spec-dev open ticket <ticket-name>.",
    )
    open_sub = open_parser.add_subparsers(dest="open_target", metavar="target")
    open_ticket = open_sub.add_parser(
        "ticket",
        help="Open a ticket by id or name.",
        description="Open a ticket and print desired-first implementation instructions.",
        allow_abbrev=False,
    )
    open_ticket.add_argument("ticket_name", help="Ticket id from desired_program_model/ticket_plan.yaml.")
    open_ticket.add_argument("--ticket-root", type=Path, default=Path("tickets"), help="Ticket directory root, relative to spec root by default.")
    open_ticket.add_argument("--force", action="store_true", help="Overwrite existing ticket-local files, and reopen a ticket the plan already marks terminal (SKILL_GATES=off also allows the reopen).")
    open_ticket.add_argument("--dry-run", action="store_true", help="Print planned writes without changing files.")
    open_ticket.add_argument(
        "--with-current",
        action="store_true",
        help="Also seed a ticket-local current/ (the older two-directory loop). Default: desired/ only.",
    )
    open_ticket.set_defaults(
        func=run_open_ticket,
        command_path="tla-spec-dev open ticket",
        next_step="Edit ticket desired first, then update current to match.",
    )

    run_parser = subparsers.add_parser(
        "run",
        help="Run spec workflow validations.",
        description="Run generated or adapter-backed validations from the selected spec root.",
        allow_abbrev=False,
    )
    run_parser.set_defaults(
        func=incomplete_command,
        command_path="tla-spec-dev run",
        next_step="Choose a target: tla-spec-dev run spec-unit-tests.",
    )
    run_sub = run_parser.add_subparsers(dest="run_target", metavar="target")
    run_spec_units = run_sub.add_parser(
        "spec-unit-tests",
        help="Run generated spec-unit adapter tests.",
        description="Run generated/adapted spec-unit tests for the selected spec root.",
        allow_abbrev=False,
    )
    run_spec_units.add_argument("--ticket", help="Run ticket-local current spec-unit tests for this ticket.")
    run_spec_units.add_argument(
        "--scope",
        choices=["auto", "project"],
        default="auto",
        help="Target active ticket current/ when present, otherwise project current/. Use project to force specs/current.",
    )
    run_spec_units.add_argument("--target", type=Path, help="Explicit spec directory to validate.")
    run_spec_units.add_argument("--tests-dir", type=Path, help="Test directory relative to the selected spec directory.")
    run_spec_units.add_argument("--cases-dir", action="append", help="Generated spec-unit case package directory.")
    run_spec_units.add_argument("--mapping", type=Path, help="Adapter mapping TOML/YAML. Defaults to target case_adapters.toml.")
    run_spec_units.add_argument("--work-dir", type=Path, help="Work directory for generated case adapter execution.")
    run_spec_units.add_argument("--label", action="append", default=[], help="Only run generated cases with this label.")
    run_spec_units.add_argument("--case", action="append", default=[], help="Only run this generated case name.")
    run_spec_units.add_argument("--limit", type=int, help="Limit generated cases.")
    run_spec_units.add_argument("--validate-only", action="store_true", help="Validate adapter coverage without executing generated cases.")
    run_spec_units.add_argument("--validate-capabilities", action="store_true", help="Ask adapters whether they can run selected cases.")
    run_spec_units.add_argument(
        "--no-batch",
        action="store_true",
        help=(
            "ACCEPTED AND INERT (CA-06-DF-03). It used to select one Python "
            "program per case instead of batched hooks; CA-06 deleted that mode "
            "after finding it carried fewer oracles than the one nothing chose "
            "against it. Batch is now the only mode, so this flag selects "
            "nothing. Kept accepted rather than removed so callers that pass it "
            "keep working."
        ),
    )
    run_spec_units.add_argument(
        "--fuzz-runs",
        type=int,
        default=1,
        help="Run each selected provider-bearing case this many deterministic iterations.",
    )
    run_spec_units.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Root seed for deterministic per-effect representative generation.",
    )
    run_spec_units.add_argument(
        "--fuzz-iteration",
        type=int,
        help="Replay exactly this deterministic effect-provider iteration.",
    )
    run_spec_units.add_argument(
        "--uv-project",
        help=(
            "Directory of the uv project whose environment the spec tests need, "
            "passed through as `uv run --project DIR`. Falls back to "
            "$TLA_SPEC_DEV_UV_PROJECT. Omit for the historical bare `uv run`, "
            "which cannot import a repository package that lives in a project "
            "subdirectory."
        ),
    )
    run_spec_units.add_argument(
        "--uv-with",
        action="append",
        help=(
            "Dependency for `uv run --with`. May be repeated. Defaults to "
            "pytest alone; pass it again when a repo's spec tests also need, "
            "for example, pyyaml."
        ),
    )
    run_spec_units.add_argument(
        "--pytest-arg",
        action="append",
        default=["-q"],
        help="Argument passed to pytest. May be repeated. Defaults to -q.",
    )
    run_spec_units.set_defaults(
        func=run_spec_unit_tests,
        command_path="tla-spec-dev run spec-unit-tests",
        next_step="tla-spec-dev close ticket <ticket>",
    )

    run_effects = run_sub.add_parser(
        "effect-conformance",
        help="Diff observed adapter side effects against declared effect ports.",
        description=(
            "Execute component adapters in a sandbox (temp dirs, fake transports, recorded "
            "boundaries), collect the side effects that actually crossed a boundary, and diff "
            "them against the ports declared in actions.yml / spec_manifest.yaml. "
            "An observed effect with no declared port is a GAP; a declared port no case "
            "exercises is DEAD MODEL SURFACE. Both are recorded AND fail the command. "
            "Nothing suppresses a gap report -- there is no justification, waiver, or "
            "override flag, and out-of-contract justifications were withdrawn 2026-07-18."
        ),
        allow_abbrev=False,
    )
    run_effects.add_argument("--ticket", help="Use this ticket's current/ spec directory.")
    run_effects.add_argument("--target", type=Path, help="Explicit spec directory carrying the effect declarations.")
    run_effects.add_argument("--cases-dir", action="append", help="Generated spec-unit case package directory.")
    run_effects.add_argument("--mapping", type=Path, help="Adapter mapping TOML/YAML. Defaults to target case_adapters.toml.")
    run_effects.add_argument("--work-dir", type=Path, help="Work directory for sandboxed adapter execution.")
    run_effects.add_argument("--out", type=Path, help="Write the JSON diff report here (ticket results/ evidence).")
    run_effects.add_argument("--format", choices=["text", "json"], default="text", help="Output format.")
    run_effects.set_defaults(
        func=run_effect_conformance_cmd,
        command_path="tla-spec-dev run effect-conformance",
        next_step="tla-spec-dev run spec-unit-tests --ticket <ticket>",
    )

    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analyze model complexity against the budgets.",
        description="Analyze a spec + cfg for state-space complexity and gate it against manifest budgets.",
        allow_abbrev=False,
    )
    analyze_parser.set_defaults(
        func=incomplete_command,
        command_path="tla-spec-dev analyze",
        next_step=(
            "Choose a target: tla-spec-dev analyze complexity <spec.tla> [<cfg>], "
            "or tla-spec-dev analyze corpus <cases-dir>."
        ),
    )
    analyze_sub = analyze_parser.add_subparsers(dest="analyze_target", metavar="target")
    analyze_complexity_parser = analyze_sub.add_parser(
        "complexity",
        help="Print the complexity descriptor: dimension table, bound, R/W matrix, modularity.",
        description=(
            "Print the complexity DESCRIPTOR: the per-variable domain cardinality table, the "
            "state-space upper bound (or an explicit unknown), the variables x actions "
            "read/write matrix, the graph-modularity score with near-decomposable clusters and "
            "candidate port-crossing actions, dense rows/columns (god-state detection), "
            "variables no configured invariant reads, and unjustified variables. Facts, not "
            "judgment: it makes no suggestions, is advisory, and exits nonzero only when the "
            "model cannot be analyzed at all."
        ),
        allow_abbrev=False,
    )
    from scripts.analyze_complexity import add_arguments as _add_analyze_arguments

    _add_analyze_arguments(analyze_complexity_parser)
    analyze_complexity_parser.set_defaults(
        func=run_analyze_complexity,
        command_path="tla-spec-dev analyze complexity",
        next_step="Record the report under the ticket results/ directory as evidence.",
    )

    analyze_corpus_parser = analyze_sub.add_parser(
        "corpus",
        help="Print the case distribution and gate it against the case caps.",
        description=(
            "Print the generated corpus distribution per (action, label class), which "
            "strata dominate, which are starved, and what varies across any redundant "
            "group -- the measured cause of the redundancy. Exits nonzero when a "
            "component or action exceeds its manifest case cap "
            "(max_internal_cases_per_component / max_external_cases_per_action). "
            "NOTHING IS EVER DROPPED, FILTERED, SAMPLED, OR TRUNCATED to fit a cap: "
            "over budget the gate reports and refuses. It prescribes no move; the "
            "failure output states the finding and ends with a REDESIGN QUESTION -- "
            "can the architecture be redesigned to make the program simpler, judged "
            "with the complexity descriptor (analyze complexity) and "
            "references/complexity_intuition.md -- and the two ways forward are that "
            "redesign or raising the cap with a recorded rationale."
        ),
        allow_abbrev=False,
    )
    from scripts.corpus_diagnostics import add_arguments as _add_corpus_arguments

    _add_corpus_arguments(analyze_corpus_parser)
    analyze_corpus_parser.set_defaults(
        func=run_analyze_corpus,
        command_path="tla-spec-dev analyze corpus",
        next_step="Consider whether the architecture can be redesigned to make the program simpler (analyze complexity + references/complexity_intuition.md), or raise the cap with a recorded rationale.",
    )

    # RC-01 (MF-026 G-6): case generation joins the shipped command surface.
    # It was always shipped -- references/case_modules.md documents it and the
    # epic's own tickets ran it -- but only by invoking the script file, which
    # is why `build_parser`'s import closure never reached it and the model
    # never represented it.
    generate_parser = subparsers.add_parser(
        "generate",
        help="Generate spec-unit case packages from a TLC state graph.",
        description="Generate the case corpus a view (or a case module) implies.",
        allow_abbrev=False,
    )
    generate_parser.set_defaults(
        func=incomplete_command,
        command_path="tla-spec-dev generate",
        next_step="Choose a target: tla-spec-dev generate cases <spec.tla> <cfg> --out <dir>.",
    )
    generate_sub = generate_parser.add_subparsers(dest="generate_target", metavar="target")
    generate_cases_parser = generate_sub.add_parser(
        "cases",
        help="Generate a view-aware spec-unit case package from a TLC dump.",
        description=(
            "Explore the module with TLC, dump the reachable state graph, and render one "
            "case per action-labeled edge into a generated Python package. When the "
            "module is declared in the manifest's `case_modules:` block, the per-action "
            "coverage report is scoped to the aspect that module enters, so the actions "
            "the slice deliberately does not enter are NOT reported as coverage holes. "
            "The corpus is never trimmed to fit a budget: the complete package is "
            "written first and the case caps are measured over it afterwards "
            "(max_internal_cases_per_component / max_external_cases_per_action), so "
            "over cap the command reports the distribution and exits nonzero with every "
            "generated case still on disk."
        ),
        allow_abbrev=False,
    )
    from scripts.generate_cases_from_tlc_dump import add_arguments as _add_generate_arguments

    _add_generate_arguments(generate_cases_parser)
    generate_cases_parser.set_defaults(
        func=run_generate_cases,
        command_path="tla-spec-dev generate cases",
        next_step="tla-spec-dev analyze corpus <cases-dir>",
    )

    retire_parser = subparsers.add_parser(
        "retire",
        help="Record an owner decision to withdraw a dispatched ticket.",
        description=(
            "Write an append-only ticket-retirement receipt without promoting ticket "
            "desired/current state or claiming validation. The plan entry must already "
            "be marked status: retired and contain the complete retirement decision."
        ),
        allow_abbrev=False,
    )
    retire_parser.set_defaults(
        func=incomplete_command,
        command_path="tla-spec-dev retire",
        next_step="Choose a target: tla-spec-dev retire ticket <ticket-name>.",
    )
    retire_sub = retire_parser.add_subparsers(dest="retire_target", metavar="target")
    retire_ticket = retire_sub.add_parser(
        "ticket",
        help="Write the canonical no-promotion retirement receipt for one ticket.",
        description=(
            "Validate status: retired plus its owner decision, archive any active ticket "
            "workspace as unaccepted work, and write the canonical append-only receipt. "
            "This is not close ticket: it runs no validation or complexity ledger and "
            "promotes no semantic state."
        ),
        allow_abbrev=False,
    )
    retire_ticket.add_argument(
        "ticket_name", help="Ticket id from desired_program_model/ticket_plan.yaml."
    )
    retire_ticket.add_argument(
        "--workflow-name",
        help="Override ticket_plan.yaml name/status.workflow for the history directory.",
    )
    retire_ticket.add_argument(
        "--ticket-root",
        type=Path,
        default=Path("tickets"),
        help="Ticket directory root, relative to spec root by default.",
    )
    retire_ticket.add_argument(
        "--force",
        action="store_true",
        help="Warn instead of refusing on retirement-declaration and prior-receipt gates. SKILL_GATES=off means the same.",
    )
    retire_ticket.set_defaults(
        func=run_retire_ticket,
        command_path="tla-spec-dev retire ticket",
        next_step="Commit the unchanged plan entry and its append-only retirement receipt together.",
    )

    close_parser = subparsers.add_parser(
        "close",
        # E-03 (#311): this said "Close ticket or workflow history." `close`
        # accepts only `ticket`; workflow-history close is scripts/close_tickets.py,
        # run from references/workflows.md step 5. An agent read the help as a map,
        # looked for `close workflow`, and got an argparse error -- the help was
        # describing a real step that lives somewhere the CLI does not point to.
        help="Close a ticket. (Workflow history: scripts/close_tickets.py.)",
        description="Close a ticket once current equals desired and validations pass.",
        allow_abbrev=False,
    )
    close_parser.set_defaults(
        func=incomplete_command,
        command_path="tla-spec-dev close",
        next_step=(
            "Choose a target: tla-spec-dev close ticket <ticket-name>. "
            "To close WORKFLOW history, run scripts/close_tickets.py -- it is not "
            "a `close` target (references/workflows.md step 5)."
        ),
    )
    close_sub = close_parser.add_subparsers(dest="close_target", metavar="target")
    close_ticket = close_sub.add_parser(
        "ticket",
        help="Close a ticket by id or name.",
        description="Close a ticket, write append-only history, and promote ticket desired into project current.",
        allow_abbrev=False,
    )
    close_ticket.add_argument("ticket_name", help="Ticket id from desired_program_model/ticket_plan.yaml.")
    close_ticket.add_argument("--workflow-name", help="Override ticket_plan.yaml name/status.workflow for the history directory.")
    close_ticket.add_argument("--entry-name", help="Override the default ticket-NNN-id history entry name.")
    close_ticket.add_argument("--summary", default="", help="Human-readable summary of the ticket-specific change.")
    close_ticket.add_argument("--result", action="append", type=Path, default=[], help="TLC, generated-case, adapter, or test result path to snapshot.")
    close_ticket.add_argument("--allow-open", action="store_true", help="Allow snapshotting a ticket whose status is not closed/done.")
    close_ticket.add_argument("--ticket-root", type=Path, default=Path("tickets"), help="Ticket directory root, relative to spec root by default.")
    close_ticket.add_argument("--no-promote-current", action="store_true", help="Do not replace project current/ with ticket desired/ during ticket close.")
    close_ticket.add_argument(
        "--accept-new",
        action="store_true",
        help="Accept the ticket desired/ as the new current/: skip the current==desired check and overwrite current/ from desired/ before promotion.",
    )
    close_ticket.add_argument(
        "--force",
        action="store_true",
        help="Warn instead of refusing on status, receipt, and convergence gates; a divergent ticket is accepted as with --accept-new. SKILL_GATES=off means the same. Recorded in the receipt.",
    )
    close_ticket.set_defaults(
        func=run_close_ticket,
        command_path="tla-spec-dev close ticket",
        next_step="Open the next ticket or close the workflow.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "func", None)
    if handler is None:
        parser.print_help()
        return 0
    return int(handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
