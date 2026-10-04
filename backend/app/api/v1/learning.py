from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, select

from app.deps import require_roles
from app.db.session import get_db
from app.models import (
    CohortEnrollment,
    EmploymentOutcome,
    Institution,
    LearnerProfile,
    LearnerSkill,
    LearningPath,
    LearningPathItem,
    Opportunity,
    OpportunitySkill,
    Skill,
    TrainingCohort,
    User,
)
from app.schemas import (
    LearnerProfileResponse,
    LearnerProfileUpdate,
    LearnerSkillAssessmentUpdate,
    EmployerOpportunityResponse,
    LearningPathItemResponse,
    LearningPathItemStatusUpdate,
    LearningPathResponse,
    OpportunityCreate,
    ApplicationStatusUpdate,
    CohortEnrollmentCreate,
    CohortLearnerResponse,
    EmploymentOutcomeResponse,
    InstitutionAnalyticsResponse,
    InstitutionLearnerResponse,
    OpportunityStatusUpdate,
    TrainingCohortCreate,
    TrainingCohortResponse,
)
from app.services.skill_gap_service import (
    build_learning_recommendations,
    calculate_skill_gap,
    ensure_learner_profile,
    get_learning_resource,
    get_role_skill_requirements,
    match_opportunities,
)

router = APIRouter(prefix="/api/v1", tags=["learning"])


def _require_institution_id(current_user: User) -> UUID:
    if current_user.institution_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is not assigned to an institution.",
        )
    return current_user.institution_id


def _cohort_payload(db: Session, cohort: TrainingCohort) -> dict:
    active_enrollments = [enrollment for enrollment in cohort.enrollments if enrollment.status == "active"]
    learner_profile_ids = select(LearnerProfile.id).join(
        User, LearnerProfile.user_id == User.id
    ).where(User.id.in_([enrollment.learner_user_id for enrollment in active_enrollments]))
    assessed_learner_count = (
        db.query(func.count(func.distinct(LearnerSkill.learner_profile_id)))
        .filter(LearnerSkill.learner_profile_id.in_(learner_profile_ids))
        .scalar()
        or 0
    )
    application_count = (
        db.query(func.count(EmploymentOutcome.id))
        .filter(EmploymentOutcome.learner_profile_id.in_(learner_profile_ids))
        .scalar()
        or 0
    )
    placement_count = (
        db.query(func.count(func.distinct(EmploymentOutcome.learner_profile_id)))
        .filter(
            EmploymentOutcome.learner_profile_id.in_(learner_profile_ids),
            EmploymentOutcome.status == "hired",
        )
        .scalar()
        or 0
    )
    return {
        "id": cohort.id,
        "name": cohort.name,
        "program": cohort.program,
        "capacity": cohort.capacity,
        "status": cohort.status,
        "learner_count": len(active_enrollments),
        "assessed_learner_count": assessed_learner_count,
        "application_count": application_count,
        "placement_count": placement_count,
        "learners": [
            {
                "user_id": enrollment.learner.id,
                "full_name": enrollment.learner.full_name,
                "email": enrollment.learner.email,
                "status": enrollment.status,
            }
            for enrollment in active_enrollments
        ],
    }


@router.get("/institutions/me/cohorts", response_model=list[TrainingCohortResponse])
def list_institution_cohorts(
    current_user: User = Depends(require_roles("institution")), db: Session = Depends(get_db)
) -> list[dict]:
    institution_id = _require_institution_id(current_user)
    cohorts = (
        db.query(TrainingCohort)
        .filter(TrainingCohort.institution_id == institution_id)
        .order_by(TrainingCohort.created_at.desc())
        .all()
    )
    return [_cohort_payload(db, cohort) for cohort in cohorts]


@router.post(
    "/institutions/me/cohorts",
    response_model=TrainingCohortResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_institution_cohort(
    payload: TrainingCohortCreate,
    current_user: User = Depends(require_roles("institution")),
    db: Session = Depends(get_db),
) -> dict:
    institution_id = _require_institution_id(current_user)
    cohort = TrainingCohort(
        institution_id=institution_id,
        name=payload.name.strip(),
        program=payload.program.strip(),
        capacity=payload.capacity,
    )
    db.add(cohort)
    db.commit()
    db.refresh(cohort)
    return _cohort_payload(db, cohort)


@router.post(
    "/institutions/me/cohorts/{cohort_id}/learners",
    response_model=CohortLearnerResponse,
    status_code=status.HTTP_201_CREATED,
)
def enroll_institution_learner(
    cohort_id: UUID,
    payload: CohortEnrollmentCreate,
    current_user: User = Depends(require_roles("institution")),
    db: Session = Depends(get_db),
) -> dict:
    institution_id = _require_institution_id(current_user)
    cohort = (
        db.query(TrainingCohort)
        .filter(
            TrainingCohort.id == cohort_id,
            TrainingCohort.institution_id == institution_id,
        )
        .first()
    )
    if cohort is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cohort not found.")

    learner = (
        db.query(User)
        .filter(
            User.id == payload.learner_user_id,
            User.role == "learner",
            User.is_active.is_(True),
            User.institution_id == institution_id,
        )
        .first()
    )
    if learner is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institution learner not found.")

    if any(enrollment.learner_user_id == learner.id for enrollment in cohort.enrollments):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Learner is already enrolled in this cohort.")
    if len(cohort.enrollments) >= cohort.capacity:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cohort is at capacity.")

    enrollment = CohortEnrollment(cohort_id=cohort.id, learner_user_id=learner.id, status="active")
    db.add(enrollment)
    db.commit()
    return {
        "user_id": learner.id,
        "full_name": learner.full_name,
        "email": learner.email,
        "status": enrollment.status,
    }


@router.get("/institutions/me/learners", response_model=list[InstitutionLearnerResponse])
def list_institution_learners(
    current_user: User = Depends(require_roles("institution")), db: Session = Depends(get_db)
) -> list[User]:
    institution_id = _require_institution_id(current_user)
    return (
        db.query(User)
        .filter(
            User.institution_id == institution_id,
            User.role == "learner",
            User.is_active.is_(True),
        )
        .order_by(User.full_name.asc())
        .all()
    )


@router.get("/learners/me/profile", response_model=LearnerProfileResponse)
def get_learner_profile(
    current_user: User = Depends(require_roles("learner")), db: Session = Depends(get_db)
) -> dict:
    profile = ensure_learner_profile(db, current_user)
    calculate_skill_gap(db, current_user)
    db.expire(profile, ["skill_assessments"])
    role_requirements = get_role_skill_requirements(profile.target_role or current_user.role)
    return {
        "target_role": profile.target_role,
        "preferred_location": profile.preferred_location,
        "skills": [
            {
                "skill_name": assessment.skill.name,
                "self_rating": float(assessment.self_rating or 0.0),
                "target_rating": float(assessment.target_rating or 0.0),
                "gap_score": float(assessment.gap_score or 0.0),
            }
            for assessment in profile.skill_assessments
            if assessment.skill.name.strip().lower() in role_requirements
        ],
    }


@router.put("/learners/me/profile", response_model=LearnerProfileResponse)
def update_learner_profile(
    payload: LearnerProfileUpdate,
    current_user: User = Depends(require_roles("learner")),
    db: Session = Depends(get_db),
) -> dict:
    profile = ensure_learner_profile(db, current_user)
    profile.target_role = payload.target_role
    profile.preferred_location = payload.preferred_location.strip() if payload.preferred_location else None
    db.commit()
    db.refresh(profile)
    calculate_skill_gap(db, current_user)
    db.expire(profile, ["skill_assessments"])
    return get_learner_profile(current_user, db)


@router.put("/learners/me/skills", response_model=LearnerProfileResponse)
def update_learner_skill_ratings(
    payload: LearnerSkillAssessmentUpdate,
    current_user: User = Depends(require_roles("learner")),
    db: Session = Depends(get_db),
) -> dict:
    profile = ensure_learner_profile(db, current_user)
    role_requirements = get_role_skill_requirements(profile.target_role)
    normalized_ratings: dict[str, float] = {}
    for rating in payload.ratings:
        normalized_name = rating.skill_name.strip().lower()
        if normalized_name not in role_requirements:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{rating.skill_name} is not a skill for the selected target role.",
            )
        if normalized_name in normalized_ratings:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Duplicate rating provided for {rating.skill_name}.",
            )
        normalized_ratings[normalized_name] = rating.self_rating

    calculate_skill_gap(db, current_user)
    db.expire(profile, ["skill_assessments"])
    assessments = {
        assessment.skill.name.strip().lower(): assessment
        for assessment in profile.skill_assessments
    }
    for skill_name, self_rating in normalized_ratings.items():
        assessment = assessments[skill_name]
        assessment.self_rating = self_rating
        assessment.gap_score = max(0.0, float(assessment.target_rating or 0.0) - self_rating)
    db.commit()
    db.expire(profile, ["skill_assessments"])
    return get_learner_profile(current_user, db)


@router.get("/learners/me/skill-gap")
def get_skill_gap(current_user: User = Depends(require_roles("learner")), db: Session = Depends(get_db)) -> dict:
    profile = ensure_learner_profile(db, current_user)
    payload = calculate_skill_gap(db, current_user)
    payload["target_role"] = profile.target_role or current_user.role
    return payload


@router.get("/learners/me/recommendations")
def get_learning_recommendations(
    current_user: User = Depends(require_roles("learner")), db: Session = Depends(get_db)
) -> dict:
    return build_learning_recommendations(db, current_user)


@router.post(
    "/learners/me/learning-paths/generate",
    response_model=LearningPathResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_learning_path(
    current_user: User = Depends(require_roles("learner")), db: Session = Depends(get_db)
) -> LearningPath:
    profile = ensure_learner_profile(db, current_user)
    recommendations = build_learning_recommendations(db, current_user)["items"]
    db.query(LearningPath).filter(
        LearningPath.learner_profile_id == profile.id,
        LearningPath.status == "active",
    ).update({LearningPath.status: "superseded"}, synchronize_session=False)

    path = LearningPath(
        learner_profile_id=profile.id,
        title=f"{profile.target_role.title()} readiness roadmap",
        status="active",
        priority_score=round(
            sum(item["priority_score"] for item in recommendations) / len(recommendations), 2
        )
        if recommendations
        else 0.0,
    )
    db.add(path)
    db.flush()

    item_index = 0
    for recommendation in recommendations:
        skill_name = recommendation["skill_name"]
        actions = (
            ("Learn the foundations of", "course", max(1, round(recommendation["gap_score"]))),
            ("Build a practical project using", "project", max(2, round(recommendation["gap_score"] * 2))),
            ("Complete a skills check for", "assessment", 1),
        )
        for action, module_type, estimated_hours in actions:
            resource = get_learning_resource(skill_name, module_type)
            db.add(
                LearningPathItem(
                    learning_path_id=path.id,
                    title=f"{action} {skill_name}",
                    module_type=module_type,
                    estimated_hours=estimated_hours,
                    order_index=item_index,
                    resource_label=resource[0] if resource else None,
                    resource_url=resource[1] if resource else None,
                    status="not_started",
                )
            )
            item_index += 1

    db.commit()
    db.refresh(path)
    return path


@router.get("/learners/me/learning-paths/current", response_model=LearningPathResponse)
def get_current_learning_path(
    current_user: User = Depends(require_roles("learner")), db: Session = Depends(get_db)
) -> LearningPath:
    profile = ensure_learner_profile(db, current_user)
    path = (
        db.query(LearningPath)
        .filter(LearningPath.learner_profile_id == profile.id)
        .order_by(LearningPath.created_at.desc())
        .first()
    )
    if path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No learning path found.")
    return path


@router.patch(
    "/learners/me/learning-path-items/{item_id}",
    response_model=LearningPathItemResponse,
)
def update_learning_path_item_status(
    item_id: UUID,
    payload: LearningPathItemStatusUpdate,
    current_user: User = Depends(require_roles("learner")),
    db: Session = Depends(get_db),
) -> LearningPathItem:
    profile = ensure_learner_profile(db, current_user)
    item = (
        db.query(LearningPathItem)
        .join(LearningPath)
        .filter(
            LearningPathItem.id == item_id,
            LearningPath.learner_profile_id == profile.id,
        )
        .first()
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learning path item not found.")

    item.status = payload.status
    path = item.learning_path
    if path.items and all(path_item.status == "completed" for path_item in path.items):
        path.status = "completed"
    else:
        path.status = "active"
    db.commit()
    db.refresh(item)
    return item


@router.get("/learners/me/opportunity-matches")
def get_opportunity_matches(
    current_user: User = Depends(require_roles("learner")), db: Session = Depends(get_db)
) -> dict:
    return {"matches": match_opportunities(db, current_user)}


@router.post(
    "/learners/me/opportunities/{opportunity_id}/applications",
    response_model=EmploymentOutcomeResponse,
    status_code=status.HTTP_201_CREATED,
)
def apply_to_opportunity(
    opportunity_id: UUID,
    current_user: User = Depends(require_roles("learner")),
    db: Session = Depends(get_db),
) -> dict:
    opportunity = db.get(Opportunity, opportunity_id)
    if opportunity is None or opportunity.status != "active":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active opportunity not found.")

    profile = ensure_learner_profile(db, current_user)
    existing = (
        db.query(EmploymentOutcome)
        .filter(
            EmploymentOutcome.learner_profile_id == profile.id,
            EmploymentOutcome.opportunity_id == opportunity.id,
        )
        .first()
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You already applied to this opportunity.")

    application = EmploymentOutcome(
        learner_profile_id=profile.id,
        opportunity_id=opportunity.id,
        status="applied",
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return {
        "id": application.id,
        "opportunity_id": opportunity.id,
        "company_name": opportunity.company_name,
        "opportunity_title": opportunity.title,
        "learner_name": current_user.full_name,
        "learner_email": current_user.email,
        "status": application.status,
        "applied_at": application.created_at,
        "placement_date": application.placement_date,
    }


@router.get("/learners/me/applications", response_model=list[EmploymentOutcomeResponse])
def get_learner_applications(
    current_user: User = Depends(require_roles("learner")), db: Session = Depends(get_db)
) -> list[dict]:
    profile = ensure_learner_profile(db, current_user)
    applications = (
        db.query(EmploymentOutcome)
        .join(Opportunity, EmploymentOutcome.opportunity_id == Opportunity.id)
        .filter(EmploymentOutcome.learner_profile_id == profile.id)
        .order_by(EmploymentOutcome.created_at.desc())
        .all()
    )
    return [
        {
            "id": application.id,
            "opportunity_id": application.opportunity.id,
            "company_name": application.opportunity.company_name,
            "opportunity_title": application.opportunity.title,
            "learner_name": current_user.full_name,
            "learner_email": current_user.email,
            "status": application.status,
            "applied_at": application.created_at,
            "placement_date": application.placement_date,
        }
        for application in applications
    ]


@router.get("/institutions/me/analytics", response_model=InstitutionAnalyticsResponse)
def get_institution_analytics(
    current_user: User = Depends(require_roles("institution")), db: Session = Depends(get_db)
) -> dict[str, int | float | str]:
    if current_user.institution_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is not assigned to an institution.",
        )

    institution = db.get(Institution, current_user.institution_id)
    if institution is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Institution is unavailable.")

    learner_count = (
        db.query(func.count(User.id))
        .filter(User.institution_id == institution.id, User.role == "learner", User.is_active.is_(True))
        .scalar()
        or 0
    )
    learner_profile_ids = (
        select(LearnerProfile.id)
        .join(User, LearnerProfile.user_id == User.id)
        .filter(User.institution_id == institution.id, User.role == "learner", User.is_active.is_(True))
    )
    assessed_learner_count = (
        db.query(func.count(func.distinct(LearnerSkill.learner_profile_id)))
        .filter(LearnerSkill.learner_profile_id.in_(learner_profile_ids))
        .scalar()
        or 0
    )
    application_count = (
        db.query(func.count(EmploymentOutcome.id))
        .filter(EmploymentOutcome.learner_profile_id.in_(learner_profile_ids))
        .scalar()
        or 0
    )
    applicants_count = (
        db.query(func.count(func.distinct(EmploymentOutcome.learner_profile_id)))
        .filter(EmploymentOutcome.learner_profile_id.in_(learner_profile_ids))
        .scalar()
        or 0
    )
    placement_count = (
        db.query(func.count(func.distinct(EmploymentOutcome.learner_profile_id)))
        .filter(
            EmploymentOutcome.learner_profile_id.in_(learner_profile_ids),
            EmploymentOutcome.status == "hired",
        )
        .scalar()
        or 0
    )
    active_opportunity_count = (
        db.query(func.count(Opportunity.id))
        .filter(
            Opportunity.institution_id == institution.id,
            Opportunity.status == "active",
        )
        .scalar()
        or 0
    )
    application_rate = round(applicants_count * 100 / learner_count, 2) if learner_count else 0.0
    placement_rate = round(placement_count * 100 / learner_count, 2) if learner_count else 0.0

    return {
        "institution_name": institution.name,
        "learner_count": learner_count,
        "assessed_learner_count": assessed_learner_count,
        "application_count": application_count,
        "applicants_count": applicants_count,
        "placement_count": placement_count,
        "active_opportunity_count": active_opportunity_count,
        "application_rate_percent": application_rate,
        "placement_rate_percent": placement_rate,
    }


@router.get("/employers/me/opportunities", response_model=list[EmployerOpportunityResponse])
def get_employer_opportunities(
    current_user: User = Depends(require_roles("employer")), db: Session = Depends(get_db)
) -> list[Opportunity]:
    return (
        db.query(Opportunity)
        .filter(Opportunity.owner_user_id == current_user.id)
        .order_by(Opportunity.created_at.desc())
        .all()
    )


@router.patch(
    "/employers/me/opportunities/{opportunity_id}",
    response_model=EmployerOpportunityResponse,
)
def update_employer_opportunity_status(
    opportunity_id: UUID,
    payload: OpportunityStatusUpdate,
    current_user: User = Depends(require_roles("employer")),
    db: Session = Depends(get_db),
) -> Opportunity:
    opportunity = (
        db.query(Opportunity)
        .filter(
            Opportunity.id == opportunity_id,
            Opportunity.owner_user_id == current_user.id,
        )
        .first()
    )
    if opportunity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found.")

    opportunity.status = payload.status
    db.commit()
    db.refresh(opportunity)
    return opportunity


@router.get(
    "/employers/me/opportunities/{opportunity_id}/applications",
    response_model=list[EmploymentOutcomeResponse],
)
def get_opportunity_applications(
    opportunity_id: UUID,
    current_user: User = Depends(require_roles("employer")),
    db: Session = Depends(get_db),
) -> list[dict]:
    opportunity = (
        db.query(Opportunity)
        .filter(Opportunity.id == opportunity_id, Opportunity.owner_user_id == current_user.id)
        .first()
    )
    if opportunity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found.")

    applications = (
        db.query(EmploymentOutcome)
        .join(LearnerProfile)
        .join(User)
        .filter(EmploymentOutcome.opportunity_id == opportunity.id)
        .order_by(EmploymentOutcome.created_at.desc())
        .all()
    )
    return [
        {
            "id": application.id,
            "opportunity_id": opportunity.id,
            "company_name": opportunity.company_name,
            "opportunity_title": opportunity.title,
            "learner_name": application.learner_profile.user.full_name,
            "learner_email": application.learner_profile.user.email,
            "status": application.status,
            "applied_at": application.created_at,
            "placement_date": application.placement_date,
        }
        for application in applications
    ]


@router.patch(
    "/employers/me/applications/{application_id}",
    response_model=EmploymentOutcomeResponse,
)
def update_application_status(
    application_id: UUID,
    payload: ApplicationStatusUpdate,
    current_user: User = Depends(require_roles("employer")),
    db: Session = Depends(get_db),
) -> dict:
    application = (
        db.query(EmploymentOutcome)
        .join(Opportunity, EmploymentOutcome.opportunity_id == Opportunity.id)
        .join(LearnerProfile)
        .join(User)
        .filter(
            EmploymentOutcome.id == application_id,
            Opportunity.owner_user_id == current_user.id,
        )
        .first()
    )
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")

    if application.status in {"hired", "rejected"} and payload.status != application.status:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Hired and rejected applications are terminal outcomes.",
        )

    application.status = payload.status
    if payload.status == "hired":
        application.placement_date = application.placement_date or datetime.now(timezone.utc)
    else:
        application.placement_date = None
    db.commit()
    db.refresh(application)
    opportunity = application.opportunity
    learner = application.learner_profile.user
    return {
        "id": application.id,
        "opportunity_id": opportunity.id,
        "company_name": opportunity.company_name,
        "opportunity_title": opportunity.title,
        "learner_name": learner.full_name,
        "learner_email": learner.email,
        "status": application.status,
        "applied_at": application.created_at,
        "placement_date": application.placement_date,
    }


@router.post("/opportunities", status_code=status.HTTP_201_CREATED)
def create_opportunity(
    payload: OpportunityCreate,
    current_user: User = Depends(require_roles("employer")),
    db: Session = Depends(get_db),
) -> dict:
    opportunity = Opportunity(
        owner_user_id=current_user.id,
        company_name=payload.company_name,
        title=payload.title,
        location=payload.location,
        employment_type=payload.employment_type,
        salary_band=payload.salary_band,
        description=payload.description,
        status="active",
    )
    db.add(opportunity)
    db.commit()
    db.refresh(opportunity)

    for requirement in payload.required_skills:
        skill_name = requirement.skill_name
        skill = db.query(Skill).filter(Skill.name.ilike(skill_name)).first()
        if skill is None:
            skill = Skill(
                name=skill_name.strip().title(),
                category="core",
                description=f"Requirement for {payload.title}",
                demand_score=0.0,
            )
            db.add(skill)
            db.commit()
            db.refresh(skill)

        requirement_row = OpportunitySkill(
            opportunity_id=opportunity.id,
            skill_id=skill.id,
            required_level=requirement.required_level,
            weight=requirement.weight,
        )
        db.add(requirement_row)

    db.commit()
    db.refresh(opportunity)
    return {
        "id": str(opportunity.id),
        "company_name": opportunity.company_name,
        "title": opportunity.title,
        "location": opportunity.location,
        "employment_type": opportunity.employment_type,
        "required_skills": [
            {
                "skill_name": item.skill.name,
                "required_level": item.required_level,
                "weight": item.weight,
            }
            for item in opportunity.required_skills
        ],
    }
