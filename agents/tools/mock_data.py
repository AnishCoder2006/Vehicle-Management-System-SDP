"""Realistic mock database dataset for parallel teammate testing.

Matches backend schemas, field names, and seed data distributions exactly.
Can be reset at any time for isolated test runs.
"""

from datetime import date, datetime, timedelta
from typing import Any


def get_fresh_mock_db() -> dict[str, list[dict[str, Any]]]:
    """Generates an initial state identical to backend seed data."""
    today = date.today()
    now = datetime.now()

    vehicles = [
        {
            "id": 1,
            "plate_number": "KAA-1001",
            "make": "Toyota",
            "model": "Corolla",
            "year": 2021,
            "vehicle_type": "car",
            "mileage": 24500,
            "status": "assigned",
            "next_service_date": today - timedelta(days=3),  # Overdue
        },
        {
            "id": 2,
            "plate_number": "KBB-2002",
            "make": "Ford",
            "model": "Transit",
            "year": 2020,
            "vehicle_type": "van",
            "mileage": 48000,
            "status": "assigned",
            "next_service_date": today + timedelta(days=2),  # Due in 2 days
        },
        {
            "id": 3,
            "plate_number": "KCC-3003",
            "make": "Isuzu",
            "model": "NPR",
            "year": 2019,
            "vehicle_type": "truck",
            "mileage": 85000,
            "status": "assigned",
            "next_service_date": today + timedelta(days=5),  # Due in 5 days
        },
        {
            "id": 4,
            "plate_number": "KDD-4004",
            "make": "Honda",
            "model": "Civic",
            "year": 2022,
            "vehicle_type": "car",
            "mileage": 15200,
            "status": "in_service",
            "next_service_date": today + timedelta(days=45),
        },
        {
            "id": 5,
            "plate_number": "KEE-5005",
            "make": "Yamaha",
            "model": "MT-07",
            "year": 2023,
            "vehicle_type": "bike",
            "mileage": 6100,
            "status": "in_service",
            "next_service_date": today + timedelta(days=60),
        },
        {
            "id": 6,
            "plate_number": "KFF-6006",
            "make": "Mercedes",
            "model": "Sprinter",
            "year": 2021,
            "vehicle_type": "van",
            "mileage": 39400,
            "status": "available",
            "next_service_date": today + timedelta(days=90),
        },
        {
            "id": 7,
            "plate_number": "KGG-7007",
            "make": "Volvo",
            "model": "FH16",
            "year": 2018,
            "vehicle_type": "truck",
            "mileage": 124000,
            "status": "available",
            "next_service_date": today + timedelta(days=120),
        },
        {
            "id": 8,
            "plate_number": "KHH-8008",
            "make": "Toyota",
            "model": "RAV4",
            "year": 2022,
            "vehicle_type": "car",
            "mileage": 18900,
            "status": "available",
            "next_service_date": today + timedelta(days=150),
        },
        {
            "id": 9,
            "plate_number": "KJJ-9009",
            "make": "Scania",
            "model": "R500",
            "year": 2020,
            "vehicle_type": "truck",
            "mileage": 92000,
            "status": "available",
            "next_service_date": today + timedelta(days=180),
        },
        {
            "id": 10,
            "plate_number": "KKK-0101",
            "make": "Honda",
            "model": "CB500X",
            "year": 2022,
            "vehicle_type": "bike",
            "mileage": 9800,
            "status": "available",
            "next_service_date": today + timedelta(days=210),
        },
        {
            "id": 11,
            "plate_number": "KBZ-4567",
            "make": "Toyota",
            "model": "HiAce",
            "year": 2022,
            "vehicle_type": "van",
            "mileage": 14200,
            "status": "available",
            "next_service_date": today + timedelta(days=30),
        },
    ]

    drivers = [
        {"id": 1, "name": "John Doe", "phone": "555-0101", "license_number": "DL-11111"},
        {"id": 2, "name": "Jane Smith", "phone": "555-0102", "license_number": "DL-22222"},
        {"id": 3, "name": "Robert Brown", "phone": "555-0103", "license_number": "DL-33333"},
        {"id": 4, "name": "Emily Davis", "phone": "555-0104", "license_number": "DL-44444"},
    ]

    assignments = [
        {
            "id": 1,
            "vehicle_id": 1,
            "driver_id": 1,
            "assigned_at": now - timedelta(days=14),
            "released_at": None,
            "is_active": True,
        },
        {
            "id": 2,
            "vehicle_id": 2,
            "driver_id": 2,
            "assigned_at": now - timedelta(days=10),
            "released_at": None,
            "is_active": True,
        },
        {
            "id": 3,
            "vehicle_id": 3,
            "driver_id": 3,
            "assigned_at": now - timedelta(days=5),
            "released_at": None,
            "is_active": True,
        },
    ]

    services = [
        {
            "id": 1,
            "vehicle_id": 4,
            "customer_name": "Apex Logistics",
            "service_type": "Routine Inspection",
            "description": "Check brake pads and all fluid levels",
            "status": "in_progress",
            "booked_date": today - timedelta(days=2),
            "completed_date": None,
        },
        {
            "id": 2,
            "vehicle_id": 5,
            "customer_name": "City Couriers",
            "service_type": "Chain & Sprocket Check",
            "description": "Adjust chain tension and lubricate",
            "status": "in_progress",
            "booked_date": today - timedelta(days=1),
            "completed_date": None,
        },
        {
            "id": 3,
            "vehicle_id": 1,
            "customer_name": "Metro Transport",
            "service_type": "Oil Change",
            "description": "Full synthetic 5W-30 oil replacement",
            "status": "pending",
            "booked_date": today,
            "completed_date": None,
        },
    ]

    costs = [
        {
            "id": 1,
            "vehicle_id": 1,
            "category": "fuel",
            "amount": 45.50,
            "description": "50L Diesel refill",
            "log_date": today - timedelta(days=2),
        },
        {
            "id": 2,
            "vehicle_id": 2,
            "category": "service",
            "amount": 120.00,
            "description": "Oil filter and replacement",
            "log_date": today - timedelta(days=5),
        },
        {
            "id": 3,
            "vehicle_id": 3,
            "category": "parts",
            "amount": 350.00,
            "description": "New front brake pads",
            "log_date": today - timedelta(days=8),
        },
        {
            "id": 4,
            "vehicle_id": 4,
            "category": "service",
            "amount": 210.00,
            "description": "Scheduled transmission check",
            "log_date": today - timedelta(days=12),
        },
    ]

    return {
        "vehicles": vehicles,
        "drivers": drivers,
        "assignments": assignments,
        "services": services,
        "costs": costs,
    }


# Global in-memory storage for mock mode
MOCK_STORE = get_fresh_mock_db()


def reset_mock_db() -> None:
    """Reset mock storage to fresh initial seed state."""
    global MOCK_STORE
    MOCK_STORE = get_fresh_mock_db()
