"""Group-level graph export for a completed run."""

from __future__ import annotations

from pathlib import Path

import networkx as nx

from simlab.runner.population import PreparedSimulationInput
from simlab.visualization.graph_export import write_dot


def write_group_influence_graph(
    *,
    prepared: PreparedSimulationInput,
    path: Path,
) -> None:
    graph = nx.DiGraph()
    group_labels = prepared.group_labels
    offsets = prepared.graph["offsets"]
    targets = prepared.graph["targets"]
    weights = prepared.graph["weights"]
    agent_groups = prepared.initial_state["group_id"]

    for label in group_labels.values():
        graph.add_node(label, label=label)

    edge_weights: dict[tuple[str, str], float] = {}
    edge_counts: dict[tuple[str, str], int] = {}

    for source in range(len(offsets) - 1):
        source_label = group_labels[int(agent_groups[source])]
        for edge_index in range(offsets[source], offsets[source + 1]):
            target = int(targets[edge_index])
            target_label = group_labels[int(agent_groups[target])]
            key = (source_label, target_label)
            edge_weights[key] = edge_weights.get(key, 0.0) + float(weights[edge_index])
            edge_counts[key] = edge_counts.get(key, 0) + 1

    for (source_label, target_label), total_weight in edge_weights.items():
        graph.add_edge(
            source_label,
            target_label,
            label=f"{edge_counts[(source_label, target_label)]} edges / {total_weight:.1f}",
        )

    write_dot(graph, path)

