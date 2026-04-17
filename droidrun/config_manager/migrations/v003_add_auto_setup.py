"""Migration v3: Add device.auto_setup field."""

from typing import Any, Dict

VERSION = 3


# 教程注释：这个迁移给 device 配置补上 auto_setup 字段，让老配置也拥有新默认行为。
def migrate(config: Dict[str, Any]) -> Dict[str, Any]:
    """Add auto_setup to device config (defaults to True)."""
    device = config.setdefault("device", {})
    device.setdefault("auto_setup", True)
    return config
