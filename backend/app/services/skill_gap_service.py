from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import LearnerProfile, LearnerSkill, Opportunity, OpportunitySkill, Skill, User

ROLE_SKILL_MAP: dict[str, dict[str, float]] = {
    "learner": {"python": 4.0, "sql": 4.0, "communication": 3.0, "excel": 3.0},
    "data analyst": {"python": 4.0, "sql": 4.0, "excel": 3.5, "statistics": 3.0},
    "software engineer": {"python": 4.5, "algorithms": 3.5, "sql": 3.5, "communication": 2.5},
    "product manager": {"communication": 4.5, "analytics": 4.0, "sql": 3.0, "research": 3.0},
}

SKILL_RESOURCES: dict[str, dict[str, tuple[str, str]]] = {
    "python": {
        "course": ("Python Tutorial", "https://docs.python.org/3/tutorial/"),
        "project": ("Practice Python projects", "https://github.com/practical-tutorials/project-based-learning#python"),
        "assessment": ("Python exercises", "https://exercism.org/tracks/python"),
    },
    "sql": {
        "course": ("PostgreSQL Tutorial", "https://www.postgresql.org/docs/current/tutorial.html"),
        "project": ("SQLBolt interactive lessons", "https://sqlbolt.com/"),
        "assessment": ("SQL practice", "https://www.hackerrank.com/domains/sql"),
    },
    "excel": {
        "course": ("Excel video training", "https://support.microsoft.com/en-us/excel"),
        "project": ("Excel data analysis guide", "https://support.microsoft.com/en-us/office/analyze-data-in-excel-3223aab8-f543-4fda-85ed-76bb0295ffc4"),
        "assessment": ("Excel skills assessment", "https://learn.microsoft.com/en-us/credentials/certifications/mos-excel-associate-m365-apps/"),
    },
    "statistics": {
        "course": ("OpenIntro Statistics", "https://www.openintro.org/book/os/"),
        "project": ("Kaggle data visualization course", "https://www.kaggle.com/learn/data-visualization"),
        "assessment": ("Khan Academy statistics", "https://www.khanacademy.org/math/statistics-probability"),
    },
    "algorithms": {
        "course": ("Princeton Algorithms", "https://www.coursera.org/learn/algorithms-part1"),
        "project": ("The Algorithms project", "https://github.com/TheAlgorithms/Python"),
        "assessment": ("Algorithm practice", "https://leetcode.com/problemset/"),
    },
    "communication": {
        "course": ("Business communication", "https://www.open.edu/openlearn/money-business/business-communication/content-section-0"),
        "project": ("Workplace communication guide", "https://www.mindtools.com/communication-skills/"),
        "assessment": ("Communication skills self-assessment", "https://www.skillsyouneed.com/ips/communication-skills.html"),
    },
    "analytics": {
        "course": ("Google Analytics Academy", "https://skillshop.exceedlms.com/student/catalog"),
        "project": ("Kaggle data analytics projects", "https://www.kaggle.com/learn"),
        "assessment": ("Data analysis practice", "https://www.datacamp.com/blog/data-analytics-projects-for-beginners"),
    },
    "research": {
        "course": ("Research methods guide", "https://libguides.usc.edu/writingguide/researchdesigns"),
        "project": ("Google Search education", "https://newsinitiative.withgoogle.com/resources/trainings/google-search/"),
        "assessment": ("Research methods practice", "https://www.open.edu/openlearn/education-development/research-methods-education/content-section-0"),
    },
}


def get_learning_resource(skill_name: str, module_type: str) -> tuple[str, str] | None:
    resources = SKILL_RESOURCES.get(_normalize_skill_name(skill_name))
    if resources is None:
        return None
    return resources.get(module_type)


def _normalize_skill_name(name: str) -> str:
    return name.strip().lower()


def _ensure_skill(db: Session, skill_name: str) -> Skill:
    normalized = _normalize_skill_name(skill_name)
    skill = db.query(Skill).filter(func.lower(Skill.name) == normalized).first()
    if skill is not None:
        return skill

    skill = Skill(
        name=skill_name.strip().title(),
        category="core",
        description=f"Skill auto-created for {skill_name.title()} tracking.",
        demand_score=0.0,
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


def ensure_learner_profile(db: Session, user: User) -> LearnerProfile:
    profile = db.query(LearnerProfile).filter(LearnerProfile.user_id == user.id).first()
    if profile is not None:
        return profile

    profile = LearnerProfile(
        user_id=user.id,
        target_role="data analyst" if user.role == "learner" else user.role,
        current_stage="assessing",
        self_assessment_score=0.0,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def _ensure_learner_skill(db: Session, profile: LearnerProfile, skill_name: str, target_rating: float) -> LearnerSkill:
    skill = _ensure_skill(db, skill_name)
    learner_skill = (
        db.query(LearnerSkill)
        .filter(
            LearnerSkill.learner_profile_id == profile.id,
            LearnerSkill.skill_id == skill.id,
        )
        .first()
    )
    if learner_skill is not None:
        learner_skill.target_rating = target_rating
        learner_skill.gap_score = max(0.0, target_rating - float(learner_skill.self_rating or 0.0))
        db.commit()
        return learner_skill

    learner_skill = LearnerSkill(
        learner_profile_id=profile.id,
        skill_id=skill.id,
        self_rating=0.0,
        target_rating=target_rating,
        gap_score=target_rating,
    )
    db.add(learner_skill)
    db.commit()
    db.refresh(learner_skill)
    return learner_skill


def get_role_skill_requirements(role: str | None) -> dict[str, float]:
    normalized = (role or "learner").strip().lower()
    return ROLE_SKILL_MAP.get(normalized, ROLE_SKILL_MAP["learner"]).copy()


def calculate_skill_gap(db: Session, user: User) -> dict[str, Any]:
    profile = ensure_learner_profile(db, user)
    required_skills = get_role_skill_requirements(profile.target_role or user.role)

    for skill_name, target_rating in required_skills.items():
        _ensure_learner_skill(db, profile, skill_name, target_rating)

    learner_skills = {
        _normalize_skill_name(ls.skill.name): float(ls.self_rating or 0.0)
        for ls in profile.skill_assessments
    }

    gaps: list[dict[str, Any]] = []
    for skill_name, target_rating in required_skills.items():
        current_rating = learner_skills.get(skill_name, 0.0)
        gap_score = max(0.0, target_rating - current_rating)
        if gap_score > 0:
            gaps.append(
                {
                    "skill_name": skill_name.title(),
                    "current_rating": round(current_rating, 2),
                    "target_rating": round(target_rating, 2),
                    "gap_score": round(gap_score, 2),
                    "priority": "high" if gap_score >= 2.0 else "medium",
                }
            )

    gaps.sort(key=lambda item: (-item["gap_score"], item["skill_name"]))
    return {
        "target_role": profile.target_role or user.role,
        "gaps": gaps,
    }


def build_learning_recommendations(db: Session, user: User) -> dict[str, Any]:
    gap_payload = calculate_skill_gap(db, user)
    items = []
    for gap in gap_payload["gaps"]:
        skill_name = gap["skill_name"]
        priority_score = round((gap["gap_score"] / max(gap["target_rating"], 1.0)) * 100, 2)
        items.append(
            {
                "skill_name": skill_name,
                "current_rating": gap["current_rating"],
                "target_rating": gap["target_rating"],
                "gap_score": gap["gap_score"],
                "priority_score": priority_score,
                "suggested_action": f"Complete a focused learning sprint for {skill_name} and validate with a project-based assessment.",
            }
        )

    items.sort(key=lambda item: (-item["priority_score"], item["skill_name"]))
    return {"target_role": gap_payload["target_role"], "items": items}


def match_opportunities(db: Session, user: User) -> list[dict[str, Any]]:
    profile = ensure_learner_profile(db, user)
    learner_skills = {
        _normalize_skill_name(ls.skill.name): float(ls.self_rating or 0.0)
        for ls in profile.skill_assessments
    }

    opportunities = db.query(Opportunity).filter(Opportunity.status == "active").all()
    matches: list[dict[str, Any]] = []
    for opportunity in opportunities:
        weighted_score = 0.0
        total_weight = 0.0
        for requirement in opportunity.required_skills:
            skill_name = _normalize_skill_name(requirement.skill.name)
            required_level = float(requirement.required_level or 3.0)
            weight = float(requirement.weight or 1.0)
            candidate_rating = learner_skills.get(skill_name, 0.0)
            weighted_score += min(candidate_rating / required_level, 1.0) * weight
            total_weight += weight

        match_score = round((weighted_score / total_weight) * 100, 2) if total_weight else 0.0
        matches.append(
            {
                "id": str(opportunity.id),
                "company_name": opportunity.company_name,
                "title": opportunity.title,
                "location": opportunity.location,
                "employment_type": opportunity.employment_type,
                "match_score": match_score,
            }
        )

    matches.sort(key=lambda item: (-item["match_score"], item["company_name"]))
    return matches
