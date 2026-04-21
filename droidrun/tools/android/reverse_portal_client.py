"""ReversePortalClient — host a local WebSocket endpoint for Portal reverse mode."""

from __future__ import annotations

import asyncio
import base64
import http
import json
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, urlunparse
from uuid import uuid4

from websockets.asyncio.server import Server, ServerConnection, serve
from websockets.exceptions import ConnectionClosed

from droidrun.tools.driver.base import DeviceDisconnectedError

logger = logging.getLogger("droidrun")

PORTAL_REVERSE_DEFAULT_PORT = 8765


def validate_android_portal_reverse_url(
    url: str,
    default_port: int = PORTAL_REVERSE_DEFAULT_PORT,
) -> str:
    """Validate and normalize the reverse WebSocket URL for Portal."""
    normalized = url.strip().rstrip("/")
    if not normalized:
        raise ValueError(
            "Portal reverse URL cannot be empty. Provide a ws://host:port URL."
        )

    if "://" not in normalized:
        normalized = f"ws://{normalized}"

    parsed = urlparse(normalized)
    if parsed.scheme not in {"ws", "wss"} or not parsed.hostname:
        raise ValueError(
            "Portal reverse URL must be a valid ws(s) URL, e.g. ws://0.0.0.0:8765/reverse"
        )

    if parsed.scheme == "wss":
        raise ValueError(
            "Portal reverse mode currently supports ws:// hosts only; wss relays are not implemented yet."
        )

    host = parsed.hostname
    port = parsed.port or default_port
    path = parsed.path or "/"
    query = parsed.query
    return urlunparse((parsed.scheme, f"{host}:{port}", path, "", query, ""))


class ReversePortalClient:
    """Serve a local WebSocket endpoint and talk JSON-RPC with Portal reverse mode."""

    def __init__(
        self,
        listen_url: str,
        auth_token: str | None = None,
        expected_device_id: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.listen_url = validate_android_portal_reverse_url(listen_url)
        parsed = urlparse(self.listen_url)

        self._bind_host = (
            parsed.hostname
            if parsed.hostname in {"127.0.0.1", "localhost", "::1"}
            else "0.0.0.0"
        )
        self._port = parsed.port or PORTAL_REVERSE_DEFAULT_PORT
        self._expected_resource = parsed.path or "/"
        if parsed.query:
            self._expected_resource = f"{self._expected_resource}?{parsed.query}"

        self._auth_token = auth_token
        self._expected_device_id = expected_device_id
        self._timeout = timeout

        self._server: Server | None = None
        self._connection: ServerConnection | None = None
        self._connection_ready = asyncio.Event()
        self._pending: dict[str, asyncio.Future[Any]] = {}

    async def connect(self) -> None:
        if self._server is None:
            self._server = await serve(
                self._handle_connection,
                self._bind_host,
                self._port,
                process_request=self._process_request,
            )
            logger.info(
                "Waiting for Portal reverse connection on %s",
                self.listen_url,
            )

        await self._wait_for_connection()

    async def _process_request(
        self,
        connection: ServerConnection,
        request,
    ):
        if request.path != self._expected_resource:
            return connection.respond(http.HTTPStatus.NOT_FOUND, "Unknown reverse path\n")

        if self._auth_token is not None:
            expected_auth = f"Bearer {self._auth_token}"
            if request.headers.get("Authorization") != expected_auth:
                return connection.respond(http.HTTPStatus.UNAUTHORIZED, "Unauthorized\n")

        if self._expected_device_id is not None:
            if request.headers.get("X-Device-ID") != self._expected_device_id:
                return connection.respond(http.HTTPStatus.FORBIDDEN, "Unexpected device\n")

        return None

    async def _handle_connection(self, connection: ServerConnection) -> None:
        request = connection.request
        headers = request.headers if request is not None else {}
        device_id = headers.get("X-Device-ID")
        device_name = headers.get("X-Device-Name")

        logger.info(
            "Portal reverse connected: device_id=%s device_name=%s path=%s",
            device_id or "unknown",
            device_name or "unknown",
            request.path if request is not None else self._expected_resource,
        )

        previous_connection = self._connection
        self._connection = connection
        self._connection_ready.set()

        if previous_connection is not None and previous_connection is not connection:
            try:
                await previous_connection.close(code=1012, reason="replaced by new reverse session")
            except Exception:
                pass

        try:
            async for message in connection:
                await self._handle_message(message)
        except ConnectionClosed as exc:
            logger.info("Portal reverse disconnected: %s", exc)
        finally:
            if self._connection is connection:
                self._connection = None
                self._connection_ready.clear()
            self._fail_pending(DeviceDisconnectedError("Portal reverse connection closed"))

    async def _handle_message(self, message: str | bytes) -> None:
        if isinstance(message, bytes):
            logger.debug("Ignoring unexpected binary reverse payload (%d bytes)", len(message))
            return

        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            logger.debug("Ignoring non-JSON reverse payload")
            return

        message_id = data.get("id")
        if message_id is None:
            logger.debug("Received reverse notification: %s", data.get("method", "unknown"))
            return

        pending = self._pending.pop(str(message_id), None)
        if pending is None:
            logger.debug("Ignoring reverse response for unknown id=%s", message_id)
            return

        if pending.done():
            return

        if data.get("status") == "error" or "error" in data:
            pending.set_exception(
                ConnectionError(data.get("error") or data.get("message") or str(data))
            )
            return

        pending.set_result(self._unwrap_payload(data))

    def _fail_pending(self, error: Exception) -> None:
        pending = list(self._pending.values())
        self._pending.clear()
        for future in pending:
            if not future.done():
                future.set_exception(error)

    @staticmethod
    def _unwrap_payload(data: Any) -> Any:
        if isinstance(data, dict):
            if "result" in data:
                return data["result"]
            if "data" in data:
                return data["data"]
        return data

    async def _wait_for_connection(self) -> ServerConnection:
        connection = self._connection
        if connection is not None:
            return connection

        try:
            await asyncio.wait_for(self._connection_ready.wait(), timeout=self._timeout)
        except TimeoutError as exc:
            raise ConnectionError(
                "Timed out waiting for Portal reverse connection. "
                "Configure the Portal app to connect to the reverse URL and enable reverse connection."
            ) from exc

        connection = self._connection
        if connection is None:
            raise ConnectionError("Portal reverse connection did not become ready")
        return connection

    async def _request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        connection = await self._wait_for_connection()
        request_id = str(uuid4())
        future: asyncio.Future[Any] = asyncio.get_running_loop().create_future()
        self._pending[request_id] = future

        payload = {
            "id": request_id,
            "method": method,
            "params": params or {},
        }

        try:
            await connection.send(json.dumps(payload))
        except ConnectionClosed as exc:
            self._pending.pop(request_id, None)
            raise DeviceDisconnectedError("Portal reverse connection closed while sending") from exc

        try:
            return await asyncio.wait_for(future, timeout=timeout or self._timeout)
        finally:
            self._pending.pop(request_id, None)

    async def get_state(self) -> Dict[str, Any]:
        data = await self._request("state", {"filter": False})
        if isinstance(data, str):
            return json.loads(data)
        if isinstance(data, dict):
            return data
        raise ConnectionError(f"Unexpected reverse state payload: {type(data).__name__}")

    async def input_text(self, text: str, clear: bool = False) -> bool:
        payload = {
            "base64_text": base64.b64encode(text.encode()).decode(),
            "clear": clear,
        }
        await self._request("keyboard/input", payload)
        return True

    async def take_screenshot(self, hide_overlay: bool = True) -> bytes:
        data = await self._request("screenshot", {"hideOverlay": hide_overlay})
        if isinstance(data, str):
            return base64.b64decode(data)
        raise ConnectionError("Unexpected reverse screenshot payload")

    async def get_apps(self, include_system: bool = True) -> List[Dict[str, str]]:
        packages_data = await self._request("packages")
        if not packages_data:
            return []

        packages_list = None
        if isinstance(packages_data, list):
            packages_list = packages_data
        elif isinstance(packages_data, dict):
            if "packages" in packages_data:
                packages_list = packages_data["packages"]
            else:
                inner_value = self._unwrap_payload(packages_data)
                if isinstance(inner_value, list):
                    packages_list = inner_value
                elif isinstance(inner_value, dict) and "packages" in inner_value:
                    packages_list = inner_value["packages"]

        if not packages_list:
            return []

        apps = []
        for package_info in packages_list:
            if not include_system and package_info.get("isSystemApp", False):
                continue
            apps.append(
                {
                    "package": package_info.get("packageName", ""),
                    "label": package_info.get("label", ""),
                }
            )
        return apps

    async def get_time(self) -> str:
        return str(await self._request("time"))

    async def tap(self, x: int, y: int) -> None:
        await self._request("tap", {"x": x, "y": y})

    async def swipe(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration_ms: float = 1000,
    ) -> None:
        await self._request(
            "swipe",
            {
                "startX": start_x,
                "startY": start_y,
                "endX": end_x,
                "endY": end_y,
                "duration": int(duration_ms),
            },
            timeout=max(self._timeout, duration_ms / 1000 + 2),
        )

    async def perform_global_action(self, action: int) -> Any:
        return await self._request("global", {"action": action})

    async def press_key(self, key_code: int) -> Any:
        return await self._request("keyboard/key", {"key_code": key_code})

    async def start_app(
        self,
        package: str,
        activity: Optional[str] = None,
        stop_before_launch: bool = False,
    ) -> Any:
        payload: Dict[str, Any] = {
            "package": package,
            "stopBeforeLaunch": stop_before_launch,
        }
        if activity:
            payload["activity"] = activity
        return await self._request("app", payload)

    async def stop_app(self, package: str) -> Any:
        return await self._request("app/stop", {"package": package})

    async def get_version(self) -> str:
        return str(await self._request("version"))