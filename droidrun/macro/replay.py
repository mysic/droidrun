"""
Macro Replay Module - Replay recorded UI automation sequences.

This module provides functionality to load and replay macro JSON files
that were generated during DroidAgent trajectory recording.
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from droidrun.agent.utils.trajectory import Trajectory
from droidrun.config_manager.config_manager import DeviceConfig
from droidrun.tools.driver.factory import create_driver_from_device_config

logger = logging.getLogger("droidrun-macro")

# Reverse map for legacy key_press macro entries
_KEYCODE_TO_BUTTON = {4: "back", 3: "home", 66: "enter"}


# 教程注释：MacroPlayer 负责把录制的动作序列回放到设备上，是“可复现自动化”的执行器。
class MacroPlayer:
    """
    A class for loading and replaying Droidrun macro sequences.

    This player can execute recorded UI actions (taps, swipes, text input, key presses)
    on Android devices using the configured backend.
    """

    def __init__(
        self,
        device_serial: str = None,
        delay_between_actions: float = 1.0,
        driver_backend: str = "portal",
        portal_mode: str = "direct",
        portal_url: str | None = None,
        portal_token: str | None = None,
        auto_setup: bool = True,
    ):
        """
        Initialize the MacroPlayer.

        Args:
            device_serial: Serial number of the target device. If None, will use first available device.
            delay_between_actions: Delay in seconds between each action (default: 1.0s)
            driver_backend: Android driver backend to use for replay.
            portal_mode: Portal connection mode when using the portal backend.
            portal_url: Direct portal base URL for no-ADB macro replay.
            portal_token: Direct portal auth token for no-ADB macro replay.
            auto_setup: Whether to auto-setup Portal when ADB is in use.
        """
        self.device_serial = device_serial
        self.delay_between_actions = delay_between_actions
        self.driver_backend = driver_backend
        self.portal_mode = portal_mode
        self.portal_url = portal_url
        self.portal_token = portal_token
        self.auto_setup = auto_setup
        self.driver = None

    async def _initialize_driver(self):
        """Initialize the configured device driver for the target device."""
        if self.driver is None:
            device_config = DeviceConfig(
                serial=self.device_serial,
                platform="android",
                driver_backend=self.driver_backend,
                portal_connection_mode=self.portal_mode,
                portal_url=self.portal_url,
                portal_token=self.portal_token,
                auto_setup=self.auto_setup,
            )
            self.driver, _ = await create_driver_from_device_config(
                device_config,
                debug=logger.isEnabledFor(logging.DEBUG),
            )
            logger.info(
                f"🤖 Initialized {self.driver_backend} driver for device: {self.device_serial or self.portal_url}"
            )
        return self.driver

    def load_macro_from_file(self, macro_file_path: str) -> Dict[str, Any]:
        """
        Load macro data from a JSON file.

        Args:
            macro_file_path: Path to the macro JSON file

        Returns:
            Dictionary containing the macro data
        """
        return Trajectory.load_macro_sequence(macro_file_path)

    def load_macro_from_folder(self, trajectory_folder: str) -> Dict[str, Any]:
        """
        Load macro data from a trajectory folder.

        Args:
            trajectory_folder: Path to the trajectory folder containing macro.json

        Returns:
            Dictionary containing the macro data
        """
        return Trajectory.load_macro_sequence(trajectory_folder)

    # 教程注释：replay_action 按 action_type 分发到对应 driver 调用，是单步动作回放核心。
    async def replay_action(self, action: Dict[str, Any]) -> bool:
        """
        Replay a single action.

        Args:
            action: Action dictionary containing type and parameters

        Returns:
            True if action was executed successfully, False otherwise
        """
        driver = await self._initialize_driver()
        action_type = action.get("action_type", action.get("type", "unknown"))

        try:
            if action_type == "start_app":
                package = action.get("package")
                activity = action.get("activity", None)
                await driver.start_app(package, activity)
                return True

            elif action_type == "tap":
                x = action.get("x", 0)
                y = action.get("y", 0)
                logger.info(f"🫰 Tapping at ({x}, {y})")
                await driver.tap(x, y)
                return True

            elif action_type == "swipe":
                start_x = action.get("start_x", 0)
                start_y = action.get("start_y", 0)
                end_x = action.get("end_x", 0)
                end_y = action.get("end_y", 0)
                duration_ms = action.get("duration_ms", 300)

                logger.info(
                    f"👆 Swiping from ({start_x}, {start_y}) to ({end_x}, {end_y}) in {duration_ms}ms"
                )
                await driver.swipe(start_x, start_y, end_x, end_y, duration_ms)
                # Additional wait after swipe for UI to settle
                await asyncio.sleep(2)
                return True

            elif action_type == "drag":
                start_x = action.get("start_x", 0)
                start_y = action.get("start_y", 0)
                end_x = action.get("end_x", 0)
                end_y = action.get("end_y", 0)
                duration = action.get(
                    "duration", action.get("duration_ms", 300) / 1000.0
                )

                logger.info(
                    f"👆 Dragging from ({start_x}, {start_y}) to ({end_x}, {end_y})"
                )
                await driver.drag(start_x, start_y, end_x, end_y, duration)
                return True

            elif action_type == "input_text":
                text = action.get("text", "")
                clear = action.get("clear", False)
                logger.info(f"⌨️  Inputting text: '{text}'")
                await driver.input_text(text, clear)
                return True

            elif action_type == "key_press":
                keycode = action.get("keycode", 0)
                button = _KEYCODE_TO_BUTTON.get(keycode)
                if button:
                    logger.info(f"🔘 Pressing button: {button}")
                    await driver.press_button(button)
                else:
                    logger.warning(f"⚠️  Unknown keycode {keycode}, skipping")
                return True

            elif action_type == "button_press":
                button = action.get("button", "")
                logger.info(f"🔘 Pressing button: {button}")
                await driver.press_button(button)
                return True

            elif action_type == "back":
                logger.info("⬅️  Pressing back button")
                await driver.press_button("back")
                return True

            elif action_type == "wait":
                duration = action.get("duration", 1.0)
                logger.info(f"⏳ Waiting for {duration} seconds")
                await asyncio.sleep(duration)
                return True

            else:
                logger.warning(f"⚠️  Unknown action type: {action_type}")
                return False

        except Exception as e:
            logger.error(f"❌ Error executing action {action_type}: {e}")
            return False

    # 教程注释：replay_macro 会按顺序执行整段动作并统计成功率，支持从中间步骤开始和限制步数。
    async def replay_macro(
        self,
        macro_data: Dict[str, Any],
        start_from_step: int = 0,
        max_steps: Optional[int] = None,
    ) -> bool:
        """
        Replay a complete macro sequence.

        Args:
            macro_data: Macro data dictionary loaded from JSON
            start_from_step: Step number to start from (0-based, default: 0)
            max_steps: Maximum number of steps to execute (default: all)

        Returns:
            True if all actions were executed successfully, False otherwise
        """
        if not macro_data or "actions" not in macro_data:
            logger.error("❌ Invalid macro data - no actions found")
            return False

        actions = macro_data["actions"]
        description = macro_data.get("description", "Unknown macro")
        total_actions = len(actions)

        # Apply start_from_step and max_steps filters
        if start_from_step > 0:
            actions = actions[start_from_step:]
            logger.info(f"📍 Starting from step {start_from_step + 1}")

        if max_steps is not None:
            actions = actions[:max_steps]
            logger.info(f"🎯 Limiting to {max_steps} steps")

        logger.info(f"🎬 Starting macro replay: '{description}'")
        logger.info(f"📊 Total actions to execute: {len(actions)} / {total_actions}")

        success_count = 0
        failed_count = 0

        for i, action in enumerate(actions, start=start_from_step + 1):
            action_type = action.get("action_type", action.get("type", "unknown"))
            description_text = action.get("description", "")

            logger.info(f"\n📍 Step {i}/{total_actions}: {action_type}")
            if description_text:
                logger.info(f"   Description: {description_text}")

            # Execute the action
            success = await self.replay_action(action)

            if success:
                success_count += 1
                logger.info("   ✅ Action completed successfully")
            else:
                failed_count += 1
                logger.error("   ❌ Action failed")

            # Wait between actions (except for the last one)
            if i < len(actions):
                logger.debug(f"   ⏳ Waiting {self.delay_between_actions}s...")
                await asyncio.sleep(self.delay_between_actions)

        # Summary
        total_executed = success_count + failed_count
        success_rate = (
            (success_count / total_executed * 100) if total_executed > 0 else 0
        )

        logger.info("\n🎉 Macro replay completed!")
        logger.info(
            f"📊 Success: {success_count}/{total_executed} ({success_rate:.1f}%)"
        )

        if failed_count > 0:
            logger.warning(f"⚠️  Failed actions: {failed_count}")

        return failed_count == 0


# Utility functions for convenience


async def replay_macro_file(
    macro_file_path: str,
    device_serial: str = None,
    delay_between_actions: float = 1.0,
    start_from_step: int = 0,
    max_steps: Optional[int] = None,
    driver_backend: str = "portal",
    portal_mode: str = "direct",
    portal_url: str | None = None,
    portal_token: str | None = None,
    auto_setup: bool = True,
) -> bool:
    """
    Convenience function to replay a macro from a file.

    Args:
        macro_file_path: Path to the macro JSON file
        device_serial: Target device serial (optional)
        delay_between_actions: Delay between actions in seconds
        start_from_step: Step to start from (0-based)
        max_steps: Maximum steps to execute
        driver_backend: Android driver backend to use.
        portal_mode: Portal connection mode when using the portal backend.
        portal_url: Direct portal base URL for no-ADB macro replay.
        portal_token: Direct portal auth token for no-ADB macro replay.
        auto_setup: Whether to auto-setup Portal when ADB is in use.

    Returns:
        True if replay was successful, False otherwise
    """
    # 教程注释：文件回放快捷入口，适合脚本或测试场景直接调用。
    player = MacroPlayer(
        device_serial=device_serial,
        delay_between_actions=delay_between_actions,
        driver_backend=driver_backend,
        portal_mode=portal_mode,
        portal_url=portal_url,
        portal_token=portal_token,
        auto_setup=auto_setup,
    )

    try:
        macro_data = player.load_macro_from_file(macro_file_path)
        return await player.replay_macro(
            macro_data, start_from_step=start_from_step, max_steps=max_steps
        )
    except Exception as e:
        logger.error(f"❌ Error replaying macro file {macro_file_path}: {e}")
        return False


async def replay_macro_folder(
    trajectory_folder: str,
    device_serial: str = None,
    delay_between_actions: float = 1.0,
    start_from_step: int = 0,
    max_steps: Optional[int] = None,
    driver_backend: str = "portal",
    portal_mode: str = "direct",
    portal_url: str | None = None,
    portal_token: str | None = None,
    auto_setup: bool = True,
) -> bool:
    """
    Convenience function to replay a macro from a trajectory folder.

    Args:
        trajectory_folder: Path to the trajectory folder containing macro.json
        device_serial: Target device serial (optional)
        delay_between_actions: Delay between actions in seconds
        start_from_step: Step to start from (0-based)
        max_steps: Maximum steps to execute
        driver_backend: Android driver backend to use.
        portal_mode: Portal connection mode when using the portal backend.
        portal_url: Direct portal base URL for no-ADB macro replay.
        portal_token: Direct portal auth token for no-ADB macro replay.
        auto_setup: Whether to auto-setup Portal when ADB is in use.

    Returns:
        True if replay was successful, False otherwise
    """
    # 教程注释：目录回放快捷入口，自动读取轨迹目录中的 macro.json。
    player = MacroPlayer(
        device_serial=device_serial,
        delay_between_actions=delay_between_actions,
        driver_backend=driver_backend,
        portal_mode=portal_mode,
        portal_url=portal_url,
        portal_token=portal_token,
        auto_setup=auto_setup,
    )

    try:
        macro_data = player.load_macro_from_folder(trajectory_folder)
        return await player.replay_macro(
            macro_data, start_from_step=start_from_step, max_steps=max_steps
        )
    except Exception as e:
        logger.error(f"❌ Error replaying macro folder {trajectory_folder}: {e}")
        return False
