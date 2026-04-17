# 29 Tracing后端教程（Phoenix、LangfuseProcessor、TracingSetup）

承接：第 28 轮把 telemetry 主干的事件模型和发送器讲清楚了，这一轮继续下钻 tracing 后端，补齐 Phoenix 接入、Langfuse 自定义 SpanProcessor，以及 tracing_setup.py 如何把两者挂接到 Droidrun 运行时。

## 1. 学习目标
1. 理解 Phoenix 集成为什么要单独包装 callback handler。
2. 理解 LangfuseSpanProcessor 为什么不仅做 span 转发，还要做消息改写和图片上传。
3. 理解 tracing_setup.py 如何作为统一入口，在运行期选择具体 tracing 后端。

## 2. 分析范围
1. droidrun/telemetry/phoenix.py
2. droidrun/telemetry/langfuse_processor.py
3. droidrun/agent/utils/tracing_setup.py

## 3. Phoenix 后端：telemetry/phoenix.py
它做什么：
1. `arize_phoenix_callback_handler` 创建并配置 OpenTelemetry exporter。
2. 把 `PHOENIX_URL` 和 `PHOENIX_PROJECT_NAME` 这样的环境变量映射到 tracing 资源配置。
3. `clean_span` 提供一个更干净的 span 命名装饰器，避免 trace 里出现过多类名前缀噪音。

教程式理解：
Phoenix 分支更像“标准 tracing 接线层”。它的重点不是改写业务数据，而是把 LlamaIndex 的执行过程导出到 Phoenix，并顺手把 span 名称变得更适合人看。

关键点：
1. `arize_phoenix_callback_handler` 内部创建 `TracerProvider` 和 `OTLPSpanExporter`，说明 Phoenix 主要依赖标准 OpenTelemetry 协议。
2. `clean_span` 同时兼容同步与异步函数，甚至额外处理返回 `Future` 的情况，保证 span 真正覆盖任务生命周期。
3. `active_span_id` 和 `dispatcher.span_enter/span_exit` 的手动调用，说明这里是在对接 LlamaIndex 内部 instrumentation 机制，而不是简单包一层装饰器。

## 4. Langfuse 后端：telemetry/langfuse_processor.py
它做什么：
1. 继承官方 `LangfuseSpanProcessor`，增加 Droidrun 特有的 tracing 增强。
2. 用 `ContextVar` 存储当前 Agent、根 span、最近步骤 span，解决并发环境下的上下文传递。
3. 在 `on_start` 注入 Agent 配置、LLM 角色、视觉模式、记忆长度等运行元数据。
4. 在 `on_end` 把 LlamaIndex 的 block 消息结构转换为 Langfuse 更适合展示的 content 结构。
5. 对图片执行异步上传，把大体积图片从 span 文本属性中搬运到 Langfuse blob storage。

教程式理解：
这个处理器不是“单纯上传 span”，而是一个“tracing 数据整理器”。它把 Droidrun 运行时的上下文、图片、消息块、工具调用都整理成 Langfuse 控制台容易理解的形态。

关键点：
1. `set_current_agent` / `set_root_span_context` / `set_last_step_span_context` 用 `ContextVar` 替代全局变量，能在多线程、多协程环境中更安全地共享 tracing 状态。
2. `_extract_agent_input` 从 Agent 中提取 goal、reasoning、device、vision、模型信息，说明 tracing 不只是采样调用，还会保留运行配置快照。
3. `_process_field`、`_transform_and_set_field`、`_convert_blocks_to_content` 组成一条消息转换流水线，把 block 风格消息改写为 Langfuse 友好的 content 列表。
4. `_upload_image_to_storage` 先做体积校验和 SHA-256 去重，再异步提交上传任务，说明图片是作为独立媒体资源处理，而不是内嵌到 span 文本里。
5. `_process_screenshot_span` 会把截图 span 重写成图片消息，这使得自动化执行中的“现场截图”也能进入同一条 trace 视图。

## 5. 统一入口：agent/utils/tracing_setup.py
它做什么：
1. `setup_tracing` 根据 `TracingConfig.provider` 选择 Phoenix 或 Langfuse。
2. 通过 `_tracing_initialized`、`_tracing_provider` 避免重复初始化。
3. Phoenix 分支会先检查服务是否可达，再安装 handler。
4. Langfuse 分支会设置环境变量、验证认证、安装 LlamaIndex instrumentor、修补 Pydantic 编码器，再挂载自定义 `LangfuseSpanProcessor`。
5. `apply_session_context` 给后续 span 注入 session_id 和 user_id。
6. `record_langfuse_screenshot` 用独立 span 上报截图，为 Langfuse 图片上传链路提供入口。

教程式理解：
tracing_setup.py 是 tracing 的“总开关控制台”。调用方只关心配置，具体用 Phoenix 还是 Langfuse、是否需要打补丁、截图怎么入 trace，都在这里封装。

## 6. Python 知识点联动
### 6.1 ContextVar
项目位置：droidrun/telemetry/langfuse_processor.py

作用：
在并发场景下保存“当前 Agent / 当前 span”的上下文，比普通全局变量更安全。

### 6.2 装饰器工厂
项目位置：droidrun/telemetry/phoenix.py

作用：
`clean_span(span_name)` 先接收 span 名称，再返回真正装饰函数，是 Python 中很常见的“带参数装饰器”写法。

### 6.3 继承并覆写框架处理器
项目位置：droidrun/telemetry/langfuse_processor.py

作用：
通过继承官方 `LangfuseSpanProcessor`，项目可以保留原始行为，同时只在 `on_start`、`on_end` 等关键钩子追加 Droidrun 特有逻辑。

### 6.4 延迟导入
项目位置：droidrun/agent/utils/tracing_setup.py

作用：
只有在启用某个 tracing provider 时才导入对应依赖，减少可选依赖未安装时对主流程的影响。

## 7. 源码注释落点
本轮已补充教程注释的位置：
1. telemetry/phoenix.py 的 async/sync span 包装逻辑
2. telemetry/langfuse_processor.py 的 `on_start`、`on_end`、消息转换、截图处理、图片上传关键点
3. tracing_setup.py 沿用第 24 轮已有关键注释

## 8. 证据清单
1. droidrun/telemetry/phoenix.py: `arize_phoenix_callback_handler`, `clean_span`
2. droidrun/telemetry/langfuse_processor.py: `LangfuseSpanProcessor.on_start`, `on_end`, `_process_field`, `_convert_blocks_to_content`, `_upload_image_to_storage`
3. droidrun/agent/utils/tracing_setup.py: `setup_tracing`, `_setup_phoenix_tracing`, `_setup_langfuse_tracing`, `apply_session_context`, `record_langfuse_screenshot`

## 9. [不确定] 项
1. [不确定] Langfuse 官方父类未来版本若调整 `on_end` 或内部属性格式，这个自定义处理器的兼容性需要再次验证。
2. [不确定] 图片上传线程池上限 50 是否适合所有部署环境，若部署在受限容器里，可能需要进一步参数化。

## 10. 覆盖率与下一轮
### 10.1 本轮已覆盖
1. droidrun/telemetry/phoenix.py
2. droidrun/telemetry/langfuse_processor.py
3. droidrun/agent/utils/tracing_setup.py

### 10.2 下一轮建议
1. 继续扫描 `droidrun` 中尚未做教程化拆解的边角模块
2. 优先检查是否还有未单独成篇的 provider / config / cli 辅助文件

## 11. 小结
这一轮把 tracing 后端的真实实现补齐了：Phoenix 负责标准化导出，LangfuseProcessor 负责把运行时上下文、消息和图片整理成可观察数据，tracing_setup.py 则把两类 provider 收束成统一初始化入口。