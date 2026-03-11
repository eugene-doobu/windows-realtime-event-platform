"""Scenario input schemas for runtime-injected simulations."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class ChannelKind(StrEnum):
    NEWS = "news"
    COMMUNITY = "community"
    PRIVATE_CHAT = "private_chat"


class InterventionKind(StrEnum):
    ANNOUNCEMENT = "announcement"
    CLARIFICATION = "clarification"
    SUPPORT_MEASURE = "support_measure"
    RUMOR = "rumor"
    FACT_CHECK = "fact_check"


class ArchetypeSpec(BaseModel):
    id: str
    label: str
    share: float = Field(gt=0, le=1)
    base_stance: float = Field(ge=-1.0, le=1.0)
    base_trust: float = Field(ge=0.0, le=1.0)
    base_salience: float = Field(ge=0.0, le=1.0)
    base_susceptibility: float = Field(ge=0.0, le=1.0)
    base_activity: float = Field(ge=0.0, le=1.0)
    base_influence: float = Field(ge=0.0, le=1.0)
    narrative_affinity: dict[str, float] = Field(default_factory=dict)
    channel_affinity: dict[ChannelKind, float] = Field(default_factory=dict)
    age_band: str = "adult"
    job_type: str = "general_worker"
    household_stage: str = "single_adult"
    education_level: str = "mixed"
    region_type: str = "mixed"
    income_pressure: float = Field(default=0.5, ge=0.0, le=1.0)
    media_diet: dict[str, float] = Field(default_factory=dict)
    conflict_tolerance: float = Field(default=0.5, ge=0.0, le=1.0)
    conformity: float = Field(default=0.5, ge=0.0, le=1.0)
    risk_aversion: float = Field(default=0.5, ge=0.0, le=1.0)
    trust_in_officials_baseline: float | None = Field(default=None, ge=0.0, le=1.0)
    rumor_susceptibility: float | None = Field(default=None, ge=0.0, le=1.0)
    correction_acceptance: float = Field(default=0.5, ge=0.0, le=1.0)
    reply_tendency: float | None = Field(default=None, ge=0.0, le=1.0)
    post_tendency: float | None = Field(default=None, ge=0.0, le=1.0)
    reaction_tendency: float | None = Field(default=None, ge=0.0, le=1.0)
    verbosity: float = Field(default=0.5, ge=0.0, le=1.0)
    tone_style: str = "neutral"
    argument_style: str = "pragmatic"

    @model_validator(mode="after")
    def populate_persona_defaults(self) -> "ArchetypeSpec":
        if self.trust_in_officials_baseline is None:
            self.trust_in_officials_baseline = self.base_trust
        if self.rumor_susceptibility is None:
            self.rumor_susceptibility = self.base_susceptibility
        if self.post_tendency is None:
            self.post_tendency = self.base_activity
        if self.reply_tendency is None:
            self.reply_tendency = min(1.0, self.base_activity + (self.conflict_tolerance * 0.15))
        if self.reaction_tendency is None:
            self.reaction_tendency = min(1.0, self.base_activity + 0.1)
        if not self.media_diet:
            self.media_diet = {
                channel_kind.value: weight
                for channel_kind, weight in self.channel_affinity.items()
            }
        return self


class PopulationConfig(BaseModel):
    size: int = Field(ge=10, le=100_000)
    archetypes: list[ArchetypeSpec]
    intra_group_edge_prob: float = Field(ge=0.0, le=1.0)
    inter_group_edge_prob: float = Field(ge=0.0, le=1.0)
    intra_group_degree: int = Field(default=12, ge=1, le=256)
    inter_group_degree: int = Field(default=4, ge=0, le=256)
    influencer_ratio: float = Field(ge=0.0, le=0.2)
    variation_sigma: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_shares(self) -> "PopulationConfig":
        total = sum(archetype.share for archetype in self.archetypes)
        if abs(total - 1.0) > 1e-6:
            raise ValueError("archetype shares must sum to 1.0")
        return self


class ChannelConfig(BaseModel):
    id: str
    kind: ChannelKind
    exposure_weight: float = Field(gt=0.0)
    repost_factor: float = Field(ge=0.0)
    rumor_decay: float = Field(ge=0.0, le=1.0)
    trust_penalty: float = Field(ge=0.0, le=1.0)


class InterventionEvent(BaseModel):
    round_index: int = Field(ge=0)
    kind: InterventionKind
    target_groups: list[str] = Field(default_factory=list)
    target_channels: list[str] = Field(default_factory=list)
    narrative_push: dict[str, float] = Field(default_factory=dict)
    trust_delta: float = Field(default=0.0, ge=-1.0, le=1.0)
    stance_delta: float = Field(default=0.0, ge=-1.0, le=1.0)
    salience_delta: float = Field(default=0.0, ge=-1.0, le=1.0)


class SimulationConfig(BaseModel):
    rounds: int = Field(ge=1, le=365)
    random_seed: int
    max_posts_per_round: int = Field(ge=1, le=100_000)
    narrative_tokens: list[str]
    channels: list[ChannelConfig]
    interventions: list[InterventionEvent] = Field(default_factory=list)


class GroundingConfig(BaseModel):
    enabled: bool = False
    document_paths: list[str] = Field(default_factory=list)
    top_k: int = Field(default=5, ge=1, le=20)


class Scenario(BaseModel):
    scenario_id: str
    title: str
    population: PopulationConfig
    simulation: SimulationConfig
    grounding: GroundingConfig = Field(default_factory=GroundingConfig)
