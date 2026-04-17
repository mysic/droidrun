# 12 动作协议与 MCP 配置教程（ActionContext、ActionResult、CommonEvents）

承接：上一轮讲完 provider 选择和运行观测，这一轮回到“动作执行协议本身”，以及你当前打开的 MCP 配置模型，帮助你把执行层接口串成一张图。

## 1. 学习目标
1. 理解动作函数的输入协议 `ActionContext`。
2. 理解动作函数的输出协议 `ActionResult`。
3. 理解 common 事件对象如何在 workflow 内传递截图、UI 与工具执行结果。
4. 理解 MCP 配置模型如何描述外部工具服务。

## 2. 分析范围
1. `droidrun/agent/action_context.py`
2. `droidrun/agent/action_result.py`
3. `droidrun/agent/common/constants.py`
4. `droidrun/agent/common/events.py`
5. `droidrun/mcp/config.py`

## 3. 输入协议：action_context.py
它做什么：
1. 用 `ActionContext` 把动作执行依赖一次性打包。
2. 统一包含 driver、UI 快照、共享状态、state provider、可选 app opener llm、凭据管理器等。

教程式理解：
`ActionContext` 相当于“依赖注入容器的轻量版本”。动作函数不关心这些依赖如何创建，只消费当前上下文。

## 4. 输出协议：action_result.py
它做什么：
1. 用 `ActionResult(success, summary)` 表达动作结果。
2. 定义 `__str__` 返回 `summary`，让日志和展示层可直接打印。

教程式理解：
动作层与调度层之间只约定“是否成功 + 摘要”，这是一种稳定接口，能降低上游对具体动作实现的耦合。

## 5. common 常量与事件：agent/common
### 5.1 constants.py
1. `LLM_HISTORY_LIMIT = 100`：限制模型提示词中注入的历史步骤数量。
2. 目标是控制上下文体积与成本，避免历史过长引发噪音。

### 5.2 events.py
1. `ScreenshotEvent`：在 workflow 节点间传递截图二进制。
2. `RecordUIStateEvent`：传递结构化 UI 元素列表。
3. `ToolExecutionEvent`：记录工具调用名称、参数、成功状态和摘要。

教程式理解：
这些事件类是 workflow 内部“消息总线协议”，用类型化字段约束节点间通信。

## 6. MCP 配置模型：mcp/config.py
它做什么：
1. `MCPServerConfig` 描述单个 MCP 服务：命令、参数、环境变量、工具过滤、前缀等。
2. `MCPConfig` 描述 MCP 全局配置：是否启用、有哪些 server。

关键点：
1. `include_tools` 与 `exclude_tools` 提供白名单/黑名单控制。
2. `prefix` 允许同名工具做命名空间隔离。

## 7. Python 知识点联动
### 7.1 dataclass 作为协议对象
项目位置：`action_result.py`、`mcp/config.py`

作用：
用声明式字段表达“数据契约”，方便序列化、检查和文档化。

### 7.2 类型注解与前向引用
项目位置：`action_context.py`

作用：
在不引入运行时循环依赖的前提下，保持 IDE 和静态检查可读性。

### 7.3 事件驱动建模
项目位置：`agent/common/events.py`

作用：
把执行流程拆成可观测、可组合的消息流。

## 8. 源码注释落点
本轮已补充教程注释的位置：
1. `action_context.py` 的 `ActionContext`
2. `action_result.py` 的 `ActionResult`
3. `constants.py` 的 `LLM_HISTORY_LIMIT`
4. `events.py` 的三个事件类
5. `mcp/config.py` 的 `MCPServerConfig` 与 `MCPConfig`

## 9. 证据清单
1. `droidrun/agent/action_context.py`：`ActionContext`
2. `droidrun/agent/action_result.py`：`ActionResult`
3. `droidrun/agent/common/constants.py`：`LLM_HISTORY_LIMIT`
4. `droidrun/agent/common/events.py`：`ScreenshotEvent`、`ToolExecutionEvent`
5. `droidrun/mcp/config.py`：`MCPServerConfig`、`MCPConfig`

## 10. [不确定] 项
1. [不确定] `ActionResult` 是否需要扩展错误码或结构化 payload，取决于后续 UI 展示需求。
2. [不确定] MCP 工具过滤在 server 热更新场景下的行为是否与静态启动一致，建议补集成测试。

## 11. 覆盖率与下一轮
### 11.1 本轮已覆盖
1. `droidrun/agent/action_context.py`
2. `droidrun/agent/action_result.py`
3. `droidrun/agent/common/constants.py`
4. `droidrun/agent/common/events.py`
5. `droidrun/mcp/config.py`

### 11.2 下一轮建议
1. `droidrun/portal.py`
2. `droidrun/agent/manager/prompts.py`
3. `droidrun/agent/executor/prompts.py`

## 12. 小结
这一轮把执行协议层讲清楚了：动作函数通过 `ActionContext` 接收依赖，通过 `ActionResult` 回传结果；workflow 通过事件对象在节点间传递状态；MCP 通过 dataclass 配置模型声明外部工具服务接入规则。