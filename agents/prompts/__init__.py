"""Prompts package for all agents in the multi-agent system.
"""

from agents.prompts.master_prompt import MASTER_SYSTEM_PROMPT
from agents.prompts.vehicle_prompt import VEHICLE_SYSTEM_PROMPT
from agents.prompts.analytics_prompt import ANALYTICS_SYSTEM_PROMPT
from agents.prompts.automation_prompt import AUTOMATION_SYSTEM_PROMPT

__all__ = [
    "MASTER_SYSTEM_PROMPT",
    "VEHICLE_SYSTEM_PROMPT",
    "ANALYTICS_SYSTEM_PROMPT",
    "AUTOMATION_SYSTEM_PROMPT",
]
