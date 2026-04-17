"""Custom input widget with command history and slash detection."""

from __future__ import annotations

from textual.widgets import Input
from textual.message import Message
from textual import events


class InputBar(Input):

    class Submitted(Message):
        def __init__(self, value: str) -> None:
            super().__init__()
            self.value = value

    class SlashChanged(Message):
        def __init__(self, query: str) -> None:
            super().__init__()
            self.query = query

    class SlashExited(Message):
        pass

    class SlashSelect(Message):
        """Enter pressed while dropdown is visible."""

        pass

    class SlashNavigate(Message):
        """Up/Down pressed while dropdown is visible."""

        def __init__(self, direction: int) -> None:
            super().__init__()
            self.direction = direction

    class TabPressed(Message):
        pass

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._history: list[str] = []
        self._history_index: int = -1
        self._was_slash: bool = False
        self.slash_mode: bool = False

    @property
    def history(self) -> list[str]:
        return list(self._history)

    # 教程注释：这里重写按键处理，把 Tab、方向键、Enter 从普通输入框语义改造成命令历史和斜杠菜单控制语义。
    def _on_key(self, event: events.Key) -> None:
        if event.key == "tab":
            event.prevent_default()
            event.stop()
            self.post_message(self.TabPressed())
            return

        if self.slash_mode:
            if event.key == "enter":
                event.prevent_default()
                event.stop()
                self.post_message(self.SlashSelect())
                return
            elif event.key in ("up", "down"):
                event.prevent_default()
                event.stop()
                direction = -1 if event.key == "up" else 1
                self.post_message(self.SlashNavigate(direction))
                return

        if event.key == "up":
            event.prevent_default()
            event.stop()
            self._navigate_history(-1)
            return
        elif event.key == "down":
            event.prevent_default()
            event.stop()
            self._navigate_history(1)
            return
        elif event.key == "enter":
            event.prevent_default()
            event.stop()
            self._submit()
            return

        super()._on_key(event)

    # 教程注释：输入历史导航和 shell 类似，便于反复试运行同一条命令或快速微调参数。
    def _navigate_history(self, direction: int) -> None:
        if not self._history:
            return

        if direction == -1:
            if self._history_index == -1:
                self._history_index = len(self._history) - 1
            elif self._history_index > 0:
                self._history_index -= 1
            else:
                return
        else:
            if self._history_index == -1:
                return
            elif self._history_index < len(self._history) - 1:
                self._history_index += 1
            else:
                self._history_index = -1
                self.value = ""
                return

        self.value = self._history[self._history_index]
        self.cursor_position = len(self.value)

    # 教程注释：提交时既发送消息，也把当前命令写入历史，形成输入组件与上层 App 的事件桥接点。
    def _submit(self) -> None:
        text = self.value.strip()
        if not text:
            return

        if not self._history or self._history[-1] != text:
            self._history.append(text)
        self._history_index = -1

        self.post_message(self.Submitted(text))
        self.value = ""

    # 教程注释：watch_value 用 Textual 的响应式钩子检测是否进入斜杠模式，并通知下拉命令面板更新候选项。
    def watch_value(self, value: str) -> None:
        is_slash = value.startswith("/")

        if is_slash:
            query = value[1:]
            self.post_message(self.SlashChanged(query))
            self._was_slash = True
        elif self._was_slash:
            self.post_message(self.SlashExited())
            self._was_slash = False

    def clear_input(self) -> None:
        self.value = ""
        self._history_index = -1
