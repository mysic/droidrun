"""Coordinate conversion utilities for normalized [0-1000] coordinates."""

NORMALIZED_MAX = 1000


# 教程注释：把 [0-1000] 相对坐标换算为设备真实像素，供实际点击/滑动动作使用。
def to_absolute(x: int, y: int, width: int, height: int) -> tuple[int, int]:
    """Convert [0-1000] normalized to absolute pixels."""
    if width is None or height is None:
        raise ValueError("Screen dimensions not available. Call get_state() first.")
    return int(x * width / NORMALIZED_MAX), int(y * height / NORMALIZED_MAX)


# 教程注释：把像素坐标反向映射为归一化坐标，便于跨分辨率复用轨迹。
def to_normalized(x: int, y: int, width: int, height: int) -> tuple[int, int]:
    """Convert absolute pixels to [0-1000] normalized."""
    if width is None or height is None:
        raise ValueError("Screen dimensions not available. Call get_state() first.")
    return int(x * NORMALIZED_MAX / width), int(y * NORMALIZED_MAX / height)


def bounds_to_normalized(bounds_str: str, width: int, height: int) -> str:
    """Convert 'left,top,right,bottom' bounds string to normalized."""
    left, top, right, bottom = map(int, bounds_str.split(","))
    n_left, n_top = to_normalized(left, top, width, height)
    n_right, n_bottom = to_normalized(right, bottom, width, height)
    return f"{n_left},{n_top},{n_right},{n_bottom}"
