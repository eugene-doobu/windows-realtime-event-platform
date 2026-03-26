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


def _env(*names: str, default: str | Path | None = None) -> str | Path | None:
    for name in names:
        value = os.environ.get(name)
        if value is not None:
            return value
    return default


def load_app_paths() -> AppPaths:
    repo_root = Path(_env("GAN_SIMLAB_REPO_ROOT", "SIMLAB_REPO_ROOT", default=Path(__file__).resolve().parents[2]))
    artifacts_dir = Path(_env("GAN_SIMLAB_ARTIFACTS_DIR", "SIMLAB_ARTIFACTS_DIR", default=repo_root / "artifacts"))
    runs_dir = Path(_env("GAN_SIMLAB_RUNS_DIR", "SIMLAB_RUNS_DIR", default=artifacts_dir / "api-runs"))
    cache_dir = Path(_env("GAN_SIMLAB_CACHE_DIR", "SIMLAB_CACHE_DIR", default=artifacts_dir / "cache" / "prepared"))
    db_path = Path(_env("GAN_SIMLAB_DB_PATH", "SIMLAB_DB_PATH", default=artifacts_dir / "gan_simlab.db"))
    return AppPaths(
        repo_root=repo_root,
        artifacts_dir=artifacts_dir,
        runs_dir=runs_dir,
        cache_dir=cache_dir,
        db_path=db_path,
    )


def load_grounding_settings() -> GroundingSettings:
    return GroundingSettings(
        postgres_dsn=_env("GAN_SIMLAB_RAG_POSTGRES_DSN", "SIMLAB_RAG_POSTGRES_DSN"),
        embedding_model=str(
            _env(
                "GAN_SIMLAB_RAG_EMBEDDING_MODEL",
                "SIMLAB_RAG_EMBEDDING_MODEL",
                default="sentence-transformers/all-MiniLM-L6-v2",
            )
        ),
    )
