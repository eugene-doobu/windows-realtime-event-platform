"""Application paths and repository-local defaults."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True, slots=True)
class AppPaths:
    repo_root: Path
    artifacts_dir: Path
    runs_dir: Path
    cache_dir: Path
    db_path: Path


@dataclass(frozen=True, slots=True)
class GroundingSettings:
    postgres_dsn: str | None
    embedding_model: str


def load_app_paths() -> AppPaths:
    repo_root = Path(os.environ.get("SIMLAB_REPO_ROOT", Path(__file__).resolve().parents[2]))
    artifacts_dir = Path(os.environ.get("SIMLAB_ARTIFACTS_DIR", repo_root / "artifacts"))
    runs_dir = Path(os.environ.get("SIMLAB_RUNS_DIR", artifacts_dir / "api-runs"))
    cache_dir = Path(os.environ.get("SIMLAB_CACHE_DIR", artifacts_dir / "cache" / "prepared"))
    db_path = Path(os.environ.get("SIMLAB_DB_PATH", artifacts_dir / "simlab.db"))
    return AppPaths(
        repo_root=repo_root,
        artifacts_dir=artifacts_dir,
        runs_dir=runs_dir,
        cache_dir=cache_dir,
        db_path=db_path,
    )


def load_grounding_settings() -> GroundingSettings:
    return GroundingSettings(
        postgres_dsn=os.environ.get("SIMLAB_RAG_POSTGRES_DSN"),
        embedding_model=os.environ.get(
            "SIMLAB_RAG_EMBEDDING_MODEL",
            "sentence-transformers/all-MiniLM-L6-v2",
        ),
    )
