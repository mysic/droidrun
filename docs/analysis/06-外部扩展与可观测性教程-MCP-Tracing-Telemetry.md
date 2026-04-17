# 06 外部扩展与可观测性教程（MCP、Tracing、Telemetry）

承接：前几轮已经把核心执行链、动作系统、事件系统拆开了。这一轮讲两件偏“工程化”的能力：第一，Droidrun 如何接入外部 MCP 工具；第二，它如何记录 tracing 和 telemetry 来帮助观察执行过程。

## 1. 学习目标
1. 理解 MCP 工具为什么能被当成 Droidrun 自定义工具使用。
2. 理解 tracing 和 telemetry 的区别。
3. 看懂 tracing provider 是如何按配置切换 Phoenix / Langfuse 的。
4. 理解 telemetry event 模型如何配合 tracker 记录关键运行数据。

## 2. 分析范围
1. `droidrun/mcp/adapter.py`
2. `droidrun/mcp/client.py`
3. `droidrun/mcp/config.py`
4. `droidrun/mcp/__init__.py`
5. `droidrun/agent/utils/tracing_setup.py`
6. `droidrun/telemetry/events.py`
7. `droidrun/telemetry/phoenix.py`
8. `droidrun/telemetry/langfuse_processor.py`

## 3. 先区分两个概念
1. Telemetry 更像“埋点统计”，关心启动次数、访问过哪些包、最终是否成功。
2. Tracing 更像“链路追踪”，关心某一次执行里每个步骤、每个 span 怎么发生。

## 4. MCP：外部工具如何接入 Droidrun
### 4.1 MCPConfig：定义要连哪些服务器
文件：`droidrun/mcp/config.py`

它做什么：
1. 定义单个 MCP 服务器的命令、参数、环境变量、启用状态。
2. 定义全局 MCP 是否启用以及服务器列表。

### 4.2 MCPClientManager：发现工具、懒连接、调用工具
文件：`droidrun/mcp/client.py`

它做什么：
1. 扫描所有已配置 MCP server 的工具 schema。
2. 缓存这些工具元数据。
3. 真正调用某个工具时才建立持久连接。
4. 任务结束时统一断开连接。

教程式理解：
这像一个“外部插件管理器”。它先做发现，再按需连接，最后统一清理。

### 4.3 adapter.py：把 MCP 工具翻译成 Droidrun 工具
文件：`droidrun/mcp/adapter.py`

它做什么：
1. 把 MCP 的 JSON Schema 参数格式转换成 Droidrun 的参数定义格式。
2. 给每个 MCP 工具包一层 wrapper。
3. 让上层 Agent 看起来就像在调用普通 Droidrun tool。

最关键的一点：
MCP 工具并不是特殊对待，而是被“适配”成和内置工具一致的接口。

## 5. Tracing：链路追踪如何初始化
### 5.1 tracing_setup.py：总入口
文件：`droidrun/agent/utils/tracing_setup.py`

它做什么：
1. 根据 `TracingConfig` 判断是否启用 tracing。
2. 根据 provider 选择 Phoenix 或 Langfuse。
3. 维护 session_id、user_id 和初始化状态。
4. 为截图等特殊内容补充 tracing span。

关键函数：
1. `setup_tracing`
2. `_setup_phoenix_tracing`
3. `_setup_langfuse_tracing`
4. `apply_session_context`
5. `record_langfuse_screenshot`

### 5.2 Phoenix：LlamaIndex 追踪接入
文件：`droidrun/telemetry/phoenix.py`

它做什么：
1. 创建 Phoenix callback handler。
2. 建立 OpenTelemetry exporter。
3. 为 LlamaIndex 调用与工作流执行生成 trace。

### 5.3 Langfuse：更复杂的 span 处理器
文件：`droidrun/telemetry/langfuse_processor.py`

它做什么：
1. 自定义 span processor。
2. 支持图片上传、内容转换、线程池上传。
3. 从 `DroidAgent` 提取上下文信息补充到 trace 中。

教程式理解：
如果说 Phoenix 更像“标准 tracing 接入”，Langfuse 这里就是“定制增强版 tracing 后处理器”。

## 6. Telemetry：统计事件如何建模
### 6.1 telemetry/events.py
它做什么：
1. 定义 `TelemetryEvent` 基类。
2. 定义初始化、访问包、收尾等统计事件模型。

关键事件：
1. `DroidAgentInitEvent`
2. `PackageVisitEvent`
3. `DroidAgentFinalizeEvent`

教程式理解：
这些类更像“统计报表里的结构化记录”，不是工作流事件，不负责驱动流程，只负责记录数据。

## 7. 整体关系图
```text
配置
-> setup_tracing()
-> Phoenix / Langfuse 初始化
-> LLM / Agent 运行时产生 trace

同时

DroidAgentState / 运行流程
-> capture(TelemetryEvent)
-> tracker / PostHog 统计

同时

MCPConfig
-> MCPClientManager discover_tools()
-> adapter 转成 Droidrun tool
-> Agent 像调用普通工具一样调用 MCP 工具
```

## 8. Python 知识点联动
### 8.1 `@dataclass`
项目位置：`MCPToolInfo`、MCP 配置模型。

作用：
快速定义轻量配置与元数据对象。

### 8.2 懒初始化
项目位置：`MCPClientManager._connect_server`、`setup_tracing`

作用：
只有真正需要时才建立连接或初始化 provider，减少启动成本。

### 8.3 全局模块状态
项目位置：`tracing_setup.py` 中 `_tracing_initialized`、`_session_id` 等。

作用：
记录 tracing 是否已经初始化，避免重复 setup。

### 8.4 ContextVar
项目位置：`langfuse_processor.py`

作用：
在并发环境里安全保存当前 Agent、root span、last step span 上下文。

## 9. 源码注释落点
本轮已补充教程注释的位置：
1. MCP 配置、管理器和适配器关键类/函数
2. tracing 初始化入口和 provider 分支
3. telemetry 事件模型入口
4. Phoenix 和 Langfuse 处理器关键入口

## 10. 证据清单
1. `droidrun/mcp/config.py`：`MCPConfig`、`MCPServerConfig`
2. `droidrun/mcp/client.py`：`MCPClientManager.discover_tools`、`call_tool`
3. `droidrun/mcp/adapter.py`：`mcp_to_droidrun_tools`
4. `droidrun/agent/utils/tracing_setup.py`：`setup_tracing`、`record_langfuse_screenshot`
5. `droidrun/telemetry/events.py`：`DroidAgentInitEvent`、`PackageVisitEvent`
6. `droidrun/telemetry/phoenix.py`：`arize_phoenix_callback_handler`
7. `droidrun/telemetry/langfuse_processor.py`：`LangfuseSpanProcessor`

## 11. [不确定] 项
1. [不确定] 某些 Langfuse 上传分支的完整失败恢复逻辑还未通读到底层所有私有方法。
2. [不确定] MCP server 断线重连策略是否在上层有额外保护，还未全局搜索所有调用点。

## 12. 覆盖率与下一轮
### 12.1 本轮已覆盖
1. `droidrun/mcp/config.py`
2. `droidrun/mcp/client.py`
3. `droidrun/mcp/adapter.py`
4. `droidrun/mcp/__init__.py`
5. `droidrun/agent/utils/tracing_setup.py`
6. `droidrun/telemetry/events.py`
7. `droidrun/telemetry/phoenix.py`
8. `droidrun/telemetry/langfuse_processor.py`

### 12.2 下一轮建议
1. `droidrun/config_manager/config_manager.py`
2. `droidrun/config_manager/prompt_loader.py`
3. `droidrun/config_manager/path_resolver.py`
4. `droidrun/config_manager/migrations/*`

## 13. 小结
这一轮补齐了两个很工程化的能力：一是如何把外部 MCP server 变成 Droidrun 工具，二是如何通过 tracing 和 telemetry 观察系统运行。到这里，你已经不只是理解“它怎么跑”，也开始理解“它怎么扩展”和“它怎么被观察”。