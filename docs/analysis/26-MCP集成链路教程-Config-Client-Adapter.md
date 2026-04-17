# 26 MCP 集成链路教程（Config、Client、Adapter）

承接：第 25 轮讲了 trajectory 异步写入，这一轮回到扩展能力接入层，梳理 MCP 从配置到工具调用的完整链路。

## 1. 学习目标
1. 理解 MCP 配置模型如何描述 server 与工具过滤规则。
2. 理解 MCPClientManager 如何发现工具、懒连接并执行调用。
3. 理解 adapter 如何把 MCP 工具转换为 Droidrun 可注册工具。

## 2. 分析范围
1. droidrun/mcp/config.py
2. droidrun/mcp/client.py
3. droidrun/mcp/adapter.py
4. droidrun/mcp/__init__.py

## 3. 配置层：mcp/config.py
它做什么：
1. `MCPServerConfig` 描述 server 启动参数与工具过滤策略。
2. `MCPConfig` 描述 MCP 全局开关及 server 集合。

关键点：
1. `include_tools` + `exclude_tools` 支持白/黑名单组合。
2. `prefix` 支持工具命名空间隔离，避免重名冲突。

## 4. 管理层：mcp/client.py
它做什么：
1. `discover_tools` 扫描启用 server，拉取工具 schema。
2. `call_tool` 在首次调用时懒连接 server，并转发工具调用。
3. `disconnect_all` 统一关闭连接与资源。

关键流程：
1. 发现阶段用临时连接拿元数据（低驻留成本）。
2. 调用阶段建立持久会话（减少反复握手）。
3. 工具名通过 `MCPToolInfo` 维护 server_name/original_name 映射。

## 5. 适配层：mcp/adapter.py
它做什么：
1. `schema_to_parameters` 把 JSON Schema 转为 Droidrun 参数定义。
2. `mcp_to_droidrun_tools` 为每个 MCP 工具创建异步 wrapper。
3. wrapper 统一提取文本输出，返回给上层 Agent。

教程式理解：
Adapter 是“协议翻译器”：把 MCP 世界的工具描述与返回对象，转成 Droidrun 的工具契约。

## 6. 导出层：mcp/__init__.py
它做什么：
1. 统一导出 config/client/adapter 关键类型与函数。
2. 让上层接入时只依赖单入口模块。

## 7. Python 知识点联动
### 7.1 懒初始化
项目位置：droidrun/mcp/client.py

作用：
延迟建立连接到真正需要调用时，降低空闲资源成本。

### 7.2 协议适配
项目位置：droidrun/mcp/adapter.py

作用：
在不修改上层业务代码的前提下，接入外部工具生态。

### 7.3 元数据缓存
项目位置：MCPToolInfo + _tools

作用：
避免重复发现，支持快速工具路由。

## 8. 源码注释落点
本轮已补充教程注释的位置：
1. client.py 的临时发现连接策略说明
2. adapter.py 的统一注册输出说明
3. 其余核心入口注释延续既有内容

## 9. 证据清单
1. droidrun/mcp/config.py: MCPServerConfig, MCPConfig
2. droidrun/mcp/client.py: discover_tools, _discover_server_tools, call_tool
3. droidrun/mcp/adapter.py: schema_to_parameters, mcp_to_droidrun_tools
4. droidrun/mcp/__init__.py: module exports

## 10. [不确定] 项
1. [不确定] 大量 MCP servers 并存时发现阶段的启动成本与超时策略仍可进一步细化。
2. [不确定] 某些 MCP 工具返回非文本结构时 wrapper 的输出提取策略可能需要扩展。

## 11. 覆盖率与下一轮
### 11.1 本轮已覆盖
1. droidrun/mcp/config.py
2. droidrun/mcp/client.py
3. droidrun/mcp/adapter.py
4. droidrun/mcp/__init__.py

### 11.2 下一轮建议
1. droidrun/config_manager/env_keys.py
2. droidrun/config_manager/loader.py
3. droidrun/config_manager/path_resolver.py（回顾强化）

## 12. 小结
这一轮完成了 MCP 接入三层串讲：配置声明接入边界，Client 管理发现与调用，Adapter 完成协议翻译并并入 Droidrun 工具生态。