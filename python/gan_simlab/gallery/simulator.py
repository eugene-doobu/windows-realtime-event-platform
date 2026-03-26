"""Simulation logic for gallery-oriented post ranking experiments."""

from __future__ import annotations

from uuid import uuid4

from gan_simlab.gallery.schema import (
    GalleryAssertion,
    GalleryAssertionCondition,
    GalleryAssertionsArtifact,
    GalleryArchetypeContribution,
    GalleryCandidatePostResult,
    GalleryRunArtifact,
    GalleryScenario,
    GalleryValidationArtifact,
    GalleryValidationCheck,
)


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _weighted_attention_score(scenario: GalleryScenario, archetype, features) -> float:
    mood = scenario.gallery.baseline_mood
    usefulness_fit = features.practical_utility * archetype.usefulness_sensitivity
    insider_fit = features.insider_credibility_signal * archetype.insider_credibility_sensitivity
    meme_fit = features.meme_fitness * archetype.meme_affinity
    cynicism_fit = mood.cynicism * archetype.cynicism * features.anti_corporate_charge
    career_fit = mood.career_anxiety * archetype.career_anxiety * (
        (features.practical_utility * 0.55) + (features.empathy_signal * 0.45)
    )
    controversy_fit = features.controversy_level * archetype.controversy_preference
    tone_fit = features.gallery_native_tone_fit * archetype.gallery_native_tone_preference
    analysis_fit = features.technical_depth * ((archetype.usefulness_sensitivity * 0.7) + ((1.0 - archetype.meme_affinity) * 0.3))
    timing_fit = features.timing_relevance
    emotional_fit = features.emotional_charge * (0.45 + (archetype.reply_tendency * 0.55))

    score = (
        0.18 * usefulness_fit
        + 0.16 * insider_fit
        + 0.11 * meme_fit
        + 0.13 * cynicism_fit
        + 0.10 * career_fit
        + 0.10 * controversy_fit
        + 0.09 * tone_fit
        + 0.09 * analysis_fit
        + 0.04 * timing_fit
        + 0.05 * emotional_fit
    )
    score += 0.08 * mood.rumor_heat * features.insider_credibility_signal
    score += 0.06 * mood.meme_appetite * features.meme_fitness
    score += 0.05 * mood.analysis_tolerance * features.technical_depth
    return clamp01(score)


def _build_visibility_curve(
    *,
    scenario: GalleryScenario,
    early_velocity_score: float,
    sustained_attention_score: float,
    controversy_score: float,
    recommendation_count_estimate: int,
    mid_run_decay_score: float,
    peak_visibility_score: float,
) -> list[float]:
    curve: list[float] = []
    current = peak_visibility_score
    recommendation_signal = recommendation_count_estimate / max(scenario.population.size * 0.2, 1)
    decay_factor = clamp01(0.42 + (sustained_attention_score * 0.33) + (0.20 * (1.0 - mid_run_decay_score)))
    controversy_boost = controversy_score * scenario.simulation.controversy_boost_multiplier * 0.18
    recommendation_boost = recommendation_signal * scenario.simulation.recommendation_visibility_multiplier * 0.14
    opening_boost = early_velocity_score * 0.11

    for round_index in range(scenario.simulation.rounds):
        if round_index == 0:
            current = clamp01(current + opening_boost)
        else:
            current = clamp01((current * decay_factor) + controversy_boost + recommendation_boost)
        curve.append(round(current, 4))
    return curve


def _post_result(scenario: GalleryScenario, candidate_post) -> GalleryCandidatePostResult:
    features = candidate_post.features
    contributions: list[GalleryArchetypeContribution] = []
    total_visible = 0
    total_replies = 0
    total_reactions = 0
    total_recommendations = 0
    silent_recommendations = 0
    weighted_alignment = 0.0

    for archetype in scenario.population.archetypes:
        archetype_population = int(round(scenario.population.size * archetype.share))
        alignment_score = _weighted_attention_score(scenario, archetype, features)
        attention = clamp01(
            scenario.simulation.gallery_feed_exposure_weight
            * archetype.activity
            * (0.35 + (alignment_score * 0.65))
            * (0.45 + (features.timing_relevance * 0.55))
        )
        visible_agents = int(round(archetype_population * attention))

        reply_rate = clamp01(
            archetype.reply_tendency
            * (
                0.16
                + (features.controversy_level * 0.28)
                + (features.emotional_charge * 0.17)
                + (features.gallery_native_tone_fit * 0.12)
                + (features.outrage_level * 0.14)
                + (alignment_score * 0.13)
            )
        )
        reaction_rate = clamp01(
            archetype.reaction_tendency
            * (
                0.18
                + (features.meme_fitness * 0.24)
                + (features.emotional_charge * 0.12)
                + (features.controversy_level * 0.14)
                + (features.irony_level * 0.10)
                + (alignment_score * 0.12)
            )
        )
        recommend_rate = clamp01(
            archetype.recommendation_tendency
            * (
                0.18
                + (features.practical_utility * archetype.usefulness_sensitivity * 0.18)
                + (features.insider_credibility_signal * archetype.insider_credibility_sensitivity * 0.16)
                + (features.technical_depth * (0.5 + (archetype.usefulness_sensitivity * 0.5)) * 0.13)
                + (features.empathy_signal * archetype.silent_conversion_weight * 0.14)
                + (features.gallery_native_tone_fit * archetype.gallery_native_tone_preference * 0.10)
                + (features.anti_corporate_charge * archetype.cynicism * 0.11)
                + (alignment_score * 0.10)
            )
        )

        reply_count = int(round(visible_agents * reply_rate * 0.34))
        reaction_count = int(round(visible_agents * reaction_rate * 0.47))
        silent_recommendation_count = int(
            round(
                visible_agents
                * archetype.silent_conversion_weight
                * recommend_rate
                * scenario.simulation.lurker_conversion_multiplier
                * 0.24
            )
        )
        recommendation_count = int(round(visible_agents * recommend_rate * 0.18)) + silent_recommendation_count

        contributions.append(
            GalleryArchetypeContribution(
                archetype_id=archetype.id,
                archetype_label=archetype.label,
                visible_agents=visible_agents,
                reply_count=reply_count,
                reaction_count=reaction_count,
                recommendation_count=recommendation_count,
                alignment_score=round(alignment_score, 4),
                silent_recommendation_count=silent_recommendation_count,
            )
        )

        total_visible += visible_agents
        total_replies += reply_count
        total_reactions += reaction_count
        total_recommendations += recommendation_count
        silent_recommendations += silent_recommendation_count
        weighted_alignment += alignment_score * archetype.share

    view_activation_score = clamp01(total_visible / max(scenario.population.size * 0.82, 1))
    early_velocity_score = clamp01(
        ((total_replies * 1.2) + (total_reactions * 0.85) + (total_recommendations * 1.55))
        / max(scenario.population.size * 0.28, 1)
    )
    controversy_score = clamp01(
        (features.controversy_level * 0.50)
        + (features.outrage_level * 0.18)
        + (features.irony_level * 0.07)
        + ((total_replies / max(total_visible, 1)) * 0.25)
    )
    lurker_conversion_score = clamp01(silent_recommendations / max(scenario.population.size * 0.12, 1))
    sustained_attention_score = clamp01(
        (features.information_density * 0.16)
        + (features.practical_utility * 0.16)
        + (features.technical_depth * 0.18)
        + (features.empathy_signal * 0.13)
        + (features.insider_credibility_signal * 0.12)
        + (features.gallery_native_tone_fit * 0.08)
        + (features.timing_relevance * 0.10)
        + (weighted_alignment * 0.07)
        - (features.meme_fitness * 0.06)
    )
    mid_run_decay_score = clamp01(
        0.58
        - (sustained_attention_score * 0.36)
        + (features.meme_fitness * 0.18)
        + (features.controversy_level * 0.11)
        + ((1.0 - features.information_density) * 0.07)
    )
    peak_visibility_score = clamp01(
        (view_activation_score * 0.52)
        + ((total_recommendations / max(scenario.population.size * 0.18, 1)) * 0.20)
        + ((total_replies / max(scenario.population.size * 0.16, 1)) * 0.10)
        + (features.timing_relevance * 0.10)
        + (features.gallery_native_tone_fit * 0.08)
    )

    threshold = scenario.gallery.concept_threshold
    recommendation_ratio = clamp01(total_recommendations / max(threshold.recommendation_count * 1.6, 1))
    concept_likelihood_score = clamp01(
        (recommendation_ratio * 0.42)
        + (early_velocity_score * 0.20)
        + (lurker_conversion_score * 0.15)
        + (sustained_attention_score * 0.13)
        + (peak_visibility_score * 0.10)
    )
    concept_threshold_reached = (
        total_recommendations >= threshold.recommendation_count
        and early_velocity_score >= threshold.minimum_velocity_score
        and lurker_conversion_score >= threshold.minimum_lurker_conversion_score
    )

    visibility_curve = _build_visibility_curve(
        scenario=scenario,
        early_velocity_score=early_velocity_score,
        sustained_attention_score=sustained_attention_score,
        controversy_score=controversy_score,
        recommendation_count_estimate=total_recommendations,
        mid_run_decay_score=mid_run_decay_score,
        peak_visibility_score=peak_visibility_score,
    )

    contributions.sort(
        key=lambda item: (item.recommendation_count, item.reply_count, item.alignment_score),
        reverse=True,
    )

    return GalleryCandidatePostResult(
        post_id=candidate_post.id,
        label=candidate_post.label,
        ranking_position=0,
        view_activation_score=round(view_activation_score, 4),
        reply_count_estimate=total_replies,
        reaction_count_estimate=total_reactions,
        recommendation_count_estimate=total_recommendations,
        early_velocity_score=round(early_velocity_score, 4),
        mid_run_decay_score=round(mid_run_decay_score, 4),
        controversy_score=round(controversy_score, 4),
        lurker_conversion_score=round(lurker_conversion_score, 4),
        concept_threshold_reached=concept_threshold_reached,
        concept_likelihood_score=round(concept_likelihood_score, 4),
        peak_visibility_score=round(peak_visibility_score, 4),
        sustained_attention_score=round(sustained_attention_score, 4),
        archetype_contributions=contributions,
        visibility_curve=visibility_curve,
    )


def simulate_gallery_scenario(scenario: GalleryScenario) -> GalleryRunArtifact:
    posts = [_post_result(scenario, candidate_post) for candidate_post in scenario.candidate_posts]
    posts.sort(
        key=lambda item: (
            item.concept_threshold_reached,
            item.concept_likelihood_score,
            item.recommendation_count_estimate,
            item.early_velocity_score,
        ),
        reverse=True,
    )
    for index, post in enumerate(posts, start=1):
        post.ranking_position = index
    return GalleryRunArtifact(
        run_id=str(uuid4()),
        scenario_id=scenario.scenario_id,
        gallery_id=scenario.gallery.id,
        gallery_label=scenario.gallery.label,
        population_size=scenario.population.size,
        rounds=scenario.simulation.rounds,
        concept_threshold=scenario.gallery.concept_threshold,
        posts=posts,
    )


def _post_index(artifact: GalleryRunArtifact) -> dict[str, GalleryCandidatePostResult]:
    return {post.post_id: post for post in artifact.posts}


def _ranking_check(assertion: GalleryAssertion, artifact: GalleryRunArtifact) -> GalleryValidationCheck:
    posts = _post_index(artifact)
    target = posts[assertion.target or ""]
    higher_than = posts[assertion.higher_than or ""]
    metric = assertion.metric or ""
    target_value = getattr(target, metric)
    other_value = getattr(higher_than, metric)
    passed = target_value > other_value
    return GalleryValidationCheck(
        check_id=assertion.id,
        passed=passed,
        message=assertion.description,
        metric=metric,
        target=assertion.target or "",
        actual=target_value,
        expected=f"> {other_value}",
    )


def _compare_values(left: float | int | bool | str, comparison: str, right: float | int | bool | str) -> bool:
    if comparison == "gte":
        return left >= right
    if comparison == "gt":
        return left > right
    if comparison == "lte":
        return left <= right
    if comparison == "lt":
        return left < right
    if comparison == "eq":
        return left == right
    raise ValueError(f"unsupported comparison: {comparison}")


def _condition_check(
    *,
    condition: GalleryAssertionCondition,
    artifact: GalleryRunArtifact,
    assertion_id: str,
    description: str,
) -> GalleryValidationCheck:
    posts = _post_index(artifact)
    target = posts[condition.target]
    metric_value = getattr(target, condition.metric)
    expected: float | int | bool | str
    passed: bool
    if condition.comparison in {"lt_target", "gt_target"}:
        if condition.other_target is None:
            raise ValueError("other_target is required for target-to-target comparisons")
        other_value = getattr(posts[condition.other_target], condition.metric)
        passed = metric_value < other_value if condition.comparison == "lt_target" else metric_value > other_value
        expected = f"{condition.comparison} {condition.other_target}:{other_value}"
    else:
        if condition.value is None:
            raise ValueError("value is required for literal comparisons")
        passed = _compare_values(metric_value, condition.comparison, condition.value)
        expected = condition.value

    return GalleryValidationCheck(
        check_id=assertion_id,
        passed=passed,
        message=description,
        metric=condition.metric,
        target=condition.target,
        actual=metric_value,
        expected=expected,
    )


def validate_gallery_assertions(
    *,
    artifact: GalleryRunArtifact,
    assertions: GalleryAssertionsArtifact,
) -> GalleryValidationArtifact:
    checks: list[GalleryValidationCheck] = []
    for assertion in assertions.assertions:
        if assertion.kind == "ranking":
            checks.append(_ranking_check(assertion, artifact))
            continue
        for index, condition in enumerate(assertion.checks, start=1):
            checks.append(
                _condition_check(
                    condition=condition,
                    artifact=artifact,
                    assertion_id=f"{assertion.id}.{index}",
                    description=assertion.description,
                )
            )
    return GalleryValidationArtifact(
        run_id=artifact.run_id,
        scenario_id=artifact.scenario_id,
        passed=all(check.passed for check in checks),
        checks=checks,
    )
