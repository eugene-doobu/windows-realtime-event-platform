"""Render representative text for deterministic interaction artifacts."""

from __future__ import annotations

from gan_simlab.schemas.artifacts import ConversationEntry, ReactionEvent, ThreadMessage

_NARRATIVE_PHRASES = {
    "burden_unfair": "the burden feels unfair",
    "reform_needed": "the reform still looks necessary",
    "future_distrust": "trust in the future is weakening",
    "clarification_accepted": "the clarification helps a bit",
}

_TONE_PREFIX = {
    "frustrated": "Honestly, ",
    "measured": "From a practical angle, ",
    "formal": "In my view, ",
    "neutral": "",
}

_ARGUMENT_SUFFIX = {
    "fairness_first": "and that is the fairness issue people keep reacting to.",
    "cost_benefit": "so the cost-benefit balance matters most here.",
    "stability_first": "because stability matters more than short-term noise.",
    "pragmatic": "so the next step should stay practical.",
}

_ARGUMENT_SHORT_SUFFIX = {
    "fairness_first": "Fairness still matters most here.",
    "cost_benefit": "The tradeoff still matters here.",
    "stability_first": "Stability still matters here.",
    "pragmatic": "The next step should stay practical.",
}


def render_conversation(
    *,
    messages: list[ThreadMessage],
    reactions: list[ReactionEvent],
    persona: dict[str, list[float] | list[int] | list[str] | list[dict[str, float]]],
) -> list[ConversationEntry]:
    rendered: list[ConversationEntry] = []
    for message in messages:
        rendered.append(
            ConversationEntry(
                round_index=message.round_index,
                thread_id=message.thread_id,
                message_id=message.message_id,
                agent_id=message.agent_id,
                group_id=message.group_id,
                action_type=message.action_type,
                rendered_text=_render_message(
                    action_type=message.action_type,
                    narrative_token=message.narrative_token,
                    tone_style=message.tone_style,
                    argument_style=message.argument_style,
                    verbosity=float(persona["verbosity"][message.agent_id]),
                ),
                narrative_token=message.narrative_token,
                channel_id=message.channel_id,
                tone_style=message.tone_style,
                argument_style=message.argument_style,
            )
        )
    for reaction in reactions:
        tone_style = str(persona["tone_style"][reaction.agent_id])
        argument_style = str(persona["argument_style"][reaction.agent_id])
        rendered.append(
            ConversationEntry(
                round_index=reaction.round_index,
                thread_id=reaction.thread_id,
                message_id=reaction.target_message_id,
                agent_id=reaction.agent_id,
                group_id=reaction.group_id,
                action_type="react",
                rendered_text=_render_reaction(
                    reaction_kind=reaction.reaction_kind,
                    narrative_token=reaction.narrative_token,
                    tone_style=tone_style,
                    argument_style=argument_style,
                ),
                narrative_token=reaction.narrative_token,
                channel_id=reaction.channel_id,
                tone_style=tone_style,
                argument_style=argument_style,
            )
        )
    rendered.sort(key=lambda entry: (entry.round_index, entry.thread_id, entry.message_id, entry.agent_id))
    return rendered


def _render_message(
    *,
    action_type: str,
    narrative_token: str,
    tone_style: str,
    argument_style: str,
    verbosity: float,
) -> str:
    prefix = _TONE_PREFIX.get(tone_style, "")
    phrase = _NARRATIVE_PHRASES.get(narrative_token, narrative_token.replace("_", " "))
    suffix = _ARGUMENT_SUFFIX.get(argument_style, _ARGUMENT_SUFFIX["pragmatic"])
    if action_type == "reply":
        prefix = prefix or "Replying here, "
    if verbosity < 0.4:
        short_suffix = _ARGUMENT_SHORT_SUFFIX.get(argument_style, _ARGUMENT_SHORT_SUFFIX["pragmatic"])
        return f"{prefix}{phrase}. {short_suffix}"
    if verbosity < 0.7:
        return f"{prefix}{phrase}, {suffix}"
    return f"{prefix}{phrase}, and that keeps showing up across the discussion, {suffix}"


def _render_reaction(
    *,
    reaction_kind: str,
    narrative_token: str,
    tone_style: str,
    argument_style: str,
) -> str:
    phrase = _NARRATIVE_PHRASES.get(narrative_token, narrative_token.replace("_", " "))
    if reaction_kind == "amplify":
        return f"{_TONE_PREFIX.get(tone_style, '')}amplifying the point that {phrase}."
    if reaction_kind == "question":
        return f"{_TONE_PREFIX.get(tone_style, '')}questioning whether {phrase}."
    return f"{_TONE_PREFIX.get(tone_style, '')}endorsing the view that {phrase}."
