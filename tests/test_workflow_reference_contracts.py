"""Doc-contract tests for three workflow-reference instructions (BS-04, #189).

Each pins an instruction agents read, so a later edit cannot silently drop it.
The owner's rule is to fix these with instructions, not scripts; these tests
are the proof that the instruction is there.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOAL_SIGNAL = ROOT / "skills/git-issue-workflow/references/goal-signal.md"
VALIDATION_REVIEW = ROOT / "skills/git-epic-workflow/references/validation-review.md"
DEFERMENT = ROOT / "skills/git-epic-workflow/references/deferment.md"


def _flat(path: Path) -> str:
    return re.sub(r"\s+", " ", path.read_text())


def _section(path: Path, heading: str) -> str:
    text = path.read_text()
    start = text.index(heading)
    nxt = re.search(r"^#{1,3} ", text[start + len(heading):], re.M)
    end = start + len(heading) + nxt.start() if nxt else len(text)
    return re.sub(r"\s+", " ", text[start:end])


def test_goal_signal_red_control_must_apply_to_measured_node_revision() -> None:
    """#169: a committed RED control is checked against the node revision measured."""
    sec = _section(GOAL_SIGNAL, "### A control is only as current as the node revision it ran on")
    assert "git log --oneline <control-commit>..HEAD -- <node source>" in sec
    assert "re-run its seed on the tip" in sec
    assert "caveat named per node" in sec
    assert "Do not rebuild pre-fix binaries" in sec
    # It must sit inside the evaluation-ticket section, before the verdicts.
    text = GOAL_SIGNAL.read_text()
    assert (
        text.index("## The evaluation ticket")
        < text.index("### A control is only as current")
        < text.index("## Goal verdicts")
    )


def test_validation_review_contract_change_reruns_every_asserting_instrument() -> None:
    """#170: a contract change pulls in every graph binding the action, and the host episode."""
    sec = _section(VALIDATION_REVIEW, "## A changed contract reruns every instrument that asserts it")
    assert "every graph whose nodes bind that action" in sec
    assert "`testgraph_bindings`" in sec
    assert "not from the list the ticket was dispatched with" in sec
    assert "image/host episode" in sec
    assert "CI job" in sec


def test_deferment_fixed_findings_are_flipped_and_reproduced_before_dispatch() -> None:
    """#167: a fixed finding is flipped, and dispatch re-runs a finding's reproduction."""
    agent = _section(DEFERMENT, "## Ticket-agent behavior")
    assert "6. If your change fixes a finding filed by ANOTHER ticket" in agent
    assert "`disposition: fixed`" in agent and "`fixed_at`" in agent
    assert "the planner reads the backlog, not the log" in agent

    triage = _section(DEFERMENT, "## Owner triage")
    assert "re-run its `reproduction` on the dispatch base" in triage
    assert "no longer reproduces is not scheduled" in triage

    flat = _flat(DEFERMENT)
    assert "fixed-inline | fixed" in flat
    assert "fixed_at:" in flat
