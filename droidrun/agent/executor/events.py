"""
Events for the ExecutorAgent workflow.

Internal events for streaming to frontend/logging.
For DroidAgent coordination events, see droid/events.py
"""

from typing import Dict, Optional

from llama_index.core.workflow import Event

from droidrun.agent.usage import UsageResult


# 教程注释：Executor 的事件把“模型建议了什么动作”和“动作实际执行结果如何”拆成不同阶段。
class ExecutorContextEvent(Event):
    """Context prepared, ready for LLM call."""

    subgoal: str


class ExecutorResponseEvent(Event):
    """LLM response received, ready for parsing."""

    response: str
    usage: Optional[UsageResult] = None


class ExecutorActionEvent(Event):
    """Action parsed, ready to execute."""

    action_json: str
    thought: str
    description: str
    full_response: str = ""


class ExecutorActionResultEvent(Event):
    """Action execution result (internal event with full details)."""

    action: Dict
    success: bool
    error: str
    summary: str
    thought: str = ""
    full_response: str = ""
