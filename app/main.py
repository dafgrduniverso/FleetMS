"""
Application entry point.

Registers all routers and creates the database tables on first run.
Run with:  python -m uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from app.database import engine
from app.models import Base
from app.routers import auth, vehicles, drivers, maintenance, contracts, users
from app.seed import seed_admin

# Create all tables if they don't exist yet
Base.metadata.create_all(bind=engine)

# Seed the first admin user so the system is usable on first launch
seed_admin()

app = FastAPI(title="Fleet Management System", docs_url=None, redoc_url=None)

# Serve static files (custom CSS, images)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Register feature routers
app.include_router(auth.router)
app.include_router(vehicles.router)
app.include_router(drivers.router)
app.include_router(maintenance.router)
app.include_router(contracts.router)
app.include_router(users.router)


@app.get("/")
def root():
    return RedirectResponse(url="/dashboard")
