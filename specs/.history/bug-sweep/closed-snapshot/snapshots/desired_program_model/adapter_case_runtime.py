"""MF-032: the shared before-state builder, projector, and field comparator.

Promoted out of ``production_adapters.py`` as a MODULE, deliberately **not** a
base class. The adapters have incompatible ``apply()`` signatures -- ``apply()``,
``apply(bin_dir, cache_dir)``, ``apply(target_repo, *, ...)`` -- so inheritance
would fight them (MF-028 spike report, section 5.3). Every case-executing
adapter instead *imports* these free functions and composes them inside its own
``run(case, work_dir)``. ``apply()`` stays the spec-unit surface untouched;
``run()`` is additive.

The three obligations of a ``run()`` -- MATERIALIZE ``case.before`` as a real
repository, EXECUTE the action, PROJECT the result back into the model variables
and COMPARE field by field -- live here once and are shared by all of them.

MF-028 measured this surface at ~145 shared lines; MF-031 added the ticket
segment; MF-032 gives it a home of its own so InstallLocalCli, ScaffoldWorkflow,
RecordBudgets and OpenTicket reuse it without copying a line.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


def repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "skills" / "spec-double-2" / "scripts" / "tla_spec_dev.py").is_file():
            return parent
    raise RuntimeError("could not locate tla-spec-dev repository root")


def run_cli(root: Path, target_repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    import sys

    return subprocess.run(
        [sys.executable, str(root / "skills" / "spec-double-2" / "scripts" / "tla_spec_dev.py"), *args],
        cwd=target_repo,
        text=True,
        capture_output=True,
        check=False,
    )


# ---------------------------------------------------------------------------
# The case-execution seam (MF-028 spike, promoted here by MF-032).
#
# `run_generated_case_adapters.py` calls `run(case, work_dir=...)`; the adapters
# implement `apply(target_repo, ...)`. This module is the measured minimum that
# crosses that seam and is shared by every case-executing adapter.
#
# A generated case is (before-state, action, after-state) over the nine model
# variables. `run()` therefore has three obligations, each with a different cost
# profile:
#
#   1. MATERIALIZE `case.before` as a real repository.
#   2. EXECUTE the action against it.
#   3. PROJECT the resulting repository back into the nine variables.
# ---------------------------------------------------------------------------

#: The setup pipeline as the model orders it. `setup_phase` is an ORDINAL over
#: this list, which is the single most important fact for costing this work:
#: the before-state of the setup segment is not arbitrary filesystem content,
#: it is a PREFIX of this sequence. Materializing "setup_phase = N" therefore
#: means replaying elements [0:N] -- an operation that is shared across every
#: adapter in the segment rather than adapter-specific.
SETUP_PIPELINE = [
    "BuildSkillCli",       # phase 0 -> 1
    "InstallLocalCli",     # phase 1 -> 2
    "ScaffoldProject",     # phase 2 -> 3
    "RecordBudgets",       # phase 3 -> 4
    "ScaffoldWorkflow",    # phase 4 -> 5
]

#: Variables that NO filesystem inspection can recover. `lastCommand` and
#: `result` describe the last CLI invocation, not the repository: two different
#: command histories can leave byte-identical trees. The complexity analyzer
#: independently flagged exactly this pair ("no configured invariant reads
#: [lastCommand, result]").
#:
#: They are still checked here, but from the CLI invocation the adapter
#: actually performed -- the command it ran and that command's exit status --
#: never by copying them out of `case.after`. `result.next` is the one field
#: that is genuinely unobservable: the CLI prints a prose "next:" block, not
#: the model's token, so comparing it would require re-encoding the spec inside
#: the adapter. The seam declines to do that and reports the field as
#: unprojectable instead of faking agreement.
UNPROJECTABLE_FIELDS = ("result.next",)


# MF-031: the per-ticket lifecycle ordinal, mirroring the TLA+ `ticket_state`
# constants (TicketUnopened..TicketClosed). Kept as module constants so the
# adapters read as a lifecycle rather than as arithmetic on an integer.
TICKET_UNOPENED = 0
TICKET_OPENED = 1
TICKET_DESIRED_READY = 2
TICKET_CURRENT_READY = 3
TICKET_SPEC_UNIT_PASSED = 4
TICKET_CLOSED = 5
# RC-01: the weakened close (CloseTicketWeakened). Mirrored here so the
# constants remain the whole lifecycle, but note it is NOT reachable through
# this seam: `materialize_before` already refuses every stage at or beyond
# TICKET_SPEC_UNIT_PASSED as out-of-segment, and 6 is beyond it. Read the
# ordinal through the model's TicketReached, never through `>=` -- 6 is the
# HIGHEST number and certifies the LEAST.
TICKET_CLOSED_WEAKENED = 6

# MF-031: the two agent steps (UpdateTicketDesired / UpdateTicketCurrent) have no
# CLI command -- they are the model's record of the human editing the ticket's
# desired, then current, model. The observable trace of that edit is a marker
# line appended to the ticket-local model. `project_ticket_state` reads these
# back to recover the lifecycle stage from the filesystem, exactly as
# `project_state` reads `setup_phase` from directory evidence. A marker is a
# faithful stand-in for "the agent updated this tree": the value it stands for
# is asserted against the model's after-state and has a proven-failing negative
# control, so it is never a free pass.
DESIRED_READY_MARKER = "\\* tla-spec-dev-adapter: DESIRED-READY"
CURRENT_READY_MARKER = "\\* tla-spec-dev-adapter: CURRENT-READY"


class BeforeStateUnreachable(RuntimeError):
    """Raised when `case.before` cannot be built by replaying the CLI.

    This is the honest failure mode for case execution and it is raised, never
    swallowed: an adapter that quietly ran against the wrong before-state would
    report a conformance result about a repository the case never described.
    """


def materialize_before(case: object, work_dir: Path) -> tuple[Path, str, list[dict[str, object]]]:
    """Build a repository in `case.before` by replaying the CLI prefix.

    Returns (target_repo, spec_root, replay records).

    COST NOTE (the number the MF-028 spike produced): for the setup segment
    this is ~15 lines and is entirely SHARED -- no adapter contributes anything
    adapter-specific to it. That is because phases 0..2 concern the tla-spec-dev
    source repo, which is already built in any checkout, so they materialize to
    an EMPTY DIRECTORY and cost nothing; and phases 3..5 are exactly the CLI's
    own scaffold commands, which the adapters were already calling by hand.
    The ticket segment (`ticket_state`) is a second, per-ticket ordinal replayed
    the same way. The expensive-sounding phrase in the ticket -- "constructing a
    repository already in that state" -- turns out to be "replay a prefix",
    because this model has no free-form state.
    """
    before = dict(getattr(case, "before"))
    phase = int(before["setup_phase"])
    if not 0 <= phase <= 5:
        raise BeforeStateUnreachable(f"setup_phase {phase} is outside the modelled pipeline")

    spec_root_token = str(before.get("spec_root", "NoRoot"))
    # The model's SpecRoots are symbolic constants; the repository directory
    # they denote is a binding decision, not a model fact. `default_specs` is
    # the conventional "specs" tree.
    spec_root = "specs" if spec_root_token in ("NoRoot", "default_specs") else str(spec_root_token)

    target_repo = Path(work_dir) / "target-repo"
    target_repo.mkdir(parents=True, exist_ok=True)

    root = repo_root()
    replay: list[dict[str, object]] = []
    for step in SETUP_PIPELINE[:phase]:
        if step in ("BuildSkillCli", "InstallLocalCli"):
            # Concern the tla-spec-dev checkout itself, which is already built
            # and importable. Nothing to construct in the target repo.
            replay.append({"step": step, "action": "no-op (source repo already built)"})
            continue
        if step == "ScaffoldProject":
            record = run_cli(root, target_repo, "--spec-root", spec_root, "scaffold", "project", "--name", "CliProject")
        elif step == "RecordBudgets":
            # The model has RecordBudgets as its own transition; the shipped CLI
            # emits the budgets block as part of `scaffold project` and expects
            # the agent to negotiate the values. Replaying it is therefore an
            # in-place manifest edit, not a command. This is the first place the
            # replay stops being a pure command sequence.
            record = _negotiate_budgets(target_repo, spec_root)
        elif step == "ScaffoldWorkflow":
            record = run_cli(
                root, target_repo, "--spec-root", spec_root, "scaffold", "workflow", "CLI-028", "MF-028 spike replay"
            )
        else:  # pragma: no cover - SETUP_PIPELINE is closed
            raise BeforeStateUnreachable(f"no replay defined for {step}")
        replay.append(
            {
                "step": step,
                "exit_code": getattr(record, "returncode", 0),
                "stderr": getattr(record, "stderr", "")[-400:],
            }
        )
        if getattr(record, "returncode", 0) != 0:
            raise BeforeStateUnreachable(
                f"replaying {step} to reach setup_phase={phase} failed: {getattr(record, 'stderr', '')[-600:]}"
            )

    # MF-031: the ticket segment. MF-028 measured the setup segment and refused
    # every ticket_state > 0 as out of its scope. That refusal is what blocked
    # 72.5% of the corpus by absence -- no adapter advanced ticket_state, so no
    # before-state with an active ticket could be built. This replays the ticket
    # lifecycle the same way the setup segment is replayed: `open ticket` is a
    # real CLI command, and the two agent steps (desired-ready, current-ready)
    # are the in-place model edits the agent performs, recorded as markers that
    # `project_ticket_state` reads back. Stages at or beyond
    # SpecUnitTestsPassed(4) are refused honestly (see _materialize_ticket_segment):
    # they need the spec-unit/close gate machinery, which is a different segment.
    ticket_state = dict(before.get("ticket_state") or {})
    replay.extend(_materialize_ticket_segment(root, target_repo, spec_root, phase, ticket_state))

    return target_repo, spec_root, replay


def _negotiate_budgets(target_repo: Path, spec_root: str):
    """Mark the scaffolded budgets block as negotiated, as RecordBudgets means."""
    manifest = target_repo / spec_root / "program_model" / "spec_manifest.yaml"
    if not manifest.exists():
        raise BeforeStateUnreachable(f"cannot record budgets before scaffold project: {manifest} missing")
    text = manifest.read_text(encoding="utf-8")
    if "source: negotiated" not in text:
        text = text.replace("source: default", "source: negotiated", 1)
        manifest.write_text(text, encoding="utf-8")
    return subprocess.CompletedProcess(args=["<record-budgets>"], returncode=0, stdout="", stderr="")


def project_state(
    target_repo: Path,
    spec_root: str,
    *,
    prior: dict[str, object],
    last_command: str,
    accepted: bool,
) -> dict[str, object]:
    """Project a real repository back into the nine model variables.

    COST NOTE: this is the half of the seam that does NOT come for free, and it
    is where the remaining adapters will diverge. `setup_phase` and `spec_root`
    are read from directory evidence below in ~10 lines. The four gate variables
    (complexity_gate, corpus_gate, effect_conformance) are read from
    results artifacts and are only meaningful once the corresponding oracle has
    run -- for setup-segment actions they are carried from `prior` because the
    action provably cannot change them (the TLA+ action lists them UNCHANGED).
    Carrying an UNCHANGED variable through is sound; carrying a CHANGED one
    would be the exact self-deception this epic keeps catching, so the caller
    asserts the changed-set instead.
    """
    state = dict(prior)

    specs = Path(target_repo) / spec_root
    program_model = specs / "program_model"
    manifest = program_model / "spec_manifest.yaml"

    phase = 2  # source repo built + CLI importable; both true in any checkout
    if program_model.is_dir() and any(program_model.glob("*.tla")):
        phase = 3
        if manifest.exists() and "source: negotiated" in manifest.read_text(encoding="utf-8"):
            phase = 4
            if (specs / "current").is_dir() and (specs / "desired_program_model").is_dir():
                phase = 5
    state["setup_phase"] = phase

    # spec_root is observable only once a root has actually been written.
    if phase >= 3:
        state["spec_root"] = "default_specs" if spec_root == "specs" else spec_root
    else:
        state["spec_root"] = "NoRoot"

    # Observed from the invocation the adapter actually performed.
    state["lastCommand"] = last_command
    prior_result = dict(prior.get("result") or {})
    state["result"] = {
        "accepted": bool(accepted),
        "reason": prior_result.get("reason", "NoReason"),
        # NOT observable -- see UNPROJECTABLE_FIELDS. Carried so the dict shape
        # matches; the comparison below excludes it by name rather than
        # pretending it was checked.
        "next": prior_result.get("next"),
    }
    return state


def compare_projection(
    *,
    case: object,
    projected: dict[str, object],
    unobservable: tuple[str, ...] = (),
) -> dict[str, object]:
    """Compare a projected after-state to `case.after`, field by field.

    Reports agreements, disagreements and explicitly-unchecked fields
    separately. A field that could not be observed is reported as UNCHECKED --
    never as agreement.
    """
    expected = dict(getattr(case, "after"))
    agreements: list[str] = []
    disagreements: list[dict[str, object]] = []
    unchecked: list[str] = []

    for field in sorted(set(expected) | set(projected)):
        want = expected.get(field)
        got = projected.get(field)
        if field == "result":
            want_r, got_r = dict(want or {}), dict(got or {})
            for key in sorted(set(want_r) | set(got_r)):
                dotted = f"result.{key}"
                if dotted in UNPROJECTABLE_FIELDS or dotted in unobservable:
                    unchecked.append(dotted)
                elif want_r.get(key) == got_r.get(key):
                    agreements.append(dotted)
                else:
                    disagreements.append({"field": dotted, "expected": want_r.get(key), "actual": got_r.get(key)})
            continue
        if field in unobservable:
            unchecked.append(field)
        elif want == got:
            agreements.append(field)
        else:
            disagreements.append({"field": field, "expected": want, "actual": got})

    return {
        "agreements": agreements,
        "disagreements": disagreements,
        "unchecked": unchecked,
        "conformant": not disagreements,
    }


def enforce_projection(case: object, comparison: dict[str, object]) -> None:
    """Fail the run when the projected after-state disagrees with the case.

    The runner's built-in `assert_case_result` compared `result.after` to
    `case.after` with `==` over the WHOLE dict, which could not express "this
    field is not observable". MF-032 taught the runner per-field comparison that
    honors UNCHECKED, but the adapters keep raising here too so that a direct
    `adapter.run(case)` call -- the way the spec-unit negative controls exercise
    them -- fails on a disagreement without going through the runner. Costing
    note: the missing runner support was a REAL gap shared by all fifteen
    remaining adapters, and it is now fixed centrally.
    """
    disagreements = comparison.get("disagreements") or []
    if disagreements:
        detail = "; ".join(
            f"{item['field']}: expected {item['expected']!r}, observed {item['actual']!r}" for item in disagreements
        )
        raise AssertionError(f"{getattr(case, 'name')}: projected after-state disagrees with the model -- {detail}")


# ---------------------------------------------------------------------------
# MF-031: ticket-segment materialization and projection
# ---------------------------------------------------------------------------


def _ensure_ticket_in_plan(plan_path: Path, ticket: str) -> None:
    """Add `ticket` to the scaffolded plan so `open ticket` can find it.

    `scaffold workflow` writes a plan with a single placeholder ticket. A
    before-state can hold several active tickets, so each modelled ticket is
    appended to the plan before it is opened. Appending is idempotent.
    """
    if not plan_path.exists():
        raise BeforeStateUnreachable(f"ticket plan missing at {plan_path}; workflow was not scaffolded")
    text = plan_path.read_text(encoding="utf-8")
    if f"id: {ticket}\n" in text or f"id: {ticket} " in text:
        return
    plan_path.write_text(
        text.rstrip("\n")
        + f'\n  - id: {ticket}\n    title: "MF-031 ticket-segment replay"\n    status: next\n    depends_on: []\n',
        encoding="utf-8",
    )


def _mark_ticket_tree(target_repo: Path, spec_root: str, ticket: str, tree: str, marker: str) -> None:
    """Record an agent edit into a ticket-local model tree.

    Appends `marker` to every non-MC `.tla` in `tickets/<ticket>/<tree>`. This
    is the observable trace of the modelled agent step; `project_ticket_state`
    reads it back. Raises rather than silently no-op'ing when the tree has no
    model, because a ticket that cannot be readied is a before-state that was
    not actually built.
    """
    model_dir = target_repo / spec_root / "tickets" / ticket / tree
    marked = False
    for tla in sorted(model_dir.glob("*.tla")):
        if tla.name.startswith("MC"):
            continue
        text = tla.read_text(encoding="utf-8")
        if marker not in text:
            tla.write_text(text.rstrip("\n") + "\n" + marker + "\n", encoding="utf-8")
        marked = True
    if not marked:
        raise BeforeStateUnreachable(f"ticket {ticket!r} has no {tree} model to mark ready")


def _materialize_ticket_segment(
    root: Path,
    target_repo: Path,
    spec_root: str,
    setup_phase: int,
    ticket_state: dict[str, object],
) -> list[dict[str, object]]:
    """Replay a before-state's ticket lifecycle by driving the real CLI.

    For each modelled ticket:

      * ``TicketUnopened`` -- nothing on disk, nothing to do.
      * ``TicketOpened`` -- run ``open ticket``; the ticket workspace exists.
      * ``TicketDesiredReady`` -- open, then mark the desired tree (the
        UpdateTicketDesired agent step).
      * ``TicketCurrentReady`` -- open, mark desired, then mark current (the
        UpdateTicketCurrent agent step).

    ``TicketSpecUnitTestsPassed`` and ``TicketClosed`` are REFUSED with
    ``BeforeStateUnreachable``. Reaching them means running spec-unit tests and
    closing the ticket, which requires the four oracle gates -- a different
    segment this adapter deliberately does not claim. Refusing is honest; a
    fabricated before-state would report a conformance verdict about a
    repository the case never described.
    """
    records: list[dict[str, object]] = []
    if not ticket_state:
        return records
    if any(int(value) > TICKET_UNOPENED for value in ticket_state.values()) and setup_phase < 5:
        raise BeforeStateUnreachable(
            "an active ticket requires a scaffolded workflow (setup_phase >= 5), "
            f"but setup_phase is {setup_phase}"
        )
    plan_path = target_repo / spec_root / "desired_program_model" / "ticket_plan.yaml"
    for ticket in sorted(ticket_state):
        stage = int(ticket_state[ticket])
        if stage <= TICKET_UNOPENED:
            continue
        if stage >= TICKET_SPEC_UNIT_PASSED:
            raise BeforeStateUnreachable(
                f"ticket {ticket!r} before-state ticket_state={stage} is at or beyond "
                "SpecUnitTestsPassed(4); replaying it needs the spec-unit/close gate "
                "machinery (RunSpecUnitTests, CloseTicket, and the four oracle gates), "
                "which is MF-031's out-of-segment surface"
            )
        _ensure_ticket_in_plan(plan_path, ticket)
        opened = run_cli(root, target_repo, "--spec-root", spec_root, "open", "ticket", ticket)
        records.append({"step": f"open ticket {ticket}", "exit_code": opened.returncode, "stderr": opened.stderr[-400:]})
        if opened.returncode != 0:
            raise BeforeStateUnreachable(
                f"open ticket {ticket} (to reach ticket_state={stage}) failed: {opened.stderr[-600:]}"
            )
        if stage >= TICKET_DESIRED_READY:
            _mark_ticket_tree(target_repo, spec_root, ticket, "desired", DESIRED_READY_MARKER)
            records.append({"step": f"ready desired {ticket}"})
        if stage >= TICKET_CURRENT_READY:
            _mark_ticket_tree(target_repo, spec_root, ticket, "current", CURRENT_READY_MARKER)
            records.append({"step": f"ready current {ticket}"})
    return records


def project_ticket_state(
    target_repo: Path,
    spec_root: str,
    tickets: object,
) -> dict[str, int]:
    """Recover the ticket lifecycle ordinal for each ticket from the filesystem.

    Reads only real evidence -- whether the ticket workspace exists and which
    readiness markers its trees carry -- and never consults the case's
    after-state. Stages 0..3 are recoverable this way; a ticket the adapters
    never advance past CurrentReady is never observed higher.
    """
    result: dict[str, int] = {}
    for ticket in tickets:
        ticket_dir = target_repo / spec_root / "tickets" / str(ticket)
        if not ticket_dir.is_dir():
            result[str(ticket)] = TICKET_UNOPENED
            continue
        desired_ready = _tree_has_marker(ticket_dir / "desired", DESIRED_READY_MARKER)
        current_ready = _tree_has_marker(ticket_dir / "current", CURRENT_READY_MARKER)
        if current_ready:
            result[str(ticket)] = TICKET_CURRENT_READY
        elif desired_ready:
            result[str(ticket)] = TICKET_DESIRED_READY
        else:
            result[str(ticket)] = TICKET_OPENED
    return result


def _tree_has_marker(tree_dir: Path, marker: str) -> bool:
    if not tree_dir.is_dir():
        return False
    return any(marker in tla.read_text(encoding="utf-8") for tla in tree_dir.glob("*.tla") if not tla.name.startswith("MC"))


def recover_ticket_except_index(case: object) -> str:
    """MF-029 except-index recovery of the `ticket` argument.

    `OpenTicket`/`UpdateTicketDesired`/`UpdateTicketCurrent` write
    ``ticket_state' = [ticket_state EXCEPT ![ticket] = ...]``. The argument is
    therefore the single `ticket_state` index whose entry differs between the
    before- and after-state. Recovering it consumes "which index changed" as an
    independent check for `ticket_state`; the VALUE it changed to, and every
    other ticket's value, stay independently checked in the projection. If zero
    or more than one index changed the argument is not determined by the state
    pair, and the adapter refuses rather than guessing.
    """
    before = dict(getattr(case, "before").get("ticket_state") or {})
    after = dict(getattr(case, "after").get("ticket_state") or {})
    changed = [key for key in sorted(set(before) | set(after)) if before.get(key) != after.get(key)]
    if len(changed) != 1:
        raise BeforeStateUnreachable(
            f"{getattr(case, 'name')}: ticket argument is not recoverable -- "
            f"{len(changed)} ticket_state indices changed, expected exactly 1"
        )
    return changed[0]
