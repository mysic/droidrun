"""ActionResult — structured return type from action functions."""

from __future__ import annotations

from dataclasses import dataclass


# 教程注释：ActionResult 是动作层统一的返回对象，上层 Agent 只需要看成功状态和摘要信息即可。
@dataclass
class ActionResult:
    """What the agent sees after an action runs."""

    success: bool
    summary: str

    def __str__(self) -> str:
        return self.summary
