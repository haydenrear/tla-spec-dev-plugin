"""Resolve the execution settings for one workflow role."""
import json
import os
import tomllib
from pathlib import Path
from urllib.parse import urlsplit

from .episode import AgentError


def add_options(parser):
    parser.add_argument("--profile", help="named profile in the project's skt-agents.toml")
    parser.add_argument("--harness-config", help="meta-harness provider configuration for private serve")
    parser.add_argument("--skill-home", help="installed skill-manager home for this episode")
    parser.add_argument("--transport", choices=("acp", "http"), help="capabilities of the routed provider")
    parser.add_argument("--model", help="meta-harness model ID including its routing prefix")
    parser.add_argument("--timeout", type=int, help="episode time limit in seconds (default 14400)")
    parser.add_argument("--stall-timeout", type=int, help="private server idle limit (default 900, 0 disables)")
    parser.add_argument("--meta-harness", help="meta-harness executable (default $META_HARNESS_BIN or PATH)")
    parser.add_argument("--base-url", help="use a caller-owned meta-harness server")


def resolve(role, root, args):
    root = Path(root)
    file = root / "skt-agents.toml"
    config = tomllib.loads(file.read_text()) if file.is_file() else {}
    defaults = {"model": "CLAUDE_haiku", "transport": "acp", "timeout": 14400,
                "stall_timeout": 900, "base_url": None, "meta_harness": None,
                "harness_config": None, "skill_home": None}
    values = dict(defaults)
    sources = dict.fromkeys(defaults, "role default")
    for key, var in (("model", "SKT_REGRESS_MODEL" if role == "regress" else "SKT_REVIEW_MODEL"),
                     ("harness_config", "MH_CONFIG"), ("meta_harness", "META_HARNESS_BIN")):
        if os.environ.get(var):
            values[key], sources[key] = os.environ[var], var
    roles = config.get("roles", {})
    profiles = config.get("profiles", {})
    if not isinstance(roles, dict) or not isinstance(profiles, dict):
        raise AgentError(f"{file}: roles and profiles must be tables")
    profile = args.profile if args.profile is not None else roles.get(role)
    if profile is not None:
        if not isinstance(profile, str) or not isinstance(profiles.get(profile), dict):
            raise AgentError(f"unknown profile for {role} in {file}")
        for key, value in profiles[profile].items():
            if key not in defaults:
                raise AgentError(f"unknown profile setting {key!r} in {file}")
            values[key], sources[key] = value, f"profile {profile}"
    for key in defaults:
        explicit = getattr(args, key, None)
        if explicit is not None:
            values[key], sources[key] = explicit, "command line"
    for key, value in values.items():
        if key in ("timeout", "stall_timeout"):
            if type(value) is not int or value < (1 if key == "timeout" else 0):
                raise AgentError(f"invalid {key} for {role}")
        elif value is not None and (not isinstance(value, str) or not value.strip()):
            raise AgentError(f"invalid {key} for {role}")
    if values["transport"] not in ("http", "acp"):
        raise AgentError("transport must be http or acp")
    if role == "regress" and values["transport"] == "http":
        raise AgentError("regress needs an agent with shell and filesystem tools; select an ACP profile")
    if values["base_url"]:
        url = urlsplit(values["base_url"])
        if url.scheme not in ("http", "https") or not url.hostname or url.username is not None or url.query or url.fragment:
            raise AgentError("base_url must be an HTTP(S) endpoint without embedded credentials, query or fragment")
    for key in ("harness_config", "skill_home", "meta_harness"):
        if values[key]:
            base = root if sources[key].startswith("profile ") else Path.cwd()
            path = (base / Path(values[key]).expanduser()).resolve()
            if key == "skill_home" and not path.is_dir():
                raise AgentError(f"missing skill home: {path}")
            if key == "harness_config" and not path.is_file():
                raise AgentError(f"missing meta-harness configuration: {path}")
            values[key] = str(path)
    return {"role": role, "profile": profile, "settings": values, "sources": sources}


def write_receipt(directory, plan):
    (directory / "settings.json").write_text(json.dumps(plan, indent=2) + "\n")


def request(attempt_id, brief, worktree, plan, env=None):
    settings = plan["settings"]
    environment = dict(env or {})
    if settings["skill_home"]:
        environment["SKILL_MANAGER_HOME"] = settings["skill_home"]
    return {"attemptId": attempt_id, "model": settings["model"],
            "messages": [{"role": "user", "content": brief}], "workingDirectory": str(worktree),
            "timeoutSeconds": settings["timeout"], "env": environment}
