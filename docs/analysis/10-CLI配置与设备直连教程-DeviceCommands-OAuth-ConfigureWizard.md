# 10 CLI 配置与设备直连教程（DeviceCommands、OAuth、ConfigureWizard）

承接：前几轮更多关注 Agent 执行内核，这一轮专门讲“用户在命令行里看到和操作到的入口层”，尤其是设备直连命令、OAuth 登录动作和配置向导流程。

## 1. 学习目标
1. 理解 `droidrun device ...` 是如何绕过 Agent 直接操作设备的。
2. 理解 OAuth 登录动作与凭据持久化机制。
3. 理解 configure wizard 如何引导用户完成 provider/model/高级设置。
4. 理解 CLI 子模块之间如何协作。

## 2. 分析范围
1. `droidrun/cli/device_commands.py`
2. `droidrun/cli/oauth_actions.py`
3. `droidrun/cli/configure_wizard.py`
4. `droidrun/config_manager/credential_paths.py`
5. `droidrun/cli/__init__.py`

## 3. 设备直连命令：device_commands.py
它做什么：
1. 提供 `screenshot`、`ui`、`tap`、`swipe`、`type`、`press`、`apps`、`start` 等子命令。
2. 这些命令不经过 LLM Agent，直接调用 driver。
3. 支持 Android / iOS，支持 TCP、auto_setup、device serial 选择。

关键流程：
1. `_create_driver()` 根据配置和参数创建合适的 driver。
2. 各子命令执行业务动作。
3. `_teardown_android()` 做收尾（例如输入法状态清理）。

教程式理解：
这套命令就是“裸设备 API 层 CLI”，适合调试和快速验证设备能力。

## 4. OAuth 动作：oauth_actions.py
它做什么：
1. 封装 OpenAI / Gemini / Anthropic 的 OAuth 登录动作。
2. 登录成功后把凭据写到统一的 credential 文件。
3. 支持 setup token 流程和已有凭据合并。

关键点：
1. `run_openai_oauth_login` / `run_gemini_oauth_login` / `run_anthropic_setup_token_oauth`
2. `save_anthropic_setup_token` 负责写文件和权限控制。

## 5. 配置向导：configure_wizard.py
它做什么：
1. 交互式选择 provider family、auth mode、model。
2. 处理 API key 来源（env/file/paste）和 OAuth 凭据复用。
3. 可选进入高级设置（vision/reasoning/max_steps/temperature/max_tokens）。
4. 最终保存配置并输出摘要。

这部分是 CLI 用户体验的核心，因为它把复杂配置过程变成了可交互流程。

## 6. 凭据路径：credential_paths.py
它做什么：
1. 定义统一凭据文件路径。
2. 保留历史 provider 路径别名，但实际都指向同一份 auth profiles 文件。

## 7. CLI 模块入口：cli/__init__.py
它做什么：
1. 把主 CLI 入口导出为 `cli`。
2. 方便外部通过包级导入直接使用 CLI 入口。

## 8. Python 知识点联动
### 8.1 Click 装饰器模式
项目位置：`device_commands.py`、`macro/cli.py`

作用：
用装饰器声明命令、参数和选项，形成可组合 CLI。

### 8.2 闭包与回调
项目位置：`configure_wizard.py`

作用：
通过 callback/state 对象把多步交互流程串起来。

### 8.3 dataclass 状态容器
项目位置：`ConfigureWizardState`、`ConfigureWizardCallbacks`

作用：
把多轮交互状态和外部动作依赖整理成结构化对象。

### 8.4 `Path` 与文件权限
项目位置：`oauth_actions.py`、`credential_paths.py`

作用：
保证凭据文件路径和权限处理更稳健。

## 9. 源码注释落点
本轮已补充教程注释的位置：
1. `device_commands.py` 的 driver 创建、命令组和关键命令
2. `oauth_actions.py` 的登录与凭据保存入口
3. `configure_wizard.py` 的状态模型和主流程入口
4. `credential_paths.py` 的统一凭据路径声明
5. `cli/__init__.py` 的包级入口导出

## 10. 证据清单
1. `droidrun/cli/device_commands.py`：`_create_driver`、`device_cli`、`replay`类命令函数
2. `droidrun/cli/oauth_actions.py`：`run_openai_oauth_login`、`save_anthropic_setup_token`
3. `droidrun/cli/configure_wizard.py`：`run_configure_wizard`、`_configure_provider_model`
4. `droidrun/config_manager/credential_paths.py`：`AUTH_PROFILES_PATH`
5. `droidrun/cli/__init__.py`：`cli`

## 11. [不确定] 项
1. [不确定] 各 provider OAuth 回调边界（超时、重定向异常）在用户网络环境下的差异，还需实测。
2. [不确定] 配置向导在极端参数组合下的回退路径是否全覆盖，还可补充集成测试。

## 12. 覆盖率与下一轮
### 12.1 本轮已覆盖
1. `droidrun/cli/device_commands.py`
2. `droidrun/cli/oauth_actions.py`
3. `droidrun/cli/configure_wizard.py`
4. `droidrun/config_manager/credential_paths.py`
5. `droidrun/cli/__init__.py`

### 12.2 下一轮建议
1. `droidrun/agent/providers/*`
2. `droidrun/agent/usage.py`
3. `droidrun/log_handlers.py`

## 13. 小结
这一轮把用户最直接接触的 CLI 入口讲透了：你现在不仅知道 Agent 如何运行，也知道当用户不走 Agent 时如何直接操作设备、如何完成 OAuth 登录，以及如何一步步配置模型与执行参数。