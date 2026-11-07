#!/usr/bin/env python3
"""Close a ticket workflow after current, desired, and program models converge.

This script is intentionally limited to workflow cleanup. Promote the converged
model to ``program_model`` and close every ticket in ``ticket_plan.yaml`` before
running it.
"""

from __future__ import annotations

import argparse
import filecmp
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

try:
    from . import complexity_ledger
    from .skill_feedback import parse_close_out_entries, skill_feedback_path
    from .spec_evolution import (
        TICKET_CLOSED_STATUSES,
        ModelSelectionError,
        complexity_ledger_input_path,
        create_workflow_closed_snapshot,
        gates_forced,
        live_receipt_manifests,
        print_commit_recommendation,
        refuse_or_warn,
        select_model_files,
        validate_model_pair,
        validate_workflow_ticket_completion,
        workflow_name as resolve_workflow_name,
    )
except ImportError:  # pragma: no cover - direct script execution
    import complexity_ledger
    from skill_feedback import parse_close_out_entries, skill_feedback_path
    from spec_evolution import (
        TICKET_CLOSED_STATUSES,
        ModelSelectionError,
        complexity_ledger_input_path,
        create_workflow_closed_snapshot,
        gates_forced,
        live_receipt_manifests,
        print_commit_recommendation,
        refuse_or_warn,
        select_model_files,
        validate_model_pair,
        validate_workflow_ticket_completion,
        workflow_name as resolve_workflow_name,
    )


SEMANTIC_SUFFIXES = {".tla", ".cfg", ".yaml", ".yml"}
#: Files that live in a model directory but are NOT part of the program model:
#: the schedule, the desired-state note, and the deferment backlog. They are
#: never compared for convergence and never promoted between trees.
#:
#: `deferred_findings.yaml` is the git-epic-workflow deferment backlog
#: (`references/deferment.md`), and it sits beside `ticket_plan.yaml` in
#: `desired_program_model/`. Classifying it as semantic made it a promotion
#: SUBJECT: it exists in `desired_program_model/` alone, so a convergence
#: promotion would have deleted the epic's entire findings ledger as a file
#: "the source no longer has", and `--accept-new` would have copied the backlog
#: into the promoted program model as though it were part of the specification.
#: It is bookkeeping about the work, not a statement about the program.
#:
#: `attribution.yaml` is the same kind of record (#177): `references/
#: bug_attribution.md` has epics keep it beside the findings ledger, and the
#: close refused a converged workflow with "semantic file exists only in
#: desired_program_model: attribution.yaml" until it was moved out by hand.
#:
#: BACKLOG_FILES are the subset appended to WHILE the epic runs, after any one
#: ticket closed. They are excluded from the exact-snapshot comparison too (#72):
#: a finding filed after the terminal ticket's close is not a change to the
#: desired program.
BACKLOG_FILES = {
    "deferred_findings.yaml",
    "attribution.yaml",
}
PLANNING_FILES = {
    "README.md",
    "ticket_plan.yaml",
    "desired_state.yaml",
    *BACKLOG_FILES,
}
SKILL_ROOT = Path(__file__).resolve().parents[1]

#: The three spec trees a module reference can name. A binding map names the
#: tree it lives in, so promoting one between trees requires RE-ROOTING, not a
#: byte copy.
MODEL_DIR_NAMES = ("current", "desired_program_model", "program_model")
_MODULE_PREFIX = re.compile(r"\bspecs\.(?:%s)\." % "|".join(MODEL_DIR_NAMES))

#: Only mapping files carry module references; .tla and .cfg files do not.
REROOTED_NAMES = {"testgraph_bindings.yml", "case_adapters.toml"}


def _load_yaml(path: Path) -> dict[str, Any]:
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


def _resolve_spec_root(repo_root: Path, spec_root: Path) -> Path:
    return spec_root if spec_root.is_absolute() else repo_root / spec_root


def _semantic_files(root: Path) -> dict[Path, Path]:
    return {
        path.relative_to(root): path
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and path.suffix.lower() in SEMANTIC_SUFFIXES
        and path.relative_to(root).as_posix() not in PLANNING_FILES
    }


def _semantic_yaml(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _semantic_yaml(inner)
            for key, inner in value.items()
            if key not in {"status", "notes"} and key != "package"
        }
    if isinstance(value, list):
        return [_semantic_yaml(inner) for inner in value]
    return value


def _semantic_file_matches(left: Path, right: Path) -> bool:
    if left.name == "spec_manifest.yaml" and right.name == "spec_manifest.yaml":
        return _semantic_yaml(_load_yaml(left)) == _semantic_yaml(_load_yaml(right))
    if left.name in REROOTED_NAMES and right.name == left.name:
        # These files are RE-ROOTED on promotion, not copied, so the two trees
        # are equivalent when they differ ONLY by which spec tree their module
        # references name. Comparing the bytes would make a correct promotion
        # look like a divergence and block closeout. Normalizing to a common
        # placeholder compares everything else strictly, so a real edit to a
        # binding still shows up as a difference.
        return _MODULE_PREFIX.sub("specs.<tree>.", left.read_text(encoding="utf-8")) == (
            _MODULE_PREFIX.sub("specs.<tree>.", right.read_text(encoding="utf-8"))
        )
    return filecmp.cmp(left, right, shallow=False)


def validate_equivalent(current_dir: Path, desired_dir: Path, label: str = "desired_program_model") -> list[str]:
    errors: list[str] = []
    if not current_dir.exists():
        errors.append(f"missing model directory: {current_dir}")
    if not desired_dir.exists():
        errors.append(f"missing model directory: {desired_dir}")
    if errors:
        return errors

    current_files = _semantic_files(current_dir)
    desired_files = _semantic_files(desired_dir)
    if not current_files and not desired_files:
        errors.append("no semantic model files found to compare")
        return errors

    current_only = sorted(set(current_files) - set(desired_files))
    desired_only = sorted(set(desired_files) - set(current_files))
    for relative in current_only:
        errors.append(f"semantic file exists only in {current_dir.name}: {relative}")
    for relative in desired_only:
        errors.append(f"semantic file exists only in {label}: {relative}")

    for relative in sorted(set(current_files) & set(desired_files)):
        if not _semantic_file_matches(current_files[relative], desired_files[relative]):
            errors.append(f"semantic file differs: {relative}")
    return errors


def workflow_promotion_guidance() -> str:
    """Explain how to prepare current/desired/program_model for workflow closeout."""
    semantic_suffixes = ", ".join(sorted(SEMANTIC_SUFFIXES))
    return (
        "How to prepare this workflow for closeout:\n"
        "- Closeout requires the semantic files in current/, desired_program_model/, and the promoted "
        "program_model/ to match, every delivered ticket to have one matching successful-close receipt, "
        "and every retired ticket to have its exact retirement receipt.\n"
        f"- Compared semantic files: {semantic_suffixes} (planning files such as README.md, "
        "ticket_plan.yaml, and status/notes metadata are ignored).\n"
        "- Option A: reconcile the models by hand (finish landing current/, promote the converged model "
        "into program_model/, mark every ticket closed), then re-run this command.\n"
        "- Option B: re-run with --accept-new to accept desired_program_model/ as the new current/ and "
        "program_model/ automatically (their semantic files are overwritten from desired_program_model/ "
        "before the snapshot); tickets must still be marked closed. It runs desired -> current: when "
        "desired_program_model/ is the STALE side (it still holds the previous model), --accept-new "
        "discards the delivered model.\n"
        "- `close ticket` carries each delivered delta into desired_program_model/ three ways (#141 "
        "SF-075; `desired_carry` in each ticket receipt names what followed, merged, or conflicted). "
        "A desired file a receipt lists under desired_carry.conflicts, or a workflow whose tickets "
        "closed before that, is reconciled by hand toward current/ and committed before this command."
    )


# ---------------------------------------------------------------------------
# Close records (#187): what a close writes must be about THIS close.
# ---------------------------------------------------------------------------

#: Written in place of an empty `--summary` (#143 SF-045). A close never blocks
#: on a missing summary; it records the gap so the entry is never silently empty.
MISSING_SUMMARY = "missing: no --summary was given at close"

#: The conventional TLC evidence names the ledger probes beside its input.
TLC_PROBE_NAMES = ("tlc-current.txt", "tlc.txt", "tlc-baseline.txt")


def summary_or_missing(summary: str | None) -> str:
    """The summary to record: the given text, or an explicit `missing` marker."""
    text = (summary or "").strip()
    if text:
        return text
    print(
        "WARNING: no --summary given; the close records "
        f"'{MISSING_SUMMARY}' in manifest.json, summary.md and skill_feedback.md.",
        file=sys.stderr,
    )
    return MISSING_SUMMARY


def print_summary_preview(summary: str, targets: list[str]) -> None:
    """#173: show the rendered summary before it is written to several files."""
    print("summary preview (written verbatim to: " + ", ".join(targets) + "):")
    for line in summary.splitlines() or [""]:
        print(f"  | {line}")


def complexity_ledger_input_problems(
    specs_dir: Path,
    *,
    scope: str,
    scope_id: str,
    workflow: str,
    model_dir: Path,
    input_path: Path,
) -> list[str]:
    """Why this close must not record `input_path` as its complexity evidence.

    Two refusals, both by name, both forceable (`--force` / SKILL_GATES=off):

    - #172: the input names a different workflow in its `workflow:` key. An
      input left behind by an earlier epic was copied into every later close's
      ledger entry and closed-snapshot `refinement_record` as though it
      described that epic.
    - #134: the ledger would REJECT the input. The close used to proceed with a
      one-line warning, so a ticket could finish without ever supplying it.

    An ABSENT or unreadable input is not a problem here: the close never blocks
    on it, and records the measurement as skipped (missing).
    """
    if not input_path.exists():
        return []
    try:
        ledger_input = complexity_ledger.load_input(input_path)
    except Exception:  # unreadable: the close records a skipped measurement
        return []
    problems: list[str] = []
    named = str(ledger_input.get("workflow", "") or "").strip()
    if named and named != workflow:
        problems.append(
            f"complexity ledger input was written for workflow '{named}', not "
            f"'{workflow}': {input_path}. Rewrite it for this {scope} (set "
            f"`workflow: {workflow}`) or delete it; --force records it anyway."
        )
        return problems
    try:
        selection = select_model_files(model_dir)
    except ModelSelectionError:
        return problems
    if selection is None or validate_model_pair(selection):
        return problems
    tlc_report = next(
        (input_path.parent / name for name in TLC_PROBE_NAMES if (input_path.parent / name).exists()),
        None,
    )
    try:
        metrics = complexity_ledger.collect_metrics(
            selection.tla, selection.cfg, selection.manifest, tlc_report
        )
        ledger = complexity_ledger.load_ledger(complexity_ledger.ledger_path(specs_dir))
        verdict = complexity_ledger.evaluate(
            scope=scope,
            scope_id=scope_id,
            workflow=workflow,
            metrics=metrics,
            ledger_input=ledger_input,
            previous=complexity_ledger.previous_entry(ledger),
            input_dir=input_path.parent,
        )
    except Exception:  # the close's own measurement reports what it cannot read
        return problems
    if verdict.rejected:
        first = " ".join(str(verdict.errors[0]).split()) if verdict.errors else ""
        problems.append(
            f"complexity ledger input is rejected ({len(verdict.errors)} issue(s); "
            f"first: {first[:120]}): {input_path}. Fill it in, or --force to "
            "record the rejection and close anyway."
        )
    return problems


def unreviewed_ticket_feedback(specs_dir: Path, workflow: str) -> list[str]:
    """#174: this workflow's ticket close-out entries still `unreviewed`."""
    path = skill_feedback_path(specs_dir)
    if not path.exists():
        return []
    return [
        entry.fields.get("close_id", entry.heading)
        for entry in parse_close_out_entries(path.read_text(encoding="utf-8"))
        if entry.fields.get("close_scope") == "ticket"
        and entry.fields.get("workflow") == workflow
        and entry.declared_status in ("", "unreviewed")
    ]


def print_unreviewed_ticket_feedback(specs_dir: Path, workflow: str) -> list[str]:
    unreviewed = unreviewed_ticket_feedback(specs_dir, workflow)
    if unreviewed:
        print(
            f"WARNING: {len(unreviewed)} ticket skill-feedback entr"
            f"{'y is' if len(unreviewed) == 1 else 'ies are'} still unreviewed in "
            f"{skill_feedback_path(specs_dir)} for workflow {workflow}: "
            + ", ".join(unreviewed)
            + ". Triage them here: set each feedback_status to none-found or items-recorded.",
            file=sys.stderr,
        )
    return unreviewed


def reroot_module_prefixes(text: str, dst_name: str) -> tuple[str, int]:
    """Rewrite ``specs.<any-model-dir>.`` to ``specs.<dst_name>.``.

    Returns the new text and how many references actually MOVED -- a reference
    already naming the destination is not a change and is not counted.

    Bare module names carry no prefix and are left exactly as they are. That is
    the form that cannot rot on promotion, and the one to prefer when authoring.
    """
    replacement = f"specs.{dst_name}."
    moved = sum(1 for m in _MODULE_PREFIX.finditer(text) if m.group(0) != replacement)
    return _MODULE_PREFIX.sub(replacement, text), moved


def promote_semantic_files(src: Path, dst: Path) -> list[str]:
    """Make dst's semantic files identical to src's, preserving dst planning/metadata files.

    Binding maps are RE-ROOTED rather than copied byte-for-byte. Promotion moves
    a file between spec trees, and a module reference inside it names the tree it
    came from: ``desired_program_model/`` is promoted onto BOTH ``current/`` and
    ``program_model/``, so a reference to ``specs.current.adapters`` is correct in
    one destination and dangling in the other. The whole-workflow close then
    DELETES ``current/``, which turns the dangling half into a reference to a
    package that no longer exists.

    Measured before this was fixed: 88 such references across two constituents of
    the meta-orchestrator integration repo, every one naming
    ``specs.current.adapters`` from inside a promoted ``program_model/`` tree
    whose sibling ``current/`` the same close had removed. Nothing failed,
    because the node that would have imported them was blocked for an unrelated
    reason -- a binding that is never resolved cannot fail to resolve.
    """
    if not src.exists():
        return []
    dst.mkdir(parents=True, exist_ok=True)
    src_files = _semantic_files(src)
    dst_files = _semantic_files(dst)
    promoted: list[str] = []
    for relative in sorted(set(dst_files) - set(src_files)):
        dst_files[relative].unlink()
        promoted.append(f"removed {relative}")
    for relative in sorted(src_files):
        destination = dst / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        source = src_files[relative]
        if (
            Path(relative).name == "spec_manifest.yaml"
            and destination.exists()
            and _semantic_file_matches(source, destination)
        ):
            # #177: the manifests differ only in `status:`/`notes:`, which
            # convergence ignores. The destination's header is the accepted-model
            # record the epic agent wrote at promotion; copying the source over
            # it would replace that record with the ticket-workflow header.
            promoted.append(f"kept {relative} (semantically equal; status/notes preserved)")
            continue
        if Path(relative).name in REROOTED_NAMES:
            rerooted, moved = reroot_module_prefixes(
                source.read_text(encoding="utf-8"), dst.name
            )
            destination.write_text(rerooted, encoding="utf-8")
            promoted.append(
                f"wrote {relative} (re-rooted {moved} module reference(s) "
                f"to specs.{dst.name}.)"
                if moved
                else f"wrote {relative}"
            )
        else:
            shutil.copy2(source, destination)
            promoted.append(f"wrote {relative}")
    return promoted


def validate_ticket_plan_closed(
    ticket_plan: Path,
    *,
    repo_root: Path | None = None,
    workflow: str | None = None,
    specs_dir: Path | None = None,
) -> list[str]:
    """Every delivered ticket in `ticket_plan` has its close receipt.

    `specs_dir` is derived from the plan's own location by default, which is
    right for a LIVE plan at `specs/desired_program_model/ticket_plan.yaml` and
    wrong for an ARCHIVED one: a close copies the plan it consumed to
    `specs/.history/<workflow>/closed-snapshot/snapshots/desired_program_model/`,
    where `parent.parent` is the snapshots directory and the receipts are three
    levels above it. Checking a closed workflow against its own archived plan is
    the only way to ask "did this close ship a ticket without a receipt" after
    the live plan is gone, so that caller passes `specs_dir` explicitly.
    """
    if not ticket_plan.exists():
        return [f"missing ticket plan: {ticket_plan}"]
    plan = _load_yaml(ticket_plan)
    specs_dir = (specs_dir or ticket_plan.resolve().parent.parent).resolve()
    resolved_repo_root = (repo_root or specs_dir.parent).resolve()
    return validate_workflow_ticket_completion(
        repo_root=resolved_repo_root,
        specs_dir=specs_dir,
        plan=plan,
        workflow=workflow,
    )


def ticket_plan_has_retirements(ticket_plan: Path) -> bool:
    plan = _load_yaml(ticket_plan)
    tickets = plan.get("tickets")
    return isinstance(tickets, list) and any(
        isinstance(ticket, dict)
        and str(ticket.get("status", "")).strip().lower() == "retired"
        for ticket in tickets
    )


def _exact_snapshot_files(root: Path) -> dict[Path, Path]:
    return {
        path.relative_to(root): path
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and not any(part in IGNORED_EXACT_SNAPSHOT_NAMES for part in path.relative_to(root).parts)
        and path.relative_to(root).as_posix() not in BACKLOG_FILES
    }


IGNORED_EXACT_SNAPSHOT_NAMES = {
    ".DS_Store",
    "__pycache__",
    ".history",
    ".tla-spec-evolution",
    ".gradle",
    ".pytest_cache",
    "build",
    "states",
}


def validate_exact_snapshot(left: Path, right: Path) -> list[str]:
    """Compare every archived planning and semantic byte, excluding snapshot ignores."""
    if not left.is_dir():
        return [f"missing desired program directory: {left}"]
    if not right.is_dir():
        return [f"missing terminal ticket desired snapshot: {right}"]
    left_files = _exact_snapshot_files(left)
    right_files = _exact_snapshot_files(right)
    errors: list[str] = []
    for relative in sorted(set(left_files) - set(right_files)):
        errors.append(f"file exists only in current desired_program_model: {relative}")
    for relative in sorted(set(right_files) - set(left_files)):
        errors.append(f"file exists only in terminal ticket desired snapshot: {relative}")
    for relative in sorted(set(left_files) & set(right_files)):
        if not filecmp.cmp(left_files[relative], right_files[relative], shallow=False):
            errors.append(f"terminal ticket desired snapshot differs: {relative}")
    return errors


def _terminal_delivered_ticket(plan: dict[str, Any]) -> tuple[int, dict[str, Any]] | None:
    tickets = plan.get("tickets")
    if not isinstance(tickets, list):
        return None
    delivered = [
        (index, ticket)
        for index, ticket in enumerate(tickets)
        if isinstance(ticket, dict)
        and str(ticket.get("status", "")).strip().lower() in TICKET_CLOSED_STATUSES
    ]
    if not delivered:
        return None
    ordered = [
        item
        for item in delivered
        if type(item[1].get("promotion_order")) is int
    ]
    if ordered:
        maximum = max(ticket["promotion_order"] for _, ticket in ordered)
        terminal = [item for item in ordered if item[1]["promotion_order"] == maximum]
        return terminal[0] if len(terminal) == 1 else None
    return delivered[-1]


def validate_retirement_accept_new_authority(
    *,
    repo_root: Path,
    specs_dir: Path,
    desired_dir: Path,
    plan: dict[str, Any],
    workflow: str | None,
) -> list[str]:
    """Prove withdrawn desired state came through the terminal delivered ticket."""
    terminal = _terminal_delivered_ticket(plan)
    if terminal is None:
        return [
            "retired-ticket --accept-new requires one terminal successfully closed "
            "non-retired ticket"
        ]
    terminal_index, terminal_ticket = terminal
    terminal_id = str(terminal_ticket.get("id", f"ticket-{terminal_index}"))
    resolved_workflow = resolve_workflow_name(plan, workflow)
    history_root = specs_dir / ".history" / resolved_workflow
    # Superseded receipts stay on disk but do not count: see the
    # SUPERSEDED_MARKER_KEY note in spec_evolution.
    candidates = live_receipt_manifests(history_root, kind="ticket", ticket_id=terminal_id)
    if len(candidates) != 1:
        return [
            f"terminal delivered ticket {terminal_id} must have exactly one successful "
            f"close receipt, found {len(candidates)}"
        ]
    manifest_path, manifest = candidates[0]
    errors: list[str] = []
    if manifest.get("ticket_index") != terminal_index:
        errors.append(
            f"terminal ticket {terminal_id} close receipt has the wrong immutable ordinal"
        )
    if manifest.get("workflow_name") != resolved_workflow:
        errors.append(f"terminal ticket {terminal_id} close receipt names another workflow")
    if str(manifest.get("ticket_status", "")).strip().lower() not in TICKET_CLOSED_STATUSES:
        errors.append(f"terminal ticket {terminal_id} receipt is not a successful close")
    # A forced or accept-new terminal close is recorded in its receipt's
    # guard_weakening block; it does not disqualify that close as an authority.
    snapshots = manifest.get("snapshots")
    desired_records = [
        record
        for record in snapshots if isinstance(record, dict) and record.get("role") == "desired_program_model"
    ] if isinstance(snapshots, list) else []
    if len(desired_records) != 1:
        errors.append(
            f"terminal ticket {terminal_id} receipt must contain exactly one desired snapshot"
        )
        return errors
    snapshot_value = desired_records[0].get("snapshot")
    if not isinstance(snapshot_value, str) or not snapshot_value:
        return errors + [f"terminal ticket {terminal_id} desired snapshot path is missing"]
    snapshot_dir = Path(snapshot_value)
    if not snapshot_dir.is_absolute():
        snapshot_dir = repo_root / snapshot_dir
    receipt_dir = manifest_path.parent.resolve()
    expected_snapshot_dir = receipt_dir / "snapshots" / "desired_program_model"
    if snapshot_dir.resolve() != expected_snapshot_dir:
        errors.append(
            f"terminal ticket {terminal_id} desired snapshot is not the canonical "
            "snapshots/desired_program_model directory"
        )
        return errors
    errors.extend(validate_exact_snapshot(desired_dir, snapshot_dir))
    return errors


def close_ticket_workflow(
    repo_root: Path,
    spec_root: Path,
    *,
    dry_run: bool,
    summary: str = "",
    result_paths: list[Path] | None = None,
    workflow_name: str | None = None,
    history_entry: str = "closed-snapshot",
    accept_new: bool = False,
    emit_feedback: bool = True,
    force: bool = False,
) -> list[Path]:
    """Close the workflow. Under `force` (or SKILL_GATES=off) every refusal
    below except a missing desired tree becomes one warning line, and a
    divergent tree is accepted as if `--accept-new` had been passed."""
    force = gates_forced(force)
    resolved_spec_root = _resolve_spec_root(repo_root, spec_root)
    program_dir = resolved_spec_root / "program_model"
    current_dir = resolved_spec_root / "current"
    desired_dir = resolved_spec_root / "desired_program_model"
    ticket_plan = desired_dir / "ticket_plan.yaml"

    if not accept_new:
        current_errors = validate_equivalent(current_dir, desired_dir)
        program_errors = validate_equivalent(desired_dir, program_dir, label="program_model")
        convergence_errors = current_errors + program_errors
        errors = [
            *current_errors,
            *validate_ticket_plan_closed(ticket_plan, repo_root=repo_root, workflow=workflow_name),
            *program_errors,
        ]
        refuse_or_warn(
            errors,
            force=force,
            header="cannot close ticket workflow:",
            guidance=workflow_promotion_guidance(),
        )
        # A forced close over a DIVERGENT tree accepts desired as the outcome.
        # #177: only divergence takes that overwrite. A forced close over a
        # converged tree (forced past a receipt or ordinal gate) must leave
        # program_model/ exactly as it is.
        accept_new = bool(convergence_errors)

    plan = _load_yaml(ticket_plan)
    resolved_workflow = resolve_workflow_name(plan, workflow_name) if plan else (workflow_name or "")
    summary = summary_or_missing(summary)
    if resolved_workflow:
        refuse_or_warn(
            complexity_ledger_input_problems(
                resolved_spec_root,
                scope="workflow",
                scope_id=resolved_workflow,
                workflow=resolved_workflow,
                model_dir=desired_dir if accept_new else current_dir,
                input_path=complexity_ledger_input_path(resolved_spec_root, None, "workflow"),
            ),
            force=force,
            header="cannot close ticket workflow: complexity ledger input refused:",
        )
        print_unreviewed_ticket_feedback(resolved_spec_root, resolved_workflow)
    if dry_run:
        targets = ["closed-snapshot/manifest.json", "closed-snapshot/summary.md"]
        if emit_feedback:
            targets.append("results/skill_feedback.md")
        print_summary_preview(summary, targets)

    if accept_new:
        if not desired_dir.exists():
            raise SystemExit(f"cannot accept new workflow state: missing model directory: {desired_dir}")
        errors = validate_ticket_plan_closed(
            ticket_plan,
            repo_root=repo_root,
            workflow=workflow_name,
        )
        header = "cannot close ticket workflow:"
        if ticket_plan_has_retirements(ticket_plan):
            retirement_errors = validate_retirement_accept_new_authority(
                repo_root=repo_root,
                specs_dir=resolved_spec_root,
                desired_dir=desired_dir,
                plan=_load_yaml(ticket_plan),
                workflow=workflow_name,
            )
            if retirement_errors:
                errors.extend(retirement_errors)
                header = (
                    "cannot close ticket workflow with --accept-new: the plan contains "
                    "retired tickets, so desired state must exactly match the archived "
                    "desired snapshot of the terminal successful ticket:"
                )
        refuse_or_warn(
            errors,
            force=force,
            header=header,
            guidance="" if header != "cannot close ticket workflow:" else workflow_promotion_guidance(),
        )
        if not dry_run:
            for relative in promote_semantic_files(desired_dir, current_dir):
                print(f"accept-new current: {relative}")
            for relative in promote_semantic_files(desired_dir, program_dir):
                print(f"accept-new program_model: {relative}")
        else:
            print("would accept desired_program_model as the new current and program_model")

    if not dry_run:
        result = create_workflow_closed_snapshot(
            repo_root=repo_root,
            spec_root=spec_root,
            summary=summary,
            result_paths=result_paths or [],
            workflow=workflow_name,
            entry_name=history_entry,
            emit_feedback=emit_feedback,
            force=force,
        )
        print_commit_recommendation(result)
        # MF-017: migration.md Phase 6 calls the retro part of the workflow, not
        # optional polish. Workflow close records the filing status rather than
        # gating on it, but it must never be quiet about an unresolved retro:
        # current/ and desired/ are removed just below, so this is the last
        # moment the omission is cheap to fix.
        feedback = result.skill_feedback
        if feedback and not feedback.get("resolved"):
            print(
                "WARNING: skill feedback is unresolved at workflow close. "
                f"Fill in {feedback['path']} and file each finding as a ticket or PR "
                f"against {feedback['feedback_repository']}; the close history records this as not filed."
            )

    removed = [current_dir, desired_dir]
    for directory in removed:
        if dry_run:
            print(f"would remove {directory}")
        else:
            shutil.rmtree(directory)
            print(f"removed {directory}")
    return removed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd(), help="Repository root.")
    parser.add_argument("--spec-root", type=Path, default=Path("specs"), help="Spec root under the repository.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and print removals without deleting files.")
    parser.add_argument("--workflow-name", help="Override ticket_plan.yaml name/status.workflow for the history directory.")
    parser.add_argument("--history-entry", default="closed-snapshot", help="History entry name under the workflow directory.")
    parser.add_argument("--summary", default="", help="Human-readable summary for the closed workflow snapshot.")
    parser.add_argument("--result", action="append", type=Path, default=[], help="TLC, generated-case, adapter, or test result path to snapshot.")
    parser.add_argument(
        "--no-skill-feedback",
        action="store_true",
        help="Do not emit/append the references/migration.md Phase 6 skill-feedback retro into <spec-root>/results/skill_feedback.md.",
    )
    parser.add_argument(
        "--accept-new",
        action="store_true",
        help="Accept desired_program_model/ as the new current/ and program_model/: skip the semantic-equivalence checks and overwrite them from desired_program_model/ before the snapshot. Ticket receipts are still required; with retirement, desired must exactly match the terminal delivered ticket's archived desired snapshot.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Warn instead of refusing on status, receipt, convergence, and complexity-ledger gates; a divergent tree is accepted as with --accept-new. SKILL_GATES=off means the same. Recorded in the receipt.",
    )
    args = parser.parse_args()

    close_ticket_workflow(
        args.repo_root.resolve(),
        args.spec_root,
        dry_run=args.dry_run,
        summary=args.summary,
        result_paths=args.result,
        workflow_name=args.workflow_name,
        history_entry=args.history_entry,
        accept_new=args.accept_new,
        emit_feedback=not args.no_skill_feedback,
        force=args.force,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
