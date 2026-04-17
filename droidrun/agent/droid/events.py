"""
DroidAgent coordination events.

These events route between DroidAgent and child agents.
For internal agent events, see each agent's events.py file.
"""

from typing import Dict, List, Optional

from llama_index.core.workflow import Event, StopEvent
from pydantic import BaseModel


# 教程注释：这些事件是顶层协调器和子 Agent 之间的“流程消息”，用来驱动 planning、execution 和最终收尾。
class FastAgentExecuteEvent(Event):
    instruction: str


class FastAgentResultEvent(Event):
    success: bool
    reason: str
    instruction: str


# ============================================================================
# Manager/Executor coordination events
# ============================================================================


class ManagerInputEvent(Event):
    """Trigger Manager workflow for planning"""

    pass



# 教程注释：ManagerPlanEvent 是 Manager 回给 DroidAgent 的协调结果，顶层会据此决定是否进入 Executor 或直接结束。
class ManagerPlanEvent(Event):
    """
    Coordination event from ManagerAgent to DroidAgent.

    Used for workflow step routing only (NOT streamed to frontend).
    For internal events with memory_update metadata, see ManagerPlanDetailsEvent.
    """

    plan: str
    current_subgoal: str
    thought: str
    answer: str = ""
    success: Optional[bool] = None  # True/False if complete, None if in progress


class ExecutorInputEvent(Event):
    """Trigger Executor workflow for action execution"""

    current_subgoal: str


class ExecutorResultEvent(Event):
    """Executor finished with action result."""

    action: Dict
    outcome: bool
    error: str
    summary: str


# ============================================================================
# EXTERNAL USER MESSAGE EVENTS
# ============================================================================


# 教程注释：AppliedEvent 表示一批外部插队消息已被某个消费者（manager/fast_agent）真正吸收到上下文中。
class ExternalUserMessageAppliedEvent(Event):
    message_ids: List[str]
    consumer: str
    step_number: int


# 教程注释：DroppedEvent 表示消息还没来得及消费就被丢弃，常见于达到最大步数或任务结束边界。
class ExternalUserMessageDroppedEvent(Event):
    message_ids: List[str]
    reason: str
    step_number: int


# ============================================================================
# FINALIZATION EVENTS
# ============================================================================


class FinalizeEvent(Event):
    """Trigger finalization."""

    success: bool
    reason: str



# 教程注释：ResultEvent 是整个任务最终返回给调用方的结果对象，相当于顶层工作流的统一出口。
class ResultEvent(StopEvent):
    """
    Final result from DroidAgent.

    Returned by DroidAgent.run() with:
    - success: Whether the task completed successfully
    - reason: Explanation or answer
    - steps: Number of steps taken
    - structured_output: Extracted structured data (if output_model was provided)
    """

    success: bool
    reason: str
    steps: int
    structured_output: Optional[BaseModel] = None
