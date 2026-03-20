"""
User management routes (Admin only for most actions).
Also handles the profile/change-password page for all users.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import get_current_user, hash_password, require_roles, verify_password
from app.database import get_db
from app.models import Role, User

router = APIRouter(prefix="/users")
_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATE_DIR))


@router.get("", response_class=HTMLResponse)
def list_users(
    request: Request,
    current_user: User = Depends(require_roles(Role.ADMIN)),
    db: Session = Depends(get_db),
):
    users = db.query(User).order_by(User.name).all()
    return templates.TemplateResponse(
        "users/list.html",
        {"request": request, "user": current_user, "users": users},
    )


@router.get("/new", response_class=HTMLResponse)
def new_user_form(
    request: Request,
    current_user: User = Depends(require_roles(Role.ADMIN)),
):
    return templates.TemplateResponse(
        "users/form.html",
        {
            "request": request,
            "user": current_user,
            "target": None,
            "roles": [r.value for r in Role],
        },
    )


@router.post("/new")
def create_user(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    current_user: User = Depends(require_roles(Role.ADMIN)),
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return templates.TemplateResponse(
            "users/form.html",
            {
                "request": request,
                "user": current_user,
                "target": None,
                "roles": [r.value for r in Role],
                "error": "A user with that email already exists.",
            },
            status_code=400,
        )
    new_user = User(
        name=name,
        email=email,
        hashed_password=hash_password(password),
        role=Role(role),
    )
    db.add(new_user)
    db.commit()
    return RedirectResponse(url="/users", status_code=status.HTTP_302_FOUND)


@router.get("/{user_id}/edit", response_class=HTMLResponse)
def edit_user_form(
    user_id: int,
    request: Request,
    current_user: User = Depends(require_roles(Role.ADMIN)),
    db: Session = Depends(get_db),
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        return RedirectResponse(url="/users")
    return templates.TemplateResponse(
        "users/form.html",
        {
            "request": request,
            "user": current_user,
            "target": target,
            "roles": [r.value for r in Role],
        },
    )


@router.post("/{user_id}/edit")
def update_user(
    user_id: int,
    name: str = Form(...),
    email: str = Form(...),
    role: str = Form(...),
    is_active: bool = Form(False),
    current_user: User = Depends(require_roles(Role.ADMIN)),
    db: Session = Depends(get_db),
):
    target = db.query(User).filter(User.id == user_id).first()
    if target:
        target.name = name
        target.email = email
        target.role = Role(role)
        target.is_active = is_active
        db.commit()
    return RedirectResponse(url="/users", status_code=status.HTTP_302_FOUND)


@router.get("/profile", response_class=HTMLResponse)
def profile_page(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    return templates.TemplateResponse(
        "users/profile.html",
        {"request": request, "user": current_user},
    )


@router.post("/profile/change-password")
def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    error = None
    if not verify_password(current_password, current_user.hashed_password):
        error = "Current password is incorrect."
    elif new_password != confirm_password:
        error = "New passwords do not match."
    elif len(new_password) < 8:
        error = "New password must be at least 8 characters."

    if error:
        return templates.TemplateResponse(
            "users/profile.html",
            {"request": request, "user": current_user, "error": error},
            status_code=400,
        )

    current_user.hashed_password = hash_password(new_password)
    db.commit()
    return templates.TemplateResponse(
        "users/profile.html",
        {"request": request, "user": current_user, "success": "Password updated successfully."},
    )
