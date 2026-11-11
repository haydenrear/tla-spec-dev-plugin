#!/usr/bin/env python3
"""Clean disposable build outputs while retaining validation evidence and active-run state."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile

from _common import add_test_graph_root_arg, run_gradle, target_project_root

# Both contained skills ship in the same pinned plugin unit.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "git-epic-workflow/scripts"))
from evidence import EvidenceError, cleanup_plan, read_document
from milestone import owner_state, repo_root

INIT_SCRIPT = """
import groovy.json.JsonSlurper
gradle.projectsEvaluated {
    def targets = new JsonSlurper().parse(new File(System.getProperty("testgraph.cleanup.targets")))
    gradle.rootProject.tasks.named("clean").configure {
        setFollowSymlinks(false)
        setDelete(targets)
    }
}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    add_test_graph_root_arg(parser)
    parser.add_argument("--retain", type=Path, action="append", default=[],
                        help="Preserve this registered path and its containing build directory")
    parser.add_argument("--lock", type=Path, help="Milestone lock to check; default <repo>/build/milestone.lock")
    parser.add_argument("--dry-run", action="store_true", help="Print the bounded retention plan without deleting")
    args = parser.parse_args()
    try:
        root = target_project_root(args.test_graph_root)
        lock = args.lock or repo_root(root) / "build/milestone.lock"
        if lock.exists():
            owner = read_document(lock)
            if not isinstance(owner, dict) or not isinstance(owner.get("pid"), int):
                raise EvidenceError("cleanup lock has no valid owner")
            if owner_state(owner) != "stale":
                raise EvidenceError("cleanup refused while a milestone owner is active")
        plan = cleanup_plan(root / "build", args.retain)
        if args.dry_run:
            print(json.dumps(plan, indent=2, sort_keys=True))
            return 0
        # Retained paths are never moved or passed to Gradle's deleter. A task
        # failure after partial cache deletion leaves the retained originals.
        with tempfile.TemporaryDirectory(prefix="testgraph-clean-") as temporary:
            directory = Path(temporary)
            targets = directory / "targets.json"
            targets.write_text(json.dumps(plan["remove"]), encoding="utf-8")
            init = directory / "retained-clean.gradle"
            init.write_text(INIT_SCRIPT, encoding="utf-8")
            return run_gradle(["--console=plain", "--init-script", str(init),
                               "-Dtestgraph.cleanup.targets=" + str(targets), ":clean"], root)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"clean: refused: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
