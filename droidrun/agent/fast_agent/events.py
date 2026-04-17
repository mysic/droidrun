"""
Events for the FastAgent workflow.

Internal events for streaming to frontend/logging.
"""

from typing import Optional

from llama_index.core.workflow import Event

from droidrun.agent.usage import UsageResult


# 教程注释：FastAgent 事件围绕一个自循环展开，依次表示输入、模型回复、工具调用、工具结果和结束状态。
class FastAgentInputEvent(Event):
    """Input ready for LLM."""

    pass


class FastAgentResponseEvent(Event):
    """LLM response received."""

    # 教程注释：thought 是模型本轮思考文本，code 是 XML 工具调用块，usage 是本轮 token 统计。
    thought: str
    code: Optional[str] = None
    usage: Optional[UsageResult] = None


class FastAgentToolCallEvent(Event):
    """Tool calls ready to execute."""

    # 教程注释：tool_calls_repr 保留原始调用片段，便于日志和调试复盘。
    tool_calls_repr: str


class FastAgentOutputEvent(Event):
    """Tool execution result."""

    output: str


class FastAgentEndEvent(Event):
    """FastAgent finished."""

    success: bool
    reason: str
    tool_call_count: int = 0
