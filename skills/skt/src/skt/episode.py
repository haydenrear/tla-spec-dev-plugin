"""The meta-harness episode transport shared by workflow roles."""
from __future__ import annotations

import json
import os
import shutil
import signal
import socket
import subprocess
import time
import urllib.request
from pathlib import Path

DEFAULT_STALL_TIMEOUT = 900

class AgentError(RuntimeError):
    def __init__(self, reason: str, fix: str | None = None, code: int = 2):
        super().__init__(reason)
        self.reason, self.fix, self.code = reason, fix, code

def find_meta_harness(explicit: str | None = None) -> str:
    for value in (explicit, os.environ.get("META_HARNESS_BIN")):
        if value:
            path = Path(value).expanduser()
            if not path.is_file():
                raise AgentError(f"meta-harness binary not found at {path}")
            return str(path.resolve())
    found = shutil.which("meta-harness")
    if found:
        return found
    raise AgentError(
        "meta-harness is not on PATH",
        fix="pass --meta-harness <binary> or set META_HARNESS_BIN "
            "(cargo build -p meta-harness in the meta-harness checkout)",
    )


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


AUTH_ENV = ("CLAUDE_CODE_OAUTH_TOKEN", "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX")


def _agent_env() -> dict:
    # A session spawned from inside another agent session must not inherit its
    # identity. Its credentials are another matter: without them the agent has
    # nothing to log in with.
    return {k: v for k, v in os.environ.items()
            if k in AUTH_ENV or not (k == "CLAUDECODE" or k.startswith("CLAUDE_CODE_"))}

def _wait_listening(base_url: str, proc: subprocess.Popen, seconds: float = 60) -> None:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if proc.poll() is not None:
            raise AgentError(f"meta-harness serve exited with {proc.returncode} before listening",
                               code=3)
        try:
            urllib.request.urlopen(f"{base_url}/v1/models", timeout=2).close()
            return
        except urllib.error.HTTPError:
            return  # it answered; that is all this asks
        except OSError:
            time.sleep(0.5)
    raise AgentError("meta-harness serve did not start listening within 60s", code=3)


def _trace_mtime(evidence: Path) -> float | None:
    times = [f.stat().st_mtime for f in evidence.glob("*/events.jsonl")] if evidence.is_dir() else []
    return max(times) if times else None


def _stop_group(proc: subprocess.Popen) -> None:
    """Stop a process and everything it started that stayed in its group."""
    for sig, grace in ((signal.SIGTERM, 20), (signal.SIGKILL, 5)):
        try:
            os.killpg(proc.pid, sig)
        except (ProcessLookupError, PermissionError):
            pass
        try:
            proc.wait(timeout=grace)
            return
        except subprocess.TimeoutExpired:
            continue


def run_episode(binary: str, attempt_dir: Path, request: dict, base_url: str | None,
                stall_timeout: int = DEFAULT_STALL_TIMEOUT, harness_config: str | None = None) -> tuple[dict, str]:
    """Drive one episode. Starts a private ``serve`` unless ``base_url`` names one.

    The private server runs in its own process group, and the group is stopped
    when the episode ends, so nothing the agent started outlives the run unless
    it detached itself. With a private server the trace is watched: an episode
    that records nothing for ``stall_timeout`` seconds is stopped.
    """
    command = [binary, "--project-root", str(attempt_dir)]
    if harness_config:
        command.extend(["--config", harness_config])
    request_path = attempt_dir / "request.json"
    result_path = attempt_dir / "episode.json"
    request_path.write_text(json.dumps(request, indent=2) + "\n")
    evidence = attempt_dir / ".meta-harness" / "evidence"
    serve = client = log = None
    stopped = None
    try:
        if base_url is None:
            port = _free_port()
            base_url = f"http://127.0.0.1:{port}"
            log = open(attempt_dir / "serve.log", "w")
            serve = subprocess.Popen(
                [*command, "serve", "--port", str(port)],
                stdout=log, stderr=subprocess.STDOUT, env=_agent_env(), cwd=str(attempt_dir),
                start_new_session=True,
            )
            _wait_listening(base_url, serve)
        client = subprocess.Popen(
            [*command, "episode", "--base-url", base_url,
             "--request", str(request_path), "--output", str(result_path)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        began = time.time()
        deadline = began + request["timeoutSeconds"] + 300
        while client.poll() is None:
            now = time.time()
            if now > deadline:
                stopped = "the episode ran past its timeout"
                break
            if serve is not None and stall_timeout:
                quiet = now - (_trace_mtime(evidence) or began)
                if quiet > stall_timeout:
                    stopped = (f"the agent recorded nothing for {int(quiet)}s and was stopped "
                               f"(--stall-timeout {stall_timeout})")
                    break
            time.sleep(2)
    finally:
        if client is not None and client.poll() is None:
            client.kill()
            client.wait()
        if serve is not None:
            _stop_group(serve)
        if log is not None:
            log.close()
    if stopped:
        return {"outcome": "stopped", "error": stopped}, base_url
    try:
        result = json.loads(result_path.read_text())
        if not isinstance(result, dict):
            raise ValueError("expected episode object")
        if client.returncode and result.get("outcome") == "succeeded":
            result.update(outcome="failed", error=f"episode exited {client.returncode}")
        return result, base_url
    except (OSError, ValueError):
        return {"outcome": "failed", "error": "meta-harness episode wrote no result"}, base_url
