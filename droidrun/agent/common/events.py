from typing import Any, Dict

from llama_index.core.workflow import Event


# 教程注释：ScreenshotEvent 在工作流节点间传递截图二进制，供视觉理解或调试输出使用。
class ScreenshotEvent(Event):
    screenshot: bytes


# 教程注释：RecordUIStateEvent 传递结构化 UI 元素列表，用于后续规划、过滤和格式化。
class RecordUIStateEvent(Event):
    ui_state: list[Dict[str, Any]]


# 教程注释：ToolExecutionEvent 记录每一次工具调用结果，方便日志、UI 展示和上层工作流追踪执行历史。
class ToolExecutionEvent(Event):
    """Emitted after every tool call dispatched through ToolRegistry."""

    tool_name: str
    tool_args: Dict[str, Any]
    success: bool
    summary: str
