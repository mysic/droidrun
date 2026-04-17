# 32 Oneflows任务编排教程（AppStarter、StructuredOutputAgent、OpenApp）

承接：第 30 轮把 TUI 的交互入口拆开了，第 31 轮把凭证边界讲清了。这一轮继续下钻 `agent/oneflows/`，专门解释 droidrun 如何把“单个工具动作”升级成“带决策的小工作流”。

## 1. 学习目标
1. 理解 `AppStarter` 如何把“按描述打开应用”封装成独立 workflow。
2. 理解 `StructuredOutputAgent` 如何在主任务结束后做结构化结果提取。
3. 理解 `actions.open_app` 与 `DroidAgent` 如何在主链中接入这些 oneflow。

## 2. 分析范围
1. `droidrun/agent/oneflows/app_starter_workflow.py`
2. `droidrun/agent/oneflows/structured_output_agent.py`
3. `droidrun/agent/utils/actions.py` 中 `open_app`
4. `droidrun/agent/droid/droid_agent.py` 中结构化输出收尾逻辑

排除项：
1. `manager` / `executor` 的完整主循环
2. `ToolRegistry` 的注册与执行细节
3. `LLM` 加载与 provider 选择逻辑

## 3. 架构/流程总览
文字图：
1. 模型或用户请求触发 `open_app` 动作。
2. `actions.open_app()` 创建 `AppStarter` workflow。
3. `AppStarter.open_app_step()` 读取已安装应用列表，调用 LLM 选择最匹配的 package。
4. workflow 再调用 `driver.start_app()`，把结果归一成字符串返回给动作层。
5. 主 Agent 结束时，如果用户要求结构化输出，则创建 `StructuredOutputAgent`。
6. `StructuredOutputAgent.extract_structured_output()` 用 `structured_predict` 将最终答案转成 Pydantic 对象。
7. 主 Agent 把结构化对象挂到最终 `ResultEvent.structured_output` 中返回。

## 4. 文件级讲解（按职责分组）
### 4.1 应用打开工作流
1. 文件：`droidrun/agent/oneflows/app_starter_workflow.py`
2. 做什么：封装“按自然语言描述打开应用”的完整流程，而不是让普通动作函数自己拼 prompt、查 app 列表、解析 JSON。
3. 关键符号：`AppStarter`、`open_app_step`
4. 调用关系：`actions.open_app()` -> `AppStarter.run(app_description=...)` -> `driver.get_apps()` / `acomplete_with_retries()` / `driver.start_app()`
5. 初学者易错点：
   - 这不是通用 Agent，而是只有一个 step 的专用 workflow。
   - LLM 返回值不一定是纯 JSON，所以代码先截取最内层 `{...}` 再解析。
   - workflow 负责决策和错误归一，真正设备启动还是由 driver 完成。

### 4.2 结构化输出工作流
1. 文件：`droidrun/agent/oneflows/structured_output_agent.py`
2. 做什么：把主 Agent 的最终自然语言结果，二次提取为 Pydantic 结构化对象。
3. 关键符号：`StructuredOutputAgent`、`extract_structured_output`
4. 调用关系：`DroidAgent` 收尾逻辑 -> `StructuredOutputAgent.run()` -> `astructured_predict_with_retries()` -> `StopEvent`
5. 初学者易错点：
   - 这里的 prompt 很短，真正的输出约束主要来自 `pydantic_model` schema。
   - 失败时不会抛出异常中断主流程，而是返回 `success=False` 的结果字典。
   - 它发生在“任务结束之后”，不是让主 Agent 全程都按结构化 schema 说话。

### 4.3 上下游接入点
1. 文件：`droidrun/agent/utils/actions.py`
2. 做什么：在工具动作层把 `open_app` 委托给 `AppStarter`，对上仍保持普通 `ActionResult` 接口。
3. 关键符号：`open_app`
4. 调用关系：`ToolRegistry.execute()` -> `actions.open_app()` -> `AppStarter` -> `ActionResult`
5. 初学者易错点：
   - 动作函数没有直接做模糊匹配，而是显式转交给专用 workflow。
   - workflow 返回字符串后，动作层还要再做一次成功/失败归一。

### 4.4 主 Agent 收尾整合
1. 文件：`droidrun/agent/droid/droid_agent.py`
2. 做什么：在最终答案已经产生后，可选触发 `StructuredOutputAgent` 做结果后处理。
3. 关键符号：`StructuredOutputAgent(...)`、`handler.stream_events()`、`result.structured_output`
4. 调用关系：主 workflow 完成 -> 构造 `ResultEvent` -> 条件触发结构化提取 -> 返回最终结果
5. 初学者易错点：
   - 结构化提取是后处理层，不会影响主任务本身的成功与否。
   - 嵌套 workflow 的事件仍继续转发到外层，CLI/TUI 能看到内部过程。

## 4.2 源码注释落点
1. 需要补充注释的类/函数：`AppStarter.open_app_step`、`StructuredOutputAgent.extract_structured_output`、`actions.open_app`、`DroidAgent` 结构化输出收尾段
2. 注释写入位置：
   - app 列表获取前、JSON 解析前、`driver.start_app` 前
   - `PromptTemplate` 构造前、异常包装处
   - `AppStarter` 创建前、动作结果归一处
   - `StructuredOutputAgent` 创建前、嵌套事件转发前
3. 注释解释目标：说明 oneflow 的职责边界、为什么要拆成专用 workflow、以及它如何与主 Agent / 动作层协作

## 5. Python 知识点联动
1. 语法/关键字/内置函数：类继承、协程、异常捕获、字典结果归一
2. 在本项目中的位置：`Workflow` 子类、`@step` 协程、`StopEvent(result=...)`、`ActionResult`
3. 为什么这样写：
   - 把复杂动作封装进 workflow，能复用事件流、超时控制和调试体验。
   - 把结构化输出放到后处理层，能避免主推理链被严格 schema 限制。
4. 最小示例：
```python
class DemoFlow(Workflow):
    @step
    async def only_step(self, ev: StartEvent, ctx: Context) -> StopEvent:
        data = await some_async_call()
        return StopEvent(result={"value": data, "success": True})
```
5. 常见错误与修正：
   - 错误：让普通工具函数同时做设备调用、LLM 决策、复杂解析。
   - 修正：把这类多阶段逻辑抽成专用 workflow。
   - 错误：结构化提取失败就抛异常中断主结果。
   - 修正：返回带 `success=False` 的结果，让主任务结果仍可交付。

## 6. 证据清单
1. `droidrun/agent/oneflows/app_starter_workflow.py`：`AppStarter`、`open_app_step`
2. `droidrun/agent/oneflows/structured_output_agent.py`：`StructuredOutputAgent`、`extract_structured_output`
3. `droidrun/agent/utils/actions.py`：`open_app`
4. `droidrun/agent/droid/droid_agent.py`：最终结果中的结构化提取分支

## 7. [不确定] 项
1. [不确定] `AppStarter` 当前把所有已安装应用都喂给 LLM，在应用数量很多时 prompt 长度是否会成为瓶颈。
2. [不确定] `StructuredOutputAgent` 的失败恢复目前只记录日志，是否需要附带更细粒度的 schema 校验信息给上层调用者。

## 8. 覆盖率与下一轮
### 8.1 本轮已覆盖
1. `droidrun/agent/oneflows/app_starter_workflow.py`
2. `droidrun/agent/oneflows/structured_output_agent.py`
3. `droidrun/agent/utils/actions.py` 中 `open_app`
4. `droidrun/agent/droid/droid_agent.py` 中结构化输出整合

### 8.2 下一轮建议
1. `droidrun/agent/providers/registry.py` 与 TUI / configure wizard 的联动边界
2. `droidrun/agent/manager/manager_agent.py` 与 `stateless_manager_agent.py` 的差异化执行路径
3. `droidrun/agent/common/` 中 workflow 事件与共享协议的更细粒度拆解

## 9. 小结
这一轮可以把 `oneflows` 理解为“轻量专用子流程”。它们不像主 Agent 那样负责整轮任务，也不像普通动作那样只做一步设备操作，而是把一个高频、带决策的局部问题单独封装起来：`AppStarter` 解决“按描述找应用”，`StructuredOutputAgent` 解决“把最终答案变成结构化结果”。这种拆分让主链更稳定，也更容易调试和复用。
