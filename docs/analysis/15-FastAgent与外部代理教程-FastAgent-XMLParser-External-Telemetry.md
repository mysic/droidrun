# 15 FastAgent 与外部代理教程（FastAgent、XMLParser、External、Telemetry）

承接：第 14 轮讲了工具注册与分发中枢，这一轮继续沿执行链向外扩展，覆盖 FastAgent 自循环、XML 调用协议解析、external 插件加载和遥测跟踪。

## 1. 学习目标
1. 理解 FastAgent 的闭环执行流程。
2. 理解 XML 工具调用从文本解析到参数类型转换的关键步骤。
3. 理解 external agent 的动态发现与契约校验。
4. 理解 telemetry tracker 的匿名标识与限时上报策略。

## 2. 分析范围
1. `droidrun/agent/fast_agent/fast_agent.py`
2. `droidrun/agent/fast_agent/xml_parser.py`
3. `droidrun/agent/fast_agent/events.py`
4. `droidrun/agent/external/__init__.py`
5. `droidrun/agent/external/README.md`
6. `droidrun/telemetry/tracker.py`

## 3. FastAgent 主循环：fast_agent.py
它做什么：
1. 初始化系统提示、用户目标、可用工具描述。
2. 每轮抓取设备状态（截图 + UI 树）并调用 LLM。
3. 解析 XML 工具调用，逐个执行并回填结果。
4. 直到 `complete` 或达到最大步数。

关键步骤：
1. `prepare_chat`：清理并初始化消息历史。
2. `handle_llm_input`：采集状态并请求模型下一步动作。
3. `handle_llm_output`：判断是否有工具调用，没有则补充引导提示。
4. `execute_code`：分发工具执行并格式化结果。
5. `handle_execution_result`：把结果作为下一轮观察输入。
6. `finalize`：返回 success/reason/tool_call_count。

教程式理解：
FastAgent 是“单代理 ReAct 引擎”：状态观测、动作生成、动作执行、结果反馈形成一个自循环。

## 4. XML 协议层：xml_parser.py
它做什么：
1. `parse_tool_calls` 从模型文本抽取 `<function_calls>` 块并转成 `ToolCall`。
2. `_sanitize_param_content` 清理参数文本中的 XML 冲突字符。
3. `_coerce_param` 按工具签名做参数类型转换（boolean/number/list）。
4. `format_tool_results` 把执行结果回包为 `<function_results>`。

关键点：
1. 解析失败会跳过异常块，尽量保留可执行部分。
2. 类型转换失败会写入每个 ToolCall 的 error，执行阶段再统一反馈。

## 5. external 插件加载：agent/external
### 5.1 README 契约
1. 外部代理必须实现 async `run(device, instruction, config, max_steps)`。
2. 要求零依赖 droidrun 内部工具，仅通过原始 `AdbDevice` 操作设备。

### 5.2 动态加载器
1. `list_agents` 扫描目录发现单文件或包式代理。
2. `load_agent` 动态导入并校验 `run` 是否存在且为 async。
3. 返回 `run` + `DEFAULT_CONFIG`（若定义）。

教程式理解：
这是一条“外部扩展通道”：核心框架负责生命周期与契约校验，策略逻辑留给插件自由实现。

## 6. 遥测追踪：telemetry/tracker.py
它做什么：
1. 读取环境变量决定是否开启遥测。
2. 维护本地持久化匿名 `user_id`。
3. `capture` 发送事件（附带 `run_id`）。
4. `flush` 在超时保护下异步刷新发送队列。

关键点：
1. 默认开启，可通过环境变量显式关闭。
2. flush 设定 10 秒超时，防止退出时卡住主流程。

## 7. Python 知识点联动
### 7.1 Workflow step 设计
项目位置：`fast_agent.py`

作用：
将复杂代理循环拆成可观测、可测试的阶段。

### 7.2 结构化文本协议解析
项目位置：`xml_parser.py`

作用：
把自然语言模型输出转换为机器可执行调用。

### 7.3 动态导入插件
项目位置：`agent/external/__init__.py`

作用：
支持运行时扩展，不需要修改核心流程代码。

### 7.4 异步超时保护
项目位置：`telemetry/tracker.py`

作用：
在网络不可控场景下保持主流程稳定性。

## 8. 源码注释落点
本轮已补充教程注释的位置：
1. `fast_agent/events.py` 的响应与调用事件字段
2. `fast_agent/xml_parser.py` 的参数清洗与布尔类型转换
3. `agent/external/__init__.py` 的发现与加载入口
4. `telemetry/tracker.py` 的 user_id 持久化与 flush 行为

## 9. 证据清单
1. `droidrun/agent/fast_agent/fast_agent.py`：`prepare_chat`、`handle_llm_input`、`execute_code`
2. `droidrun/agent/fast_agent/xml_parser.py`：`parse_tool_calls`、`_coerce_param`
3. `droidrun/agent/external/__init__.py`：`list_agents`、`load_agent`
4. `droidrun/telemetry/tracker.py`：`is_telemetry_enabled`、`capture`、`flush`

## 10. [不确定] 项
1. [不确定] XML 解析容错在极端嵌套参数文本下是否仍能稳定保留全部调用块，建议后续加 fuzz case。
2. [不确定] external agent 的第三方依赖冲突处理目前由用户自行负责，后续可考虑隔离运行环境。

## 11. 覆盖率与下一轮
### 11.1 本轮已覆盖
1. `droidrun/agent/fast_agent/fast_agent.py`
2. `droidrun/agent/fast_agent/xml_parser.py`
3. `droidrun/agent/fast_agent/events.py`
4. `droidrun/agent/external/__init__.py`
5. `droidrun/agent/external/README.md`
6. `droidrun/telemetry/tracker.py`

### 11.2 下一轮建议
1. `droidrun/tools/driver/android.py`（连接模式与 Portal 通道）
2. `droidrun/tools/driver/ios.py`（平台差异与能力抽象）
3. `droidrun/tools/ui/provider.py`（状态采集策略与降级）

## 12. 小结
这一轮完成了“执行闭环外围能力”的串讲：FastAgent 负责闭环调度，XML parser 负责协议落地，external loader 提供可插拔扩展，telemetry tracker 提供匿名可观测性。