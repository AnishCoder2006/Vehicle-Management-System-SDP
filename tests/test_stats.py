
def test_stats_summary_structure(client):
    response = client.get("/stats/summary")

    assert response.status_code == 200

    data = response.json()
    expected_fields = {
        "total_vehicles",
        "available",
        "assigned",
        "in_service",
        "pending_services",
        "services_due_soon",
    }

    assert expected_fields.issubset(data.keys())


def test_stats_reflect_created_vehicle(client):
    response = client.post("/vehicles", json={
        "plate_number": "STA-1001"
    })
    assert response.status_code == 201

    stats = client.get("/stats/summary")
    assert stats.status_code == 200
    assert stats.json()["total_vehicles"] >= 1
