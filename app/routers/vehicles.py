"""
Vehicle management routes.
- List, create, edit, delete vehicles
- Accessible by Admin and Fleet Manager; Employees see only their assigned vehicle
"""

from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_roles
from app.database import get_db
from app.models import Contract, ContractStatus, FuelType, Role, User, Vehicle, VehicleStatus

router = APIRouter(prefix="/vehicles")
_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))

MANAGERS = (Role.ADMIN, Role.FLEET_MANAGER)


@router.get("", response_class=HTMLResponse)
def list_vehicles(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role in MANAGERS or current_user.role == Role.FINANCE:
        vehicles = db.query(Vehicle).order_by(Vehicle.brand, Vehicle.model).all()
    else:
        # Employee: only see vehicles assigned to them via an active contract
        contract = (
            db.query(Contract)
            .filter(
                Contract.driver_id == current_user.id,
                Contract.status == ContractStatus.ACTIVE,
            )
            .first()
        )
        vehicles = [contract.vehicle] if contract else []

    return templates.TemplateResponse(
        "vehicles/list.html",
        {"request": request, "user": current_user, "vehicles": vehicles},
    )


@router.get("/new", response_class=HTMLResponse)
def new_vehicle_form(
    request: Request,
    current_user: User = Depends(require_roles(*MANAGERS)),
):
    return templates.TemplateResponse(
        "vehicles/form.html",
        {
            "request": request,
            "user": current_user,
            "vehicle": None,
            "fuel_types": [f.value for f in FuelType],
            "statuses": [s.value for s in VehicleStatus],
        },
    )


@router.post("/new")
def create_vehicle(
    request: Request,
    plate: str = Form(...),
    brand: str = Form(...),
    model: str = Form(...),
    year: int = Form(...),
    color: str = Form(""),
    fuel_type: str = Form(...),
    current_km: int = Form(0),
    notes: str = Form(""),
    current_user: User = Depends(require_roles(*MANAGERS)),
    db: Session = Depends(get_db),
):
    vehicle = Vehicle(
        plate=plate.upper().strip(),
        brand=brand,
        model=model,
        year=year,
        color=color or None,
        fuel_type=FuelType(fuel_type),
        current_km=current_km,
        notes=notes or None,
    )
    db.add(vehicle)
    db.commit()
    return RedirectResponse(url="/vehicles", status_code=status.HTTP_302_FOUND)


@router.get("/{vehicle_id}", response_class=HTMLResponse)
def vehicle_detail(
    vehicle_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        return RedirectResponse(url="/vehicles")

    return templates.TemplateResponse(
        "vehicles/detail.html",
        {
            "request": request,
            "user": current_user,
            "vehicle": vehicle,
            "maintenance_records": sorted(vehicle.maintenance_records, key=lambda r: r.date, reverse=True),
            "contracts": sorted(vehicle.contracts, key=lambda c: c.start_date, reverse=True),
        },
    )


@router.get("/{vehicle_id}/edit", response_class=HTMLResponse)
def edit_vehicle_form(
    vehicle_id: int,
    request: Request,
    current_user: User = Depends(require_roles(*MANAGERS)),
    db: Session = Depends(get_db),
):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        return RedirectResponse(url="/vehicles")

    return templates.TemplateResponse(
        "vehicles/form.html",
        {
            "request": request,
            "user": current_user,
            "vehicle": vehicle,
            "fuel_types": [f.value for f in FuelType],
            "statuses": [s.value for s in VehicleStatus],
        },
    )


@router.post("/{vehicle_id}/edit")
def update_vehicle(
    vehicle_id: int,
    plate: str = Form(...),
    brand: str = Form(...),
    model: str = Form(...),
    year: int = Form(...),
    color: str = Form(""),
    fuel_type: str = Form(...),
    vehicle_status: str = Form(...),
    current_km: int = Form(0),
    notes: str = Form(""),
    current_user: User = Depends(require_roles(*MANAGERS)),
    db: Session = Depends(get_db),
):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if vehicle:
        vehicle.plate = plate.upper().strip()
        vehicle.brand = brand
        vehicle.model = model
        vehicle.year = year
        vehicle.color = color or None
        vehicle.fuel_type = FuelType(fuel_type)
        vehicle.status = VehicleStatus(vehicle_status)
        vehicle.current_km = current_km
        vehicle.notes = notes or None
        db.commit()
    return RedirectResponse(url=f"/vehicles/{vehicle_id}", status_code=status.HTTP_302_FOUND)


@router.post("/{vehicle_id}/delete")
def delete_vehicle(
    vehicle_id: int,
    current_user: User = Depends(require_roles(Role.ADMIN)),
    db: Session = Depends(get_db),
):
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if vehicle:
        db.delete(vehicle)
        db.commit()
    return RedirectResponse(url="/vehicles", status_code=status.HTTP_302_FOUND)
