"""Schemas for gallery-oriented post engagement simulations."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class GalleryConceptThreshold(BaseModel):
    recommendation_count: int = Field(ge=1)
    minimum_velocity_score: float = Field(ge=0.0, le=1.0)
    minimum_lurker_conversion_score: float = Field(ge=0.0, le=1.0)


class GalleryBaselineMood(BaseModel):
    cynicism: float = Field(ge=0.0, le=1.0)
    career_anxiety: float = Field(ge=0.0, le=1.0)
    rumor_heat: float = Field(ge=0.0, le=1.0)
    meme_appetite: float = Field(ge=0.0, le=1.0)
    analysis_tolerance: float = Field(ge=0.0, le=1.0)


class GalleryConfig(BaseModel):
    id: str
    label: str
    platform: str
    culture_tokens: list[str] = Field(default_factory=list)
    concept_threshold: GalleryConceptThreshold
    baseline_mood: GalleryBaselineMood


class GalleryArchetype(BaseModel):
    id: str
    label: str
    share: float = Field(gt=0.0, le=1.0)
    activity: float = Field(ge=0.0, le=1.0)
    recommendation_tendency: float = Field(ge=0.0, le=1.0)
    reply_tendency: float = Field(ge=0.0, le=1.0)
    reaction_tendency: float = Field(ge=0.0, le=1.0)
    ignore_tendency: float = Field(ge=0.0, le=1.0)
    controversy_preference: float = Field(ge=0.0, le=1.0)
    usefulness_sensitivity: float = Field(ge=0.0, le=1.0)
    insider_credibility_sensitivity: float = Field(ge=0.0, le=1.0)
    meme_affinity: float = Field(ge=0.0, le=1.0)
    career_anxiety: float = Field(ge=0.0, le=1.0)
    cynicism: float = Field(ge=0.0, le=1.0)
    gallery_native_tone_preference: float = Field(ge=0.0, le=1.0)
    silent_conversion_weight: float = Field(ge=0.0, le=1.0)


class GalleryPopulationConfig(BaseModel):
    size: int = Field(ge=10, le=1_000_000)
    archetypes: list[GalleryArchetype]

    @model_validator(mode="after")
    def validate_shares(self) -> "GalleryPopulationConfig":
        total = sum(archetype.share for archetype in self.archetypes)
        if abs(total - 1.0) > 1e-6:
            raise ValueError("archetype shares must sum to 1.0")
        return self


class CandidatePostFeatures(BaseModel):
    title_style: str
    body_length: float = Field(ge=0.0, le=1.0)
    information_density: float = Field(ge=0.0, le=1.0)
    emotional_charge: float = Field(ge=0.0, le=1.0)
    irony_level: float = Field(ge=0.0, le=1.0)
    outrage_level: float = Field(ge=0.0, le=1.0)
    insider_credibility_signal: float = Field(ge=0.0, le=1.0)
    practical_utility: float = Field(ge=0.0, le=1.0)
    technical_depth: float = Field(ge=0.0, le=1.0)
    empathy_signal: float = Field(ge=0.0, le=1.0)
    meme_fitness: float = Field(ge=0.0, le=1.0)
    controversy_level: float = Field(ge=0.0, le=1.0)
    anti_corporate_charge: float = Field(ge=0.0, le=1.0)
    gallery_native_tone_fit: float = Field(ge=0.0, le=1.0)
    timing_relevance: float = Field(ge=0.0, le=1.0)


class CandidatePostConfig(BaseModel):
    id: str
    label: str
    features: CandidatePostFeatures


class GallerySimulationConfig(BaseModel):
    rounds: int = Field(ge=1, le=365)
    random_seed: int
    max_interactions_per_round: int = Field(ge=1)
    gallery_feed_exposure_weight: float = Field(gt=0.0)
    reply_visibility_multiplier: float = Field(ge=0.0)
    recommendation_visibility_multiplier: float = Field(ge=0.0)
    controversy_boost_multiplier: float = Field(ge=0.0)
    lurker_conversion_multiplier: float = Field(ge=0.0)


class GalleryScenario(BaseModel):
    scenario_id: str
    title: str
    version: str
    gallery: GalleryConfig
    population: GalleryPopulationConfig
    candidate_posts: list[CandidatePostConfig]
    simulation: GallerySimulationConfig


class GalleryArchetypeContribution(BaseModel):
    archetype_id: str
    archetype_label: str
    visible_agents: int
    reply_count: int
    reaction_count: int
    recommendation_count: int
    alignment_score: float
    silent_recommendation_count: int


class GalleryCandidatePostResult(BaseModel):
    post_id: str
    label: str
    ranking_position: int
    view_activation_score: float
    reply_count_estimate: int
    reaction_count_estimate: int
    recommendation_count_estimate: int
    early_velocity_score: float
    mid_run_decay_score: float
    controversy_score: float
    lurker_conversion_score: float
    concept_threshold_reached: bool
    concept_likelihood_score: float
    peak_visibility_score: float
    sustained_attention_score: float
    archetype_contributions: list[GalleryArchetypeContribution]
    visibility_curve: list[float]


class GalleryRunArtifact(BaseModel):
    run_id: str
    scenario_id: str
    gallery_id: str
    gallery_label: str
    population_size: int
    rounds: int
    concept_threshold: GalleryConceptThreshold
    posts: list[GalleryCandidatePostResult]


class GalleryValidationCheck(BaseModel):
    check_id: str
    passed: bool
    message: str
    metric: str
    target: str
    actual: float | int | bool | str
    expected: float | int | bool | str


class GalleryValidationArtifact(BaseModel):
    run_id: str
    scenario_id: str
    passed: bool
    checks: list[GalleryValidationCheck]


class GalleryAssertionCondition(BaseModel):
    metric: str
    target: str
    comparison: Literal["gte", "gt", "lte", "lt", "eq", "lt_target", "gt_target"]
    value: float | int | bool | str | None = None
    other_target: str | None = None


class GalleryAssertion(BaseModel):
    id: str
    description: str
    kind: Literal["ranking", "compound"]
    metric: str | None = None
    target: str | None = None
    higher_than: str | None = None
    checks: list[GalleryAssertionCondition] = Field(default_factory=list)


class GalleryAssertionsArtifact(BaseModel):
    scenario_id: str
    version: str
    assertions: list[GalleryAssertion]
