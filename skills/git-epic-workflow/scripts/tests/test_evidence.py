"""Behavioral observations for evidence admission, empty claims and safe cleanup planning."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).parents[1] / "evidence.py"
spec = importlib.util.spec_from_file_location("epic_evidence_contract", SCRIPT)
evidence = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evidence)


class EvidenceTest(unittest.TestCase):
    def setUp(self):
        self.holder = tempfile.TemporaryDirectory()
        self.addCleanup(self.holder.cleanup)
        self.root = Path(self.holder.name)
        self.artifact = self.root / "artifact.json"
        self.artifact.write_text('{"observed":1}')
        self.reference = {"path": str(self.artifact), "sha256": evidence.file_digest(self.artifact)}

    def claim(self, **changes):
        record = {"id": "goal", "verdict": "met", "baseline": 0, "measured": 1,
                  "target": 1, "evidence": [self.reference]}
        record.update(changes)
        path = self.root / "claims.json"
        path.write_text(json.dumps({"claims": [record]}))
        return path

    def test_zero_and_false_are_observations(self):
        for value in (0, False, {"count": 0}, [False]):
            self.assertEqual(evidence.render_claims(self.claim(measured=value))["claims"][0]["measured"], value)

    def test_empty_and_nonfinite_inputs_cannot_be_met(self):
        for field in ("measured", "baseline", "target"):
            for value in (None, "", " ", [], {}, float("nan"), float("inf")):
                with self.subTest(field=field, value=value), self.assertRaises(evidence.EvidenceError):
                    evidence.render_claims(self.claim(**{field: value}))

    def test_evidence_mutation_invalidates_claim(self):
        path = self.claim()
        self.artifact.write_text('{"observed":2}')
        with self.assertRaises(evidence.EvidenceError):
            evidence.render_claims(path)

    def test_unmeasured_reason_is_preserved(self):
        path = self.root / "claims.json"
        path.write_text('{"claims":[{"id":"goal","verdict":"unmeasured","reason":"input unavailable"}]}')
        self.assertEqual(evidence.render_claims(path)["claims"][0]["reason"], "input unavailable")

    def test_cleanup_preserves_registered_alias_and_default_reports(self):
        build = self.root / "build"
        protected = build / "validation-reports"
        registered = build / "nested/retained"
        protected.mkdir(parents=True)
        registered.mkdir(parents=True)
        (build / "cache").mkdir()
        alias = self.root / "alias"
        alias.symlink_to(registered, target_is_directory=True)
        plan = evidence.cleanup_plan(build, [alias])
        self.assertEqual(plan["remove"], [str(build / "cache")])
        self.assertEqual(set(plan["preserve"]), {str(build / "nested"), str(protected)})

    def test_cleanup_build_symlink_is_refused(self):
        target = self.root / "target"
        target.mkdir()
        build = self.root / "build"
        build.symlink_to(target, target_is_directory=True)
        with self.assertRaises(evidence.EvidenceError):
            evidence.cleanup_plan(build, [])


if __name__ == "__main__":
    unittest.main()
