"""MF-017 spec-unit conformance: close-out emits the skill-feedback retro.

Drives the shipped CLI end to end (`scaffold -> open ticket -> close ticket`)
rather than the emit function in isolation, so it covers the real seam between
close-out promotion and the append-only history entry.
"""

import importlib.util
from pathlib import Path


def load_adapters():
    path = Path(__file__).resolve().parents[1] / "production_adapters.py"
    spec = importlib.util.spec_from_file_location("mf017_production_adapters", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_close_out_emits_skill_feedback_template(tmp_path: Path) -> None:
    adapters = load_adapters()
    result = adapters.SkillFeedbackCloseOutAdapter().apply(
        tmp_path, spec_root="project_specs", ticket_id="CLI-129"
    )

    assert result["exit_code"] == 0, result["stderr"]
    assert result["template_emitted"] is True, "close-out did not emit specs/results/skill_feedback.md"
    assert result["prompt_sections_present"] is True, (
        "the template must prompt for all four Phase 6 categories: surviving mutants, "
        "unmodelable effects, budget/metric adjustments, profile/CLI workarounds"
    )
    assert result["instructs_filing_against_skill_repo"] is True, (
        "the template must instruct turning each item into a ticket or PR against "
        "the spec-double-compiler repository"
    )


def test_history_scopes_feedback_to_the_newest_close(tmp_path: Path) -> None:
    adapters = load_adapters()
    result = adapters.SkillFeedbackCloseOutAdapter().apply(
        tmp_path, spec_root="project_specs", ticket_id="CLI-130"
    )

    assert result["first_close_feedback_filed"] is False, (
        "an unreviewed retro must be recorded as not filed, not silently accepted"
    )
    assert result["second_close_feedback_filed"] is False, (
        "a new unreviewed close must not inherit a prior ticket's filed finding"
    )
    assert result["feedback_filed_where"] == []


def test_accumulated_findings_survive_the_next_close(tmp_path: Path) -> None:
    """A filled finding is evidence; regenerating the template over it is data loss."""
    adapters = load_adapters()
    result = adapters.SkillFeedbackCloseOutAdapter().apply(
        tmp_path, spec_root="project_specs", ticket_id="CLI-131"
    )

    assert result["finding_survived_second_close"] is True
    assert result["accepted"] is True
