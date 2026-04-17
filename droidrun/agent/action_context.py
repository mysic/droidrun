"""ActionContext — composed bag of dependencies for action functions.

Replaces the ``tools=tools_instance`` parameter that action functions
previously received.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from droidrun.agent.droid.state import DroidAgentState
    from droidrun.credential_manager import CredentialManager
    from droidrun.tools.driver.base import DeviceDriver
    from droidrun.tools.ui.provider import StateProvider
    from droidrun.tools.ui.state import UIState


# 教程注释：ActionContext 把执行动作时需要的依赖打包到一起，避免每个动作函数都传一长串参数。
class ActionContext:
    """Everything an action function needs to interact with the device."""

    def __init__(
        self,
        driver: "DeviceDriver",
        ui: "Optional[UIState]",
        shared_state: "DroidAgentState",
        state_provider: "StateProvider",
        app_opener_llm=None,
        credential_manager: "Optional[CredentialManager]" = None,
        streaming: bool = False,
    ) -> None:
        self.driver = driver
        self.ui = ui  # refreshed each step before tool execution
        self.shared_state = shared_state
        self.state_provider = state_provider
        self.app_opener_llm = app_opener_llm
        self.credential_manager = credential_manager
        self.streaming = streaming
