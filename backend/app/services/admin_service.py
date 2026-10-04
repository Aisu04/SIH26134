from sqlalchemy.orm import Session

from app.models import User
from app.services.auth_service import hash_password


def create_initial_admin(db: Session, full_name: str, email: str, password: str) -> User:
    normalized_email = email.strip().lower()
    if len(full_name.strip()) < 2:
        raise ValueError("Full name must be at least 2 characters.")
    if not normalized_email or "@" not in normalized_email:
        raise ValueError("Enter a valid email address.")
    password_bytes = len(password.encode("utf-8"))
    if password_bytes < 8 or password_bytes > 72:
        raise ValueError("Password must be 8-72 UTF-8 bytes.")
    if db.query(User).filter(User.role == "admin").first() is not None:
        raise RuntimeError("An admin account already exists; bootstrap is disabled.")
    if db.query(User).filter(User.email == normalized_email).first() is not None:
        raise ValueError("A user with that email already exists.")

    admin = User(
        full_name=full_name.strip(),
        email=normalized_email,
        password_hash=hash_password(password),
        role="admin",
        is_active=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin