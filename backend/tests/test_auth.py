from fastapi.testclient import TestClient

from app.main import app
from app.db.session import get_db
from app.services.admin_service import create_initial_admin

client = TestClient(app)


def create_user(email: str, password: str = "Pass1234!") -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test User",
            "email": email,
            "password": password,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_register_and_login_success():
    email = "learner@example.com"
    create_user(email)

    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Pass1234!"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_invalid_credentials():
    create_user("invalid@example.com")

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "invalid@example.com", "password": "WrongPassword!"},
    )

    assert response.status_code == 401


def test_duplicate_registration_rejected():
    email = "duplicate@example.com"
    create_user(email)

    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Another User",
            "email": email,
            "password": "Pass9876!",
        },
    )

    assert response.status_code == 409


def test_registration_rejects_client_selected_role():
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Self Promoted User",
            "email": "self-promoted@example.com",
            "password": "Pass1234!",
            "role": "admin",
        },
    )

    assert response.status_code == 422


def test_password_over_bcrypt_byte_limit_is_rejected():
    long_password = "p" * 73
    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Long Password User",
            "email": "long-password@example.com",
            "password": long_password,
        },
    )
    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": "long-password@example.com", "password": long_password},
    )

    assert register_response.status_code == 422
    assert login_response.status_code == 422


def test_unauthenticated_access_denied():
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_admin_role_restriction(set_user_role):
    admin = create_user("admin@example.com")
    set_user_role(admin["id"], "admin")
    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "Pass1234!"},
    )
    admin_token = admin_login.json()["access_token"]

    response = client.get(
        "/api/v1/admin/check",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200

    learner = create_user("learner2@example.com")
    learner_login = client.post(
        "/api/v1/auth/login",
        json={"email": "learner2@example.com", "password": "Pass1234!"},
    )
    learner_token = learner_login.json()["access_token"]

    denied_response = client.get(
        "/api/v1/admin/check",
        headers={"Authorization": f"Bearer {learner_token}"},
    )
    assert denied_response.status_code == 403


def test_user_can_access_own_profile_but_not_another_users_profile():
    create_user("self@example.com")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "self@example.com", "password": "Pass1234!"},
    )
    token = login.json()["access_token"]

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

    other = create_user("other@example.com")
    profile_response = client.get(
        f"/api/v1/users/{other['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert profile_response.status_code == 403


def test_admin_can_provision_employer_and_institution_accounts(set_user_role):
    admin = create_user("provisioning-admin@example.com")
    set_user_role(admin["id"], "admin")
    admin_token = client.post(
        "/api/v1/auth/login",
        json={"email": "provisioning-admin@example.com", "password": "Pass1234!"},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}

    institution_response = client.post(
        "/api/v1/admin/institutions",
        headers=headers,
        json={"name": "Provisioned Institute", "sector": "Education", "location": "Chennai"},
    )
    assert institution_response.status_code == 201, institution_response.text
    institution_id = institution_response.json()["id"]
    duplicate_institution = client.post(
        "/api/v1/admin/institutions",
        headers=headers,
        json={"name": "provisioned institute", "sector": "Education"},
    )
    assert duplicate_institution.status_code == 409

    institution_user = client.post(
        "/api/v1/admin/users",
        headers=headers,
        json={
            "full_name": "Institute Manager",
            "email": "provisioned-manager@example.com",
            "password": "Pass1234!",
            "role": "institution",
            "institution_id": institution_id,
        },
    )
    assert institution_user.status_code == 201, institution_user.text
    assert institution_user.json()["role"] == "institution"

    learner_user = client.post(
        "/api/v1/admin/users",
        headers=headers,
        json={
            "full_name": "Enrolled Learner",
            "email": "provisioned-learner@example.com",
            "password": "Pass1234!",
            "role": "learner",
            "institution_id": institution_id,
        },
    )
    assert learner_user.status_code == 201, learner_user.text
    assert learner_user.json()["role"] == "learner"

    employer_user = client.post(
        "/api/v1/admin/users",
        headers=headers,
        json={
            "full_name": "Employer Manager",
            "email": "provisioned-employer@example.com",
            "password": "Pass1234!",
            "role": "employer",
        },
    )
    assert employer_user.status_code == 201, employer_user.text
    assert employer_user.json()["role"] == "employer"

    employer_login = client.post(
        "/api/v1/auth/login",
        json={"email": "provisioned-employer@example.com", "password": "Pass1234!"},
    )
    assert employer_login.status_code == 200


def test_learner_cannot_provision_accounts_or_institutions():
    create_user("provisioning-learner@example.com")
    token = client.post(
        "/api/v1/auth/login",
        json={"email": "provisioning-learner@example.com", "password": "Pass1234!"},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    user_response = client.post(
        "/api/v1/admin/users",
        headers=headers,
        json={
            "full_name": "Unauthorized Employer",
            "email": "unauthorized-employer@example.com",
            "password": "Pass1234!",
            "role": "employer",
        },
    )
    institution_response = client.post(
        "/api/v1/admin/institutions",
        headers=headers,
        json={"name": "Unauthorized Institute", "sector": "Education"},
    )

    assert user_response.status_code == 403
    assert institution_response.status_code == 403


def test_only_learner_and_institution_accounts_can_be_enrolled(set_user_role):
    admin = create_user("enrollment-admin@example.com")
    set_user_role(admin["id"], "admin")
    admin_token = client.post(
        "/api/v1/auth/login",
        json={"email": "enrollment-admin@example.com", "password": "Pass1234!"},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}
    institution = client.post(
        "/api/v1/admin/institutions",
        headers=headers,
        json={"name": "Enrollment Institute", "sector": "Education"},
    ).json()

    employer_assignment = client.post(
        "/api/v1/admin/users",
        headers=headers,
        json={
            "full_name": "Employer",
            "email": "enrolled-employer@example.com",
            "password": "Pass1234!",
            "role": "employer",
            "institution_id": institution["id"],
        },
    )

    assert employer_assignment.status_code == 422


def test_initial_admin_bootstrap_hashes_password_and_runs_once(isolated_db):
    admin = create_initial_admin(
        isolated_db,
        "First Admin",
        " FIRST-ADMIN@example.com ",
        "StrongPass123!",
    )
    assert admin.email == "first-admin@example.com"
    assert admin.role == "admin"
    assert admin.password_hash != "StrongPass123!"

    try:
        create_initial_admin(isolated_db, "Second Admin", "second-admin@example.com", "StrongPass123!")
    except RuntimeError as exc:
        assert "already exists" in str(exc)
    else:
        raise AssertionError("Bootstrap must refuse when an admin already exists.")
