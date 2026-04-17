# 05 事件系统与共享状态教程（Events、State）

承接：前几轮已经讲清了 Agent、动作系统、UI 树处理和 CLI 展示。这一轮把它们之间真正“串起来”的机制讲透，也就是事件系统和共享状态模型。

## 1. 学习目标
1. 理解 Droidrun 为什么大量使用 Event 类，而不是直接层层函数返回。
2. 理解 DroidAgent、Manager、Executor、FastAgent 各自事件的职责边界。
3. 理解 `DroidAgentState` 为什么是整个系统的共享状态中心。
4. 看懂“事件流 + 共享状态”是如何一起驱动多 Agent 协作的。

## 2. 分析范围
1. `droidrun/agent/droid/events.py`
2. `droidrun/agent/manager/events.py`
3. `droidrun/agent/executor/events.py`
4. `droidrun/agent/fast_agent/events.py`
5. `droidrun/agent/droid/state.py`
6. `droidrun/agent/manager/__init__.py`
7. `droidrun/agent/executor/__init__.py`
8. `droidrun/agent/fast_agent/__init__.py`

## 3. 先记住两个核心概念
1. Event 解决“工作流每一步之间怎么传递阶段性结果”。
2. State 解决“整个任务执行过程中哪些信息需要持续共享”。

## 4. 为什么需要事件系统
如果只靠普通函数返回值，会有几个问题：
1. 难以把中间过程实时流到 CLI/TUI。
2. 难以把不同 Agent 的阶段拆分成工作流步骤。
3. 很难同时支持“内部控制”和“前端日志展示”。

所以 Droidrun 的做法是：
1. 用 Event 表达“当前处于哪个阶段、产出了什么信息”。
2. 用 State 保存“整个任务共享的上下文和历史”。

## 5. 事件分层
### 5.1 DroidAgent 协调事件
文件：`droidrun/agent/droid/events.py`

职责：
1. 在顶层协调器和子 Agent 之间路由。
2. 表达 planning/execution/finalization 等跨模块阶段。

关键事件：
1. `ManagerInputEvent`：通知 Manager 开始规划
2. `ManagerPlanEvent`：Manager 规划结束后回给 DroidAgent 的协调事件
3. `ExecutorInputEvent`：通知 Executor 开始执行子目标
4. `ExecutorResultEvent`：Executor 执行完一轮动作后的结果
5. `FastAgentExecuteEvent` / `FastAgentResultEvent`：直连模式下的启动和完成
6. `FinalizeEvent` / `ResultEvent`：最终收口

### 5.2 Manager 内部事件
文件：`droidrun/agent/manager/events.py`

职责：
1. 描述 Manager 工作流内部各步骤的阶段产物。
2. 这些事件更细，更适合日志展示和中间调试。

关键事件：
1. `ManagerContextEvent`
2. `ManagerResponseEvent`
3. `ManagerPlanDetailsEvent`

### 5.3 Executor 内部事件
文件：`droidrun/agent/executor/events.py`

职责：
1. 记录 Executor 在“准备 -> 响应 -> 解析 -> 执行”链路上的阶段。

关键事件：
1. `ExecutorContextEvent`
2. `ExecutorResponseEvent`
3. `ExecutorActionEvent`
4. `ExecutorActionResultEvent`

### 5.4 FastAgent 内部事件
文件：`droidrun/agent/fast_agent/events.py`

职责：
1. 记录 FastAgent 自循环中的每个阶段。

关键事件：
1. `FastAgentInputEvent`
2. `FastAgentResponseEvent`
3. `FastAgentToolCallEvent`
4. `FastAgentOutputEvent`
5. `FastAgentEndEvent`

## 6. 共享状态：DroidAgentState
文件：`droidrun/agent/droid/state.py`

它为什么重要：
因为多 Agent 协作不是“各干各的”，而是共享同一个执行上下文。`DroidAgentState` 就是这个共享上下文容器。

### 6.1 它保存了什么
1. 任务上下文：instruction、step_number、platform
2. 当前设备状态：formatted_device_state、a11y_tree、phone_state、screenshot
3. 规划状态：plan、current_subgoal、answer
4. 执行历史：action_history、summary_history、action_outcomes、error_descriptions
5. 记忆：manager_memory、fast_memory
6. 结束状态：finished、success
7. 消息历史：message_history
8. 外部消息队列：pending_user_messages
9. 自定义变量：custom_variables

### 6.2 它不仅存数据，还提供行为
关键方法：
1. `remember()`
2. `complete()`
3. `queue_user_message()`
4. `drain_user_messages()`
5. `update_current_app()`

这说明它不是被动 DTO，而是“带行为的状态对象”。

## 7. 一个典型协作过程
### 7.1 reasoning=True
1. `ManagerInputEvent` 触发 Manager
2. Manager 内部产出 `ManagerContextEvent -> ManagerResponseEvent -> ManagerPlanDetailsEvent`
3. 顶层拿到计划后发 `ExecutorInputEvent`
4. Executor 内部产出 `ExecutorContextEvent -> ExecutorResponseEvent -> ExecutorActionEvent -> ExecutorActionResultEvent`
5. 顶层决定是否继续下一轮或收尾
6. 最终触发 `FinalizeEvent` / `ResultEvent`

### 7.2 reasoning=False
1. `FastAgentExecuteEvent` 启动
2. FastAgent 在 `Input -> Response -> ToolCall -> Output` 之间循环
3. 达到完成条件后发 `FastAgentEndEvent`
4. 顶层转成 `FastAgentResultEvent` 和最终 `ResultEvent`

## 8. Python 知识点联动
### 8.1 Pydantic BaseModel
项目位置：`DroidAgentState`、`QueuedUserMessage`

作用：
让状态对象拥有类型校验、默认值、字段工厂等能力。

### 8.2 `Field(default_factory=...)`
项目位置：状态中的列表、集合、消息 ID。

作用：
避免可变默认值陷阱，并支持动态生成默认值。

### 8.3 继承事件基类
项目位置：所有 `...Event` 类。

作用：
让工作流框架识别它们是可传递的流程消息。

### 8.4 `Optional[bool]`
项目位置：多个事件中的 `success`。

作用：
表示三态：成功 / 失败 / 尚未完成。

## 9. 源码注释落点
本轮已补充教程注释的位置：
1. `droid/events.py` 的协调事件分组与关键事件类
2. `manager/events.py`、`executor/events.py`、`fast_agent/events.py` 的关键事件类
3. `state.py` 中 `QueuedUserMessage`、`DroidAgentState` 和关键行为方法
4. 三个子包的 `__init__.py` 导出入口

## 10. 证据清单
1. `droidrun/agent/droid/events.py`：`ManagerInputEvent`、`ExecutorResultEvent`、`ResultEvent`
2. `droidrun/agent/manager/events.py`：`ManagerPlanDetailsEvent`
3. `droidrun/agent/executor/events.py`：`ExecutorActionResultEvent`
4. `droidrun/agent/fast_agent/events.py`：`FastAgentEndEvent`
5. `droidrun/agent/droid/state.py`：`DroidAgentState.complete`、`DroidAgentState.update_current_app`

## 11. [不确定] 项
1. [不确定] 工作流框架底层对这些 Event 的调度机制还没继续追到 llama-index workflow 内部实现。
2. [不确定] 某些非 streamed 的协调事件在前端侧是否完全不可见，还需要结合运行时 trace 进一步确认。

## 12. 覆盖率与下一轮
### 12.1 本轮已覆盖
1. `droidrun/agent/droid/events.py`
2. `droidrun/agent/manager/events.py`
3. `droidrun/agent/executor/events.py`
4. `droidrun/agent/fast_agent/events.py`
5. `droidrun/agent/droid/state.py`
6. `droidrun/agent/manager/__init__.py`
7. `droidrun/agent/executor/__init__.py`
8. `droidrun/agent/fast_agent/__init__.py`

### 12.2 下一轮建议
1. `droidrun/mcp/*`
2. `droidrun/agent/utils/tracing_setup.py`
3. `droidrun/telemetry/events.py`
4. `droidrun/telemetry/phoenix.py`

## 13. 小结
到这一轮为止，你已经能把 Droidrun 看成一个“事件驱动的多 Agent 状态机”。事件负责阶段切换和中间结果流动，共享状态负责上下文持续存在。后面继续看 MCP 和 tracing，就能把外部扩展和可观测性也补齐。