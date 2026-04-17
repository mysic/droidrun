# 23 AppCards 提供器教程（Local、Server、Composite）

承接：第 22 轮讲了 macro 回放，这一轮聚焦 app_cards 子系统，解释应用知识卡如何从本地与服务端加载并做回退。

## 1. 学习目标
1. 理解 AppCardProvider 抽象接口的作用。
2. 理解本地 provider、服务端 provider、组合 provider 的分工。
3. 理解缓存与回退策略如何提升稳定性与响应速度。

## 2. 分析范围
1. droidrun/app_cards/app_card_provider.py
2. droidrun/app_cards/providers/local_provider.py
3. droidrun/app_cards/providers/server_provider.py
4. droidrun/app_cards/providers/composite_provider.py

## 3. 抽象层：AppCardProvider
它做什么：
1. 定义统一异步接口 `load_app_card(package_name, instruction)`。
2. 屏蔽数据来源差异（本地文件 / 远程服务 / 组合策略）。

教程式理解：
上层只关心“拿到卡片内容”，不关心来源实现细节。

## 4. 本地实现：LocalAppCardProvider
它做什么：
1. 启动时加载 app_cards.json 映射。
2. 按 package_name 定位 markdown 卡片文件。
3. 用内存缓存减少重复文件读取。

关键点：
1. 初始化时预加载映射，查询阶段快速命中。
2. 读取失败返回空字符串，避免中断上游流程。

## 5. 服务端实现：ServerAppCardProvider
它做什么：
1. POST 请求服务器 `/app-cards` 获取动态卡片。
2. 按 (package_name, instruction) 做缓存。
3. 带 timeout + retry，失败时缓存空结果。

关键点：
1. 200/404/异常分支处理清晰。
2. 重试次数较小，兼顾鲁棒性和响应时延。

## 6. 组合实现：CompositeAppCardProvider
它做什么：
1. 优先调用服务端 provider。
2. 服务端失败或返回空时回退本地 provider。
3. 对外保持单一接口和统一缓存清理入口。

教程式理解：
这是“新鲜度优先 + 可用性兜底”的典型组合策略。

## 7. Python 知识点联动
### 7.1 抽象基类与策略替换
项目位置：droidrun/app_cards/app_card_provider.py

作用：
不同后端实现可互换，上层调用稳定。

### 7.2 异步 I/O 与缓存
项目位置：local_provider.py / server_provider.py

作用：
平衡读取性能、网络波动与请求成本。

### 7.3 组合模式
项目位置：composite_provider.py

作用：
把两个 provider 组合成更鲁棒的统一服务。

## 8. 源码注释落点
本轮已补充教程注释的位置：
1. local_provider.py 的映射预加载说明
2. server_provider.py 的重试策略说明
3. 其余核心入口注释延续既有内容

## 9. 证据清单
1. droidrun/app_cards/app_card_provider.py: load_app_card
2. droidrun/app_cards/providers/local_provider.py: __init__, load_app_card
3. droidrun/app_cards/providers/server_provider.py: load_app_card
4. droidrun/app_cards/providers/composite_provider.py: load_app_card

## 10. [不确定] 项
1. [不确定] 服务端返回策略在 instruction 维度上的去重与缓存淘汰策略是否需要细化。
2. [不确定] 本地 app_cards 映射在热更新场景下是否需要自动重载机制。

## 11. 覆盖率与下一轮
### 11.1 本轮已覆盖
1. droidrun/app_cards/app_card_provider.py
2. droidrun/app_cards/providers/local_provider.py
3. droidrun/app_cards/providers/server_provider.py
4. droidrun/app_cards/providers/composite_provider.py

### 11.2 下一轮建议
1. droidrun/agent/utils/prompt_resolver.py
2. droidrun/agent/utils/trajectory.py
3. droidrun/agent/utils/tracing_setup.py

## 12. 小结
这一轮讲清了 AppCards 的供给链：抽象接口统一调用，本地与远程各司其职，组合策略保障在网络波动下依然可用。