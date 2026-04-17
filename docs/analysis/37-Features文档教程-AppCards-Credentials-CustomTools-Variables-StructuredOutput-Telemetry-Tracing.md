# 37 Features文档教程（AppCards、Credentials、CustomTools、Variables、StructuredOutput、Telemetry、Tracing）

承接：前面已经把 `config/` 资源层和 `manager` prompt 模板补齐，但 `docs/features/` 这一组正式文档同样值得单独分析。它们面向用户解释“Droidrun 具体能做什么”，本质上是把源码里的离散能力重新整理成可组合的产品功能面。

## 1. 学习目标
1. 理解 `docs/features/` 不是重复 README，而是对核心能力的正式分面说明。
2. 理解这些页面分别对应源码中的哪一层能力：app cards、凭证、工具扩展、变量注入、结构化输出、遥测、追踪。
3. 理解这一组文档如何把“能力”从实现细节提升为用户可配置、可组合的接口。

## 2. 分析范围
1. `docs/features/app-cards.mdx`
2. `docs/features/credentials.mdx`
3. `docs/features/custom-tools.mdx`
4. `docs/features/custom-variables.mdx`
5. `docs/features/structured-output.mdx`
6. `docs/features/telemetry.mdx`
7. `docs/features/tracing.mdx`

排除项：
1. `docs/concepts/` 的底层概念解释
2. `docs/sdk/` 的类级 API 参考
3. `droidrun-examples` 仓库的外部示例实现

## 3. 结构定位
文字图：
1. `concepts/` 解释系统原理。
2. `features/` 解释可直接使用的能力面。
3. `guides/` 解释如何落地使用这些能力。
4. `sdk/` 解释具体类与参数接口。

所以 `features/` 的角色不是讲底层源码，而是把“源码里已经存在的能力”翻译成产品说明书。

## 4. 文件级讲解（按能力分组）
### 4.1 领域知识与安全输入
1. `app-cards.mdx`：解释 App Card 如何按包名自动注入应用特定知识，对应前面已经分析过的 `config/app_cards/*` 与 app-card provider 链路。
2. `credentials.mdx`：解释凭证的两种接入方式，强调 Agent 通过 `type_secret` 使用 secret ID 而不是直接暴露值，对应 `CredentialManager` 与 `FileCredentialManager`。
3. 这一组页面的共同点：都在解决“让 Agent 知道额外信息，但尽量不把敏感值或特定知识硬编码进 prompt”。

### 4.2 可扩展执行能力
1. `custom-tools.mdx`：把“注册 Python 函数给 Agent 调用”的能力包装成用户可理解的扩展点，对应 `ToolRegistry`、`ActionContext`、自定义工具签名约定。
2. `custom-variables.mdx`：解释变量如何进入 `DroidAgentState.custom_variables`，并通过自定义 Jinja2 prompt 或 `ctx.shared_state.custom_variables` 暴露给 Agent 和工具。
3. 这一组页面的共同点：都在讲“如何把你的业务数据或业务函数接进 Droidrun”。

### 4.3 输出与可观测性
1. `structured-output.mdx`：把 Pydantic 模型、两阶段提取、`StructuredOutputAgent` 的工作方式讲成一个可直接上手的功能。
2. `telemetry.mdx`：说明匿名遥测的开关与边界，并明确当前以环境变量为主。
3. `tracing.mdx`：说明 Phoenix / Langfuse tracing 与 trajectory recording 的区别，帮助用户区分“云端可观测”与“本地调试留痕”。
4. 这一组页面的共同点：都在回答“任务执行后如何拿到结果、如何观察过程、如何调试”。

## 5. 这一组文档传达的产品分层
1. `app-cards`、`credentials` 负责给 Agent 注入额外上下文与安全输入能力。
2. `custom-tools`、`custom-variables` 负责把用户自己的业务逻辑接进来。
3. `structured-output` 负责把自然语言完成结果收束成 typed data。
4. `telemetry`、`tracing` 负责让运行过程可观察。

这说明 `features/` 的真正价值，是把 Droidrun 从“能点手机的 agent”提升为“可配置、可集成、可观测的自动化框架”。

## 6. 与源码分析轮次的对应关系
1. `app-cards.mdx` 对应第 23 轮 app cards provider，以及第 35 轮 config 资源层。
2. `credentials.mdx` 对应第 31 轮凭证管理，以及第 35 轮 `credentials_example.yaml`。
3. `custom-tools.mdx`、`custom-variables.mdx` 对应第 12 轮动作协议与 `ActionContext`，也关联 `ToolRegistry`。
4. `structured-output.mdx` 对应第 32 轮 `StructuredOutputAgent`。
5. `telemetry.mdx`、`tracing.mdx` 对应第 28、29 轮可观测性子系统。

## 7. 初学者最容易忽略的点
1. `custom-variables.mdx` 明确指出默认 prompt 不会自动渲染变量，必须自定义 prompt 才能让 Agent 在提示词里“看见”变量。
2. `credentials.mdx` 的核心不是“怎么存密码”，而是“Agent 只看 secret ID，不看 secret value”。
3. `structured-output.mdx` 不是执行期间边走边结构化，而是任务结束后再做一次提取。
4. `telemetry.mdx` 还特地指出当前 `telemetry.enabled` 配置项并未真正驱动系统，这种“文档写出真实边界”的做法很重要。
5. `tracing.mdx` 把 tracing 与 trajectory recording 明确拆开，避免用户把云端 trace 和本地截图轨迹混为一谈。

## 8. 证据清单
1. `docs/features/app-cards.mdx`
2. `docs/features/credentials.mdx`
3. `docs/features/custom-tools.mdx`
4. `docs/features/custom-variables.mdx`
5. `docs/features/structured-output.mdx`
6. `docs/features/telemetry.mdx`
7. `docs/features/tracing.mdx`

## 9. [不确定] 项
1. [不确定] `telemetry.enabled` 配置项未来是否会与环境变量行为统一，目前文档明确说还没有接通。
2. [不确定] `features/` 后续是否还会继续扩展到 macro、portal 或外部 agent 之类主题，目前这些更分散在别的目录。

## 10. 覆盖率与下一轮
### 10.1 本轮已覆盖
1. `docs/features/app-cards.mdx`
2. `docs/features/credentials.mdx`
3. `docs/features/custom-tools.mdx`
4. `docs/features/custom-variables.mdx`
5. `docs/features/structured-output.mdx`
6. `docs/features/telemetry.mdx`
7. `docs/features/tracing.mdx`

### 10.2 下一轮建议
1. `docs/guides/` 这一层如何把 CLI、设备安装、Docker 落地流程串成用户 onboarding 路径。
2. `docs/sdk/` 这一层如何把 `DroidAgent`、driver、config 暴露成稳定 API 面。

## 11. 小结
`docs/features/` 这一组页面，本质上是在回答“Droidrun 作为产品到底提供了哪些关键能力，以及这些能力怎样组合使用”。它和源码轮次是一一对应的，但视角更偏用户能力面，而不是内部实现面。