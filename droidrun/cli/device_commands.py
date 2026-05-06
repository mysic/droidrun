"""Direct device action CLI commands.

Provides ``droidrun device <action>`` subcommands that bypass the LLM agent
and talk directly to the device driver.
"""

import asyncio
import os
import tempfile
from io import BytesIO
from dataclasses import dataclass
from functools import wraps
from typing import Any, Dict, List, Optional

import click
from PIL import Image, ImageDraw
from rich.console import Console

from droidrun.config_manager import ConfigLoader
from droidrun.tools.helpers.coordinate import NORMALIZED_MAX, to_absolute, to_normalized
from droidrun.tools.driver.factory import create_driver_from_device_config
from droidrun.tools.filters import ConciseFilter
from droidrun.tools.formatters import IndexedFormatter
from droidrun.tools.ui.ios_provider import IOSStateProvider
from droidrun.tools.ui.provider import AndroidStateProvider
from droidrun.tools.ui.state import UIState

console = Console()


def _save_marked_screenshot(png: bytes, source_path: str, x: int, y: int) -> str:
    """Save a copy of the screenshot with the resolved point highlighted."""
    base, ext = os.path.splitext(source_path)
    marked_path = f"{base}_marked{ext or '.png'}"

    image = Image.open(BytesIO(png)).convert("RGBA")
    draw = ImageDraw.Draw(image)
    radius = 20
    draw.ellipse(
        (x - radius, y - radius, x + radius, y + radius),
        outline="red",
        width=5,
    )
    image.save(marked_path)
    return marked_path


@dataclass
class DeviceCommandContext:
    """Runtime context resolved before executing a direct device command."""

    use_normalized_coordinates: bool
    screen_width: Optional[int]
    screen_height: Optional[int]
    ui_state: Optional[UIState] = None

    def convert_point(self, x: int, y: int) -> tuple[int, int]:
        """Resolve input coordinates to absolute device pixels.

        In normalized mode, [0-1000] values are treated as UI-tree normalized.
        If values exceed [0-1000] but fit current screen bounds, treat them as
        absolute pixel coordinates for compatibility with screenshot/device inputs.
        """
        if not self.use_normalized_coordinates:
            return x, y

        if self.screen_width is None or self.screen_height is None:
            raise click.ClickException(
                "agent.use_normalized_coordinates is enabled, but screen resolution "
                "is unavailable. Please ensure UI state is accessible."
            )

        if 0 <= x <= NORMALIZED_MAX and 0 <= y <= NORMALIZED_MAX:
            return to_absolute(x, y, self.screen_width, self.screen_height)

        if 0 <= x <= self.screen_width and 0 <= y <= self.screen_height:
            return x, y

        raise click.ClickException(
            f"Coordinates ({x}, {y}) are neither normalized [0, {NORMALIZED_MAX}] "
            f"nor absolute screen pixels [0, {self.screen_width}] x [0, {self.screen_height}]."
        )

    @staticmethod
    def _iter_elements(elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Flatten UI elements recursively for point hit-testing."""
        result: List[Dict[str, Any]] = []
        for item in elements:
            result.append(item)
            children = item.get("children", []) or []
            if children:
                result.extend(DeviceCommandContext._iter_elements(children))
        return result

    def _find_element_by_point(self, x: int, y: int) -> Optional[Dict[str, Any]]:
        """Find the top-most UI element containing absolute point (x, y)."""
        if not self.ui_state:
            return None

        point_x, point_y = x, y
        if (
            self.use_normalized_coordinates
            and self.screen_width is not None
            and self.screen_height is not None
        ):
            point_x, point_y = to_normalized(x, y, self.screen_width, self.screen_height)

        hit: Optional[Dict[str, Any]] = None
        for element in self._iter_elements(self.ui_state.elements):
            bounds = element.get("bounds")
            if not bounds:
                continue
            try:
                left, top, right, bottom = map(int, bounds.split(","))
            except Exception:
                continue
            if left <= point_x <= right and top <= point_y <= bottom:
                # Later elements tend to be visually on top in this flattened list.
                hit = element
        return hit

    async def resolve_action_point(
        self,
        driver,
        x: int,
        y: int,
        action_name: str,
    ) -> tuple[int, int]:
        """Resolve a command point via UI tree first, with screenshot fallback."""
        abs_x, abs_y = self.convert_point(x, y)
        hit = self._find_element_by_point(abs_x, abs_y)
        if hit is not None:
            idx = hit.get("index", "?")
            text = hit.get("text", "")
            class_name = hit.get("className", "Unknown")
            click.echo(
                f"[{action_name}] UI hit index={idx}, class={class_name}, text={text!r}, point=({abs_x}, {abs_y})"
            )
            return abs_x, abs_y

        # Fallback: no element hit in UI tree -> capture screenshot for analysis.
        fd, path = tempfile.mkstemp(prefix="droidrun_fallback_", suffix=".png")
        try:
            png = await driver.screenshot()
            try:
                os.write(fd, png)
            finally:
                os.close(fd)
            marked_path = _save_marked_screenshot(png, path, abs_x, abs_y)
            click.echo(
                f"[{action_name}] No matching element in UI tree for point ({abs_x}, {abs_y}). "
                f"Fallback screenshot saved: {path}; marked screenshot saved: {marked_path}",
                err=True,
            )
        except Exception as exc:
            try:
                os.close(fd)
            except Exception:
                pass
            click.echo(
                f"[{action_name}] No UI element match and screenshot fallback failed: {exc}",
                err=True,
            )

        return abs_x, abs_y


async def _prepare_device_command_context(
    driver,
    is_ios: bool,
    use_normalized_coordinates: bool,
) -> DeviceCommandContext:
    """Run per-command preflight and read real device resolution/UI state."""
    screen_width: Optional[int] = None
    screen_height: Optional[int] = None
    ui_state: Optional[UIState] = None

    try:
        if is_ios:
            provider = IOSStateProvider(driver, use_normalized=use_normalized_coordinates)
        else:
            provider = AndroidStateProvider(
                driver,
                tree_filter=ConciseFilter(),
                tree_formatter=IndexedFormatter(),
                use_normalized=use_normalized_coordinates,
            )
        ui_state = await provider.get_state()
        screen_width = int(ui_state.screen_width)
        screen_height = int(ui_state.screen_height)
    except Exception as exc:
        click.echo(
            f"Warning: failed to resolve UI state in preflight: {exc}",
            err=True,
        )

        # Best-effort fallback: still try raw state for screen bounds.
        try:
            state = await driver.get_ui_tree()
            if isinstance(state, dict):
                screen_bounds = state.get("device_context", {}).get("screen_bounds", {})
                width = screen_bounds.get("width")
                height = screen_bounds.get("height")
                if width is not None and height is not None:
                    screen_width = int(width)
                    screen_height = int(height)
        except Exception:
            pass

    return DeviceCommandContext(
        use_normalized_coordinates=use_normalized_coordinates,
        screen_width=screen_width,
        screen_height=screen_height,
        ui_state=ui_state,
    )


def coro(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper


def device_options(f):
    """Common device options for all action commands."""
    f = click.option(
        "--device", "-d", help="Device serial number or IP address", default=None
    )(f)
    f = click.option(
        "--config", "-c", "config_path", help="Path to config file", default=None
    )(f)
    f = click.option("--tcp/--no-tcp", default=None, help="Use TCP communication")(f)
    f = click.option(
        "--driver-backend",
        type=click.Choice(["portal", "adb"]),
        default=None,
        help="Android driver backend to use",
    )(f)
    f = click.option(
        "--portal-mode",
        type=click.Choice(["direct", "reverse"]),
        default=None,
        help="Portal connection mode",
    )(f)
    f = click.option(
        "--portal-url",
        default=None,
        help="Portal endpoint URL: http://... for direct mode or ws://... for reverse mode",
    )(f)
    f = click.option(
        "--portal-token",
        default=None,
        help="Direct portal auth token copied from the Portal app",
    )(f)
    f = click.option("--ios", is_flag=True, default=False, help="Target iOS device")(f)
    return f



# 教程注释：_create_driver 是设备直连命令的核心入口，会根据参数和配置选择 Android/iOS driver 并完成连接准备。
async def _create_driver(
    device: Optional[str],
    config_path: Optional[str],
    tcp: Optional[bool],
    driver_backend: Optional[str],
    portal_mode: Optional[str],
    portal_url: Optional[str],
    portal_token: Optional[str],
    ios: bool,
):
    """Create and connect a device driver based on CLI options."""
    config = ConfigLoader.load(config_path)

    if device is not None:
        config.device.serial = device
    if tcp is not None:
        config.device.use_tcp = tcp
    if driver_backend is not None:
        config.device.driver_backend = driver_backend
    if portal_mode is not None:
        config.device.portal_connection_mode = portal_mode
    if portal_url is not None:
        config.device.portal_url = portal_url
    if portal_token is not None:
        config.device.portal_token = portal_token
    if ios:
        config.device.platform = "ios"

    use_normalized_coordinates = bool(config.agent.use_normalized_coordinates)

    try:
        driver, is_ios = await create_driver_from_device_config(
            config.device, debug=False
        )
        context = await _prepare_device_command_context(
            driver,
            is_ios,
            use_normalized_coordinates,
        )
        return driver, is_ios, context
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


async def _teardown_android(driver):
    """Disable Droidrun keyboard after direct command execution."""
    device = getattr(driver, "device", None)
    if device is not None:
        try:
            await device.shell(
                "ime disable com.droidrun.portal/.input.DroidrunKeyboardIME"
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Click group
# ---------------------------------------------------------------------------


# 教程注释：device_cli 命令组提供“绕过 Agent 直接操作设备”的一组调试/运维指令。
@click.group()
def device_cli():
    """Direct device actions (screenshot, tap, swipe, etc.)."""
    pass


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@device_cli.command()
@device_options
@coro
async def screenshot(device, config_path, tcp, driver_backend, portal_mode, portal_url, portal_token, ios):
    """Take a screenshot and print the saved file path to stdout."""
    driver, _, _ = await _create_driver(
        device,
        config_path,
        tcp,
        driver_backend,
        portal_mode,
        portal_url,
        portal_token,
        ios,
    )
    try:
        png_bytes = await driver.screenshot()
        fd, path = tempfile.mkstemp(prefix="droidrun_", suffix=".png")
        try:
            os.write(fd, png_bytes)
        finally:
            os.close(fd)
        click.echo(path)
    finally:
        await _teardown_android(driver)


# 教程注释：ui 命令会抓取并格式化当前无障碍树，便于人工查看索引和 bounds。
@device_cli.command()
@device_options
@coro
async def ui(device, config_path, tcp, driver_backend, portal_mode, portal_url, portal_token, ios):
    """Print the UI accessibility tree with element bounds for targeting."""
    driver, is_ios, context = await _create_driver(
        device,
        config_path,
        tcp,
        driver_backend,
        portal_mode,
        portal_url,
        portal_token,
        ios,
    )
    try:
        if is_ios:
            provider = IOSStateProvider(
                driver,
                use_normalized=context.use_normalized_coordinates,
            )
        else:
            provider = AndroidStateProvider(
                driver,
                tree_filter=ConciseFilter(),
                tree_formatter=IndexedFormatter(),
                use_normalized=context.use_normalized_coordinates,
            )
        state = await provider.get_state()
        click.echo(state.formatted_text)
        if state.phone_state:
            click.echo(f"\nPhone state: {state.phone_state}")
    finally:
        await _teardown_android(driver)


@device_cli.command()
@click.argument("x", type=int)
@click.argument("y", type=int)
@device_options
@coro
async def tap(x, y, device, config_path, tcp, driver_backend, portal_mode, portal_url, portal_token, ios):
    """Tap at screen coordinates.

    If agent.use_normalized_coordinates=true, coordinates are interpreted as
    UI-tree normalized [0-1000] and converted before execution.
    """
    driver, _, context = await _create_driver(
        device,
        config_path,
        tcp,
        driver_backend,
        portal_mode,
        portal_url,
        portal_token,
        ios,
    )
    try:
        tap_x, tap_y = await context.resolve_action_point(driver, x, y, "tap")
        await driver.tap(tap_x, tap_y)
        if context.use_normalized_coordinates:
            click.echo(f"Tapped normalized ({x}, {y}) -> device ({tap_x}, {tap_y})")
        else:
            click.echo(f"Tapped ({tap_x}, {tap_y})")
    finally:
        await _teardown_android(driver)


@device_cli.command("swipe")
@click.argument("x1", type=int)
@click.argument("y1", type=int)
@click.argument("x2", type=int)
@click.argument("y2", type=int)
@click.option(
    "--duration", type=float, default=1.0, show_default=True, help="Duration in seconds"
)
@device_options
@coro
async def swipe_cmd(x1, y1, x2, y2, duration, device, config_path, tcp, driver_backend, portal_mode, portal_url, portal_token, ios):
    """Swipe from (x1, y1) to (x2, y2).

    If agent.use_normalized_coordinates=true, coordinates are interpreted as
    UI-tree normalized [0-1000] and converted before execution.
    """
    driver, _, context = await _create_driver(
        device,
        config_path,
        tcp,
        driver_backend,
        portal_mode,
        portal_url,
        portal_token,
        ios,
    )
    try:
        abs_x1, abs_y1 = await context.resolve_action_point(driver, x1, y1, "swipe:start")
        abs_x2, abs_y2 = await context.resolve_action_point(driver, x2, y2, "swipe:end")
        await driver.swipe(abs_x1, abs_y1, abs_x2, abs_y2, duration_ms=duration * 1000)
        if context.use_normalized_coordinates:
            click.echo(
                f"Swiped normalized ({x1}, {y1}) -> ({x2}, {y2}) -> "
                f"device ({abs_x1}, {abs_y1}) -> ({abs_x2}, {abs_y2})"
            )
        else:
            click.echo(f"Swiped ({abs_x1}, {abs_y1}) -> ({abs_x2}, {abs_y2})")
    finally:
        await _teardown_android(driver)


@device_cli.command("long-press")
@click.argument("x", type=int)
@click.argument("y", type=int)
@device_options
@coro
async def long_press(x, y, device, config_path, tcp, driver_backend, portal_mode, portal_url, portal_token, ios):
    """Long press at screen coordinates.

    If agent.use_normalized_coordinates=true, coordinates are interpreted as
    UI-tree normalized [0-1000] and converted before execution.
    """
    if ios:
        raise click.ClickException("long-press is not supported on iOS")
    driver, _, context = await _create_driver(
        device,
        config_path,
        tcp,
        driver_backend,
        portal_mode,
        portal_url,
        portal_token,
        ios,
    )
    try:
        abs_x, abs_y = await context.resolve_action_point(driver, x, y, "long-press")
        await driver.swipe(abs_x, abs_y, abs_x, abs_y, 1000)
        if context.use_normalized_coordinates:
            click.echo(
                f"Long pressed normalized ({x}, {y}) -> device ({abs_x}, {abs_y})"
            )
        else:
            click.echo(f"Long pressed ({abs_x}, {abs_y})")
    finally:
        await _teardown_android(driver)


@device_cli.command("type")
@click.argument("text")
@click.option("--clear", is_flag=True, default=False, help="Clear field before typing")
@device_options
@coro
async def type_text(text, clear, device, config_path, tcp, driver_backend, portal_mode, portal_url, portal_token, ios):
    """Type text into the currently focused field. Use 'tap' first to focus."""
    driver, _, _ = await _create_driver(
        device,
        config_path,
        tcp,
        driver_backend,
        portal_mode,
        portal_url,
        portal_token,
        ios,
    )
    try:
        success = await driver.input_text(text, clear)
        if success:
            click.echo(f"Typed: {text}")
        else:
            raise click.ClickException("Failed to type text")
    finally:
        await _teardown_android(driver)


@device_cli.command()
@click.argument(
    "button", type=click.Choice(["back", "home", "enter"], case_sensitive=False)
)
@device_options
@coro
async def press(button, device, config_path, tcp, driver_backend, portal_mode, portal_url, portal_token, ios):
    """Press a system button."""
    driver, _, _ = await _create_driver(
        device,
        config_path,
        tcp,
        driver_backend,
        portal_mode,
        portal_url,
        portal_token,
        ios,
    )
    try:
        await driver.press_button(button)
        click.echo(f"Pressed {button}")
    finally:
        await _teardown_android(driver)


@device_cli.command()
@click.option("--system/--no-system", default=False, help="Include system apps")
@device_options
@coro
async def apps(system, device, config_path, tcp, driver_backend, portal_mode, portal_url, portal_token, ios):
    """List installed apps."""
    driver, _, _ = await _create_driver(
        device,
        config_path,
        tcp,
        driver_backend,
        portal_mode,
        portal_url,
        portal_token,
        ios,
    )
    try:
        app_list = await driver.get_apps(include_system=system)
        for app in app_list:
            label = app.get("label", "")
            package = app.get("package", "")
            if label and label != package:
                click.echo(f"{package}  ({label})")
            else:
                click.echo(package)
    finally:
        await _teardown_android(driver)


@device_cli.command()
@click.argument("package")
@device_options
@coro
async def start(package, device, config_path, tcp, driver_backend, portal_mode, portal_url, portal_token, ios):
    """Launch an app by package name."""
    driver, _, _ = await _create_driver(
        device,
        config_path,
        tcp,
        driver_backend,
        portal_mode,
        portal_url,
        portal_token,
        ios,
    )
    try:
        result = await driver.start_app(package)
        click.echo(result)
    finally:
        await _teardown_android(driver)
