"""
Entry point for running Droidrun macro CLI as a module.

Usage: python -m droidrun.macro <command>
"""

from droidrun.macro.cli import macro_cli


# 教程注释：模块模式入口，把 `python -m droidrun.macro` 转发到 macro_cli 命令组。
if __name__ == "__main__":
    macro_cli()
