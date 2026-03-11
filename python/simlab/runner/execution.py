"""Execution profiles for cheaper local iteration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from simlab.schemas.scenario import Scenario


class RunMode(StrEnum):
    SMOKE = "smoke"
    STANDARD = "standard"
    FULL = "full"


class ArtifactVerbosity(StrEnum):
    MINIMAL = "minimal"
    STANDARD = "standard"
    FULL = "full"


@dataclass(frozen=True, slots=True)
class RunProfile:
    population_cap: int
    round_cap: int
    max_posts_cap: int
    artifact_verbosity: ArtifactVerbosity


RUN_PROFILES: dict[RunMode, RunProfile] = {
    RunMode.SMOKE: RunProfile(
        population_cap=100,
        round_cap=5,
        max_posts_cap=200,
        artifact_verbosity=ArtifactVerbosity.MINIMAL,
    ),
    RunMode.STANDARD: RunProfile(
        population_cap=300,
        round_cap=10,
        max_posts_cap=1_000,
        artifact_verbosity=ArtifactVerbosity.STANDARD,
    ),
    RunMode.FULL: RunProfile(
        population_cap=100_000,
        round_cap=365,
        max_posts_cap=100_000,
        artifact_verbosity=ArtifactVerbosity.FULL,
    ),
}


def apply_run_mode(scenario: Scenario, run_mode: RunMode) -> Scenario:
    profile = RUN_PROFILES[run_mode]
    resolved = scenario.model_copy(deep=True)
    resolved.population.size = min(resolved.population.size, profile.population_cap)
    resolved.simulation.rounds = min(resolved.simulation.rounds, profile.round_cap)
    resolved.simulation.max_posts_per_round = min(
        resolved.simulation.max_posts_per_round,
        profile.max_posts_cap,
    )
    return resolved


def artifact_verbosity_for_run_mode(run_mode: RunMode) -> ArtifactVerbosity:
    return RUN_PROFILES[run_mode].artifact_verbosity
