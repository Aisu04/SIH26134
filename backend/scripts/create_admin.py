from __future__ import annotations

import getpass

from app.db.session import SessionLocal
from app.services.admin_service import create_initial_admin


def main() -> None:
    full_name = input("Admin full name: ").strip()
    email = input("Admin email: ").strip()
    password = getpass.getpass("Admin password (8-72 UTF-8 bytes): ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match.")

    with SessionLocal() as db:
        try:
            admin = create_initial_admin(db, full_name, email, password)
        except (ValueError, RuntimeError) as exc:
            raise SystemExit(str(exc)) from exc
    print(f"Admin account created for {admin.email}.")


if __name__ == "__main__":
    main()
