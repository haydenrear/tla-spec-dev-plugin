#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "PyYAML>=6.0.2,<7",
# ]
# ///

from __future__ import annotations

import copy
from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
import unittest.mock

import yaml


SCRIPT = Path(__file__).parents[1] / "validate_assignment.py"
SPEC = importlib.util.spec_from_file_location("validate_assignment", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
validator = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = validator
SPEC.loader.exec_module(validator)

REFERENCE = Path(__file__).parents[2] / "references" / "epic-ticket.md"


def valid_assignment() -> dict:
    return {
        "version": 1,
        "epic": {
            "id": "EPIC-7",
            "workflow": "cut_the_apparatus",
            "branch": "epic/cut-the-apparatus",
            "base_sha": "1f2e3d4c5b6a7988",
            "plan_commit": "aabbccddeeff0011",
            "schedule_revision": 2,
            "default_branch": "main",
        },
        "ticket": {
            "spec_id": "CA-03",
            "feature_branch": "feature/141-trim-adapter",
            "worktree": "../wt-141-trim-adapter",
            "pr_base": "epic/cut-the-apparatus",
            "depends_on": ["CA-01"],
            "blocks": ["CA-05"],
            "wave": 2,
            "promotion_order": 30,
            "promotion_predecessor": "CA-01",
            "role": "implementation",
            "conflict_keys": {
                "production": ["src/adapter.py"],
                "tla": [],
                "adapters": ["adapter"],
                "test_graph": [],
                "workflow": [],
            },
        },
        "goals": [
            {
                "goal": "GOAL-1",
                "kind": "perf",
                "statement": "the adapter stops dominating p99",
                "metric": "p99 latency of the read path",
                "baseline": "412ms at 1f2e3d4c",
                "target": "under 300ms",
                "decided_by": {
                    "ticket": "CA-09",
                    "harness": "uv run bench/read_path.py --full",
                },
                "contribution": "direct",
                "expected_effect": "-120ms p99",
                "local_signal": "uv run bench/read_path.py --quick",
            }
        ],
        "validation": {
            "tlc": "N/A: no TLA delta in this slice",
            "spec_unit": "uv run pytest specs/tests",
            "repository_unit": "uv run pytest tests/adapter",
            "graphs": ["adapter-graph"],
            "spec_graph": "spec-conformance",
            "toolchain_spec_workflow": "N/A: this repository is not tla-spec-dev",
            "evidence_root": "results/CA-03",
        },
        "review": {
            "mode": "external",
            "ticket_agent_stops_after": "pr_open",
            "merged_by": "epic-owner",
            "cadence": "wave",
            "artifact_root": "results/epic-cut-the-apparatus/review",
        },
        "deferment": {
            "mode": "batch",
            "blocking": "escalate",
            "budget": 5,
            "backlog": "specs/desired_program_model/deferred_findings.yaml",
        },
    }


def rendered(assignment: dict, *, prose: str = "Do the work.") -> str:
    body = yaml.safe_dump(assignment, sort_keys=False)
    return (
        "## Discovery\n\nSome discovery text.\n\n"
        f"{validator.START_MARKER}\n"
        "## Epic execution — REQUIRED\n\n"
        f"```yaml\n{body}```\n\n"
        f"{prose}\n"
        f"{validator.END_MARKER}\n"
    )


def check(assignment: dict, **kwargs) -> validator.AssignmentReport:
    kwargs.setdefault("strict", True)
    return validator.validate_assignment(assignment, **kwargs)


class ExtractBlockTests(unittest.TestCase):
    def test_extracts_yaml_between_markers(self) -> None:
        parsed = validator.parse_assignment(rendered(valid_assignment()))
        self.assertEqual(parsed["ticket"]["spec_id"], "CA-03")

    def test_rejects_body_without_start_marker(self) -> None:
        with self.assertRaises(validator.AssignmentError) as caught:
            validator.parse_assignment("## Discovery\n\nno assignment here\n")
        self.assertIn("no assignment block", str(caught.exception))

    def test_rejects_unclosed_block(self) -> None:
        body = rendered(valid_assignment()).replace(validator.END_MARKER, "")
        with self.assertRaises(validator.AssignmentError) as caught:
            validator.parse_assignment(body)
        self.assertIn("never closed", str(caught.exception))

    def test_rejects_block_without_yaml_fence(self) -> None:
        body = (
            f"{validator.START_MARKER}\nDo the work, trust me.\n"
            f"{validator.END_MARKER}\n"
        )
        with self.assertRaises(validator.AssignmentError) as caught:
            validator.parse_assignment(body)
        self.assertIn("no ```yaml fence", str(caught.exception))

    def test_rejects_unclosed_yaml_fence(self) -> None:
        body = (
            f"{validator.START_MARKER}\n```yaml\nversion: 1\n"
            f"{validator.END_MARKER}\n"
        )
        with self.assertRaises(validator.AssignmentError) as caught:
            validator.parse_assignment(body)
        self.assertIn("never closed", str(caught.exception))

    def test_rejects_second_start_marker_inside_the_block(self) -> None:
        body = rendered(valid_assignment()).replace(
            "## Epic execution — REQUIRED",
            f"{validator.START_MARKER}\n## Epic execution — REQUIRED",
        )
        with self.assertRaises(validator.AssignmentError) as caught:
            validator.parse_assignment(body)
        self.assertIn("second assignment start marker", str(caught.exception))

    def test_rejects_unparseable_yaml(self) -> None:
        body = (
            f"{validator.START_MARKER}\n```yaml\nversion: 1\n  bad: [indent\n```\n"
            f"{validator.END_MARKER}\n"
        )
        with self.assertRaises(validator.AssignmentError) as caught:
            validator.parse_assignment(body)
        self.assertIn("does not parse", str(caught.exception))


class ValidAssignmentTests(unittest.TestCase):
    def test_accepts_a_fully_rendered_assignment(self) -> None:
        report = check(valid_assignment())
        self.assertEqual(report.errors, ())
        self.assertEqual(report.warnings, ())

    def test_rejects_non_mapping(self) -> None:
        report = check(["not", "a", "mapping"])
        self.assertEqual(len(report.errors), 1)
        self.assertIn("YAML mapping", report.errors[0])

    def test_accepts_assignment_without_optional_review_fields(self) -> None:
        assignment = valid_assignment()
        del assignment["review"]["merged_by"]
        del assignment["review"]["cadence"]
        del assignment["review"]["artifact_root"]
        self.assertEqual(check(assignment).errors, ())

    def test_rejects_wrong_version(self) -> None:
        assignment = valid_assignment()
        assignment["version"] = 2
        self.assertTrue(
            any("version must be 1" in error for error in check(assignment).errors)
        )


class PlaceholderTests(unittest.TestCase):
    def test_rejects_unrendered_placeholders(self) -> None:
        assignment = valid_assignment()
        assignment["ticket"]["worktree"] = "../wt-<issue-number>-<slug>"
        errors = check(assignment).errors
        self.assertTrue(any("ticket.worktree still holds" in e for e in errors))
        self.assertTrue(any("<issue-number>" in e for e in errors))

    def test_finds_placeholders_nested_in_lists(self) -> None:
        assignment = valid_assignment()
        assignment["validation"]["graphs"] = ["<affected-repository-graph>"]
        self.assertTrue(
            any(
                "validation.graphs[0] still holds" in error
                for error in check(assignment).errors
            )
        )

    def test_ignores_shell_redirection(self) -> None:
        assignment = valid_assignment()
        assignment["validation"]["spec_unit"] = "uv run pytest specs < input.txt"
        self.assertEqual(check(assignment).errors, ())

    def test_the_reference_template_is_still_a_template(self) -> None:
        """The documented block is unrendered by construction; prove we catch it."""
        assignment = validator.parse_assignment(REFERENCE.read_text(encoding="utf-8"))
        errors = check(assignment).errors
        self.assertTrue(any("still holds unrendered template" in e for e in errors))


class EpicTests(unittest.TestCase):
    def test_requires_epic_block(self) -> None:
        assignment = valid_assignment()
        del assignment["epic"]
        self.assertTrue(
            any(
                "must declare epic" in error for error in check(assignment).errors
            )
        )

    def test_rejects_branch_that_is_not_an_epic_branch(self) -> None:
        assignment = valid_assignment()
        assignment["epic"]["branch"] = "feature/whatever"
        assignment["ticket"]["pr_base"] = "feature/whatever"
        self.assertTrue(
            any(
                "must name an epic integration branch" in error
                for error in check(assignment).errors
            )
        )

    def test_rejects_epic_branch_equal_to_default_branch(self) -> None:
        assignment = valid_assignment()
        assignment["epic"]["branch"] = "main"
        assignment["ticket"]["pr_base"] = "main"
        self.assertTrue(
            any(
                "is the default branch" in error
                for error in check(assignment).errors
            )
        )

    def test_rejects_non_positive_schedule_revision(self) -> None:
        assignment = valid_assignment()
        assignment["epic"]["schedule_revision"] = 0
        self.assertTrue(
            any(
                "epic.schedule_revision must be an integer >= 1" in error
                for error in check(assignment).errors
            )
        )


class TicketTests(unittest.TestCase):
    def test_rejects_pr_base_that_is_not_the_epic_branch(self) -> None:
        assignment = valid_assignment()
        assignment["ticket"]["pr_base"] = "main"
        self.assertTrue(
            any(
                "is not the epic branch" in error
                for error in check(assignment).errors
            )
        )

    def test_rejects_unknown_role(self) -> None:
        assignment = valid_assignment()
        assignment["ticket"]["role"] = "cleanup"
        self.assertTrue(
            any("ticket.role must be one of" in e for e in check(assignment).errors)
        )

    def test_rejects_ticket_that_depends_on_itself(self) -> None:
        assignment = valid_assignment()
        assignment["ticket"]["depends_on"] = ["CA-03"]
        self.assertTrue(
            any(
                "depends_on lists this ticket itself" in error
                for error in check(assignment).errors
            )
        )

    def test_rejects_id_in_both_depends_on_and_blocks(self) -> None:
        assignment = valid_assignment()
        assignment["ticket"]["blocks"] = ["CA-01"]
        self.assertTrue(
            any(
                "both depends_on and blocks" in error
                for error in check(assignment).errors
            )
        )

    def test_rejects_self_as_promotion_predecessor(self) -> None:
        assignment = valid_assignment()
        assignment["ticket"]["promotion_predecessor"] = "CA-03"
        self.assertTrue(
            any(
                "promotion_predecessor is this ticket itself" in error
                for error in check(assignment).errors
            )
        )

    def test_accepts_null_promotion_predecessor(self) -> None:
        assignment = valid_assignment()
        assignment["ticket"]["promotion_predecessor"] = None
        self.assertEqual(check(assignment).errors, ())

    def test_accepts_any_conflict_lanes_and_missing_ones(self) -> None:
        assignment = valid_assignment()
        assignment["ticket"]["conflict_keys"] = {
            "implementation": ["src/app.py"],
            "model": [],
        }
        self.assertEqual(check(assignment).errors, ())
        del assignment["ticket"]["conflict_keys"]
        self.assertEqual(check(assignment).errors, ())


class DefaultModeTests(unittest.TestCase):
    def test_policy_and_shape_slips_are_warnings(self) -> None:
        assignment = valid_assignment()
        assignment["review"]["mode"] = "wave"
        del assignment["deferment"]
        report = validator.validate_assignment(assignment)
        self.assertEqual(report.errors, ())
        self.assertTrue(any("review.mode" in w for w in report.warnings))

    def test_wrong_base_still_blocks(self) -> None:
        assignment = valid_assignment()
        assignment["ticket"]["pr_base"] = "main"
        report = validator.validate_assignment(assignment)
        self.assertTrue(any("wrong base" in e for e in report.errors))


class GoalTests(unittest.TestCase):
    def test_requires_goals(self) -> None:
        assignment = valid_assignment()
        del assignment["goals"]
        self.assertTrue(
            any("must declare goals" in e for e in check(assignment).errors)
        )

    def test_rejects_empty_goals(self) -> None:
        assignment = valid_assignment()
        assignment["goals"] = []
        self.assertTrue(
            any("non-empty list" in e for e in check(assignment).errors)
        )

    def test_rejects_unknown_goal_kind(self) -> None:
        assignment = valid_assignment()
        assignment["goals"][0]["kind"] = "vibes"
        self.assertTrue(
            any("goals[0].kind must be one of" in e for e in check(assignment).errors)
        )

    def test_rejects_unknown_contribution(self) -> None:
        assignment = valid_assignment()
        assignment["goals"][0]["contribution"] = "helpful"
        self.assertTrue(
            any(
                "goals[0].contribution must be one of" in error
                for error in check(assignment).errors
            )
        )

    def test_rejects_na_local_signal_without_a_reason(self) -> None:
        assignment = valid_assignment()
        assignment["goals"][0]["local_signal"] = "N/A"
        self.assertTrue(
            any(
                "local_signal is 'N/A' without a reason" in error
                for error in check(assignment).errors
            )
        )

    def test_accepts_na_local_signal_with_a_reason(self) -> None:
        assignment = valid_assignment()
        assignment["goals"][0]["local_signal"] = "N/A: needs the integrated epic"
        self.assertEqual(check(assignment).errors, ())

    def test_accepts_na_local_signal_reasoned_without_a_colon(self) -> None:
        assignment = valid_assignment()
        assignment["goals"][0]["local_signal"] = "N/A until the harness is built"
        self.assertEqual(check(assignment).errors, ())

    def test_rejects_implementation_ticket_deciding_its_own_goal(self) -> None:
        assignment = valid_assignment()
        assignment["goals"][0]["decided_by"]["ticket"] = "CA-03"
        self.assertTrue(
            any(
                "cannot decide its own goal" in error
                for error in check(assignment).errors
            )
        )

    def test_requires_harness_for_the_deciding_ticket(self) -> None:
        assignment = valid_assignment()
        del assignment["goals"][0]["decided_by"]["harness"]
        self.assertTrue(
            any(
                "decided_by.harness is required" in error
                for error in check(assignment).errors
            )
        )


class EvaluationTicketTests(unittest.TestCase):
    def evaluation(self) -> dict:
        assignment = valid_assignment()
        assignment["ticket"]["role"] = "evaluation"
        assignment["ticket"]["owns_goals"] = ["GOAL-1"]
        assignment["goals"][0]["decided_by"]["ticket"] = "CA-03"
        # SIS-KICKOFF-F-01: `guard` is the authoritative spelling, shown by
        # references/epic-ticket.md and git-issue's references/epic-assignment.md
        # and required by the canonical plan on every goal relation.
        assignment["goals"][0]["contribution"] = "guard"
        return assignment

    def test_accepts_an_evaluation_ticket(self) -> None:
        report = check(self.evaluation())
        self.assertEqual(report.errors, ())
        self.assertEqual(report.warnings, ())

    def test_guard_on_an_evaluation_ticket_is_silent(self) -> None:
        report = check(self.evaluation())
        self.assertFalse(any("contribution" in w for w in report.warnings))

    def test_warns_when_an_evaluation_ticket_omits_the_contribution(self) -> None:
        assignment = self.evaluation()
        del assignment["goals"][0]["contribution"]
        report = check(assignment)
        self.assertEqual(report.errors, ())
        self.assertTrue(
            any("contribution is absent" in w for w in report.warnings)
        )

    def test_requires_owns_goals(self) -> None:
        assignment = self.evaluation()
        assignment["ticket"]["owns_goals"] = []
        self.assertTrue(
            any(
                "owns_goals names no goal" in error
                for error in check(assignment).errors
            )
        )

    def test_rejects_owns_goals_the_block_does_not_declare(self) -> None:
        assignment = self.evaluation()
        assignment["ticket"]["owns_goals"] = ["GOAL-9"]
        self.assertTrue(
            any(
                "which the goals block does not declare" in error
                for error in check(assignment).errors
            )
        )

    def test_warns_when_an_evaluation_ticket_claims_it_contributes(self) -> None:
        assignment = self.evaluation()
        assignment["goals"][0]["contribution"] = "direct"
        report = check(assignment)
        self.assertEqual(report.errors, ())
        self.assertTrue(
            any("decides this goal rather than" in w for w in report.warnings)
        )

    def test_rejects_owns_goals_on_an_implementation_ticket(self) -> None:
        assignment = valid_assignment()
        assignment["ticket"]["owns_goals"] = ["GOAL-1"]
        self.assertTrue(
            any(
                "only the evaluation ticket owns goals" in error
                for error in check(assignment).errors
            )
        )


class ValidationMatrixTests(unittest.TestCase):
    def test_rejects_na_for_a_required_entry(self) -> None:
        assignment = valid_assignment()
        assignment["validation"]["spec_unit"] = "N/A: felt slow"
        self.assertTrue(
            any(
                "validation.spec_unit is REQUIRED and cannot be" in error
                for error in check(assignment).errors
            )
        )

    def test_accepts_na_spec_unit_when_the_ticket_declares_no_model_delta(self) -> None:
        # A NOT REQUIRED spec workflow: no TLC, no spec graph, no spec-unit
        # cases of its own. Found by meta-harness-run, where 8 of 11 valid
        # assignments carried the "REQUIRED and cannot be 'N/A'" warning.
        assignment = valid_assignment()
        assignment["validation"]["tlc"] = "N/A: no model delta"
        assignment["validation"]["spec_graph"] = "N/A: no model delta"
        assignment["validation"]["spec_unit"] = "N/A: no model delta"
        self.assertFalse(
            [error for error in check(assignment).errors if "spec_unit" in error],
        )

    def test_a_no_model_delta_waiver_of_spec_unit_still_needs_a_reason(self) -> None:
        assignment = valid_assignment()
        assignment["validation"]["tlc"] = "N/A: no model delta"
        assignment["validation"]["spec_graph"] = "N/A: no model delta"
        assignment["validation"]["spec_unit"] = "N/A"
        self.assertTrue(
            any("validation.spec_unit is 'N/A' without a reason" in error for error in check(assignment).errors)
        )

    def test_rejects_na_spec_unit_when_only_one_model_check_is_waived(self) -> None:
        assignment = valid_assignment()
        assignment["validation"]["tlc"] = "run_tlc.sh Internal.tla Internal.cfg"
        assignment["validation"]["spec_graph"] = "N/A: no graph for this view"
        assignment["validation"]["spec_unit"] = "N/A: no model delta"
        self.assertTrue(
            any(
                "validation.spec_unit is REQUIRED and cannot be" in error
                for error in check(assignment).errors
            )
        )

    def test_rejects_na_without_a_reason_on_an_excusable_entry(self) -> None:
        assignment = valid_assignment()
        assignment["validation"]["tlc"] = "N/A"
        self.assertTrue(
            any(
                "validation.tlc is 'N/A' without a reason" in error
                for error in check(assignment).errors
            )
        )

    def test_accepts_an_na_reason_written_without_a_colon(self) -> None:
        """The schema's own wording for this field uses no colon."""
        assignment = valid_assignment()
        assignment["validation"]["toolchain_spec_workflow"] = (
            "N/A unless this repository is tla-spec-dev"
        )
        self.assertEqual(check(assignment).errors, ())

    def test_rejects_bare_na_with_only_punctuation(self) -> None:
        assignment = valid_assignment()
        assignment["validation"]["tlc"] = "N/A:"
        self.assertTrue(
            any(
                "validation.tlc is 'N/A' without a reason" in error
                for error in check(assignment).errors
            )
        )

    def test_requires_at_least_one_graph(self) -> None:
        assignment = valid_assignment()
        assignment["validation"]["graphs"] = []
        self.assertTrue(
            any(
                "validation.graphs must be a non-empty list" in error
                for error in check(assignment).errors
            )
        )


class ReviewTests(unittest.TestCase):
    def test_rejects_any_mode_other_than_external(self) -> None:
        assignment = valid_assignment()
        assignment["review"]["mode"] = "wave"
        errors = check(assignment).errors
        self.assertTrue(any("review.mode must be 'external'" in e for e in errors))
        self.assertTrue(any("never in review.mode" in e for e in errors))

    def test_rejects_a_ticket_agent_that_does_not_stop_at_pr_open(self) -> None:
        assignment = valid_assignment()
        assignment["review"]["ticket_agent_stops_after"] = "merge"
        self.assertTrue(
            any(
                "must be 'pr_open'" in error for error in check(assignment).errors
            )
        )

    def test_rejects_a_merger_other_than_the_epic_owner(self) -> None:
        assignment = valid_assignment()
        assignment["review"]["merged_by"] = "ticket-agent"
        self.assertTrue(
            any(
                "review.merged_by must be 'epic-owner'" in error
                for error in check(assignment).errors
            )
        )

    def test_rejects_unknown_cadence(self) -> None:
        assignment = valid_assignment()
        assignment["review"]["cadence"] = "whenever"
        self.assertTrue(
            any(
                "review.cadence must be one of" in error
                for error in check(assignment).errors
            )
        )

    def test_requires_the_review_block(self) -> None:
        assignment = valid_assignment()
        del assignment["review"]
        self.assertTrue(
            any("must declare review" in e for e in check(assignment).errors)
        )


class DefermentTests(unittest.TestCase):
    def test_rejects_a_missing_deferment_block(self) -> None:
        assignment = valid_assignment()
        del assignment["deferment"]
        errors = check(assignment).errors
        self.assertTrue(any("must declare deferment" in e for e in errors))
        self.assertTrue(any("this check exists to catch" in e for e in errors))

    def test_rejects_unknown_deferment_mode(self) -> None:
        assignment = valid_assignment()
        assignment["deferment"]["mode"] = "whenever"
        self.assertTrue(
            any(
                "deferment.mode must be one of" in error
                for error in check(assignment).errors
            )
        )

    def test_rejects_unknown_blocking_policy(self) -> None:
        assignment = valid_assignment()
        assignment["deferment"]["blocking"] = "ignore"
        self.assertTrue(
            any(
                "deferment.blocking must be one of" in error
                for error in check(assignment).errors
            )
        )

    def test_rejects_non_positive_budget(self) -> None:
        assignment = valid_assignment()
        assignment["deferment"]["budget"] = 0
        self.assertTrue(
            any(
                "deferment.budget must be an integer >= 1" in error
                for error in check(assignment).errors
            )
        )

    def test_rejects_empty_backlog_path(self) -> None:
        assignment = valid_assignment()
        assignment["deferment"]["backlog"] = "  "
        self.assertTrue(
            any(
                "deferment.backlog must be a non-empty string" in error
                for error in check(assignment).errors
            )
        )


class DispatchExpectationTests(unittest.TestCase):
    def test_accepts_matching_expectations(self) -> None:
        report = check(
            valid_assignment(),
            expect_ticket="CA-03",
            expect_epic_branch="epic/cut-the-apparatus",
        )
        self.assertEqual(report.errors, ())

    def test_rejects_a_ticket_id_the_dispatch_did_not_expect(self) -> None:
        report = check(valid_assignment(), expect_ticket="CA-04")
        self.assertTrue(
            any("this dispatch expects 'CA-04'" in e for e in report.errors)
        )

    def test_rejects_an_epic_branch_the_dispatch_did_not_expect(self) -> None:
        report = check(valid_assignment(), expect_epic_branch="epic/other")
        self.assertTrue(
            any("this dispatch expects 'epic/other'" in e for e in report.errors)
        )


class MainTests(unittest.TestCase):
    def run_main(self, body: str, *args: str) -> tuple[int, str, str]:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "issue-body.md"
            path.write_text(body, encoding="utf-8")
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = validator.main(["--assignment", str(path), *args])
        return code, out.getvalue(), err.getvalue()

    def test_reports_ok_for_a_valid_body(self) -> None:
        code, out, err = self.run_main(rendered(valid_assignment()))
        self.assertEqual(code, 0)
        self.assertIn("OK:", out)
        self.assertIn("CA-03", out)
        self.assertIn("wave 2", out)
        self.assertIn("base epic/cut-the-apparatus", out)
        self.assertEqual(err, "")

    def test_strict_returns_1_for_an_invalid_assignment(self) -> None:
        assignment = valid_assignment()
        assignment["review"]["mode"] = "wave"
        code, _, err = self.run_main(rendered(assignment), "--strict")
        self.assertEqual(code, 1)
        self.assertIn("INVALID:", err)
        self.assertIn("review.mode", err)

    def test_default_passes_a_policy_slip_with_a_short_summary(self) -> None:
        assignment = valid_assignment()
        assignment["review"]["mode"] = "wave"
        assignment["ticket"]["conflict_keys"] = {"implementation": [], "model": []}
        del assignment["deferment"]
        del assignment["goals"]
        code, out, err = self.run_main(rendered(assignment))
        self.assertEqual(code, 0)
        self.assertIn("OK:", out)
        self.assertLessEqual(len(err.splitlines()), 4)

    def test_force_and_env_pass_a_blocking_error(self) -> None:
        assignment = valid_assignment()
        assignment["ticket"]["pr_base"] = "main"
        body = rendered(assignment)
        self.assertEqual(self.run_main(body)[0], 1)
        code, _, err = self.run_main(body, "--force")
        self.assertEqual(code, 0)
        self.assertIn("FORCED", err)
        with unittest.mock.patch.dict(os.environ, {"SKILL_GATES": "off"}):
            self.assertEqual(self.run_main(body)[0], 0)

    def test_returns_2_when_no_block_is_present(self) -> None:
        code, _, err = self.run_main("## Discovery\n\nnothing here\n")
        self.assertEqual(code, 2)
        self.assertIn("no assignment block", err)

    def test_returns_2_for_an_unreadable_file(self) -> None:
        err = io.StringIO()
        with redirect_stderr(err):
            code = validator.main(["--assignment", "/nonexistent/issue-body.md"])
        self.assertEqual(code, 2)
        self.assertIn("cannot read", err.getvalue())

    def test_honours_expect_ticket_from_the_command_line(self) -> None:
        code, _, err = self.run_main(
            rendered(valid_assignment()), "--expect-ticket", "CA-99"
        )
        self.assertEqual(code, 1)
        self.assertIn("CA-99", err)

    def test_prints_warnings_without_failing(self) -> None:
        assignment = valid_assignment()
        assignment["ticket"]["role"] = "evaluation"
        assignment["ticket"]["owns_goals"] = ["GOAL-1"]
        assignment["goals"][0]["decided_by"]["ticket"] = "CA-03"
        code, out, err = self.run_main(rendered(assignment))
        self.assertEqual(code, 0)
        self.assertIn("OK:", out)
        self.assertIn("WARNING:", err)

    def test_reads_stdin_when_no_path_is_given(self) -> None:
        original = sys.stdin
        sys.stdin = io.StringIO(rendered(valid_assignment()))
        try:
            out = io.StringIO()
            with redirect_stdout(out):
                code = validator.main([])
        finally:
            sys.stdin = original
        self.assertEqual(code, 0)
        self.assertIn("OK:", out.getvalue())


class FixtureIntegrityTests(unittest.TestCase):
    def test_valid_assignment_is_not_mutated_between_tests(self) -> None:
        first = valid_assignment()
        second = copy.deepcopy(first)
        first["ticket"]["wave"] = 99
        self.assertEqual(second["ticket"]["wave"], 2)


class TicketWorkspaceTests(unittest.TestCase):
    """SIS-KICKOFF-F-03: `--ticket <id>` against a workspace nobody scaffolded.

    Every case here runs through `check`, which sets `strict=True`, so the
    absence of these messages from `report.errors` is asserted throughout
    rather than only in the one test that says so.
    """

    def repo(self, *scaffolded: str) -> Path:
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        root = Path(holder.name)
        workspaces = root / "specs" / "tickets"
        workspaces.mkdir(parents=True)
        for ticket in scaffolded:
            (workspaces / ticket).mkdir()
        return root

    def naming_ticket(self, ticket: str = "CA-03") -> dict:
        assignment = valid_assignment()
        assignment["validation"]["spec_unit"] = (
            f"tla-spec-dev --spec-root specs run spec-unit-tests --ticket {ticket}"
        )
        return assignment

    def test_warns_when_the_workspace_does_not_exist(self) -> None:
        report = check(self.naming_ticket(), repo_root=self.repo())
        self.assertTrue(
            any("specs/tickets/CA-03 does not exist" in w for w in report.warnings)
        )

    def test_silent_when_the_epic_agent_scaffolded_it(self) -> None:
        report = check(self.naming_ticket(), repo_root=self.repo("CA-03"))
        self.assertFalse(any("does not exist" in w for w in report.warnings))

    def test_silent_when_no_command_names_a_ticket(self) -> None:
        report = check(valid_assignment(), repo_root=self.repo())
        self.assertFalse(any("does not exist" in w for w in report.warnings))

    def test_silent_without_a_repo_root(self) -> None:
        report = check(self.naming_ticket())
        self.assertFalse(any("does not exist" in w for w in report.warnings))

    def test_silent_outside_a_repository_with_ticket_workspaces(self) -> None:
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        report = check(self.naming_ticket(), repo_root=Path(holder.name))
        self.assertFalse(any("does not exist" in w for w in report.warnings))

    def test_names_a_sibling_ticket_the_matrix_refers_to(self) -> None:
        report = check(self.naming_ticket("CA-09"), repo_root=self.repo("CA-03"))
        self.assertTrue(
            any("ticket CA-09's workspace" in w for w in report.warnings)
        )

    def test_reads_the_equals_spelling(self) -> None:
        assignment = valid_assignment()
        assignment["validation"]["spec_unit"] = (
            "tla-spec-dev run spec-unit-tests --ticket=CA-03"
        )
        report = check(assignment, repo_root=self.repo())
        self.assertTrue(any("specs/tickets/CA-03" in w for w in report.warnings))

    def test_never_becomes_an_error_even_under_strict(self) -> None:
        report = check(self.naming_ticket(), repo_root=self.repo())
        self.assertFalse(any("does not exist" in e for e in report.errors))
        self.assertTrue(any("does not exist" in w for w in report.warnings))

    def test_main_exits_zero_when_the_workspace_is_absent(self) -> None:
        root = self.repo()
        body = rendered(self.naming_ticket())
        path = root / "issue-body.md"
        path.write_text(body, encoding="utf-8")
        err = io.StringIO()
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = validator.main(
                ["--assignment", str(path), "--repo-root", str(root), "--verbose"]
            )
        self.assertEqual(code, 0)
        self.assertIn("OK:", out.getvalue())
        self.assertIn("does not exist", err.getvalue())


if __name__ == "__main__":
    unittest.main()
