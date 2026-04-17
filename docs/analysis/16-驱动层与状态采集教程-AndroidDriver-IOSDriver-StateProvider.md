# 16 驱动层与状态采集教程（AndroidDriver、IOSDriver、StateProvider）

承接：第 15 轮讲了 FastAgent 闭环和外部扩展，这一轮下沉到最底层“设备 I/O + 状态采集翻译”链路，覆盖 Android/iOS 驱动与 Android 状态提供器。

## 1. 学习目标
1. 理解设备驱动层如何屏蔽 ADB/HTTP 细节。
2. 理解 Android 与 iOS 驱动的能力抽象和差异。
3. 理解状态采集失败后的重试与自愈机制。

## 2. 分析范围
1. `droidrun/tools/driver/android.py`
2. `droidrun/tools/driver/ios.py`
3. `droidrun/tools/ui/provider.py`

## 3. AndroidDriver：ADB + Portal 通道
它做什么：
1. 建立 ADB 连接并初始化 `PortalClient`。
2. 封装 tap/swipe/input/press/start_app/get_ui_tree/screenshot 等基础设备操作。
3. 在连接阶段准备输入法能力（Portal keyboard）。

关键点：
1. `connect` 会验证设备在线状态并接入 Portal。
2. 上层动作只调用统一接口，不感知 ADB shell/Portal 协议细节。
3. `supported`/`supported_buttons` 给上层能力裁剪提供依据。

## 4. IOSDriver：HTTP Portal 通道
它做什么：
1. 通过 REST API 与 iOS Portal 通信。
2. 提供与 AndroidDriver 一致的抽象接口。
3. 支持端口扫描发现 Portal 服务。

关键流程：
1. `validate_ios_portal_url` 先做 URL 合法性与规范化。
2. `discover_ios_portal` 先探默认端口，再并发扫描邻近端口。
3. `connect` 用 `/device/date` 作为健康探针。
4. `get_ui_tree` 返回统一结构，兼容上层状态处理逻辑。

平台差异：
1. iOS 当前只支持 `home` 按键抽象。
2. iOS 应用列表主要依赖预设 bundle 标识与映射，不同于 Android 的动态包查询。

## 5. StateProvider：状态抓取与翻译
它做什么：
1. `fetch_state_with_retry` 提供重试、退避、可选恢复钩子。
2. `AndroidStateProvider` 把原始 a11y 树过滤并格式化为 `UIState`。
3. 把屏幕尺寸注入 formatter，保证索引与坐标计算一致。

关键点：
1. 连续失败到阈值后触发 `_recover_portal`。
2. `_recover_portal` 会尝试重启 accessibility 与 TCP socket，并刷新 token。
3. 最终输出统一 `UIState`，供 Agent 决策层消费。

## 6. Python 知识点联动
### 6.1 抽象基类 + 平台实现
项目位置：`tools/driver/android.py`、`tools/driver/ios.py`

作用：
通过同一接口承载跨平台差异，减少上层分支判断。

### 6.2 异步重试与退避策略
项目位置：`tools/ui/provider.py`

作用：
提升设备状态获取在不稳定链路下的成功率。

### 6.3 统一数据契约
项目位置：`tools/driver/ios.py`、`tools/ui/provider.py`

作用：
平台输出对齐到同一结构，复用同一过滤/格式化链。

## 7. 源码注释落点
本轮已补充教程注释的位置：
1. `ios.py` 的 URL 校验、端口发现、连接探针、统一状态输出
2. `provider.py` 的恢复钩子与格式化尺寸注入
3. `android.py` 关键注释已存在并延续使用（连接与能力封装）

## 8. 证据清单
1. `droidrun/tools/driver/android.py`：`connect`、`get_ui_tree`
2. `droidrun/tools/driver/ios.py`：`discover_ios_portal`、`connect`、`get_ui_tree`
3. `droidrun/tools/ui/provider.py`：`fetch_state_with_retry`、`_recover_portal`、`get_state`

## 9. [不确定] 项
1. [不确定] 不同 Android 机型对 accessibility 设置写入命令的兼容性仍可能影响自愈成功率。
2. [不确定] iOS Portal 在高频状态拉取下的延迟波动边界需要更多实机压测。

## 10. 覆盖率与下一轮
### 10.1 本轮已覆盖
1. `droidrun/tools/driver/android.py`
2. `droidrun/tools/driver/ios.py`
3. `droidrun/tools/ui/provider.py`

### 10.2 下一轮建议
1. `droidrun/tools/filters/*`（树过滤策略）
2. `droidrun/tools/formatters/*`（元素编号与文本渲染策略）
3. `droidrun/tools/ui/state.py`（状态对象与坐标转换）

## 11. 小结
这一轮补齐了“最底层执行基座”：驱动层负责可靠设备 I/O，状态提供器负责把原始设备数据翻译成上层可决策的统一 UIState，并在失败时具备自愈能力。