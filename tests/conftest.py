"""Shared test fixtures and configuration."""

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def _ensure_plugins():
    """Ensure all plugins are loaded for every test."""
    import hotbuckets.plugins  # noqa: F401
