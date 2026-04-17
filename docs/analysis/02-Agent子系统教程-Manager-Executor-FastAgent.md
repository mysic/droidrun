# 02 Agent 子系统教程（Manager、Executor、FastAgent）

承接：上一轮已经建立全局架构图，这一轮开始拆开 droidrun 最核心的三个 Agent，理解“谁负责规划、谁负责执行、谁负责快速直达”。

## 1. 学习目标
1. 看懂 Manager、Executor、FastAgent 的职责边界。
2. 理解三者如何共享状态、拼接 Prompt、调用工具。
3. 学会从这些真实代码里读出 Python 异步工作流、类型提示、事件驱动处理方式。

## 2. 分析范围
1. 包含：`droidrun/agent/manager/manager_agent.py`、`droidrun/agent/executor/executor_agent.py`、`droidrun/agent/fast_agent/fast_agent.py`、`droidrun/agent/fast_agent/xml_parser.py`、`droidrun/agent/manager/stateless_manager_agent.py`
2. 排除：更底层的 actions 细节、driver 细节、prompt 文件全文。

## 3. 先记住三句话
1. ManagerAgent 负责“想下一步做什么”。
2. ExecutorAgent 负责“把某个子目标变成一次具体动作”。
3. FastAgent 负责“在简单模式下自己想、自己调工具、自己循环直到完成”。

## 4. 角色分工图
```text
DroidAgent
├── reasoning=True
│   ├── ManagerAgent        -> 规划计划、更新 memory、决定子目标
│   └── ExecutorAgent       -> 根据子目标挑动作并执行
└── reasoning=False
    └── FastAgent           -> 直接循环：思考 -> 调工具 -> 看结果 -> 再思考
```

## 5. 文件级讲解
### 5.1 ManagerAgent：规划器
文件：`droidrun/agent/manager/manager_agent.py`

它做什么：
1. 收集当前 UI 状态、截图、历史动作、错误记录。
2. 生成 Manager 专用 Prompt。
3. 让 LLM 产出计划、当前子目标、最终答案或记忆更新。
4. 把这些结果写回 shared_state，供后续执行阶段继续使用。

关键符号：
1. `ManagerAgent`
2. `_initialize_app_card_provider`
3. `_build_system_prompt`
4. `prepare_context`
5. `get_response`
6. `process_response`
7. `finalize`

怎么理解它：
可以把它类比成后端里的“调度层 + 计划生成器”。它不直接点按钮，而是先把上下文整理干净，再让模型决定“下一步最合理的子目标是什么”。

为什么要拆成多个 `@step`：
因为它继承了 `Workflow`。这是一种事件驱动流水线设计，把“准备上下文”“请求模型”“解析结果”“返回结果”拆成独立阶段，更容易串联事件和调试。

### 5.2 StatelessManagerAgent：无历史重建版规划器
文件：`droidrun/agent/manager/stateless_manager_agent.py`

它做什么：
1. 不依赖完整 message_history，而是每轮重新拼一个 prompt。
2. 适合更轻量、可重复构建的 planning 场景。

和 ManagerAgent 的区别：
1. `ManagerAgent` 更像保留多轮对话上下文。
2. `StatelessManagerAgent` 更像“每次重新提交当前快照”。

### 5.3 ExecutorAgent：执行器
文件：`droidrun/agent/executor/executor_agent.py`

它做什么：
1. 接收 Manager 给出的 subgoal。
2. 基于当前界面状态、计划、动作历史生成执行 Prompt。
3. 让模型输出一个动作 JSON。
4. 通过 `ToolRegistry.execute` 真正执行动作。

关键符号：
1. `prepare_context`
2. `get_response`
3. `process_response`
4. `execute`
5. `finalize`

教程式理解：
如果 Manager 是“项目经理”，Executor 就是“现场施工员”。它不负责规划全局，只负责把这一小步做出来。

### 5.4 FastAgent：直连执行器
文件：`droidrun/agent/fast_agent/fast_agent.py`

它做什么：
1. 在 `reasoning=False` 时直接承担整个任务。
2. 用 XML 协议让模型输出工具调用。
3. 执行工具后，把 `<function_results>` 再喂回模型，形成循环。
4. 直到模型调用 `complete` 工具宣布结束。

关键符号：
1. `_build_system_prompt`
2. `_build_user_prompt`
3. `prepare_chat`
4. `handle_llm_input`
5. `handle_llm_output`
6. `execute_code`
7. `handle_execution_result`
8. `finalize`

教程式理解：
它像一个自循环的小型代理。Manager + Executor 是“两段式”，FastAgent 是“一段式闭环”。

### 5.5 XML 解析器：模型输出到真实工具调用的桥梁
文件：`droidrun/agent/fast_agent/xml_parser.py`

它做什么：
1. 从 LLM 输出文本里抓 `<function_calls>`。
2. 把 XML 参数转成 Python 值。
3. 把工具执行结果格式化成 `<function_results>` 再塞回对话。

这段很重要，因为它决定了“模型说的话”如何被系统安全地转成“程序真的去执行的动作”。

## 6. 关键调用链
### 6.1 reasoning=True
1. `DroidAgent` 调用 `ManagerAgent.prepare_context`
2. `ManagerAgent.get_response`
3. `ManagerAgent.process_response`
4. Manager 产出 `current_subgoal`
5. `ExecutorAgent.prepare_context`
6. `ExecutorAgent.get_response`
7. `ExecutorAgent.process_response`
8. `ExecutorAgent.execute`
9. 工具经 `ToolRegistry.execute` 触发真实动作

### 6.2 reasoning=False
1. `FastAgent.prepare_chat`
2. `FastAgent.handle_llm_input`
3. `FastAgent.handle_llm_output`
4. `FastAgent.execute_code`
5. `FastAgent.handle_execution_result`
6. 回到下一轮 `FastAgentInputEvent`

## 7. Python 知识点联动
### 7.1 `@step` 装饰器
项目位置：多个 Agent 的工作流方法前。

作用：
把普通异步函数注册成工作流节点。

类比：
像 Spring 注解式流程节点，或某种状态机里的 transition handler。

最小示例：
```python
from llama_index.core.workflow import step

class Demo:
    @step
    async def run_part(self, ctx, ev):
        return ev
```

### 7.2 `async def`
项目位置：三个 Agent 的绝大多数核心步骤。

作用：
让截图、状态抓取、模型调用、工具执行等 I/O 操作非阻塞串联。

新手常见误区：
1. 忘记 `await`。
2. 把异步函数当普通函数直接调用。

### 7.3 类型提示里的 `| None`
项目位置：如 `ActionContext | None`、`Type[BaseModel] | None`。

作用：
表示“这个参数可能是某类型，也可能是空值”。

类比：
类似 TypeScript 的 `Foo | null`。

### 7.4 `dict` / `list` 推导与 `zip(..., strict=True)`
项目位置：Manager 与 Executor 构建历史记录时。

作用：
把多份并行历史压成结构化对象，并确保长度不一致时直接报错。

### 7.5 数据类 `@dataclass`
项目位置：`xml_parser.py` 中 `ToolCall`、`ToolResult`。

作用：
用更轻量的方式描述“一个工具调用”和“一个工具结果”。

类比：
类似 Java 的简单 DTO / record。

## 8. 源码注释落点
本轮已计划把教程式注释放到这些关键起始位置前一行：
1. `ManagerAgent` 类与其四个工作流步骤
2. `ExecutorAgent` 类与其五个工作流步骤
3. `FastAgent` 类与其关键循环步骤
4. `parse_tool_calls` 与 `format_tool_results`

## 9. 证据清单
1. `droidrun/agent/manager/manager_agent.py`：`ManagerAgent`、`prepare_context`、`get_response`、`process_response`
2. `droidrun/agent/manager/stateless_manager_agent.py`：`StatelessManagerAgent`
3. `droidrun/agent/executor/executor_agent.py`：`ExecutorAgent`、`execute`
4. `droidrun/agent/fast_agent/fast_agent.py`：`FastAgent`、`handle_llm_input`、`execute_code`
5. `droidrun/agent/fast_agent/xml_parser.py`：`parse_tool_calls`、`format_tool_results`

## 10. [不确定] 项
1. [不确定] Executor 最终可调动作全集的业务语义还未逐个下钻到 `agent/utils/actions.py`。
2. [不确定] FastAgent 在并行工具模式开启时的边界行为，还需要结合 prompt 与实际执行测试确认。

## 11. 覆盖率与下一轮
### 11.1 本轮已覆盖
1. `droidrun/agent/manager/manager_agent.py`
2. `droidrun/agent/manager/stateless_manager_agent.py`
3. `droidrun/agent/executor/executor_agent.py`
4. `droidrun/agent/fast_agent/fast_agent.py`
5. `droidrun/agent/fast_agent/xml_parser.py`

### 11.2 下一轮建议
1. `droidrun/agent/utils/actions.py`
2. `droidrun/agent/common/*`
3. `droidrun/agent/droid/events.py`
4. `droidrun/tools/ui/*`
5. `droidrun/cli/event_handler.py`

## 12. 小结
这一轮的核心收获是：你已经能把 droidrun 的 Agent 子系统拆成三种思维模式来看了。Manager 负责规划，Executor 负责落地单步动作，FastAgent 负责一体化快速闭环。接下来只要继续分析动作函数和 UI 状态对象，整个执行系统就会变得非常具体。