from datetime import date, datetime
from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    plate_number = Column(String(50), unique=True, nullable=False, index=True)
    make = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    year = Column(Integer, nullable=True)
    vehicle_type = Column(String(50), nullable=True)
    mileage = Column(Integer, default=0, nullable=False)
    status = Column(String(50), default="available", nullable=False)
    next_service_date = Column(Date, nullable=True)

    # Relationships for convenience
    assignments = relationship("Assignment", back_populates="vehicle", cascade="all, delete-orphan")
    service_records = relationship("ServiceRecord", back_populates="vehicle", cascade="all, delete-orphan")
    cost_logs = relationship("CostLog", back_populates="vehicle", cascade="all, delete-orphan")
    sensor_readings = relationship("VehicleSensorReading", back_populates="vehicle", cascade="all, delete-orphan")


class Driver(Base):
    __tablename__ = "drivers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(50), nullable=False)
    license_number = Column(String(50), unique=True, nullable=False, index=True)

    assignments = relationship("Assignment", back_populates="driver", cascade="all, delete-orphan")


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=False)
    assigned_at = Column(DateTime, default=datetime.now, nullable=False)
    released_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    vehicle = relationship("Vehicle", back_populates="assignments")
    driver = relationship("Driver", back_populates="assignments")


class ServiceRecord(Base):
    __tablename__ = "service_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    customer_name = Column(String(100), nullable=False)
    service_type = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    status = Column(String(50), default="pending", nullable=False)
    booked_date = Column(Date, default=date.today, nullable=False)
    completed_date = Column(Date, nullable=True)

    vehicle = relationship("Vehicle", back_populates="service_records")


class CostLog(Base):
    __tablename__ = "cost_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    category = Column(String(50), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String(255), nullable=True)
    log_date = Column(Date, default=date.today, nullable=False)

    vehicle = relationship("Vehicle", back_populates="cost_logs")

class VehicleSensorReading(Base):
    __tablename__ = "vehicle_sensor_readings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False, index=True)
    time_step = Column(Integer, nullable=False)
    features = Column(JSON, nullable=False)
    recorded_at = Column(DateTime, default=datetime.now, nullable=False)

    vehicle = relationship("Vehicle", back_populates="sensor_readings")
