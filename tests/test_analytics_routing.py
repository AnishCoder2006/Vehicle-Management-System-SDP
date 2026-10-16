
from agents.router import Intent, classify_intent


def test_maintenance_request_routes_to_analytics():
    decision = classify_intent(
        "Predict maintenance risk for vehicle 0",
        {},
    )

    assert decision.intent == Intent.ANALYTICS
    assert "analytics_agent" in decision.target_agents


def test_cost_summary_routes_to_analytics():
    decision = classify_intent(
        "Show me the cost summary",
        {},
    )

    assert decision.intent == Intent.ANALYTICS
    assert "analytics_agent" in decision.target_agents


def test_fleet_statistics_routes_to_analytics():
    decision = classify_intent(
        "Show overall fleet statistics",
        {},
    )

    assert decision.intent == Intent.ANALYTICS
    assert "analytics_agent" in decision.target_agents
