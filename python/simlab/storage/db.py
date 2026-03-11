"""SQLite helpers for run metadata."""

from __future__ import annotations

import sqlite3
from pathlib import Path


def connect(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            scenario_id TEXT NOT NULL,
            status TEXT NOT NULL,
            artifact_dir TEXT NOT NULL,
            run_mode TEXT NOT NULL DEFAULT 'standard',
            kernel_backend TEXT NOT NULL DEFAULT 'unknown',
            created_at TEXT NOT NULL,
            updated_at TEXT,
            error_message TEXT
        )
        """
    )
    _ensure_column(connection, "runs", "run_mode", "TEXT NOT NULL DEFAULT 'standard'")
    _ensure_column(connection, "runs", "kernel_backend", "TEXT NOT NULL DEFAULT 'unknown'")
    _ensure_column(connection, "runs", "updated_at", "TEXT")
    _ensure_column(connection, "runs", "error_message", "TEXT")
    connection.commit()


def _ensure_column(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
    column_definition: str,
) -> None:
    columns = {
        row["name"]
        for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    if column_name in columns:
        return
    connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")
