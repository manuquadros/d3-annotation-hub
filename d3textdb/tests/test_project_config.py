"""The gates this project documents must be runnable as written.

A script entry alone is not enough: without `ruff` in the dev group the
script resolves to whatever `ruff` happens to sit on PATH, or to an
unrelated binary of the same name, and reports a result that is not this
project's.
"""

import re
import tomllib
from pathlib import Path
from typing import Any

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def load_pyproject() -> dict[str, Any]:
    """Parse this project's own pyproject.toml."""
    with PYPROJECT.open("rb") as handle:
        return tomllib.load(handle)


def dist_name(requirement: str) -> str:
    """The distribution name at the head of a PEP 508 requirement."""
    return re.split(r"[\[<>=!~; ]", requirement, maxsplit=1)[0].lower()


def test_pdm_scripts_define_the_documented_gates() -> None:
    scripts = load_pyproject().get("tool", {}).get("pdm", {}).get("scripts")

    assert scripts is not None, "no [tool.pdm.scripts] table"
    assert scripts.get("lint") == "ruff check ."
    assert scripts.get("fmt") == "ruff format ."
    assert scripts.get("fmt-check") == "ruff format --check ."
    assert scripts.get("test") == "pytest"


def test_ruff_is_declared_as_a_dev_dependency() -> None:
    dev = load_pyproject().get("dependency-groups", {}).get("dev", [])

    assert "ruff" in {dist_name(spec) for spec in dev}
