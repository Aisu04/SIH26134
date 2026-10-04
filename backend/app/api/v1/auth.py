from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import get_current_user, require_roles
from app.models import Institution, User
from app.schemas import (
    AdminUserCreate,
    InstitutionCreate,
    InstitutionPublic,
    Token,
    UserCreate,
    UserLogin,
    UserPublic,
)
from app.services.auth_service import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/v1", tags=["auth"])


@router.post("/auth/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    normalized_email = payload.email.lower().strip()
    existing_user = db.query(User).filter(User.email == normalized_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with that email already exists.",
        )

    user = User(
        full_name=payload.full_name.strip(),
        email=normalized_email,
        password_hash=hash_password(payload.password),
        role="learner",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/auth/login", response_model=Token)
def login_user(payload: UserLogin, db: Session = Depends(get_db)) -> dict[str, str]:
    normalized_email = payload.email.lower().strip()
    user = db.query(User).filter(User.email == normalized_email).first()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )

    token = create_access_token(str(user.id), user.role)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/auth/logout")
def logout_user(current_user: User = Depends(get_current_user)) -> dict[str, str]:
    # In a production app, this would revoke a token server-side or clear secure cookies.
    return {
        "message": "Logout successful. Client should discard the JWT token.",
        "user_id": str(current_user.id),
    }


@router.get("/auth/me", response_model=UserPublic)
def get_current_user_profile(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.get("/users/{user_id}", response_model=UserPublic)
def get_user_by_id(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if str(current_user.id) != str(user_id) and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own profile unless you are an admin.",
        )

    return user


@router.get("/admin/check")
def admin_check(current_user: User = Depends(require_roles("admin"))) -> dict[str, str]:
    return {"message": f"Admin access granted for {current_user.full_name}."}


@router.post(
    "/admin/institutions",
    response_model=InstitutionPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_institution(
    payload: InstitutionCreate,
    _current_admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> Institution:
    name = payload.name.strip()
    existing = db.query(Institution).filter(Institution.name.ilike(name)).first()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Institution already exists.")

    institution = Institution(
        name=name,
        sector=payload.sector.strip(),
        location=payload.location.strip() if payload.location else None,
        description=payload.description,
    )
    db.add(institution)
    db.commit()
    db.refresh(institution)
    return institution


@router.get("/admin/institutions", response_model=list[InstitutionPublic])
def list_institutions(
    _current_admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> list[Institution]:
    return db.query(Institution).order_by(Institution.name.asc()).all()


@router.post(
    "/admin/users",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
)
def provision_user(
    payload: AdminUserCreate,
    _current_admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> User:
    normalized_email = payload.email.lower().strip()
    existing_user = db.query(User).filter(User.email == normalized_email).first()
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A user with that email already exists.")

    institution_id = payload.institution_id
    if payload.role in {"institution", "learner"}:
        if payload.role == "institution" and institution_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Institution accounts must be assigned to an institution.",
            )
        if institution_id is not None and db.get(Institution, institution_id) is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Institution does not exist.",
            )
    elif institution_id is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Only learner or institution accounts may be assigned to an institution.",
        )

    user = User(
        full_name=payload.full_name.strip(),
        email=normalized_email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        institution_id=institution_id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
