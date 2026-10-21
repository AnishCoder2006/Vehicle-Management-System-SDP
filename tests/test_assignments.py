
def create_vehicle(client, plate="ASN-1001"):
    response = client.post("/vehicles", json={"plate_number": plate})
    assert response.status_code == 201
    return response.json()


def create_driver(client):
    response = client.post("/drivers", json={
        "name": "Test Driver",
        "phone": "9876543210",
        "license_number": "TEST-DL-1001",
    })
    assert response.status_code == 201
    return response.json()


def test_create_assignment(client):
    vehicle = create_vehicle(client)
    driver = create_driver(client)

    response = client.post("/assignments", json={
        "vehicle_id": vehicle["id"],
        "driver_id": driver["id"],
    })

    assert response.status_code == 201
    assert response.json()["is_active"] is True

    updated_vehicle = client.get(f"/vehicles/{vehicle['id']}")
    assert updated_vehicle.json()["status"] == "assigned"


def test_assignment_rejects_missing_vehicle(client):
    driver = create_driver(client)

    response = client.post("/assignments", json={
        "vehicle_id": 999999,
        "driver_id": driver["id"],
    })
    assert response.status_code == 404


def test_assignment_rejects_missing_driver(client):
    vehicle = create_vehicle(client)

    response = client.post("/assignments", json={
        "vehicle_id": vehicle["id"],
        "driver_id": 999999,
    })
    assert response.status_code == 404


def test_release_assignment(client):
    vehicle = create_vehicle(client)
    driver = create_driver(client)

    assignment = client.post("/assignments", json={
        "vehicle_id": vehicle["id"],
        "driver_id": driver["id"],
    }).json()

    response = client.post(
        f"/assignments/{assignment['id']}/release"
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    updated_vehicle = client.get(f"/vehicles/{vehicle['id']}")
    assert updated_vehicle.json()["status"] == "available"


def test_assignment_cannot_be_released_twice(client):
    vehicle = create_vehicle(client)
    driver = create_driver(client)

    assignment = client.post("/assignments", json={
        "vehicle_id": vehicle["id"],
        "driver_id": driver["id"],
    }).json()

    path = f"/assignments/{assignment['id']}/release"
    assert client.post(path).status_code == 200
    assert client.post(path).status_code == 400
