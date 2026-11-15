"""A run uses the repository's selected storage profile and records it.

``run.py`` calls ``deploy-storage up`` when the repository tracks a
``deploy-storage.toml``. These tests put a scripted ``deploy-storage`` in its
place and replace Gradle with a recorder, so they show exactly three things:
what reaches the nodes' environment, what ``outcome.json`` says, and that a
drive which is not connected stops the run before Gradle starts.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

import _storage  # noqa: E402
import run  # noqa: E402

READY = {
    "schema": "deploy-storage.status.v1",
    "selected": "portable",
    "profile": {"name": "portable", "location": "external", "backend": "directory", "device": "development-ssd"},
    "ready": True,
    "root": "/Volumes/renamed/proj",
    "device": {"name": "development-ssd", "volume_uuid": "AAAA-1111", "mount": "/Volumes/renamed"},
    "image": None,
    "action": "already-present",
    "env": {"DEPLOY_STORAGE_ROOT": "/Volumes/renamed/proj", "DEPLOY_STORAGE_PROFILE": "portable",
            "K3D_MEDIA_ROOT": "/Volumes/renamed/proj"},
}


class StorageProfileTest(unittest.TestCase):
    def setUp(self) -> None:
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.repo = Path(holder.name).resolve() / "repo"
        self.root = self.repo / "test_graph"
        self.root.mkdir(parents=True)
        (self.root / "settings.gradle.kts").write_text("")
        (self.root / "build.gradle.kts").write_text("validationGraph {}\n")
        (self.repo / ".git").mkdir()
        self.bin = self.repo / "fake-bin"
        self.bin.mkdir()
        self.calls = self.repo / "deploy-storage.calls"
        self.gradle_env: list[dict] = []
        env = {k: v for k, v in os.environ.items()
               if k not in (_storage.MODE_ENV, _storage.BINARY_ENV, "DEPLOY_STORAGE_CONFIG")}
        env["PATH"] = f"{self.bin}{os.pathsep}/usr/bin{os.pathsep}/bin"
        patcher = patch.dict(os.environ, env, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def track_config(self) -> Path:
        path = self.repo / _storage.CONFIG_NAME
        path.write_text('[storage]\nselected = "portable"\n')
        return path

    def fake_deploy_storage(self, *, exit_code: int = 0, stdout: str = "", stderr: str = "") -> None:
        script = self.bin / "deploy-storage"
        (self.repo / "out.txt").write_text(stdout)
        (self.repo / "err.txt").write_text(stderr)
        script.write_text(
            "#!/bin/sh\n"
            f'echo "$@" >> "{self.calls}"\n'
            f'cat "{self.repo}/out.txt"\n'
            f'cat "{self.repo}/err.txt" >&2\n'
            f"exit {exit_code}\n"
        )
        script.chmod(script.stat().st_mode | stat.S_IEXEC)

    def invoke(self, *argv: str) -> tuple[int, dict, str]:
        def fake_gradle(args, root, extra_env=None):
            self.gradle_env.append(dict(extra_env or {}))
            return 0

        out = io.StringIO()
        with patch.object(run, "run_gradle", fake_gradle), contextlib.redirect_stdout(out):
            code = run.main(["smoke", "--test-graph-root", str(self.root), *argv])
        outcome = json.loads(Path(out.getvalue().strip().splitlines()[-1]).read_text())
        return code, outcome, out.getvalue()

    def test_a_repository_without_the_file_is_untouched(self) -> None:
        self.fake_deploy_storage(stdout=json.dumps(READY))
        _, outcome, printed = self.invoke()
        self.assertIsNone(outcome["storage"])
        self.assertFalse(self.calls.exists())
        self.assertNotIn("storage:", printed)
        self.assertEqual(1, len(self.gradle_env))
        self.assertNotIn("DEPLOY_STORAGE_ROOT", self.gradle_env[0])

    def test_the_selected_profile_reaches_the_nodes_and_the_report(self) -> None:
        config = self.track_config()
        self.fake_deploy_storage(stdout=json.dumps(READY))

        _, outcome, printed = self.invoke()

        self.assertEqual(f"--config {config} up --json", self.calls.read_text().strip())
        self.assertEqual("/Volumes/renamed/proj", self.gradle_env[0]["K3D_MEDIA_ROOT"])
        self.assertEqual("portable", self.gradle_env[0]["DEPLOY_STORAGE_PROFILE"])
        storage = outcome["storage"]
        self.assertEqual(
            ("ready", "portable", "external", "directory", "/Volumes/renamed/proj", "AAAA-1111"),
            (storage["status"], storage["profile"], storage["location"], storage["backend"],
             storage["root"], storage["device"]["volume_uuid"]))
        self.assertEqual(["DEPLOY_STORAGE_PROFILE", "DEPLOY_STORAGE_ROOT", "K3D_MEDIA_ROOT"], storage["env"])
        self.assertIn("storage: profile portable (external, directory) at /Volumes/renamed/proj "
                      "on development-ssd (uuid AAAA-1111)", printed)

    def test_a_missing_drive_stops_the_run_before_gradle(self) -> None:
        self.track_config()
        self.fake_deploy_storage(
            exit_code=3, stderr="error: drive 'development-ssd' (volume UUID AAAA-1111) is not connected.")

        code, outcome, printed = self.invoke()

        self.assertEqual(run.SWEEP_EXIT_ERRORED, code)
        self.assertEqual([], self.gradle_env)  # nothing ran against another disk
        self.assertEqual(("errored", 3), (outcome["status"], outcome["exit_code"]))
        self.assertEqual("unavailable", outcome["storage"]["status"])
        self.assertIn("development-ssd", outcome["reason"])
        self.assertIn("not connected", outcome["reason"])
        self.assertEqual(["not_run"], [g["status"] for g in outcome["graphs"]])
        self.assertIn("ERRORED before any graph ran", printed)

    def test_a_tracked_file_without_the_command_is_an_error_not_a_default(self) -> None:
        self.track_config()  # and no deploy-storage on PATH
        code, outcome, _ = self.invoke()
        self.assertEqual(run.SWEEP_EXIT_ERRORED, code)
        self.assertEqual([], self.gradle_env)
        self.assertIn("`deploy-storage` is not on PATH", outcome["reason"])

    def test_storage_off_runs_and_says_it_was_skipped(self) -> None:
        self.track_config()
        self.fake_deploy_storage(exit_code=3, stderr="error: not connected")
        for argv, env in ((("--storage", "off"), {}), ((), {_storage.MODE_ENV: "off"})):
            with self.subTest(argv=argv, env=env), patch.dict(os.environ, env):
                self.gradle_env.clear()
                _, outcome, _ = self.invoke(*argv)
                self.assertEqual("skipped", outcome["storage"]["status"])
                self.assertEqual(1, len(self.gradle_env))
        self.assertFalse(self.calls.exists())

    def test_unreadable_output_is_an_error(self) -> None:
        self.track_config()
        self.fake_deploy_storage(stdout="not json")
        code, outcome, _ = self.invoke()
        self.assertEqual(run.SWEEP_EXIT_ERRORED, code)
        self.assertIn("cannot read", outcome["reason"])

    def test_the_search_for_the_file_stops_at_the_repository_root(self) -> None:
        (self.repo.parent / _storage.CONFIG_NAME).write_text("[storage]\n")  # outside the repository
        self.assertIsNone(_storage.find_config(self.root))
        self.assertEqual(self.track_config(), _storage.find_config(self.root))


if __name__ == "__main__":
    unittest.main()
