"""
Droidrun main entry point
"""

from droidrun.cli.main import cli


# 教程注释：这里是 Python 包作为命令行程序启动时的最外层入口，只负责把控制权交给 CLI 模块。
if __name__ == "__main__":
    cli()
