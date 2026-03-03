from __future__ import annotations

import sys
from pathlib import Path

import pytest


def pytest_configure() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    tests_dir = repo_root / "tests"
    sys.path.insert(0, str(tests_dir))
    cypilot_scripts_dir = repo_root / "skills" / "cypilot" / "scripts"
    sys.path.insert(0, str(cypilot_scripts_dir))
    overwork_alert_src_dir = repo_root / "examples" / "overwork_alert" / "src"
    sys.path.insert(0, str(overwork_alert_src_dir))


@pytest.fixture(autouse=True)
def _enable_json_mode():
    """Enable JSON output mode for all tests (tests expect JSON on stdout)."""
    from cypilot.utils.ui import set_json_mode
    set_json_mode(True)
    yield
    set_json_mode(False)
