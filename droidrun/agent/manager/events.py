"""
Events for the ManagerAgent workflow.

Internal events for streaming to frontend/logging.
For DroidAgent coordination events, see droid/events.py
"""

from typing import Optional

from llama_index.core.workflow import Event

from droidrun.agent.usage import UsageResult


# 教程注释：Manager 的事件描述“上下文准备好了”“模型回应回来了”“计划已经解析好了”这几个内部阶段。
class ManagerContextEvent(Event):
    """Context prepared, ready for LLM call."""

    pass


class ManagerResponseEvent(Event):
    """LLM response received, ready for parsing."""

    response: str
    usage: Optional[UsageResult] = None


class ManagerPlanDetailsEvent(Event):
    """Plan parsed and ready (internal event with full details)."""

    plan: str
    subgoal: str
    thought: str
    answer: str = ""
    memory_update: str = ""
    progress_summary: str = ""
    success: Optional[bool] = None  # True/False if complete, None if in progress
    full_response: str = ""
