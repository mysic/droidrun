"""UI state and provider abstractions for Droidrun."""

from droidrun.tools.ui.ios_provider import IOSStateProvider
from droidrun.tools.ui.provider import AndroidStateProvider, StateProvider
from droidrun.tools.ui.state import UIState
from droidrun.tools.ui.stealth_state import StealthUIState


# 教程注释：这里集中导出 UI 相关主类型，外部模块无需记住 provider/state 的具体文件位置。
__all__ = [
    "UIState",
    "StealthUIState",
    "StateProvider",
    "AndroidStateProvider",
    "IOSStateProvider",
]
