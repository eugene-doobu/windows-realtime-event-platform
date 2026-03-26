"""Launch run workers in-process for tests or via subprocess in normal operation."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from gan_simlab.config import GroundingSettings
from gan_simlab.runner.execution import RunMode
from gan_simlab.runner.worker import run_worker
from gan_simlab.storage.db import connect
from gan_simlab.storage.runs import update_run_status


def launch_run_process(
    *,
    run_id: str,
    scenario_path: Path,
    output_dir: Path,
    cache_dir: Path,
    db_path: Path,
    run_mode: RunMode,
    grounding_settings: GroundingSettings,
) -> None:
    launch_mode = os.environ.get(
        "GAN_SIMLAB_RUN_LAUNCH_MODE",
        os.environ.get("SIMLAB_RUN_LAUNCH_MODE", "subprocess"),
    )
    if launch_mode == "inline":
        try:
            run_worker(
                run_id=run_id,
                scenario_path=scenario_path,
                output_dir=output_dir,
                cache_dir=cache_dir,
                db_path=db_path,
                run_mode=run_mode,
                grounding_settings=grounding_settings,
            )
        except Exception:
            return
        return

    try:
        subprocess.Popen(
            [
                sys.executable,
                "-m",
                "gan_simlab.runner.worker",
                "--run-id",
                run_id,
                "--scenario",
                str(scenario_path),
                "--output-dir",
                str(output_dir),
                "--cache-dir",
                str(cache_dir),
                "--db-path",
                str(db_path),
                "--run-mode",
                run_mode.value,
            ],
            cwd=str(Path(__file__).resolve().parents[3]),
            env=os.environ.copy(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "DETACHED_PROCESS", 0),
        )
    except Exception as exc:
        connection = connect(db_path)
        try:
            update_run_status(
                connection,
                run_id=run_id,
                status="failed",
                error_message=str(exc),
            )
        finally:
            connection.close()
        raise
