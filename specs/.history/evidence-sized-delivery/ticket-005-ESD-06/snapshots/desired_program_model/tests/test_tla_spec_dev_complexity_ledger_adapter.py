"""MF-019 spec-unit conformance: the standing objective is a gate on close.

Drives the shipped CLI end to end rather than the ledger functions in
isolation, so it covers the real seam between close-out, promotion, and the
append-only history entry. The four cases mirror what this epic did by hand:
record the delta jointly with retention, refuse an unfilled record, reject a
reduction whose validated-refactor evidence is degraded (CD-09), and record a
validated decrease whose fuzzing-era members are honestly `not_run` (CD-09:
those members are experimental since the 2026-07-21 pivot and no longer gate).
"""

import importlib.util
from pathlib import Path


def load_adapters():
    path = Path(__file__).resolve().parents[1] / "production_adapters.py"
    spec = importlib.util.spec_from_file_location("mf019_production_adapters", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_close_records_delta_jointly_with_retention_and_refinement(tmp_path: Path) -> None:
    adapters = load_adapters()
    result = adapters.ComplexityLedgerCloseOutAdapter().apply(
        tmp_path, spec_root="project_specs", ticket_id="CLI-140"
    )

    assert result["close_recorded"] is True, result["stderr"]
    assert result["ledger_file_written"] is True
    assert result["delta_and_retention_in_same_entry"] is True, (
        "a complexity delta must never be recorded without the retention evidence "
        "from the same run -- the number is meaningless alone"
    )
    assert result["refinement_recorded"] == "none", (
        "the refinement-loop record is required at every close: an approved "
        "recommendation, or an explicit 'searched, found none'"
    )


def test_unfilled_ledger_template_refuses_the_close(tmp_path: Path) -> None:
    """Silence is not an acceptable substitute for the record."""
    adapters = load_adapters()
    result = adapters.ComplexityLedgerCloseOutAdapter().apply(
        tmp_path, spec_root="project_specs", ticket_id="CLI-141"
    )

    assert result["template_scaffolded_with_sentinels"] is True
    assert result["unfilled_template_refuses_close"] is True, (
        "an unfilled ledger template must fail the close, not pass it silently"
    )
    assert result["unfilled_names_refinement_and_narrative"] is True


def test_decrease_with_degraded_validated_refactor_evidence_is_rejected(tmp_path: Path) -> None:
    """The anti-gaming rule on the amended basis (CD-09): a reduction whose
    descriptor comparison is stale cannot close."""
    adapters = load_adapters()
    result = adapters.ComplexityLedgerCloseOutAdapter().apply(
        tmp_path, spec_root="project_specs", ticket_id="CLI-142"
    )

    assert result["degraded_decrease_rejected"] is True, (
        "a complexity reduction with degraded validated-refactor evidence must "
        "be rejected at close, not recorded as an improvement"
    )
    assert result["degraded_message_says_rejected"] is True
    assert result["degraded_message_names_the_basis"] is True


def test_validated_decrease_with_not_run_fuzzing_members_is_recorded(tmp_path: Path) -> None:
    """CD-09, the amended licensing: TLC green before/after + behavior tests +
    descriptor comparison license a decrease; kill_rate/effect_conformance/
    external_coverage stay recorded as the honest `not_run`, never gating."""
    adapters = load_adapters()
    result = adapters.ComplexityLedgerCloseOutAdapter().apply(
        tmp_path, spec_root="project_specs", ticket_id="CLI-143"
    )

    assert result["validated_decrease_recorded"] is True, result["stderr"]
    assert result["validated_delta_direction"] == "decrease"
    assert result["fuzzing_members_recorded_not_run"] is True, (
        "non-gating is not unrecorded: the experimental members must stay "
        "visible in the entry as not_run"
    )
    assert result["validated_refactor_recorded_in_entry"] is True
