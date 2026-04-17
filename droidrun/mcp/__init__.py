"""MCP client integration for Droidrun."""

from droidrun.mcp.config import MCPConfig, MCPServerConfig
from droidrun.mcp.client import MCPClientManager, MCPToolInfo
from droidrun.mcp.adapter import mcp_to_droidrun_tools


# 教程注释：这里集中导出 MCP 子系统的主配置、管理器和适配函数，方便上层统一接入外部工具。
__all__ = [
    "MCPConfig",
    "MCPServerConfig",
    "MCPClientManager",
    "MCPToolInfo",
    "mcp_to_droidrun_tools",
]
