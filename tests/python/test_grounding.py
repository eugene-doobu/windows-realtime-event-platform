import json
from pathlib import Path

import pytest

from gan_simlab.config import GroundingSettings
from gan_simlab.grounding import build_grounding_queries, resolve_grounding_documents
from gan_simlab.grounding.service import GroundingQuery, retrieve_grounding_evidence_for_testing
from gan_simlab.schemas.scenario import Scenario


def test_resolve_grounding_documents_for_fixture() -> None:
    scenario_path = (
        Path(__file__).resolve().parents[2]
        / "fixtures"
        / "synthetic_public_issue"
        / "scenario_grounded.json"
    )
    scenario = Scenario.model_validate(json.loads(scenario_path.read_text(encoding="utf-8")))

    resolved = resolve_grounding_documents(scenario_path=scenario_path, scenario=scenario)

    assert [path.name for path in resolved] == [
        "briefing.md",
        "community.txt",
        "interventions.json",
    ]


def test_build_grounding_queries_is_deterministic() -> None:
    scenario_path = (
        Path(__file__).resolve().parents[2]
        / "fixtures"
        / "synthetic_public_issue"
        / "scenario_grounded.json"
    )
    scenario = Scenario.model_validate(json.loads(scenario_path.read_text(encoding="utf-8")))

    queries = build_grounding_queries(scenario)

    assert queries[0].label == "scenario:synthetic-public-issue-grounded"
    assert "archetype:young_workers" in {query.label for query in queries}
    assert "intervention:clarification:3" in {query.label for query in queries}
    assert "narrative:clarification_accepted" in {query.label for query in queries}


def test_resolve_grounding_documents_rejects_unsupported_extension(tmp_path: Path) -> None:
    scenario = Scenario.model_validate(
        {
            "scenario_id": "invalid-grounding",
            "title": "Invalid Grounding",
            "population": {
                "size": 10,
                "archetypes": [
                    {
                        "id": "group_a",
                        "label": "Group A",
                        "share": 1.0,
                        "base_stance": 0.0,
                        "base_trust": 0.5,
                        "base_salience": 0.5,
                        "base_susceptibility": 0.5,
                        "base_activity": 0.5,
                        "base_influence": 0.5,
                    }
                ],
                "intra_group_edge_prob": 0.1,
                "inter_group_edge_prob": 0.0,
                "influencer_ratio": 0.0,
                "variation_sigma": 0.1,
            },
            "simulation": {
                "rounds": 1,
                "random_seed": 7,
                "max_posts_per_round": 10,
                "narrative_tokens": ["token_a"],
                "channels": [
                    {
                        "id": "news_a",
                        "kind": "news",
                        "exposure_weight": 1.0,
                        "repost_factor": 0.1,
                        "rumor_decay": 0.5,
                        "trust_penalty": 0.1,
                    }
                ],
            },
            "grounding": {
                "enabled": True,
                "document_paths": ["notes.pdf"],
            },
        }
    )
    (tmp_path / "notes.pdf").write_text("pdf", encoding="utf-8")

    with pytest.raises(ValueError, match="unsupported grounding document format"):
        resolve_grounding_documents(scenario_path=tmp_path / "scenario.json", scenario=scenario)


def test_retrieve_grounding_evidence_returns_known_synthetic_snippets(monkeypatch) -> None:
    class FakeCursor:
        def __init__(self) -> None:
            self._rows = []

        def execute(self, query, params) -> None:
            vector_literal, document_ids, _, top_k = params
            assert vector_literal.startswith("[")
            assert document_ids == ["doc-briefing", "doc-community"]
            assert top_k == 2
            self._rows = [
                (
                    "fixtures/synthetic_public_issue/grounding/briefing.md",
                    "chunk-briefing-0001",
                    "Young workers are expected to react strongly to unfair burden framing.",
                    0.91,
                ),
                (
                    "fixtures/synthetic_public_issue/grounding/community.txt",
                    "chunk-community-0002",
                    "Community discussion quickly turns toward distrust when policy burdens feel unfair.",
                    0.84,
                ),
            ]

        def fetchall(self):
            return self._rows

    class FakeConnection:
        def __init__(self) -> None:
            self._cursor = FakeCursor()

        def cursor(self):
            return self._cursor

    monkeypatch.setattr(
        "gan_simlab.grounding.service._embed_texts",
        lambda texts, model_name: [[0.1] * 384 for _ in list(texts)],
    )

    evidence = retrieve_grounding_evidence_for_testing(
        connection=FakeConnection(),
        queries=[GroundingQuery(label="archetype:young_workers", text="Young workers")],
        document_ids=["doc-briefing", "doc-community"],
        top_k=2,
        settings=GroundingSettings(
            postgres_dsn="postgresql://postgres:postgres@localhost:5432/simlab",
            embedding_model="sentence-transformers/all-MiniLM-L6-v2",
        ),
    )

    assert len(evidence) == 2
    assert evidence[0].query_label == "archetype:young_workers"
    assert "Young workers are expected to react strongly" in evidence[0].snippet
    assert evidence[1].source_path.endswith("community.txt")
