# 22 Macro 回放与 CLI 桥接教程（MacroCLI、Replay）

承接：第 21 轮讲了 CLI 主编排与诊断，这一轮聚焦 macro 子系统，补齐“轨迹回放”链路和命令行桥接方式。

## 1. 学习目标
1. 理解 macro CLI 如何加载并回放轨迹动作。
2. 理解 MacroPlayer 如何把动作类型映射到 driver 调用。
3. 理解 module 入口与导出接口如何对外提供能力。

## 2. 分析范围
1. droidrun/macro/cli.py
2. droidrun/macro/replay.py
3. droidrun/macro/__main__.py
4. droidrun/macro/__init__.py

## 3. Macro CLI：macro/cli.py
它做什么：
1. 提供 `macro replay` 与 `macro list` 命令。
2. 负责路径解析、设备选择、dry-run 展示、参数转换（1-based -> 0-based step）。
3. 调用 `MacroPlayer` 执行实际回放。

关键流程：
1. `replay` 收集参数并构造异步执行上下文。
2. `_replay_async` 统一处理文件/目录加载、信息展示、执行与异常处理。
3. `_show_dry_run` 使用表格输出将执行动作预览化。

## 4. 回放执行器：macro/replay.py
它做什么：
1. `MacroPlayer` 初始化 AndroidDriver 并执行动作分发。
2. `replay_action` 按 action_type 调用对应 driver API。
3. `replay_macro` 控制整体步进、延迟、成功率统计和总结。
4. 提供 `replay_macro_file` / `replay_macro_folder` 便捷入口。

关键点：
1. 支持 `start_from_step` 与 `max_steps`，便于失败重放与局部调试。
2. 对未知 action_type 做告警而非崩溃，回放流程更稳健。
3. swipe 后额外等待，降低 UI 还未稳定导致的连锁失败。

## 5. 入口与导出
### 5.1 __main__.py
1. 提供 `python -m droidrun.macro` 模块运行入口。
2. 转发到 `macro_cli`。

### 5.2 __init__.py
1. 对外导出 `MacroPlayer`、`replay_macro_file`、`replay_macro_folder`。
2. 降低其他模块使用 macro 能力时的导入成本。

## 6. Python 知识点联动
### 6.1 命令与执行分层
项目位置：droidrun/macro/cli.py + droidrun/macro/replay.py

作用：
CLI 负责参数与展示，Replay 负责执行逻辑，职责清晰。

### 6.2 动作分发表
项目位置：MacroPlayer.replay_action

作用：
把录制动作标准化映射到 driver API。

### 6.3 便捷包装函数
项目位置：replay_macro_file / replay_macro_folder

作用：
减少上层调用样板代码，提升可复用性。

## 7. 源码注释落点
本轮已补充教程注释的位置：
1. macro/cli.py 的 _replay_async 主流程入口
2. macro/replay.py 的 replay_macro_file / replay_macro_folder 便捷入口
3. __main__.py 与 __init__.py 的入口/导出说明沿用现有注释

## 8. 证据清单
1. droidrun/macro/cli.py: replay, _replay_async, _show_dry_run
2. droidrun/macro/replay.py: replay_action, replay_macro
3. droidrun/macro/replay.py: replay_macro_file, replay_macro_folder
4. droidrun/macro/__main__.py: module entry

## 9. [不确定] 项
1. [不确定] 某些录制轨迹在不同分辨率设备重放时坐标偏差风险仍存在，建议结合归一化策略进一步优化。
2. [不确定] 长序列回放时固定 delay 是否最佳仍依赖场景，后续可考虑动态等待条件。

## 10. 覆盖率与下一轮
### 10.1 本轮已覆盖
1. droidrun/macro/cli.py
2. droidrun/macro/replay.py
3. droidrun/macro/__main__.py
4. droidrun/macro/__init__.py

### 10.2 下一轮建议
1. droidrun/app_cards/providers/local_provider.py
2. droidrun/app_cards/providers/server_provider.py
3. droidrun/app_cards/providers/composite_provider.py

## 11. 小结
这一轮把 macro 子系统走通了：CLI 层负责输入与预览，Replay 层负责动作映射与执行统计，入口/导出层负责外部可用性。