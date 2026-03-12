import json
from pathlib import Path

from fastapi.testclient import TestClient

from simlab.api.main import create_app
from simlab.schemas.artifacts import GroundingArtifact, GroundingEvidence


def test_api_run_lifecycle(tmp_path: Path, monkeypatch) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    monkeypatch.setenv("SIMLAB_REPO_ROOT", str(repo_root))
    monkeypatch.setenv("SIMLAB_ARTIFACTS_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setenv("SIMLAB_RUNS_DIR", str(tmp_path / "artifacts" / "api-runs"))
    monkeypatch.setenv("SIMLAB_CACHE_DIR", str(tmp_path / "artifacts" / "cache" / "prepared"))
    monkeypatch.setenv("SIMLAB_DB_PATH", str(tmp_path / "artifacts" / "simlab.db"))
    monkeypatch.setenv("SIMLAB_RUN_LAUNCH_MODE", "inline")

    with TestClient(create_app()) as client:
        create_response = client.post(
            "/runs",
            json={
                "scenario_path": "fixtures/synthetic_public_issue/scenario.json",
                "run_mode": "smoke",
            },
        )
        assert create_response.status_code == 200
        payload = create_response.json()
        run_id = payload["run_id"]
        assert payload["status"] == "pending"

        list_response = client.get("/runs")
        assert list_response.status_code == 200
        runs = list_response.json()
        assert any(run["run_id"] == run_id for run in runs)

        status_response = client.get(f"/runs/{run_id}")
        assert status_response.status_code == 200
        status_payload = status_response.json()
        assert status_payload["status"] == "completed"
        assert status_payload["summary"]["validation_passed"] is True

        artifact_response = client.get(f"/runs/{run_id}/artifacts")
        assert artifact_response.status_code == 200
        artifact_payload = artifact_response.json()
        assert artifact_payload["run_config"]["run_mode"] == "smoke"
        assert artifact_payload["summary"]["validation_passed"] is True
        assert artifact_payload["runtime_profile"]["estimated_total_prepared_bytes"] > 0
        assert artifact_payload["grounding_status"]["status"] == "disabled"
        assert artifact_payload["persona_snapshot"]["population_size"] == 100
        assert artifact_payload["persona_validation"]["passed"] is True
        assert artifact_payload["interaction_summary"]["thread_count"] > 0
        assert artifact_payload["interaction_validation"]["passed"] is True
        assert len(artifact_payload["group_action_summary"]["groups"]) > 0
        assert len(artifact_payload["group_round_summary"]["rounds"]) > 0
        assert len(artifact_payload["narrative_dominance"]["rounds"]) > 0
        assert artifact_payload["representative_thread"]["thread_id"] is not None
        assert "summary.json" in artifact_payload["available_files"]
        assert "grounding_status.json" in artifact_payload["available_files"]
        assert "persona_snapshot.json" in artifact_payload["available_files"]
        assert "persona_validation.json" in artifact_payload["available_files"]
        assert "interaction_summary.json" in artifact_payload["available_files"]
        assert "interaction_validation.json" in artifact_payload["available_files"]
        assert "group_action_summary.json" in artifact_payload["available_files"]
        assert "group_round_summary.json" in artifact_payload["available_files"]
        assert "narrative_dominance.json" in artifact_payload["available_files"]
        assert "representative_thread.json" in artifact_payload["available_files"]
        assert "threads.jsonl" in artifact_payload["available_files"]
        assert "conversation.jsonl" in artifact_payload["available_files"]
        assert "timeline.jsonl" not in artifact_payload["available_files"]


def test_api_artifacts_include_grounding_when_present(tmp_path: Path, monkeypatch) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    monkeypatch.setenv("SIMLAB_REPO_ROOT", str(repo_root))
    monkeypatch.setenv("SIMLAB_ARTIFACTS_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setenv("SIMLAB_RUNS_DIR", str(tmp_path / "artifacts" / "api-runs"))
    monkeypatch.setenv("SIMLAB_CACHE_DIR", str(tmp_path / "artifacts" / "cache" / "prepared"))
    monkeypatch.setenv("SIMLAB_DB_PATH", str(tmp_path / "artifacts" / "simlab.db"))
    monkeypatch.setenv("SIMLAB_RUN_LAUNCH_MODE", "inline")
    monkeypatch.setattr(
        "simlab.runner.launch.ground_scenario",
        lambda **_: GroundingArtifact(
            run_id="ignored",
            scenario_id="synthetic-public-issue-grounded",
            source_count=1,
            query_count=2,
            evidence=[
                GroundingEvidence(
                    query_label="scenario:synthetic-public-issue-grounded",
                    source_path="grounding/briefing.md",
                    chunk_id="chunk-1",
                    score=0.88,
                    snippet="Clarification messages should emphasize fairness.",
                )
            ],
        ),
    )

    with TestClient(create_app()) as client:
        create_response = client.post(
            "/runs",
            json={
                "scenario_path": "fixtures/synthetic_public_issue/scenario_grounded.json",
                "run_mode": "smoke",
            },
        )
        assert create_response.status_code == 200
        run_id = create_response.json()["run_id"]

        artifact_response = client.get(f"/runs/{run_id}/artifacts")
        assert artifact_response.status_code == 200
        artifact_payload = artifact_response.json()
        assert artifact_payload["grounding"]["source_count"] == 1
        assert artifact_payload["grounding_status"]["status"] == "succeeded"
        assert artifact_payload["persona_snapshot"]["population_size"] == 100
        assert artifact_payload["persona_validation"]["passed"] is True
        assert artifact_payload["interaction_summary"]["thread_count"] > 0
        assert artifact_payload["interaction_validation"]["passed"] is True
        assert len(artifact_payload["group_action_summary"]["groups"]) > 0
        assert artifact_payload["representative_thread"]["thread_id"] is not None
        assert "grounding.json" in artifact_payload["available_files"]


def test_api_returns_early_grounding_failure_reason(tmp_path: Path, monkeypatch) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    monkeypatch.setenv("SIMLAB_REPO_ROOT", str(repo_root))
    monkeypatch.setenv("SIMLAB_ARTIFACTS_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setenv("SIMLAB_RUNS_DIR", str(tmp_path / "artifacts" / "api-runs"))
    monkeypatch.setenv("SIMLAB_CACHE_DIR", str(tmp_path / "artifacts" / "cache" / "prepared"))
    monkeypatch.setenv("SIMLAB_DB_PATH", str(tmp_path / "artifacts" / "simlab.db"))
    monkeypatch.setenv("SIMLAB_RUN_LAUNCH_MODE", "inline")
    monkeypatch.delenv("SIMLAB_RAG_POSTGRES_DSN", raising=False)

    with TestClient(create_app()) as client:
        create_response = client.post(
            "/runs",
            json={
                "scenario_path": "fixtures/synthetic_public_issue/scenario_grounded.json",
                "run_mode": "smoke",
            },
        )
        assert create_response.status_code == 200
        run_id = create_response.json()["run_id"]

        status_response = client.get(f"/runs/{run_id}")
        assert status_response.status_code == 200
        status_payload = status_response.json()
        assert status_payload["status"] == "failed"
        assert "SIMLAB_RAG_POSTGRES_DSN" in status_payload["error_message"]

        artifact_response = client.get(f"/runs/{run_id}/artifacts")
        assert artifact_response.status_code == 409
