# 24 Prompt 与轨迹追踪教程（PromptResolver、Trajectory、TracingSetup）

承接：第 23 轮讲完 AppCards 供给链，这一轮补齐“提示词覆写 + 轨迹复盘 + tracing 初始化”三块通用能力。

## 1. 学习目标
1. 理解 PromptResolver 如何支持运行时提示词覆写。
2. 理解 Trajectory 如何组织、加载和统计执行轨迹。
3. 理解 TracingSetup 如何初始化 Phoenix/Langfuse 并管理上下文。

## 2. 分析范围
1. droidrun/agent/utils/prompt_resolver.py
2. droidrun/agent/utils/trajectory.py
3. droidrun/agent/utils/tracing_setup.py

## 3. Prompt 覆写层：prompt_resolver.py
它做什么：
1. 保存运行时传入的 `custom_prompts`。
2. 按 key 读取自定义模板（fast_agent/manager/executor）。
3. 暴露合法 key 列表用于输入校验。

关键点：
1. 内存模板优先，文件模板回退由上层 `PromptLoader` 负责。
2. 运行时覆写让实验和 A/B prompt 调参成本更低。

## 4. 轨迹工具层：trajectory.py
它做什么：
1. 创建唯一轨迹目录（时间戳 + UUID）。
2. 聚合事件、截图、宏动作并转换为可序列化数据。
3. 提供轨迹/宏加载与摘要统计工具。

关键能力：
1. `load_trajectory_folder`：一次性读取 trajectory + macro + gif。
2. `load_macro_sequence`：兼容文件或目录路径。
3. `get_trajectory_statistics`：输出计划/执行步骤与成功失败分布。

教程式理解：
Trajectory 是“可回放、可审计”的诊断底座，帮助你从结果反推执行过程。

## 5. Tracing 初始化层：tracing_setup.py
它做什么：
1. 按配置初始化 tracing provider（Phoenix 或 Langfuse）。
2. 维护 session_id/user_id 并写入 tracing context。
3. 为 Langfuse 提供截图 span 附件能力。

关键点：
1. `setup_tracing` 具备“仅初始化一次”的全局保护。
2. Phoenix 分支先做可达性检查再启用。
3. Langfuse 分支包含 instrumentation、processor 注入和认证校验。

## 6. Python 知识点联动
### 6.1 运行时策略注入
项目位置：droidrun/agent/utils/prompt_resolver.py

作用：
在不改配置文件的情况下快速覆写系统行为。

### 6.2 序列化与离线分析
项目位置：droidrun/agent/utils/trajectory.py

作用：
把运行时对象转换为持久化数据，支持回溯与统计。

### 6.3 全局初始化幂等
项目位置：droidrun/agent/utils/tracing_setup.py

作用：
避免重复注入 tracer/provider 引发的冲突与重复上报。

## 7. 源码注释落点
本轮已补充教程注释的位置：
1. prompt_resolver.py 的 custom_prompts 初始化与 get_prompt 回退边界
2. trajectory.py 的 Trajectory 聚合定位、序列化入口与统计入口
3. tracing_setup.py 的 provider 分支初始化说明

## 8. 证据清单
1. droidrun/agent/utils/prompt_resolver.py: get_prompt, get_valid_prompt_keys
2. droidrun/agent/utils/trajectory.py: get_trajectory, load_macro_sequence, get_trajectory_statistics
3. droidrun/agent/utils/tracing_setup.py: setup_tracing, _setup_phoenix_tracing, _setup_langfuse_tracing

## 9. [不确定] 项
1. [不确定] Langfuse 与其他 tracing provider 共存时的 processor 叠加顺序在复杂部署中可能仍需验证。
2. [不确定] 大规模轨迹目录下的加载性能与清理策略可进一步工程化。

## 10. 覆盖率与下一轮
### 10.1 本轮已覆盖
1. droidrun/agent/utils/prompt_resolver.py
2. droidrun/agent/utils/trajectory.py
3. droidrun/agent/utils/tracing_setup.py

### 10.2 下一轮建议
1. droidrun/agent/trajectory/writer.py
2. droidrun/agent/trajectory/models.py
3. droidrun/agent/trajectory/worker.py

## 11. 小结
这一轮补齐了执行链路的“可调优 + 可复盘 + 可观测”三件套：PromptResolver 做运行时覆写，Trajectory 做离线复盘，TracingSetup 做在线追踪。