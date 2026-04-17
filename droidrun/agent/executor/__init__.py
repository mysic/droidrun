"""
Executor Agent - Action execution workflow.
"""

from droidrun.agent.droid.events import ExecutorInputEvent, ExecutorResultEvent
from droidrun.agent.executor.events import (
    ExecutorActionEvent,
    ExecutorContextEvent,
    ExecutorResponseEvent,
    ExecutorActionResultEvent,
)
from droidrun.agent.executor.executor_agent import ExecutorAgent


# 教程注释：这里集中导出 Executor 子系统的主类和事件，供上层协调器统一接入执行阶段。
__all__ = [
    "ExecutorAgent",
    "ExecutorInputEvent",
    "ExecutorResultEvent",
    "ExecutorContextEvent",
    "ExecutorResponseEvent",
    "ExecutorActionEvent",
    "ExecutorActionResultEvent",
]
