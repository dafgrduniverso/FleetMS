"""
Database models — every table in the system is defined here.
SQLAlchemy maps these Python classes to actual database tables.
"""

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Enum, Float,
    ForeignKey, Integer, String, Text
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


# ---------------------------------------------------------------------------
# Enumerations (controlled vocabularies)
# ---------------------------------------------------------------------------

class Role(str, enum.Enum):
    ADMIN = "ADMIN"
    FLEET_MANAGER = "FLEET_MANAGER"
    EMPLOYEE = "EMPLOYEE"
    FINANCE = "FINANCE"


class VehicleStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    IN_USE = "IN_USE"
    MAINTENANCE = "MAINTENANCE"
    DECOMMISSIONED = "DECOMMISSIONED"


class FuelType(str, enum.Enum):
    PETROL = "PETROL"
    DIESEL = "DIESEL"
    ELECTRIC = "ELECTRIC"
    HYBRID = "HYBRID"


class MaintenanceType(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    REPAIR = "REPAIR"
    INSPECTION = "INSPECTION"
    TIRE = "TIRE"
    OTHER = "OTHER"


class ContractStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    hashed_password = Column(String(200), nullable=False)
    role = Column(Enum(Role), nullable=False, default=Role.EMPLOYEE)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # An employee may have a driver profile
    driver_profile = relationship("Driver", back_populates="user", uselist=False)
    # Contracts where this user is the assigned driver
    contracts = relationship("Contract", foreign_keys="Contract.driver_id", back_populates="driver")
    # Contracts this user created
    contracts_created = relationship("Contract", foreign_keys="Contract.created_by_id", back_populates="created_by")


class Driver(Base):
    """Extended profile for users who drive company vehicles."""
    __tablename__ = "drivers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    license_number = Column(String(50), unique=True, nullable=False)
    license_expiry = Column(Date, nullable=False)
    notes = Column(Text, nullable=True)

    user = relationship("User", back_populates="driver_profile")
    contracts = relationship("Contract", back_populates="driver_profile")


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    plate = Column(String(20), unique=True, nullable=False, index=True)
    brand = Column(String(50), nullable=False)
    model = Column(String(50), nullable=False)
    year = Column(Integer, nullable=False)
    color = Column(String(30), nullable=True)
    fuel_type = Column(Enum(FuelType), nullable=False)
    status = Column(Enum(VehicleStatus), nullable=False, default=VehicleStatus.AVAILABLE)
    current_km = Column(Integer, default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    maintenance_records = relationship("MaintenanceRecord", back_populates="vehicle")
    contracts = relationship("Contract", back_populates="vehicle")


class MaintenanceRecord(Base):
    __tablename__ = "maintenance_records"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    maintenance_type = Column(Enum(MaintenanceType), nullable=False)
    date = Column(Date, nullable=False)
    cost = Column(Float, nullable=True)
    km_at_service = Column(Integer, nullable=True)
    next_service_km = Column(Integer, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    vehicle = relationship("Vehicle", back_populates="maintenance_records")


class Contract(Base):
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"), nullable=False)
    driver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    driver_profile_id = Column(Integer, ForeignKey("drivers.id"), nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    status = Column(Enum(ContractStatus), nullable=False, default=ContractStatus.ACTIVE)
    notes = Column(Text, nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    vehicle = relationship("Vehicle", back_populates="contracts")
    driver = relationship("User", foreign_keys=[driver_id], back_populates="contracts")
    driver_profile = relationship("Driver", back_populates="contracts")
    created_by = relationship("User", foreign_keys=[created_by_id], back_populates="contracts_created")
