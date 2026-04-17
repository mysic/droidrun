# 13 Portal 健康检查与 Prompt 解析教程（Portal、Manager、Executor）

承接：第 12 轮讲执行协议层，这一轮聚焦两件与“稳定执行”直接相关的能力：
1. Android 侧 Portal 的自动安装与健康检查。
2. Manager/Executor 两级模型输出的结构化解析。

## 1. 学习目标
1. 理解 SDK 如何自动保证 Portal 可用。
2. 理解 Manager 与 Executor 的响应解析协议。
3. 理解“设备健康层 + 指令解析层”如何共同保障执行稳定性。

## 2. 分析范围
1. `droidrun/portal.py`
2. `droidrun/agent/manager/prompts.py`
3. `droidrun/agent/executor/prompts.py`

## 3. Portal 管理：portal.py
它做什么：
1. 根据 SDK 版本查询兼容 Portal APK 版本并下载。
2. 安装 APK，尝试自动启用 accessibility 服务。
3. 在运行前执行并行健康检查并自动修复（安装/升级/启用服务）。

关键流程：
1. `get_compatible_portal_version`：解析版本映射。
2. `setup_portal`：下载、安装、启用服务、等待可响应。
3. `_wait_for_portal_service`：轮询 content provider，确认服务就绪。
4. `ensure_portal_ready`：并发检查包安装、版本、a11y，必要时自动修复。

教程式理解：
这是一套“前置自愈”机制。相比把错误暴露给最终动作执行，先把基础设施修好能显著提升成功率。

## 4. Manager 解析：manager/prompts.py
它做什么：
1. 从 Manager LLM 的 XML 风格输出中提取 `thought`、`plan`、`memory`、`answer`。
2. 解析任务完成状态 `success`。
3. 从 `plan` 首项提取 `current_subgoal`（支持 script 特殊分支）。

关键点：
1. 通过正则兼容带属性标签，如 `<request_accomplished success="true">`。
2. 兼容 `<answer>` 作为旧格式回退。

## 5. Executor 解析：executor/prompts.py
它做什么：
1. 按 `### Thought`、`### Action`、`### Description` 三段解析模型响应。
2. 对 action 字段提取大括号区间，尽可能保留 JSON 样式内容。

教程式理解：
执行器解析器是“格式纠偏器”：它不保证模型永远格式完美，但会尽力提取可执行信息。

## 6. Python 知识点联动
### 6.1 上下文管理器
项目位置：`portal.py`

作用：
下载 APK 后自动清理临时文件，避免磁盘残留。

### 6.2 `asyncio.gather` 并发检查
项目位置：`portal.py`

作用：
并行执行安装、版本、服务状态检查，缩短健康检测耗时。

### 6.3 正则 + 文本容错解析
项目位置：`manager/prompts.py`

作用：
把松散的自然语言输出转换成结构化字段。

### 6.4 字符串分段协议
项目位置：`executor/prompts.py`

作用：
用稳定分段标题约束模型输出格式，降低执行歧义。

## 7. 源码注释落点
本轮已补充教程注释的位置：
1. `portal.py` 的版本兼容选择、服务等待、总健康检查入口
2. `manager/prompts.py` 的 `parse_manager_response`
3. `executor/prompts.py` 的 `parse_executor_response`

## 8. 证据清单
1. `droidrun/portal.py`：`get_compatible_portal_version`、`setup_portal`、`ensure_portal_ready`
2. `droidrun/agent/manager/prompts.py`：`parse_manager_response`
3. `droidrun/agent/executor/prompts.py`：`parse_executor_response`

## 9. [不确定] 项
1. [不确定] 设备厂商对 accessibility 自动开关命令的限制差异仍可能导致少量设备需手动开启。
2. [不确定] 当模型输出严重偏离协议时，executor 的字符串切分策略仍可能提取到不完整 action。

## 10. 覆盖率与下一轮
### 10.1 本轮已覆盖
1. `droidrun/portal.py`
2. `droidrun/agent/manager/prompts.py`
3. `droidrun/agent/executor/prompts.py`

### 10.2 下一轮建议
1. `droidrun/cli/event_handler.py`（深挖 Rich 展示路径）
2. `droidrun/agent/tool_registry.py`（错误恢复策略与事件发射）
3. `droidrun/agent/utils/signatures.py`（参数签名规范化）

## 11. 小结
这一轮补齐了“前置稳定性”的关键拼图：Portal 自愈确保设备通道可用，Prompt 解析器确保模型输出可执行。两者共同减少了执行链路上的不确定性。