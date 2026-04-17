# 39 SDK文档教程（DroidAgent、Drivers、Configuration、Reference）

承接：`features/` 负责讲能力，`guides/` 负责讲上手，而 `docs/sdk/` 则负责把这些能力落到具体类、参数和调用方式上。它是正式 API 参考层，也是源码分析与用户接入之间最直接的桥梁。

## 1. 学习目标
1. 理解 `docs/sdk/` 在整个文档站中的职责是“稳定 API 面说明”。
2. 理解 `DroidAgent`、driver、config、reference 四类页面如何共同构成 SDK 文档体系。
3. 理解这一层与前面源码分析轮次之间的映射关系。

## 2. 分析范围
1. `docs/sdk/droid-agent.mdx`
2. `docs/sdk/adb-tools.mdx`
3. `docs/sdk/base-tools.mdx`
4. `docs/sdk/configuration.mdx`
5. `docs/sdk/ios-tools.mdx`
6. `docs/sdk/reference.mdx`

排除项：
1. `docs/features/` 的能力说明
2. `docs/guides/` 的操作流程说明
3. 自动生成 API 站点的构建过程

## 3. 结构定位
文字图：
1. `droid-agent.mdx` 讲顶层入口类 `DroidAgent`。
2. `adb-tools.mdx`、`ios-tools.mdx`、`base-tools.mdx` 讲设备驱动与工具抽象。
3. `configuration.mdx` 讲 `DroidConfig` 及各子配置对象。
4. `reference.mdx` 讲整个 SDK 参考入口与导航。

所以 `sdk/` 这一层，本质上是在回答“如果我要写代码接入 Droidrun，应该实例化什么、传什么、看什么返回值”。

## 4. 文件级讲解
### 4.1 droid-agent.mdx：顶层入口 API
1. 做什么：把 `DroidAgent` 的构造参数、运行方式、返回结果、常见初始化模式讲清楚。
2. 关键价值：这是用户最先接触的 SDK 对象，也是把前面所有子系统收束到一个入口的页面。
3. 与源码关系：直接映射 `droidrun/agent/droid/droid_agent.py`，并把 reasoning / fast-agent 双路径以文档化方式公开出来。

### 4.2 adb-tools.mdx / ios-tools.mdx：平台驱动 API
1. 做什么：分别说明 Android 与 iOS 驱动的构造方式、支持方法、平台差异和限制。
2. 关键价值：把“设备控制”从 agent 叙事中拆出来，允许用户把 Droidrun 也当作原始驱动层使用。
3. 与源码关系：对应 `AndroidDriver`、`IOSDriver` 及其能力集 `supported` / `supported_buttons`。

### 4.3 base-tools.mdx：抽象层 API
1. 做什么：解释 `DeviceDriver`、`StateProvider`、`UIState`、`ActionContext`、`ToolRegistry`、`ActionResult` 这些横向基础对象。
2. 关键价值：这页相当于“工具抽象总图”，对理解自定义动作与扩展工具尤其重要。
3. 与源码关系：覆盖 driver base、UI state、动作上下文与工具注册等多个子系统，是 SDK 层最接近内部架构的一页。

### 4.4 configuration.mdx：配置 API
1. 做什么：集中解释 `DroidConfig` 与 `AgentConfig`、`ManagerConfig`、`FastAgentConfig`、`DeviceConfig`、`TracingConfig` 等子配置。
2. 关键价值：把 YAML / Python 配置的等价接口收束到一页，降低接入成本。
3. 与源码关系：对应前面第 7、27、33、35 轮分析过的配置系统、路径、prompt 配置和 stateless 开关。

### 4.5 reference.mdx：参考入口页
1. 做什么：作为 SDK 文档的导航页，把核心类页面串起来。
2. 关键价值：它本身信息不多，但承担“把参考站点变成一个完整入口”的作用。
3. 与源码关系：它不映射具体逻辑，而是映射文档信息架构。

## 5. 这组文档的设计特点
1. 大量使用“签名 + 参数表 + 示例”的写法，明显偏 API reference。
2. 一边给最小可运行示例，一边暴露高级参数，兼顾初学者和嵌入式接入场景。
3. 不只讲 `DroidAgent`，也把 driver / state / tool registry 暴露出来，说明项目并不想把用户锁死在单一高层入口。
4. Android 与 iOS 页面对 unsupported 能力写得比较明确，这对跨平台预期管理很重要。

## 6. 与前面源码分析轮次的对应关系
1. `droid-agent.mdx` 对应第 1、2、33、34 轮里涉及的顶层 workflow 与 manager 分叉。
2. `adb-tools.mdx`、`ios-tools.mdx`、`base-tools.mdx` 对应第 16、18、19、20 轮的驱动与状态采集体系。
3. `configuration.mdx` 对应第 7、27、35、36 轮的配置与 prompt 资源层。
4. `reference.mdx` 则像把这些轮次的对象重新组织成“开发者查阅入口”。

## 7. 初学者最容易忽略的点
1. `DroidAgent` 文档明确把 `llms` 设计成“单 LLM / 多 LLM 字典 / 从 config 加载”三种模式，这代表 SDK 并不强迫单一接入方式。
2. `configuration.mdx` 里 `prompts` 参数强调传的是模板字符串而不是文件路径，这和 config 文件里写模板路径是两个不同入口。
3. `base-tools.mdx` 说明自定义工具应通过 `ActionContext` 获取 driver、state 和 credential manager，而不是直接跨层依赖内部对象。
4. Android / iOS 驱动页明确写出哪些方法声明支持、哪些只是 API 兼容但未完全实现，这种透明度很高。

## 8. 证据清单
1. `docs/sdk/droid-agent.mdx`
2. `docs/sdk/adb-tools.mdx`
3. `docs/sdk/base-tools.mdx`
4. `docs/sdk/configuration.mdx`
5. `docs/sdk/ios-tools.mdx`
6. `docs/sdk/reference.mdx`

## 9. [不确定] 项
1. [不确定] 这些 SDK 页面是否完全手写维护，还是部分内容来自自动化生成后再人工润色，从现有页面难以完全确认。
2. [不确定] `reference.mdx` 后续是否会扩展到更细粒度对象索引，目前还是以几个大类入口为主。

## 10. 覆盖率与下一轮
### 10.1 本轮已覆盖
1. `docs/sdk/droid-agent.mdx`
2. `docs/sdk/adb-tools.mdx`
3. `docs/sdk/base-tools.mdx`
4. `docs/sdk/configuration.mdx`
5. `docs/sdk/ios-tools.mdx`
6. `docs/sdk/reference.mdx`

### 10.2 下一轮建议
1. 单独补一轮“文档站信息架构教程”，把 `overview / concepts / features / guides / sdk / analysis` 六层关系画清楚。
2. 回到仍未充分展开的 provider 配置联动链路。

## 11. 小结
`docs/sdk/` 是 Droidrun 文档体系里最像“正式开发者接口说明书”的一层。它把前面很多已经分析过的内部对象，重新组织成可直接调用、可查参数、可抄示例的 SDK 入口，因此也应该被纳入文档化分析范围。