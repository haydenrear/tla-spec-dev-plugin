import importlib.util
from pathlib import Path


def load_adapters():
    path = Path(__file__).resolve().parents[1] / "production_adapters.py"
    spec = importlib.util.spec_from_file_location("ticket_cli_002_production_adapters", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_skill_cli_adapter_finds_entrypoint_and_installer() -> None:
    adapters = load_adapters()
    result = adapters.BuildSkillCliAdapter().apply()

    assert result["accepted"] is True
    assert str(result["entrypoint"]).endswith("scripts/tla_spec_dev.py")
    assert str(result["installer"]).endswith("skill-scripts/install-tla-spec-dev.sh")


def test_install_local_cli_adapter_installs_wrapper(tmp_path: Path) -> None:
    adapters = load_adapters()
    result = adapters.InstallLocalCliAdapter().apply(tmp_path / "bin", tmp_path / "cache")

    assert result["accepted"] is True
    assert result["version"] == "tla-spec-dev 0.1.0"
