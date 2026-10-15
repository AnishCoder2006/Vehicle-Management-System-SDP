"""Seed script to populate the database with initial sample data.

Safe to run multiple times.
Usage:
    python seed.py
"""

from datetime import date, datetime, timedelta
from app.database import Base, SessionLocal, engine
from app.models import Assignment, CostLog, Driver, ServiceRecord, Vehicle


def seed_database():
    print("Creating tables if they don't exist...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("Clearing existing data...")
        # Delete dependent tables first to respect foreign keys
        db.query(CostLog).delete()
        db.query(ServiceRecord).delete()
        db.query(Assignment).delete()
        db.query(Driver).delete()
        db.query(Vehicle).delete()
        db.commit()

        today = date.today()
        now = datetime.now()

        print("Inserting 10 vehicles...")
        vehicles = [
            Vehicle(
                plate_number="KAA-1001",
                make="Toyota",
                model="Corolla",
                year=2021,
                vehicle_type="car",
                mileage=24500,
                status="assigned",
                next_service_date=today - timedelta(days=3),  # Overdue (1)
            ),
            Vehicle(
                plate_number="KBB-2002",
                make="Ford",
                model="Transit",
                year=2020,
                vehicle_type="van",
                mileage=48000,
                status="assigned",
                next_service_date=today + timedelta(days=2),  # Due in 2 days (2)
            ),
            Vehicle(
                plate_number="KCC-3003",
                make="Isuzu",
                model="NPR",
                year=2019,
                vehicle_type="truck",
                mileage=85000,
                status="assigned",
                next_service_date=today + timedelta(days=5),  # Due in 5 days (3)
            ),
            Vehicle(
                plate_number="KDD-4004",
                make="Honda",
                model="Civic",
                year=2022,
                vehicle_type="car",
                mileage=15200,
                status="in_service",
                next_service_date=today + timedelta(days=45),
            ),
            Vehicle(
                plate_number="KEE-5005",
                make="Yamaha",
                model="MT-07",
                year=2023,
                vehicle_type="bike",
                mileage=6100,
                status="in_service",
                next_service_date=today + timedelta(days=60),
            ),
            Vehicle(
                plate_number="KFF-6006",
                make="Mercedes",
                model="Sprinter",
                year=2021,
                vehicle_type="van",
                mileage=39400,
                status="available",
                next_service_date=today + timedelta(days=90),
            ),
            Vehicle(
                plate_number="KGG-7007",
                make="Volvo",
                model="FH16",
                year=2018,
                vehicle_type="truck",
                mileage=124000,
                status="available",
                next_service_date=None,
            ),
            Vehicle(
                plate_number="KHH-8008",
                make="Hyundai",
                model="Elantra",
                year=2022,
                vehicle_type="car",
                mileage=18700,
                status="available",
                next_service_date=today + timedelta(days=120),
            ),
            Vehicle(
                plate_number="KII-9009",
                make="Kawasaki",
                model="Ninja",
                year=2020,
                vehicle_type="bike",
                mileage=11300,
                status="available",
                next_service_date=None,
            ),
            Vehicle(
                plate_number="KJJ-0101",
                make="Nissan",
                model="NV200",
                year=2021,
                vehicle_type="van",
                mileage=31000,
                status="available",
                next_service_date=today + timedelta(days=30),
            ),
        ]
        db.add_all(vehicles)
        db.commit()

        # Refresh vehicles to get their auto-assigned IDs
        for v in vehicles:
            db.refresh(v)

        print("Inserting 4 drivers...")
        drivers = [
            Driver(name="John Mwangi", phone="0711-234567", license_number="DL-10001"),
            Driver(name="Grace Wanjiku", phone="0722-345678", license_number="DL-10002"),
            Driver(name="David Ochieng", phone="0733-456789", license_number="DL-10003"),
            Driver(name="Fatuma Hassan", phone="0744-567890", license_number="DL-10004"),
        ]
        db.add_all(drivers)
        db.commit()

        for d in drivers:
            db.refresh(d)

        print("Inserting 3 active assignments...")
        assignments = [
            Assignment(
                vehicle_id=vehicles[0].id,
                driver_id=drivers[0].id,
                assigned_at=now - timedelta(days=10),
                released_at=None,
                is_active=True,
            ),
            Assignment(
                vehicle_id=vehicles[1].id,
                driver_id=drivers[1].id,
                assigned_at=now - timedelta(days=5),
                released_at=None,
                is_active=True,
            ),
            Assignment(
                vehicle_id=vehicles[2].id,
                driver_id=drivers[2].id,
                assigned_at=now - timedelta(days=1),
                released_at=None,
                is_active=True,
            ),
        ]
        db.add_all(assignments)
        db.commit()

        print("Inserting 6 service records across all 3 statuses...")
        services = [
            ServiceRecord(
                vehicle_id=vehicles[0].id,
                customer_name="Apex Logistics",
                service_type="Routine Inspection",
                description="Check brake pads and all fluid levels",
                status="pending",
                booked_date=today - timedelta(days=2),
                completed_date=None,
            ),
            ServiceRecord(
                vehicle_id=vehicles[1].id,
                customer_name="Metro Couriers",
                service_type="Tire Rotation",
                description="Rotate tires and check wheel balance",
                status="pending",
                booked_date=today - timedelta(days=1),
                completed_date=None,
            ),
            ServiceRecord(
                vehicle_id=vehicles[3].id,
                customer_name="Swift Freight",
                service_type="Engine Diagnostics",
                description="Investigate check engine light code",
                status="in_progress",
                booked_date=today - timedelta(days=4),
                completed_date=None,
            ),
            ServiceRecord(
                vehicle_id=vehicles[4].id,
                customer_name="City Express",
                service_type="Chain & Sprocket",
                description="Replace worn drive chain and adjust tension",
                status="in_progress",
                booked_date=today - timedelta(days=3),
                completed_date=None,
            ),
            ServiceRecord(
                vehicle_id=vehicles[5].id,
                customer_name="Quick Trans",
                service_type="Oil & Filter Change",
                description="Full synthetic oil change and filter replacement",
                status="completed",
                booked_date=today - timedelta(days=15),
                completed_date=today - timedelta(days=14),
            ),
            ServiceRecord(
                vehicle_id=vehicles[6].id,
                customer_name="Prime Haulers",
                service_type="Brake Overhaul",
                description="Complete overhaul of heavy-duty air brake drums",
                status="completed",
                booked_date=today - timedelta(days=25),
                completed_date=today - timedelta(days=24),
            ),
        ]
        db.add_all(services)
        db.commit()

        print("Inserting 15 cost logs over the last 3 months...")
        costs = [
            CostLog(vehicle_id=vehicles[0].id, category="fuel", amount=85.00, description="Full tank petrol", log_date=today - timedelta(days=2)),
            CostLog(vehicle_id=vehicles[1].id, category="fuel", amount=120.00, description="Diesel top-up", log_date=today - timedelta(days=6)),
            CostLog(vehicle_id=vehicles[2].id, category="parts", amount=310.50, description="Heavy-duty battery", log_date=today - timedelta(days=12)),
            CostLog(vehicle_id=vehicles[3].id, category="service", amount=250.00, description="Diagnostic labor fee", log_date=today - timedelta(days=18)),
            CostLog(vehicle_id=vehicles[4].id, category="fuel", amount=35.00, description="Bike fuel refill", log_date=today - timedelta(days=22)),
            CostLog(vehicle_id=vehicles[5].id, category="service", amount=180.00, description="Oil service labor", log_date=today - timedelta(days=28)),
            CostLog(vehicle_id=vehicles[0].id, category="parts", amount=95.00, description="Wiper blades and cabin filter", log_date=today - timedelta(days=35)),
            CostLog(vehicle_id=vehicles[1].id, category="service", amount=140.00, description="Wheel alignment", log_date=today - timedelta(days=42)),
            CostLog(vehicle_id=vehicles[2].id, category="fuel", amount=260.00, description="Long-haul diesel", log_date=today - timedelta(days=49)),
            CostLog(vehicle_id=vehicles[6].id, category="parts", amount=520.00, description="Air brake drum replacement parts", log_date=today - timedelta(days=55)),
            CostLog(vehicle_id=vehicles[7].id, category="fuel", amount=75.00, description="Petrol refill", log_date=today - timedelta(days=62)),
            CostLog(vehicle_id=vehicles[5].id, category="parts", amount=110.00, description="Synthetic oil and oil filter", log_date=today - timedelta(days=70)),
            CostLog(vehicle_id=vehicles[6].id, category="service", amount=350.00, description="Brake overhaul workshop labor", log_date=today - timedelta(days=75)),
            CostLog(vehicle_id=vehicles[8].id, category="parts", amount=65.00, description="Spark plugs and air filter", log_date=today - timedelta(days=80)),
            CostLog(vehicle_id=vehicles[9].id, category="fuel", amount=90.00, description="Standard diesel refill", log_date=today - timedelta(days=85)),
        ]
        db.add_all(costs)
        db.commit()

        print("Database seeded successfully!")
        print(f"Summary: {len(vehicles)} vehicles, {len(drivers)} drivers, {len(assignments)} assignments, {len(services)} service records, {len(costs)} cost logs.")

    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
