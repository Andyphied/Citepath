"""Unit tests for agent planning payload coercion."""

from app.modules.agents.schemas import AgentPlanAction


def test_agent_plan_action_accepts_call_tool() -> None:
    plan = AgentPlanAction.model_validate(
        {
            "action": "call_tool",
            "tool_name": "search_knowledge_base",
            "arguments": {"query": "billing 502"},
            "reason": "gather evidence",
        }
    )
    assert plan.action == "call_tool"
    assert plan.tool_name == "search_knowledge_base"


def test_agent_plan_action_coerces_tool_name_in_action_field() -> None:
    """gpt-4o-mini often sets action to the tool name instead of call_tool."""
    plan = AgentPlanAction.model_validate(
        {
            "action": "search_knowledge_base",
            "tool_name": "search_knowledge_base",
            "arguments": {"query": "billing API 502 errors after deployment"},
            "reason": "gather relevant information",
        }
    )
    assert plan.action == "call_tool"
    assert plan.tool_name == "search_knowledge_base"


def test_agent_plan_action_coerces_when_tool_name_missing() -> None:
    plan = AgentPlanAction.model_validate(
        {
            "action": "suggest_debugging_steps",
            "arguments": {"service": "billing-api", "symptom": "502"},
            "reason": "checklist",
        }
    )
    assert plan.action == "call_tool"
    assert plan.tool_name == "suggest_debugging_steps"
