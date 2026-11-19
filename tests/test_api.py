from __future__ import annotations

import sqlite3


def test_health_and_seed_are_repeatable(client):
    assert client.get("/health").status_code == 200
    assert client.get("/health/live").json()["status"] == "alive"
    first = client.post("/api/seed")
    second = client.post("/api/seed")
    assert first.status_code == second.status_code == 200
    assert second.json()["resources"] == 18
    assert second.json()["parts"] == 50
    assert second.json()["work_orders"] == 150
    board = client.get("/api/flow-board")
    assert board.status_code == 200
    assert board.json()["total_wip_orders"] == 150
    assert [item["stage"] for item in board.json()["queues"]] == [
        "Molding", "Debinding", "Sintering", "CNC Machining", "Finishing"
    ]


def test_configured_api_token_and_seed_admin_token(client, monkeypatch):
    monkeypatch.setenv("INDOFLOW_API_TOKEN", "test-api-token")
    monkeypatch.setenv("INDOFLOW_ADMIN_TOKEN", "test-admin-token")
    assert client.get("/api/flow-board").status_code == 401
    assert client.get("/api/flow-board", headers={"Authorization": "Bearer test-api-token"}).status_code == 200
    assert client.get("/api/flow-board", headers={"Authorization": "Bearer test-admin-token"}).status_code == 401
    assert client.post("/api/schedule/optimize", json={"time_limit_seconds": 0.1},
                       headers={"Authorization": "Bearer test-admin-token"}).status_code == 401
    assert client.post("/api/seed", headers={"Authorization": "Bearer test-api-token"}).status_code == 403
    assert client.post("/api/seed", headers={"Authorization": "Bearer test-admin-token"}).status_code == 200
    monkeypatch.delenv("INDOFLOW_API_TOKEN")
    monkeypatch.delenv("INDOFLOW_ADMIN_TOKEN")


def test_admin_token_does_not_open_or_authorize_normal_api(client, monkeypatch):
    monkeypatch.delenv("INDOFLOW_API_TOKEN", raising=False)
    monkeypatch.setenv("INDOFLOW_ADMIN_TOKEN", "test-admin-token")
    assert client.get("/api/flow-board").status_code == 401
    assert client.get(
        "/api/flow-board", headers={"Authorization": "Bearer test-admin-token"}
    ).status_code == 401
    monkeypatch.delenv("INDOFLOW_ADMIN_TOKEN")


def test_seed_is_disabled_in_production_by_default(client, monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("INDOFLOW_ADMIN_TOKEN", "test-admin-token")
    response = client.post("/api/seed", headers={"Authorization": "Bearer test-admin-token"})
    assert response.status_code == 404
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("INDOFLOW_ADMIN_TOKEN")


def test_optimize_persists_comparable_schedules_without_mutating_work_orders(client, monkeypatch):
    monkeypatch.delenv("INDOFLOW_API_TOKEN", raising=False)
    monkeypatch.delenv("INDOFLOW_ADMIN_TOKEN", raising=False)
    assert client.post("/api/seed").status_code == 200
    before = sqlite3.connect(client.app.state.database_path).execute(
        "SELECT current_stage, status, quantity, due_date_hours, wip_age_hours FROM work_orders ORDER BY id"
    ).fetchall()
    response = client.post("/api/schedule/optimize", json={"time_limit_seconds": 0.1})
    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data["gantt"]["baseline"]) > 0
    assert len(data["gantt"]["optimized"]) > 0
    assert data["comparison"]["baseline"]["schedule_version_id"]
    assert data["comparison"]["optimized"]["schedule_version_id"]
    assert len(data["why_late"]["optimized"]) == data["comparison"]["optimized"]["late_orders"]
    after = sqlite3.connect(client.app.state.database_path).execute(
        "SELECT current_stage, status, quantity, due_date_hours, wip_age_hours FROM work_orders ORDER BY id"
    ).fetchall()
    assert after == before


def test_scenario_validates_overrides_and_does_not_persist(client, monkeypatch):
    monkeypatch.delenv("INDOFLOW_API_TOKEN", raising=False)
    monkeypatch.delenv("INDOFLOW_ADMIN_TOKEN", raising=False)
    assert client.post("/api/seed").status_code == 200
    optimized = client.post("/api/schedule/optimize", json={"time_limit_seconds": 0.1})
    assert optimized.status_code == 200
    before_versions = sqlite3.connect(client.app.state.database_path).execute(
        "SELECT COUNT(*) FROM schedule_versions"
    ).fetchone()[0]
    response = client.post("/api/schedule/simulate", json={
        "down_resource_ids": ["CNC-3"],
        "rush_order_ids": ["wo-0001"],
        "demand_spike_pct": 10,
        "time_limit_seconds": 0.1,
    })
    assert response.status_code == 200, response.text
    result = response.json()
    assert len(result["gantt"]) > 0
    assert result["scenario_inputs"]["rush_order_ids"] == ["wo-0001"]
    assert client.post("/api/schedule/simulate", json={"down_resource_ids": ["missing"]}).status_code == 422
    assert client.post("/api/schedule/simulate", json={"demand_spike_pct": 400}).status_code == 422
    after_versions = sqlite3.connect(client.app.state.database_path).execute(
        "SELECT COUNT(*) FROM schedule_versions"
    ).fetchone()[0]
    assert after_versions == before_versions
