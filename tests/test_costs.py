
def create_vehicle(client):
    response = client.post("/vehicles", json={
        "plate_number": "CST-1001"
    })
    assert response.status_code == 201
    return response.json()


def test_create_cost(client):
    vehicle = create_vehicle(client)

    response = client.post("/costs", json={
        "vehicle_id": vehicle["id"],
        "category": "fuel",
        "amount": 1500.0,
        "description": "Fuel purchase",
    })

    assert response.status_code == 201
    assert response.json()["amount"] == 1500.0


def test_cost_rejects_missing_vehicle(client):
    response = client.post("/costs", json={
        "vehicle_id": 999999,
        "category": "fuel",
        "amount": 100,
    })
    assert response.status_code == 404


def test_invalid_cost_category_rejected(client):
    vehicle = create_vehicle(client)

    response = client.post("/costs", json={
        "vehicle_id": vehicle["id"],
        "category": "insurance",
        "amount": 100,
    })
    assert response.status_code == 422


def test_list_costs(client):
    vehicle = create_vehicle(client)

    client.post("/costs", json={
        "vehicle_id": vehicle["id"],
        "category": "parts",
        "amount": 500,
    })

    response = client.get("/costs")
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_cost_summary(client):
    vehicle = create_vehicle(client)

    client.post("/costs", json={
        "vehicle_id": vehicle["id"],
        "category": "fuel",
        "amount": 250,
    })

    response = client.get("/costs/summary")
    assert response.status_code == 200

    data = response.json()
    assert "by_vehicle" in data
    assert "by_month" in data
    assert "grand_total" in data
    assert data["grand_total"] >= 250
