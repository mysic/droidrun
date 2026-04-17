# 33 Manager规划分叉教程（ManagerAgent、StatelessManagerAgent、ManagerConfig）

承接：第 32 轮把 oneflows 的局部工作流讲清了。这一轮回到顶层规划链，专门解释 Droidrun 为什么同时保留 `ManagerAgent` 和 `StatelessManagerAgent` 两条 planning 路径，以及它们如何由配置开关接入 `DroidAgent`。

## 1. 学习目标
1. 理解 `ManagerAgent` 和 `StatelessManagerAgent` 的核心差异。
2. 理解 `ManagerConfig.stateless` 如何影响顶层 Agent 选择哪种规划器。
3. 理解“长期 message_history”与“每轮重建上下文”两种 planning 策略的取舍。

## 2. 分析范围
1. `droidrun/agent/manager/manager_agent.py`
2. `droidrun/agent/manager/stateless_manager_agent.py`
3. `droidrun/agent/manager/prompts.py`
4. `droidrun/agent/droid/droid_agent.py` 中 Manager 选择逻辑
5. `droidrun/config_manager/config_manager.py` 中 `ManagerConfig`

排除项：
1. `ExecutorAgent` 的动作执行细节
2. `FastAgent` 的无规划直连模式
3. `app_cards`、`ToolRegistry`、driver 的底层实现

## 3. 架构/流程总览
文字图：
1. `DroidAgent` 启动时读取 `config.agent.reasoning`。
2. 若开启 reasoning，则继续检查 `config.agent.manager.stateless`。
3. `stateless=False`：创建 `ManagerAgent`，保留多轮 `message_history`。
4. `stateless=True`：创建 `StatelessManagerAgent`，每轮重建 prompt 和上下文。
5. 两条路径最终都返回同样的 planning 结果结构：`plan/current_subgoal/thought/answer/success`。
6. 因为返回协议一致，`DroidAgent` 上层不需要关心底层具体使用了哪种 Manager。

## 4. 文件级讲解（按职责分组）
### 4.1 有状态规划器
1. 文件：`droidrun/agent/manager/manager_agent.py`
2. 做什么：维护长期消息历史，把“系统提示 + 多轮 user/assistant 消息 + 当前状态”一起发送给 LLM，让规划器带着上下文连续思考。
3. 关键符号：`ManagerAgent`、`_build_system_prompt`、`_build_messages_with_context`、`prepare_context`、`get_response`、`process_response`
4. 调用关系：`DroidAgent` -> `ManagerAgent.run()` -> 更新 `shared_state.message_history` -> 产出 `ManagerPlanDetailsEvent`
5. 初学者易错点：
   - 它不是每轮都只发当前 prompt，而是会把累计 `message_history` 一起送给模型。
   - `prepare_context` 末尾会向 `message_history` 追加 user 消息，`process_response` 再追加 assistant 消息，所以历史是持续增长的。
   - app card、外部用户消息、memory 等信息会被注入到多轮上下文，而不只是当前轮临时变量。

### 4.2 无状态规划器
1. 文件：`droidrun/agent/manager/stateless_manager_agent.py`
2. 做什么：每轮只基于当前 `shared_state` 里的状态快照、压缩后的动作历史和当前 prompt 重建上下文，不持续维护完整多轮对话。
3. 关键符号：`StatelessManagerAgent`、`_build_action_history`、`_build_prompt`、`_validate_and_retry`
4. 调用关系：`DroidAgent` -> `StatelessManagerAgent.run()` -> 临时构造 messages -> 解析结果 -> 回写关键规划字段
5. 初学者易错点：
   - 这里没有像 `ManagerAgent` 那样维护完整 assistant/user 历史。
   - `_build_action_history` 只保留最近最多 5 条动作摘要，是“压缩上下文”而不是“完整回放”。
   - 仍然会更新 `shared_state.plan/current_subgoal/answer`，所以对上层来说它依旧是一个标准 Manager。

### 4.3 共同解析协议
1. 文件：`droidrun/agent/manager/prompts.py`
2. 做什么：无论哪种 Manager，最终都用同一个 `parse_manager_response` 来解析 `<thought>`、`<plan>`、`<request_accomplished>` 等标签文本。
3. 关键符号：`parse_manager_response`
4. 调用关系：`ManagerAgent.process_response()` 与 `StatelessManagerAgent.process_response()` 共用这个解析器
5. 初学者易错点：
   - 两种 Manager 的差异主要在“如何组织上下文”，不是“如何解析结果”。
   - 因为解析协议一致，所以顶层协调器可以统一消费 planning 结果。

### 4.4 顶层选择与配置入口
1. 文件：`droidrun/agent/droid/droid_agent.py`
2. 做什么：在 `__init__` 中根据配置决定使用 `ManagerAgent` 还是 `StatelessManagerAgent`。
3. 关键符号：`self.config.agent.manager.stateless`、`ManagerClass = StatelessManagerAgent`、`ManagerClass = ManagerAgent`
4. 调用关系：配置 -> `DroidAgent` 构造阶段 -> 选择具体 Manager 类 -> 后续 `start_handler` 中进入 planning 流程
5. 初学者易错点：
   - 选择分支发生在顶层 Agent 初始化阶段，而不是运行中动态切换。
   - 只有 `reasoning=True` 时这个开关才有意义；否则直接走 `FastAgent` 分支。

### 4.5 配置模型开关
1. 文件：`droidrun/config_manager/config_manager.py`
2. 做什么：`ManagerConfig.stateless` 暴露给 YAML / CLI / TUI 的配置树，决定是否启用无状态规划器。
3. 关键符号：`ManagerConfig.stateless`
4. 调用关系：配置加载 -> `DroidConfig.agent.manager.stateless` -> `DroidAgent.__init__` 读取
5. 初学者易错点：
   - 这是一个规划策略开关，不影响 Executor 或 FastAgent 的行为。
   - 它不是“关闭记忆能力”，而是改变 Manager 如何构造提示上下文。

## 4.2 源码注释落点
1. 需要补充注释的类/函数：`StatelessManagerAgent`、`_build_action_history`、`_build_prompt`、`prepare_context`、`get_response`、`process_response`、`DroidAgent` 中 Manager 分支选择、`ManagerConfig.stateless`
2. 注释写入位置：
   - `StatelessManagerAgent` 类定义前与关键 helper / step 前
   - `DroidAgent.__init__` 中 `ManagerClass` 分支选择处
   - `ManagerConfig.stateless` 字段定义前
3. 注释解释目标：说明两种规划器的职责差异、状态边界和为什么顶层可以统一消费它们的结果

## 5. Python 知识点联动
1. 语法/关键字/内置函数：类选择、条件分支、共享状态回写、压缩历史构造
2. 在本项目中的位置：`DroidAgent.__init__` 的 `ManagerClass` 选择、`StatelessManagerAgent._build_action_history` 的 `zip(..., strict=True)`、两个 Manager 的 `@step` 协程
3. 为什么这样写：
   - 先在顶层选择具体类，能让运行期流程保持简洁，不需要在每个 planning 步骤里反复判断模式。
   - 把两种实现统一成同一返回协议，能降低 `DroidAgent` 对具体 Manager 类型的耦合。
   - 通过“完整历史”和“压缩历史”两种策略并存，可以在上下文质量与 token 成本之间灵活权衡。
4. 最小示例：
```python
ManagerClass = StatelessManager if use_stateless else StatefulManager
manager = ManagerClass(shared_state=state)
result = await manager.run()
```
5. 常见错误与修正：
   - 错误：把 `stateless` 理解成“完全没有状态”。
   - 修正：它仍然依赖 `shared_state`，只是不用完整 message_history。
   - 错误：认为两种 Manager 会返回不同结果结构。
   - 修正：它们共用同一解析协议，返回字段保持一致。

## 6. 证据清单
1. `droidrun/agent/manager/manager_agent.py`：`_build_messages_with_context`、`prepare_context`、`process_response`
2. `droidrun/agent/manager/stateless_manager_agent.py`：`_build_action_history`、`_build_prompt`、`prepare_context`、`process_response`
3. `droidrun/agent/manager/prompts.py`：`parse_manager_response`
4. `droidrun/agent/droid/droid_agent.py`：`ManagerClass = StatelessManagerAgent` / `ManagerClass = ManagerAgent`
5. `droidrun/config_manager/config_manager.py`：`ManagerConfig.stateless`

## 7. [不确定] 项
1. [不确定] 在超长任务里，无状态模式仅保留最近 5 条动作历史是否足够，还需要结合真实长任务样本验证。
2. [不确定] 有状态模式下 `message_history` 持续增长后，是否还需要更激进的裁剪或摘要策略来控制 token 成本。

## 8. 覆盖率与下一轮
### 8.1 本轮已覆盖
1. `droidrun/agent/manager/manager_agent.py`
2. `droidrun/agent/manager/stateless_manager_agent.py`
3. `droidrun/agent/manager/prompts.py`
4. `droidrun/agent/droid/droid_agent.py` 中 Manager 选择逻辑
5. `droidrun/config_manager/config_manager.py` 中 `ManagerConfig`

### 8.2 下一轮建议
1. `droidrun/agent/providers/registry.py` 与 `setup_service.py` 在 CLI / TUI 中的联动路径
2. `droidrun/cli/tui/settings/settings_screen.py` 下各页签组件的更细粒度配置映射
3. `droidrun/agent/common/` 与 `droidrun/agent/droid/state.py` 中外部消息插队机制的进一步拆解

## 9. 小结
这一轮把 Droidrun 的 planning 分叉讲清楚了：`ManagerAgent` 偏连续对话式规划，`StatelessManagerAgent` 偏每轮重建式规划；两者的上下文组织方式不同，但最终输出协议一致，因此顶层 `DroidAgent` 只需要在初始化时选好实现，后续执行链就可以保持统一。
