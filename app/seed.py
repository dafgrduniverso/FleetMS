"""
Seeds the database with the first admin user on first launch.
Credentials can be changed after logging in.
"""

from app.database import SessionLocal
from app.models import Role, User
from app.auth import hash_password


def seed_admin():
    db = SessionLocal()
    try:
        exists = db.query(User).filter(User.email == "admin@fleet.local").first()
        if not exists:
            admin = User(
                name="Administrator",
                email="admin@fleet.local",
                hashed_password=hash_password("admin1234"),
                role=Role.ADMIN,
            )
            db.add(admin)
            db.commit()
            print("✓ Default admin created — email: admin@fleet.local  password: admin1234")
            print("  Change this password immediately after first login!")
    finally:
        db.close()
