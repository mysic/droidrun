"""Max number of recent conversation steps to include in LLM prompt"""


# 教程注释：这个常量限制传给模型的历史消息长度，避免上下文无限增长导致成本和噪音上升。
LLM_HISTORY_LIMIT = 100
