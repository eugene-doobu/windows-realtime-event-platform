"""Minimal run routes for the first control-plane slice."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from pydantic import ValidationError

from gan_simlab.runner.execution import RunMode
from gan_simlab.runner.subprocess_runner import launch_run_process
from gan_simlab.schemas.scenario import Scenario
from gan_simlab.storage.db import connect
from gan_simlab.storage.runs import create_run as create_run_record
from gan_simlab.storage.runs import get_run, list_runs as list_run_records


class RunCreateResponse(BaseModel):
    run_id: str
    status: str


class RunCreateRequest(BaseModel):
    scenario_path: str
    run_mode: RunMode = RunMode.STANDARD


class RunArtifactsResponse(BaseModel):
    run_id: str
    available_files: list[str]
    run_config: dict[str, object]
    summary: dict[str, object] | None
    runtime_profile: dict[str, object] | None
    validation: dict[str, object]
    grounding: dict[str, object] | None
    grounding_status: dict[str, object] | None
    persona_snapshot: dict[str, object] | None
    persona_validation: dict[str, object] | None
    interaction_summary: dict[str, object] | None
    interaction_validation: dict[str, object] | None
    group_action_summary: dict[str, object] | None
    group_round_summary: dict[str, object] | None
    narrative_dominance: dict[str, object] | None
    representative_thread: dict[str, object] | None


router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("")
def list_runs(request: Request) -> list[dict[str, object]]:
    connection = connect(request.app.state.paths.db_path)
    try:
        return list_run_records(connection)
    finally:
        connection.close()


@router.post("", response_model=RunCreateResponse)
def create_run(request: Request, payload: RunCreateRequest) -> RunCreateResponse:
    scenario_path = _resolve_scenario_path(request, payload.scenario_path)
    if not scenario_path.exists():
        raise HTTPException(status_code=404, detail="scenario file not found")

    try:
        scenario = Scenario.model_validate(json.loads(scenario_path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise HTTPException(status_code=400, detail=f"invalid scenario: {exc}") from exc

    run_id = str(uuid4())
    artifact_dir = request.app.state.paths.runs_dir / run_id

    connection = connect(request.app.state.paths.db_path)
    try:
        create_run_record(
            connection,
            run_id=run_id,
            scenario_id=scenario.scenario_id,
            status="pending",
            artifact_dir=artifact_dir,
            run_mode=payload.run_mode.value,
            kernel_backend="pending",
        )
    finally:
        connection.close()

    launch_run_process(
        run_id=run_id,
        scenario_path=scenario_path,
        output_dir=request.app.state.paths.runs_dir,
        cache_dir=request.app.state.paths.cache_dir,
        db_path=request.app.state.paths.db_path,
        run_mode=payload.run_mode,
        grounding_settings=request.app.state.grounding_settings,
    )

    return RunCreateResponse(run_id=run_id, status="pending")


@router.get("/{run_id}")
def get_run_status(request: Request, run_id: str) -> dict[str, object]:
    connection = connect(request.app.state.paths.db_path)
    try:
        run = get_run(connection, run_id)
    finally:
        connection.close()

    if run is None:
        raise HTTPException(status_code=404, detail="run not found")

    run_dir = Path(run["artifact_dir"])
    response: dict[str, object] = dict(run)
    response["summary"] = _load_json_if_exists(run_dir / "summary.json")
    return response


@router.get("/{run_id}/artifacts", response_model=RunArtifactsResponse)
def get_run_artifacts(request: Request, run_id: str) -> RunArtifactsResponse:
    connection = connect(request.app.state.paths.db_path)
    try:
        run = get_run(connection, run_id)
    finally:
        connection.close()

    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    if run["status"] != "completed":
        raise HTTPException(status_code=409, detail=f"artifacts unavailable while run is {run['status']}")

    run_dir = Path(run["artifact_dir"])
    available_files = sorted(path.name for path in run_dir.iterdir() if path.is_file())

    return RunArtifactsResponse(
        run_id=run_id,
        available_files=available_files,
        run_config=_load_json(run_dir / "run_config.json"),
        summary=_load_json_if_exists(run_dir / "summary.json"),
        runtime_profile=_load_json_if_exists(run_dir / "runtime_profile.json"),
        validation=_load_json(run_dir / "validation.json"),
        grounding=_load_json_if_exists(run_dir / "grounding.json"),
        grounding_status=_load_json_if_exists(run_dir / "grounding_status.json"),
        persona_snapshot=_load_json_if_exists(run_dir / "persona_snapshot.json"),
        persona_validation=_load_json_if_exists(run_dir / "persona_validation.json"),
        interaction_summary=_load_json_if_exists(run_dir / "interaction_summary.json"),
        interaction_validation=_load_json_if_exists(run_dir / "interaction_validation.json"),
        group_action_summary=_load_json_if_exists(run_dir / "group_action_summary.json"),
        group_round_summary=_load_json_if_exists(run_dir / "group_round_summary.json"),
        narrative_dominance=_load_json_if_exists(run_dir / "narrative_dominance.json"),
        representative_thread=_load_json_if_exists(run_dir / "representative_thread.json"),
    )


def _resolve_scenario_path(request: Request, scenario_path: str) -> Path:
    path = Path(scenario_path)
    if path.is_absolute():
        return path
    return request.app.state.paths.repo_root / path


def _load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_json_if_exists(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    return _load_json(path)
