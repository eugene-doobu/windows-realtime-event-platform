"""Run summary and human-readable report generation."""

from __future__ import annotations

from pathlib import Path

from simlab.schemas.artifacts import (
    ConversationEntry,
    GroundingArtifact,
    InteractionSummaryArtifact,
    InteractionValidationArtifact,
    MetricsArtifact,
    PersonaSnapshotArtifact,
    PersonaValidationArtifact,
    RunConfigArtifact,
    SummaryArtifact,
    ValidationArtifact,
)


def build_summary_artifact(
    *,
    run_config: RunConfigArtifact,
    metrics: MetricsArtifact,
    validation: ValidationArtifact,
    grounding: GroundingArtifact | None = None,
    execution_time_ms: float = 0.0,
    prepare_time_ms: float = 0.0,
    kernel_time_ms: float = 0.0,
    interaction_time_ms: float = 0.0,
    grounding_time_ms: float = 0.0,
    state_generation_time_ms: float = 0.0,
    graph_generation_time_ms: float = 0.0,
    config_generation_time_ms: float = 0.0,
    edge_count: int = 0,
    estimated_state_bytes: int = 0,
    estimated_graph_bytes: int = 0,
    estimated_persona_bytes: int = 0,
    estimated_total_prepared_bytes: int = 0,
) -> SummaryArtifact:
    final_round = metrics.round_metrics[-1] if metrics.round_metrics else None
    return SummaryArtifact(
        run_id=run_config.run_id,
        scenario_id=run_config.scenario_id,
        run_mode=run_config.run_mode,
        kernel_backend=run_config.kernel_backend,
        validation_passed=validation.passed,
        grounding_enabled=(grounding is not None),
        grounding_source_count=(grounding.source_count if grounding is not None else 0),
        execution_time_ms=execution_time_ms,
        prepare_time_ms=prepare_time_ms,
        kernel_time_ms=kernel_time_ms,
        interaction_time_ms=interaction_time_ms,
        grounding_time_ms=grounding_time_ms,
        state_generation_time_ms=state_generation_time_ms,
        graph_generation_time_ms=graph_generation_time_ms,
        config_generation_time_ms=config_generation_time_ms,
        edge_count=edge_count,
        estimated_state_bytes=estimated_state_bytes,
        estimated_graph_bytes=estimated_graph_bytes,
        estimated_persona_bytes=estimated_persona_bytes,
        estimated_total_prepared_bytes=estimated_total_prepared_bytes,
        final_round_index=(final_round.round_index if final_round is not None else -1),
        final_mean_stance=(final_round.mean_stance if final_round is not None else 0.0),
        final_mean_trust=(final_round.mean_trust if final_round is not None else 0.0),
        final_mean_salience=(final_round.mean_salience if final_round is not None else 0.0),
        groups=metrics.group_metrics,
    )


def build_markdown_report(
    *,
    run_config: RunConfigArtifact,
    metrics: MetricsArtifact,
    validation: ValidationArtifact,
    summary: SummaryArtifact | None = None,
    grounding: GroundingArtifact | None = None,
    persona_snapshot: PersonaSnapshotArtifact | None = None,
    persona_validation: PersonaValidationArtifact | None = None,
    interaction_summary: InteractionSummaryArtifact | None = None,
    interaction_validation: InteractionValidationArtifact | None = None,
    conversation: list[ConversationEntry] | None = None,
) -> str:
    final_round = metrics.round_metrics[-1] if metrics.round_metrics else None
    lines = [
        f"# Run Report: {run_config.run_id}",
        "",
        f"- Scenario: `{run_config.scenario_id}`",
        f"- Run mode: `{run_config.run_mode}`",
        f"- Kernel backend: `{run_config.kernel_backend}`",
        f"- Validation passed: `{validation.passed}`",
        "",
    ]

    if final_round is not None:
        lines.extend(
            [
                "## Final Round",
                "",
                f"- Round index: `{final_round.round_index}`",
                f"- Mean stance: `{final_round.mean_stance:.4f}`",
                f"- Mean trust: `{final_round.mean_trust:.4f}`",
                f"- Mean salience: `{final_round.mean_salience:.4f}`",
                f"- Total posts: `{final_round.total_posts}`",
                "",
            ]
        )

    if summary is not None:
        lines.extend(
            [
                "## Runtime",
                "",
                f"- Edge count: `{summary.edge_count}`",
                f"- Estimated prepared input bytes: `{summary.estimated_total_prepared_bytes}`",
                f"- Total time (ms): `{summary.execution_time_ms:.2f}`",
                f"- Prepare time (ms): `{summary.prepare_time_ms:.2f}`",
                f"- State generation time (ms): `{summary.state_generation_time_ms:.2f}`",
                f"- Graph generation time (ms): `{summary.graph_generation_time_ms:.2f}`",
                f"- Config generation time (ms): `{summary.config_generation_time_ms:.2f}`",
                f"- Kernel time (ms): `{summary.kernel_time_ms:.2f}`",
                f"- Interaction time (ms): `{summary.interaction_time_ms:.2f}`",
                f"- Grounding time (ms): `{summary.grounding_time_ms:.2f}`",
                "",
            ]
        )

    lines.extend(["## Group Snapshot", ""])
    for group in metrics.group_metrics:
        lines.append(
            f"- `{group.group_id}`: stance `{group.mean_stance:.4f}`, trust `{group.mean_trust:.4f}`, posts `{group.post_count}`"
        )

    lines.extend(["", "## Validation Checks", ""])
    for check in validation.checks:
        status = "PASS" if check.passed else "FAIL"
        lines.append(f"- `{status}` {check.check_id}: {check.message}")

    if grounding is not None and grounding.evidence:
        lines.extend(["", "## Grounding Evidence", ""])
        grouped: dict[str, list[tuple[str, float, str]]] = {}
        for item in grounding.evidence:
            grouped.setdefault(item.query_label, []).append(
                (item.source_path, item.score, item.snippet)
            )
        for label in sorted(grouped):
            lines.append(f"### `{label}`")
            lines.append("")
            for source_path, score, snippet in grouped[label]:
                lines.append(f"- `{source_path}` ({score:.4f}): {snippet}")
            lines.append("")

    if persona_snapshot is not None:
        lines.extend(["## Persona Snapshot", ""])
        for group in persona_snapshot.group_summaries:
            lines.append(
                f"- `{group.group_id}`: income `{group.mean_income_pressure:.4f}`, conflict `{group.mean_conflict_tolerance:.4f}`, trust `{group.mean_trust_in_officials_baseline:.4f}`, reply `{group.mean_reply_tendency:.4f}`, tone `{group.dominant_tone_style}`"
            )
        lines.append("")

    if persona_validation is not None:
        lines.extend(["## Persona Validation", ""])
        for check in persona_validation.checks:
            status = "PASS" if check.passed else "FAIL"
            lines.append(f"- `{status}` {check.check_id}: {check.message}")
        for warning in persona_validation.warnings:
            lines.append(f"- `WARN` {warning}")
        lines.append("")

    if interaction_summary is not None:
        lines.extend(
            [
                "## Interaction Summary",
                "",
                f"- Threads: `{interaction_summary.thread_count}`",
                f"- Messages: `{interaction_summary.message_count}`",
                f"- Reactions: `{interaction_summary.reaction_count}`",
                f"- Per-round active agents: `{interaction_summary.per_round_active_agents}`",
                "",
            ]
        )

    if interaction_validation is not None:
        lines.extend(["## Interaction Validation", ""])
        for check in interaction_validation.checks:
            status = "PASS" if check.passed else "FAIL"
            lines.append(f"- `{status}` {check.check_id}: {check.message}")
        for warning in interaction_validation.warnings:
            lines.append(f"- `WARN` {warning}")
        lines.append("")

    if conversation:
        lines.extend(["## Representative Conversation", ""])
        for entry in conversation[:12]:
            lines.append(
                f"- `[r{entry.round_index}] {entry.group_id}/{entry.action_type}` {entry.rendered_text}"
            )
        lines.append("")

    return "\n".join(lines) + "\n"


def write_report(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
