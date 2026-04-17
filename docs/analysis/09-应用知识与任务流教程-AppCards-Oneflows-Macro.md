# 09 应用知识与任务流教程（AppCards、Oneflows、Macro）

承接：前几轮把基础执行链、配置、LLM 工具链都讲清楚了。这一轮关注三块“能力增强层”：
1) AppCards（给 Agent 注入应用知识）
2) Oneflows（把特定任务封装成小工作流）
3) Macro（把操作轨迹回放成可复现自动化）

## 1. 学习目标
1. 理解 AppCards 为什么能提升 Agent 在特定 App 场景下的表现。
2. 理解 oneflow 这类小工作流如何专门解决某类任务。
3. 理解 Macro 回放如何从 trajectory 还原动作序列。

## 2. 分析范围
1. `droidrun/app_cards/app_card_provider.py`
2. `droidrun/app_cards/providers/local_provider.py`
3. `droidrun/app_cards/providers/server_provider.py`
4. `droidrun/app_cards/providers/composite_provider.py`
5. `droidrun/agent/oneflows/app_starter_workflow.py`
6. `droidrun/agent/oneflows/structured_output_agent.py`
7. `droidrun/macro/replay.py`
8. `droidrun/macro/cli.py`
9. `droidrun/macro/__main__.py`
10. `droidrun/macro/__init__.py`

## 3. AppCards：把“应用领域知识”注入执行
### 3.1 AppCardProvider 抽象接口
文件：`app_card_provider.py`

它做什么：
1. 定义统一接口 `load_app_card(package_name, instruction)`。
2. 让不同来源（本地、服务端、组合）都可以被同一方式调用。

### 3.2 LocalAppCardProvider
文件：`providers/local_provider.py`

它做什么：
1. 读取 `app_cards.json` 建立 package -> markdown 文件映射。
2. 按 package 加载本地 app card 文本。
3. 用内存缓存减少重复读盘。

### 3.3 ServerAppCardProvider
文件：`providers/server_provider.py`

它做什么：
1. 通过 HTTP 接口按 package + instruction 获取 app card。
2. 内置超时和重试。
3. 同样做内存缓存。

### 3.4 CompositeAppCardProvider
文件：`providers/composite_provider.py`

它做什么：
1. 先走 server。
2. server 失败或为空时回退本地。

教程式理解：
这是典型的“远程优先、本地兜底”策略，兼顾实时性和可用性。

## 4. Oneflows：把高频能力封装成小工作流
### 4.1 AppStarter
文件：`agent/oneflows/app_starter_workflow.py`

它做什么：
1. 拉取设备安装应用列表。
2. 把用户描述和应用列表交给 LLM。
3. 解析返回 JSON 获取 package。
4. 调 driver 启动目标应用。

为什么存在：
“打开某个应用”是高频需求，单独封装能让主 Agent 少写样板逻辑。

### 4.2 StructuredOutputAgent
文件：`agent/oneflows/structured_output_agent.py`

它做什么：
1. 把最终文本答案交给 `structured_predict`。
2. 用 Pydantic 模型提取结构化结果。

教程式理解：
它像“文本到结构化对象”的后处理器，专门解决最终输出规范化问题。

## 5. Macro：把历史动作回放成可重复执行
### 5.1 MacroPlayer
文件：`macro/replay.py`

它做什么：
1. 加载 `macro.json`。
2. 按动作类型（tap/swipe/input_text/key_press 等）逐步调用 driver。
3. 支持从某一步开始、限制最大步数、统计成功率。

### 5.2 宏回放 CLI
文件：`macro/cli.py`

它做什么：
1. 提供 `replay` 和 `list` 子命令。
2. 支持 dry-run 展示而不实际执行。
3. 兼容路径解析与日志输出。

### 5.3 模块入口
文件：`macro/__main__.py`

作用：
支持 `python -m droidrun.macro ...` 方式运行。

## 6. 三者关系
```text
AppCards: 提升“知道该怎么做”
Oneflows: 提升“把某类动作流程封装好”
Macro:    提升“把做过的流程复现出来”
```

## 7. Python 知识点联动
### 7.1 抽象基类 `ABC`
项目位置：`AppCardProvider`

作用：
统一 provider 接口，方便替换实现。

### 7.2 异步工作流 step
项目位置：`AppStarter.open_app_step`、`StructuredOutputAgent.extract_structured_output`

作用：
把特定任务拆成可组合的异步步骤。

### 7.3 缓存字典
项目位置：多个 AppCard provider 的 `_content_cache`

作用：
减少重复 I/O 和重复网络请求。

### 7.4 `Optional` 与参数过滤
项目位置：macro 回放函数参数

作用：
支持灵活指定重放范围和步数。

## 8. 源码注释落点
本轮已补充教程注释的位置：
1. `AppCardProvider` 与三个 provider 的关键入口
2. `AppStarter`、`StructuredOutputAgent` 的核心步骤
3. `MacroPlayer` 与 replay CLI 的关键执行入口

## 9. 证据清单
1. `droidrun/app_cards/app_card_provider.py`：`AppCardProvider.load_app_card`
2. `droidrun/app_cards/providers/local_provider.py`：`LocalAppCardProvider.load_app_card`
3. `droidrun/app_cards/providers/composite_provider.py`：`CompositeAppCardProvider.load_app_card`
4. `droidrun/agent/oneflows/app_starter_workflow.py`：`AppStarter.open_app_step`
5. `droidrun/agent/oneflows/structured_output_agent.py`：`extract_structured_output`
6. `droidrun/macro/replay.py`：`MacroPlayer.replay_action`、`replay_macro`
7. `droidrun/macro/cli.py`：`replay`、`_replay_async`、`_show_dry_run`

## 10. [不确定] 项
1. [不确定] app card server 的外部 API 协议约束（字段扩展、鉴权）在仓库内未完整定义。
2. [不确定] macro 录制字段在不同版本 trajectory 里的兼容边界，还需结合历史样本验证。

## 11. 覆盖率与下一轮
### 11.1 本轮已覆盖
1. `droidrun/app_cards/app_card_provider.py`
2. `droidrun/app_cards/providers/local_provider.py`
3. `droidrun/app_cards/providers/server_provider.py`
4. `droidrun/app_cards/providers/composite_provider.py`
5. `droidrun/agent/oneflows/app_starter_workflow.py`
6. `droidrun/agent/oneflows/structured_output_agent.py`
7. `droidrun/macro/replay.py`
8. `droidrun/macro/cli.py`
9. `droidrun/macro/__main__.py`
10. `droidrun/macro/__init__.py`

### 11.2 下一轮建议
1. `droidrun/cli/device_commands.py`
2. `droidrun/cli/oauth_actions.py`
3. `droidrun/cli/configure_wizard.py`
4. `droidrun/config_manager/credential_paths.py`

## 12. 小结
这一轮补齐了“领域知识注入、任务子流封装、轨迹回放复现”三种增强能力。到这里，你看到的不只是主执行链，也包括了 Droidrun 在实际工程里提高成功率和可复现性的配套机制。