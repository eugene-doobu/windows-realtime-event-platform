"""Representative thread graph export for interaction-heavy runs."""

from __future__ import annotations

from pathlib import Path

import networkx as nx

from simlab.schemas.artifacts import ReactionEvent, RepresentativeThreadArtifact, ThreadMessage
from simlab.visualization.graph_export import write_dot


def write_representative_thread_graph(
    *,
    representative_thread,
    messages: list[ThreadMessage],
    reactions: list[ReactionEvent],
    path: Path,
) -> None:
    graph = nx.DiGraph()
    thread = representative_thread
    if thread.thread_id is None:
        graph.add_node("empty-thread", label="No representative thread")
        write_dot(graph, path)
        return

    thread_root = thread.thread_id
    graph.add_node(
        thread_root,
        label=f"{thread.thread_id}\\n{thread.channel_id}\\n{thread.narrative_token}",
    )

    message_lookup = {
        message.message_id: message
        for message in messages
        if message.thread_id == thread.thread_id
    }
    reaction_lookup = [
        reaction
        for reaction in reactions
        if reaction.thread_id == thread.thread_id
    ]

    for message in message_lookup.values():
        node_id = f"message:{message.message_id}"
        graph.add_node(
            node_id,
            label=(
                f"{message.message_id}\\n"
                f"r{message.round_index} {message.group_id}/{message.action_type}\\n"
                f"{message.narrative_token}"
            ),
        )
        parent = thread_root if message.parent_message_id is None else f"message:{message.parent_message_id}"
        graph.add_edge(parent, node_id, label=message.action_type)

    for reaction in reaction_lookup:
        node_id = f"reaction:{reaction.reaction_id}"
        graph.add_node(
            node_id,
            label=(
                f"{reaction.reaction_id}\\n"
                f"r{reaction.round_index} {reaction.group_id}/{reaction.reaction_kind}\\n"
                f"{reaction.narrative_token}"
            ),
        )
        graph.add_edge(f"message:{reaction.target_message_id}", node_id, label=reaction.reaction_kind)

    write_dot(graph, path)
