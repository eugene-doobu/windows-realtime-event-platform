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
    now = datetime.now(UTC).isoformat()
    connection.execute(
        """
        INSERT INTO runs (
            run_id,
            scenario_id,
            status,
            artifact_dir,
            run_mode,
            kernel_backend,
            created_at,
            updated_at,
            error_message
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)
        """,
        (
            run_id,
            scenario_id,
            status,
            str(artifact_dir),
            run_mode,
            kernel_backend,
            now,
            now,
        ),
    )
    connection.commit()


def list_runs(connection: sqlite3.Connection) -> list[dict[str, object]]:
    rows = connection.execute(
        """
        SELECT
            run_id,
            scenario_id,
            status,
            artifact_dir,
            run_mode,
            kernel_backend,
            created_at,
            updated_at,
            error_message
        FROM runs
        ORDER BY created_at DESC
        """
    ).fetchall()
    return [dict(row) for row in rows]


def get_run(connection: sqlite3.Connection, run_id: str) -> dict[str, object] | None:
    row = connection.execute(
        """
        SELECT
            run_id,
            scenario_id,
            status,
            artifact_dir,
            run_mode,
            kernel_backend,
            created_at,
            updated_at,
            error_message
        FROM runs
        WHERE run_id = ?
        """,
        (run_id,),
    ).fetchone()
    if row is None:
        return None
    return dict(row)


def update_run_status(
    connection: sqlite3.Connection,
    *,
    run_id: str,
    status: str,
    kernel_backend: str | None = None,
    error_message: str | None = None,
) -> None:
    updates = [
        "status = ?",
        "updated_at = ?",
        "error_message = ?",
    ]
    parameters: list[object] = [
        status,
        datetime.now(UTC).isoformat(),
        error_message,
    ]
    if kernel_backend is not None:
        updates.append("kernel_backend = ?")
        parameters.append(kernel_backend)
    parameters.append(run_id)
    connection.execute(
        f"""
        UPDATE runs
        SET {", ".join(updates)}
        WHERE run_id = ?
        """,
        parameters,
    )
    connection.commit()
