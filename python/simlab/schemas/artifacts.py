"""Artifact schemas for reproducible runs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class RunConfigArtifact(BaseModel):
    run_id: str
    scenario_id: str
    run_mode: str
    artifact_verbosity: str
    kernel_backend: str
    prepared_input_source: str
    prepared_input_cache_key: str
    population_size: int
    rounds: int
    random_seed: int
    channel_ids: list[str]
    narrative_tokens: list[str]


class RoundMetric(BaseModel):
    round_index: int
    total_exposures: int
    total_posts: int
    mean_stance: float
    mean_trust: float
    mean_salience: float
    rumor_share: float
    clarification_share: float


class GroupMetric(BaseModel):
    round_index: int
    group_id: str
    population: int
    mean_stance: float
    mean_trust: float
    mean_salience: float
    post_count: int


class TimelineEvent(BaseModel):
    round_index: int
    event_type: Literal[
        "intervention_applied",
        "narrative_spike",
        "group_shift",
        "rumor_peak",
        "clarification_peak",
    ]
    subject_id: str
    details: dict[str, float | int | str]


class ValidationCheck(BaseModel):
    check_id: str
    passed: bool
    actual: float | int | str
    expected: float | int | str
    message: str


class ValidationArtifact(BaseModel):
    run_id: str
    passed: bool
    checks: list[ValidationCheck]


class MetricsArtifact(BaseModel):
    run_id: str
    round_metrics: list[RoundMetric]
    group_metrics: list[GroupMetric]


class GroundingEvidence(BaseModel):
    query_label: str
    source_path: str
    chunk_id: str
    score: float
    snippet: str


class GroundingArtifact(BaseModel):
    run_id: str
    scenario_id: str
    source_count: int
    query_count: int
    evidence: list[GroundingEvidence]


class GroundingStatusArtifact(BaseModel):
    run_id: str
    scenario_id: str
    status: Literal["disabled", "succeeded", "failed"]
    error_code: str | None = None
    message: str | None = None
    source_count: int = 0
    query_count: int = 0


class PersonaSample(BaseModel):
    agent_id: int
    group_id: str
    age_band: str
    job_type: str
    household_stage: str
    education_level: str
    region_type: str
    income_pressure: float
    media_diet: dict[str, float]
    conflict_tolerance: float
    conformity: float
    risk_aversion: float
    trust_in_officials_baseline: float
    rumor_susceptibility: float
    correction_acceptance: float
    reply_tendency: float
    post_tendency: float
    reaction_tendency: float
    verbosity: float
    tone_style: str
    argument_style: str


class PersonaGroupSummary(BaseModel):
    group_id: str
    population: int
    mean_income_pressure: float
    mean_conflict_tolerance: float
    mean_trust_in_officials_baseline: float
    mean_rumor_susceptibility: float
    mean_correction_acceptance: float
    mean_reply_tendency: float
    mean_verbosity: float
    dominant_tone_style: str
    dominant_argument_style: str


class PersonaSnapshotArtifact(BaseModel):
    run_id: str
    scenario_id: str
    population_size: int
    sample_agents: list[PersonaSample]
    group_summaries: list[PersonaGroupSummary]


class PersonaValidationCheck(BaseModel):
    check_id: str
    passed: bool
    actual: float | int | str
    expected: float | int | str
    message: str


class PersonaValidationArtifact(BaseModel):
    run_id: str
    scenario_id: str
    passed: bool
    checks: list[PersonaValidationCheck]
    warnings: list[str]


class AgentAction(BaseModel):
    round_index: int
    agent_id: int
    group_id: str
    action_type: Literal["post", "reply", "react", "ignore"]
    target_message_id: str | None = None
    target_thread_id: str | None = None
    narrative_token: str
    channel_id: str


class ThreadMessage(BaseModel):
    message_id: str
    thread_id: str
    round_index: int
    agent_id: int
    group_id: str
    action_type: Literal["post", "reply"]
    narrative_token: str
    channel_id: str
    tone_style: str
    argument_style: str
    parent_message_id: str | None = None


class ReactionEvent(BaseModel):
    reaction_id: str
    thread_id: str
    round_index: int
    agent_id: int
    group_id: str
    target_message_id: str
    reaction_kind: Literal["endorse", "question", "amplify"]
    narrative_token: str
    channel_id: str


class ThreadArtifact(BaseModel):
    thread_id: str
    channel_id: str
    narrative_token: str
    created_round: int
    root_message_id: str
    message_count: int
    reaction_count: int
    participant_groups: list[str]


class InteractionGroupMetric(BaseModel):
    round_index: int
    group_id: str
    activation_count: int
    post_count: int
    reply_count: int
    reaction_count: int
    ignore_count: int


class RoundActionMetric(BaseModel):
    round_index: int
    activation_count: int
    post_count: int
    reply_count: int
    reaction_count: int
    ignore_count: int


class InteractionSummaryArtifact(BaseModel):
    run_id: str
    scenario_id: str
    total_rounds: int
    thread_count: int
    message_count: int
    reaction_count: int
    action_counts: dict[str, int]
    per_round_active_agents: list[int]
    round_metrics: list[RoundActionMetric]
    group_metrics: list[InteractionGroupMetric]


class InteractionValidationCheck(BaseModel):
    check_id: str
    passed: bool
    actual: float | int | str
    expected: float | int | str
    message: str


class InteractionValidationArtifact(BaseModel):
    run_id: str
    scenario_id: str
    passed: bool
    checks: list[InteractionValidationCheck]
    warnings: list[str]


class ConversationEntry(BaseModel):
    round_index: int
    thread_id: str
    message_id: str
    agent_id: int
    group_id: str
    action_type: Literal["post", "reply", "react"]
    rendered_text: str
    narrative_token: str
    channel_id: str
    tone_style: str
    argument_style: str


class SummaryArtifact(BaseModel):
    run_id: str
    scenario_id: str
    run_mode: str
    kernel_backend: str
    validation_passed: bool
    grounding_enabled: bool = False
    grounding_source_count: int = 0
    execution_time_ms: float = 0.0
    prepare_time_ms: float = 0.0
    kernel_time_ms: float = 0.0
    interaction_time_ms: float = 0.0
    grounding_time_ms: float = 0.0
    edge_count: int = 0
    final_round_index: int
    final_mean_stance: float
    final_mean_trust: float
    final_mean_salience: float
    groups: list[GroupMetric]


class BenchmarkEntry(BaseModel):
    population_size: int
    rounds: int
    edge_count: int
    prepare_time_ms: float
    kernel_time_ms: float
    interaction_time_ms: float
    total_time_ms: float
    final_mean_stance: float
    final_mean_trust: float


class BenchmarkArtifact(BaseModel):
    scenario_id: str
    kernel_backend: str
    entries: list[BenchmarkEntry]
