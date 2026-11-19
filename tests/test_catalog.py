def test_catalog_exposes_scenario_choices_without_excluded_orders(client):
    seeded = client.post("/api/seed")
    assert seeded.status_code == 200

    response = client.get("/api/catalog")

    assert response.status_code == 200
    payload = response.json()
    assert payload["resources"]
    assert payload["work_orders"]
    assert all(order["status"] not in {"COMPLETED", "QUALITY_HOLD"} for order in payload["work_orders"])
    assert {"id", "name", "stage", "plant", "status"} <= payload["resources"][0].keys()
    assert {"id", "wo_number", "sku_code", "stage", "due_date_hours"} <= payload["work_orders"][0].keys()


def test_demo_furnace_downtime_reroutes_to_compatible_backup(client):
    assert client.post("/api/seed").status_code == 200

    response = client.post("/api/schedule/simulate", json={
        "down_resource_ids": ["F-1"],
        "time_limit_seconds": 0.2,
    })

    assert response.status_code == 200, response.text
    sintering_operations = [operation for operation in response.json()["gantt"] if operation["stage"] == "Sintering"]
    assert sintering_operations
    assert all(operation["resource_id"] != "F-1" for operation in sintering_operations)
