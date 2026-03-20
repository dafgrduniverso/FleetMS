"""
Driver profile routes.
A Driver profile is an extension of a User account with license info.
"""

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import get_current_user, require_roles
from app.database import get_db
from app.models import Driver, Role, User

router = APIRouter(prefix="/drivers")
templates = Jinja2Templates(directory="app/templates")

MANAGERS = (Role.ADMIN, Role.FLEET_MANAGER)


@router.get("", response_class=HTMLResponse)
def list_drivers(
    request: Request,
    current_user: User = Depends(require_roles(*MANAGERS, Role.FINANCE)),
    db: Session = Depends(get_db),
):
    drivers = (
        db.query(Driver)
        .join(User, Driver.user_id == User.id)
        .order_by(User.name)
        .all()
    )
    return templates.TemplateResponse(
        "drivers/list.html",
        {"request": request, "user": current_user, "drivers": drivers},
    )


@router.get("/new", response_class=HTMLResponse)
def new_driver_form(
    request: Request,
    current_user: User = Depends(require_roles(*MANAGERS)),
    db: Session = Depends(get_db),
):
    # Only users without a driver profile can be assigned one
    existing_driver_user_ids = {d.user_id for d in db.query(Driver).all()}
    eligible_users = (
        db.query(User)
        .filter(User.is_active == True, ~User.id.in_(existing_driver_user_ids))
        .order_by(User.name)
        .all()
    )
    return templates.TemplateResponse(
        "drivers/form.html",
        {
            "request": request,
            "user": current_user,
            "driver": None,
            "eligible_users": eligible_users,
        },
    )


@router.post("/new")
def create_driver(
    user_id: int = Form(...),
    license_number: str = Form(...),
    license_expiry: str = Form(...),
    notes: str = Form(""),
    current_user: User = Depends(require_roles(*MANAGERS)),
    db: Session = Depends(get_db),
):
    from datetime import date
    driver = Driver(
        user_id=user_id,
        license_number=license_number.strip(),
        license_expiry=date.fromisoformat(license_expiry),
        notes=notes or None,
    )
    db.add(driver)
    db.commit()
    return RedirectResponse(url="/drivers", status_code=status.HTTP_302_FOUND)


@router.get("/{driver_id}/edit", response_class=HTMLResponse)
def edit_driver_form(
    driver_id: int,
    request: Request,
    current_user: User = Depends(require_roles(*MANAGERS)),
    db: Session = Depends(get_db),
):
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        return RedirectResponse(url="/drivers")
    return templates.TemplateResponse(
        "drivers/form.html",
        {
            "request": request,
            "user": current_user,
            "driver": driver,
            "eligible_users": [driver.user],
        },
    )


@router.post("/{driver_id}/edit")
def update_driver(
    driver_id: int,
    license_number: str = Form(...),
    license_expiry: str = Form(...),
    notes: str = Form(""),
    current_user: User = Depends(require_roles(*MANAGERS)),
    db: Session = Depends(get_db),
):
    from datetime import date
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if driver:
        driver.license_number = license_number.strip()
        driver.license_expiry = date.fromisoformat(license_expiry)
        driver.notes = notes or None
        db.commit()
    return RedirectResponse(url="/drivers", status_code=status.HTTP_302_FOUND)


@router.post("/{driver_id}/delete")
def delete_driver(
    driver_id: int,
    current_user: User = Depends(require_roles(Role.ADMIN)),
    db: Session = Depends(get_db),
):
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if driver:
        db.delete(driver)
        db.commit()
    return RedirectResponse(url="/drivers", status_code=status.HTTP_302_FOUND)
