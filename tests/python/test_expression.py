from gan_simlab.expression import render_conversation
from gan_simlab.schemas.artifacts import ThreadMessage


def test_render_conversation_reflects_tone_and_argument_style() -> None:
    messages = [
        ThreadMessage(
            message_id="msg-001",
            thread_id="thread-001",
            round_index=0,
            agent_id=0,
            group_id="young_workers",
            action_type="post",
            narrative_token="burden_unfair",
            channel_id="community_forum",
            tone_style="frustrated",
            argument_style="fairness_first",
        ),
        ThreadMessage(
            message_id="msg-002",
            thread_id="thread-001",
            round_index=0,
            agent_id=1,
            group_id="benefit_recipients",
            action_type="reply",
            narrative_token="clarification_accepted",
            channel_id="news_main",
            tone_style="formal",
            argument_style="stability_first",
            parent_message_id="msg-001",
        ),
    ]
    persona = {
        "verbosity": [0.8, 0.35],
        "tone_style": ["frustrated", "formal"],
        "argument_style": ["fairness_first", "stability_first"],
    }

    conversation = render_conversation(
        messages=messages,
        reactions=[],
        persona=persona,
    )
    rendered_by_agent = {entry.agent_id: entry.rendered_text for entry in conversation}

    assert rendered_by_agent[0].startswith("Honestly, ")
    assert "fairness issue" in rendered_by_agent[0]
    assert rendered_by_agent[1].startswith("In my view, ")
    assert "stability" in rendered_by_agent[1].lower()
