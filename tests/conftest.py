from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient

_test_directory = Path(tempfile.mkdtemp(prefix="indoflow-tests-"))
_project_root = str(Path(__file__).resolve().parents[1])
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
os.environ["APP_ENV"] = "development"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_test_directory / 'api.db').as_posix()}"
os.environ.pop("INDOFLOW_API_TOKEN", None)
os.environ.pop("INDOFLOW_ADMIN_TOKEN", None)

from database import engine  # noqa: E402
from main import app  # noqa: E402
app.state.database_path = str(_test_directory / "api.db")


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client
    asyncio.run(engine.dispose())
    shutil.rmtree(_test_directory, ignore_errors=True)
