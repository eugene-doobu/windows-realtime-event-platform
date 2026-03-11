"""Graph export utilities for post-run inspection."""

from __future__ import annotations

from pathlib import Path

import networkx as nx


def write_dot(graph: nx.DiGraph, path: Path) -> None:
    lines = ["digraph simlab {"]

    for node_id, attributes in graph.nodes(data=True):
        label = str(attributes.get("label", node_id)).replace('"', '\\"')
        lines.append(f'  "{node_id}" [label="{label}"];')

    for source, target, attributes in graph.edges(data=True):
        label = str(attributes.get("label", "")).replace('"', '\\"')
        lines.append(f'  "{source}" -> "{target}" [label="{label}"];')

    lines.append("}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
