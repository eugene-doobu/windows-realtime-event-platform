"""Minimal run bootstrap for synthetic scenarios."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from simlab.analysis import build_interaction_analysis_artifacts
from simlab.config import GroundingSettings, load_grounding_settings
from simlab.expression import render_conversation
from simlab.grounding import GroundingError, ground_scenario
from simlab.interaction import build_interaction_validation, generate_interactions
from simlab.persona import build_persona_snapshot
from simlab.persona.validation import build_persona_validation
from simlab.runner.artifacts import ensure_directory, write_json, write_jsonl
from simlab.runner.execution import (
    ArtifactVerbosity,
    RunMode,
    apply_run_mode,
    artifact_verbosity_for_run_mode,
)
from simlab.runner.kernel_client import kernel_backend_name, run_kernel
from simlab.runner.prepared_cache import load_or_prepare_prepared_input
from simlab.runner.reporting import build_markdown_report, build_summary_artifact, write_report
from simlab.schemas.artifacts import (
    ConversationEntry,
    GroupMetric,
    GroundingStatusArtifact,
    InteractionSummaryArtifact,
    MetricsArtifact,
    RoundMetric,
    RuntimeProfileArtifact,
    RunConfigArtifact,
    TimelineEvent,
    ValidationArtifact,
)
from simlab.schemas.scenario import Scenario
from simlab.validation.checks import validate_run
from simlab.visualization.group_graph import write_group_influence_graph
from simlab.visualization.thread_graph import write_representative_thread_graph


class RunBootstrapError(RuntimeError):
    def __init__(self, *, run_id: str, run_dir: Path, stage: str, message: str) -> None:
        super().__init__(message)
        self.run_id = run_id
        self.run_dir = run_dir
        self.stage = stage


def bootstrap_run(
    scenario_path: Path,
    output_dir: Path,
    *,
    run_mode: RunMode = RunMode.STANDARD,
    cache_dir: Path = Path("artifacts") / "cache" / "prepared",
    grounding_settings: GroundingSettings | None = None,
    run_id: str | None = None,
) -> str:
    total_started_at = perf_counter()
    scenario = Scenario.model_validate(json.loads(scenario_path.read_text(encoding="utf-8")))
    resolved_scenario = apply_run_mode(scenario, run_mode)
    run_id = run_id or str(uuid4())
    run_dir = ensure_directory(output_dir / run_id)
    grounding_status = GroundingStatusArtifact(
        run_id=run_id,
        scenario_id=resolved_scenario.scenario_id,
        status="disabled",
        message="grounding is disabled for this scenario",
    )
    grounding_started_at = perf_counter()
    try:
        grounding_artifact = ground_scenario(
            run_id=run_id,
            scenario_path=scenario_path,
            scenario=resolved_scenario,
            settings=(grounding_settings or load_grounding_settings()),
        )
    except GroundingError as exc:
        grounding_status = GroundingStatusArtifact(
            run_id=run_id,
            scenario_id=resolved_scenario.scenario_id,
            status="failed",
            error_code=exc.code,
            message=str(exc),
        )
        write_json(run_dir / "grounding_status.json", grounding_status.model_dump())
        raise RunBootstrapError(
            run_id=run_id,
            run_dir=run_dir,
            stage="grounding",
            message=str(exc),
        ) from exc
    grounding_time_ms = (perf_counter() - grounding_started_at) * 1000.0
    if grounding_artifact is not None:
        grounding_status = GroundingStatusArtifact(
            run_id=run_id,
            scenario_id=resolved_scenario.scenario_id,
            status="succeeded",
            source_count=grounding_artifact.source_count,
            query_count=grounding_artifact.query_count,
            message="grounding completed successfully",
        )
    prepare_started_at = perf_counter()
    prepared_result = load_or_prepare_prepared_input(
        scenario=resolved_scenario,
        run_mode=run_mode,
        cache_dir=cache_dir,
    )
    prepared = prepared_result.prepared
    prepare_time_ms = (perf_counter() - prepare_started_at) * 1000.0
    persona_snapshot = build_persona_snapshot(
        run_id=run_id,
        scenario_id=resolved_scenario.scenario_id,
        persona=prepared.persona,
        group_labels=prepared.group_labels,
    )
    persona_validation = build_persona_validation(
        run_id=run_id,
        scenario=resolved_scenario,
        persona=prepared.persona,
        group_labels=prepared.group_labels,
    )
    kernel_started_at = perf_counter()
    kernel_result = run_kernel(
        initial_state=prepared.initial_state,
        graph=prepared.graph,
        config=prepared.config,
    )
    kernel_time_ms = (perf_counter() - kernel_started_at) * 1000.0
    interaction_started_at = perf_counter()
    interaction_artifacts = generate_interactions(
        run_id=run_id,
        scenario=resolved_scenario,
        run_mode=run_mode,
        final_state=kernel_result["final_state"],
        round_metrics=kernel_result["round_metrics"],
        persona=prepared.persona,
        group_labels=prepared.group_labels,
    )
    conversation = render_conversation(
        messages=interaction_artifacts.messages,
        reactions=interaction_artifacts.reactions,
        persona=prepared.persona,
    )
    interaction_validation = build_interaction_validation(
        run_id=run_id,
        scenario=resolved_scenario,
        interaction_summary=interaction_artifacts.summary,
        persona_snapshot=persona_snapshot,
        messages=interaction_artifacts.messages,
        reactions=interaction_artifacts.reactions,
        conversation=conversation,
    )
    analysis_artifacts = build_interaction_analysis_artifacts(
        run_id=run_id,
        scenario_id=resolved_scenario.scenario_id,
        interaction_summary=interaction_artifacts.summary,
        threads=interaction_artifacts.threads,
        messages=interaction_artifacts.messages,
        reactions=interaction_artifacts.reactions,
    )
    interaction_time_ms = (perf_counter() - interaction_started_at) * 1000.0

    run_config = RunConfigArtifact(
        run_id=run_id,
        scenario_id=resolved_scenario.scenario_id,
        run_mode=run_mode.value,
        artifact_verbosity=artifact_verbosity_for_run_mode(run_mode).value,
        kernel_backend=kernel_backend_name(),
        prepared_input_source=prepared_result.source,
        prepared_input_cache_key=prepared_result.cache_key,
        population_size=resolved_scenario.population.size,
        rounds=resolved_scenario.simulation.rounds,
        random_seed=resolved_scenario.simulation.random_seed,
        channel_ids=[channel.id for channel in resolved_scenario.simulation.channels],
        narrative_tokens=resolved_scenario.simulation.narrative_tokens,
    )

    round_metrics = [
        RoundMetric(**metric)
        for metric in kernel_result["round_metrics"]
    ]
    group_metrics = _build_group_metrics(
        final_state=kernel_result["final_state"],
        group_labels=prepared.group_labels,
        final_round_index=(round_metrics[-1].round_index if round_metrics else 0),
    )
    metrics = MetricsArtifact(run_id=run_id, round_metrics=round_metrics, group_metrics=group_metrics)
    validation = validate_run(
        run_id=run_id,
        scenario=resolved_scenario,
        run_mode=run_mode,
        metrics=metrics,
        final_state=kernel_result["final_state"],
        expected_assertions_path=_resolve_expected_assertions_path(scenario_path),
    )
    summary = build_summary_artifact(
        run_config=run_config,
        metrics=metrics,
        validation=validation,
        grounding=grounding_artifact,
        execution_time_ms=(perf_counter() - total_started_at) * 1000.0,
        prepare_time_ms=prepare_time_ms,
        kernel_time_ms=kernel_time_ms,
        interaction_time_ms=interaction_time_ms,
        grounding_time_ms=grounding_time_ms,
        state_generation_time_ms=prepared.profile.state_generation_time_ms,
        graph_generation_time_ms=prepared.profile.graph_generation_time_ms,
        config_generation_time_ms=prepared.profile.config_generation_time_ms,
        edge_count=len(prepared.graph["targets"]),
        estimated_state_bytes=prepared.profile.estimated_state_bytes,
        estimated_graph_bytes=prepared.profile.estimated_graph_bytes,
        estimated_persona_bytes=prepared.profile.estimated_persona_bytes,
        estimated_total_prepared_bytes=prepared.profile.estimated_total_bytes,
    )
    runtime_profile = RuntimeProfileArtifact(
        run_id=run_id,
        scenario_id=resolved_scenario.scenario_id,
        run_mode=run_mode.value,
        prepared_input_source=prepared_result.source,
        population_size=prepared.profile.population_size,
        edge_count=prepared.profile.edge_count,
        execution_time_ms=summary.execution_time_ms,
        grounding_time_ms=summary.grounding_time_ms,
        prepare_time_ms=summary.prepare_time_ms,
        state_generation_time_ms=prepared.profile.state_generation_time_ms,
        graph_generation_time_ms=prepared.profile.graph_generation_time_ms,
        config_generation_time_ms=prepared.profile.config_generation_time_ms,
        kernel_time_ms=summary.kernel_time_ms,
        interaction_time_ms=summary.interaction_time_ms,
        estimated_state_bytes=prepared.profile.estimated_state_bytes,
        estimated_graph_bytes=prepared.profile.estimated_graph_bytes,
        estimated_persona_bytes=prepared.profile.estimated_persona_bytes,
        estimated_total_prepared_bytes=prepared.profile.estimated_total_bytes,
    )
    report = build_markdown_report(
        run_config=run_config,
        metrics=metrics,
        validation=validation,
        summary=summary,
        grounding=grounding_artifact,
        persona_snapshot=persona_snapshot,
        persona_validation=persona_validation,
        interaction_summary=interaction_artifacts.summary,
        interaction_validation=interaction_validation,
        group_action_summary=analysis_artifacts.group_action_summary,
        group_round_summary=analysis_artifacts.group_round_summary,
        narrative_dominance=analysis_artifacts.narrative_dominance,
        representative_thread=analysis_artifacts.representative_thread,
        conversation=conversation,
    )
    timeline = _build_timeline(resolved_scenario)

    write_json(run_dir / "run_config.json", run_config.model_dump())
    write_json(run_dir / "metrics.json", metrics.model_dump())
    write_json(run_dir / "validation.json", validation.model_dump())
    write_json(run_dir / "summary.json", summary.model_dump())
    write_json(run_dir / "runtime_profile.json", runtime_profile.model_dump())
    write_json(run_dir / "grounding_status.json", grounding_status.model_dump())
    write_json(run_dir / "persona_snapshot.json", persona_snapshot.model_dump())
    write_json(run_dir / "persona_validation.json", persona_validation.model_dump())
    write_json(run_dir / "interaction_summary.json", interaction_artifacts.summary.model_dump())
    write_json(run_dir / "interaction_validation.json", interaction_validation.model_dump())
    write_json(run_dir / "group_action_summary.json", analysis_artifacts.group_action_summary.model_dump())
    write_json(run_dir / "group_round_summary.json", analysis_artifacts.group_round_summary.model_dump())
    write_json(run_dir / "narrative_dominance.json", analysis_artifacts.narrative_dominance.model_dump())
    write_json(run_dir / "representative_thread.json", analysis_artifacts.representative_thread.model_dump())
    write_jsonl(run_dir / "threads.jsonl", _build_thread_rows(interaction_artifacts))
    write_jsonl(run_dir / "conversation.jsonl", [entry.model_dump() for entry in conversation])
    if grounding_artifact is not None:
        write_json(run_dir / "grounding.json", grounding_artifact.model_dump())
    _write_optional_artifacts(
        run_dir=run_dir,
        artifact_verbosity=artifact_verbosity_for_run_mode(run_mode),
        timeline=timeline,
        prepared=prepared,
        report=report,
        analysis_artifacts=analysis_artifacts,
        interaction_artifacts=interaction_artifacts,
    )

    return run_id


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap a synthetic simulation run.")
    parser.add_argument("scenario", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts") / "runs")
    parser.add_argument(
        "--run-mode",
        choices=[mode.value for mode in RunMode],
        default=RunMode.STANDARD.value,
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path("artifacts") / "cache" / "prepared",
    )
    args = parser.parse_args()

    try:
        run_id = bootstrap_run(
            args.scenario,
            args.output_dir,
            run_mode=RunMode(args.run_mode),
            cache_dir=args.cache_dir,
        )
        print(run_id)
        return 0
    except RunBootstrapError as exc:
        print(f"{exc.stage} failed for run {exc.run_id}: {exc}")
        return 1


def _write_optional_artifacts(
    *,
    run_dir: Path,
    artifact_verbosity: ArtifactVerbosity,
    timeline: list[TimelineEvent],
    prepared,
    report: str,
    analysis_artifacts,
    interaction_artifacts,
) -> None:
    if artifact_verbosity is ArtifactVerbosity.MINIMAL:
        return
    write_jsonl(run_dir / "timeline.jsonl", [event.model_dump() for event in timeline])
    write_report(run_dir / "report.md", report)
    write_group_influence_graph(
        prepared=prepared,
        path=run_dir / "group_influence.dot",
    )
    write_representative_thread_graph(
        representative_thread=analysis_artifacts.representative_thread,
        messages=interaction_artifacts.messages,
        reactions=interaction_artifacts.reactions,
        path=run_dir / "representative_thread.dot",
    )


def _build_thread_rows(interaction_artifacts) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for thread in interaction_artifacts.threads:
        rows.append({"record_type": "thread", **thread.model_dump()})
    for message in interaction_artifacts.messages:
        rows.append({"record_type": "message", **message.model_dump()})
    for reaction in interaction_artifacts.reactions:
        rows.append({"record_type": "reaction", **reaction.model_dump()})
    return rows

def _build_group_metrics(
    *,
    final_state: dict[str, list[float] | list[int]],
    group_labels: dict[int, str],
    final_round_index: int,
) -> list[GroupMetric]:
    grouped: dict[int, dict[str, list[float] | int]] = {}

    for index, current_group_id in enumerate(final_state["group_id"]):
        bucket = grouped.setdefault(
            int(current_group_id),
            {"stance": [], "trust": [], "salience": [], "population": 0, "post_count": 0},
        )
        bucket["stance"].append(float(final_state["stance"][index]))
        bucket["trust"].append(float(final_state["trust"][index]))
        bucket["salience"].append(float(final_state["salience"][index]))
        bucket["population"] = int(bucket["population"]) + 1
        emission = float(final_state["activity"][index]) * (0.5 + (float(final_state["salience"][index]) * 0.5))
        if emission > 0.55:
            bucket["post_count"] = int(bucket["post_count"]) + 1

    metrics: list[GroupMetric] = []
    for current_group_id, bucket in grouped.items():
        metrics.append(
            GroupMetric(
                round_index=final_round_index,
                group_id=group_labels[current_group_id],
                population=int(bucket["population"]),
                mean_stance=sum(bucket["stance"]) / len(bucket["stance"]),
                mean_trust=sum(bucket["trust"]) / len(bucket["trust"]),
                mean_salience=sum(bucket["salience"]) / len(bucket["salience"]),
                post_count=int(bucket["post_count"]),
            )
        )

    return sorted(metrics, key=lambda metric: metric.group_id)


def _build_timeline(scenario: Scenario) -> list[TimelineEvent]:
    timeline: list[TimelineEvent] = []
    for intervention in scenario.simulation.interventions:
        timeline.append(
            TimelineEvent(
                round_index=intervention.round_index,
                event_type="intervention_applied",
                subject_id=intervention.kind.value,
                details={
                    "target_group_count": len(intervention.target_groups),
                    "target_channel_count": len(intervention.target_channels),
                },
            )
        )
    return timeline


def _resolve_expected_assertions_path(scenario_path: Path) -> Path:
    scenario_specific = scenario_path.with_name(f"{scenario_path.stem}.expected_assertions.json")
    if scenario_specific.exists():
        return scenario_specific
    return scenario_path.with_name("expected_assertions.json")


if __name__ == "__main__":
    raise SystemExit(main())
