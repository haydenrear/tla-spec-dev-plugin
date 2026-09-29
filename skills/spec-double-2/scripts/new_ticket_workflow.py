#!/usr/bin/env python3
"""Scaffold a model-backed ticket workflow in a repository.

The workflow is intentionally general. It is for any ticket or behavior change
where the repository should keep a formal desired state, executable current
state, adapters, and validation evidence in sync.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
# Importable both as `scripts.new_ticket_workflow` and as a direct script, where
# sys.path[0] is scripts/ rather than the repository root.
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from scripts.budgets import budgets_block
from scripts.onboard_program_model import missing_baseline_files
from scripts import complexity_ledger

TICKET_COPY_IGNORE = {
    ".DS_Store",
    "__pycache__",
    ".history",
    ".tla-spec-evolution",
    ".gradle",
    ".pytest_cache",
    "build",
}
PROJECT_WORKFLOW_TEST = "tests/test_current_ticket_workflow.py"
PROGRAM_MODEL_ONBOARDING_TEST = "tests/test_program_model_onboarding.py"


def _load_manifest(path: Path) -> dict[str, Any]:
    import sys

    skill_root = str(SKILL_ROOT)
    if skill_root not in sys.path:
        sys.path.insert(0, skill_root)
    from scripts.extract_spec_manifest import load_manifest

    if not path.exists():
        return {}
    try:
        return load_manifest(path)
    except ValueError as error:
        raise SystemExit(f"ERROR: {path}: {error}") from error


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return normalized or "ticket"


def _title(value: str) -> str:
    return " ".join(part.capitalize() for part in re.split(r"[-_\s]+", value) if part)


def _module_name(value: str) -> str:
    candidate = "".join(part.capitalize() for part in re.split(r"[^a-zA-Z0-9]+", value) if part)
    if not candidate:
        return "ProgramModel"
    if candidate[0].isdigit():
        return f"Program{candidate}"
    return candidate


def _safe_segment(value: str) -> str:
    rendered = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip(".-")
    if not rendered:
        raise SystemExit("ticket ids must contain at least one safe path character")
    return rendered


@dataclass(frozen=True)
class Baseline:
    module: str
    package: str
    repo_root: Path
    spec_root: Path
    program_dir: Path
    tla_path: Path | None
    cfg_path: Path | None
    manifest_path: Path | None
    # "three_module" is the accepted shape: Core/Internal/External plus adapter
    # mappings for both views. "legacy_single_module" is a pre-Internal/External
    # baseline that cannot generate Test Graph cases.
    layout: str = "three_module"

    @property
    def is_legacy_single_module(self) -> bool:
        return self.layout == "legacy_single_module"


def _resolve_spec_root(repo_root: Path, spec_root: Path) -> Path:
    return spec_root if spec_root.is_absolute() else repo_root / spec_root


def _display_spec_root(repo_root: Path, spec_root: Path) -> str:
    if spec_root.is_absolute():
        try:
            return spec_root.relative_to(repo_root).as_posix()
        except ValueError:
            return spec_root.as_posix()
    return spec_root.as_posix()


def discover_baseline(repo_root: Path, spec_root: Path, fallback_module: str) -> Baseline:
    resolved_spec_root = _resolve_spec_root(repo_root, spec_root)
    program_dir = resolved_spec_root / "program_model"
    manifest_path = program_dir / "spec_manifest.yaml"
    manifest = _load_manifest(manifest_path)
    module = str(manifest.get("module") or fallback_module)
    package = str(manifest.get("package") or f"{_slug(module).replace('-', '_')}_cases")

    # Accepted shape: Core.tla + Internal.tla/.cfg + External.tla/.cfg. Internal
    # is the module-level entry point; the whole program_model tree is copied
    # into ticket dirs, so no single module stands in for the baseline.
    internal_tla = program_dir / "Internal.tla"
    internal_cfg = program_dir / "Internal.cfg"
    if internal_tla.exists():
        baseline = Baseline(
            module=module,
            package=package,
            repo_root=repo_root,
            spec_root=resolved_spec_root,
            program_dir=program_dir,
            tla_path=internal_tla,
            cfg_path=internal_cfg if internal_cfg.exists() else None,
            manifest_path=manifest_path if manifest_path.exists() else None,
            layout="three_module",
        )
        # Advisory, never a refusal (2026-09-14). This used to raise SystemExit
        # on a baseline missing any of thirteen files, and neither --force nor
        # SKILL_GATES=off got past it -- it refused on the skill's own
        # examples/distributed_history. An agent told "the model is incomplete"
        # stops; the workflow scaffold copies whatever the baseline has.
        missing = missing_baseline_files(program_dir)
        if missing:
            details = "\n".join(f"  - {program_dir / name}" for name in missing)
            print(
                "WARNING: the accepted program model is missing baseline files; "
                "scaffolding the workflow from what is there:\n" + details,
                file=sys.stderr,
            )
        return baseline

    # Legacy: a pre-Internal/External baseline built from a single module.
    tla_path = program_dir / f"{module}.tla"
    if not tla_path.exists():
        candidates = sorted(program_dir.glob("*.tla"))
        tla_path = candidates[0] if candidates else None
        if tla_path is not None:
            match = re.search(r"(?m)^\s*-+\s*MODULE\s+([A-Za-z][A-Za-z0-9_]*)\s*-+", tla_path.read_text())
            if match:
                module = match.group(1)
    cfg_path = program_dir / "MC.cfg"
    baseline = Baseline(
        module=module,
        package=package,
        repo_root=repo_root,
        spec_root=resolved_spec_root,
        program_dir=program_dir,
        tla_path=tla_path if tla_path and tla_path.exists() else None,
        cfg_path=cfg_path if cfg_path.exists() else None,
        manifest_path=manifest_path if manifest_path.exists() else None,
        layout="legacy_single_module",
    )
    missing = []
    if baseline.manifest_path is None:
        missing.append(manifest_path)
    if baseline.tla_path is None:
        missing.append(program_dir / f"{module}.tla")
    if baseline.cfg_path is None:
        missing.append(cfg_path)
    if missing:
        details = "\n".join(f"- {path}" for path in missing)
        raise SystemExit(
            "cannot scaffold ticket workflow without an accepted program model. "
            "Run 'tla-spec-dev scaffold project' first.\nMissing baseline files:\n" + details
        )

    print(
        f"WARNING: {program_dir} is a single-module baseline with no Internal.tla/External.tla.\n"
        "         It cannot generate Test Graph cases, so this project's public surface is\n"
        "         not validated. Split it into Core/Internal/External and add adapters.py +\n"
        "         testgraph_bindings.yml. See references/testgraph_adapters.md.",
        file=sys.stderr,
    )
    return baseline


def write_file(path: Path, content: str, *, force: bool, dry_run: bool) -> bool:
    if path.exists() and not force:
        return False
    if dry_run:
        print(f"would write {path}")
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"wrote {path}")
    return True


def copy_file(src: Path | None, dst: Path, fallback: str, *, force: bool, dry_run: bool) -> bool:
    if dst.exists() and not force:
        return False
    if dry_run:
        action = f"copy {src}" if src else "write fallback"
        print(f"would {action} -> {dst}")
        return True
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src is not None:
        shutil.copyfile(src, dst)
        print(f"copied {src} -> {dst}")
    else:
        dst.write_text(fallback, encoding="utf-8")
        print(f"wrote {dst}")
    return True


MANIFEST_CARRY_ANCHOR = "# Per-program complexity and case budgets"


def carry_manifest_semantic_tail(template_text: str, baseline_manifest: Path) -> str:
    """MR-DF-01: keep the accepted manifest's semantic blocks at scaffold time.

    The workflow scaffold regenerates spec_manifest.yaml from a bare template,
    which silently drops everything the accepted program model negotiated:
    budgets with recorded rationales, the effects/ports declarations, the
    justification table, schema stanzas. The fresh status header still comes
    from the template; everything from the budgets section onward is carried
    verbatim from the accepted manifest when both sides carry the anchor.
    """
    if not baseline_manifest.is_file():
        return template_text
    accepted = baseline_manifest.read_text(encoding="utf-8")
    template_idx = template_text.find(MANIFEST_CARRY_ANCHOR)
    accepted_idx = accepted.find(MANIFEST_CARRY_ANCHOR)
    if template_idx == -1 or accepted_idx == -1:
        return template_text
    return template_text[:template_idx] + accepted[accepted_idx:]


#: A binding map copied into a ticket view must name THAT view's modules.
#:
#: `G-10`: bindings written `specs.program_model.adapters:X` resolve from the
#: project root, so a ticket's copy points back at the accepted baseline and the
#: ticket's own `adapters.py` is never imported -- **a ticket that edits its
#: adapters runs green without executing them.** The scaffold now emits bare
#: names, which resolve against whichever view is selected, but a scaffold fix
#: only reaches NEW projects. The defect lives here, at the copy seam, and every
#: project onboarded before it keeps the hole.
#:
#: `close_tickets.promote_semantic_files` already re-roots on the way OUT. This
#: is the symmetric move on the way IN, and it strips to BARE rather than
#: re-rooting to the ticket's own dotted path, because bare is the form
#: `reroot_module_prefixes` itself calls "the one that cannot rot on promotion".
#:
#: It is loud. A silent rewrite of a file the operator is about to edit is worse
#: than the defect it fixes.
BINDING_MAP_NAMES = {"testgraph_bindings.yml", "case_adapters.toml"}
VIEW_DIR_NAMES = ("current", "desired_program_model", "program_model", "desired")
_VIEW_QUALIFIED_MODULE = re.compile(r"\bspecs\.(?:%s)\." % "|".join(VIEW_DIR_NAMES))


def strip_view_prefixes(text: str) -> tuple[str, int]:
    """`specs.<view>.adapters:X` -> `adapters:X`. Returns the text and the count."""
    moved = len(_VIEW_QUALIFIED_MODULE.findall(text))
    return _VIEW_QUALIFIED_MODULE.sub("", text), moved


def _seed_file(src: Path, dst: Path) -> str:
    """Copy one seeded file, un-rooting a binding map's module references."""
    if src.name not in BINDING_MAP_NAMES:
        shutil.copyfile(src, dst)
        return f"copied {src} -> {dst}"
    text = src.read_text(encoding="utf-8")
    rewritten, moved = strip_view_prefixes(text)
    dst.write_text(rewritten, encoding="utf-8")
    if not moved:
        return f"copied {src} -> {dst}"
    return (
        f"copied {src} -> {dst} (un-rooted {moved} view-qualified module "
        "reference(s) so this view executes its OWN adapters; see G-10)"
    )


def copy_baseline_tree(src_dir: Path, dst_dir: Path, *, force: bool, dry_run: bool) -> list[Path]:
    if not src_dir.exists():
        return []

    copied: list[Path] = []
    for src in sorted(path for path in src_dir.rglob("*") if path.is_file()):
        relative = src.relative_to(src_dir)
        if relative.as_posix() in {"README.md", "spec_manifest.yaml", PROGRAM_MODEL_ONBOARDING_TEST}:
            continue
        dst = dst_dir / relative
        if dst.exists() and not force:
            continue
        if dry_run:
            print(f"would copy {src} -> {dst}")
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            print(_seed_file(src, dst))
        copied.append(dst)
    return copied


def copy_workflow_tree(
    src_dir: Path,
    dst_dir: Path,
    *,
    force: bool,
    dry_run: bool,
    skip_paths: set[str] | None = None,
) -> list[Path]:
    if not src_dir.exists():
        return []

    skipped = skip_paths or set()
    copied: list[Path] = []
    for src in sorted(path for path in src_dir.rglob("*") if path.is_file()):
        relative = src.relative_to(src_dir)
        if any(part in TICKET_COPY_IGNORE for part in relative.parts):
            continue
        if relative.as_posix() in skipped:
            continue
        dst = dst_dir / relative
        if dst.exists() and not force:
            continue
        if dry_run:
            print(f"would copy {src} -> {dst}")
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            print(_seed_file(src, dst))
        copied.append(dst)
    return copied


def workflow_tree_seed_paths(src_dir: Path, skip_paths: set[str] | None = None) -> list[str]:
    """Relative paths ``copy_workflow_tree`` seeds from ``src_dir``.

    This is the logical seeded set, independent of which files a resumed
    scaffold actually rewrote, so it stays stable across ``--force`` and
    re-runs. Promotion reads it back to tell a path the ticket deliberately
    deleted from a path the ticket was never given.
    """
    if not src_dir.exists():
        return []
    skipped = skip_paths or set()
    seeded: list[str] = []
    for src in sorted(path for path in src_dir.rglob("*") if path.is_file()):
        relative = src.relative_to(src_dir)
        if any(part in TICKET_COPY_IGNORE for part in relative.parts):
            continue
        posix = relative.as_posix()
        if posix in skipped:
            continue
        seeded.append(posix)
    return seeded


def copy_optional_tree(src_dir: Path, dst_dir: Path, *, force: bool, dry_run: bool) -> list[Path]:
    if not src_dir.exists():
        return []
    return copy_workflow_tree(src_dir, dst_dir, force=force, dry_run=dry_run)


def ticket_plan_path(specs_dir: Path) -> Path:
    return specs_dir / "desired_program_model" / "ticket_plan.yaml"


def load_ticket_plan(specs_dir: Path) -> dict[str, Any]:
    path = ticket_plan_path(specs_dir)
    if not path.exists():
        raise SystemExit(f"missing ticket plan: {path}")
    plan = _load_manifest(path)
    if not isinstance(plan, dict) or not isinstance(plan.get("tickets"), list):
        raise SystemExit(f"ticket plan must contain a tickets list: {path}")
    return plan


def find_ticket(plan: dict[str, Any], ticket_ref: str, *, source: Path | None = None) -> tuple[int, dict[str, Any]]:
    tickets = plan.get("tickets")
    if not isinstance(tickets, list):
        raise SystemExit("ticket plan has no tickets list")
    for index, ticket in enumerate(tickets):
        if isinstance(ticket, dict) and str(ticket.get("id", "")) == ticket_ref:
            return index, ticket
    normalized = ticket_ref.removeprefix("ticket-")
    if normalized.isdigit():
        index = int(normalized)
        if 0 <= index < len(tickets) and isinstance(tickets[index], dict):
            return index, tickets[index]
    plan_source = source or Path("ticket_plan.yaml")
    raise SystemExit(f"ticket {ticket_ref!r} was not found in {plan_source}")


def ticket_title(ticket: dict[str, Any], fallback: str) -> str:
    value = ticket.get("title")
    return str(value) if value is not None and str(value).strip() else fallback


def ticket_root_dir(specs_dir: Path, ticket_root: Path) -> Path:
    return ticket_root if ticket_root.is_absolute() else specs_dir / ticket_root


def project_current_source(specs_dir: Path) -> Path:
    current = specs_dir / "current"
    return current if current.exists() else specs_dir / "program_model"


def ticket_close_command(
    ticket_id: str,
    spec_root: Path = Path("specs"),
    ticket_root: Path = Path("tickets"),
) -> str:
    command = f"tla-spec-dev --spec-root {spec_root.as_posix()} close ticket {ticket_id}"
    if ticket_root.as_posix().rstrip("/") != "tickets":
        command += f" --ticket-root {ticket_root.as_posix()}"
    return command


def ticket_readme(
    ticket_id: str,
    title: str,
    source_current: Path,
    spec_root: Path = Path("specs"),
    ticket_root: Path = Path("tickets"),
    with_current: bool = False,
) -> str:
    current_line = (
        "- `current/`: the whole-program state this ticket started from (opened with `--with-current`).\n"
        if with_current
        else ""
    )
    step_2 = (
        """2. Implement the ticket, then update `current/` to the behavior that actually
   landed. A `current/` that diverges from `desired/` at close is accepted as
   `desired/` and the receipt says so."""
        if with_current
        else "2. Implement the ticket."
    )
    close_validates = (
        "Closing accepts `desired/` (a divergent `current/` is recorded, never refused), replaces"
        if with_current
        else "Closing replaces"
    )
    return f"""# Ticket {ticket_id}: {title}

This directory is the active, ticket-local spec workflow for one ticket.

Layout:

- `ticket.yaml`: copied ticket-plan entry and lifecycle metadata.
{current_line}- `desired/`: the whole-program state that should be true after this ticket.
- `testgraph/`: copied Test Graph bindings/selectors/assertions when present.
- `results/`: ticket-local TLC, adapter, Test Graph, and review evidence.

Workflow:

1. Edit `desired/`. It starts as a copy of the project current model; change
   its TLA+, configs and, when the project has them, generated-case metadata,
   spec adapters, tests, and Test Graph bindings so it represents the
   whole-program state after this ticket is done. Run TLC on it once.
{step_2}
3. If this ticket adds spec-unit or Test Graph coverage, keep those adapters,
   tests, bindings, selectors, and assertions in the ticket directory.
4. Run TLC and, when the project has them, generated spec-unit adapters and
   Test Graph validation.
5. Mark the global ticket-plan entry done.
6. Run `{ticket_close_command(ticket_id, spec_root, ticket_root)}`. {close_validates}
   project `specs/current` with ticket `desired/`, merges ticket Test Graph
   config back into project specs, snapshots this directory into history, and
   removes the active ticket directory. If it refuses, rerun with `--force`
   and say why in `--summary`; never edit the plan's status to get past it.
7. Close-out skill feedback: a finding you record whose `target:` is in THIS
   repository owes this repository a change. Give each one a `skill_change:`
   of `applied(<commit>)` (the file is in your worktree, so prefer this),
   `proposed(<unit>, <diff or issue>)`, or `declined(<reason>)`. A proposal is
   a diff or an issue with a diff; prose alone reads as no proposal. The close
   prints one warning line per finding without one and PROCEEDS -- it is a
   report, not a gate, so there is nothing to force past.

Starting source: `{source_current}`

Future worktree support should attach the ticket worktree here, but this
scaffold intentionally records only the spec-side state for now.
"""


def ticket_next_steps(
    ticket_id: str,
    ticket_dir: Path,
    spec_root: Path = Path("specs"),
    ticket_root: Path = Path("tickets"),
    with_current: bool = False,
) -> str:
    step_4 = (
        f"""  4. Implement the ticket, then update {ticket_dir / "current"} to match the
     landed behavior. At close, a divergent current is accepted as desired."""
        if with_current
        else "  4. Implement the ticket."
    )
    return f"""
Next ticket workflow steps for {ticket_id}:
  1. Edit {ticket_dir / "desired"}. Update the TLA+ model/configs so they
     describe the whole-program state after this ticket. Run TLC on it once.
  2. Optional: ticket-local spec-unit adapters/tests under
     {ticket_dir / "desired"} when the project has the generated-case layer.
  3. Optional: ticket-local Test Graph adapters/bindings/selectors under
     {ticket_dir / "testgraph"} or {ticket_dir / "test_graph"} when the
     project has one.
{step_4}
  5. Mark {ticket_id} done in the project ticket plan and run:
     {ticket_close_command(ticket_id, spec_root, ticket_root)}
     If the close refuses, rerun it with --force and say why in --summary.
  6. In the close-out feedback, give every finding that targets THIS repository
     a skill_change: applied(<commit>) | proposed(<unit>, <diff or issue>) |
     declined(<reason>). A proposal is a diff or an issue with a diff, never
     prose. The close warns once per finding without one and still proceeds.
"""


def ticket_state_payload(
    *,
    specs_dir: Path,
    ticket_root: Path,
    ticket_root_arg: Path,
    ticket_dir: Path,
    ticket_id: str,
    ticket_index: int,
    ticket: dict[str, Any],
    source_current: Path,
    source_project_desired: Path,
    spec_root: Path,
    seed_manifest: dict[str, Any] | None = None,
    with_current: bool = True,
) -> dict[str, Any]:
    return {
        "schema_version": "tla-spec-dev.ticket-workflow.v1",
        "seed_manifest": seed_manifest if seed_manifest is not None else {},
        "ticket_id": ticket_id,
        "ticket_index": ticket_index,
        "status": "active",
        "ticket_plan": str(ticket_plan_path(specs_dir)),
        "ticket_root": str(ticket_root),
        "ticket_dir": str(ticket_dir),
        "source_current": str(source_current),
        "source_project_desired": str(source_project_desired),
        "current_dir": "current" if with_current else None,
        "desired_dir": "desired",
        "results_dir": "results",
        "testgraph_dir": "testgraph",
        "promotion": {
            "close_command": ticket_close_command(ticket_id, spec_root, ticket_root_arg),
            "on_close": "promote ticket desired/ onto project current/ (removing only seeded paths this ticket dropped, preserving unseeded current-only paths) and merge Test Graph artifacts into project specs/",
            "worktree": "deferred",
        },
        "ticket": ticket,
    }


def minimal_tla(module: str) -> str:
    return f"""----------------------------- MODULE {module} -----------------------------
EXTENDS Naturals, FiniteSets, Sequences, TLC

CONSTANTS
  Tickets,
  NoReason

VARIABLES
  accepted_tickets,
  result

vars == << accepted_tickets, result >>

Init ==
  /\\ accepted_tickets = {{}}
  /\\ result = [accepted |-> TRUE, reason |-> NoReason]

\\* @command AcceptTicket
\\* @result AcceptTicketResult
AcceptTicket(t) ==
  /\\ accepted_tickets' = accepted_tickets \\cup {{t}}
  /\\ result' = [accepted |-> TRUE, reason |-> NoReason]

Next ==
  \\E t \\in Tickets:
    AcceptTicket(t)

\\* @invariant AcceptedTicketsAreKnown
AcceptedTicketsAreKnown ==
  accepted_tickets \\subseteq Tickets

Spec ==
  Init /\\ [][Next]_vars

=============================================================================
"""


def minimal_cfg() -> str:
    return """SPECIFICATION Spec

CONSTANTS
  Tickets = {t1}
  NoReason = NoReason

INVARIANTS
  AcceptedTicketsAreKnown
"""


def current_readme(ticket_id: str, title: str, baseline: Baseline, spec_root: Path = Path("specs")) -> str:
    spec_root_text = _display_spec_root(baseline.repo_root, spec_root)
    return f"""# Current Program Model

This directory is the executable whole-program model of what the repository
implements right now for the active ticket workflow.

Active ticket: `{ticket_id}` - {title}

Baseline:

- Program model manifest: `../program_model/spec_manifest.yaml`
- Program model TLA module: `../program_model/{baseline.module}.tla`

Workflow:

1. Keep this model equivalent to the entire `{spec_root_text}/program_model` before
   implementation. Do not copy only the feature or ticket-local subset.
2. After each ticket slice lands in production code, update this directory with
   the implemented whole-program state, actions, invariants, adapter mappings,
   and tests while preserving existing modeled behavior.
3. Run TLC and current-model adapter/unit tests before adding broader
   integration or graph coverage.
4. Record validation evidence in `spec_manifest.yaml` and keep
   `../desired_program_model/ticket_plan.yaml` synchronized.

Do not model tests, test graph nodes, CI jobs, integration harnesses, or
validation workflow mechanics as TLA+ state/actions. Those belong in manifest
status, ticket evidence, or adapter validation commands.
"""


def desired_readme(ticket_id: str, title: str, baseline: Baseline) -> str:
    return f"""# Desired Program Model

This directory describes the planned destination for the active ticket
workflow. It is both a formal model target and a structured implementation
plan.

Initial ticket: `{ticket_id}` - {title}

Baseline:

- Program model manifest: `../program_model/spec_manifest.yaml`
- Program model: `../program_model/` (Core.tla, Internal.tla, External.tla)

Files:

- `Core.tla`: shared constants and operators for the desired target.
- `Internal.tla` / `Internal.cfg`: desired internal view. Drives spec-unit cases.
- `External.tla` / `External.cfg`: desired external view. Drives Test Graph
  cases. Edit this whenever the ticket changes publicly observable behavior.
- `actions.yml`: keep in sync with both modules.
- `case_adapters.toml` / `testgraph_bindings.yml`: spec-unit and Test Graph
  adapter mappings. A new action is not done until it is mapped in the one that
  matches its layer.
- `spec_manifest.yaml`: desired generated-case manifest plus workflow status.
- `ticket_plan.yaml`: ticket breakdown with dependencies, current-model
  increments, adapter expectations, validation commands, and evidence slots.
- `desired_state.yaml`: human-readable index of modeled boundaries and
  implementation status.
"""


def current_manifest(module: str, package: str, ticket_id: str, title: str, spec_root: Path = Path("specs")) -> str:
    spec_root_text = spec_root.as_posix()
    return f"""module: {module}
package: current_program_cases

status:
  workflow: ticket
  active_ticket: {ticket_id}
  active_ticket_title: "{title}"
  relation_to_program_model: starts_equivalent_then_advances_as_slices_land
  relation_to_desired_program_model: implemented_prefix_of_desired_ticket_plan
  current_model_rule: whole_program_working_copy_not_ticket_projection
  test_modeling_rule: do_not_model_tests_or_validation_harnesses_as_program_behavior
  updated: null
  current_slice:
    name: baseline
    status: scaffolded
    refines: []
    implemented_actions: []
    validation:
      unit: []
      tlc: []
      graph: []
      evidence: []
  next:
    - Fill in whole-program current state fields, actions, invariants, and adapters after the first production slice lands.
    - Preserve all existing {spec_root_text}/program_model state/actions unless production behavior changes them.
    - Run TLC and adapter/unit tests before adding graph execution coverage.
    - Propose the budgets below to the user, ask which to adjust for this program, and record a one-line rationale per changed value.

# Per-program complexity and case budgets -- advisory thresholds read by
# analyze complexity (which warns with facts and never blocks) and by the
# EXPERIMENTAL fuzzing surface (case generation, the adapter runner, the
# mutation kill test). Defaults come from references/modular_fuzzing.md;
# doctrine: SKILL.md "Complexity Budgets Are Advisory".
{budgets_block()}
# Optional dead-weight audit (advisory): add a justification: table linking
# every declared variable to what depends on it. Schema: one mapping per
# variable with at least one NON-EMPTY list among invariants/effects/
# kill_tests. Prose strings are not linkage -- a prose-only entry leaves the
# variable flagged DEAD WEIGHT. Example:
#   justification:
#     orders:
#       invariants: [SafetyInv]
#       effects: [order_submitted]
#       kill_tests: [test_order_cap]

source_model:
  program_model_manifest: ../program_model/spec_manifest.yaml
  program_model_core: ../program_model/Core.tla
  program_model_internal: ../program_model/Internal.tla
  program_model_external: ../program_model/External.tla
  desired_ticket_plan: ../desired_program_model/ticket_plan.yaml

case_codegen:
  style: explicit_transition_cases
  generation_status: planned

# Generated-case index stanzas: placeholders owned by case codegen, filled
# only when case_codegen.generation_status reaches `generated`. Empty means
# "no generated case index yet", NOT "the model has no state/actions/ports"
# -- those live in the TLA+ module and the effects block. An empty stanza and
# an inapplicable stanza are different claims (CD-11, audit run 4 ESC-R4-2).
state_fields: []
actions: []
ports: {{}}
adapters: case_adapters.toml
notes:
  package_from_program_model: {package}
"""


def desired_manifest(module: str, package: str, ticket_id: str, title: str, spec_root: Path = Path("specs")) -> str:
    spec_root_text = spec_root.as_posix()
    return f"""module: {module}
package: desired_program_cases

status:
  workflow: ticket
  initial_ticket: {ticket_id}
  initial_ticket_title: "{title}"
  ticket_plan: ticket_plan.yaml
  relation_to_program_model: desired_successor_of_accepted_program_model
  relation_to_current: target_state_for_specs_current_to_converge_to
  updated: null
  summary:
    desired_model_scaffolded: true
    ticket_plan_scaffolded: true
    current_model_scaffolded: true
    generated_cases: pending
    adapters: pending
  done: []
  pending:
    - Fill in desired state/actions/invariants for the ticket.
    - Break the work into tickets in ticket_plan.yaml.
    - Update {spec_root_text}/current as each ticket lands.
    - Promote converged desired/current model back into {spec_root_text}/program_model.
    - Propose the budgets below to the user, ask which to adjust for this program, and record a one-line rationale per changed value.

# Per-program complexity and case budgets -- advisory thresholds read by
# analyze complexity (which warns with facts and never blocks) and by the
# EXPERIMENTAL fuzzing surface (case generation, the adapter runner, the
# mutation kill test). Defaults come from references/modular_fuzzing.md;
# doctrine: SKILL.md "Complexity Budgets Are Advisory".
{budgets_block()}
# Optional dead-weight audit (advisory): add a justification: table linking
# every declared variable to what depends on it. Schema: one mapping per
# variable with at least one NON-EMPTY list among invariants/effects/
# kill_tests. Prose strings are not linkage -- a prose-only entry leaves the
# variable flagged DEAD WEIGHT. Example:
#   justification:
#     orders:
#       invariants: [SafetyInv]
#       effects: [order_submitted]
#       kill_tests: [test_order_cap]

source_model:
  program_model_manifest: ../program_model/spec_manifest.yaml
  program_model_core: ../program_model/Core.tla
  program_model_internal: ../program_model/Internal.tla
  program_model_external: ../program_model/External.tla
  baseline_package: {package}

case_codegen:
  style: explicit_transition_cases
  generation_status: planned

# Generated-case index stanzas: placeholders owned by case codegen, filled
# only when case_codegen.generation_status reaches `generated`. Empty means
# "no generated case index yet", NOT "the model has no state/actions/ports"
# -- those live in the TLA+ module and the effects block. An empty stanza and
# an inapplicable stanza are different claims (CD-11, audit run 4 ESC-R4-2).
state_fields: []
actions: []
ports: {{}}
notes:
  direction: "This manifest records the target whole-program model and the ticket workflow status. Keep ticket_plan.yaml synchronized whenever scope, order, validation, or acceptance criteria change."
"""


def ticket_plan(ticket_id: str, title: str, module: str, spec_root: Path = Path("specs")) -> str:
    spec_root_text = spec_root.as_posix()
    return f"""# This file is part of the desired program model.
# It is intentionally general: use it for any model-backed ticket workflow,
# not only migrations. Keep it synchronized with spec_manifest.yaml status.
version: 1
name: desired-ticket-workflow
updated: null
purpose: "Break the desired whole-program change into tickets that can be implemented, modeled in {spec_root_text}/current, unit-tested, and then validated with broader graph or integration checks."

planning_rules:
  current_model_rule: Update {spec_root_text}/current after each production slice lands as a whole-program working copy of {spec_root_text}/program_model, not a ticket projection.
  unit_validation_rule: Run current-model TLC and adapter/unit tests before adding graph execution.
  graph_rule: Add graph or integration nodes only after current-model validation passes.
  semantic_model_rule: Do not add test graph nodes, pytest jobs, CI workflow steps, integration harnesses, or validation scripts as TLA+ program state/actions.
  evidence_rule: Record tests and graph runs as evidence for semantic program actions in manifests or ticket status.
  desired_sync_rule: Update this file and spec_manifest.yaml whenever scope, order, acceptance checks, or status changes.
  promotion_rule: When {spec_root_text}/current equals {spec_root_text}/desired_program_model, promote the converged model to {spec_root_text}/program_model.

status:
  workflow: ticket
  active_ticket: {ticket_id}
  active_ticket_title: "{title}"
  desired_module: {module}
  phase: planning

# Replace or extend these sections with project-specific domains. Service,
# process, queue, database, file, API, model, permission, or UI boundaries can
# all be listed here when they matter to correctness.
service_catalog:
  existing_boundaries: []
  desired_boundaries: []
  adapter_boundaries: []
  known_gaps: []

tickets:
  - id: {ticket_id}
    title: "{title}"
    status: next
    depends_on: []
    objective: "Describe the behavior change in program terms. Name the resource or state boundary that must become true, not only the implementation file."
    desired_actions:
      # Add TLA+ action names that will exist in {spec_root_text}/desired_program_model.
      - ReplaceWithDesiredAction
    implementation_scope:
      # Add production files, scripts, descriptors, infrastructure, or adapters
      # this ticket is allowed to touch.
      - Replace with implementation surfaces
    current_increment:
      model_state:
        # Add state fields that the whole-program {spec_root_text}/current model will gain after implementation.
        # Preserve all existing {spec_root_text}/program_model fields unless the program behavior changes.
        - replace_with_state_field
      model_actions:
        # Add semantic program actions that {spec_root_text}/current will gain after implementation.
        # Do not add tests, graph nodes, CI jobs, or validation harness steps here.
        - ReplaceWithDesiredAction
      adapters:
        # Add adapter classes or commands that prove production conforms.
        - ReplaceWithAdapter
      unit_tests:
        # Add current-model tests that must pass before graph coverage.
        - pytest {spec_root_text}/current/tests
      graph_after_unit_pass:
        # Add graph/test nodes only after current-model tests pass.
        - replace.with.graph.node
    acceptance:
      commands:
        # A wrapper that saves transcripts derives its output dir from the
        # target model; checking desired/ never writes current's transcripts.
        - python scripts/run_tlc_or_project_specific_check.py
      assertions:
        - The production slice refines to the current model.
        - The current model advances toward the desired model.
      evidence: []
"""


def desired_state(ticket_id: str, title: str, module: str, spec_root: Path = Path("specs")) -> str:
    spec_root_text = spec_root.as_posix()
    return f"""version: 1
name: desired-program-model
canonical_tla_module: {module}
views:
  internal:
    module: Internal.tla
    config: Internal.cfg
    generates: spec_unit
    adapter_mapping: case_adapters.toml
  external:
    module: External.tla
    config: External.cfg
    generates: testgraph
    adapter_mapping: testgraph_bindings.yml
manifest: spec_manifest.yaml
ticket_plan: ticket_plan.yaml

relationship:
  extends_current_program_model: ../program_model/Internal.tla
  extends_current_external_model: ../program_model/External.tla
  purpose: desired whole-program model for ticket workflow
  generation_status: planned

implementation_status:
  updated: null
  policy: {spec_root_text}/current is the executable state of landed work; this file summarizes the desired destination.
  active_ticket: {ticket_id}
  active_ticket_title: "{title}"
  summary:
    desired_model_scaffolded: true
    ticket_breakdown: scaffolded
    current_model: scaffolded
    generated_desired_cases: pending
    adapters: pending

modeled_boundary_status:
  ticket_plan:
    status: scaffolded
    artifact: ticket_plan.yaml
    next_ticket: {ticket_id}

program_domains: []
implementation_sources: {{}}
adapter_plan:
  desired_new_ports: []
guardrails: {{}}
"""


def case_adapters_toml() -> str:
    return """# Map generated current-model case labels to production adapters.
# Example:
# [adapters.ReplaceWithDesiredAction]
# adapter = "my_project.spec_adapters:ReplaceWithDesiredActionAdapter"
"""


def production_adapters_py() -> str:
    return '''"""Production adapters for current-model ticket workflow cases.

Add one small adapter per modeled boundary. Each adapter should materialize the
case pre-state, call the production boundary, observe production state, and
refine that observation back to the generated case shape.
"""

from __future__ import annotations


class ScaffoldedTicketAdapter:
    """Placeholder adapter documenting the expected shape."""

    def can_run(self, case):
        return False, "replace ScaffoldedTicketAdapter with a ticket-specific adapter"
'''


def current_test(ticket_id: str) -> str:
    return current_test_for_spec_root(ticket_id, Path("specs"))


def current_test_for_spec_root(ticket_id: str, spec_root: Path) -> str:
    return f'''from pathlib import Path


SPEC_ROOT = Path(__file__).resolve().parents[1].parent


def test_current_ticket_workflow_scaffold_points_to_desired_plan() -> None:
    manifest = SPEC_ROOT / "current/spec_manifest.yaml"
    plan = SPEC_ROOT / "desired_program_model/ticket_plan.yaml"

    assert manifest.exists()
    assert plan.exists()
    assert "{ticket_id}" in manifest.read_text(encoding="utf-8")
    assert "{ticket_id}" in plan.read_text(encoding="utf-8")
'''


def ticket_workflow_test(ticket_id: str) -> str:
    return f'''from pathlib import Path


TICKET_ROOT = Path(__file__).resolve().parents[1]


def test_ticket_workflow_scaffold_points_to_local_desired() -> None:
    desired = TICKET_ROOT / "desired/spec_manifest.yaml"
    ticket = TICKET_ROOT / "ticket.yaml"

    assert desired.exists()
    assert ticket.exists()
    assert "{ticket_id}" in ticket.read_text(encoding="utf-8")
'''


def scaffold_ticket_directory(
    repo_root: Path,
    ticket_ref: str,
    *,
    force: bool,
    dry_run: bool,
    spec_root: Path = Path("specs"),
    ticket_root: Path = Path("tickets"),
    print_next_steps: bool = False,
    with_current: bool = False,
) -> list[Path]:
    """Open a ticket workspace.

    Default (2026-09-14): `desired/` only. The ticket edits the model it wants
    and the close promotes it. `with_current=True` also seeds `current/` for
    the older two-directory loop, in which a divergent `current/` at close is
    accepted as `desired/` rather than refused.
    """
    fallback_module = _module_name(repo_root.name)
    baseline = discover_baseline(repo_root, spec_root, fallback_module)
    specs_dir = baseline.spec_root
    plan = load_ticket_plan(specs_dir)
    ticket_index, ticket = find_ticket(plan, ticket_ref, source=ticket_plan_path(specs_dir))
    resolved_ticket_id = str(ticket.get("id") or f"ticket-{ticket_index}")

    # E-01 (#310): `open ticket` used to succeed on a ticket the plan already
    # marks closed or retired, scaffolding 53 files and printing the ordinary
    # next steps -- reopening finished work was indistinguishable from starting
    # new work. TlaSpecDevCli.tla guards OpenTicket on
    # `ticket_state[ticket] = TicketUnopened`, under a comment that names the
    # property: "the never-reopened property is now structural". It was not
    # enforced anywhere in production, and nothing -- TLC, the Test Graph, the
    # suite -- reported it, because nothing drives the CLI against the plan's
    # status field.
    #
    # `--force` (or SKILL_GATES=off) reopens anyway, with one warning line.
    from scripts.spec_evolution import (
        TICKET_CLOSED_STATUSES,
        TICKET_RETIRED_STATUS,
        gates_forced,
        refuse_or_warn,
    )

    raw_status = str(ticket.get("status") or "").strip().lower()
    if raw_status in TICKET_CLOSED_STATUSES or raw_status == TICKET_RETIRED_STATUS:
        refuse_or_warn(
            [
                f"ERROR: ticket {resolved_ticket_id} has already entered the lifecycle: "
                f"status={raw_status}. Add a NEW ticket entry to "
                f"{ticket_plan_path(specs_dir)}, or pass --force to reopen it."
            ],
            force=gates_forced(force),
        )
    title = ticket_title(ticket, resolved_ticket_id)
    root_dir = ticket_root_dir(specs_dir, ticket_root)
    ticket_dir = root_dir / _safe_segment(resolved_ticket_id)
    source_current = project_current_source(specs_dir)
    source_project_desired = specs_dir / "desired_program_model"

    current_dir = ticket_dir / "current"
    desired_dir = ticket_dir / "desired"
    skip_project_tests = {PROJECT_WORKFLOW_TEST}
    written: list[Path] = []
    if with_current:
        written.extend(copy_workflow_tree(source_current, current_dir, force=force, dry_run=dry_run, skip_paths=skip_project_tests))
    written.extend(copy_workflow_tree(source_current, desired_dir, force=force, dry_run=dry_run, skip_paths=skip_project_tests))
    seed_manifest = {
        "source": str(source_current),
        "excluded": sorted(skip_project_tests),
        "desired": workflow_tree_seed_paths(source_current, skip_project_tests),
        "note": (
            "Paths seeded from project current/ into this ticket workspace. Promotion may "
            "remove a project current/ path only if it appears here and the ticket dropped it; "
            "paths absent from this list were never offered to the ticket and are preserved."
        ),
    }
    written.extend(copy_optional_tree(specs_dir / "testgraph", ticket_dir / "testgraph", force=force, dry_run=dry_run))
    written.extend(copy_optional_tree(specs_dir / "test_graph", ticket_dir / "test_graph", force=force, dry_run=dry_run))

    ticket_payload = ticket_state_payload(
        specs_dir=specs_dir,
        ticket_root=root_dir,
        ticket_root_arg=ticket_root,
        ticket_dir=ticket_dir,
        ticket_id=resolved_ticket_id,
        ticket_index=ticket_index,
        ticket=ticket,
        source_current=source_current,
        source_project_desired=source_project_desired,
        spec_root=spec_root,
        seed_manifest=seed_manifest,
        with_current=with_current,
    )
    files = [
        (ticket_dir / "README.md", ticket_readme(resolved_ticket_id, title, source_current, spec_root, ticket_root, with_current=with_current)),
        (ticket_dir / "ticket.yaml", json.dumps(ticket_payload, indent=2, sort_keys=True) + "\n"),
        (ticket_dir / "tests" / "test_ticket_workflow.py", ticket_workflow_test(resolved_ticket_id)),
        (ticket_dir / "results" / ".gitkeep", ""),
        # MF-019: every ticket opens with the complexity-ledger input already
        # scaffolded. It is advisory: an unfilled one is recorded as rejected
        # and the close proceeds with one warning line.
        (ticket_dir / "results" / "complexity_ledger.yaml", complexity_ledger.TEMPLATE),
    ]
    for path, content in files:
        if write_file(path, content, force=force, dry_run=dry_run):
            written.append(path)

    if print_next_steps:
        print(ticket_next_steps(resolved_ticket_id, ticket_dir, spec_root, ticket_root, with_current=with_current))

    return written


def scaffold(
    repo_root: Path,
    ticket_id: str,
    title: str,
    force: bool,
    dry_run: bool,
    spec_root: Path = Path("specs"),
) -> list[Path]:
    fallback_module = _module_name(repo_root.name)
    baseline = discover_baseline(repo_root, spec_root, fallback_module)
    module = baseline.module
    package = baseline.package
    current_dir = baseline.spec_root / "current"
    desired_dir = baseline.spec_root / "desired_program_model"

    written: list[Path] = []
    written.extend(copy_baseline_tree(baseline.program_dir, current_dir, force=force, dry_run=dry_run))
    written.extend(copy_baseline_tree(baseline.program_dir, desired_dir, force=force, dry_run=dry_run))

    files = [
        (current_dir / "README.md", current_readme(ticket_id, title, baseline, spec_root)),
        (
            current_dir / "spec_manifest.yaml",
            carry_manifest_semantic_tail(
                current_manifest(module, package, ticket_id, title, spec_root),
                baseline.program_dir / "spec_manifest.yaml",
            ),
        ),
        (current_dir / "tests" / "test_current_ticket_workflow.py", current_test_for_spec_root(ticket_id, spec_root)),
        (desired_dir / "README.md", desired_readme(ticket_id, title, baseline)),
        (
            desired_dir / "spec_manifest.yaml",
            carry_manifest_semantic_tail(
                desired_manifest(module, package, ticket_id, title, spec_root),
                baseline.program_dir / "spec_manifest.yaml",
            ),
        ),
        (desired_dir / "ticket_plan.yaml", ticket_plan(ticket_id, title, module, spec_root)),
        (desired_dir / "desired_state.yaml", desired_state(ticket_id, title, module, spec_root)),
    ]
    for path, content in files:
        if write_file(path, content, force=force, dry_run=dry_run):
            written.append(path)

    # Adapter mappings and adapters belong to the baseline and arrive via
    # copy_baseline_tree. Never write over them -- even with --force, which would
    # otherwise replace a real spec-unit mapping with an empty stub. A
    # three-module baseline carries adapters.py plus both mappings, so these
    # placeholders exist only to seed a legacy baseline that had neither.
    if baseline.is_legacy_single_module:
        for path, content in [
            (current_dir / "case_adapters.toml", case_adapters_toml()),
            (current_dir / "production_adapters.py", production_adapters_py()),
        ]:
            if not path.exists() and write_file(path, content, force=False, dry_run=dry_run):
                written.append(path)

    # A three-module baseline already arrived whole via copy_baseline_tree:
    # Core/Internal/External plus both adapter mappings. Only a legacy
    # single-module baseline needs its module and MC.cfg placed by name.
    if baseline.is_legacy_single_module:
        for target_dir in [current_dir, desired_dir]:
            tla_target = target_dir / f"{module}.tla"
            cfg_target = target_dir / "MC.cfg"
            if copy_file(baseline.tla_path, tla_target, "", force=force, dry_run=dry_run):
                written.append(tla_target)
            if copy_file(baseline.cfg_path, cfg_target, "", force=force, dry_run=dry_run):
                written.append(cfg_target)

    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ticket_id", help="Ticket id, for example AUTH-123 or K8S-010.")
    parser.add_argument("title", help="Human-readable ticket title.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd(), help="Repository root to scaffold into.")
    parser.add_argument("--spec-root", type=Path, default=Path("specs"), help="Spec root under the repository.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing scaffold files.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned writes without changing files.")
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    written = scaffold(repo_root, args.ticket_id, args.title, args.force, args.dry_run, args.spec_root)
    print(f"scaffolded ticket workflow files: {len(written)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
