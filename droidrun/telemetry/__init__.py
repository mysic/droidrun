from droidrun.telemetry.events import (
    DroidAgentFinalizeEvent,
    DroidAgentInitEvent,
    PackageVisitEvent,
)
from droidrun.telemetry.tracker import capture, flush, print_telemetry_message


# 教程注释：这里把遥测模块对外开放的主函数和事件类型集中导出，外部无需关心 tracker 等内部文件结构。
__all__ = [
    "capture",
    "flush",
    "DroidAgentInitEvent",
    "PackageVisitEvent",
    "DroidAgentFinalizeEvent",
    "print_telemetry_message",
]
