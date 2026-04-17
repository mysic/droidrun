"""
Manager Agent - Planning and reasoning workflow.

Two variants available:
- ManagerAgent: Stateful, maintains chat history
- StatelessManagerAgent: Stateless, rebuilds context each turn
"""

from droidrun.agent.droid.events import ManagerInputEvent, ManagerPlanEvent
from droidrun.agent.manager.events import (
    ManagerContextEvent,
    ManagerPlanDetailsEvent,
    ManagerResponseEvent,
)
from droidrun.agent.manager.manager_agent import ManagerAgent
from droidrun.agent.manager.stateless_manager_agent import StatelessManagerAgent
from droidrun.agent.manager.prompts import parse_manager_response


# 教程注释：这个包入口把 Manager 相关的主类和事件统一导出，方便外部只通过 manager 包访问规划子系统。
__all__ = [
    "ManagerAgent",
    "StatelessManagerAgent",
    "ManagerInputEvent",
    "ManagerPlanEvent",
    "ManagerContextEvent",
    "ManagerResponseEvent",
    "ManagerPlanDetailsEvent",
    "parse_manager_response",
]
