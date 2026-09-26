#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "PyYAML>=6.0.2,<7",
# ]
# ///
"""Validate scheduling metadata in an epic ticket plan."""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
import os
from pathlib import Path
import re
import sys
from typing import Any, Sequence

import yaml


DEFAULT_PLAN = Path("specs/desired_program_model/ticket_plan.yaml")
STABLE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
MISSING = object()
DEFERMENT_MODES = ("batch", "ask", "inline")
DEFERMENT_BLOCKING = ("escalate", "ask")
REVIEW_CADENCES = ("wave", "ticket", "milestone", "finalization-only")
REVIEW_MERGES = ("owner", "human")
REVIEW_WALKTHROUGH = ("required", "on-request")
MILESTONE = "milestone"
GOAL_KINDS = ("perf", "eval", "integration", "quality")
GOAL_TEXT_FIELDS = ("statement", "metric", "harness", "target", "evidence_root")
CONTRIBUTIONS = ("direct", "enabling", "guard")
TICKET_ROLES = ("implementation", "evaluation")
EVALUATION = "evaluation"
UNMEASURED = "unmeasured"
RETIRED = "retired"
DELIVERED_STATUSES = {"accepted", "closed", "complete", "completed", "done"}
RETIREMENT_RESOLUTIONS = ("carried", "superseded", "abandoned")
GOAL_RETIREMENT_DISPOSITIONS = (
    "accepted_missed",
    "accepted_unmeasured",
    "carried",
)
RETIREMENT_FIELDS = frozenset(
    {
        "schedule_revision",
        "resolution",
        "reason",
        "decided_by",
        "decided_at",
        "receipt",
        "affected_goals",
        "successor_issue",
        "successor_workflow",
    }
)
GOAL_RETIREMENT_FIELDS = frozenset(
    {
        "goal",
        "disposition",
        "reason",
        "successor_issue",
        "successor_workflow",
    }
)


GATES_ENV = "SKILL_GATES"

# The blocks a wave-close review artifact carries once the epic agent is the
# one writer of the loop (`references/human-review.md` §3.4). Each entry is a
# label and the substrings that count as having written it, matched
# case-insensitively so a reworded heading still resolves.
#
# EVERY diagnostic these produce is appended to `warnings`, never to `errors`.
# That is not a convention, it is the mechanism: `validate_plan` splits
# `errors` into blocking and advisory and `--strict` promotes the advisory
# half, while `warnings` passes through both paths untouched. So there is no
# flag, and no combination of flags, that turns a missing block into a refusal
# — which is what `GOAL-no-new-gates` asks for, and the predecessor epic
# measured that a gate here reads to an agent as a stop.
WAVE_BLOCKS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("model delta applied", ("model delta",)),
    ("anchors placed", ("anchors placed", "anchor placed")),
    ("improvement-card row", ("improvement-card row", "improvement card row")),
    (
        "skill changes applied or declined",
        ("skill changes applied", "skill changes declined"),
    ),
    (
        "model corrections owed by merged tickets",
        ("model corrections owed", "corrections owed by merged"),
    ),
)
#: A wave-review directory. The trailing group is what `wave-11-12`,
#: `wave-13-15` and `wave-17-18` need: whenever two or more waves close
#: together the epic agent names the directory for the RANGE, and the original
#: `\Awave-(\d+)\Z` did not match any of them.
#:
#: EA-DF-07 / #386. The consequence was not a missed warning, it was a
#: MISLEADING clean run: the checker warned about waves 1-3, whose artifacts
#: predate the block rule, and said nothing whatever about the combined
#: directories -- not because they satisfied the rule but because it never
#: opened them. Three of the epic's eight review artifacts were in the
#: unchecked set, and all three did in fact carry 5/5 blocks, so the checker's
#: blindness and the artifacts' correctness were independent facts that
#: happened to agree. That is why nobody noticed.
WAVE_DIR = re.compile(r"\Awave-(\d+)(?:-(\d+))?\Z")


class Blocking(str):
    """A diagnostic that fails the plan by default.

    Only what makes the schedule unusable blocks: no tickets, unusable or
    duplicate IDs, dangling or cyclic dependencies. Every other diagnostic is
    advisory unless `strict` is set.
    """


@dataclass(frozen=True)
class PlanReport:
    errors: list[str]
    warnings: list[str]


@dataclass(frozen=True)
class GoalLink:
    goal: str
    contribution: str | None
    local_signal: str | None


@dataclass(frozen=True)
class Goal:
    id: str
    evaluation_ticket: object
    baseline_value: str | None


@dataclass(frozen=True)
class GoalRetirement:
    disposition: str
    reason: str
    successor_issue: str | None
    successor_workflow: str | None


@dataclass(frozen=True)
class Retirement:
    resolution: str
    affected_goals: dict[str, GoalRetirement]


@dataclass(frozen=True)
class Ticket:
    index: int
    id: str
    status: str
    depends_on: tuple[str, ...]
    blocks: tuple[str, ...]
    wave: int | None
    promotion_order: int | None
    promotion_predecessor: object
    conflict_keys: frozenset[tuple[str, str]]
    role: str
    goals: tuple[GoalLink, ...]
    owns_goals: object

    @property
    def retired(self) -> bool:
        return self.status == RETIRED

    @property
    def delivered(self) -> bool:
        return self.status in DELIVERED_STATUSES


def _ticket_label(index: int, raw_id: object) -> str:
    if isinstance(raw_id, str) and raw_id:
        return f"ticket {raw_id!r}"
    return f"ticket at index {index}"


def _id_list(
    raw: dict[str, Any], field: str, label: str, errors: list[str]
) -> tuple[str, ...]:
    value = raw.get(field, MISSING)
    if value is MISSING or value is None:
        return ()
    if not isinstance(value, list):
        errors.append(f"{label}: {field} must be a list")
        return ()

    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not STABLE_ID.fullmatch(item):
            errors.append(
                f"{label}: {field}[{index}] must be a stable ticket ID "
                "using only letters, digits, '.', '_' or '-'"
            )
            continue
        result.append(item)

    duplicates = sorted({item for item in result if result.count(item) > 1})
    if duplicates:
        errors.append(f"{label}: {field} contains duplicate IDs: {duplicates}")
    return tuple(result)


def _conflict_keys(
    raw: dict[str, Any], label: str, errors: list[str]
) -> frozenset[tuple[str, str]]:
    value = raw.get("conflict_keys", MISSING)
    if not isinstance(value, dict):
        errors.append(f"{label}: conflict_keys must be a mapping of lists")
        return frozenset()

    result: set[tuple[str, str]] = set()
    for category, keys in value.items():
        if not isinstance(category, str) or not category.strip():
            errors.append(f"{label}: conflict_keys categories must be non-empty strings")
            continue
        if not isinstance(keys, list):
            errors.append(f"{label}: conflict_keys.{category} must be a list")
            continue
        seen: set[str] = set()
        for index, key in enumerate(keys):
            if not isinstance(key, str) or not key.strip():
                errors.append(
                    f"{label}: conflict_keys.{category}[{index}] must be a "
                    "non-empty string"
                )
                continue
            if key in seen:
                errors.append(
                    f"{label}: conflict_keys.{category} contains duplicate key {key!r}"
                )
            seen.add(key)
            result.add((category, key))
    return frozenset(result)


def _goal_links(
    raw: dict[str, Any], label: str, errors: list[str]
) -> tuple[GoalLink, ...]:
    value = raw.get("goals", MISSING)
    if value is MISSING:
        return ()
    if not isinstance(value, list):
        errors.append(f"{label}: goals must be a list of goal relations")
        return ()

    links: list[GoalLink] = []
    seen: set[str] = set()
    for index, entry in enumerate(value):
        entry_label = f"{label}: goals[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{entry_label} must be a mapping")
            continue

        goal_id = entry.get("goal", MISSING)
        if not isinstance(goal_id, str) or not STABLE_ID.fullmatch(goal_id):
            errors.append(f"{entry_label}: goal must be a stable goal ID")
            continue
        if goal_id in seen:
            errors.append(f"{entry_label}: duplicate relation to goal {goal_id!r}")
            continue
        seen.add(goal_id)

        contribution = entry.get("contribution", MISSING)
        if contribution not in CONTRIBUTIONS:
            errors.append(
                f"{entry_label}: contribution must be one of {list(CONTRIBUTIONS)}"
            )
            contribution = None

        effect = entry.get("expected_effect", MISSING)
        if not isinstance(effect, str) or not effect.strip():
            errors.append(
                f"{entry_label}: expected_effect must state the result this ticket "
                "should produce, or 'none — enabling only'"
            )

        signal = entry.get("local_signal", MISSING)
        if not isinstance(signal, str) or not signal.strip():
            errors.append(
                f"{entry_label}: local_signal must be a command or 'N/A: <reason>'"
            )
            signal = None

        links.append(
            GoalLink(
                goal=goal_id,
                contribution=contribution if isinstance(contribution, str) else None,
                local_signal=signal if isinstance(signal, str) else None,
            )
        )
    return tuple(links)


def _parse_tickets(plan: object, errors: list[str]) -> dict[str, Ticket]:
    if not isinstance(plan, dict):
        errors.append(Blocking("plan root must be a mapping"))
        return {}
    raw_tickets = plan.get("tickets")
    if not isinstance(raw_tickets, list) or not raw_tickets:
        errors.append(Blocking("plan must contain a non-empty tickets list"))
        return {}

    tickets: dict[str, Ticket] = {}
    for index, raw in enumerate(raw_tickets):
        if not isinstance(raw, dict):
            errors.append(f"ticket at index {index} must be a mapping")
            continue

        raw_id = raw.get("id", MISSING)
        label = _ticket_label(index, raw_id)
        if not isinstance(raw_id, str) or not STABLE_ID.fullmatch(raw_id):
            errors.append(Blocking(
                f"{label}: id must be a stable string using only letters, digits, "
                "'.', '_' or '-' and must start with a letter or digit"
            ))
            continue
        if raw_id in tickets:
            errors.append(Blocking(f"duplicate ticket ID {raw_id!r}"))
            continue

        raw_status = raw.get("status", "planned")
        if not isinstance(raw_status, str) or not raw_status.strip():
            errors.append(f"{label}: status must be a non-empty string")
            status = "planned"
        else:
            status = raw_status.strip().lower()
        if status == RETIRED and raw_status != RETIRED:
            errors.append(
                f"{label}: retirement status must be written exactly as "
                f"{RETIRED!r}"
            )
        if status in RETIREMENT_RESOLUTIONS:
            errors.append(
                f"{label}: status {status!r} is not a retirement receipt; use "
                f"status: retired with retirement.resolution: {status}"
            )

        wave = raw.get("wave", MISSING)
        if type(wave) is not int or wave < 1:
            errors.append(f"{label}: wave must be a positive integer")
            parsed_wave = None
        else:
            parsed_wave = wave

        promotion_order = raw.get("promotion_order", MISSING)
        if type(promotion_order) is not int:
            errors.append(f"{label}: promotion_order must be an integer")
            parsed_order = None
        else:
            parsed_order = promotion_order

        predecessor = raw.get("promotion_predecessor", MISSING)
        if predecessor is not MISSING and predecessor is not None:
            if not isinstance(predecessor, str) or not STABLE_ID.fullmatch(predecessor):
                errors.append(
                    f"{label}: promotion_predecessor must be null or a stable ticket ID"
                )

        role = raw.get("role", "implementation")
        if role not in TICKET_ROLES:
            errors.append(f"{label}: role must be one of {list(TICKET_ROLES)}")
            role = "implementation"

        tickets[raw_id] = Ticket(
            index=index,
            id=raw_id,
            status=status,
            depends_on=_id_list(raw, "depends_on", label, errors),
            blocks=_id_list(raw, "blocks", label, errors),
            wave=parsed_wave,
            promotion_order=parsed_order,
            promotion_predecessor=predecessor,
            conflict_keys=_conflict_keys(raw, label, errors),
            role=role,
            goals=_goal_links(raw, label, errors),
            owns_goals=raw.get("owns_goals", MISSING),
        )
    return tickets


def _nonempty_string(
    value: object, label: str, field: str, errors: list[str]
) -> str | None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label}: {field} must be a non-empty string")
        return None
    return value.strip()


def _reject_unknown_fields(
    value: dict[object, object],
    allowed: frozenset[str],
    label: str,
    errors: list[str],
) -> None:
    unknown = sorted(str(field) for field in value if field not in allowed)
    if unknown:
        errors.append(f"{label}: unknown fields are forbidden: {unknown}")


def _schedule_revision(plan: object, errors: list[str]) -> int | None:
    if not isinstance(plan, dict):
        return None
    revision = plan.get("schedule_revision", MISSING)
    if type(revision) is not int or revision < 1:
        errors.append("schedule_revision must be a positive integer")
        return None
    return revision


def _workflow_name(plan: dict[str, Any]) -> object:
    name = plan.get("name", MISSING)
    if name is not MISSING:
        return name
    status = plan.get("status")
    if isinstance(status, dict):
        return status.get("workflow", MISSING)
    return MISSING


def _expected_retirement_receipt(workflow: str, ticket: Ticket) -> str:
    return (
        f"specs/.history/{workflow}/retired-ticket-{ticket.index:03d}-"
        f"{ticket.id}/manifest.json"
    )


def _ticket_goal_ids(ticket: Ticket, goals: dict[str, Goal]) -> set[str]:
    result = {link.goal for link in ticket.goals}
    if isinstance(ticket.owns_goals, list):
        result.update(goal for goal in ticket.owns_goals if isinstance(goal, str))
    result.update(
        goal.id for goal in goals.values() if goal.evaluation_ticket == ticket.id
    )
    return result


def _validate_retirements(
    plan: object,
    tickets: dict[str, Ticket],
    goals: dict[str, Goal],
    schedule_revision: int | None,
    errors: list[str],
) -> dict[str, Retirement]:
    """Validate explicit scope retirement without treating it as delivery."""
    if not isinstance(plan, dict):
        return {}
    raw_tickets = plan.get("tickets")
    if not isinstance(raw_tickets, list):
        return {}

    retired = [ticket for ticket in tickets.values() if ticket.retired]
    workflow_value = _workflow_name(plan)
    workflow = (
        workflow_value.strip()
        if isinstance(workflow_value, str) and workflow_value.strip()
        else None
    )
    if retired and (workflow is None or not STABLE_ID.fullmatch(workflow)):
        errors.append(
            "retired tickets require plan name (or status.workflow) to be a "
            "stable workflow ID"
        )

    result: dict[str, Retirement] = {}
    for ticket in tickets.values():
        raw = raw_tickets[ticket.index]
        if not isinstance(raw, dict):
            continue
        retirement = raw.get("retirement", MISSING)
        label = f"ticket {ticket.id!r}"

        if not ticket.retired:
            if retirement is not MISSING:
                errors.append(
                    f"{label}: retirement metadata is allowed only with status: retired"
                )
            continue
        if not isinstance(retirement, dict):
            errors.append(f"{label}: status retired requires a retirement mapping")
            continue
        _reject_unknown_fields(retirement, RETIREMENT_FIELDS, "retirement", errors)

        retired_revision = retirement.get("schedule_revision", MISSING)
        if type(retired_revision) is not int or retired_revision < 1:
            errors.append(
                f"{label}: retirement.schedule_revision must be a positive integer"
            )
        elif schedule_revision is not None and retired_revision > schedule_revision:
            errors.append(
                f"{label}: retirement.schedule_revision is the sealed decision "
                f"revision and cannot exceed current root schedule_revision "
                f"{schedule_revision}; got {retired_revision}"
            )

        resolution = retirement.get("resolution", MISSING)
        if resolution not in RETIREMENT_RESOLUTIONS:
            errors.append(
                f"{label}: retirement.resolution must be one of "
                f"{list(RETIREMENT_RESOLUTIONS)}"
            )
            parsed_resolution = ""
        else:
            parsed_resolution = resolution

        for field in ("reason", "decided_by", "decided_at"):
            _nonempty_string(retirement.get(field, MISSING), label, f"retirement.{field}", errors)

        successor_issue = retirement.get("successor_issue", MISSING)
        successor_workflow = retirement.get("successor_workflow", MISSING)
        if resolution == "carried":
            parsed_successor_issue = _nonempty_string(
                successor_issue, label, "retirement.successor_issue", errors
            )
            parsed_successor_workflow = _nonempty_string(
                successor_workflow, label, "retirement.successor_workflow", errors
            )
        else:
            parsed_successor_issue = None
            parsed_successor_workflow = None
            for field in ("successor_issue", "successor_workflow"):
                if field in retirement:
                    errors.append(
                        f"{label}: retirement.{field} must be absent unless "
                        "retirement.resolution is carried"
                    )

        receipt = retirement.get("receipt", MISSING)
        if workflow is not None and STABLE_ID.fullmatch(workflow):
            expected_receipt = _expected_retirement_receipt(workflow, ticket)
            if receipt != expected_receipt:
                errors.append(
                    f"{label}: retirement.receipt must preserve immutable ticket "
                    f"ordinal {ticket.index} at {expected_receipt!r}; got {receipt!r}"
                )
        elif not isinstance(receipt, str) or not receipt.strip():
            errors.append(f"{label}: retirement.receipt must be a non-empty path")

        raw_affected = retirement.get("affected_goals", MISSING)
        parsed_affected: dict[str, GoalRetirement] = {}
        if not isinstance(raw_affected, list):
            errors.append(f"{label}: retirement.affected_goals must be a list")
            raw_affected = []
        for index, entry in enumerate(raw_affected):
            entry_label = f"{label}: retirement.affected_goals[{index}]"
            if not isinstance(entry, dict):
                errors.append(f"{entry_label} must be a mapping")
                continue
            _reject_unknown_fields(
                entry, GOAL_RETIREMENT_FIELDS, entry_label, errors
            )
            goal_id = entry.get("goal", MISSING)
            if not isinstance(goal_id, str) or not STABLE_ID.fullmatch(goal_id):
                errors.append(f"{entry_label}: goal must be a stable goal ID")
                continue
            if goal_id in parsed_affected:
                errors.append(f"{entry_label}: duplicate goal {goal_id!r}")
                continue
            if goal_id not in goals:
                errors.append(f"{entry_label}: unknown goal {goal_id!r}")

            disposition = entry.get("disposition", MISSING)
            if disposition not in GOAL_RETIREMENT_DISPOSITIONS:
                errors.append(
                    f"{entry_label}: disposition must be one of "
                    f"{list(GOAL_RETIREMENT_DISPOSITIONS)}"
                )
                parsed_disposition = ""
            else:
                parsed_disposition = disposition
            reason = _nonempty_string(
                entry.get("reason", MISSING), entry_label, "reason", errors
            ) or ""
            goal_successor_issue = entry.get("successor_issue", MISSING)
            goal_successor_workflow = entry.get("successor_workflow", MISSING)
            if disposition == "carried":
                goal_successor_issue = _nonempty_string(
                    goal_successor_issue, entry_label, "successor_issue", errors
                )
                goal_successor_workflow = _nonempty_string(
                    goal_successor_workflow,
                    entry_label,
                    "successor_workflow",
                    errors,
                )
            else:
                goal_successor_issue = None
                goal_successor_workflow = None
                for field in ("successor_issue", "successor_workflow"):
                    if field in entry:
                        errors.append(
                            f"{entry_label}: {field} must be absent unless "
                            "disposition is carried"
                        )

            if resolution != "carried":
                if disposition == "carried":
                    errors.append(
                        f"{entry_label}: carried disposition contradicts ticket "
                        f"retirement.resolution {resolution!r}"
                    )
                for field in ("successor_issue", "successor_workflow"):
                    if field in entry:
                        errors.append(
                            f"{entry_label}: {field} must be absent when ticket "
                            "retirement.resolution is not carried"
                        )
            elif disposition != "carried":
                errors.append(
                    f"{entry_label}: disposition must be carried when ticket "
                    "retirement.resolution is carried"
                )
            elif (
                goal_successor_issue,
                goal_successor_workflow,
            ) != (parsed_successor_issue, parsed_successor_workflow):
                errors.append(
                    f"{entry_label}: carried successor must exactly match ticket "
                    "retirement successor_issue/successor_workflow"
                )

            parsed_affected[goal_id] = GoalRetirement(
                disposition=parsed_disposition,
                reason=reason,
                successor_issue=goal_successor_issue,
                successor_workflow=goal_successor_workflow,
            )

        expected_goals = _ticket_goal_ids(ticket, goals)
        actual_goals = set(parsed_affected)
        if actual_goals != expected_goals:
            errors.append(
                f"{label}: retirement.affected_goals must exactly preserve every "
                f"goal relation/ownership; expected {sorted(expected_goals)}, got "
                f"{sorted(actual_goals)}"
            )

        result[ticket.id] = Retirement(
            resolution=parsed_resolution,
            affected_goals=parsed_affected,
        )
    return result


def _find_dependency_cycle(tickets: dict[str, Ticket]) -> list[str] | None:
    state = {ticket_id: 0 for ticket_id in tickets}
    stack: list[str] = []

    def visit(ticket_id: str) -> list[str] | None:
        state[ticket_id] = 1
        stack.append(ticket_id)
        for dependency in sorted(tickets[ticket_id].depends_on):
            if dependency not in tickets:
                continue
            if state[dependency] == 0:
                cycle = visit(dependency)
                if cycle:
                    return cycle
            elif state[dependency] == 1:
                start = stack.index(dependency)
                return stack[start:] + [dependency]
        stack.pop()
        state[ticket_id] = 2
        return None

    for ticket_id in sorted(tickets):
        if state[ticket_id] == 0:
            cycle = visit(ticket_id)
            if cycle:
                return cycle
    return None


def _validate_dependency_graph(tickets: dict[str, Ticket], errors: list[str]) -> None:
    non_retired = {
        ticket_id: ticket
        for ticket_id, ticket in tickets.items()
        if not ticket.retired
    }
    retired_ids = {ticket_id for ticket_id, ticket in tickets.items() if ticket.retired}
    expected_blocks: dict[str, set[str]] = {
        ticket_id: set() for ticket_id in non_retired
    }

    # A retirement keeps the original schedule entry as history. Its edges no
    # longer participate in readiness, but deleting their endpoint would still
    # rewrite that history, so retain basic identity checks.
    for ticket_id in retired_ids:
        ticket = tickets[ticket_id]
        for field, references in (
            ("depends_on", ticket.depends_on),
            ("blocks", ticket.blocks),
        ):
            for reference in references:
                if reference == ticket.id:
                    errors.append(f"ticket {ticket.id!r}: cannot {field} itself")
                elif reference not in tickets:
                    errors.append(
                        f"ticket {ticket.id!r}: retired {field} references unknown "
                        f"ticket {reference!r}; retired entries preserve original IDs"
                    )

    for ticket in non_retired.values():
        for dependency in ticket.depends_on:
            if dependency == ticket.id:
                errors.append(f"ticket {ticket.id!r}: cannot depend on itself")
            elif dependency not in tickets:
                errors.append(Blocking(
                    f"ticket {ticket.id!r}: depends_on references unknown ticket "
                    f"{dependency!r}"
                ))
            elif dependency in retired_ids:
                if not ticket.delivered:
                    errors.append(
                        f"ticket {ticket.id!r}: non-delivered depends_on cannot "
                        f"reference retired ticket {dependency!r}; remove or retire "
                        "the dependent"
                    )
            else:
                expected_blocks[dependency].add(ticket.id)
                dependency_ticket = tickets[dependency]
                if (
                    ticket.wave is not None
                    and dependency_ticket.wave is not None
                    and dependency_ticket.wave >= ticket.wave
                ):
                    errors.append(
                        f"ticket {ticket.id!r}: dependency {dependency!r} is in wave "
                        f"{dependency_ticket.wave}, which is not earlier than wave "
                        f"{ticket.wave}"
                    )

        for blocked in ticket.blocks:
            if blocked == ticket.id:
                errors.append(f"ticket {ticket.id!r}: cannot block itself")
            elif blocked not in tickets:
                errors.append(
                    f"ticket {ticket.id!r}: blocks references unknown ticket {blocked!r}"
                )
            elif blocked in retired_ids:
                if not ticket.delivered:
                    errors.append(
                        f"ticket {ticket.id!r}: non-delivered blocks cannot reference "
                        f"retired ticket {blocked!r}"
                    )

    for ticket in non_retired.values():
        actual = {blocked for blocked in ticket.blocks if blocked in non_retired}
        expected = expected_blocks[ticket.id]
        if actual != expected:
            errors.append(
                f"ticket {ticket.id!r}: blocks must be the exact reverse of "
                f"depends_on; expected {sorted(expected)}, got {sorted(actual)}"
            )

    cycle = _find_dependency_cycle(non_retired)
    if cycle:
        errors.append(Blocking(f"dependency cycle detected: {' -> '.join(cycle)}"))


def _validate_conflicts(tickets: dict[str, Ticket], errors: list[str]) -> None:
    by_wave: dict[int, list[Ticket]] = defaultdict(list)
    for ticket in tickets.values():
        if not ticket.retired and ticket.wave is not None:
            by_wave[ticket.wave].append(ticket)

    for wave, wave_tickets in sorted(by_wave.items()):
        ordered = sorted(wave_tickets, key=lambda ticket: ticket.id)
        for left_index, left in enumerate(ordered):
            for right in ordered[left_index + 1 :]:
                overlap = sorted(left.conflict_keys & right.conflict_keys)
                if overlap:
                    rendered = [f"{category}:{key}" for category, key in overlap]
                    errors.append(
                        f"wave {wave}: tickets {left.id!r} and {right.id!r} share "
                        f"conflict keys {rendered}"
                    )


def _render_predecessor(value: object) -> str:
    if value is MISSING:
        return "<missing>"
    return repr(value)


def _validate_promotion_lane(tickets: dict[str, Ticket], errors: list[str]) -> None:
    orders: dict[int, list[str]] = defaultdict(list)
    for ticket in tickets.values():
        if ticket.promotion_order is not None:
            orders[ticket.promotion_order].append(ticket.id)
        if ticket.retired:
            predecessor = ticket.promotion_predecessor
            if isinstance(predecessor, str) and predecessor not in tickets:
                errors.append(
                    f"ticket {ticket.id!r}: retired promotion_predecessor references "
                    f"unknown ticket {predecessor!r}; retired entries preserve "
                    "original IDs"
                )
            continue
        predecessor = ticket.promotion_predecessor
        if isinstance(predecessor, str):
            if predecessor == ticket.id:
                errors.append(
                    f"ticket {ticket.id!r}: promotion_predecessor cannot name itself"
                )
            elif predecessor not in tickets:
                errors.append(
                    f"ticket {ticket.id!r}: promotion_predecessor references unknown "
                    f"ticket {predecessor!r}"
                )
            elif tickets[predecessor].retired and not ticket.delivered:
                errors.append(
                    f"ticket {ticket.id!r}: non-delivered promotion_predecessor "
                    f"cannot reference retired ticket {predecessor!r}; point to the "
                    "previous non-retired ticket"
                )

    duplicate_orders = {
        order: sorted(ticket_ids)
        for order, ticket_ids in orders.items()
        if len(ticket_ids) > 1
    }
    for order, ticket_ids in sorted(duplicate_orders.items()):
        errors.append(
            f"promotion_order {order} is not unique; used by tickets {ticket_ids}"
        )

    active = {
        ticket_id: ticket
        for ticket_id, ticket in tickets.items()
        if not ticket.retired
    }
    for ticket in active.values():
        if ticket.promotion_order is None:
            continue
        for dependency in ticket.depends_on:
            dependency_ticket = active.get(dependency)
            if dependency_ticket is None or dependency_ticket.promotion_order is None:
                continue
            if dependency_ticket.promotion_order >= ticket.promotion_order:
                errors.append(
                    "promotion_order is not a topological extension: dependency "
                    f"{dependency!r} ({dependency_ticket.promotion_order}) must precede "
                    f"ticket {ticket.id!r} ({ticket.promotion_order})"
                )

    active_orders = {
        ticket.promotion_order
        for ticket in active.values()
        if ticket.promotion_order is not None
    }
    if len(active_orders) != len(active) or duplicate_orders:
        return

    lane = sorted(
        active.values(), key=lambda ticket: ticket.promotion_order
    )  # type: ignore[arg-type]
    for index, ticket in enumerate(lane):
        expected = None if index == 0 else lane[index - 1].id
        actual = ticket.promotion_predecessor
        if actual is MISSING:
            errors.append(
                f"ticket {ticket.id!r}: promotion_predecessor is required; "
                f"expected {_render_predecessor(expected)}"
            )
        elif (
            actual != expected
            and not (
                ticket.delivered
                and isinstance(actual, str)
                and actual in tickets
                and tickets[actual].retired
            )
        ):
            errors.append(
                f"ticket {ticket.id!r}: promotion_predecessor must be "
                f"{_render_predecessor(expected)}; got {_render_predecessor(actual)}"
            )


def _baseline_value(
    raw: object, label: str, errors: list[str]
) -> str | None:
    """Accept either a `{value: ...}` mapping or a bare measured string."""
    if raw is MISSING or raw is None:
        return None
    if isinstance(raw, str):
        return raw.strip() or None
    if not isinstance(raw, dict):
        errors.append(f"{label}: baseline must be a mapping with a value, or a string")
        return None
    value = raw.get("value")
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _parse_goals(
    plan: object, errors: list[str], warnings: list[str]
) -> dict[str, Goal]:
    """Goals are agreed with the user, so their absence warns rather than fails."""
    if not isinstance(plan, dict):
        return {}

    raw_goals = plan.get("epic_goals", MISSING)
    if raw_goals is MISSING or raw_goals == []:
        waiver = plan.get("goals_waived", MISSING)
        if isinstance(waiver, str) and waiver.strip():
            warnings.append(
                f"epic_goals is waived: {waiver.strip()}; no evaluation ticket will "
                "decide this epic's outcome"
            )
        else:
            warnings.append(
                "plan declares no epic_goals; ask the user what should be measurably "
                "better, add the evaluation/perf ticket that decides it, and relate "
                "every ticket to it (see references/goals-and-evaluation.md)"
            )
        return {}

    if not isinstance(raw_goals, list):
        errors.append("epic_goals must be a list of goals")
        return {}

    goals: dict[str, Goal] = {}
    for index, raw in enumerate(raw_goals):
        label = f"epic_goals[{index}]"
        if not isinstance(raw, dict):
            errors.append(f"{label} must be a mapping")
            continue

        goal_id = raw.get("id", MISSING)
        if not isinstance(goal_id, str) or not STABLE_ID.fullmatch(goal_id):
            errors.append(f"{label}: id must be a stable goal ID")
            continue
        if goal_id in goals:
            errors.append(f"duplicate goal ID {goal_id!r}")
            continue
        label = f"goal {goal_id!r}"

        if raw.get("kind", MISSING) not in GOAL_KINDS:
            errors.append(f"{label}: kind must be one of {list(GOAL_KINDS)}")
        for field in GOAL_TEXT_FIELDS:
            value = raw.get(field, MISSING)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{label}: {field} must be a non-empty string")

        baseline = _baseline_value(raw.get("baseline", MISSING), label, errors)
        if baseline is None or baseline.lower() == UNMEASURED:
            warnings.append(
                f"{label}: baseline is unmeasured; measure it on the epic branch "
                "before behavioral tickets land, or schedule a wave-1 harness ticket"
            )
            baseline = None

        evaluation_ticket = raw.get("evaluation_ticket", MISSING)
        if evaluation_ticket is MISSING or not isinstance(evaluation_ticket, str):
            errors.append(
                f"{label}: evaluation_ticket must name the ticket that decides this goal"
            )

        goals[goal_id] = Goal(
            id=goal_id,
            evaluation_ticket=evaluation_ticket,
            baseline_value=baseline,
        )
    return goals


def _ancestors(tickets: dict[str, Ticket], start: str) -> set[str]:
    """Tickets `start` transitively depends on; cycle-safe."""
    seen: set[str] = set()
    stack = [start]
    while stack:
        current = stack.pop()
        ticket = tickets.get(current)
        if ticket is None:
            continue
        for dependency in ticket.depends_on:
            if dependency in seen or dependency not in tickets:
                continue
            seen.add(dependency)
            stack.append(dependency)
    return seen


def _validate_owns_goals(
    ticket: Ticket, goals: dict[str, Goal], errors: list[str]
) -> None:
    if ticket.owns_goals is MISSING:
        return
    if not isinstance(ticket.owns_goals, list):
        errors.append(f"ticket {ticket.id!r}: owns_goals must be a list of goal IDs")
        return
    for goal_id in ticket.owns_goals:
        if not isinstance(goal_id, str) or goal_id not in goals:
            errors.append(
                f"ticket {ticket.id!r}: owns_goals references unknown goal {goal_id!r}"
            )
            continue
        if goals[goal_id].evaluation_ticket != ticket.id:
            errors.append(
                f"ticket {ticket.id!r}: owns_goals lists {goal_id!r}, but that goal's "
                f"evaluation_ticket is {goals[goal_id].evaluation_ticket!r}"
            )
    owned = {
        goal.id for goal in goals.values() if goal.evaluation_ticket == ticket.id
    }
    declared = {goal for goal in ticket.owns_goals if isinstance(goal, str)}
    missing = sorted(owned - declared)
    if missing:
        errors.append(
            f"ticket {ticket.id!r}: owns_goals must list every goal it decides; "
            f"missing {missing}"
        )


def _validate_goal_alignment(
    goals: dict[str, Goal],
    tickets: dict[str, Ticket],
    retirements: dict[str, Retirement],
    errors: list[str],
    warnings: list[str],
) -> None:
    if not goals:
        return

    retirement_impacts: dict[str, list[tuple[Ticket, GoalRetirement]]] = defaultdict(list)
    for ticket_id, retirement in retirements.items():
        ticket = tickets[ticket_id]
        for goal_id, disposition in retirement.affected_goals.items():
            if goal_id in goals:
                retirement_impacts[goal_id].append((ticket, disposition))

    undisposed_goals = set(goals) - set(retirement_impacts)
    has_live_evaluation_ticket = any(
        ticket.role == EVALUATION and not ticket.retired
        for ticket in tickets.values()
    )
    if undisposed_goals and not has_live_evaluation_ticket:
        warnings.append(
            "no ticket declares role: evaluation; schedule a terminal "
            "evaluation/perf/integration ticket that runs each goal harness on the "
            "integrated epic and decides it"
        )

    contributors: dict[str, list[Ticket]] = defaultdict(list)
    associated: dict[str, list[Ticket]] = defaultdict(list)
    for ticket in sorted(tickets.values(), key=lambda item: item.id):
        _validate_owns_goals(ticket, goals, errors)

        if not ticket.goals:
            errors.append(
                f"ticket {ticket.id!r}: must relate to at least one epic goal so its "
                "agent knows which measured outcome the work serves"
            )
            continue

        for link in ticket.goals:
            if link.goal not in goals:
                errors.append(
                    f"ticket {ticket.id!r}: goals references unknown goal {link.goal!r}"
                )
                continue
            associated[link.goal].append(ticket)
            if link.contribution == "direct":
                if not ticket.retired and ticket.role != EVALUATION and (
                    link.local_signal is None
                    or link.local_signal.strip().upper().startswith("N/A")
                ):
                    warnings.append(
                        f"ticket {ticket.id!r}: direct contribution to {link.goal!r} "
                        "has no local signal; the agent cannot tell whether its change "
                        "moved the metric until finalization"
                    )
            # A goal's own decider never counts as a contributor to it, even when
            # the plan has not marked its role yet.
            if (
                not ticket.retired
                and ticket.role != EVALUATION
                and goals[link.goal].evaluation_ticket != ticket.id
            ):
                contributors[link.goal].append(ticket)

    for goal_id, goal in sorted(goals.items()):
        impacts = retirement_impacts.get(goal_id, [])
        if impacts:
            dispositions = {impact.disposition for _, impact in impacts}
            if len(dispositions) != 1:
                errors.append(
                    f"goal {goal_id!r}: retired tickets disagree on affected-goal "
                    f"disposition: {sorted(dispositions)}"
                )
            carried_targets = {
                (impact.successor_issue, impact.successor_workflow)
                for _, impact in impacts
                if impact.disposition == "carried"
            }
            if len(carried_targets) > 1:
                errors.append(
                    f"goal {goal_id!r}: carried retirement dispositions must name "
                    "one successor issue/workflow"
                )

            evaluator_id = goal.evaluation_ticket
            evaluator = tickets.get(evaluator_id) if isinstance(evaluator_id, str) else None
            if (
                evaluator is not None
                and not evaluator.retired
                and not evaluator.delivered
            ):
                retired_ids = sorted(ticket.id for ticket, _ in impacts)
                errors.append(
                    f"goal {goal_id!r}: active evaluation ticket {evaluator.id!r} "
                    f"cannot decide retired work {retired_ids}; "
                    "decide with the owner whether it still measures this goal"
                )

            active_associations = sorted(
                ticket.id
                for ticket in associated.get(goal_id, [])
                if not ticket.retired and not ticket.delivered
            )
            if active_associations:
                errors.append(
                    f"goal {goal_id!r}: retirement disposition conflicts with active "
                    f"tickets {active_associations}; they can proceed -- note the partial "
                    "retirement in the epic PR"
                )
            continue

        goal_contributors = contributors.get(goal_id, [])
        if not goal_contributors:
            errors.append(
                f"goal {goal_id!r}: no implementation ticket contributes to it; "
                "schedule the work or drop the goal"
            )

        evaluator_id = goal.evaluation_ticket
        if not isinstance(evaluator_id, str):
            continue
        evaluator = tickets.get(evaluator_id)
        if evaluator is None:
            errors.append(
                f"goal {goal_id!r}: evaluation_ticket references unknown ticket "
                f"{evaluator_id!r}"
            )
            continue
        if evaluator.retired:
            errors.append(
                f"goal {goal_id!r}: retired evaluation_ticket {evaluator_id!r} must "
                "record this goal in retirement.affected_goals"
            )
            continue
        if evaluator.role != EVALUATION and has_live_evaluation_ticket:
            errors.append(
                f"goal {goal_id!r}: evaluation_ticket {evaluator_id!r} must declare "
                "role: evaluation"
            )

        active_tickets = {
            ticket_id: ticket
            for ticket_id, ticket in tickets.items()
            if not ticket.retired
        }
        evaluator_ancestors = _ancestors(active_tickets, evaluator_id)
        for contributor in goal_contributors:
            if contributor.id not in evaluator_ancestors:
                errors.append(
                    f"goal {goal_id!r}: evaluation ticket {evaluator_id!r} must depend "
                    f"on contributor {contributor.id!r}, directly or transitively, so "
                    "the measurement runs on the integrated result"
                )
            if (
                evaluator.promotion_order is not None
                and contributor.promotion_order is not None
                and evaluator.promotion_order <= contributor.promotion_order
            ):
                errors.append(
                    f"goal {goal_id!r}: evaluation ticket {evaluator_id!r} "
                    f"({evaluator.promotion_order}) must promote after contributor "
                    f"{contributor.id!r} ({contributor.promotion_order})"
                )


def _validate_deferment_policy(plan: object, errors: list[str]) -> None:
    """The policy is agreed with the user at epic creation, so require it here."""
    if not isinstance(plan, dict):
        return

    policy = plan.get("deferment_policy", MISSING)
    if policy is MISSING:
        errors.append(
            "plan must declare deferment_policy; agree the failure-case policy "
            "with the user before dispatch (see references/deferment.md)"
        )
        return
    if not isinstance(policy, dict):
        errors.append("deferment_policy must be a mapping")
        return

    mode = policy.get("mode", MISSING)
    if mode not in DEFERMENT_MODES:
        errors.append(
            f"deferment_policy.mode must be one of {list(DEFERMENT_MODES)}"
        )

    blocking = policy.get("blocking", MISSING)
    if blocking not in DEFERMENT_BLOCKING:
        errors.append(
            f"deferment_policy.blocking must be one of {list(DEFERMENT_BLOCKING)}"
        )

    budget = policy.get("budget", MISSING)
    if type(budget) is not int or budget < 1:
        errors.append("deferment_policy.budget must be a positive integer")

    backlog = policy.get("backlog", MISSING)
    if not isinstance(backlog, str) or not backlog.strip():
        errors.append("deferment_policy.backlog must be a non-empty path string")


def _validate_review_policy(
    plan: object, errors: list[str], warnings: list[str]
) -> None:
    """Warn on an absent policy; reject a malformed one.

    Absence warns rather than fails because an epic planned before this block
    existed is not invalid. It still warns every run: at finalization a review
    nobody chose to skip cannot be told apart from one that never happened, and
    this block is the only place that choice is recorded.
    """
    if not isinstance(plan, dict):
        return

    policy = plan.get("review_policy", MISSING)
    if policy is MISSING:
        warnings.append(
            "plan declares no review_policy; agree the review cadence, the gate, "
            "and who merges ticket PRs with the user "
            "(see references/human-review.md)"
        )
        return
    if not isinstance(policy, dict):
        errors.append("review_policy must be a mapping")
        return

    cadence = policy.get("cadence", MISSING)
    if cadence not in REVIEW_CADENCES:
        errors.append(f"review_policy.cadence must be one of {list(REVIEW_CADENCES)}")

    gate = policy.get("gate", MISSING)
    if type(gate) is not bool:
        errors.append("review_policy.gate must be a boolean")

    merges = policy.get("merges", MISSING)
    if merges not in REVIEW_MERGES:
        errors.append(f"review_policy.merges must be one of {list(REVIEW_MERGES)}")

    artifact_root = policy.get("artifact_root", MISSING)
    if not isinstance(artifact_root, str) or not artifact_root.strip():
        errors.append("review_policy.artifact_root must be a non-empty path string")

    walkthrough = policy.get("walkthrough", MISSING)
    if walkthrough not in REVIEW_WALKTHROUGH:
        errors.append(
            f"review_policy.walkthrough must be one of {list(REVIEW_WALKTHROUGH)}"
        )

    milestones = policy.get("milestones", [])
    if not isinstance(milestones, list) or any(
        type(wave) is not int or wave < 1 for wave in milestones
    ):
        errors.append(
            "review_policy.milestones must be a list of positive wave numbers"
        )
    elif cadence == MILESTONE and not milestones:
        errors.append(
            "review_policy.milestones must name at least one wave when cadence is "
            f"{MILESTONE!r}"
        )
    elif cadence != MILESTONE and milestones:
        errors.append(
            "review_policy.milestones is only meaningful when cadence is "
            f"{MILESTONE!r}"
        )

    if gate is False or cadence == "finalization-only":
        warnings.append(
            "review_policy waives the between-waves review gate; the epic PR must "
            "say so, and every implicit decision and guardrail override still "
            "needs the user's answer before close"
        )


def _validate_wave_artifacts(
    plan: object, tickets: dict[str, "Ticket"], repo_root: Path | None, warnings: list[str]
) -> None:
    """Warn — never error — when a committed wave artifact lacks a block.

    The epic agent is the one writer of the loop, so the wave-close artifact is
    where it shows what it applied: the model delta, the anchors it placed, the
    improvement-card row, the disposition of every proposed skill change, and
    the model corrections merged tickets still owe it. A block that is absent
    is a step no reader can tell apart from a step that was skipped, which is
    the same reason `review_policy` is recorded at all.

    Nothing here refuses, under any flag — see `WAVE_BLOCKS`. Waves that
    predate the block schema warn exactly as they should: they are the
    baseline shape, and the warning is what measures the change.
    """
    if not isinstance(plan, dict) or repo_root is None:
        return
    policy = plan.get("review_policy")
    if not isinstance(policy, dict):
        return
    artifact_root = policy.get("artifact_root")
    if not isinstance(artifact_root, str) or not artifact_root.strip():
        return
    root = repo_root / artifact_root.strip()
    if not root.is_dir():
        # Before the first wave closes there is nothing to read, and a plan
        # validated outside its own repository is not this check's business.
        # Saying nothing is correct in both cases.
        return

    waves = []
    covered: set[int] = set()
    for path in root.iterdir():
        match = WAVE_DIR.fullmatch(path.name)
        if path.is_dir() and match:
            first = int(match.group(1))
            last = int(match.group(2)) if match.group(2) else first
            waves.append((first, path))
            # A combined directory covers the whole inclusive range it names,
            # so a wave reviewed inside `wave-13-15` is not also missing.
            covered.update(range(min(first, last), max(first, last) + 1))

    # The other half of #386, and the half a widened regex alone does not give:
    # ask the PLAN which waves exist, rather than only reading what happens to
    # be on disk. A wave with no artifact under ANY spelling is then the thing
    # that warns, instead of being invisible because no directory named it.
    declared = {
        t.wave
        for t in tickets.values()
        if getattr(t, "wave", None) is not None and not getattr(t, "retired", False)
    }
    for wave_number in sorted(declared - covered):
        warnings.append(
            f"wave-{wave_number}: the plan declares this wave and no review "
            f"directory under {artifact_root.strip()} covers it, under any "
            "spelling -- advisory, nothing here refuses"
        )
    for _, wave in sorted(waves):
        review = wave / "review.md"
        if not review.is_file():
            warnings.append(
                f"{wave.name}: no review.md; at finalization a review nobody "
                "produced cannot be told apart from one nobody chose to skip "
                "(references/human-review.md §3)"
            )
            continue
        try:
            text = review.read_text(encoding="utf-8").lower()
        except OSError as error:
            warnings.append(f"{wave.name}: cannot read review.md: {error}")
            continue
        missing = [
            label
            for label, needles in WAVE_BLOCKS
            if not any(needle in text for needle in needles)
        ]
        if missing:
            warnings.append(
                f"{wave.name}: review artifact does not show {missing}; the epic "
                "agent writes these at wave close (references/human-review.md "
                "§3.4) -- advisory, nothing here refuses"
            )


def _validate_findings_partition(
    plan: object, tickets: dict[str, Ticket], warnings: list[str]
) -> None:
    """Warn when a wave shares one mutable backlog with no per-agent partition.

    Measured three times in one wave of this skill's own epic: four tickets
    appending to the end of one cumulative ledger produced four reconciles, one
    ticket twice. `conflict_keys` cannot express it, because each ticket
    legitimately owns only *its own rows* and none of them wrote a line another
    one wrote.

    The remedy on the record is a per-ticket findings file merged at wave
    close, and deliberately **not** a union merge driver: a union driver
    silently produces a valid-looking file when it is wrong, which is the same
    shape as the defect it would be papering over.
    """
    if not isinstance(plan, dict):
        return
    policy = plan.get("deferment_policy")
    if not isinstance(policy, dict):
        return
    partition = policy.get("per_ticket_backlog")
    if isinstance(partition, str) and partition.strip():
        return

    by_wave: dict[int, list[str]] = defaultdict(list)
    for ticket in tickets.values():
        if not ticket.retired and ticket.wave is not None:
            by_wave[ticket.wave].append(ticket.id)
    shared = sorted(wave for wave, ids in by_wave.items() if len(ids) > 1)
    if not shared:
        return
    warnings.append(
        f"waves {shared} run more than one ticket against the single backlog "
        f"{policy.get('backlog')!r}; collision is then certain rather than "
        "careless. Add deferment_policy.per_ticket_backlog so each ticket "
        "appends to its own file and the epic agent merges them at wave close "
        "(references/deferment.md) -- advisory, nothing here refuses"
    )


def _default_repo_root(plan_path: Path) -> Path | None:
    """The repository the plan describes, inferred from the canonical layout.

    This skill puts the plan at `specs/desired_program_model/ticket_plan.yaml`,
    so two levels above its directory is the repository root. Anything else
    falls back to the working directory, and a wrong guess costs nothing: the
    checks above find no directory and say nothing rather than guessing louder.
    """
    try:
        resolved = plan_path.resolve()
    except OSError:
        return None
    parent = resolved.parent
    if parent.name == "desired_program_model" and parent.parent.name == "specs":
        return parent.parent.parent
    return Path.cwd()


def validate_plan(
    plan: object, strict: bool = False, repo_root: Path | None = None
) -> PlanReport:
    """Return deterministic diagnostics; no errors means the plan is usable.

    By default only `Blocking` diagnostics are errors and everything else is a
    warning, so a shape or policy slip never stops an epic. `strict` restores
    the full rule set as errors — except the wave-artifact and findings-
    partition checks, which are appended to `warnings` and are therefore
    advisory under every flag.
    """
    errors: list[str] = []
    warnings: list[str] = []
    schedule_revision = _schedule_revision(plan, errors)
    _validate_deferment_policy(plan, errors)
    _validate_review_policy(plan, errors, warnings)
    goals = _parse_goals(plan, errors, warnings)
    tickets = _parse_tickets(plan, errors)
    if tickets:
        retirements = _validate_retirements(
            plan, tickets, goals, schedule_revision, errors
        )
        _validate_dependency_graph(tickets, errors)
        _validate_conflicts(tickets, errors)
        _validate_promotion_lane(tickets, errors)
        _validate_goal_alignment(goals, tickets, retirements, errors, warnings)
        _validate_findings_partition(plan, tickets, warnings)
    _validate_wave_artifacts(plan, tickets, repo_root, warnings)
    if strict:
        return PlanReport(errors=errors, warnings=warnings)
    blocking = [error for error in errors if isinstance(error, Blocking)]
    advisory = [error for error in errors if not isinstance(error, Blocking)]
    return PlanReport(errors=blocking, warnings=advisory + warnings)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate dependency, wave, conflict, and promotion metadata in an epic ticket plan."
    )
    parser.add_argument(
        "plan",
        nargs="?",
        type=Path,
        default=DEFAULT_PLAN,
        help=f"ticket plan YAML (default: {DEFAULT_PLAN})",
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
            "repository the plan describes, for the wave-artifact block check "
            "(default: inferred from the plan path, else the working directory)"
        ),
    )
    return parser


WARNINGS_SHOWN = 3
LINE_LIMIT = 160


def _clip(message: str) -> str:
    return message if len(message) <= LINE_LIMIT else message[: LINE_LIMIT - 3] + "..."


def print_diagnostics(
    source: object, report: PlanReport, force: bool, verbose: bool
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
    try:
        with args.plan.open("r", encoding="utf-8") as plan_file:
            plan = yaml.safe_load(plan_file)
    except OSError as error:
        print(f"ERROR: cannot read {args.plan}: {error}", file=sys.stderr)
        return 2
    except yaml.YAMLError as error:
        print(f"ERROR: invalid YAML in {args.plan}: {error}", file=sys.stderr)
        return 2

    force = gates_forced(args.force)
    repo_root = args.repo_root or _default_repo_root(args.plan)
    report = validate_plan(plan, strict=args.strict, repo_root=repo_root)
    print_diagnostics(args.plan, report, force, args.verbose)
    if report.errors and not force:
        return 1
    if not isinstance(plan, dict) or not isinstance(plan.get("tickets"), list):
        return 0

    ticket_count = len(plan["tickets"])
    retired_count = sum(
        1
        for ticket in plan["tickets"]
        if isinstance(ticket, dict)
        and str(ticket.get("status", "")).strip().lower() == RETIRED
    )
    active_tickets = [
        ticket
        for ticket in plan["tickets"]
        if isinstance(ticket, dict)
        and str(ticket.get("status", "")).strip().lower() != RETIRED
    ]
    wave_count = len({str(ticket.get("wave")) for ticket in active_tickets})
    goal_count = len(plan.get("epic_goals") or [])
    goal_label = "goal" if goal_count == 1 else "goals"
    print(
        f"OK: {args.plan} has a valid epic schedule "
        f"({ticket_count} tickets, {retired_count} retired, "
        f"{len(active_tickets)} active/delivered across {wave_count} waves, "
        f"{goal_count} {goal_label})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
