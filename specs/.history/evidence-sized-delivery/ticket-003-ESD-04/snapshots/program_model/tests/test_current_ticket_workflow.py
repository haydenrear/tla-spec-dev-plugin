from pathlib import Path

SPEC_ROOT = Path(__file__).resolve().parents[1].parent


def _active_ticket(manifest_text: str) -> str:
    for line in manifest_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("active_ticket:"):
            return stripped.split(":", 1)[1].strip().strip('"')
    raise AssertionError("current spec_manifest.yaml has no status.active_ticket")


def test_current_ticket_workflow_scaffold_points_to_desired_plan() -> None:
    """The promoted current manifest and the desired plan must name the same ticket.

    Generalized from a hardcoded ticket id so this survives promotion of each
    ticket in the epic instead of going stale after one of them lands.
    """
    manifest = SPEC_ROOT / "current/spec_manifest.yaml"
    plan = SPEC_ROOT / "desired_program_model/ticket_plan.yaml"

    assert manifest.exists()
    assert plan.exists()

    active = _active_ticket(manifest.read_text(encoding="utf-8"))
    assert active
    assert active in plan.read_text(encoding="utf-8"), (
        f"current manifest active_ticket {active!r} is not present in the desired ticket plan"
    )


def test_current_model_carries_the_budgets_gate() -> None:
    """MF-012 promoted budgets into the whole-program current model."""
    model = (SPEC_ROOT / "current/TlaSpecDevCli.tla").read_text(encoding="utf-8")
    manifest = (SPEC_ROOT / "current/spec_manifest.yaml").read_text(encoding="utf-8")

    # MF-022 collapsed budgets_recorded into the setup_phase ordinal
    # (budgets recorded == setup_phase >= 4); the action and the invariant
    # that make budgets a gate are unchanged.
    assert "setup_phase" in model
    assert "RecordBudgets" in model
    assert "WorkflowRequiresBudgets" in model
    assert "budgets:" in manifest


def test_current_model_carries_the_ticket_state_ordinal() -> None:
    """MF-025 collapsed the whole per-ticket lifecycle into one ordinal.

    ``active_tickets``, ``closed_tickets`` and ``ticket_phase`` were not three
    independent facts but one lifecycle recorded three ways: OpenTicket guarded
    on the ticket being in neither set (never reopened), CloseTicket left the
    phase UNCHANGED (a closed ticket retains phase 3), and NoOpenClosedOverlap
    forbade being both. Exactly six of the 4,096 declared combinations were
    reachable and they were totally ordered, so ``ticket_state`` represents the
    reachable set exactly: 0=unopened, 1..4=active at phases 0..3, 5=closed.
    """
    model = (SPEC_ROOT / "current/TlaSpecDevCli.tla").read_text(encoding="utf-8")

    assert "ticket_state" in model
    # RC-01 widened the ordinal to 0..6: TicketClosedWeakened is the sixth
    # stage, recording a close taken under a guard-weakening flag. Note that 6
    # is the HIGHEST number and certifies the LEAST, which is why the module
    # reads the lifecycle through TicketReached rather than through `>=` -- five
    # invariants would otherwise have gone on holding, by accident of the
    # encoding, about a ticket that passed nothing.
    assert "ticket_state \\in [Tickets -> 0..6]" in model, (
        "TypeInvariant must bound the ordinal to 0..6"
    )
    assert "TicketClosedWeakened      == 6" in model
    assert "TicketReached(t, stage) ==" in model, (
        "the lifecycle reader must stay named: `>=` reads the weakened stage as progress"
    )

    # Check code lines only: the module carries an explanatory comment that
    # names the old variables on purpose, to document the encoding.
    code = "\n".join(
        line for line in model.splitlines() if not line.lstrip().startswith("\\*")
    )
    for gone in ("active_tickets", "closed_tickets", "ticket_phase"):
        assert gone not in code, f"{gone} survived the MF-025 collapse"
    for gone in ("desired_ready", "current_ready", "spec_unit_tests_passed"):
        assert gone not in code, f"{gone} survived the MF-020 collapse"

    # Set-valued readers must keep reading sets: the model has to read as a
    # lifecycle rather than as arithmetic on an integer.
    assert "ActiveTickets ==" in code, "the set of active tickets must stay named"
    assert "ClosedTickets ==" in code, "the set of closed tickets must stay named"

    # The ordering and overlap invariants are deliberately retained rather than
    # deleted: keeping them documents that the constraint still holds and was
    # absorbed into the representation instead of dropped.
    assert "CurrentRequiresDesired" in model
    assert "SpecUnitTestsRequireCurrent" in model
    assert "ClosedTicketsPassedSpecUnitTests" in model
    assert "NoOpenClosedOverlap" in model

    # RunSpecUnitTests must stay re-runnable on an already-passing ticket. Under
    # the ordinal the old `ticket_phase[ticket] >= 2` on an active ticket is the
    # range 3..4. Tightening it to an equality would delete the idempotent
    # re-run self-loop (measured at MF-020: 3664 -> 3184 generated states).
    assert "ticket_state[ticket] \\in TicketCurrentReady..TicketSpecUnitTestsPassed" in code, (
        "RunSpecUnitTests guard must remain a range to preserve the re-run self-loop"
    )
