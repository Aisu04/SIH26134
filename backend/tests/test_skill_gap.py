from fastapi.testclient import TestClient

from app.main import app
from app.services.skill_gap_service import get_learning_resource

client = TestClient(app)


def create_user(email: str, password: str = "Pass1234!") -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student User",
            "email": email,
            "password": password,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def login_user(email: str, password: str = "Pass1234!") -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def test_skill_gap_and_recommendations_for_learner():
    create_user("skillgap@example.com")
    token = login_user("skillgap@example.com")

    response = client.get(
        "/api/v1/learners/me/skill-gap",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["target_role"]
    assert body["gaps"]
    assert any(item["skill_name"].lower() == "python" for item in body["gaps"])

    recommendations = client.get(
        "/api/v1/learners/me/recommendations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert recommendations.status_code == 200, recommendations.text
    recs = recommendations.json()
    assert recs["items"]
    assert recs["items"][0]["priority_score"] >= 0


def test_opportunity_match_ranking_for_learner(set_user_role, set_opportunity_status):
    employer = create_user("employer@example.com")
    set_user_role(employer["id"], "employer")
    employer_token = login_user("employer@example.com")

    create_response = client.post(
        "/api/v1/opportunities",
        headers={"Authorization": f"Bearer {employer_token}"},
        json={
            "company_name": "SkillBridge Labs",
            "title": "Junior Data Analyst",
            "location": "Bengaluru",
            "employment_type": "full-time",
            "description": "Analyse trends using SQL and Python.",
            "required_skills": [
                {"skill_name": "python", "required_level": 4.0, "weight": 0.6},
                {"skill_name": "sql", "required_level": 4.0, "weight": 0.4},
            ],
        },
    )
    assert create_response.status_code == 201, create_response.text
    inactive_response = client.post(
        "/api/v1/opportunities",
        headers={"Authorization": f"Bearer {employer_token}"},
        json={
            "company_name": "Closed Company",
            "title": "Closed Analyst Role",
            "required_skills": [{"skill_name": "python", "required_level": 3.0}],
        },
    )
    assert inactive_response.status_code == 201, inactive_response.text
    set_opportunity_status(inactive_response.json()["id"], "closed")

    create_user("opportunity@example.com")
    learner_token = login_user("opportunity@example.com")
    matches = client.get(
        "/api/v1/learners/me/opportunity-matches",
        headers={"Authorization": f"Bearer {learner_token}"},
    )
    assert matches.status_code == 200, matches.text
    payload = matches.json()
    assert payload["matches"]
    assert payload["matches"][0]["company_name"] == "SkillBridge Labs"
    assert all(item["company_name"] != "Closed Company" for item in payload["matches"])


def test_learner_cannot_create_opportunity():
    create_user("learner-opportunity-create@example.com")
    token = login_user("learner-opportunity-create@example.com")

    response = client.post(
        "/api/v1/opportunities",
        headers={"Authorization": f"Bearer {token}"},
        json={"company_name": "Unauthorized Co", "title": "Unauthorized Role"},
    )

    assert response.status_code == 403


def test_employer_cannot_access_learner_skill_gap(set_user_role):
    employer = create_user("employer-skill-gap@example.com")
    set_user_role(employer["id"], "employer")
    token = login_user("employer-skill-gap@example.com")

    response = client.get(
        "/api/v1/learners/me/skill-gap",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_learner_profile_and_skill_assessment_update_gap_results():
    create_user("assessment-update@example.com")
    token = login_user("assessment-update@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    initial_profile = client.get("/api/v1/learners/me/profile", headers=headers)
    assert initial_profile.status_code == 200, initial_profile.text
    initial_assessment = client.put(
        "/api/v1/learners/me/skills",
        headers=headers,
        json={
            "ratings": [
                {"skill_name": "excel", "self_rating": 4.0},
                {"skill_name": "python", "self_rating": 3.0},
                {"skill_name": "sql", "self_rating": 3.0},
                {"skill_name": "statistics", "self_rating": 2.0},
            ]
        },
    )
    assert initial_assessment.status_code == 200, initial_assessment.text

    profile_response = client.put(
        "/api/v1/learners/me/profile",
        headers=headers,
        json={"target_role": "software engineer", "preferred_location": "Pune"},
    )
    assert profile_response.status_code == 200, profile_response.text
    assert profile_response.json()["target_role"] == "software engineer"
    current_skills = {item["skill_name"].lower() for item in profile_response.json()["skills"]}
    assert current_skills == {"python", "algorithms", "sql", "communication"}

    assessment_response = client.put(
        "/api/v1/learners/me/skills",
        headers=headers,
        json={
            "ratings": [
                {"skill_name": "python", "self_rating": 4.5},
                {"skill_name": "algorithms", "self_rating": 2.0},
                {"skill_name": "sql", "self_rating": 3.5},
                {"skill_name": "communication", "self_rating": 2.5},
            ]
        },
    )
    assert assessment_response.status_code == 200, assessment_response.text
    assessment = assessment_response.json()
    assert assessment["preferred_location"] == "Pune"
    saved_ratings = {item["skill_name"].lower(): item for item in assessment["skills"]}
    assert saved_ratings["python"]["self_rating"] == 4.5
    assert saved_ratings["algorithms"]["self_rating"] == 2.0

    gaps_response = client.get("/api/v1/learners/me/skill-gap", headers=headers)
    assert gaps_response.status_code == 200, gaps_response.text
    gaps = {item["skill_name"].lower(): item for item in gaps_response.json()["gaps"]}
    assert gaps_response.json()["target_role"] == "software engineer"
    assert "python" not in gaps
    assert gaps["algorithms"]["current_rating"] == 2.0
    assert gaps["algorithms"]["gap_score"] == 1.5


def test_skill_assessment_rejects_ratings_outside_scale():
    create_user("invalid-assessment@example.com")
    token = login_user("invalid-assessment@example.com")

    response = client.put(
        "/api/v1/learners/me/skills",
        headers={"Authorization": f"Bearer {token}"},
        json={"ratings": [{"skill_name": "python", "self_rating": 5.1}]},
    )

    assert response.status_code == 422


def test_generate_and_track_learning_path_progress():
    create_user("roadmap@example.com")
    token = login_user("roadmap@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post("/api/v1/learners/me/learning-paths/generate", headers=headers)
    assert response.status_code == 201, response.text
    path = response.json()
    assert path["status"] == "active"
    assert len(path["items"]) >= 3
    assert [item["order_index"] for item in path["items"]] == list(range(len(path["items"])))
    assert all(item["resource_url"].startswith("https://") for item in path["items"])
    assert all(item["resource_label"] for item in path["items"])

    retrieved = client.get("/api/v1/learners/me/learning-paths/current", headers=headers)
    assert retrieved.status_code == 200, retrieved.text
    assert retrieved.json()["id"] == path["id"]

    regenerated = client.post("/api/v1/learners/me/learning-paths/generate", headers=headers)
    assert regenerated.status_code == 201, regenerated.text
    assert regenerated.json()["id"] != path["id"]
    assert regenerated.json()["status"] == "active"
    assert retrieved.json()["status"] == "active"
    current = client.get("/api/v1/learners/me/learning-paths/current", headers=headers)
    assert current.json()["id"] == regenerated.json()["id"]

    item_id = regenerated.json()["items"][0]["id"]
    progress = client.patch(
        f"/api/v1/learners/me/learning-path-items/{item_id}",
        headers=headers,
        json={"status": "completed"},
    )
    assert progress.status_code == 200, progress.text
    assert progress.json()["status"] == "completed"

    updated_path = client.get("/api/v1/learners/me/learning-paths/current", headers=headers)
    assert updated_path.json()["items"][0]["status"] == "completed"


def test_learning_resource_catalog_uses_curated_links_only():
    python_course = get_learning_resource("Python", "course")
    assert python_course is not None
    assert python_course[1] == "https://docs.python.org/3/tutorial/"
    assert get_learning_resource("unknown skill", "course") is None


def test_learner_cannot_update_another_learners_path_item():
    create_user("roadmap-owner@example.com")
    owner_token = login_user("roadmap-owner@example.com")
    created = client.post(
        "/api/v1/learners/me/learning-paths/generate",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert created.status_code == 201, created.text

    create_user("roadmap-intruder@example.com")
    intruder_token = login_user("roadmap-intruder@example.com")
    item_id = created.json()["items"][0]["id"]
    response = client.patch(
        f"/api/v1/learners/me/learning-path-items/{item_id}",
        headers={"Authorization": f"Bearer {intruder_token}"},
        json={"status": "completed"},
    )

    assert response.status_code == 404


def test_employer_can_manage_only_its_own_opportunities(set_user_role):
    first_employer = create_user("first-employer@example.com")
    second_employer = create_user("second-employer@example.com")
    set_user_role(first_employer["id"], "employer")
    set_user_role(second_employer["id"], "employer")
    first_token = login_user("first-employer@example.com")
    second_token = login_user("second-employer@example.com")

    created = client.post(
        "/api/v1/opportunities",
        headers={"Authorization": f"Bearer {first_token}"},
        json={"company_name": "First Co", "title": "Analyst"},
    )
    assert created.status_code == 201, created.text
    opportunity_id = created.json()["id"]

    first_list = client.get(
        "/api/v1/employers/me/opportunities",
        headers={"Authorization": f"Bearer {first_token}"},
    )
    second_list = client.get(
        "/api/v1/employers/me/opportunities",
        headers={"Authorization": f"Bearer {second_token}"},
    )
    assert first_list.status_code == 200, first_list.text
    assert [item["id"] for item in first_list.json()] == [opportunity_id]
    assert second_list.status_code == 200, second_list.text
    assert second_list.json() == []

    denied_update = client.patch(
        f"/api/v1/employers/me/opportunities/{opportunity_id}",
        headers={"Authorization": f"Bearer {second_token}"},
        json={"status": "closed"},
    )
    assert denied_update.status_code == 404

    own_update = client.patch(
        f"/api/v1/employers/me/opportunities/{opportunity_id}",
        headers={"Authorization": f"Bearer {first_token}"},
        json={"status": "closed"},
    )
    assert own_update.status_code == 200, own_update.text
    assert own_update.json()["status"] == "closed"


def test_application_pipeline_and_employer_outcome_updates(set_user_role):
    employer = create_user("outcome-employer@example.com")
    set_user_role(employer["id"], "employer")
    employer_token = login_user("outcome-employer@example.com")
    opportunity = client.post(
        "/api/v1/opportunities",
        headers={"Authorization": f"Bearer {employer_token}"},
        json={"company_name": "Hiring Co", "title": "Junior Analyst"},
    )
    assert opportunity.status_code == 201, opportunity.text

    create_user("applicant@example.com")
    learner_token = login_user("applicant@example.com")
    learner_headers = {"Authorization": f"Bearer {learner_token}"}
    application = client.post(
        f"/api/v1/learners/me/opportunities/{opportunity.json()['id']}/applications",
        headers=learner_headers,
    )
    assert application.status_code == 201, application.text
    assert application.json()["status"] == "applied"

    duplicate = client.post(
        f"/api/v1/learners/me/opportunities/{opportunity.json()['id']}/applications",
        headers=learner_headers,
    )
    assert duplicate.status_code == 409

    employer_applicants = client.get(
        f"/api/v1/employers/me/opportunities/{opportunity.json()['id']}/applications",
        headers={"Authorization": f"Bearer {employer_token}"},
    )
    assert employer_applicants.status_code == 200, employer_applicants.text
    assert len(employer_applicants.json()) == 1
    application_id = employer_applicants.json()[0]["id"]

    status_update = client.patch(
        f"/api/v1/employers/me/applications/{application_id}",
        headers={"Authorization": f"Bearer {employer_token}"},
        json={"status": "interview"},
    )
    assert status_update.status_code == 200, status_update.text
    assert status_update.json()["status"] == "interview"

    hired_update = client.patch(
        f"/api/v1/employers/me/applications/{application_id}",
        headers={"Authorization": f"Bearer {employer_token}"},
        json={"status": "hired"},
    )
    assert hired_update.status_code == 200, hired_update.text
    assert hired_update.json()["placement_date"]

    reopen_application = client.patch(
        f"/api/v1/employers/me/applications/{application_id}",
        headers={"Authorization": f"Bearer {employer_token}"},
        json={"status": "interview"},
    )
    assert reopen_application.status_code == 409

    learner_applications = client.get("/api/v1/learners/me/applications", headers=learner_headers)
    assert learner_applications.status_code == 200, learner_applications.text
    assert learner_applications.json()[0]["status"] == "hired"


def test_employer_cannot_view_applications_for_another_employers_opportunity(set_user_role):
    owner = create_user("outcome-owner@example.com")
    intruder = create_user("outcome-intruder@example.com")
    set_user_role(owner["id"], "employer")
    set_user_role(intruder["id"], "employer")
    owner_token = login_user("outcome-owner@example.com")
    intruder_token = login_user("outcome-intruder@example.com")
    opportunity = client.post(
        "/api/v1/opportunities",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"company_name": "Owner Co", "title": "Role"},
    )

    response = client.get(
        f"/api/v1/employers/me/opportunities/{opportunity.json()['id']}/applications",
        headers={"Authorization": f"Bearer {intruder_token}"},
    )

    assert response.status_code == 404


def test_institution_analytics_are_scoped_and_data_backed(
    set_user_role,
    create_institution,
    assign_user_institution,
):
    institution_admin = create_user("institution-analytics-admin@example.com")
    set_user_role(institution_admin["id"], "admin")
    institution_admin_token = login_user("institution-analytics-admin@example.com")
    institution_admin_headers = {"Authorization": f"Bearer {institution_admin_token}"}
    institution = client.post(
        "/api/v1/admin/institutions",
        headers=institution_admin_headers,
        json={"name": "North Institute", "sector": "Education"},
    )
    assert institution.status_code == 201, institution.text
    institution_id = institution.json()["id"]
    institution_user = client.post(
        "/api/v1/admin/users",
        headers=institution_admin_headers,
        json={
            "full_name": "Institution Manager",
            "email": "institution-analytics@example.com",
            "password": "Pass1234!",
            "role": "institution",
            "institution_id": institution_id,
        },
    ).json()
    institution_token = login_user("institution-analytics@example.com")

    employer = create_user("analytics-employer@example.com")
    set_user_role(employer["id"], "employer")
    employer_token = login_user("analytics-employer@example.com")
    opportunity = client.post(
        "/api/v1/opportunities",
        headers={"Authorization": f"Bearer {employer_token}"},
        json={"company_name": "Analytics Co", "title": "Data Associate"},
    )
    assert opportunity.status_code == 201, opportunity.text

    learner = client.post(
        "/api/v1/admin/users",
        headers=institution_admin_headers,
        json={
            "full_name": "Institution Learner",
            "email": "institution-learner@example.com",
            "password": "Pass1234!",
            "role": "learner",
            "institution_id": institution_id,
        },
    )
    assert learner.status_code == 201, learner.text
    learner_token = login_user("institution-learner@example.com")
    application = client.post(
        f"/api/v1/learners/me/opportunities/{opportunity.json()['id']}/applications",
        headers={"Authorization": f"Bearer {learner_token}"},
    )
    assert application.status_code == 201, application.text

    other_institution = client.post(
        "/api/v1/admin/institutions",
        headers=institution_admin_headers,
        json={"name": "South Institute", "sector": "Education"},
    )
    assert other_institution.status_code == 201, other_institution.text
    other_learner = client.post(
        "/api/v1/admin/users",
        headers=institution_admin_headers,
        json={
            "full_name": "Other Institute Learner",
            "email": "other-institution-learner@example.com",
            "password": "Pass1234!",
            "role": "learner",
            "institution_id": other_institution.json()["id"],
        },
    )
    assert other_learner.status_code == 201, other_learner.text

    intruder = create_user("unaffiliated-institution@example.com")
    set_user_role(intruder["id"], "institution")
    intruder_token = login_user("unaffiliated-institution@example.com")
    denied = client.get(
        "/api/v1/institutions/me/analytics",
        headers={"Authorization": f"Bearer {intruder_token}"},
    )
    assert denied.status_code == 403

    response = client.get(
        "/api/v1/institutions/me/analytics",
        headers={"Authorization": f"Bearer {institution_token}"},
    )
    assert response.status_code == 200, response.text
    analytics = response.json()
    assert analytics["institution_name"] == "North Institute"
    assert analytics["learner_count"] == 1
    assert analytics["application_count"] == 1
    assert analytics["placement_count"] == 0
    assert analytics["active_opportunity_count"] == 0
    assert analytics["application_rate_percent"] == 100.0

    hired = client.patch(
        f"/api/v1/employers/me/applications/{application.json()['id']}",
        headers={"Authorization": f"Bearer {employer_token}"},
        json={"status": "hired"},
    )
    assert hired.status_code == 200, hired.text
    updated = client.get(
        "/api/v1/institutions/me/analytics",
        headers={"Authorization": f"Bearer {institution_token}"},
    )
    assert updated.json()["placement_count"] == 1
    assert updated.json()["placement_rate_percent"] == 100.0


def test_institution_cohorts_are_scoped_and_enroll_owned_learners(set_user_role):
    institution_admin = create_user("cohort-manager@example.com")
    set_user_role(institution_admin["id"], "admin")
    admin_token = login_user("cohort-manager@example.com")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    institution = client.post(
        "/api/v1/admin/institutions",
        headers=admin_headers,
        json={"name": "Cohort Institute", "sector": "Education"},
    ).json()
    manager = client.post(
        "/api/v1/admin/users",
        headers=admin_headers,
        json={
            "full_name": "Cohort Manager",
            "email": "cohort-institution-user@example.com",
            "password": "Pass1234!",
            "role": "institution",
            "institution_id": institution["id"],
        },
    ).json()
    institution_token = login_user(manager["email"])
    institution_headers = {"Authorization": f"Bearer {institution_token}"}

    learner = client.post(
        "/api/v1/admin/users",
        headers=admin_headers,
        json={
            "full_name": "Cohort Learner",
            "email": "cohort-learner@example.com",
            "password": "Pass1234!",
            "role": "learner",
            "institution_id": institution["id"],
        },
    ).json()
    other_learner = create_user("outside-cohort@example.com")

    created = client.post(
        "/api/v1/institutions/me/cohorts",
        headers=institution_headers,
        json={"name": "Data Foundations 2026", "program": "Data Analytics", "capacity": 25},
    )
    assert created.status_code == 201, created.text
    cohort_id = created.json()["id"]

    enrolled = client.post(
        f"/api/v1/institutions/me/cohorts/{cohort_id}/learners",
        headers=institution_headers,
        json={"learner_user_id": learner["id"]},
    )
    assert enrolled.status_code == 201, enrolled.text
    assert enrolled.json()["email"] == learner["email"]

    learner_token = login_user(learner["email"])
    learner_headers = {"Authorization": f"Bearer {learner_token}"}
    profile = client.get("/api/v1/learners/me/profile", headers=learner_headers)
    assert profile.status_code == 200, profile.text
    assessment = client.put(
        "/api/v1/learners/me/skills",
        headers=learner_headers,
        json={"ratings": [{"skill_name": skill["skill_name"], "self_rating": 2.0} for skill in profile.json()["skills"]]},
    )
    assert assessment.status_code == 200, assessment.text

    employer = create_user("cohort-employer@example.com")
    set_user_role(employer["id"], "employer")
    employer_token = login_user(employer["email"])
    opportunity = client.post(
        "/api/v1/opportunities",
        headers={"Authorization": f"Bearer {employer_token}"},
        json={"company_name": "Cohort Employer", "title": "Analyst"},
    )
    assert opportunity.status_code == 201, opportunity.text
    application = client.post(
        f"/api/v1/learners/me/opportunities/{opportunity.json()['id']}/applications",
        headers=learner_headers,
    )
    assert application.status_code == 201, application.text
    hired = client.patch(
        f"/api/v1/employers/me/applications/{application.json()['id']}",
        headers={"Authorization": f"Bearer {employer_token}"},
        json={"status": "hired"},
    )
    assert hired.status_code == 200, hired.text

    outside_enrollment = client.post(
        f"/api/v1/institutions/me/cohorts/{cohort_id}/learners",
        headers=institution_headers,
        json={"learner_user_id": other_learner["id"]},
    )
    assert outside_enrollment.status_code == 404

    duplicate_enrollment = client.post(
        f"/api/v1/institutions/me/cohorts/{cohort_id}/learners",
        headers=institution_headers,
        json={"learner_user_id": learner["id"]},
    )
    assert duplicate_enrollment.status_code == 409

    cohort_list = client.get("/api/v1/institutions/me/cohorts", headers=institution_headers)
    assert cohort_list.status_code == 200, cohort_list.text
    assert cohort_list.json()[0]["learner_count"] == 1
    cohort_metrics = cohort_list.json()[0]
    assert cohort_metrics["assessed_learner_count"] == 1
    assert cohort_metrics["application_count"] == 1
    assert cohort_metrics["placement_count"] == 1
    learner_roster = client.get("/api/v1/institutions/me/learners", headers=institution_headers)
    assert learner_roster.status_code == 200, learner_roster.text
    assert [item["id"] for item in learner_roster.json()] == [learner["id"]]

    other_manager = create_user("other-cohort-manager@example.com")
    set_user_role(other_manager["id"], "institution")
    other_token = login_user("other-cohort-manager@example.com")
    denied = client.get(
        "/api/v1/institutions/me/cohorts",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert denied.status_code == 403
