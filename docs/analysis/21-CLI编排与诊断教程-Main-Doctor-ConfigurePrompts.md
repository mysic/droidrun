# 21 CLI 编排与诊断教程（Main、Doctor、ConfigurePrompts）

承接：第 20 轮完成 iOS 状态与元素搜索，这一轮回到用户入口层，补齐 CLI 主命令编排、系统自检和交互提示组件。

## 1. 学习目标
1. 理解 CLI 主入口如何把参数转成执行配置。
2. 理解 doctor 如何分阶段检查并自动修复常见问题。
3. 理解 configure_prompts 的交互降级策略。

## 2. 分析范围
1. droidrun/cli/main.py
2. droidrun/cli/doctor.py
3. droidrun/cli/configure_prompts.py
4. droidrun/cli/logs.py

## 3. 主入口编排：cli/main.py
它做什么：
1. 定义 Click 命令组与子命令（run/setup/ping/doctor/configure/...）。
2. `run_command` 负责配置加载、CLI 参数覆盖、DroidAgent 初始化与执行。
3. 命令收尾阶段处理资源清理（例如键盘 IME 恢复）。

关键流程：
1. 读取配置并应用命令行 override。
2. 按平台选择设备连接逻辑（Android/iOS）。
3. 创建 `DroidAgent`，订阅事件流并交给 `EventHandler` 展示。
4. 将执行结果转成进程退出码。

## 4. 诊断与自愈：cli/doctor.py
它做什么：
1. 逐项检查 SDK/Config/ADB/Device/Portal/Accessibility/TCP/State/Screenshot。
2. 对失败项尝试自动修复（安装 Portal、开启无障碍、重跑检查）。
3. 输出结构化总结（pass/warn/fail）。

关键点：
1. `check_tcp` 按步骤拆解 TCP 故障定位。
2. `run_doctor` 是总编排器，串联检查、修复、复检。

## 5. 交互输入降级：cli/configure_prompts.py
它做什么：
1. `select_prompt`：优先 InquirerPy，缺失则回退 click 选择。
2. `text_prompt`：同样双实现策略，支持 secret 输入。

教程式理解：
这是 CLI 交互体验层的“渐进增强”模式：有增强库更好，没有也能用。

## 6. 日志适配层：cli/logs.py
它做什么：
1. 对外重导出 CLI/TUI 日志 handler。
2. 兼容历史导入路径，减少外部调用方变更成本。

## 7. Python 知识点联动
### 7.1 命令行框架组合
项目位置：droidrun/cli/main.py

作用：
用 Click 描述命令契约，把业务执行与参数解析解耦。

### 7.2 分层诊断流水线
项目位置：droidrun/cli/doctor.py

作用：
将复杂环境问题拆解为独立检查项，便于定位与自动修复。

### 7.3 依赖可选化
项目位置：droidrun/cli/configure_prompts.py

作用：
通过运行时导入实现“可选增强依赖”的平滑降级。

## 8. 源码注释落点
本轮已补充教程注释的位置：
1. doctor.py 的 check_tcp 分步检查说明
2. doctor.py 的 run_doctor 总编排说明
3. configure_prompts.py 的 InquirerPy/click 双通道交互策略

## 9. 证据清单
1. droidrun/cli/main.py: run_command, run, setup, doctor
2. droidrun/cli/doctor.py: check_tcp, run_doctor
3. droidrun/cli/configure_prompts.py: select_prompt, text_prompt
4. droidrun/cli/logs.py: re-export 兼容层

## 10. [不确定] 项
1. [不确定] 不同终端环境下 InquirerPy 与 click 混用时的编码/回显细节仍可能存在边缘差异。
2. [不确定] 某些设备上自动开启 accessibility 的稳定性受系统权限策略影响，可能仍需人工介入。

## 11. 覆盖率与下一轮
### 11.1 本轮已覆盖
1. droidrun/cli/main.py
2. droidrun/cli/doctor.py
3. droidrun/cli/configure_prompts.py
4. droidrun/cli/logs.py

### 11.2 下一轮建议
1. droidrun/tools/macro/*（宏录制与回放链路）
2. droidrun/macro/*（宏编排与 CLI 桥接）
3. droidrun/app_cards/providers/*（知识卡来源聚合）

## 12. 小结
这一轮补齐了 CLI 入口面向用户的关键层：main 负责执行编排，doctor 负责健康诊断与自愈，configure_prompts 负责交互体验的可选增强与保底回退。