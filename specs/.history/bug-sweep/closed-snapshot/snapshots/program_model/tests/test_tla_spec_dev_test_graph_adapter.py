import importlib.util
from pathlib import Path


def load_adapters():
    path = Path(__file__).resolve().parents[1] / "production_adapters.py"
    spec = importlib.util.spec_from_file_location("ticket_cli_006_production_adapters", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_test_graph_cli_adapter_validates_spec_workflow_nodes() -> None:
    adapters = load_adapters()
    result = adapters.TestGraphCliAdapter().apply()

    assert result["accepted"] is True
    assert result["missing_sources"] == []
