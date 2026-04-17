# 11 Provider 选择与用量统计教程（Providers、Usage、LogHandlers）

承接：上一轮讲的是 CLI 配置入口，这一轮往下一层看“配置真正如何落到运行时”，以及“运行后如何统计 token 与输出日志”。

## 1. 学习目标
1. 理解 provider family / variant 的建模方式。
2. 理解配置向导选择如何转换成 `LLMProfile`。
3. 理解 token usage 统计如何兼容不同模型厂商响应格式。
4. 理解 CLI/TUI 日志输出的统一机制。

## 2. 分析范围
1. `droidrun/agent/providers/types.py`
2. `droidrun/agent/providers/registry.py`
3. `droidrun/agent/providers/setup_service.py`
4. `droidrun/agent/usage.py`
5. `droidrun/log_handlers.py`

## 3. Provider 建模：types.py
它做什么：
1. 用 `ProviderFamilySpec` 表示用户看见的 provider 家族（如 OpenAI、Gemini、ZAI）。
2. 用 `ProviderVariantSpec` 表示同一家 provider 的运行时变体（例如 `api_key` 与 `oauth`）。

教程式理解：
family 是“产品层名字”，variant 是“技术层配置”。这种二层建模可以把用户交互和运行实现分离。

## 4. Provider 注册表：registry.py
它做什么：
1. 定义 `PROVIDER_FAMILIES`，集中管理模型列表、鉴权模式、默认模型和凭据路径。
2. 定义 `VARIANT_ENV_KEY_SLOT`，把 variant 映射到 `env_keys` 的槽位。
3. 提供查询函数：列 family、列 auth modes、解析 variant、规范化模型 ID。

关键点：
1. `resolve_provider_variant` 在多 variant 情况下强制要求 auth mode，避免歧义。
2. `normalize_model_id_for_variant` 支持别名前缀转 canonical id，减少配置污染。

## 5. 配置落地服务：setup_service.py
它做什么：
1. 把用户在向导中的选择封装为 `SetupSelection`。
2. 通过 `create_profile_for_variant` 生成可持久化的 `LLMProfile`。
3. 通过 `apply_selection_to_roles` 把同一选择批量应用到多角色。

关键流程：
1. 从 selection 与 variant 合成 base_url、model、kwargs。
2. 对 OpenAI 家族强制 temperature=1（与模型约束一致）。
3. 若 provider 走 env slot，保存 API key 到 `env_keys`。
4. 若 `fast_agent` 被更新，同时回填隐藏角色 `app_opener`、`structured_output`。

特殊逻辑：
1. ZAI `coding_api` 模式会探测 `glm-5` 是否可用，不可用时回退 `glm-4.7`。

## 6. Token 用量统计：usage.py
它做什么：
1. 以 `UsageResult` 统一表示 `request_tokens`、`response_tokens`、`total_tokens`、`requests`。
2. `get_usage_from_response` 按 provider 分支解析不同响应格式。
3. `TokenCountingHandler` 作为 LlamaIndex callback 在事件结束时累计统计。
4. 提供两种接入方式：
   - `llm_callback(...):` 临时上下文注册
   - `track_usage(llm):` 全程注册

教程式理解：
这是一个“反腐层”（anti-corruption layer）：把不同厂商协议映射到统一统计协议。

## 7. 日志输出桥接：log_handlers.py
它做什么：
1. `configure_logging` 重置并接管 `droidrun` logger。
2. `CLILogHandler` 用 Rich 做彩色与流式终端输出。
3. `TUILogHandler` 把日志变成结构化记录并可回调给 UI。

关键点：
1. 通过 `extra` 字段支持 `color`、`stream`、`stream_end`。
2. CLI 与 TUI 共用同一日志语义，渲染层不同。

## 8. Python 知识点联动
### 8.1 dataclass 作为配置模型
项目位置：`types.py`、`setup_service.py`

作用：
固定字段结构、提升可读性与可维护性。

### 8.2 回调模式（Callback Handler）
项目位置：`usage.py`

作用：
不侵入业务主流程，即可采集横切指标（token usage）。

### 8.3 上下文管理器（contextmanager）
项目位置：`usage.py`

作用：
确保回调生命周期成对注册/移除，减少资源泄漏风险。

### 8.4 结构化日志
项目位置：`log_handlers.py`

作用：
同一条日志可被不同前端（CLI/TUI）消费。

## 9. 源码注释落点
本轮已补充教程注释的位置：
1. `types.py` 的 `ProviderVariantSpec` 与 `ProviderFamilySpec`
2. `registry.py` 的映射常量、注册表与查询入口函数
3. `setup_service.py` 的选择模型、profile 构造与批量应用入口
4. `usage.py` 的 provider 统计入口、callback 与 tracker 接口
5. `log_handlers.py` 的 logger 接管与 CLI/TUI handler

## 10. 证据清单
1. `droidrun/agent/providers/registry.py`：`PROVIDER_FAMILIES`、`resolve_provider_variant`
2. `droidrun/agent/providers/setup_service.py`：`create_profile_for_variant`、`apply_selection_to_roles`
3. `droidrun/agent/usage.py`：`get_usage_from_response`、`TokenCountingHandler`
4. `droidrun/log_handlers.py`：`configure_logging`、`CLILogHandler`、`TUILogHandler`

## 11. [不确定] 项
1. [不确定] 当前 `SUPPORTED_PROVIDERS` 与所有运行时 provider 类名是否始终同步，建议加回归测试锁定。
2. [不确定] `apply_selection_to_roles` 在新增隐藏角色后是否需要继续扩展回填名单，取决于后续角色设计。

## 12. 覆盖率与下一轮
### 12.1 本轮已覆盖
1. `droidrun/agent/providers/types.py`
2. `droidrun/agent/providers/registry.py`
3. `droidrun/agent/providers/setup_service.py`
4. `droidrun/agent/usage.py`
5. `droidrun/log_handlers.py`

### 12.2 下一轮建议
1. `droidrun/agent/common/*`
2. `droidrun/agent/action_context.py`
3. `droidrun/agent/action_result.py`（深挖异常与输出协议）

## 13. 小结
这一轮你可以把它理解为“配置与观测基础层”：上游向导做出的选择，最终经由 provider 注册与 setup service 变成可执行 profile；执行后再通过 usage callback 与日志 handler 把行为可观测化。