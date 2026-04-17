"""
Droidrun Macro Module - Record and replay UI automation sequences.

This module provides functionality to replay macro sequences that were
recorded during DroidAgent execution.
"""

from droidrun.macro.replay import MacroPlayer, replay_macro_file, replay_macro_folder


# 教程注释：这里导出 macro 子系统最常用的回放接口，供 SDK 或其他模块直接调用。
__all__ = ["MacroPlayer", "replay_macro_file", "replay_macro_folder"]
