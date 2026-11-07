from __future__ import annotations


def assert_case_replays(case):
    if case.input.action not in case.labels:
        raise AssertionError(f"{case.name} is missing its action label")
    if case.view != "internal":
        raise AssertionError(f"{case.name} is not an internal case")
    if not isinstance(case.before, dict) or not isinstance(case.after, dict):
        raise AssertionError(f"{case.name} does not carry before/after states")
