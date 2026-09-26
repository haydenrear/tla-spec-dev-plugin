"""RC-01: conformance for the two actions the coverage audit's gaps added.

`GenerateCases` (MF-026 G-6) and `CloseTicketWeakened` (owner decision
2026-08-01) are the first actions in this model to exist BECAUSE a gate found
that the program had surface the model did not represent, rather than because a
ticket added behavior. Both adapters drive the real CLI; these are the tests
that make them more than declarations.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parents[1]


def load_adapters():
    path = MODEL_DIR / "production_adapters.py"
    spec = importlib.util.spec_from_file_location("rc01_production_adapters", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generate_cases_performs_the_effects_it_declares(tmp_path: Path) -> None:
    """The three ports on `GenerateCases`, exercised through the shipped CLI.

    `corpus_process` is the java/TLC spawn, `spec_tree` the generated package
    plus the per-action coverage record and the parameter-recovery audit, and
    `spec_tree_delete` the metadir `rmtree`. Until RC-01 none of these was
    declared and none was reachable from `build_parser`, so no oracle in this
    toolchain could observe any of them.

    A machine with no `tlc2` reports `unobservable` and FAILS this test rather
    than passing on an unobserved boundary -- the MF-027 rule, applied to the
    adapter that would otherwise be the quietest place to break it.
    """
    adapters = load_adapters()
    result = adapters.GenerateCasesAdapter().apply(tmp_path)

    assert result.get("verdict") != "unobservable", result.get("reason")
    assert result["exit_code"] == 0, result.get("stderr")
    assert result["package_written"] is True
    assert result["coverage_record_written"] is True
    assert result["param_audit_written"] is True
    assert result["coverage_report_written"] is True
    # spec_tree_delete: the metadir is removed in run_tlc_dump's finally branch,
    # so a completed generation leaves none behind.
    assert result["metadir_removed"] is True
    # The G-2 constraint, applied to this command's own report destination.
    assert result["stray_coverage_json_refused"] is True
    assert result["accepted"] is True


def test_a_weakened_close_is_recorded_as_a_different_close(tmp_path: Path) -> None:
    """`--allow-open` closes a ticket the plan still calls open, and says so.

    `CloseTicket` guards on the ticket having reached `TicketSpecUnitTestsPassed`
    and TLC proves `ClosedTicketsPassedSpecUnitTests` over the whole reachable
    state space, while `--accept-new` and `--allow-open` exist specifically to
    get past that precondition. No modeled state recorded their use and no
    oracle could see the difference, because the mutation kill test seeds faults
    per declared port and per invariant -- only inside modeled boundaries.

    The weakened close still SUCCEEDS. The flags ship and have legitimate uses;
    asserting a refusal the CLI does not perform would be the same false
    assurance this ticket exists to remove.
    """
    adapters = load_adapters()
    result = adapters.CloseTicketWeakenedAdapter().apply(tmp_path)

    assert result["guarded_exit_code"] == 0, result.get("stderr")
    assert result["weakened_exit_code"] == 0, result.get("stderr")

    guarded = result["guarded_record"]
    weakened = result["weakened_record"]
    assert guarded["weakened"] is False
    assert guarded["model_action"] == "CloseTicket"
    assert weakened["weakened"] is True
    assert weakened["model_action"] == "CloseTicketWeakened"
    assert weakened["flags"] == ["--allow-open"]
    # The record names WHAT was bypassed, not merely that something was.
    assert any("not closed/done" in entry for entry in weakened["bypassed"])
    assert result["accepted"] is True
