"""Persona validation checks for generated populations."""

from __future__ import annotations

from collections import Counter

from gan_simlab.schemas.artifacts import PersonaValidationArtifact, PersonaValidationCheck
from gan_simlab.schemas.scenario import Scenario


def build_persona_validation(
    *,
    run_id: str,
    scenario: Scenario,
    persona: dict[str, list[float] | list[int] | list[str] | list[dict[str, float]]],
    group_labels: dict[int, str],
) -> PersonaValidationArtifact:
    checks: list[PersonaValidationCheck] = []
    warnings: list[str] = []
    group_ids = [int(value) for value in persona["group_id"]]
    population_size = len(group_ids)
    counts = Counter(group_ids)

    for group_index, archetype in enumerate(scenario.population.archetypes):
        expected_share = archetype.share
        actual_share = counts[group_index] / population_size if population_size else 0.0
        difference = abs(actual_share - expected_share)
        checks.append(
            PersonaValidationCheck(
                check_id=f"group_share:{archetype.id}",
                passed=difference <= 0.02,
                actual=round(actual_share, 4),
                expected=round(expected_share, 4),
                message=f"group share drift for {archetype.id} stayed within tolerance",
            )
        )

    conflict_variance = _population_variance(persona["conflict_tolerance"])
    reply_variance = _population_variance(persona["reply_tendency"])
    checks.append(
        PersonaValidationCheck(
            check_id="variance:conflict_tolerance",
            passed=conflict_variance >= 0.0025,
            actual=round(conflict_variance, 6),
            expected=">= 0.0025",
            message="conflict tolerance retains minimum diversity",
        )
    )
    checks.append(
        PersonaValidationCheck(
            check_id="variance:reply_tendency",
            passed=reply_variance >= 0.0025,
            actual=round(reply_variance, 6),
            expected=">= 0.0025",
            message="reply tendency retains minimum diversity",
        )
    )

    distinct_tones = len(set(str(value) for value in persona["tone_style"]))
    distinct_arguments = len(set(str(value) for value in persona["argument_style"]))
    checks.append(
        PersonaValidationCheck(
            check_id="style_diversity:tone_style",
            passed=distinct_tones > 1,
            actual=distinct_tones,
            expected="> 1",
            message="tone styles retain group-level diversity",
        )
    )
    checks.append(
        PersonaValidationCheck(
            check_id="style_diversity:argument_style",
            passed=distinct_arguments > 1,
            actual=distinct_arguments,
            expected="> 1",
            message="argument styles retain group-level diversity",
        )
    )
    if distinct_tones <= 1:
        warnings.append("tone styles collapsed to a single value")
    if distinct_arguments <= 1:
        warnings.append("argument styles collapsed to a single value")

    passed = all(check.passed for check in checks)
    return PersonaValidationArtifact(
        run_id=run_id,
        scenario_id=scenario.scenario_id,
        passed=passed,
        checks=checks,
        warnings=warnings,
    )


def _population_variance(values: list[float]) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    return sum((value - mean) ** 2 for value in values) / len(values)
