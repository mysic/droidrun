"""Base interface for tree formatters."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple


# 教程注释：TreeFormatter 规定“格式化器最终必须返回什么”，保证上层总能拿到统一的 UIState 原料。
class TreeFormatter(ABC):
    """Interface for formatting filtered trees."""

    @abstractmethod
    def format(
        self, filtered_tree: Optional[Dict[str, Any]], phone_state: Dict[str, Any]
    ) -> Tuple[str, str, List[Dict[str, Any]], Dict[str, Any]]:
        """Format filtered tree to standard output format.

        Args:
            filtered_tree: Filtered accessibility tree (or None)
            phone_state: Raw phone state dictionary

        Returns:
            Tuple of:
            - formatted_text (str): Complete formatted device state for prompts
            - focused_text (str): Text content of focused element (empty if none)
            - a11y_tree (List[Dict]): Flattened/Processed accessibility tree with indices
            - phone_state (Dict): Raw phone state dict
        """
        pass
