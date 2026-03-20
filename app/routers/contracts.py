"""
Contract routes.
Fleet Managers create contracts that assign a vehicle to a driver.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_roles
from app.database import get_db
from app.models import Contract, ContractStatus, Driver, Role, User, Vehicle, VehicleStatus

router = APIRouter(prefix="/contracts")
_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))

MANAGERS = (Role.ADMIN, Role.FLEET_MANAGER)


@router.get("", response_class=HTMLResponse)
def list_contracts(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role in MANAGERS or current_user.role == Role.FINANCE:
        contracts = db.query(Contract).order_by(Contract.start_date.desc()).all()
    else:
        contracts = (
            db.query(Contract)
            .filter(Contract.driver_id == current_user.id)
            .order_by(Contract.start_date.desc())
            .all()
        )

    return templates.TemplateResponse(
        "contracts/list.html",
        {
            "request": request,
            "user": current_user,
            "contracts": contracts,
            "statuses": [s.value for s in ContractStatus],
        },
    )


@router.get("/new", response_class=HTMLResponse)
def new_contract_form(
    request: Request,
    current_user: User = Depends(require_roles(*MANAGERS)),
    db: Session = Depends(get_db),
):
    available_vehicles = (
        db.query(Vehicle)
        .filter(Vehicle.status == VehicleStatus.AVAILABLE)
        .order_by(Vehicle.brand, Vehicle.model)
        .all()
    )
    drivers = (
        db.query(Driver)
        .join(User, Driver.user_id == User.id)
        .filter(User.is_active == True)
        .order_by(User.name)
        .all()
    )
    return templates.TemplateResponse(
        "contracts/form.html",
        {
            "request": request,
            "user": current_user,
            "contract": None,
            "vehicles": available_vehicles,
            "drivers": drivers,
        },
    )


@router.post("/new")
def create_contract(
    vehicle_id: int = Form(...),
    driver_id: int = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(""),
    notes: str = Form(""),
    current_user: User = Depends(require_roles(*MANAGERS)),
    db: Session = Depends(get_db),
):
    from datetime import date
    # Find driver profile
    driver_profile = db.query(Driver).filter(Driver.user_id == driver_id).first()

    contract = Contract(
        vehicle_id=vehicle_id,
        driver_id=driver_id,
        driver_profile_id=driver_profile.id if driver_profile else None,
        start_date=date.fromisoformat(start_date),
        end_date=date.fromisoformat(end_date) if end_date else None,
        notes=notes or None,
        created_by_id=current_user.id,
    )
    db.add(contract)

    # Mark vehicle as in use
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if vehicle:
        vehicle.status = VehicleStatus.IN_USE

    db.commit()
    return RedirectResponse(url="/contracts", status_code=status.HTTP_302_FOUND)


@router.get("/{contract_id}", response_class=HTMLResponse)
def contract_detail(
    contract_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        return RedirectResponse(url="/contracts")

    # Employees can only see their own contracts
    if current_user.role == Role.EMPLOYEE and contract.driver_id != current_user.id:
        return RedirectResponse(url="/contracts")

    return templates.TemplateResponse(
        "contracts/detail.html",
        {"request": request, "user": current_user, "contract": contract},
    )


@router.get("/{contract_id}/edit", response_class=HTMLResponse)
def edit_contract_form(
    contract_id: int,
    request: Request,
    current_user: User = Depends(require_roles(*MANAGERS)),
    db: Session = Depends(get_db),
):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        return RedirectResponse(url="/contracts")

    vehicles = db.query(Vehicle).order_by(Vehicle.brand, Vehicle.model).all()
    drivers = (
        db.query(Driver)
        .join(User, Driver.user_id == User.id)
        .filter(User.is_active == True)
        .order_by(User.name)
        .all()
    )
    return templates.TemplateResponse(
        "contracts/form.html",
        {
            "request": request,
            "user": current_user,
            "contract": contract,
            "vehicles": vehicles,
            "drivers": drivers,
            "statuses": [s.value for s in ContractStatus],
        },
    )


@router.post("/{contract_id}/edit")
def update_contract(
    contract_id: int,
    vehicle_id: int = Form(...),
    driver_id: int = Form(...),
    start_date: str = Form(...),
    end_date: str = Form(""),
    contract_status: str = Form(...),
    notes: str = Form(""),
    current_user: User = Depends(require_roles(*MANAGERS)),
    db: Session = Depends(get_db),
):
    from datetime import date
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if contract:
        old_vehicle_id = contract.vehicle_id
        new_status = ContractStatus(contract_status)

        contract.vehicle_id = vehicle_id
        contract.driver_id = driver_id
        contract.start_date = date.fromisoformat(start_date)
        contract.end_date = date.fromisoformat(end_date) if end_date else None
        contract.status = new_status
        contract.notes = notes or None

        # Update vehicle statuses if contract ended or vehicle changed
        if new_status != ContractStatus.ACTIVE:
            old_vehicle = db.query(Vehicle).filter(Vehicle.id == old_vehicle_id).first()
            if old_vehicle:
                old_vehicle.status = VehicleStatus.AVAILABLE

        db.commit()
    return RedirectResponse(url=f"/contracts/{contract_id}", status_code=status.HTTP_302_FOUND)


@router.post("/{contract_id}/delete")
def delete_contract(
    contract_id: int,
    current_user: User = Depends(require_roles(Role.ADMIN)),
    db: Session = Depends(get_db),
):
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if contract:
        # Free up the vehicle
        vehicle = db.query(Vehicle).filter(Vehicle.id == contract.vehicle_id).first()
        if vehicle and vehicle.status == VehicleStatus.IN_USE:
            vehicle.status = VehicleStatus.AVAILABLE
        db.delete(contract)
        db.commit()
    return RedirectResponse(url="/contracts", status_code=status.HTTP_302_FOUND)
