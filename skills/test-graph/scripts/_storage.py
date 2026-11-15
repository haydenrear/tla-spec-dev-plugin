"""Use the repository's selected storage profile for a run, and record it.

A repository that runs clusters says which disk they use in a tracked
``deploy-storage.toml`` (the deploy-helm skill owns the format and the
``deploy-storage`` command). When that file exists, a run:

1. calls ``deploy-storage up``, which attaches the sparsebundle or finds the
   external drive;
2. exports the resolved paths to every node;
3. records the selection in ``outcome.json`` under ``storage``.

A repository without the file is untouched: ``storage`` is ``null``.

The run does not start when the selected storage cannot be used. A drive that
is not connected must never turn into a run against another disk.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_NAME = "deploy-storage.toml"
MODE_ENV = "TEST_GRAPH_STORAGE"
BINARY_ENV = "DEPLOY_STORAGE_BIN"
UP_TIMEOUT_SECONDS = 900


@dataclass
class Storage:
    record: dict | None = None
    env: dict[str, str] = field(default_factory=dict)
    error: str | None = None


def find_config(test_graph_root: Path) -> Path | None:
    """The tracked file at or above the test-graph project, inside its repository."""
    explicit = (os.environ.get("DEPLOY_STORAGE_CONFIG") or "").strip()
    if explicit:
        return Path(explicit).expanduser()
    here = Path(test_graph_root).resolve()
    for directory in [here, *here.parents]:
        candidate = directory / CONFIG_NAME
        if candidate.is_file():
            return candidate
        if (directory / ".git").exists():
            return None
    return None


def prepare(test_graph_root: Path, mode: str | None = None) -> Storage:
    config = find_config(test_graph_root)
    if config is None:
        return Storage()
    mode = (mode or os.environ.get(MODE_ENV) or "auto").strip().lower()
    if mode == "off":
        return Storage(record={
            "status": "skipped",
            "config": str(config),
            "reason": "storage preparation was turned off for this run (--storage off)",
        })
    binary = os.environ.get(BINARY_ENV) or shutil.which("deploy-storage")
    if not binary:
        message = (
            f"{config} selects a storage profile, but `deploy-storage` is not on PATH. "
            "Install or sync the deploy-helm skill, or run with --storage off to use "
            "whatever the nodes default to"
        )
        return Storage(record={"status": "unavailable", "config": str(config), "error": message}, error=message)
    try:
        done = subprocess.run(
            [binary, "--config", str(config), "up", "--json"],
            capture_output=True, text=True, timeout=UP_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        message = f"`deploy-storage up` did not finish: {exc}"
        return Storage(record={"status": "unavailable", "config": str(config), "error": message}, error=message)
    if done.returncode != 0:
        detail = (done.stderr or done.stdout).strip() or f"exit {done.returncode}"
        message = f"the selected storage cannot be used (deploy-storage up exited {done.returncode}): {detail}"
        return Storage(
            record={"status": "unavailable", "config": str(config), "exit_code": done.returncode, "error": message},
            error=message,
        )
    try:
        document = json.loads(done.stdout)
        env = {str(k): str(v) for k, v in (document.get("env") or {}).items()}
        profile = document["profile"]
        record = {
            "status": "ready",
            "config": str(config),
            "profile": profile["name"],
            "location": profile["location"],
            "backend": profile["backend"],
            "root": document["root"],
            "device": document.get("device"),
            "image": document.get("image"),
            "action": document.get("action"),
            "env": sorted(env),
        }
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        message = f"`deploy-storage up --json` printed something this runner cannot read: {exc}"
        return Storage(record={"status": "unavailable", "config": str(config), "error": message}, error=message)
    return Storage(record=record, env=env)


def describe(storage: Storage) -> str | None:
    record = storage.record
    if record is None:
        return None
    if record["status"] == "ready":
        where = record["root"]
        device = record.get("device") or {}
        if device:
            where += f" on {device.get('name')} (uuid {device.get('volume_uuid')})"
        return f"storage: profile {record['profile']} ({record['location']}, {record['backend']}) at {where}"
    if record["status"] == "skipped":
        return f"storage: not prepared ({record['reason']})"
    return f"storage: UNAVAILABLE: {record['error']}"
