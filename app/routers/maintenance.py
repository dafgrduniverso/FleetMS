"""
Maintenance record routes.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_roles
from app.database import get_db
from app.models import MaintenanceRecord, MaintenanceType, Role, User, Vehicle

router = APIRouter(prefix="/maintenance")
_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))

MANAGERS = (Role.ADMIN, Role.FLEET_MANAGER)


@router.get("", response_class=HTMLResponse)
def list_maintenance(
    request: Request,
    current_user: User = Depends(require_roles(*MANAGERS, Role.FINANCE)),
    db: Session = Depends(get_db),
):
    records = (
        db.query(MaintenanceRecord)
        .order_by(MaintenanceRecord.date.desc())
        .all()
    )
    return templates.TemplateResponse(
        "maintenance/list.html",
        {"request": request, "user": current_user, "records": records},
    )


@router.get("/new", response_class=HTMLResponse)
def new_maintenance_form(
    request: Request,
    current_user: User = Depends(require_roles(*MANAGERS)),
    db: Session = Depends(get_db),
):
    vehicles = db.query(Vehicle).order_by(Vehicle.brand, Vehicle.model).all()
    return templates.TemplateResponse(
        "maintenance/form.html",
        {
            "request": request,
            "user": current_user,
            "record": None,
            "vehicles": vehicles,
            "maintenance_types": [t.value for t in MaintenanceType],
        },
    )


@router.post("/new")
def create_maintenance(
    vehicle_id: int = Form(...),
    maintenance_type: str = Form(...),
    date: str = Form(...),
    cost: str = Form(""),
    km_at_service: str = Form(""),
    next_service_km: str = Form(""),
    description: str = Form(""),
    current_user: User = Depends(require_roles(*MANAGERS)),
    db: Session = Depends(get_db),
):
    from datetime import date as date_type
    record = MaintenanceRecord(
        vehicle_id=vehicle_id,
        maintenance_type=MaintenanceType(maintenance_type),
        date=date_type.fromisoformat(date),
        cost=float(cost) if cost else None,
        km_at_service=int(km_at_service) if km_at_service else None,
        next_service_km=int(next_service_km) if next_service_km else None,
        description=description or None,
    )
    db.add(record)
    db.commit()
    return RedirectResponse(url="/maintenance", status_code=status.HTTP_302_FOUND)


@router.get("/{record_id}/edit", response_class=HTMLResponse)
def edit_maintenance_form(
    record_id: int,
    request: Request,
    current_user: User = Depends(require_roles(*MANAGERS)),
    db: Session = Depends(get_db),
):
    record = db.query(MaintenanceRecord).filter(MaintenanceRecord.id == record_id).first()
    if not record:
        return RedirectResponse(url="/maintenance")
    vehicles = db.query(Vehicle).order_by(Vehicle.brand, Vehicle.model).all()
    return templates.TemplateResponse(
        "maintenance/form.html",
        {
            "request": request,
            "user": current_user,
            "record": record,
            "vehicles": vehicles,
            "maintenance_types": [t.value for t in MaintenanceType],
        },
    )


@router.post("/{record_id}/edit")
def update_maintenance(
    record_id: int,
    vehicle_id: int = Form(...),
    maintenance_type: str = Form(...),
    date: str = Form(...),
    cost: str = Form(""),
    km_at_service: str = Form(""),
    next_service_km: str = Form(""),
    description: str = Form(""),
    current_user: User = Depends(require_roles(*MANAGERS)),
    db: Session = Depends(get_db),
):
    from datetime import date as date_type
    record = db.query(MaintenanceRecord).filter(MaintenanceRecord.id == record_id).first()
    if record:
        record.vehicle_id = vehicle_id
        record.maintenance_type = MaintenanceType(maintenance_type)
        record.date = date_type.fromisoformat(date)
        record.cost = float(cost) if cost else None
        record.km_at_service = int(km_at_service) if km_at_service else None
        record.next_service_km = int(next_service_km) if next_service_km else None
        record.description = description or None
        db.commit()
    return RedirectResponse(url="/maintenance", status_code=status.HTTP_302_FOUND)


@router.post("/{record_id}/delete")
def delete_maintenance(
    record_id: int,
    current_user: User = Depends(require_roles(*MANAGERS)),
    db: Session = Depends(get_db),
):
    record = db.query(MaintenanceRecord).filter(MaintenanceRecord.id == record_id).first()
    if record:
        db.delete(record)
        db.commit()
    return RedirectResponse(url="/maintenance", status_code=status.HTTP_302_FOUND)
