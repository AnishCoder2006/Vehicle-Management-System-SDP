from __future__ import annotations

import os

import requests


BACKEND_API_URL = os.getenv(
    "BACKEND_API_URL",
    "http://127.0.0.1:8000",
).rstrip("/")


def _get(endpoint: str):
    response = requests.get(
        f"{BACKEND_API_URL}{endpoint}",
        timeout=15,
    )

    response.raise_for_status()

    return response.json()


def get_vehicles():
    return _get("/vehicles")


def get_services():
    return _get("/services")


def get_costs():
    return _get("/costs")


def get_fleet_data():
    """
    Fetch the current FleetFlow data through the backend API.

    The ML service does not connect directly to MySQL.
    """

    vehicles = get_vehicles()
    services = get_services()
    costs = get_costs()

    return {
        "vehicles": vehicles,
        "services": services,
        "costs": costs,
    }