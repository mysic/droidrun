## Plan: droidrun全项目源码教学分析

目标是面向“会其他语言、Python初学者”，对 droidrun 做全量源码分析，产出工程化结果：架构图谱、文件级逻辑说明、Python语法与关键字/内置函数教程（结合真实源码位置），并通过覆盖率与证据链保证可复查。

**Steps**
1. Phase A - 预处理与范围冻结
1.1 固定范围为 /home/mysic/workspace/freebie-hunting/droidrun，明确排除 /home/mysic/workspace/freebie-hunting/droidrun-portal。  
1.2 让AI先读取项目元信息（README、pyproject.toml、入口模块）并输出“模块清单 + 初步依赖关系 + 风险点”。
2. Phase B - 架构总览（先全局后局部）
2.1 输出项目分层：CLI层、Agent编排层、Tools执行层、配置层、遥测层。  
2.2 输出主执行链路：程序入口 -> 命令分发 -> Agent执行 -> Tool调用 -> 设备交互。  
2.3 输出数据/状态流：用户输入、任务状态、工具结果、日志/遥测流。
3. Phase C - 文件级全量讲解（按目录批次）
3.1 以目录为批次推进：droidrun/cli、droidrun/agent、droidrun/tools、droidrun/config_manager、droidrun/telemetry 等。  
3.2 每个文件固定模板：文件作用、关键类/函数、调用关系、执行路径、异常处理、新手易错点。  
3.3 每批结束给“已覆盖文件/未覆盖文件”清单。*可与Step 4并行滚动*
4. Phase D - Python教学联动（绑定真实代码）
4.1 从当前批次文件提取语法点：模块导入、类与继承、装饰器、类型注解、异步编程、上下文管理等。  
4.2 解释关键字与内置函数：作用、在本项目中的真实用途、等价类比（对照你已会的语言思维）、最小示例。  
4.3 每个知识点附“常见误解 + 如何排错”。
5. Phase E - 质量门禁与迭代
5.1 要求每条结论附证据：文件路径 + 符号名（类/函数/变量）。  
5.2 AI必须标注不确定结论，禁止无依据推断。  
5.3 输出差距报告：盲区、争议点、下一批优先分析文件Top N。
6. Phase F - 最终交付
6.1 交付一份“学习路线图”：先学哪些模块、每模块建议阅读顺序。  
6.2 交付“Python语法地图”：按本项目出现频次和重要度排序。  
6.3 交付“术语表”：Agent、Workflow、Tool Registry、Telemetry等概念的一句话解释。

**Relevant files**
- /home/mysic/workspace/freebie-hunting/droidrun/README.md — 项目目标、运行方式、核心概念入口。
- /home/mysic/workspace/freebie-hunting/droidrun/pyproject.toml — 依赖栈、Python版本与打包配置。
- /home/mysic/workspace/freebie-hunting/droidrun/droidrun/__main__.py — 程序启动入口。
- /home/mysic/workspace/freebie-hunting/droidrun/droidrun/cli/main.py — 命令分发与CLI主流程。
- /home/mysic/workspace/freebie-hunting/droidrun/droidrun/agent/droid/droid_agent.py — Agent核心编排。
- /home/mysic/workspace/freebie-hunting/droidrun/droidrun/agent/tool_registry.py — Tool注册与映射机制。
- /home/mysic/workspace/freebie-hunting/droidrun/droidrun/portal.py — Python与Android portal协作边界。

**Verification**
1. 覆盖率检查：确认 droidrun 下源码文件均在“已分析清单”或“明确排除清单”中。
2. 证据链检查：随机抽样10条结论，验证是否能定位到对应文件与符号。
3. 教学有效性检查：每批至少产出3个“项目内真实语法点 + 最小示例 + 易错提醒”。
4. 一致性检查：架构图、调用链、文件讲解之间不得互相矛盾。

**Decisions**
- 已确认范围：仅 droidrun（Python）。
- 用户基础：会其他语言，因此教程使用“跨语言类比”而非纯零基础叙述。
- 包含内容：源码逻辑分析 + Python语法教学联动。
- 排除内容：droidrun-portal 代码细节实现（仅在边界交互处解释）。

**Further Considerations**
1. 输出粒度建议：每轮处理20-40个文件，避免单轮上下文过载导致漏讲。  
2. 为减少幻觉，优先让AI“先列符号清单再解释”，再进入教学层输出。