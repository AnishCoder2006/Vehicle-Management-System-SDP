"""Unit tests for the intent classifier and routing table.

Verifies that the router correctly routes 12+ example messages to the right agent(s),
handles multi-agent queries, and triggers clarification for vague requests.
"""

import pytest
from agents.router import Intent, ROUTING_EXAMPLES, classify_intent


def test_routing_table_examples_coverage():
    """Verify routing accuracy across all 17 benchmark messages."""
    assert len(ROUTING_EXAMPLES) >= 12, "Must test at least 12 example messages"

    for example in ROUTING_EXAMPLES:
        msg = example["message"]
        expected_intent = example["expected_intent"]
        expected_agents = example["expected_agents"]

        decision = classify_intent(msg)

        assert decision.intent == expected_intent, (
            f"Failed on message: '{msg}'. Expected intent {expected_intent}, got {decision.intent}"
        )
        for expected_agent in expected_agents:
            assert expected_agent in decision.target_agents, (
                f"Failed on message: '{msg}'. Expected agent {expected_agent} in {decision.target_agents}"
            )


def test_unclear_message_asks_clarifying_question():
    """Verify that ambiguous/unclear inputs produce a single focused clarifying question."""
    unclear_queries = [
        "Update it please.",
        "Check the status.",
        "help",
        "do it",
    ]

    for q in unclear_queries:
        decision = classify_intent(q)
        assert decision.intent == Intent.UNCLEAR
        assert decision.clarifying_question is not None
        assert len(decision.clarifying_question) > 10


def test_multi_agent_intent_detection():
    """Verify that cross-domain requests are classified as multi-agent."""
    multi_queries = [
        "Show due vehicles and book services for them.",
        "List available vans and give me the total costs summary.",
    ]

    for q in multi_queries:
        decision = classify_intent(q)
        assert decision.intent == Intent.MULTI_AGENT
        assert len(decision.target_agents) >= 2
