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
    assert revision == "0003_process_routes"
    assert {"resources", "parts", "work_orders", "schedule_versions", "scheduled_operations"} <= tables
    with sqlite3.connect(database_path) as connection:
        resource_columns = {row[1] for row in connection.execute("PRAGMA table_info(resources)")}
        part_columns = {row[1] for row in connection.execute("PRAGMA table_info(parts)")}
        work_order_columns = {row[1] for row in connection.execute("PRAGMA table_info(work_orders)")}
    assert "blackout_windows" in resource_columns
    assert "tool_id" in part_columns
    assert "process_route" in part_columns
    assert {"locked_resource_id", "locked_until_hour"} <= work_order_columns
