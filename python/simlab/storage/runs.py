"""Run metadata operations."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import sqlite3


def create_run(
    connection: sqlite3.Connection,
    *,
    run_id: str,
    scenario_id: str,
    status: str,
    artifact_dir: Path,
    run_mode: str,
    kernel_backend: str,
) -> None:
    connection.execute(
        """
        INSERT INTO runs (run_id, scenario_id, status, artifact_dir, run_mode, kernel_backend, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            scenario_id,
            status,
            str(artifact_dir),
            run_mode,
            kernel_backend,
            datetime.now(UTC).isoformat(),
        ),
    )
    connection.commit()


def list_runs(connection: sqlite3.Connection) -> list[dict[str, str]]:
    rows = connection.execute(
        "SELECT run_id, scenario_id, status, artifact_dir, run_mode, kernel_backend, created_at FROM runs ORDER BY created_at DESC"
    ).fetchall()
    return [dict(row) for row in rows]


def get_run(connection: sqlite3.Connection, run_id: str) -> dict[str, str] | None:
    row = connection.execute(
        """
        SELECT run_id, scenario_id, status, artifact_dir, run_mode, kernel_backend, created_at
        FROM runs
        WHERE run_id = ?
        """,
        (run_id,),
    ).fetchone()
    if row is None:
        return None
    return dict(row)
