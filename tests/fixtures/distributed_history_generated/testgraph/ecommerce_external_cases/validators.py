from __future__ import annotations


def assert_case_replays(case):
    if case.input.action not in case.labels:
        raise AssertionError(f"{case.name} is missing its action label")
    if case.view != "external":
        raise AssertionError(f"{case.name} is not an external case")
    if case.controllability == "hidden":
        raise AssertionError(f"{case.name} must not export hidden internal progress")
