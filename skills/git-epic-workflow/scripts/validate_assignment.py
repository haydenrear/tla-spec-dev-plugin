#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "PyYAML>=6.0.2,<7",
# ]
# ///
"""Validate a rendered epic assignment block from an issue body.

The assignment block is written by `git-issue`, read by `git-issue-workflow`,
and specified by this skill (`references/epic-ticket.md`). Three copies of one
schema drift silently: a field added to the specification but not to the
renderer produces issues that parse fine and simply omit a policy, and the
ticket agent discovers it only by not having it. This validator is the single
mechanical check, so `references/epic-ticket.md` can be the schema's only owner.

Read an issue body (file or stdin) and check the marker-delimited block:

    uv run --script scripts/validate_assignment.py --assignment issue-body.md
    gh issue view 42 --json body -q .body | uv run --script scripts/validate_assignment.py
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import sys
from dataclasses import dataclass
from typing import Any, Sequence

import yaml


START_MARKER = "<!-- git-epic-workflow:assignment:start -->"
END_MARKER = "<!-- git-epic-workflow:assignment:end -->"
YAML_FENCE = re.compile(r"^ {0,3}```+\s*ya?ml\s*$", re.IGNORECASE)
CLOSING_FENCE = re.compile(r"^ {0,3}```+\s*$")
# `<epic-id>`, `<slug>`: an unrendered template placeholder. Requiring
# lowercase-and-dashes with no spaces keeps shell redirection (`cmd < file`)
# and comparisons out of the match.
PLACEHOLDER = re.compile(r"<[a-z][a-z0-9-]*>")
STABLE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
MISSING = object()

VERSION = 1
EPIC_BRANCH_PREFIX = "epic/"
REVIEW_MODE = "external"
REVIEW_STOPS_AFTER = "pr_open"
REVIEW_MERGED_BY = "epic-owner"
REVIEW_CADENCES = ("wave", "ticket", "milestone", "finalization-only")
DEFERMENT_MODES = ("batch", "ask", "inline")
DEFERMENT_BLOCKING = ("escalate", "ask")
GOAL_KINDS = ("perf", "eval", "integration", "quality")
CONTRIBUTIONS = ("direct", "enabling", "guard")
GUARD = "guard"
TICKET_ROLES = ("implementation", "evaluation")
EVALUATION = "evaluation"
NOT_APPLICABLE = "N/A"
# `--ticket SI-07`, `--ticket=SI-07`. Used to check that a command the
# assignment tells an agent to run names a workspace that exists.
TICKET_FLAG = re.compile(r"--ticket[=\s]+(\S+)")

EPIC_STRINGS = ("id", "workflow", "branch", "base_sha", "plan_commit", "default_branch")
TICKET_STRINGS = ("spec_id", "feature_branch", "worktree", "pr_base")
VALIDATION_FIELDS = (
    "tlc",
    "spec_unit",
    "repository_unit",
    "spec_graph",
    "toolchain_spec_workflow",
    "evidence_root",
)
# Fields whose value may be `N/A: reason` instead of a command.
EXCUSABLE = ("tlc", "repository_unit", "spec_graph", "toolchain_spec_workflow")
GOAL_STRINGS = ("statement", "metric", "baseline", "target", "expected_effect")


GATES_ENV = "SKILL_GATES"


class AssignmentError(Exception):
    """The body carries no assignment block that can be parsed at all."""


class Blocking(str):
    """A diagnostic that fails the run by default.

    Only what would send a ticket agent to the wrong branch, worktree, or
    ticket blocks. Every other diagnostic is advisory unless `strict` is set:
    a shape or policy slip is a note for the reviewer, not a reason to stop.
    """


@dataclass(frozen=True)
class AssignmentReport:
    errors: tuple[str, ...]
    warnings: tuple[str, ...]


def _gate(message: str, blocking: bool) -> str:
    return Blocking(message) if blocking else message


def extract_block(body: str) -> str:
    """Return the YAML source of the assignment block, or raise."""
    start = body.find(START_MARKER)
    if start < 0:
        raise AssignmentError(
            f"no assignment block: {START_MARKER!r} not found. An epic ticket "
            "issue must carry the marker-delimited block so an epic resume can "
            "rewrite the assignment without touching the issue's discovery"
        )
    end = body.find(END_MARKER, start)
    if end < 0:
        raise AssignmentError(
            f"assignment block opened but never closed: {END_MARKER!r} not found"
        )
    nested = body.find(START_MARKER, start + len(START_MARKER))
    if 0 <= nested < end:
        raise AssignmentError(
            "a second assignment start marker opens before the first block "
            "closes: an epic resume rewrote the block without replacing it"
        )

    inner = body[start + len(START_MARKER) : end]
    lines = inner.splitlines()
    opened: int | None = None
    for index, line in enumerate(lines):
        if YAML_FENCE.match(line):
            opened = index + 1
            break
    if opened is None:
        raise AssignmentError(
            "assignment block contains no ```yaml fence; the machine-readable "
            "assignment is what the ticket agent reads"
        )
    for index in range(opened, len(lines)):
        if CLOSING_FENCE.match(lines[index]):
            return "\n".join(lines[opened:index])
    raise AssignmentError("assignment YAML fence is never closed")


def parse_assignment(body: str) -> object:
    source = extract_block(body)
    try:
        return yaml.safe_load(source)
    except yaml.YAMLError as error:
        raise AssignmentError(f"assignment YAML does not parse: {error}") from error


def _placeholders(value: object, path: str, errors: list[str]) -> None:
    """An unrendered `<placeholder>` means the issue was never filled in."""
    if isinstance(value, str):
        found = PLACEHOLDER.findall(value)
        if found:
            errors.append(
                f"{path} still holds unrendered template placeholder(s) "
                f"{sorted(set(found))}: the assignment was copied but not filled in"
            )
    elif isinstance(value, dict):
        for key, item in value.items():
            _placeholders(item, f"{path}.{key}", errors)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _placeholders(item, f"{path}[{index}]", errors)


def _excuse_is_reasoned(value: str) -> bool:
    """True when an `N/A` carries an explanation of any punctuation style.

    `N/A: no TLA delta` and `N/A unless this repository is tla-spec-dev` are both
    reviewable; a bare `N/A` is the one that hides why a REQUIRED-adjacent entry
    was skipped.
    """
    remainder = value.strip()[len(NOT_APPLICABLE) :]
    return bool(remainder.lstrip(" \t:;,.-—–"))


def _require_str(
    mapping: dict[str, Any],
    path: str,
    field: str,
    errors: list[str],
    blocking: bool = False,
) -> str | None:
    value = mapping.get(field, MISSING)
    if value is MISSING:
        errors.append(_gate(f"{path}.{field} is required", blocking))
        return None
    if not isinstance(value, str) or not value.strip():
        errors.append(_gate(f"{path}.{field} must be a non-empty string", blocking))
        return None
    return value


def _require_int(
    mapping: dict[str, Any], path: str, field: str, errors: list[str], minimum: int = 1
) -> int | None:
    value = mapping.get(field, MISSING)
    if type(value) is not int or value < minimum:
        errors.append(f"{path}.{field} must be an integer >= {minimum}")
        return None
    return value


def _require_mapping(
    assignment: dict[str, Any], field: str, errors: list[str], blocking: bool = False
) -> dict[str, Any] | None:
    value = assignment.get(field, MISSING)
    if value is MISSING:
        errors.append(_gate(f"assignment must declare {field}", blocking))
        return None
    if not isinstance(value, dict):
        errors.append(_gate(f"{field} must be a mapping", blocking))
        return None
    return value


def _id_list(
    mapping: dict[str, Any], path: str, field: str, errors: list[str]
) -> list[str]:
    value = mapping.get(field, [])
    if value is None:
        return []
    if not isinstance(value, list):
        errors.append(f"{path}.{field} must be a list")
        return []
    ids: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not STABLE_ID.match(item.strip() or " "):
            errors.append(f"{path}.{field}[{index}] must be a stable ticket id")
            continue
        ids.append(item.strip())
    return ids


def _validate_epic(assignment: dict[str, Any], errors: list[str]) -> str | None:
    epic = _require_mapping(assignment, "epic", errors, blocking=True)
    if epic is None:
        return None
    for field in EPIC_STRINGS:
        _require_str(epic, "epic", field, errors, blocking=field == "branch")
    _require_int(epic, "epic", "schedule_revision", errors)

    branch = epic.get("branch")
    if isinstance(branch, str) and branch.strip():
        if not branch.startswith(EPIC_BRANCH_PREFIX):
            errors.append(
                f"epic.branch must name an epic integration branch "
                f"({EPIC_BRANCH_PREFIX}<slug>), not {branch!r}"
            )
        default_branch = epic.get("default_branch")
        if isinstance(default_branch, str) and branch.strip() == default_branch.strip():
            errors.append(Blocking(
                "epic.branch is the default branch: an epic integrates on its own "
                "branch and never dispatches tickets against the default branch"
            ))
        return branch.strip()
    return None


def _validate_ticket(
    assignment: dict[str, Any], epic_branch: str | None, errors: list[str]
) -> dict[str, Any] | None:
    ticket = _require_mapping(assignment, "ticket", errors, blocking=True)
    if ticket is None:
        return None
    for field in TICKET_STRINGS:
        _require_str(ticket, "ticket", field, errors, blocking=True)
    _require_int(ticket, "ticket", "wave", errors)
    _require_int(ticket, "ticket", "promotion_order", errors)

    spec_id = ticket.get("spec_id")
    if isinstance(spec_id, str) and spec_id.strip():
        if not STABLE_ID.match(spec_id.strip()):
            errors.append("ticket.spec_id must be a stable id")

    pr_base = ticket.get("pr_base")
    if (
        epic_branch is not None
        and isinstance(pr_base, str)
        and pr_base.strip() != epic_branch
    ):
        errors.append(Blocking(
            f"ticket.pr_base {pr_base!r} is not the epic branch {epic_branch!r}: "
            "the ticket PR would target the wrong base"
        ))

    role = ticket.get("role", MISSING)
    if role not in TICKET_ROLES:
        errors.append(f"ticket.role must be one of {list(TICKET_ROLES)}")

    depends_on = _id_list(ticket, "ticket", "depends_on", errors)
    blocks = _id_list(ticket, "ticket", "blocks", errors)
    if isinstance(spec_id, str):
        stripped = spec_id.strip()
        if stripped and stripped in depends_on:
            errors.append("ticket.depends_on lists this ticket itself")
        if stripped and stripped in blocks:
            errors.append("ticket.blocks lists this ticket itself")
    both = sorted(set(depends_on) & set(blocks))
    if both:
        errors.append(
            f"ticket lists {both} in both depends_on and blocks: the dependency "
            "cannot point in both directions"
        )

    predecessor = ticket.get("promotion_predecessor", None)
    if predecessor is not None:
        if not isinstance(predecessor, str) or not STABLE_ID.match(
            predecessor.strip() or " "
        ):
            errors.append(
                "ticket.promotion_predecessor must be null or a stable ticket id"
            )
        elif isinstance(spec_id, str) and predecessor.strip() == spec_id.strip():
            errors.append("ticket.promotion_predecessor is this ticket itself")

    # Lanes are whatever the plan names; a lane left out simply has no keys.
    conflicts = ticket.get("conflict_keys", {})
    if conflicts is not None and not isinstance(conflicts, dict):
        errors.append("ticket.conflict_keys must be a mapping")
    elif conflicts:
        for kind, value in conflicts.items():
            if value is not None and (
                not isinstance(value, list)
                or any(not isinstance(item, str) for item in value)
            ):
                errors.append(f"ticket.conflict_keys.{kind} must be a list of strings")
    return ticket


def _validate_goals(
    assignment: dict[str, Any],
    ticket: dict[str, Any] | None,
    errors: list[str],
    warnings: list[str],
) -> None:
    goals = assignment.get("goals", MISSING)
    if goals is MISSING:
        errors.append(
            "assignment must declare goals: every ticket relates to a goal an "
            "evaluation ticket decides (see references/epic-goals.md)"
        )
        return
    if not isinstance(goals, list) or not goals:
        errors.append("goals must be a non-empty list")
        return

    spec_id = None
    role = None
    if ticket is not None:
        raw = ticket.get("spec_id")
        spec_id = raw.strip() if isinstance(raw, str) else None
        role = ticket.get("role")

    declared: set[str] = set()
    for index, goal in enumerate(goals):
        path = f"goals[{index}]"
        if not isinstance(goal, dict):
            errors.append(f"{path} must be a mapping")
            continue
        goal_id = _require_str(goal, path, "goal", errors)
        if goal_id:
            declared.add(goal_id.strip())
        for field in GOAL_STRINGS:
            _require_str(goal, path, field, errors)
        if goal.get("kind", MISSING) not in GOAL_KINDS:
            errors.append(f"{path}.kind must be one of {list(GOAL_KINDS)}")

        signal = _require_str(goal, path, "local_signal", errors)
        if (
            signal
            and signal.strip().startswith(NOT_APPLICABLE)
            and not _excuse_is_reasoned(signal)
        ):
            errors.append(
                f"{path}.local_signal is {NOT_APPLICABLE!r} without a reason; "
                f"write '{NOT_APPLICABLE}: <why this ticket has no cheap signal>'"
            )

        decided_by = goal.get("decided_by", MISSING)
        if not isinstance(decided_by, dict):
            errors.append(f"{path}.decided_by must be a mapping")
        else:
            decider = _require_str(decided_by, f"{path}.decided_by", "ticket", errors)
            _require_str(decided_by, f"{path}.decided_by", "harness", errors)
            if (
                decider
                and spec_id
                and decider.strip() == spec_id
                and role != EVALUATION
            ):
                errors.append(
                    f"{path}.decided_by.ticket is this ticket, but role is "
                    f"{role!r}: a ticket cannot decide its own goal unless it is "
                    "the evaluation ticket"
                )

        contribution = goal.get("contribution", MISSING)
        if role == EVALUATION:
            # SIS-KICKOFF-F-01. Three places specified this field and only this
            # one disagreed. `references/epic-ticket.md` and `git-issue`'s
            # `references/epic-assignment.md` both SHOW `contribution: "guard"`
            # on the evaluation-ticket variant, and the canonical plan schema
            # requires a contribution on every goal relation — so `guard` is
            # authoritative and the warning that used to fire on it was the
            # drift. It fired once per owned goal: seven times for a correctly
            # rendered SI-08.
            if contribution is MISSING:
                warnings.append(
                    f"{path}.contribution is absent; an evaluation ticket copies "
                    f"{GUARD!r} from its canonical plan entry, which requires the "
                    "field on every goal relation"
                )
            elif contribution != GUARD:
                warnings.append(
                    f"{path}.contribution is {contribution!r} on an evaluation "
                    "ticket; it decides this goal rather than contributing to it, "
                    f"so the spelling is {GUARD!r}"
                )
        elif contribution not in CONTRIBUTIONS:
            errors.append(f"{path}.contribution must be one of {list(CONTRIBUTIONS)}")

    if role == EVALUATION and ticket is not None:
        owns = _id_list(ticket, "ticket", "owns_goals", errors)
        if not owns:
            errors.append(
                "ticket.role is 'evaluation' but owns_goals names no goal: an "
                "evaluation ticket exists to decide at least one goal"
            )
        unknown = sorted(set(owns) - declared)
        if unknown:
            errors.append(
                f"ticket.owns_goals names {unknown}, which the goals block does "
                "not declare"
            )
    elif ticket is not None and ticket.get("owns_goals"):
        errors.append(
            "ticket.owns_goals is set on a non-evaluation ticket; only the "
            "evaluation ticket owns goals"
        )


def _declares_no_model_delta(matrix: dict[str, Any]) -> bool:
    """Whether the matrix waives BOTH model checks, each with a reason.

    That pair is how an assignment says its ticket's spec workflow is NOT
    REQUIRED (git-issue's default). Only then may `spec_unit` be waived too.
    """
    for field in ("tlc", "spec_graph"):
        value = matrix.get(field)
        if not isinstance(value, str) or not value.strip().startswith(NOT_APPLICABLE):
            return False
        if not _excuse_is_reasoned(value):
            return False
    return True


def _validate_validation(assignment: dict[str, Any], errors: list[str]) -> None:
    matrix = _require_mapping(assignment, "validation", errors)
    if matrix is None:
        return
    for field in VALIDATION_FIELDS:
        value = _require_str(matrix, "validation", field, errors)
        if value is None:
            continue
        if value.strip().startswith(NOT_APPLICABLE):
            if field == "spec_unit" and _declares_no_model_delta(matrix):
                # A ticket whose spec workflow is NOT REQUIRED has no model
                # delta: it runs no TLC and no spec graph, and there are no
                # spec-unit cases of its own to run either. The waiver is
                # allowed only as a set, and only with a reason.
                if not _excuse_is_reasoned(value):
                    errors.append(
                        f"validation.{field} is {NOT_APPLICABLE!r} without a reason; "
                        f"write '{NOT_APPLICABLE}: <why>' so the waiver is reviewable"
                    )
            elif field == "spec_unit":
                errors.append(
                    f"validation.{field} is REQUIRED and cannot be "
                    f"{NOT_APPLICABLE!r} while validation.tlc or validation.spec_graph "
                    "names a command: a ticket that changes the model runs its "
                    "spec-unit cases"
                )
            elif field not in EXCUSABLE:
                errors.append(
                    f"validation.{field} is REQUIRED and cannot be "
                    f"{NOT_APPLICABLE!r}"
                )
            elif not _excuse_is_reasoned(value):
                errors.append(
                    f"validation.{field} is {NOT_APPLICABLE!r} without a reason; "
                    f"write '{NOT_APPLICABLE}: <why>' so the waiver is reviewable"
                )
    graphs = matrix.get("graphs", MISSING)
    if (
        not isinstance(graphs, list)
        or not graphs
        or any(not isinstance(item, str) or not item.strip() for item in graphs)
    ):
        errors.append("validation.graphs must be a non-empty list of graph names")


def _validate_review(assignment: dict[str, Any], errors: list[str]) -> None:
    review = _require_mapping(assignment, "review", errors)
    if review is None:
        return

    mode = review.get("mode", MISSING)
    if mode != REVIEW_MODE:
        errors.append(
            f"review.mode must be {REVIEW_MODE!r} (got {mode!r}): the field says "
            "the review is external TO THE TICKET AGENT, and "
            "git-issue-workflow's references/epic-ticket.md refuses any other "
            "value. Record the cadence in review.cadence, never in review.mode"
        )
    stops = review.get("ticket_agent_stops_after", MISSING)
    if stops != REVIEW_STOPS_AFTER:
        errors.append(
            f"review.ticket_agent_stops_after must be {REVIEW_STOPS_AFTER!r} "
            f"(got {stops!r}): the ticket agent opens the PR and stops"
        )

    merged_by = review.get("merged_by", MISSING)
    if merged_by is not MISSING and merged_by != REVIEW_MERGED_BY:
        errors.append(
            f"review.merged_by must be {REVIEW_MERGED_BY!r} (got {merged_by!r}): "
            "the epic owner merges ticket PRs into the epic branch"
        )

    cadence = review.get("cadence", MISSING)
    if cadence is not MISSING and cadence not in REVIEW_CADENCES:
        errors.append(f"review.cadence must be one of {list(REVIEW_CADENCES)}")

    artifact_root = review.get("artifact_root", MISSING)
    if artifact_root is not MISSING and (
        not isinstance(artifact_root, str) or not artifact_root.strip()
    ):
        errors.append("review.artifact_root must be a non-empty path string")


def _validate_deferment(assignment: dict[str, Any], errors: list[str]) -> None:
    deferment = assignment.get("deferment", MISSING)
    if deferment is MISSING:
        errors.append(
            "assignment must declare deferment: without it the ticket agent has "
            "no failure-case policy and will either fix out-of-scope defects or "
            "drop them. If the renderer omits this block, that is the drift this "
            "check exists to catch (see references/deferment.md)"
        )
        return
    if not isinstance(deferment, dict):
        errors.append("deferment must be a mapping")
        return

    if deferment.get("mode", MISSING) not in DEFERMENT_MODES:
        errors.append(f"deferment.mode must be one of {list(DEFERMENT_MODES)}")
    if deferment.get("blocking", MISSING) not in DEFERMENT_BLOCKING:
        errors.append(f"deferment.blocking must be one of {list(DEFERMENT_BLOCKING)}")
    _require_int(deferment, "deferment", "budget", errors)
    _require_str(deferment, "deferment", "backlog", errors)


def _validate_ticket_workspace(
    assignment: dict[str, Any],
    ticket: dict[str, Any] | None,
    repo_root: Path | None,
    warnings: list[str],
) -> None:
    """Warn when a command names `--ticket <id>` and no workspace exists.

    SIS-KICKOFF-F-03. Ten assignments told their agents to run
    `--ticket <id>` against a ticket-local workspace only the epic agent can
    create, and it had not created them. The agent discovers that by running
    the command and getting nothing useful back.

    `planning_rules.model_ownership_rule` already *promises* that the epic
    agent "scaffolds this ticket's desired and current before dispatch". This
    is that promise made checkable, one line, before the issue URL is handed
    out — which is the last moment it is cheap.

    It runs only where `specs/tickets` exists, so validating a saved body from
    outside the repository stays silent rather than warning about a tree it
    cannot see. Nothing here refuses; it is appended to `warnings`, which
    `--strict` does not promote.
    """
    if repo_root is None or ticket is None:
        return
    workspaces = repo_root / "specs" / "tickets"
    if not workspaces.is_dir():
        return
    matrix = assignment.get("validation")
    if not isinstance(matrix, dict):
        return

    raw_spec_id = ticket.get("spec_id")
    spec_id = raw_spec_id.strip() if isinstance(raw_spec_id, str) else None

    named: set[str] = set()
    for value in matrix.values():
        if isinstance(value, str):
            for match in TICKET_FLAG.finditer(value):
                named.add(match.group(1).strip().strip("\"'`<>"))

    for candidate in sorted(named):
        if not STABLE_ID.fullmatch(candidate):
            continue
        if (workspaces / candidate).is_dir():
            continue
        owner = "this ticket's" if candidate == spec_id else f"ticket {candidate}'s"
        warnings.append(
            f"validation names --ticket {candidate}, but {owner} workspace "
            f"specs/tickets/{candidate} does not exist on this branch; the epic "
            "agent scaffolds it before dispatch "
            "(planning_rules.model_ownership_rule)"
        )


def validate_assignment(
    assignment: object,
    expect_ticket: str | None = None,
    expect_epic_branch: str | None = None,
    strict: bool = False,
    repo_root: Path | None = None,
) -> AssignmentReport:
    """Return deterministic diagnostics; no errors means the block is usable.

    By default only `Blocking` diagnostics are errors and the rest are
    warnings. `strict` restores every rule as an error — except the
    ticket-workspace check, which is appended to `warnings` and is therefore
    advisory under every flag.
    """
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(assignment, dict):
        return AssignmentReport(("assignment must be a YAML mapping",), ())

    _placeholders(assignment, "assignment", errors)

    version = assignment.get("version", MISSING)
    if version != VERSION:
        errors.append(f"assignment version must be {VERSION} (got {version!r})")

    epic_branch = _validate_epic(assignment, errors)
    ticket = _validate_ticket(assignment, epic_branch, errors)
    _validate_goals(assignment, ticket, errors, warnings)
    _validate_validation(assignment, errors)
    _validate_review(assignment, errors)
    _validate_deferment(assignment, errors)
    _validate_ticket_workspace(assignment, ticket, repo_root, warnings)

    if expect_ticket is not None and ticket is not None:
        spec_id = ticket.get("spec_id")
        actual = spec_id.strip() if isinstance(spec_id, str) else None
        if actual != expect_ticket:
            errors.append(Blocking(
                f"ticket.spec_id is {actual!r} but this dispatch expects "
                f"{expect_ticket!r}"
            ))
    if expect_epic_branch is not None and epic_branch != expect_epic_branch:
        errors.append(Blocking(
            f"epic.branch is {epic_branch!r} but this dispatch expects "
            f"{expect_epic_branch!r}"
        ))

    if strict:
        return AssignmentReport(tuple(errors), tuple(warnings))
    blocking = tuple(error for error in errors if isinstance(error, Blocking))
    advisory = tuple(error for error in errors if not isinstance(error, Blocking))
    return AssignmentReport(blocking, advisory + tuple(warnings))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a rendered epic assignment block in an issue body. "
            "Reads stdin when --assignment is omitted or '-'."
        )
    )
    parser.add_argument(
        "--assignment",
        default="-",
        help="path to a file holding the issue body, or '-' for stdin",
    )
    parser.add_argument(
        "--expect-ticket",
        default=None,
        help="fail unless ticket.spec_id equals this id",
    )
    parser.add_argument(
        "--expect-epic-branch",
        default=None,
        help="fail unless epic.branch equals this branch",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="treat every diagnostic as an error, not only blocking ones",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=f"exit 0 even when errors remain (same as {GATES_ENV}=off)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="list every warning instead of a short summary",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help=(
            "repository holding specs/tickets, so a `--ticket <id>` the epic "
            "agent has not scaffolded is reported (default: working directory)"
        ),
    )
    return parser


WARNINGS_SHOWN = 3
LINE_LIMIT = 160


def _clip(message: str) -> str:
    return message if len(message) <= LINE_LIMIT else message[: LINE_LIMIT - 3] + "..."


def print_diagnostics(
    source: str, report: AssignmentReport, force: bool, verbose: bool
) -> None:
    """Print few, short lines: agents read this output into their context."""
    shown = report.warnings if verbose else report.warnings[:WARNINGS_SHOWN]
    for warning in shown:
        print(f"WARNING: {warning if verbose else _clip(warning)}", file=sys.stderr)
    hidden = len(report.warnings) - len(shown)
    if hidden:
        print(f"WARNING: {hidden} more (--verbose lists them)", file=sys.stderr)
    if report.errors:
        label = "FORCED past errors in" if force else "INVALID:"
        print(f"{label} {source}", file=sys.stderr)
        for error in report.errors:
            print(f"- {error if verbose else _clip(error)}", file=sys.stderr)


def gates_forced(flag: bool) -> bool:
    return flag or os.environ.get(GATES_ENV, "").strip().lower() in {"off", "0", "false"}


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    source = "<stdin>"
    if args.assignment == "-":
        body = sys.stdin.read()
    else:
        path = Path(args.assignment)
        source = str(path)
        try:
            body = path.read_text(encoding="utf-8")
        except OSError as error:
            print(f"ERROR: cannot read {path}: {error}", file=sys.stderr)
            return 2

    try:
        assignment = parse_assignment(body)
    except AssignmentError as error:
        print(f"ERROR: {source}: {error}", file=sys.stderr)
        return 2

    force = gates_forced(args.force)
    report = validate_assignment(
        assignment,
        expect_ticket=args.expect_ticket,
        expect_epic_branch=args.expect_epic_branch,
        strict=args.strict,
        repo_root=args.repo_root or Path.cwd(),
    )
    print_diagnostics(source, report, force, args.verbose)
    if report.errors and not force:
        return 1

    ticket = assignment.get("ticket") if isinstance(assignment, dict) else None
    ticket = ticket if isinstance(ticket, dict) else {}
    goals = assignment.get("goals") if isinstance(assignment, dict) else None
    goals = goals if isinstance(goals, list) else []
    goal_label = "goal" if len(goals) == 1 else "goals"
    print(
        f"OK: {source} carries a usable assignment for {ticket.get('spec_id')} "
        f"(wave {ticket.get('wave')}, role {ticket.get('role')}, "
        f"{len(goals)} {goal_label}, base {ticket.get('pr_base')})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
