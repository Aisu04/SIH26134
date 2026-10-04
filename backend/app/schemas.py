from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def _validate_bcrypt_password_length(password: str) -> str:
    if len(password.encode("utf-8")) > 72:
        raise ValueError("Password must be at most 72 UTF-8 bytes.")
    return password


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, password: str) -> str:
        return _validate_bcrypt_password_length(password)


class AdminUserCreate(UserCreate):
    role: Literal["learner", "employer", "institution"]
    institution_id: UUID | None = None


class InstitutionCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    sector: str = Field(min_length=2, max_length=100)
    location: str | None = Field(default=None, max_length=200)
    description: str | None = None


class InstitutionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    sector: str
    location: str | None
    description: str | None


class InstitutionLearnerResponse(BaseModel):
    id: UUID
    full_name: str
    email: EmailStr


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_fits_bcrypt(cls, password: str) -> str:
        return _validate_bcrypt_password_length(password)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    full_name: str
    email: EmailStr
    role: str
    is_active: bool = True


class UserProfile(UserPublic):
    pass


class SkillGapItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    skill_name: str
    current_rating: float
    target_rating: float
    gap_score: float
    priority: str


class SkillGapResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    target_role: str
    gaps: list[SkillGapItem]


class LearningRecommendation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    skill_name: str
    current_rating: float
    target_rating: float
    gap_score: float
    priority_score: float
    suggested_action: str


class LearningRecommendationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    target_role: str
    items: list[LearningRecommendation]


class OpportunitySkillInput(BaseModel):
    skill_name: str
    required_level: float = 3.0
    weight: float = 1.0


class OpportunityCreate(BaseModel):
    company_name: str
    title: str
    location: str | None = None
    employment_type: str | None = None
    salary_band: str | None = None
    description: str | None = None
    required_skills: list[OpportunitySkillInput] = Field(default_factory=list)


class OpportunityMatch(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_name: str
    title: str
    location: str | None = None
    employment_type: str | None = None
    match_score: float


class EmployerOpportunityResponse(BaseModel):
    id: UUID
    company_name: str
    title: str
    location: str | None
    employment_type: str | None
    salary_band: str | None
    description: str | None
    status: str
    required_skills: list[OpportunitySkillInput]


class OpportunityStatusUpdate(BaseModel):
    status: Literal["active", "closed"]


ApplicationStatus = Literal["applied", "reviewing", "interview", "offered", "hired", "rejected"]


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus


class EmploymentOutcomeResponse(BaseModel):
    id: UUID
    opportunity_id: UUID
    company_name: str
    opportunity_title: str
    learner_name: str
    learner_email: str
    status: str
    applied_at: datetime
    placement_date: datetime | None


class InstitutionAnalyticsResponse(BaseModel):
    institution_name: str
    learner_count: int
    assessed_learner_count: int
    application_count: int
    applicants_count: int
    placement_count: int
    active_opportunity_count: int
    application_rate_percent: float
    placement_rate_percent: float


class TrainingCohortCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    program: str = Field(min_length=2, max_length=200)
    capacity: int = Field(default=30, ge=1, le=5000)


class CohortEnrollmentCreate(BaseModel):
    learner_user_id: UUID


class CohortLearnerResponse(BaseModel):
    user_id: UUID
    full_name: str
    email: EmailStr
    status: str


class TrainingCohortResponse(BaseModel):
    id: UUID
    name: str
    program: str
    capacity: int
    status: str
    learner_count: int
    assessed_learner_count: int
    application_count: int
    placement_count: int
    learners: list[CohortLearnerResponse]


TargetRole = Literal["data analyst", "software engineer", "product manager"]


class LearnerProfileUpdate(BaseModel):
    target_role: TargetRole
    preferred_location: str | None = Field(default=None, max_length=150)


class LearnerSkillRatingInput(BaseModel):
    skill_name: str = Field(min_length=1, max_length=150)
    self_rating: float = Field(ge=0, le=5)


class LearnerSkillAssessmentUpdate(BaseModel):
    ratings: list[LearnerSkillRatingInput] = Field(min_length=1)


class LearnerSkillAssessmentItem(BaseModel):
    skill_name: str
    self_rating: float
    target_rating: float
    gap_score: float


class LearnerProfileResponse(BaseModel):
    target_role: str
    preferred_location: str | None
    skills: list[LearnerSkillAssessmentItem]


class LearningPathItemStatusUpdate(BaseModel):
    status: Literal["not_started", "in_progress", "completed"]


class LearningPathItemResponse(BaseModel):
    id: UUID
    title: str
    module_type: str
    estimated_hours: int | None
    order_index: int
    resource_url: str | None
    resource_label: str | None
    status: str


class LearningPathResponse(BaseModel):
    id: UUID
    title: str
    status: str
    priority_score: float | None
    items: list[LearningPathItemResponse]
