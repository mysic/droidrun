"""PortalDriver — Android device driver backed by Droidrun Portal APIs.

Supports two connection styles:
- direct HTTP mode using a manually supplied portal URL + token
- reverse WebSocket mode where Portal connects out to a local host
- adb-assisted mode using ADB only to bootstrap Portal connectivity
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from async_adbutils import adb

from droidrun.tools.android.portal_client import PortalClient, validate_android_portal_url
from droidrun.tools.android.reverse_portal_client import ReversePortalClient
from droidrun.tools.driver.base import DeviceDriver

logger = logging.getLogger("droidrun")

ANDROID_GLOBAL_ACTION_BACK = 1
ANDROID_GLOBAL_ACTION_HOME = 2
ANDROID_KEYCODE_ENTER = 66


class PortalDriver(DeviceDriver):
    """Android driver that executes all supported actions through Portal."""

    platform = "Android"

    supported = {
        "tap",
        "swipe",
        "input_text",
        "press_button",
        "start_app",
        "screenshot",
        "get_ui_tree",
        "get_date",
        "get_apps",
        "list_packages",
    }

    supported_buttons = {"back", "home", "enter"}

    def __init__(
        self,
        serial: str | None = None,
        use_tcp: bool = False,
        base_url: str | None = None,
        reverse_url: str | None = None,
        auth_token: str | None = None,
        expected_device_id: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._serial = serial
        self._use_tcp = use_tcp
        self._base_url = validate_android_portal_url(base_url) if base_url else None
        self._reverse_url = reverse_url
        self._auth_token = auth_token
        self._expected_device_id = expected_device_id
        self._timeout = timeout
        self.device = None
        self.portal = None
        self._connected = False

    async def connect(self) -> None:
        if self._connected:
            return

        if self._reverse_url is not None:
            self.portal = ReversePortalClient(
                listen_url=self._reverse_url,
                auth_token=self._auth_token,
                expected_device_id=self._expected_device_id,
                timeout=self._timeout,
            )
            await self.portal.connect()
            self._connected = True
            return

        if self._base_url is not None:
            self.portal = PortalClient(
                base_url=self._base_url,
                auth_token=self._auth_token,
                timeout=self._timeout,
            )
            await self.portal.connect()
            self._connected = True
            return

        self.device = await adb.device(serial=self._serial)
        state = await self.device.get_state()
        if state != "device":
            raise ConnectionError(f"Device is not online. State: {state}")

        self.portal = PortalClient(
            self.device,
            prefer_tcp=self._use_tcp,
            timeout=self._timeout,
        )
        await self.portal.connect()

        from droidrun.portal import setup_keyboard  # circular import guard

        await setup_keyboard(self.device)
        self._connected = True

    async def ensure_connected(self) -> None:
        if not self._connected:
            await self.connect()

    async def tap(self, x: int, y: int) -> None:
        await self.ensure_connected()
        await self.portal.tap(x, y)

    async def swipe(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        duration_ms: float = 1000,
    ) -> None:
        await self.ensure_connected()
        await self.portal.swipe(x1, y1, x2, y2, duration_ms)

    async def input_text(
        self,
        text: str,
        clear: bool = False,
        stealth: bool = False,
        wpm: int = 0,
    ) -> bool:
        await self.ensure_connected()
        return await self.portal.input_text(text, clear)

    async def press_button(self, button: str) -> None:
        await self.ensure_connected()
        button_lower = button.lower()
        if button_lower not in self.supported_buttons:
            raise ValueError(
                f"Button '{button}' not supported. "
                f"Supported: {', '.join(sorted(self.supported_buttons))}"
            )

        if button_lower == "back":
            await self.portal.perform_global_action(ANDROID_GLOBAL_ACTION_BACK)
        elif button_lower == "home":
            await self.portal.perform_global_action(ANDROID_GLOBAL_ACTION_HOME)
        else:
            await self.portal.press_key(ANDROID_KEYCODE_ENTER)

    async def drag(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        duration: float = 3.0,
    ) -> None:
        await self.ensure_connected()
        raise NotImplementedError("Drag is not implemented yet")

    async def start_app(self, package: str, activity: Optional[str] = None) -> str:
        await self.ensure_connected()
        result = await self.portal.start_app(package, activity)
        if isinstance(result, (dict, list)):
            return json.dumps(result)
        return str(result)

    async def install_app(self, path: str, **kwargs) -> str:
        raise NotImplementedError(
            "App installation is not available through PortalDriver yet"
        )

    async def get_apps(self, include_system: bool = True) -> List[Dict[str, str]]:
        await self.ensure_connected()
        return await self.portal.get_apps(include_system)

    async def list_packages(self, include_system: bool = False) -> List[str]:
        apps = await self.get_apps(include_system=include_system)
        return [app["package"] for app in apps if app.get("package")]

    async def screenshot(self, hide_overlay: bool = True) -> bytes:
        await self.ensure_connected()
        return await self.portal.take_screenshot(hide_overlay)

    async def get_ui_tree(self) -> Dict[str, Any]:
        await self.ensure_connected()
        return await self.portal.get_state()

    async def get_date(self) -> str:
        await self.ensure_connected()
        return await self.portal.get_time()