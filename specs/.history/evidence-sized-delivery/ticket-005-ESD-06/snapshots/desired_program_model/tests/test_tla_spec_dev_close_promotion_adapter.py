"""MF-021 spec-unit conformance: close promotion must not destroy specs/current.

This drives the shipped CLI end to end rather than the promotion function in
isolation, so it covers the real seam between `open ticket` (which seeds the
ticket workspace from a filtered view of specs/current) and `close ticket`
(which promotes that workspace back onto specs/current).
"""

import importlib.util
from pathlib import Path


def load_adapters():
    path = Path(__file__).resolve().parents[1] / "production_adapters.py"
    spec = importlib.util.spec_from_file_location("mf021_production_adapters", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_close_promotion_preserves_current_only_paths(tmp_path: Path) -> None:
    adapters = load_adapters()
    result = adapters.ClosePromotionPreservesCurrentAdapter().apply(
        tmp_path, spec_root="project_specs", ticket_id="CLI-127"
    )

    assert result["exit_code"] == 0, result["stderr"]
    assert result["current_only_file_survived"] is True, (
        "a file added to specs/current after the ticket opened was destroyed by promotion"
    )
    assert result["current_only_directory_survived"] is True, (
        "a directory unique to specs/current was destroyed by promotion"
    )
    assert result["project_workflow_test_survived"] is True, (
        "tests/test_current_ticket_workflow.py is excluded from the ticket workspace "
        "by design; promotion has no authority to delete it"
    )
    assert result["accepted"] is True


def test_close_promotion_enumerates_what_it_preserved(tmp_path: Path) -> None:
    """Silent survival is still the wrong failure mode; close must say so."""
    adapters = load_adapters()
    result = adapters.ClosePromotionPreservesCurrentAdapter().apply(
        tmp_path, spec_root="project_specs", ticket_id="CLI-128"
    )

    assert result["preservation_enumerated_in_output"] is True, result["stdout"]
    assert "promotion ->" in result["stdout"]
