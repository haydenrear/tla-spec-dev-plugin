#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "PyYAML>=6.0.2,<7",
# ]
# ///
"""One deferred-findings ledger per epic, and the closure census over it (#148).

The ledger is `specs/results/<epic>/deferred-ledger.yaml` (or the plan's
`deferment_policy.ledger`). Subcommands:

- ``init``    create the empty ledger at kickoff;
- ``record``  record a finding and give it its id at once (``<ticket>-DF-NN``);
              with a ``per_ticket_backlog`` the row goes to the ticket's own file
              (no shared-file collision) and reaches the ledger at ``absorb``;
              ``--duplicate-of`` names the original;
- ``absorb``  copy per-ticket rows the ledger does not hold yet into it (wave close);
- ``check``   the census (the default).

``tla-spec-dev close ticket`` marks the rows a ticket's ``closure.yaml`` closes
and keeps the closure at ``<ledger dir>/closures/<ticket>.yaml``.

The census fails (exit 1) when a per-ticket file disagrees with the ledger, when
an open ledger row's fix is already in a merged closure, when a duplicate names
no recorded original, or when a closure names an id nobody recorded. A missing
ledger is exit 2; an empty ledger with nothing to reconcile is exit 3 -- a
census that looked at nothing is not a green census. ``--force`` or
``SKILL_GATES=off`` prints everything and exits 0 (close never blocks).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
from pathlib import Path
import re
import sys
from typing import Any

import yaml


GATES_ENV_VARS = ("SKILL_GATES", "SPEC_GATES")
GATES_OFF_VALUES = {"off", "0", "false", "no", "force"}

#: Dispositions that leave a finding open; everything in CLOSED_DISPOSITIONS
#: closes it. Anything else is unreadable and counted as drift.
OPEN_DISPOSITIONS = {"pending", "open", "ticketed", "routed", ""}
CLOSED_DISPOSITIONS = {"fixed", "fixed-inline", "wontfix", "duplicate", "consumed", "closed"}
#: The closure.yaml keys, in the order a row is attributed when listed twice.
CLOSURE_KINDS = ("closed", "review_closed", "also")
DEFAULT_PER_TICKET = "specs/results/deferred/{ticket}.yaml"
FINDING_ID = re.compile(r"^(?P<ticket>.+)-DF-(?P<n>\d+)$")


def gates_forced(flag: bool) -> bool:
    return flag or any(
        os.environ.get(name, "").strip().lower() in GATES_OFF_VALUES for name in GATES_ENV_VARS
    )


def _load(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8")) if path.is_file() else None


def _dump(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=100), encoding="utf-8")


def disposition_state(value: object) -> str:
    """``open`` | ``closed`` | ``unreadable`` for a row's disposition."""
    if value is None:
        return "open"
    token = str(value).strip().lower()
    if token in OPEN_DISPOSITIONS:
        return "open"
    if token in CLOSED_DISPOSITIONS:
        return "closed"
    return "unreadable"


# --- locating the plan, the ledger and the per-ticket files ------------------


def resolve_plan(spec_root: Path, epic: str | None) -> tuple[dict[str, Any], str]:
    """The live plan, else the closed snapshot's plan (BS-12-DF-02), else none.

    Returns the plan and a one-line note naming which was read.
    """
    live = spec_root / "desired_program_model" / "ticket_plan.yaml"
    candidates = [live]
    if epic:
        candidates.append(
            spec_root / ".history" / epic / "closed-snapshot" / "snapshots"
            / "desired_program_model" / "ticket_plan.yaml"
        )
    for path in candidates:
        plan = _load(path)
        if isinstance(plan, dict) and (not epic or plan.get("name") in (None, epic)):
            return plan, f"plan: {path}"
    return {}, "plan: none found (defaults used)"


def epic_name(plan: dict[str, Any], epic: str | None) -> str:
    name = epic or plan.get("name")
    if not isinstance(name, str) or not name.strip():
        raise SystemExit("ERROR: no epic name: pass --epic or run where the ticket plan names one")
    return name.strip()


def ledger_path(repo_root: Path, spec_root: Path, plan: dict[str, Any], epic: str) -> Path:
    policy = plan.get("deferment_policy") if isinstance(plan.get("deferment_policy"), dict) else {}
    explicit = policy.get("ledger")
    if isinstance(explicit, str) and explicit.strip():
        return repo_root / explicit
    return spec_root / "results" / epic / "deferred-ledger.yaml"


def per_ticket_template(plan: dict[str, Any]) -> str | None:
    policy = plan.get("deferment_policy") if isinstance(plan.get("deferment_policy"), dict) else {}
    value = policy.get("per_ticket_backlog")
    return value if isinstance(value, str) and "{ticket}" in value else None


def plan_ticket_ids(plan: dict[str, Any]) -> list[str]:
    ids = []
    for ticket in plan.get("tickets") or []:
        if isinstance(ticket, dict) and isinstance(ticket.get("id"), str):
            ids.append(ticket["id"])
    return ids


def load_ledger(path: Path) -> dict[str, Any] | None:
    data = _load(path)
    if data is None:
        return None
    if not isinstance(data, dict) or not isinstance(data.get("findings", []), list):
        raise SystemExit(f"ERROR: ledger is not a mapping with a findings list: {path}")
    data.setdefault("findings", [])
    data["findings"] = data["findings"] or []
    return data


def rows_of(data: Any) -> list[dict[str, Any]]:
    findings = data.get("findings") if isinstance(data, dict) else None
    return [row for row in findings or [] if isinstance(row, dict) and row.get("id")]


def load_closures(directory: Path) -> list[dict[str, Any]]:
    closures = []
    for path in sorted(directory.glob("*.yaml")) if directory.is_dir() else []:
        data = _load(path)
        if not isinstance(data, dict):
            continue
        closures.append({
            "ticket": str(data.get("ticket") or path.stem),
            "path": path,
            **{kind: [str(i) for i in data.get(kind) or []] for kind in CLOSURE_KINDS},
        })
    return closures


# --- the census ----------------------------------------------------------------


def census(
    ledger: dict[str, Any],
    closures: list[dict[str, Any]],
    per_ticket: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    rows = {str(row["id"]): row for row in rows_of(ledger)}
    per_ticket_ids = {str(row["id"]) for file_rows in per_ticket.values() for row in file_rows}
    problems: dict[str, list[str]] = {
        "unabsorbed": [],
        "drift": [],
        "fixed_but_open": [],
        "dangling_duplicate": [],
        "closure_unknown_id": [],
    }
    counts = {kind: 0 for kind in CLOSURE_KINDS}
    counts["closed_by_later_ticket"] = 0

    for path, file_rows in sorted(per_ticket.items()):
        for row in file_rows:
            fid = str(row["id"])
            if fid not in rows:
                problems["unabsorbed"].append(f"{fid} ({path}) is not in the ledger")
                continue
            mine, theirs = disposition_state(row.get("disposition")), disposition_state(rows[fid].get("disposition"))
            if mine != theirs or mine == "unreadable":
                problems["drift"].append(
                    f"{fid}: {path} says {row.get('disposition')!r} ({mine}), "
                    f"the ledger says {rows[fid].get('disposition')!r} ({theirs})"
                )

    for fid, row in rows.items():
        original = row.get("duplicate_of")
        if original and str(original) not in rows and str(original) not in per_ticket_ids:
            problems["dangling_duplicate"].append(f"{fid} names original {original}, which is not recorded")

    attributed: set[str] = set()
    for closure in closures:
        for kind in CLOSURE_KINDS:
            for fid in closure[kind]:
                row = rows.get(fid)
                if row is None:
                    problems["closure_unknown_id"].append(
                        f"{closure['path']} {kind}: {fid} is not in the ledger"
                    )
                    continue
                if fid in attributed:
                    continue
                attributed.add(fid)
                counts[kind] += 1
                id_match = FINDING_ID.match(fid)
                finder = str(row.get("found_by") or (id_match["ticket"] if id_match else ""))
                by_later = bool(finder) and finder != closure["ticket"]
                counts["closed_by_later_ticket"] += by_later
                if disposition_state(row.get("disposition")) == "open":
                    problems["fixed_but_open"].append(
                        f"{fid} is open but {closure['ticket']} closed it ({kind}"
                        + (f", found by {finder}" if by_later else "") + f") in {closure['path']}"
                    )

    return {
        "ledger_rows": len(rows),
        "closures": len(closures),
        "per_ticket_rows": sum(len(r) for r in per_ticket.values()),
        "counts": counts,
        "problems": problems,
    }


def run_check(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    spec_root = repo_root / args.spec_root
    plan, plan_note = resolve_plan(spec_root, args.epic)
    epic = epic_name(plan, args.epic)
    path = ledger_path(repo_root, spec_root, plan, epic)
    force = gates_forced(args.force)
    ledger = load_ledger(path)
    if ledger is None:
        print(f"census: NO LEDGER at {path} ({plan_note}); run `census.py init` at kickoff")
        if force:
            print("census: FORCED past a missing ledger (--force / SKILL_GATES=off)")
            return 0
        return 2

    template = per_ticket_template(plan)
    per_ticket: dict[str, list[dict[str, Any]]] = {}
    if template:
        tickets = set(plan_ticket_ids(plan))
        tickets |= {str(r.get("found_by")) for r in rows_of(ledger) if r.get("found_by")}
        for ticket in sorted(tickets):
            file_path = repo_root / template.format(ticket=ticket)
            if file_path.is_file():
                per_ticket[str(file_path.relative_to(repo_root))] = rows_of(_load(file_path))
    closures = load_closures(path.parent / "closures")
    report = census(ledger, closures, per_ticket)
    report.update({"epic": epic, "ledger": str(path), "plan": plan_note})
    failing = sum(len(v) for v in report["problems"].values())
    vacuum = report["ledger_rows"] == 0 and report["closures"] == 0 and report["per_ticket_rows"] == 0
    report["verdict"] = "fail" if failing else ("vacuum" if vacuum else "pass")

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(f"census: {epic} -- {path} ({plan_note})")
        print(
            f"census: {report['ledger_rows']} ledger rows, {report['closures']} closures, "
            f"{report['per_ticket_rows']} per-ticket rows"
        )
        c = report["counts"]
        print(
            f"census: closed={c['closed']} review_closed={c['review_closed']} also={c['also']} "
            f"closed_by_later_ticket={c['closed_by_later_ticket']}"
        )
        for category, items in report["problems"].items():
            for item in items:
                print(f"  {category}: {item}")
        if vacuum:
            print("census: VACUUM -- an empty ledger and no closures; nothing was reconciled")
        print(f"census: {report['verdict'].upper()}" + (f" ({failing} problems)" if failing else ""))
    if report["verdict"] == "pass":
        return 0
    if force:
        print("census: FORCED (--force / SKILL_GATES=off); the problems above stand", file=sys.stderr)
        return 0
    return 1 if failing else 3


# --- writing ---------------------------------------------------------------


def _context(args: argparse.Namespace) -> tuple[Path, Path, dict[str, Any], str, Path]:
    repo_root = Path(args.repo_root).resolve()
    spec_root = repo_root / args.spec_root
    plan, _ = resolve_plan(spec_root, args.epic)
    epic = epic_name(plan, args.epic)
    return repo_root, spec_root, plan, epic, ledger_path(repo_root, spec_root, plan, epic)


def run_init(args: argparse.Namespace) -> int:
    _, _, _, epic, path = _context(args)
    if path.exists():
        print(f"ledger already exists: {path}")
        return 0
    _dump(path, {"version": 1, "epic": epic, "findings": []})
    print(f"ledger created: {path}")
    return 0


def next_id(ticket: str, *row_lists: list[dict[str, Any]]) -> str:
    highest = 0
    for rows in row_lists:
        for row in rows:
            match = FINDING_ID.match(str(row.get("id", "")))
            if match and match["ticket"] == ticket:
                highest = max(highest, int(match["n"]))
    return f"{ticket}-DF-{highest + 1:02d}"


def run_record(args: argparse.Namespace) -> int:
    repo_root, _, plan, _, path = _context(args)
    ledger = load_ledger(path)
    template = per_ticket_template(plan)
    if ledger is None and not template:
        print(f"ERROR: no ledger at {path}; run `census.py init` first", file=sys.stderr)
        return 2
    ledger = ledger or {"findings": []}
    target = repo_root / template.format(ticket=args.ticket) if template else path
    target_data = (_load(target) or {}) if target != path else ledger
    if not isinstance(target_data, dict):
        target_data = {}
    target_rows = target_data.setdefault("findings", []) or []
    target_data["findings"] = target_rows
    fid = next_id(args.ticket, rows_of(ledger), rows_of(target_data))
    row: dict[str, Any] = {
        "id": fid,
        "found_by": args.ticket,
        "recorded_at": _dt.date.today().isoformat(),
        "severity": args.severity,
        "summary": args.summary,
        "reproduction": args.reproduction,
        "surface": {"production": list(args.surface or []), "tla": [], "adapters": [], "test_graph": []},
        "why_out_of_scope": args.why_out_of_scope,
        "disposition": "duplicate" if args.duplicate_of else "pending",
    }
    if args.duplicate_of:
        row["duplicate_of"] = args.duplicate_of
    target_rows.append(row)
    _dump(target, target_data)
    print(f"recorded {fid} in {target}" + (f" (duplicate of {args.duplicate_of})" if args.duplicate_of else ""))
    return 0


def run_absorb(args: argparse.Namespace) -> int:
    repo_root, _, plan, _, path = _context(args)
    ledger = load_ledger(path)
    template = per_ticket_template(plan)
    if ledger is None or not template:
        print(f"ERROR: absorb needs a ledger ({path}) and a per_ticket_backlog", file=sys.stderr)
        return 2
    known = {str(r["id"]) for r in rows_of(ledger)}
    added = 0
    for ticket in args.ticket or plan_ticket_ids(plan):
        file_path = repo_root / template.format(ticket=ticket)
        for row in rows_of(_load(file_path)):
            if str(row["id"]) not in known:
                ledger["findings"].append({"found_by": ticket, **row})
                known.add(str(row["id"]))
                added += 1
    _dump(path, ledger)
    print(f"absorbed {added} row(s) into {path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--spec-root", default="specs")
    parser.add_argument("--epic", help="Epic/workflow name (default: the ticket plan's name).")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("init", help="Create the empty ledger.").set_defaults(func=run_init)
    record = sub.add_parser("record", help="Record a finding; prints its id.")
    record.add_argument("--ticket", required=True)
    record.add_argument("--summary", required=True)
    record.add_argument("--reproduction", required=True)
    record.add_argument("--severity", default="minor", choices=("blocking", "major", "minor"))
    record.add_argument("--surface", action="append", help="A production path the fix touches (repeatable).")
    record.add_argument("--why-out-of-scope", default="")
    record.add_argument("--duplicate-of", help="The id of the finding this one repeats.")
    record.set_defaults(func=run_record)
    absorb = sub.add_parser("absorb", help="Copy per-ticket rows into the ledger.")
    absorb.add_argument("--ticket", action="append", help="Only these tickets (default: every plan ticket).")
    absorb.set_defaults(func=run_absorb)
    check = sub.add_parser("check", help="Run the closure census (the default).")
    for target in (parser, check):
        target.add_argument("--force", action="store_true", default=argparse.SUPPRESS,
                            help="Report, then exit 0. SKILL_GATES=off means the same.")
        target.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
    check.set_defaults(func=run_check)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    for name in ("force", "json"):
        if not hasattr(args, name):
            setattr(args, name, False)
    return int(getattr(args, "func", run_check)(args))


if __name__ == "__main__":
    raise SystemExit(main())
