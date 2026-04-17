# 28 Telemetry 事件与导出教程（Events、Tracker、Init）

承接：第 27 轮讲完配置底座，这一轮回到 telemetry 主线，补齐事件模型、追踪发送器与对外导出层之间的配合关系。

## 1. 学习目标
1. 理解 telemetry 事件模型分别描述什么执行阶段。
2. 理解 tracker 如何把事件转换为 PostHog 上报。
3. 理解 telemetry 包级导出如何给上层提供稳定接入口。

## 2. 分析范围
1. droidrun/telemetry/events.py
2. droidrun/telemetry/tracker.py
3. droidrun/telemetry/__init__.py

## 3. 事件模型：telemetry/events.py
它做什么：
1. `TelemetryEvent` 作为所有事件的基类。
2. `DroidAgentInitEvent` 记录启动配置快照。
3. `PackageVisitEvent` 记录跨应用访问轨迹。
4. `DroidAgentFinalizeEvent` 记录任务完成结果与访问聚合指标。

关键点：
1. Init 事件更偏“配置画像”。
2. PackageVisit 事件更偏“运行过程画像”。
3. Finalize 事件更偏“结果画像”。

## 4. 上报执行器：telemetry/tracker.py
它做什么：
1. 读取环境变量决定是否启用 telemetry。
2. 生成并持久化匿名 user_id。
3. 为每次运行生成 run_id。
4. `capture` 把 Pydantic 事件转换成 PostHog 属性。
5. `flush` 在退出前限时刷新待发事件。

教程式理解：
tracker 是“事件发送泵”，events 是“数据契约”，两者分离后便于未来替换后端或扩展事件类型。

## 5. 包级导出：telemetry/__init__.py
它做什么：
1. 重导出 capture / flush / print_telemetry_message。
2. 重导出三类核心事件模型。
3. 让外部模块通过单入口接入 telemetry。

## 6. Python 知识点联动
### 6.1 事件模型分层
项目位置：droidrun/telemetry/events.py

作用：
把“配置、过程、结果”三个阶段拆成独立统计事件，便于后续分析。

### 6.2 Pydantic -> 字典序列化
项目位置：droidrun/telemetry/tracker.py

作用：
统一把结构化模型转换为外部分析系统可接受的属性对象。

### 6.3 包级门面导出
项目位置：droidrun/telemetry/__init__.py

作用：
稳定 API 面，减少调用方受内部文件拆分影响。

## 7. 源码注释落点
本轮已补充教程注释的位置：
1. telemetry/events.py 的三类核心事件语义说明
2. tracker.py 与 __init__.py 沿用前轮已有关键注释

## 8. 证据清单
1. droidrun/telemetry/events.py: DroidAgentInitEvent, PackageVisitEvent, DroidAgentFinalizeEvent
2. droidrun/telemetry/tracker.py: is_telemetry_enabled, capture, flush
3. droidrun/telemetry/__init__.py: module exports

## 9. [不确定] 项
1. [不确定] 当前事件粒度是否足以支持更细的失败根因分析，后续可能需要补充工具级或模型级 telemetry。
2. [不确定] PostHog 端的属性保留策略是否会对长文本字段造成截断，建议联调确认。

## 10. 覆盖率与下一轮
### 10.1 本轮已覆盖
1. droidrun/telemetry/events.py
2. droidrun/telemetry/tracker.py
3. droidrun/telemetry/__init__.py

### 10.2 下一轮建议
1. droidrun/telemetry/phoenix.py
2. droidrun/telemetry/langfuse_processor.py
3. droidrun/agent/utils/tracing_setup.py（与 telemetry 后端联动回顾）

## 11. 小结
这一轮把 telemetry 的主干链路讲清楚了：events 定义统计语义，tracker 负责发送与持久标识，__init__ 提供稳定接入面。