from __future__ import annotations

import os
import sqlite3
import subprocess
import sys


def test_fresh_database_migrates_to_head(tmp_path):
    database_path = tmp_path / "migration-check.db"
    env = os.environ.copy()
    env["APP_ENV"] = "development"
    env["DATABASE_URL"] = f"sqlite+aiosqlite:///{database_path.as_posix()}"
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    with sqlite3.connect(database_path) as connection:
        revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert revision == "0001_initial"
    assert {"resources", "parts", "work_orders", "schedule_versions", "scheduled_operations"} <= tables
