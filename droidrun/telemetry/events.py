"""
Telemetry event models for Droidrun analytics.

This module defines Pydantic models for telemetry events captured during
agent execution. All events inherit from TelemetryEvent base class.
"""

from typing import Dict, Optional

from pydantic import BaseModel  # type: ignore[import-not-found]


# 教程注释：TelemetryEvent 是所有统计事件的基类，后续的初始化、访问包、收尾事件都继承它。
class TelemetryEvent(BaseModel):
    """Base class for all telemetry events."""

    pass


class DroidAgentInitEvent(TelemetryEvent):
    """Event captured when DroidAgent is initialized."""

    # 教程注释：初始化事件记录运行配置快照，便于从统计侧分析模型、工具、视觉与 tracing 配置分布。
    goal: str
    llms: Dict[str, str]
    tools: str
    max_steps: int
    timeout: int
    vision: Dict[str, bool]
    reasoning: bool
    enable_tracing: bool
    debug: bool
    save_trajectories: str = "none"
    runtype: str = "developer"  # "cli" | "developer" | "web"
    custom_prompts: Optional[Dict[str, str]] = (
        None  # Keys: prompt names, Values: "custom" or None
    )


class PackageVisitEvent(TelemetryEvent):
    """Event captured when agent visits a new app package."""

    # 教程注释：访问包事件用于重建任务跨应用流转路径，辅助理解真实使用场景覆盖面。
    package_name: str
    activity_name: str
    step_number: int


class DroidAgentFinalizeEvent(TelemetryEvent):
    """Event captured when DroidAgent execution completes."""

    # 教程注释：收尾事件聚合成功结果与唯一应用访问数，是任务级效果统计的核心指标。
    success: bool
    reason: str
    steps: int
    unique_packages_count: int
    unique_activities_count: int
