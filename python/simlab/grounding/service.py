"""Runtime scenario grounding with Postgres and pgvector."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
from typing import Iterable

from simlab.config import GroundingSettings
from simlab.schemas.artifacts import GroundingArtifact, GroundingEvidence
from simlab.schemas.scenario import Scenario

SUPPORTED_GROUNDING_EXTENSIONS = {".json", ".md", ".markdown", ".txt"}
_EMBEDDING_DIMENSION = 384
_MAX_SNIPPET_LENGTH = 240


@dataclass(frozen=True, slots=True)
class GroundingQuery:
    label: str
    text: str


@dataclass(frozen=True, slots=True)
class LoadedGroundingDocument:
    source_path: Path
    document_id: str
    content_hash: str
    title: str
    content_text: str


class GroundingError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def resolve_grounding_documents(*, scenario_path: Path, scenario: Scenario) -> list[Path]:
    resolved: list[Path] = []
    for raw_path in scenario.grounding.document_paths:
        path = Path(raw_path)
        resolved_path = path if path.is_absolute() else scenario_path.parent / path
        if not resolved_path.exists():
            raise FileNotFoundError(f"grounding document not found: {resolved_path}")
        if resolved_path.suffix.lower() not in SUPPORTED_GROUNDING_EXTENSIONS:
            raise ValueError(
                f"unsupported grounding document format: {resolved_path.suffix or '<none>'}"
            )
        resolved.append(resolved_path)
    return resolved


def build_grounding_queries(scenario: Scenario) -> list[GroundingQuery]:
    queries: list[GroundingQuery] = [
        GroundingQuery(
            label=f"scenario:{scenario.scenario_id}",
            text=scenario.title,
        )
    ]
    queries.extend(
        GroundingQuery(
            label=f"archetype:{archetype.id}",
            text=archetype.label,
        )
        for archetype in scenario.population.archetypes
    )
    queries.extend(
        GroundingQuery(
            label=f"intervention:{intervention.kind.value}:{intervention.round_index}",
            text=" ".join(
                [
                    intervention.kind.value,
                    *(intervention.target_groups or ["all-groups"]),
                    *(intervention.target_channels or ["all-channels"]),
                ]
            ),
        )
        for intervention in scenario.simulation.interventions
    )
    queries.extend(
        GroundingQuery(
            label=f"narrative:{token}",
            text=token.replace("_", " "),
        )
        for token in scenario.simulation.narrative_tokens
    )
    return queries


def ground_scenario(
    *,
    run_id: str,
    scenario_path: Path,
    scenario: Scenario,
    settings: GroundingSettings,
) -> GroundingArtifact | None:
    if not scenario.grounding.enabled:
        return None
    if not settings.postgres_dsn:
        raise GroundingError(
            "missing_dsn",
            "grounding is enabled but SIMLAB_RAG_POSTGRES_DSN is not configured",
        )

    try:
        document_paths = resolve_grounding_documents(scenario_path=scenario_path, scenario=scenario)
    except FileNotFoundError as exc:
        raise GroundingError("missing_document", str(exc)) from exc
    except ValueError as exc:
        raise GroundingError("unsupported_document_format", str(exc)) from exc

    documents = [_load_grounding_document(path) for path in document_paths]
    queries = build_grounding_queries(scenario)
    try:
        with _connect(settings) as connection:
            _initialize_schema(connection)
            document_ids = _ensure_documents_indexed(connection=connection, documents=documents, settings=settings)
            evidence = _retrieve_grounding_evidence(
                connection=connection,
                queries=queries,
                document_ids=document_ids,
                top_k=scenario.grounding.top_k,
                settings=settings,
            )
            connection.commit()
    except GroundingError:
        raise
    except RuntimeError as exc:
        message = str(exc)
        if "pip install -e .[rag]" in message:
            raise GroundingError("missing_dependency", message) from exc
        if "embedding model" in message or "sentence-transformers" in message:
            raise GroundingError("embedding_model_error", message) from exc
        raise GroundingError("grounding_runtime_error", message) from exc
    except Exception as exc:  # pragma: no cover - exercised in integration paths
        raise GroundingError("retrieval_error", str(exc)) from exc

    return GroundingArtifact(
        run_id=run_id,
        scenario_id=scenario.scenario_id,
        source_count=len({entry.source_path for entry in evidence}),
        query_count=len(queries),
        evidence=evidence,
    )


def _load_grounding_document(path: Path) -> LoadedGroundingDocument:
    if path.suffix.lower() == ".json":
        parsed = json.loads(path.read_text(encoding="utf-8"))
        content_text = json.dumps(parsed, ensure_ascii=False, indent=2)
    else:
        content_text = path.read_text(encoding="utf-8")

    normalized = content_text.strip()
    content_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    title = _extract_title(path=path, content_text=normalized)
    document_id = f"doc-{content_hash[:16]}"
    return LoadedGroundingDocument(
        source_path=path,
        document_id=document_id,
        content_hash=content_hash,
        title=title,
        content_text=normalized,
    )


def _extract_title(*, path: Path, content_text: str) -> str:
    for line in content_text.splitlines():
        stripped = line.strip().lstrip("#").strip()
        if stripped:
            return stripped[:120]
    return path.stem


def _chunk_text(text: str, *, max_chars: int = 700, overlap: int = 120) -> list[str]:
    collapsed = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not collapsed:
        return []
    paragraphs = [paragraph.strip() for paragraph in collapsed.split("\n\n") if paragraph.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if not current:
            current = paragraph
            continue
        candidate = f"{current}\n\n{paragraph}"
        if len(candidate) <= max_chars:
            current = candidate
            continue
        chunks.append(current)
        current = f"{current[-overlap:]}\n\n{paragraph}" if overlap else paragraph
    if current:
        chunks.append(current)
    return chunks


def _ensure_documents_indexed(
    *,
    connection,
    documents: list[LoadedGroundingDocument],
    settings: GroundingSettings,
) -> list[str]:
    cursor = connection.cursor()
    inserted_any = False
    for document in documents:
        cursor.execute(
            """
            SELECT document_id
            FROM rag_documents
            WHERE content_hash = %s
            """,
            (document.content_hash,),
        )
        row = cursor.fetchone()
        if row is not None:
            continue

        cursor.execute(
            """
            INSERT INTO rag_documents (document_id, source_path, content_hash, title, content_text)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                document.document_id,
                str(document.source_path),
                document.content_hash,
                document.title,
                document.content_text,
            ),
        )
        chunks = _chunk_text(document.content_text)
        embeddings = _embed_texts(chunks, model_name=settings.embedding_model)
        for index, (chunk_text, embedding) in enumerate(zip(chunks, embeddings, strict=True)):
            chunk_id = f"chunk-{document.content_hash[:12]}-{index:04d}"
            cursor.execute(
                """
                INSERT INTO rag_chunks (chunk_id, document_id, chunk_index, chunk_text, embedding)
                VALUES (%s, %s, %s, %s, %s::vector)
                """,
                (
                    chunk_id,
                    document.document_id,
                    index,
                    chunk_text,
                    _vector_literal(embedding),
                ),
            )
        inserted_any = True

    if inserted_any:
        cursor.execute("ANALYZE rag_chunks")
    return [document.document_id for document in documents]


def _retrieve_grounding_evidence(
    *,
    connection,
    queries: list[GroundingQuery],
    document_ids: list[str],
    top_k: int,
    settings: GroundingSettings,
) -> list[GroundingEvidence]:
    evidence: list[GroundingEvidence] = []
    cursor = connection.cursor()
    for query in queries:
        embedding = _embed_texts([query.text], model_name=settings.embedding_model)[0]
        vector_literal = _vector_literal(embedding)
        cursor.execute(
            """
            SELECT d.source_path, c.chunk_id, c.chunk_text, 1 - (c.embedding <=> %s::vector) AS score
            FROM rag_chunks AS c
            INNER JOIN rag_documents AS d ON d.document_id = c.document_id
            WHERE c.document_id = ANY(%s)
            ORDER BY c.embedding <=> %s::vector
            LIMIT %s
            """,
            (
                vector_literal,
                document_ids,
                vector_literal,
                top_k,
            ),
        )
        for source_path, chunk_id, chunk_text, score in cursor.fetchall():
            evidence.append(
                GroundingEvidence(
                    query_label=query.label,
                    source_path=str(source_path),
                    chunk_id=str(chunk_id),
                    score=float(score),
                    snippet=_normalize_snippet(str(chunk_text)),
                )
            )
    return evidence


def retrieve_grounding_evidence_for_testing(
    *,
    connection,
    queries: list[GroundingQuery],
    document_ids: list[str],
    top_k: int,
    settings: GroundingSettings,
) -> list[GroundingEvidence]:
    return _retrieve_grounding_evidence(
        connection=connection,
        queries=queries,
        document_ids=document_ids,
        top_k=top_k,
        settings=settings,
    )


def _normalize_snippet(text: str) -> str:
    collapsed = re.sub(r"\s+", " ", text).strip()
    if len(collapsed) <= _MAX_SNIPPET_LENGTH:
        return collapsed
    return f"{collapsed[:_MAX_SNIPPET_LENGTH - 3]}..."


def _initialize_schema(connection) -> None:
    cursor = connection.cursor()
    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS rag_documents (
            document_id TEXT PRIMARY KEY,
            source_path TEXT NOT NULL,
            content_hash TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            content_text TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS rag_chunks (
            chunk_id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL REFERENCES rag_documents (document_id) ON DELETE CASCADE,
            chunk_index INTEGER NOT NULL,
            chunk_text TEXT NOT NULL,
            embedding vector({_EMBEDDING_DIMENSION}) NOT NULL
        )
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS rag_chunks_document_id_idx
        ON rag_chunks (document_id)
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS rag_chunks_embedding_idx
        ON rag_chunks
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 32)
        """
    )
    connection.commit()


def _connect(settings: GroundingSettings):
    try:
        import psycopg
    except ImportError as exc:  # pragma: no cover - optional dependency path
        raise RuntimeError(
            "grounding requires the optional 'rag' dependencies; install with pip install -e .[rag]"
        ) from exc
    return psycopg.connect(settings.postgres_dsn)


@lru_cache(maxsize=2)
def _load_embedding_model(model_name: str):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:  # pragma: no cover - optional dependency path
        raise RuntimeError(
            "grounding requires sentence-transformers; install with pip install -e .[rag]"
        ) from exc

    model = SentenceTransformer(model_name)
    dimension = getattr(model, "get_sentence_embedding_dimension", lambda: None)()
    if dimension is not None and dimension != _EMBEDDING_DIMENSION:
        raise RuntimeError(
            f"embedding model dimension mismatch: expected {_EMBEDDING_DIMENSION}, got {dimension}"
        )
    return model


def _embed_texts(texts: Iterable[str], *, model_name: str) -> list[list[float]]:
    materialized = list(texts)
    if not materialized:
        return []
    model = _load_embedding_model(model_name)
    encoded = model.encode(materialized, normalize_embeddings=True)
    return [list(map(float, row)) for row in encoded]


def _vector_literal(values: Iterable[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"
