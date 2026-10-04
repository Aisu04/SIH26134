from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        nullable=False,
    )


class Institution(Base, TimestampMixin):
    __tablename__ = "institutions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    sector: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    users: Mapped[list[User]] = relationship(back_populates="institution")
    opportunities: Mapped[list[Opportunity]] = relationship(back_populates="institution")
    cohorts: Mapped[list[TrainingCohort]] = relationship(back_populates="institution")


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="learner", nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    institution_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("institutions.id"), nullable=True)

    institution: Mapped[Institution | None] = relationship(back_populates="users")
    learner_profile: Mapped[LearnerProfile | None] = relationship(back_populates="user", uselist=False)
    cohort_enrollments: Mapped[list[CohortEnrollment]] = relationship(back_populates="learner")


class TrainingCohort(Base, TimestampMixin):
    __tablename__ = "training_cohorts"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    institution_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("institutions.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    program: Mapped[str] = mapped_column(String(200), nullable=False)
    capacity: Mapped[int] = mapped_column(nullable=False, default=30)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active", server_default="active")

    institution: Mapped[Institution] = relationship(back_populates="cohorts")
    enrollments: Mapped[list[CohortEnrollment]] = relationship(back_populates="cohort")


class CohortEnrollment(Base, TimestampMixin):
    __tablename__ = "cohort_enrollments"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    cohort_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("training_cohorts.id"), nullable=False, index=True)
    learner_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active", server_default="active")

    cohort: Mapped[TrainingCohort] = relationship(back_populates="enrollments")
    learner: Mapped[User] = relationship(back_populates="cohort_enrollments")

    __table_args__ = (
        UniqueConstraint("cohort_id", "learner_user_id", name="uq_cohort_learner"),
    )


class Skill(Base, TimestampMixin):
    __tablename__ = "skills"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    demand_score: Mapped[float | None] = mapped_column(nullable=True)

    learner_skills: Mapped[list[LearnerSkill]] = relationship(back_populates="skill")
    opportunity_skills: Mapped[list[OpportunitySkill]] = relationship(back_populates="skill")


class LearnerProfile(Base, TimestampMixin):
    __tablename__ = "learner_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    target_role: Mapped[str | None] = mapped_column(String(150), nullable=True)
    preferred_location: Mapped[str | None] = mapped_column(String(150), nullable=True)
    current_stage: Mapped[str] = mapped_column(String(80), default="exploring", nullable=False)
    self_assessment_score: Mapped[float | None] = mapped_column(nullable=True)

    user: Mapped[User] = relationship(back_populates="learner_profile")
    skill_assessments: Mapped[list[LearnerSkill]] = relationship(back_populates="learner_profile")
    learning_paths: Mapped[list[LearningPath]] = relationship(back_populates="learner_profile")
    outcomes: Mapped[list[EmploymentOutcome]] = relationship(back_populates="learner_profile")


class LearnerSkill(Base, TimestampMixin):
    __tablename__ = "learner_skills"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    learner_profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("learner_profiles.id"), nullable=False)
    skill_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("skills.id"), nullable=False)
    self_rating: Mapped[float | None] = mapped_column(nullable=True)
    target_rating: Mapped[float | None] = mapped_column(nullable=True)
    gap_score: Mapped[float | None] = mapped_column(nullable=True)

    learner_profile: Mapped[LearnerProfile] = relationship(back_populates="skill_assessments")
    skill: Mapped[Skill] = relationship(back_populates="learner_skills")

    __table_args__ = (
        UniqueConstraint("learner_profile_id", "skill_id", name="uq_learner_skill"),
    )


class LearningPath(Base, TimestampMixin):
    __tablename__ = "learning_paths"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    learner_profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("learner_profiles.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)
    priority_score: Mapped[float | None] = mapped_column(nullable=True)

    learner_profile: Mapped[LearnerProfile] = relationship(back_populates="learning_paths")
    items: Mapped[list[LearningPathItem]] = relationship(back_populates="learning_path")


class LearningPathItem(Base, TimestampMixin):
    __tablename__ = "learning_path_items"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    learning_path_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("learning_paths.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    module_type: Mapped[str] = mapped_column(String(80), default="course", nullable=False)
    estimated_hours: Mapped[int | None] = mapped_column(nullable=True)
    order_index: Mapped[int] = mapped_column(nullable=False, default=0)
    resource_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    resource_label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default="not_started", server_default="not_started", nullable=False
    )

    learning_path: Mapped[LearningPath] = relationship(back_populates="items")


class Opportunity(Base, TimestampMixin):
    __tablename__ = "opportunities"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    institution_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("institutions.id"), nullable=True)
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    employment_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    salary_band: Mapped[str | None] = mapped_column(String(80), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)

    institution: Mapped[Institution | None] = relationship(back_populates="opportunities")
    owner: Mapped[User | None] = relationship()
    required_skills: Mapped[list[OpportunitySkill]] = relationship(back_populates="opportunity")
    outcomes: Mapped[list[EmploymentOutcome]] = relationship(back_populates="opportunity")


class OpportunitySkill(Base, TimestampMixin):
    __tablename__ = "opportunity_skills"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("opportunities.id"), nullable=False)
    skill_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("skills.id"), nullable=False)
    required_level: Mapped[float | None] = mapped_column(nullable=True)
    weight: Mapped[float | None] = mapped_column(nullable=True)

    opportunity: Mapped[Opportunity] = relationship(back_populates="required_skills")
    skill: Mapped[Skill] = relationship(back_populates="opportunity_skills")

    __table_args__ = (
        UniqueConstraint("opportunity_id", "skill_id", name="uq_opportunity_skill"),
    )


class EmploymentOutcome(Base, TimestampMixin):
    __tablename__ = "employment_outcomes"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    learner_profile_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("learner_profiles.id"), nullable=False)
    opportunity_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("opportunities.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(80), default="in_progress", nullable=False)
    placement_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    learner_profile: Mapped[LearnerProfile] = relationship(back_populates="outcomes")
    opportunity: Mapped[Opportunity | None] = relationship(back_populates="outcomes")

    __table_args__ = (
        UniqueConstraint("learner_profile_id", "opportunity_id", name="uq_learner_opportunity_application"),
    )
