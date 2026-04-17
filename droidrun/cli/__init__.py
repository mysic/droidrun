"""
Droidrun CLI Module.

This module provides command-line interfaces for interacting with Android devices.
"""

from droidrun.cli.main import cli


# 教程注释：包级导出 CLI 主入口，外部可直接通过 droidrun.cli 引用命令组。
__all__ = ["cli"]
