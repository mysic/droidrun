# 34 外部消息插队教程（DroidAgentState、ExternalUserMessageEvents、FastAgent-Manager消费链）

承接：前面几轮已经把 Manager、FastAgent、共享状态和 oneflows 分别拆开了。这一轮专门解释一个容易被忽略、但对长任务很关键的能力：任务运行到一半时，外部调用方如何再插入一条新用户消息，以及这条消息最终会被谁、在什么时候消费。

## 1. 学习目标
1. 理解 `send_user_message()` 为什么不是立刻打断当前 step，而是先进入队列。
2. 理解 `pending_user_messages` 在 `DroidAgentState` 中如何保存和清空。
3. 理解 `Manager` 与 `FastAgent` 两条执行分支分别怎样消费或丢弃这些插队消息。
4. 理解 `ExternalUserMessageAppliedEvent` / `DroppedEvent` 为什么要单独建模。

## 2. 分析范围
1. `droidrun/agent/droid/state.py`
2. `droidrun/agent/droid/events.py`
3. `droidrun/agent/droid/droid_agent.py`
4. `droidrun/agent/manager/manager_agent.py`
5. `droidrun/agent/fast_agent/fast_agent.py`

排除项：
1. 普通 `message_history` 的完整规划语义
2. `ExecutorAgent` 动作执行细节
3. CLI/TUI 如何把外部消息入口暴露给最终用户

## 3. 架构/流程总览
文字图：
1. 外部调用方执行 `DroidAgent.send_user_message("...")`。
2. `send_user_message()` 调用 `shared_state.queue_user_message()`。
3. 新消息被包装成 `QueuedUserMessage` 放入 `pending_user_messages` 队列。
4. 当前 step 不被强行打断，消息等待下一次合适的消费点。
5. reasoning 模式下，`ManagerAgent.prepare_context()` 会优先 drain 队列，并把消息拼进本轮 user prompt。
6. FastAgent 模式下，`handle_execution_result()` 会把 drain 出来的消息追加到工具结果用户消息中。
7. 若已经到最大步数或准备结束但仍有待处理消息，则系统会触发 dropped 或继续循环，而不是静默丢失。

## 4. 文件级讲解（按职责分组）
### 4.1 队列存储层
1. 文件：`droidrun/agent/droid/state.py`
2. 做什么：定义插队消息对象 `QueuedUserMessage`，并在 `DroidAgentState` 中维护 `pending_user_messages` 队列。
3. 关键符号：`QueuedUserMessage`、`pending_user_messages`、`queue_user_message()`、`drain_user_messages()`
4. 调用关系：外部入口 -> `queue_user_message()` -> 后续由 Manager/FastAgent 调 `drain_user_messages()` 消费
5. 初学者易错点：
   - 这里不是消息总线，而是一个简单的“待消费列表”。
   - `drain_user_messages()` 会清空队列，所以同一批消息不会被重复消费。
   - `workflow_completed=True` 后再入队会直接报错，避免任务结束后消息悬空。

### 4.2 事件语义层
1. 文件：`droidrun/agent/droid/events.py`
2. 做什么：定义插队消息被消费或被丢弃时的事件对象，供日志、轨迹和前端观察链路使用。
3. 关键符号：`ExternalUserMessageAppliedEvent`、`ExternalUserMessageDroppedEvent`
4. 调用关系：Manager/FastAgent 消费或丢弃队列时 -> 写入 workflow event stream
5. 初学者易错点：
   - `AppliedEvent` 不是“收到消息”事件，而是“已经进入某个 Agent 上下文”事件。
   - `DroppedEvent` 是显式失败信号，表示消息未被处理，不是普通结束路径。

### 4.3 顶层注入入口
1. 文件：`droidrun/agent/droid/droid_agent.py`
2. 做什么：提供公共方法 `send_user_message()`，并在顶层协调逻辑里处理“有新消息时是否允许结束任务”。
3. 关键符号：`send_user_message()`、`run_manager()`、`handle_manager_plan()`
4. 调用关系：外部调用 -> `send_user_message()` -> `shared_state.queue_user_message()`；Manager 准备结束时 -> 若队列非空则回退到下一轮 planning
5. 初学者易错点：
   - `send_user_message()` 只入队，不会立即唤醒或中断当前底层执行步骤。
   - `handle_manager_plan()` 在 Manager 想结束时会再次检查队列，确保新消息优先级高于“现在就收尾”。
   - `run_manager()` 触顶时会把未消费消息标记为 dropped，而不是沉默清空。

### 4.4 Manager 消费路径
1. 文件：`droidrun/agent/manager/manager_agent.py`
2. 做什么：在 `prepare_context()` 阶段把待处理外部消息拼接成 `<external_user_message>` 块，直接注入本轮规划上下文。
3. 关键符号：`prepare_context()` 中 `drain_user_messages()`、`ExternalUserMessageAppliedEvent`
4. 调用关系：Manager 每次准备新一轮 planning -> drain 队列 -> 拼进 user message -> 写 AppliedEvent
5. 初学者易错点：
   - 外部消息不会单独形成一条独立 workflow 分支，而是被融合到本轮规划输入。
   - Manager 是“规划时消费”，不是“动作执行后消费”。

### 4.5 FastAgent 消费路径
1. 文件：`droidrun/agent/fast_agent/fast_agent.py`
2. 做什么：在 `handle_execution_result()` 阶段把外部消息附加到工具结果输出中，作为下一轮 LLM 输入的一部分。
3. 关键符号：`handle_execution_result()`、`handle_llm_input()` 触顶丢弃、`execute_code()` 中 complete 撤销结束
4. 调用关系：工具执行完成 -> drain 队列 -> 合并进下一条 user message；若 complete 后仍有消息 -> 撤销结束并继续
5. 初学者易错点：
   - FastAgent 不是在每轮输入前立即消费，而是在“工具结果回写”这一跳消费，这样新消息能和最新观察结果一起送给模型。
   - 如果刚调用 `complete()` 就又来了外部消息，FastAgent 会继续而不是立刻结束。
   - 触顶时同样会显式 dropped，避免调用方误判为消息还会被后续处理。

## 4.2 源码注释落点
1. 需要补充注释的类/函数：`drain_user_messages()`、`ExternalUserMessageAppliedEvent`、`ExternalUserMessageDroppedEvent`、`send_user_message()`、`run_manager()` 触顶分支、`handle_manager_plan()` 结束前检查、`FastAgent.handle_llm_input()` 触顶分支、`FastAgent.execute_code()` complete 后续处理、`ManagerAgent.prepare_context()` 的 drain 逻辑
2. 注释写入位置：
   - 队列清空函数前
   - 外部消息事件类定义前
   - 顶层公开入口和关键分支判断前
   - Manager/FastAgent 真正消费队列的位置前
3. 注释解释目标：说明“为什么不立即打断当前执行”“为什么同一批消息只消费一次”“为什么会有 applied/dropped 两类事件”

## 5. Python 知识点联动
1. 语法/关键字/内置函数：列表队列、批量 drain、事件建模、共享状态协调
2. 在本项目中的位置：`pending_user_messages` 列表、`drain_user_messages()`、workflow 事件类、Manager/FastAgent 的消费分支
3. 为什么这样写：
   - 先入队后消费能避免异步 workflow 在任意位置被粗暴中断。
   - 通过 drain 模式一次性取走消息，可以明确消费边界，避免重复注入。
   - 用显式事件记录 applied/dropped，能让外部观察链路知道消息是“已处理”还是“已丢弃”。
4. 最小示例：
```python
queued = state.queue_user_message("继续检查这个页面")
messages = state.drain_user_messages()
for item in messages:
    prompt += f"\n<external_user_message>{item.message}</external_user_message>"
```
5. 常见错误与修正：
   - 错误：以为 `send_user_message()` 会立即打断当前工具执行。
   - 修正：它只是入队，等待下一次消费点。
   - 错误：以为 `drain_user_messages()` 只是读取，不会修改队列。
   - 修正：它会清空队列，所以必须在真正准备消费时调用。

## 6. 证据清单
1. `droidrun/agent/droid/state.py`：`QueuedUserMessage`、`queue_user_message()`、`drain_user_messages()`
2. `droidrun/agent/droid/events.py`：`ExternalUserMessageAppliedEvent`、`ExternalUserMessageDroppedEvent`
3. `droidrun/agent/droid/droid_agent.py`：`send_user_message()`、`run_manager()`、`handle_manager_plan()`
4. `droidrun/agent/manager/manager_agent.py`：`prepare_context()` 中外部消息注入分支
5. `droidrun/agent/fast_agent/fast_agent.py`：`handle_llm_input()`、`execute_code()`、`handle_execution_result()`

## 7. [不确定] 项
1. [不确定] 当前插队消息仍按简单 FIFO 批量注入，没有更复杂的优先级或去重策略；是否需要升级取决于真实多消息并发场景。
2. [不确定] 如果外部消息非常频繁，Manager/FastAgent 的“准备结束前继续循环”策略是否会导致任务难以收敛，还需要结合真实长任务评估。

## 8. 覆盖率与下一轮
### 8.1 本轮已覆盖
1. `droidrun/agent/droid/state.py`
2. `droidrun/agent/droid/events.py`
3. `droidrun/agent/droid/droid_agent.py`
4. `droidrun/agent/manager/manager_agent.py`
5. `droidrun/agent/fast_agent/fast_agent.py`

### 8.2 下一轮建议
1. `droidrun/agent/providers/registry.py`、`setup_service.py`、`cli/configure_wizard.py`、`cli/tui/settings/data.py` 的 provider 配置联动链
2. `droidrun/tools/__init__.py` 与 `droidrun/tools/driver/__init__.py`、`droidrun/tools/helpers/__init__.py` 的包级导出门面
3. `droidrun/cli/tui/settings/` 下各页签组件的更细粒度字段映射

## 9. 小结
这一轮把“运行中追加用户指令”的实现链路讲透了：消息先进入共享状态队列，再由 Manager 或 FastAgent 在明确的消费点吸收进上下文；如果消息来不及处理，系统会用 dropped 事件显式告诉上层。这样一来，长任务就能在不破坏当前 workflow 结构的前提下支持中途加指令。
