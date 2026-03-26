"""Report generation helpers for gallery simulation runs."""

from __future__ import annotations

from gan_simlab.gallery.schema import GalleryRunArtifact, GalleryValidationArtifact


def build_gallery_markdown_report(
    artifact: GalleryRunArtifact,
    validation: GalleryValidationArtifact | None = None,
) -> str:
    lines = [
        f"# Gallery Simulation Report: {artifact.gallery_label}",
        "",
        f"- Run ID: `{artifact.run_id}`",
        f"- Scenario: `{artifact.scenario_id}`",
        f"- Population size: `{artifact.population_size}`",
        f"- Rounds: `{artifact.rounds}`",
        f"- Concept threshold: recommendations `>= {artifact.concept_threshold.recommendation_count}`, velocity `>= {artifact.concept_threshold.minimum_velocity_score}`, lurker conversion `>= {artifact.concept_threshold.minimum_lurker_conversion_score}`",
        "",
        "## Top Ranked Posts",
        "",
    ]

    for post in artifact.posts[:10]:
        top_archetypes = ", ".join(
            f"`{contribution.archetype_id}` ({contribution.recommendation_count})"
            for contribution in post.archetype_contributions[:3]
        )
        lines.extend(
            [
                f"### {post.ranking_position}. {post.label}",
                "",
                f"- Post ID: `{post.post_id}`",
                f"- Concept reached: `{post.concept_threshold_reached}`",
                f"- Concept likelihood: `{post.concept_likelihood_score}`",
                f"- Recommendation estimate: `{post.recommendation_count_estimate}`",
                f"- Reply estimate: `{post.reply_count_estimate}`",
                f"- Reaction estimate: `{post.reaction_count_estimate}`",
                f"- Early velocity: `{post.early_velocity_score}`",
                f"- Sustained attention: `{post.sustained_attention_score}`",
                f"- Lurker conversion: `{post.lurker_conversion_score}`",
                f"- Controversy: `{post.controversy_score}`",
                f"- Top supporting archetypes: {top_archetypes or 'n/a'}",
                f"- Visibility curve: `{post.visibility_curve}`",
                "",
            ]
        )

    if validation is not None:
        lines.extend(
            [
                "## Assertion Checks",
                "",
                f"- Overall pass: `{validation.passed}`",
                "",
            ]
        )
        for check in validation.checks:
            marker = "PASS" if check.passed else "FAIL"
            lines.append(
                f"- [{marker}] `{check.check_id}` {check.message} :: `{check.target}` `{check.metric}` actual=`{check.actual}` expected=`{check.expected}`"
            )
        lines.append("")

    lines.extend(
        [
            "## Summary",
            "",
            f"The current leader is **{artifact.posts[0].label}** with concept likelihood `{artifact.posts[0].concept_likelihood_score}` and recommendation estimate `{artifact.posts[0].recommendation_count_estimate}`.",
            f"The lowest-ranked post is **{artifact.posts[-1].label}** with concept likelihood `{artifact.posts[-1].concept_likelihood_score}`.",
            "",
        ]
    )
    return "\n".join(lines)
