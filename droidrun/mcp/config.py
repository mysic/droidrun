"""MCP configuration models."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# 教程注释：MCPServerConfig 描述单个外部 MCP 服务如何启动、暴露哪些工具、是否加名前缀等信息。
@dataclass
class MCPServerConfig:
    """Configuration for a single MCP server."""

    command: str = ""
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    prefix: Optional[str] = None
    enabled: bool = True
    include_tools: Optional[List[str]] = None
    exclude_tools: List[str] = field(default_factory=list)



# 教程注释：MCPConfig 是 MCP 子系统的总配置入口，决定是否启用以及有哪些 server 参与。
@dataclass
class MCPConfig:
    """MCP client configuration."""

    enabled: bool = False
    servers: Dict[str, MCPServerConfig] = field(default_factory=dict)
