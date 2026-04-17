# 20 iOS 状态与元素搜索教程（IOSProvider、ElementSearch、StealthState）

承接：第 19 轮讲了 driver 抽象和坐标几何，这一轮补齐“元素发现与 iOS 状态翻译”能力，覆盖 iOS 文本树解析、可组合元素搜索与拟人化点击状态。

## 1. 学习目标
1. 理解 iOS 文本 a11y 树如何转换为统一 UIState。
2. 理解 element_search 的可组合过滤器设计。
3. 理解 StealthUIState 如何在不破坏可达性的前提下增加点击随机性。

## 2. 分析范围
1. droidrun/tools/ui/ios_provider.py
2. droidrun/tools/helpers/element_search.py
3. droidrun/tools/ui/stealth_state.py
4. droidrun/tools/ui/__init__.py
5. droidrun/tools/helpers/__init__.py

## 3. iOS 状态翻译：ios_provider.py
它做什么：
1. 从 driver 获取 iOS 原始 `a11y_tree` 文本。
2. 解析坐标、类型、文本与标识符，构造成结构化元素列表。
3. 归一化 phone_state（例如 Home Screen 识别）。
4. 产出与 Android 一致的 `UIState`。

关键点：
1. `_parse_a11y_tree` 会过滤无面积节点与噪音容器节点。
2. `_prioritize_actionable_elements` 会优先可操作控件并重排 index。
3. `_format_elements` 输出模型可读的统一编号文本。

## 4. 元素搜索 DSL：element_search.py
它做什么：
1. 提供 `Filters` 静态方法族，生成 `ElementFilter` 可调用对象。
2. 支持文本/ID 匹配、上下左右空间关系、可点击/启用等特征筛选。
3. 支持组合流程：锚点过滤 -> 相对位置筛选 -> trait 过滤。

关键点：
1. `flatten_tree` 是基础能力，统一树遍历入口。
2. `text_matches` 同时匹配 `text/contentDescription/hint` 并做换行归一。
3. 相对位置过滤基于锚点中心与距离排序，返回最近候选优先。

## 5. Stealth 状态：stealth_state.py
它做什么：
1. 继承 `UIState` 并重写点击坐标选择策略。
2. `get_element_coords` 在元素安全区内随机取点。
3. `get_clear_point` 在父类避遮挡结果上增加抖动。

教程式理解：
StealthUIState 不是改变“点哪个元素”，而是改变“点元素内哪个点”，用于降低机械化点击轨迹。

## 6. Python 知识点联动
### 6.1 函数式过滤器组合
项目位置：droidrun/tools/helpers/element_search.py

作用：
把复杂查询拆成可复用的小过滤器，提高表达力与可测试性。

### 6.2 文本解析到结构化对象
项目位置：droidrun/tools/ui/ios_provider.py

作用：
将非结构化 iOS 文本树转为可消费数据模型。

### 6.3 继承与行为覆写
项目位置：droidrun/tools/ui/stealth_state.py

作用：
在保持基类接口兼容的同时替换关键行为（坐标选点）。

## 7. 源码注释落点
本轮已补充教程注释的位置：
1. element_search.py 的 flatten_tree / Filters / text_matches
2. ios_provider.py 的 get_state / _parse_a11y_tree / _format_elements
3. stealth_state.py 的 get_element_coords / get_clear_point

## 8. 证据清单
1. droidrun/tools/ui/ios_provider.py: get_state, _parse_a11y_tree
2. droidrun/tools/helpers/element_search.py: text_matches, below/right_of
3. droidrun/tools/ui/stealth_state.py: get_element_coords, get_clear_point

## 9. [不确定] 项
1. [不确定] iOS 不同系统版本下 a11y 文本字段命名是否完全一致，可能还需扩展正则解析分支。
2. [不确定] Stealth 随机范围在特小控件上的误触风险边界需通过更多真实任务回放校验。

## 10. 覆盖率与下一轮
### 10.1 本轮已覆盖
1. droidrun/tools/ui/ios_provider.py
2. droidrun/tools/helpers/element_search.py
3. droidrun/tools/ui/stealth_state.py
4. droidrun/tools/ui/__init__.py
5. droidrun/tools/helpers/__init__.py

### 10.2 下一轮建议
1. droidrun/cli/main.py（深挖主命令编排）
2. droidrun/cli/run.py（任务执行入口）
3. droidrun/cli/setup.py（初始化流程）

## 11. 小结
这一轮把“元素发现与 iOS 兼容层”讲清楚了：ios_provider 负责状态翻译，element_search 提供组合式定位能力，stealth_state 提供更拟人化的落点策略。