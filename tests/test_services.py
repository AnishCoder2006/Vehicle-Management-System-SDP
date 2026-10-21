
def create_vehicle(client):
    response = client.post("/vehicles", json={
        "plate_number": "SRV-1001"
    })
    assert response.status_code == 201
    return response.json()


def test_create_service(client):
    vehicle = create_vehicle(client)

    response = client.post("/services", json={
        "vehicle_id": vehicle["id"],
        "customer_name": "Test Customer",
        "service_type": "Oil change",
        "description": "Routine maintenance",
    })

    assert response.status_code == 201
    assert response.json()["status"] == "pending"


def test_service_rejects_missing_vehicle(client):
    response = client.post("/services", json={
        "vehicle_id": 999999,
        "customer_name": "Test Customer",
        "service_type": "Oil change",
    })
    assert response.status_code == 404


def test_service_status_transitions(client):
    vehicle = create_vehicle(client)

    service = client.post("/services", json={
        "vehicle_id": vehicle["id"],
        "customer_name": "Test Customer",
        "service_type": "Oil change",
    }).json()

    path = f"/services/{service['id']}/status"

    response = client.patch(path, json={"status": "in_progress"})
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"

    updated_vehicle = client.get(f"/vehicles/{vehicle['id']}")
    assert updated_vehicle.json()["status"] == "in_service"

    response = client.patch(path, json={"status": "completed"})
    assert response.status_code == 200
    assert response.json()["status"] == "completed"


def test_invalid_service_transition_rejected(client):
    vehicle = create_vehicle(client)

    service = client.post("/services", json={
        "vehicle_id": vehicle["id"],
        "customer_name": "Test Customer",
        "service_type": "Inspection",
    }).json()

    response = client.patch(
        f"/services/{service['id']}/status",
        json={"status": "completed"},
    )
    assert response.status_code == 400


def test_list_services(client):
    vehicle = create_vehicle(client)

    client.post("/services", json={
        "vehicle_id": vehicle["id"],
        "customer_name": "Test Customer",
        "service_type": "Inspection",
    })

    response = client.get("/services")
    assert response.status_code == 200
    assert len(response.json()) >= 1
