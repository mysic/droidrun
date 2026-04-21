"""Driver factory helpers for selecting the correct mobile device driver."""

from __future__ import annotations

from typing import TYPE_CHECKING, Tuple

from async_adbutils import adb

from droidrun.config_manager.config_manager import DeviceConfig
from droidrun.portal import ensure_portal_ready
from droidrun.tools.driver.android import AndroidDriver
from droidrun.tools.driver.ios import IOSDriver, discover_ios_portal, validate_ios_portal_url
from droidrun.tools.driver.portal import PortalDriver

if TYPE_CHECKING:
    from droidrun.tools.driver.base import DeviceDriver


def resolve_portal_direct_url(device_config: DeviceConfig) -> str | None:
    """Resolve the direct Portal URL, including the CLI shorthand using --device."""
    direct_url = device_config.portal_url
    if direct_url is None and device_config.portal_token and device_config.serial:
        direct_url = device_config.serial
    return direct_url


def device_config_uses_adb(device_config: DeviceConfig) -> bool:
    """Return whether the resolved device configuration still depends on ADB."""
    if device_config.platform.lower() == "ios":
        return False

    backend = device_config.driver_backend.lower()
    if backend == "adb":
        return True
    if backend != "portal":
        return False

    if device_config.portal_connection_mode.lower() == "reverse":
        return False

    return resolve_portal_direct_url(device_config) is None


async def create_driver_from_device_config(
    device_config: DeviceConfig,
    debug: bool = False,
) -> Tuple["DeviceDriver", bool]:
    """Create and connect a driver from resolved device configuration."""
    is_ios = device_config.platform.lower() == "ios"
    if is_ios:
        if device_config.serial:
            url = validate_ios_portal_url(device_config.serial)
        else:
            url = await discover_ios_portal()
        driver = IOSDriver(url=url)
        await driver.connect()
        return driver, True

    backend = device_config.driver_backend.lower()
    if backend == "portal":
        connection_mode = device_config.portal_connection_mode.lower()
        if connection_mode == "reverse":
            reverse_url = device_config.portal_url
            if reverse_url is None:
                raise ValueError(
                    "Portal reverse mode requires device.portal_url or --portal-url with a ws:// host URL."
                )

            driver = PortalDriver(
                reverse_url=reverse_url,
                auth_token=device_config.portal_token,
                expected_device_id=device_config.serial,
                timeout=device_config.portal_timeout,
            )
            await driver.connect()
            return driver, False

        if connection_mode != "direct":
            raise ValueError(
                f"Unknown portal connection mode '{device_config.portal_connection_mode}'. "
                "Expected 'direct' or 'reverse'."
            )

        direct_url = resolve_portal_direct_url(device_config)

        if direct_url is not None:
            if not device_config.portal_token:
                raise ValueError(
                    "Portal direct mode requires a portal token. "
                    "Set device.portal_token or pass --portal-token."
                )

            driver = PortalDriver(
                base_url=direct_url,
                auth_token=device_config.portal_token,
                timeout=device_config.portal_timeout,
            )
            await driver.connect()
            return driver, False

        serial = device_config.serial
        if serial is None:
            devices = await adb.list()
            if not devices:
                raise ValueError(
                    "No Android device is available over ADB and no portal_url was configured. "
                    "Set device.portal_url + device.portal_token for no-ADB mode."
                )
            serial = devices[0].serial

        if device_config.auto_setup:
            device_obj = await adb.device(serial=serial)
            await ensure_portal_ready(device_obj, debug=debug)

        driver = PortalDriver(
            serial=serial,
            use_tcp=device_config.use_tcp,
            timeout=device_config.portal_timeout,
        )
        await driver.connect()
        return driver, False

    if backend != "adb":
        raise ValueError(
            f"Unknown Android driver backend '{device_config.driver_backend}'. "
            "Expected 'portal' or 'adb'."
        )

    serial = device_config.serial
    if serial is None:
        devices = await adb.list()
        if not devices:
            raise ValueError("No connected Android devices found.")
        serial = devices[0].serial

    if device_config.auto_setup:
        device_obj = await adb.device(serial=serial)
        await ensure_portal_ready(device_obj, debug=debug)

    driver = AndroidDriver(serial=serial, use_tcp=device_config.use_tcp)
    await driver.connect()
    return driver, False