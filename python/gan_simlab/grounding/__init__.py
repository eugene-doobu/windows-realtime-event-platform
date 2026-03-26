"""Scenario grounding and retrieval support."""

from gan_simlab.grounding.service import (
    GroundingError,
    build_grounding_queries,
    ground_scenario,
    resolve_grounding_documents,
)

__all__ = [
    "GroundingError",
    "build_grounding_queries",
    "ground_scenario",
    "resolve_grounding_documents",
]
