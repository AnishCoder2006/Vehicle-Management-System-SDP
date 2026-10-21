
def test_create_vehicle(client):
    response = client.post("/vehicles", json={
        "plate_number": "TST-1001",
        "make": "Toyota",
        "model": "Corolla",
        "year": 2022,
        "vehicle_type": "car",
        "mileage": 15000,
        "status": "available",
    })
    assert response.status_code == 201
    assert response.json()["plate_number"] == "TST-1001"


def test_list_vehicles(client):
    client.post("/vehicles", json={"plate_number": "TST-1002"})
    response = client.get("/vehicles")

    assert response.status_code == 200
    assert any(v["plate_number"] == "TST-1002" for v in response.json())


def test_get_vehicle(client):
    created = client.post(
        "/vehicles", json={"plate_number": "TST-1003"}
    ).json()

    response = client.get(f"/vehicles/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_update_vehicle(client):
    created = client.post(
        "/vehicles", json={"plate_number": "TST-1004"}
    ).json()

    response = client.put(
        f"/vehicles/{created['id']}",
        json={"mileage": 25000},
    )
    assert response.status_code == 200
    assert response.json()["mileage"] == 25000


def test_duplicate_plate_rejected(client):
    payload = {"plate_number": "TST-1005"}
    assert client.post("/vehicles", json=payload).status_code == 201
    assert client.post("/vehicles", json=payload).status_code == 409


def test_invalid_vehicle_rejected(client):
    response = client.post(
        "/vehicles",
        json={"plate_number": "A", "year": 2022},
    )
    assert response.status_code == 422


def test_missing_vehicle_returns_404(client):
    response = client.get("/vehicles/999999")
    assert response.status_code == 404
