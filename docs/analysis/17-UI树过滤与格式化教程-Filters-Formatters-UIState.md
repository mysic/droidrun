# 17 UI 树过滤与格式化教程（Filters、Formatters、UIState）

承接：第 16 轮讲了驱动层与状态采集，这一轮继续讲“采集到原始树之后，如何变成模型可读、可操作的状态文本与索引”。

## 1. 学习目标
1. 理解过滤器如何控制 UI 树噪音与可见性。
2. 理解格式化器如何给元素编号并生成提示文本。
3. 理解 `UIState` 如何支持索引定位、坐标转换和遮挡规避。

## 2. 分析范围
1. `droidrun/tools/filters/base.py`
2. `droidrun/tools/filters/concise_filter.py`
3. `droidrun/tools/filters/detailed_filter.py`
4. `droidrun/tools/formatters/base.py`
5. `droidrun/tools/formatters/indexed_formatter.py`
6. `droidrun/tools/ui/state.py`

## 3. 过滤层：TreeFilter / Concise / Detailed
### 3.1 抽象接口
1. `TreeFilter` 规定统一 `filter(...)` 与 `get_name()`。
2. 让平台或模式切换只替换策略，不改上游流程。

### 3.2 ConciseFilter
1. 重点是快速去噪：屏幕相交 + 最小尺寸。
2. 递归保留层级结构，不做复杂可见面积计算。

适用场景：
追求速度和稳定，允许丢失部分细碎节点。

### 3.3 DetailedFilter
1. 提供可见比例阈值（默认 10%）。
2. 可选裁剪 bounds 到屏幕范围。
3. 可选过滤键盘节点。

适用场景：
需要保留更多细节、减少误删边缘元素。

## 4. 格式化层：TreeFormatter / IndexedFormatter
### 4.1 TreeFormatter 契约
`format()` 必须返回四元组：
1. `formatted_text`
2. `focused_text`
3. `a11y_tree`
4. `phone_state`

### 4.2 IndexedFormatter
它做什么：
1. 把树结构线性化并分配递增索引。
2. 把节点转为稳定字段（index/text/class/bounds）。
3. 拼接 phone_state + UI 元素文本，构成最终提示词片段。

关键点：
1. 支持归一化坐标输出。
2. 文本回退顺序：text -> contentDescription -> resourceId -> className。

## 5. 状态对象层：UIState
它做什么：
1. 存储当前快照的元素树与屏幕信息。
2. 提供 `get_element` / `get_element_coords` 等索引查询能力。
3. 提供 `convert_point` 处理归一化坐标。
4. 提供 `get_clear_point` 做遮挡规避点击点计算。

教程式理解：
`UIState` 是动作层的“查询 API”。动作函数不处理树遍历细节，只通过索引和辅助方法取坐标与信息。

## 6. Python 知识点联动
### 6.1 策略模式
项目位置：`tools/filters/*`、`tools/formatters/*`

作用：
把“怎么过滤/怎么格式化”从主流程中解耦。

### 6.2 递归树处理
项目位置：`concise_filter.py`、`detailed_filter.py`、`indexed_formatter.py`、`state.py`

作用：
稳定处理任意深度 UI 层级结构。

### 6.3 统一数据契约
项目位置：`base.py` 接口与 `UIState`

作用：
减少上下层协议漂移，便于替换实现。

## 7. 源码注释落点
本轮已补充教程注释的位置：
1. `state.py` 的 `get_clear_point`
2. `concise_filter.py` 的 `_filter_node`
3. `indexed_formatter.py` 的 `_format_node`
4. 其余核心入口注释延续前轮已存在内容

## 8. 证据清单
1. `droidrun/tools/filters/concise_filter.py`：`filter`、`_filter_node`
2. `droidrun/tools/filters/detailed_filter.py`：`filter`、`_filter_out_of_bounds`
3. `droidrun/tools/formatters/indexed_formatter.py`：`format`、`_flatten_with_index`
4. `droidrun/tools/ui/state.py`：`get_element_coords`、`get_clear_point`、`convert_point`

## 9. [不确定] 项
1. [不确定] 详细过滤模式下不同应用复杂动画页面的可见阈值是否需要动态调整。
2. [不确定] `get_clear_point` 在高密度遮挡场景下的命中率仍需更多回放数据验证。

## 10. 覆盖率与下一轮
### 10.1 本轮已覆盖
1. `droidrun/tools/filters/base.py`
2. `droidrun/tools/filters/concise_filter.py`
3. `droidrun/tools/filters/detailed_filter.py`
4. `droidrun/tools/formatters/base.py`
5. `droidrun/tools/formatters/indexed_formatter.py`
6. `droidrun/tools/ui/state.py`

### 10.2 下一轮建议
1. `droidrun/tools/android/portal_client.py`
2. `droidrun/tools/android/socket_client.py`
3. `droidrun/tools/android/content_client.py`

## 11. 小结
这一轮完成了“UI 树到模型提示词”的核心转换链路讲解：过滤器决定保留什么，格式化器决定如何表达，UIState 决定动作层如何查询与落点。