import json
from pathlib import Path

from simlab.schemas.artifacts import GroundingArtifact, GroundingEvidence
from simlab.runner.execution import RunMode
from simlab.runner.launch import RunBootstrapError, bootstrap_run


def test_bootstrap_run_writes_minimum_artifacts(tmp_path: Path) -> None:
    scenario_path = (
        Path(__file__).resolve().parents[2]
        / "fixtures"
        / "synthetic_public_issue"
        / "scenario.json"
    )

    cache_dir = tmp_path / "cache"
    run_id = bootstrap_run(
        scenario_path,
        tmp_path,
        run_mode=RunMode.STANDARD,
        cache_dir=cache_dir,
    )
    run_dir = tmp_path / run_id

    assert (run_dir / "run_config.json").exists()
    assert (run_dir / "metrics.json").exists()
    assert (run_dir / "validation.json").exists()
    assert (run_dir / "timeline.jsonl").exists()
    assert (run_dir / "summary.json").exists()
    assert (run_dir / "runtime_profile.json").exists()
    assert (run_dir / "grounding_status.json").exists()
    assert (run_dir / "persona_snapshot.json").exists()
    assert (run_dir / "persona_validation.json").exists()
    assert (run_dir / "interaction_summary.json").exists()
    assert (run_dir / "interaction_validation.json").exists()
    assert (run_dir / "threads.jsonl").exists()
    assert (run_dir / "conversation.jsonl").exists()
    assert (run_dir / "report.md").exists()
    assert (run_dir / "group_influence.dot").exists()

    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    validation = json.loads((run_dir / "validation.json").read_text(encoding="utf-8"))
    run_config = json.loads((run_dir / "run_config.json").read_text(encoding="utf-8"))
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    runtime_profile = json.loads((run_dir / "runtime_profile.json").read_text(encoding="utf-8"))
    grounding_status = json.loads((run_dir / "grounding_status.json").read_text(encoding="utf-8"))
    persona_snapshot = json.loads((run_dir / "persona_snapshot.json").read_text(encoding="utf-8"))
    persona_validation = json.loads((run_dir / "persona_validation.json").read_text(encoding="utf-8"))
    interaction_summary = json.loads((run_dir / "interaction_summary.json").read_text(encoding="utf-8"))
    interaction_validation = json.loads((run_dir / "interaction_validation.json").read_text(encoding="utf-8"))

    assert len(metrics["round_metrics"]) == 10
    assert validation["passed"] is True
    assert summary["validation_passed"] is True
    assert persona_snapshot["population_size"] == run_config["population_size"]
    assert len(persona_snapshot["sample_agents"]) == 9
    assert persona_validation["passed"] is True
    assert interaction_summary["thread_count"] > 0
    assert interaction_summary["message_count"] > 0
    assert interaction_validation["passed"] is True
    assert len(interaction_summary["round_metrics"]) == 10
    assert run_config["kernel_backend"] in {"native", "python_fallback"}
    assert run_config["run_mode"] == "standard"
    assert run_config["artifact_verbosity"] == "standard"
    assert run_config["prepared_input_source"] == "generated"
    assert (cache_dir / f"{run_config['prepared_input_cache_key']}.json").exists()
    assert summary["grounding_enabled"] is False
    assert summary["grounding_source_count"] == 0
    assert grounding_status["status"] == "disabled"
    assert summary["execution_time_ms"] >= 0.0
    assert summary["prepare_time_ms"] >= 0.0
    assert summary["kernel_time_ms"] >= 0.0
    assert summary["interaction_time_ms"] >= 0.0
    assert summary["edge_count"] > 0
    assert summary["estimated_total_prepared_bytes"] > 0
    assert summary["graph_generation_time_ms"] >= 0.0
    assert runtime_profile["estimated_total_prepared_bytes"] == summary["estimated_total_prepared_bytes"]
    assert runtime_profile["edge_count"] == summary["edge_count"]


def test_bootstrap_run_reuses_prepared_input_cache(tmp_path: Path) -> None:
    scenario_path = (
        Path(__file__).resolve().parents[2]
        / "fixtures"
        / "synthetic_public_issue"
        / "scenario.json"
    )
    cache_dir = tmp_path / "cache"

    first_run_id = bootstrap_run(
        scenario_path,
        tmp_path,
        run_mode=RunMode.SMOKE,
        cache_dir=cache_dir,
    )
    second_run_id = bootstrap_run(
        scenario_path,
        tmp_path,
        run_mode=RunMode.SMOKE,
        cache_dir=cache_dir,
    )

    first_run_config = json.loads((tmp_path / first_run_id / "run_config.json").read_text(encoding="utf-8"))
    second_run_config = json.loads((tmp_path / second_run_id / "run_config.json").read_text(encoding="utf-8"))
    first_validation = json.loads((tmp_path / first_run_id / "validation.json").read_text(encoding="utf-8"))
    second_validation = json.loads((tmp_path / second_run_id / "validation.json").read_text(encoding="utf-8"))

    assert first_run_config["run_mode"] == "smoke"
    assert first_run_config["artifact_verbosity"] == "minimal"
    assert first_run_config["population_size"] == 100
    assert first_run_config["rounds"] == 5
    assert first_validation["passed"] is True
    assert second_validation["passed"] is True
    assert not (tmp_path / first_run_id / "timeline.jsonl").exists()
    assert not (tmp_path / second_run_id / "timeline.jsonl").exists()
    assert (tmp_path / first_run_id / "summary.json").exists()
    assert (tmp_path / first_run_id / "runtime_profile.json").exists()
    assert (tmp_path / first_run_id / "persona_snapshot.json").exists()
    assert (tmp_path / first_run_id / "persona_validation.json").exists()
    assert (tmp_path / first_run_id / "interaction_summary.json").exists()
    assert (tmp_path / first_run_id / "interaction_validation.json").exists()
    assert (tmp_path / first_run_id / "threads.jsonl").exists()
    assert (tmp_path / first_run_id / "conversation.jsonl").exists()
    assert not (tmp_path / first_run_id / "report.md").exists()
    assert not (tmp_path / first_run_id / "group_influence.dot").exists()
    assert second_run_config["prepared_input_source"] == "cache"
    assert first_run_config["prepared_input_cache_key"] == second_run_config["prepared_input_cache_key"]


def test_bootstrap_run_writes_grounding_artifact_when_enabled(tmp_path: Path, monkeypatch) -> None:
    scenario_path = (
        Path(__file__).resolve().parents[2]
        / "fixtures"
        / "synthetic_public_issue"
        / "scenario_grounded.json"
    )

    monkeypatch.setattr(
        "simlab.runner.launch.ground_scenario",
        lambda **_: GroundingArtifact(
            run_id="ignored",
            scenario_id="synthetic-public-issue-grounded",
            source_count=2,
            query_count=3,
            evidence=[
                GroundingEvidence(
                    query_label="archetype:young_workers",
                    source_path="grounding/briefing.md",
                    chunk_id="chunk-a",
                    score=0.91,
                    snippet="Young workers are expected to react strongly.",
                )
            ],
        ),
    )

    run_id = bootstrap_run(
        scenario_path,
        tmp_path,
        run_mode=RunMode.STANDARD,
        cache_dir=tmp_path / "cache",
    )
    run_dir = tmp_path / run_id

    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    grounding = json.loads((run_dir / "grounding.json").read_text(encoding="utf-8"))
    grounding_status = json.loads((run_dir / "grounding_status.json").read_text(encoding="utf-8"))
    validation = json.loads((run_dir / "validation.json").read_text(encoding="utf-8"))
    persona_snapshot = json.loads((run_dir / "persona_snapshot.json").read_text(encoding="utf-8"))
    persona_validation = json.loads((run_dir / "persona_validation.json").read_text(encoding="utf-8"))
    interaction_summary = json.loads((run_dir / "interaction_summary.json").read_text(encoding="utf-8"))
    interaction_validation = json.loads((run_dir / "interaction_validation.json").read_text(encoding="utf-8"))
    report = (run_dir / "report.md").read_text(encoding="utf-8")

    assert summary["grounding_enabled"] is True
    assert summary["grounding_source_count"] == 2
    assert summary["validation_passed"] is True
    assert summary["edge_count"] > 0
    assert grounding_status["status"] == "succeeded"
    assert grounding["query_count"] == 3
    assert validation["passed"] is True
    assert persona_snapshot["group_summaries"][0]["dominant_tone_style"] in {"formal", "frustrated", "measured"}
    assert persona_validation["passed"] is True
    assert interaction_summary["reaction_count"] >= 0
    assert interaction_validation["passed"] is True
    assert "Grounding Evidence" in report
    assert "Persona Snapshot" in report
    assert "Persona Validation" in report
    assert "Interaction Summary" in report
    assert "Interaction Validation" in report
    assert "Representative Conversation" in report


def test_bootstrap_run_writes_grounding_failure_status_when_dsn_missing(tmp_path: Path, monkeypatch) -> None:
    scenario_path = (
        Path(__file__).resolve().parents[2]
        / "fixtures"
        / "synthetic_public_issue"
        / "scenario_grounded.json"
    )
    monkeypatch.delenv("SIMLAB_RAG_POSTGRES_DSN", raising=False)

    try:
        bootstrap_run(
            scenario_path,
            tmp_path,
            run_mode=RunMode.SMOKE,
            cache_dir=tmp_path / "cache",
        )
        raise AssertionError("expected bootstrap_run to fail when grounding dsn is missing")
    except RunBootstrapError as exc:
        status_path = exc.run_dir / "grounding_status.json"
        assert status_path.exists()
        status = json.loads(status_path.read_text(encoding="utf-8"))
        assert status["status"] == "failed"
        assert status["error_code"] == "missing_dsn"
