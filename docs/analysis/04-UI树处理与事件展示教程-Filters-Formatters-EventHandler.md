# 04 UI 树处理与事件展示教程（Filters、Formatters、EventHandler）

承接：上一轮已经讲清了 `StateProvider -> UIState -> actions` 这条链路。这一轮继续下钻到 UI 状态生成的中间层，也就是“原始无障碍树如何被裁剪”和“最后如何展示给模型与用户”。

## 1. 学习目标
1. 理解 Filter 在 UI 树处理中承担什么职责。
2. 理解 Formatter 如何把树转换成模型可读文本和带索引的元素列表。
3. 理解 CLI 的 `EventHandler` 如何把工作流事件翻译成日志输出。
4. 把 UI 原始数据、Agent 提示文本、CLI 展示三层串起来。

## 2. 分析范围
1. `droidrun/tools/filters/base.py`
2. `droidrun/tools/filters/concise_filter.py`
3. `droidrun/tools/filters/detailed_filter.py`
4. `droidrun/tools/formatters/base.py`
5. `droidrun/tools/formatters/indexed_formatter.py`
6. `droidrun/cli/event_handler.py`
7. `droidrun/tools/filters/__init__.py`
8. `droidrun/tools/formatters/__init__.py`

## 3. 一句话先理解这三层
1. Filter 解决“哪些节点值得保留”。
2. Formatter 解决“保留下来的节点怎么编号和展示”。
3. EventHandler 解决“运行过程中发生了什么，怎么让用户看到”。

## 4. UI 树处理链路
```text
Portal 返回原始 a11y_tree
-> TreeFilter 过滤掉不重要或无效节点
-> TreeFormatter 把树编号、压平成可读文本
-> StateProvider 返回 UIState
-> Agent 读 formatted_text 做推理
-> CLI EventHandler 把执行过程转成日志展示
```

## 5. 文件级讲解
### 5.1 TreeFilter 基类：定义过滤接口
文件：`droidrun/tools/filters/base.py`

它做什么：
1. 定义所有过滤器都必须实现的 `filter()` 和 `get_name()`。
2. 强制不同过滤策略保持统一接口，方便运行时切换。

教程式理解：
这类似 Java 里的接口或抽象基类，约束“你要当过滤器，至少得会做这两件事”。

### 5.2 ConciseFilter：简洁裁剪策略
文件：`droidrun/tools/filters/concise_filter.py`

它做什么：
1. 过滤掉不在屏幕范围内的节点。
2. 过滤掉尺寸太小的节点。
3. 保留树的层级结构，只裁掉不合格节点。

适合什么场景：
适合需要更干净、噪音更少的提示上下文，减少模型看到的无效节点数量。

### 5.3 DetailedFilter：更精细的可见性策略
文件：`droidrun/tools/filters/detailed_filter.py`

它做什么：
1. 支持按可见比例过滤节点。
2. 可选过滤键盘元素。
3. 可选把 bounds 裁剪到屏幕内。
4. 即使父节点不可见，只要子节点还能保留，也会保住层级。

和 ConciseFilter 的差异：
1. ConciseFilter 更直接，按是否相交、是否足够大判断。
2. DetailedFilter 更细，按可见面积比例判断，策略更复杂。

### 5.4 TreeFormatter 基类：定义格式化接口
文件：`droidrun/tools/formatters/base.py`

它做什么：
1. 规定所有格式化器都要返回四件东西：`formatted_text`、`focused_text`、处理后的树、`phone_state`。
2. 保证上层 `StateProvider` 不用关心具体 formatter 的内部实现差异。

### 5.5 IndexedFormatter：Droidrun 标准格式化器
文件：`droidrun/tools/formatters/indexed_formatter.py`

它做什么：
1. 给每个元素分配 index。
2. 把节点压平成可读列表。
3. 把 `phone_state` 和 UI 元素文本拼成给 Agent 的完整上下文。
4. 支持归一化坐标输出。

为什么它重要：
模型真正看到的不是原始 JSON 树，而是 `IndexedFormatter` 产出的那段结构化文本。也就是说，这个文件直接影响模型如何理解当前界面。

### 5.6 EventHandler：把内部事件翻译成用户可见日志
文件：`droidrun/cli/event_handler.py`

它做什么：
1. 接收工作流事件对象。
2. 按事件类型决定输出什么日志文案。
3. 给日志带上颜色等 `extra` 信息，交给不同 Handler 渲染。

教程式理解：
它像一个“展示适配器”。内部系统说的是 Event 对象，CLI 用户看到的是“Manager preparing context...” 或 “Action result: ...”。

## 6. 典型流程拆解
### 6.1 原始 UI 树如何变成提示文本
1. Driver 拿到 `a11y_tree`
2. `TreeFilter.filter()` 去掉无效节点
3. `IndexedFormatter.format()` 编号、提取文本、拼接 phone state
4. `StateProvider` 把结果塞进 `UIState`
5. Agent 读取 `formatted_text`

### 6.2 一个工具执行结果如何出现在终端里
1. ToolRegistry 执行动作
2. 工作流产出 `ToolExecutionEvent` 或相关结果事件
3. `EventHandler.handle(event)` 根据类型做分支
4. logger 输出带颜色的日志
5. CLI/TUI/SDK 的 handler 再决定最终怎么展示

## 7. Python 知识点联动
### 7.1 抽象基类 `ABC`
项目位置：`filters/base.py`、`formatters/base.py`

作用：
规定子类必须实现哪些方法。

### 7.2 `@staticmethod` 与 `@classmethod`
项目位置：两个 filter 与 formatter 内部大量辅助函数。

作用：
把不依赖实例状态的方法抽出来，增强组织性和可读性。

### 7.3 递归
项目位置：`ConciseFilter._filter_node()`、`DetailedFilter._filter_keyboard_elements()`、`IndexedFormatter._flatten_with_index()`

作用：
因为 UI 树天然是树状结构，递归是最自然的遍历方式。

### 7.4 `isinstance`
项目位置：`event_handler.py`

作用：
按事件对象类型决定处理分支，是事件驱动代码里的常见写法。

## 8. 源码注释落点
本轮已补充前置教程注释的位置：
1. `TreeFilter`、`ConciseFilter`、`DetailedFilter`
2. `TreeFormatter`、`IndexedFormatter`
3. `EventHandler` 及其核心 `handle()`
4. `get_filter()` 与导出模块位置

## 9. 证据清单
1. `droidrun/tools/filters/base.py`：`TreeFilter`
2. `droidrun/tools/filters/concise_filter.py`：`ConciseFilter.filter`
3. `droidrun/tools/filters/detailed_filter.py`：`DetailedFilter._filter_out_of_bounds`
4. `droidrun/tools/formatters/base.py`：`TreeFormatter.format`
5. `droidrun/tools/formatters/indexed_formatter.py`：`IndexedFormatter.format`、`_flatten_with_index`
6. `droidrun/cli/event_handler.py`：`EventHandler.handle`

## 10. [不确定] 项
1. [不确定] 当前项目中 concise 与 detailed 两种过滤模式的默认选型逻辑还未追溯到最终配置文件。
2. [不确定] 某些事件在 TUI 或 SDK 场景下是否有额外展示差异，还未深入到对应 handler 实现。

## 11. 覆盖率与下一轮
### 11.1 本轮已覆盖
1. `droidrun/tools/filters/base.py`
2. `droidrun/tools/filters/concise_filter.py`
3. `droidrun/tools/filters/detailed_filter.py`
4. `droidrun/tools/filters/__init__.py`
5. `droidrun/tools/formatters/base.py`
6. `droidrun/tools/formatters/indexed_formatter.py`
7. `droidrun/tools/formatters/__init__.py`
8. `droidrun/cli/event_handler.py`

### 11.2 下一轮建议
1. `droidrun/agent/droid/events.py`
2. `droidrun/agent/manager/events.py`
3. `droidrun/agent/executor/events.py`
4. `droidrun/agent/fast_agent/events.py`
5. `droidrun/mcp/*`

## 12. 小结
这一轮把“原始 UI 树 -> 模型可读文本 -> CLI 可见日志”的桥梁补齐了。到这里，你已经不仅知道 Agent 会执行什么动作，还知道它为什么能看懂屏幕，以及用户为什么能在终端里看到那些状态提示。