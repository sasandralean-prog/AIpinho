from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = ROOT / "scripts" / "validation" / "validate_engineering_agent_infrastructure.py"


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_engineering_agent_infrastructure", VALIDATOR_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_engineering_agent_infrastructure_contract() -> None:
    validator = _load_validator()
    assert validator.validate(ROOT) == []
