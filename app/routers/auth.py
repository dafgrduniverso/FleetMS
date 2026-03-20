"""
Authentication routes: login, logout, dashboard.
"""

from datetime import timedelta

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_current_user,
    verify_password,
)
from app.database import get_db
from app.models import Contract, MaintenanceRecord, User, Vehicle, VehicleStatus

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("auth/login.html", {"request": request})


@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email, User.is_active == True).first()
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            "auth/login.html",
            {"request": request, "error": "Invalid email or password."},
            status_code=400,
        )

    token = create_access_token(
        {"sub": str(user.id)},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    response = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
    )
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("access_token")
    return response


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    total_vehicles = db.query(Vehicle).count()
    available = db.query(Vehicle).filter(Vehicle.status == VehicleStatus.AVAILABLE).count()
    in_use = db.query(Vehicle).filter(Vehicle.status == VehicleStatus.IN_USE).count()
    in_maintenance = db.query(Vehicle).filter(Vehicle.status == VehicleStatus.MAINTENANCE).count()
    active_contracts = db.query(Contract).filter(Contract.status == "ACTIVE").count()
    recent_maintenance = (
        db.query(MaintenanceRecord)
        .order_by(MaintenanceRecord.created_at.desc())
        .limit(5)
        .all()
    )

    return templates.TemplateResponse(
        "auth/dashboard.html",
        {
            "request": request,
            "user": current_user,
            "total_vehicles": total_vehicles,
            "available": available,
            "in_use": in_use,
            "in_maintenance": in_maintenance,
            "active_contracts": active_contracts,
            "recent_maintenance": recent_maintenance,
        },
    )
