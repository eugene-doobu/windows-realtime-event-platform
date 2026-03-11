"""Cache prepared population and graph inputs between runs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from simlab.runner.execution import RunMode
from simlab.runner.population import PreparationProfile, PreparedSimulationInput, prepare_simulation_input
from simlab.schemas.scenario import Scenario


@dataclass(frozen=True, slots=True)
class PreparedInputResult:
    prepared: PreparedSimulationInput
    cache_key: str
    source: str


def load_or_prepare_prepared_input(
    *,
    scenario: Scenario,
    run_mode: RunMode,
    cache_dir: Path,
) -> PreparedInputResult:
    cache_key = build_prepared_input_cache_key(scenario=scenario, run_mode=run_mode)
    cache_path = cache_dir / f"{cache_key}.json"

    if cache_path.exists():
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
        return PreparedInputResult(
            prepared=PreparedSimulationInput(
                initial_state=payload["initial_state"],
                graph=payload["graph"],
                config=payload["config"],
                group_labels={int(key): value for key, value in payload["group_labels"].items()},
                persona=payload["persona"],
                profile=PreparationProfile(**payload["profile"]),
            ),
            cache_key=cache_key,
            source="cache",
        )

    prepared = prepare_simulation_input(scenario)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(
            {
                "initial_state": prepared.initial_state,
                "graph": prepared.graph,
                "config": prepared.config,
                "group_labels": prepared.group_labels,
                "persona": prepared.persona,
                "profile": {
                    "population_size": prepared.profile.population_size,
                    "edge_count": prepared.profile.edge_count,
                    "state_generation_time_ms": prepared.profile.state_generation_time_ms,
                    "graph_generation_time_ms": prepared.profile.graph_generation_time_ms,
                    "config_generation_time_ms": prepared.profile.config_generation_time_ms,
                    "estimated_state_bytes": prepared.profile.estimated_state_bytes,
                    "estimated_graph_bytes": prepared.profile.estimated_graph_bytes,
                    "estimated_persona_bytes": prepared.profile.estimated_persona_bytes,
                    "estimated_total_bytes": prepared.profile.estimated_total_bytes,
                },
            },
            ensure_ascii=True,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    return PreparedInputResult(prepared=prepared, cache_key=cache_key, source="generated")


def build_prepared_input_cache_key(*, scenario: Scenario, run_mode: RunMode) -> str:
    canonical = json.dumps(
        {
            "version": 4,
            "run_mode": run_mode.value,
            "scenario": scenario.model_dump(mode="json"),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
