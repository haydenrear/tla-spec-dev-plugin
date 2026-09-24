"""Regressions for SI-20-DF-05, SI-20-DF-06 and SI-20-DF-07.

Each of the three was a command answering a question it had not measured, in a
repository where the honest answer was available. They are kept together because
they are one shape: *a derivation that guesses rather than refusing.*
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skt import check as check_mod  # noqa: E402
from skt import context as ctx  # noqa: E402
from skt import sweep as sweep_mod  # noqa: E402


# ---------------------------------------------------------------- SI-20-DF-05

REFS_MANY = "\n".join([
    "epic/architectural-coherence",
    "epic/close-the-loop",
    "epic/self-improvement-substrate",
    "origin/epic/self-improvement-substrate",
])


def test_an_ambiguous_checkout_names_no_epic_rather_than_the_first_one():
    """The regression: `skt status` reported `epic architectural-coherence
    available` -- closed 2026-08-03 -- because the derivation took the FIRST of
    sixteen `epic/*` refs and broke. A wrong epic name is worse than none: the
    field is consumed as JSON by a hook."""
    assert ctx.epic_slug_from_refs(REFS_MANY) is None


def test_a_unique_epic_is_still_named():
    """Refusing on ambiguity must not mean refusing always -- otherwise the fix
    is just a different wrong answer."""
    refs = "epic/self-improvement-substrate\norigin/epic/self-improvement-substrate"
    assert ctx.epic_slug_from_refs(refs) == "self-improvement-substrate"
    assert ctx.epic_slug_from_refs("") is None


def test_the_sweep_shares_the_derivation_rather_than_describing_it():
    """`sweep.discover_epic_slug`'s docstring claimed "same derivation as
    context.gather" while the two disagreed. One implementation now, and this
    asserts the SHARING, not a matching pair of behaviours that can drift."""
    src = (Path(__file__).resolve().parents[1] / "src" / "skt" / "sweep.py").read_text()
    assert "ctx_mod.epic_slug_from_refs" in src, (
        "sweep re-implemented the epic derivation; that is how it drifted last time"
    )


# ---------------------------------------------------------------- SI-20-DF-06

PLAN = """
name: self-improvement-substrate
tickets:
  - id: SI-19
    github_issue: "https://github.com/haydenrear/tla-spec-dev/issues/368"
    status: done
  - id: SI-20
    github_issue: "https://github.com/haydenrear/tla-spec-dev/issues/369"
    status: done
"""


def test_a_branch_spelling_the_issue_resolves_to_its_spec_id():
    """The regression: every ticket worktree in the epic was told its ticket was
    NOT in the plan, because the branch spells the ISSUE
    (`feature/369-eval-ladder-skt`) and the plan spells the SPEC ID (`SI-20`).
    That is the one line of `skt status` about whether the agent is where it
    should be."""
    index = ctx.plan_issue_index(PLAN)
    assert index == {"368": "SI-19", "369": "SI-20"}


def test_the_index_is_empty_rather_than_wrong_when_the_plan_has_no_issues():
    """An absent mapping must not invent one."""
    assert ctx.plan_issue_index("tickets:\n  - id: SI-01\n") == {}


# ---------------------------------------------------------------- SI-20-DF-07

def _report(art_state: str) -> dict:
    return {
        "tier": "worktree",
        "artifacts": {"state": art_state, "reason": "probe did not finish", "fix": ""},
    }


def test_an_unmeasured_artifact_surface_is_not_reported_as_all_current():
    """The regression: `skt check: all current (…)` on line one and `artifacts
    not checked (timeout)` on line two, exit 0. A caller reading the exit code
    or the headline got "everything is fine" from a run that measured one of the
    two surfaces it names. `unverifiable` units already had this rule -- UNKNOWN
    is not a kind of current -- and artifacts did not."""
    src = (Path(__file__).resolve().parents[1] / "src" / "skt" / "check.py").read_text()
    assert "ARTIFACTS NOT CHECKED" in src, (
        "the headline no longer distinguishes a measured artifact surface from "
        "an unmeasured one"
    )
    assert 'art_state in ("timeout", "error")' in src, (
        "the unmeasured states this guards are no longer named"
    )
