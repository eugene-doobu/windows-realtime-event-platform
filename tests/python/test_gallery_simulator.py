import json
from pathlib import Path

from gan_simlab.gallery import GalleryAssertionsArtifact, GalleryScenario, simulate_gallery_scenario, validate_gallery_assertions


def _scenario_payload() -> dict:
    return {
        "scenario_id": "gallery-test",
        "title": "Gallery test",
        "version": "0.1",
        "gallery": {
            "id": "test_gallery",
            "label": "Test Gallery",
            "platform": "test",
            "culture_tokens": ["cynical", "meme_reactive"],
            "concept_threshold": {
                "recommendation_count": 8,
                "minimum_velocity_score": 0.40,
                "minimum_lurker_conversion_score": 0.10,
            },
            "baseline_mood": {
                "cynicism": 0.70,
                "career_anxiety": 0.50,
                "rumor_heat": 0.60,
                "meme_appetite": 0.45,
                "analysis_tolerance": 0.40,
            },
        },
        "population": {
            "size": 600,
            "archetypes": [
                {
                    "id": "doomer",
                    "label": "Doomer",
                    "share": 0.4,
                    "activity": 0.8,
                    "recommendation_tendency": 0.55,
                    "reply_tendency": 0.8,
                    "reaction_tendency": 0.7,
                    "ignore_tendency": 0.2,
                    "controversy_preference": 0.8,
                    "usefulness_sensitivity": 0.3,
                    "insider_credibility_sensitivity": 0.7,
                    "meme_affinity": 0.5,
                    "career_anxiety": 0.4,
                    "cynicism": 0.9,
                    "gallery_native_tone_preference": 0.8,
                    "silent_conversion_weight": 0.2,
                },
                {
                    "id": "seeker",
                    "label": "Seeker",
                    "share": 0.35,
                    "activity": 0.6,
                    "recommendation_tendency": 0.7,
                    "reply_tendency": 0.45,
                    "reaction_tendency": 0.45,
                    "ignore_tendency": 0.25,
                    "controversy_preference": 0.3,
                    "usefulness_sensitivity": 0.9,
                    "insider_credibility_sensitivity": 0.55,
                    "meme_affinity": 0.2,
                    "career_anxiety": 0.85,
                    "cynicism": 0.55,
                    "gallery_native_tone_preference": 0.45,
                    "silent_conversion_weight": 0.55,
                },
                {
                    "id": "lurker",
                    "label": "Lurker",
                    "share": 0.25,
                    "activity": 0.15,
                    "recommendation_tendency": 0.4,
                    "reply_tendency": 0.05,
                    "reaction_tendency": 0.15,
                    "ignore_tendency": 0.65,
                    "controversy_preference": 0.1,
                    "usefulness_sensitivity": 0.5,
                    "insider_credibility_sensitivity": 0.35,
                    "meme_affinity": 0.3,
                    "career_anxiety": 0.45,
                    "cynicism": 0.4,
                    "gallery_native_tone_preference": 0.35,
                    "silent_conversion_weight": 0.9,
                },
            ],
        },
        "candidate_posts": [
            {
                "id": "practical",
                "label": "Practical info",
                "features": {
                    "title_style": "direct",
                    "body_length": 0.65,
                    "information_density": 0.9,
                    "emotional_charge": 0.2,
                    "irony_level": 0.05,
                    "outrage_level": 0.1,
                    "insider_credibility_signal": 0.35,
                    "practical_utility": 0.95,
                    "technical_depth": 0.55,
                    "empathy_signal": 0.25,
                    "meme_fitness": 0.03,
                    "controversy_level": 0.15,
                    "anti_corporate_charge": 0.15,
                    "gallery_native_tone_fit": 0.30,
                    "timing_relevance": 0.65,
                },
            },
            {
                "id": "rumor",
                "label": "Insider rumor",
                "features": {
                    "title_style": "bait",
                    "body_length": 0.45,
                    "information_density": 0.55,
                    "emotional_charge": 0.7,
                    "irony_level": 0.1,
                    "outrage_level": 0.6,
                    "insider_credibility_signal": 0.9,
                    "practical_utility": 0.3,
                    "technical_depth": 0.2,
                    "empathy_signal": 0.15,
                    "meme_fitness": 0.15,
                    "controversy_level": 0.8,
                    "anti_corporate_charge": 0.65,
                    "gallery_native_tone_fit": 0.75,
                    "timing_relevance": 0.8,
                },
            },
            {
                "id": "meme",
                "label": "Meme dunk",
                "features": {
                    "title_style": "ironic",
                    "body_length": 0.1,
                    "information_density": 0.08,
                    "emotional_charge": 0.5,
                    "irony_level": 0.95,
                    "outrage_level": 0.35,
                    "insider_credibility_signal": 0.05,
                    "practical_utility": 0.01,
                    "technical_depth": 0.01,
                    "empathy_signal": 0.02,
                    "meme_fitness": 0.95,
                    "controversy_level": 0.25,
                    "anti_corporate_charge": 0.35,
                    "gallery_native_tone_fit": 0.85,
                    "timing_relevance": 0.7,
                },
            },
        ],
        "simulation": {
            "rounds": 10,
            "random_seed": 42,
            "max_interactions_per_round": 500,
            "gallery_feed_exposure_weight": 1.0,
            "reply_visibility_multiplier": 0.74,
            "recommendation_visibility_multiplier": 0.92,
            "controversy_boost_multiplier": 0.27,
            "lurker_conversion_multiplier": 0.81,
        },
    }


def test_gallery_simulation_produces_ranked_posts() -> None:
    scenario = GalleryScenario.model_validate(_scenario_payload())
    artifact = simulate_gallery_scenario(scenario)

    assert len(artifact.posts) == 3
    assert artifact.posts[0].ranking_position == 1
    assert artifact.posts[0].concept_likelihood_score >= artifact.posts[-1].concept_likelihood_score
    assert all(len(post.visibility_curve) == scenario.simulation.rounds for post in artifact.posts)

    index = {post.post_id: post for post in artifact.posts}
    assert index["rumor"].early_velocity_score > index["practical"].early_velocity_score
    assert index["practical"].recommendation_count_estimate > index["meme"].recommendation_count_estimate


def test_gallery_assertions_validate_rankings() -> None:
    scenario = GalleryScenario.model_validate(_scenario_payload())
    artifact = simulate_gallery_scenario(scenario)
    assertions = GalleryAssertionsArtifact.model_validate(
        {
            "scenario_id": "gallery-test",
            "version": "0.1",
            "assertions": [
                {
                    "id": "A1",
                    "description": "rumor beats practical on velocity",
                    "kind": "ranking",
                    "metric": "early_velocity_score",
                    "target": "rumor",
                    "higher_than": "practical",
                },
                {
                    "id": "A2",
                    "description": "practical beats meme on recommendations",
                    "kind": "ranking",
                    "metric": "recommendation_count_estimate",
                    "target": "practical",
                    "higher_than": "meme",
                },
            ],
        }
    )

    validation = validate_gallery_assertions(artifact=artifact, assertions=assertions)
    assert validation.passed is True
    assert len(validation.checks) == 2
