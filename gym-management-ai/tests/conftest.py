"""Shared test setup: every test gets its own empty temporary database."""
import pytest

from gym_ai.database import init_db


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    monkeypatch.setenv("GYM_DB_PATH", str(tmp_path / "test_gym.db"))
    init_db()
