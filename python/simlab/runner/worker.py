"""Run worker that executes a simulation and persists run status."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from simlab.config import GroundingSettings, load_grounding_settings
from simlab.runner.execution import RunMode
from simlab.runner.launch import RunBootstrapError, bootstrap_run
from simlab.storage.db import connect
from simlab.storage.runs import update_run_status


def run_worker(
    *,
    run_id: str,
    scenario_path: Path,
    output_dir: Path,
    cache_dir: Path,
    db_path: Path,
    run_mode: RunMode,
    grounding_settings: GroundingSettings,
) -> None:
    try:
        bootstrap_run(
            scenario_path,
            output_dir,
            run_mode=run_mode,
            cache_dir=cache_dir,
            grounding_settings=grounding_settings,
            run_id=run_id,
        )
        run_config = json.loads((output_dir / run_id / "run_config.json").read_text(encoding="utf-8"))
        _mark_completed(
            db_path=db_path,
            run_id=run_id,
            kernel_backend=str(run_config["kernel_backend"]),
        )
    except RunBootstrapError as exc:
        _mark_failed(
            db_path=db_path,
            run_id=run_id,
            error_message=f"{exc.stage}: {exc}",
        )
        raise
    except Exception as exc:
        _mark_failed(
            db_path=db_path,
            run_id=run_id,
            error_message=str(exc),
        )
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute a queued simulation run.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--scenario", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path, required=True)
    parser.add_argument("--db-path", type=Path, required=True)
    parser.add_argument(
        "--run-mode",
        choices=[mode.value for mode in RunMode],
        default=RunMode.STANDARD.value,
    )
    args = parser.parse_args()

    try:
        run_worker(
            run_id=args.run_id,
            scenario_path=args.scenario,
            output_dir=args.output_dir,
            cache_dir=args.cache_dir,
            db_path=args.db_path,
            run_mode=RunMode(args.run_mode),
            grounding_settings=load_grounding_settings(),
        )
        return 0
    except Exception:
        return 1


def _mark_completed(*, db_path: Path, run_id: str, kernel_backend: str) -> None:
    connection = connect(db_path)
    try:
        update_run_status(
            connection,
            run_id=run_id,
            status="completed",
            kernel_backend=kernel_backend,
            error_message=None,
        )
    finally:
        connection.close()


def _mark_failed(*, db_path: Path, run_id: str, error_message: str) -> None:
    connection = connect(db_path)
    try:
        update_run_status(
            connection,
            run_id=run_id,
            status="failed",
            error_message=error_message,
        )
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
