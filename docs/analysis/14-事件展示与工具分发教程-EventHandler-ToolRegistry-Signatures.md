# 14 事件展示与工具分发教程（EventHandler、ToolRegistry、Signatures）

承接：第 13 轮补了“设备可用性 + Prompt 解析”，这一轮继续往执行主链中间层下钻，聚焦三块：
1. 事件如何被展示层消费。
2. 工具如何注册、筛选、执行和回传。
3. 内置工具清单如何按平台和能力动态构建。

## 1. 学习目标
1. 理解事件从 workflow 到 CLI/TUI 展示的转换路径。
2. 理解 `ToolRegistry.execute` 的统一分发与错误归一策略。
3. 理解 `build_tool_registry` 如何按平台/能力动态暴露工具。

## 2. 分析范围
1. `droidrun/cli/event_handler.py`
2. `droidrun/agent/tool_registry.py`
3. `droidrun/agent/utils/signatures.py`

## 3. 展示适配层：event_handler.py
它做什么：
1. 接收 workflow 各类事件对象。
2. 根据事件类型翻译为统一日志输出（带颜色、摘要、状态）。
3. 保持 CLI/TUI/SDK 共用同一事件语义，不耦合具体 UI 组件。

关键点：
1. `handle()` 用 `isinstance` 分发到 manager / executor / fast_agent / droid 协调事件。
2. 对超长文本会做 preview 截断，避免日志刷屏。
3. 未识别事件走 fallback，保证新增事件不会静默丢失。

## 4. 执行分发层：tool_registry.py
它做什么：
1. 统一注册工具元数据（参数、描述、依赖能力）。
2. 依据 capability 做工具裁剪。
3. 执行工具并把不同返回形态归一到 `ActionResult`。
4. 可选向 workflow 发射 `ToolExecutionEvent`。

关键流程：
1. `register` / `register_from_dict`：写入工具表。
2. `disable_unsupported`：基于 `deps` 与设备能力裁剪。
3. `execute`：处理未知工具、参数错误、运行异常、返回值归一。
4. `_emit_event`：把执行结果回推到事件流。

教程式理解：
`ToolRegistry` 是“动作网关”。模型说“我要点哪里”，网关负责确认“现在能不能点、怎么点、失败怎么表达”。

## 5. 工具构建层：agent/utils/signatures.py
它做什么：
1. 组装系统内置动作（click/type/swipe/open_app/...）。
2. 按平台差异注册不同 `open_app` 实现（Android 文本名 vs iOS bundle id）。
3. 在有密钥时动态注册 `type_secret`。
4. 返回 `standard_tool_names`，用于上层提示词去重。

关键点：
1. 这是“单一注册入口”，避免工具定义散落多处。
2. 通过 `supported_buttons` 动态生成系统按键描述，提高提示词与设备一致性。

## 6. Python 知识点联动
### 6.1 dataclass + typed dict 风格注册
项目位置：`tool_registry.py`

作用：
让工具元数据结构固定、可序列化、可安全拼接到提示词。

### 6.2 协程与同步函数统一执行
项目位置：`tool_registry.py`

作用：
通过 `inspect.iscoroutinefunction` 统一 await/直调路径。

### 6.3 运行时能力裁剪
项目位置：`tool_registry.py`、`signatures.py`

作用：
让模型只看到“当前设备真的能做的事”，降低幻觉调用。

## 7. 源码注释落点
本轮已补充教程注释的位置：
1. `event_handler.py` 的 fallback 事件处理
2. `tool_registry.py` 的注册迁移、能力裁剪、签名输出入口
3. `signatures.py` 的 `type_secret` 动态注册逻辑

## 8. 证据清单
1. `droidrun/cli/event_handler.py`：`EventHandler.handle`
2. `droidrun/agent/tool_registry.py`：`disable_unsupported`、`execute`、`get_tool_descriptions_xml`
3. `droidrun/agent/utils/signatures.py`：`build_tool_registry`

## 9. [不确定] 项
1. [不确定] 当前字符串前缀规则（例如 `result.startswith("Failed")`）在新增工具返回格式时是否仍稳健。
2. [不确定] 事件展示层在高频工具调用场景下是否需要节流或聚合展示策略。

## 10. 覆盖率与下一轮
### 10.1 本轮已覆盖
1. `droidrun/cli/event_handler.py`
2. `droidrun/agent/tool_registry.py`
3. `droidrun/agent/utils/signatures.py`

### 10.2 下一轮建议
1. `droidrun/agent/external/*`（外部动作与集成边界）
2. `droidrun/agent/fast_agent/*`（XML 工具调用解析和失败恢复）
3. `droidrun/telemetry/tracker.py`（事件上报汇聚路径）

## 11. 小结
这一轮把“工具执行中枢”讲清楚了：事件层负责把系统状态翻译给用户看，ToolRegistry 负责把模型意图变成可执行动作，signatures 构建层负责把可用动作集准确暴露给模型。