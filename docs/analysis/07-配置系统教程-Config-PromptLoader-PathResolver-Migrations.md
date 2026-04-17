# 07 配置系统教程（Config、PromptLoader、PathResolver、Migrations）

承接：前几轮已经讲清了运行时怎么执行、怎么扩展、怎么观察。这一轮讲配置系统，也就是“这些行为到底从哪里配置”和“旧配置如何平滑升级”。

## 1. 学习目标
1. 理解 `DroidConfig` 为什么是项目配置总入口。
2. 理解 Prompt 路径和模板变量是如何被解析与渲染的。
3. 理解 `PathResolver` 为什么要同时支持工作目录和包内资源。
4. 理解 migration 系统如何让旧配置升级到新版本。

## 2. 分析范围
1. `droidrun/config_manager/config_manager.py`
2. `droidrun/config_manager/prompt_loader.py`
3. `droidrun/config_manager/path_resolver.py`
4. `droidrun/config_manager/migrations/__init__.py`
5. `droidrun/config_manager/migrations/v002_add_code_exec.py`
6. `droidrun/config_manager/migrations/v003_add_auto_setup.py`
7. `droidrun/config_manager/migrations/v004_remove_deprecated_agents.py`
8. `droidrun/config_manager/migrations/v005_remove_external_agents.py`

## 3. 一句话先理解配置系统
1. `config_manager.py` 负责“配置长什么样”。
2. `PathResolver` 负责“路径到底指向哪里”。
3. `PromptLoader` 负责“模板怎么渲染成最终 Prompt”。
4. `migrations/*` 负责“旧配置怎么升级成新配置”。

## 4. 配置模型层
### 4.1 LLMProfile
文件：`config_manager.py`

它做什么：
1. 描述一个 LLM 的 provider、model、temperature、API key 来源、URL 等参数。
2. 通过 `to_load_llm_kwargs()` 转成真正给 `load_llm` 用的参数。

最重要的点：
它不仅保存配置，还会根据 env/file/auto 策略主动解析 API key 来源。

### 4.2 AgentConfig / DeviceConfig / LoggingConfig / ToolsConfig 等
文件：`config_manager.py`

这些类做什么：
1. 把不同维度的配置拆开，避免一个超级大 dict 难以维护。
2. 提供合理默认值，降低首次使用门槛。

### 4.3 DroidConfig
文件：`config_manager.py`

它做什么：
1. 组合所有子配置，形成完整配置树。
2. 提供 `to_dict()`、`from_dict()`、`from_yaml()`。
3. 自动补齐默认 LLM profiles。

教程式理解：
它相当于整个项目的“配置根对象”。其他模块只要拿到它，就能知道运行时该怎么做。

## 5. Prompt 模板系统
### 5.1 PromptLoader
文件：`prompt_loader.py`

它做什么：
1. 从文件读取 Jinja2 模板。
2. 或直接对运行时字符串模板做渲染。
3. 用统一的环境设置处理 trim_blocks、lstrip_blocks 等细节。

为什么很关键：
Manager、Executor、FastAgent 的系统提示词和用户提示词都依赖它。

### 5.2 路径解析与 Prompt 关联
AgentConfig 里的这些方法：
1. `get_fast_agent_system_prompt_path()`
2. `get_fast_agent_user_prompt_path()`
3. `get_manager_system_prompt_path()`
4. `get_executor_system_prompt_path()`

它们先让 `PathResolver` 找到文件，再交给 `PromptLoader` 读取并渲染。

## 6. 路径系统
### 6.1 PathResolver
文件：`path_resolver.py`

它做什么：
1. 统一处理绝对路径和相对路径。
2. 对读取场景先查工作目录，再查包内资源。
3. 对创建场景优先工作目录。

教程式理解：
它就是路径世界里的“仲裁器”。这样用户既可以覆盖自己的本地资源，也可以回退到项目自带默认资源。

## 7. 配置迁移系统
### 7.1 migrations/__init__.py
它做什么：
1. 自动发现所有迁移模块。
2. 按版本顺序执行待升级迁移。
3. 在每次迁移后更新 `_version`。

### 7.2 迁移示例
#### v002
把旧的 `codeact` 配置迁移到 `fast_agent`。

#### v003
给 device 增加 `auto_setup`。

#### v004
移除废弃 agent 配置，并更新 prompt 路径。

#### v005
移除旧版 external agent 示例配置。

教程式理解：
迁移系统就像数据库 migration，只不过这里迁的是 YAML 配置结构。

## 8. 典型配置加载链路
1. `ConfigLoader.load()` 找到用户配置文件
2. `migrate(config)` 把旧版本升级到当前版本
3. `DroidConfig.from_dict()` 把原始 dict 变成强类型配置对象
4. Agent 在运行时读取这些配置
5. Prompt 路径再通过 `PathResolver + PromptLoader` 解析成最终提示词

## 9. Python 知识点联动
### 9.1 `@dataclass`
项目位置：几乎所有 config 类。

作用：
让配置对象更轻量、结构清晰、默认值明确。

### 9.2 `field(default_factory=...)`
项目位置：dict、list 和子配置默认值。

作用：
避免多个实例共享同一个可变默认对象。

### 9.3 `Literal`
项目位置：`api_key_source`。

作用：
把可选字符串值限制在固定集合内，增强可读性与类型检查。

### 9.4 `classmethod`
项目位置：`from_dict()`、`from_yaml()`。

作用：
把“如何构建配置对象”的逻辑放在类上，而不是外部函数里。

## 10. 源码注释落点
本轮已补充教程注释的位置：
1. `LLMProfile`、`AgentConfig`、`DroidConfig`
2. `PromptLoader` 与渲染入口
3. `PathResolver` 与 `resolve()`
4. 迁移入口与各版本迁移文件

## 11. 证据清单
1. `droidrun/config_manager/config_manager.py`：`LLMProfile.to_load_llm_kwargs`、`DroidConfig.from_dict`
2. `droidrun/config_manager/prompt_loader.py`：`PromptLoader.load_prompt`、`render_template`
3. `droidrun/config_manager/path_resolver.py`：`PathResolver.resolve`
4. `droidrun/config_manager/migrations/__init__.py`：`get_migrations`、`migrate`
5. `droidrun/config_manager/migrations/v004_remove_deprecated_agents.py`：`migrate`

## 12. [不确定] 项
1. [不确定] 某些 env key provider 变体映射的完整行为还需要继续下钻到 `agent/providers/registry.py`。
2. [不确定] Jinja2 模板里具体使用了哪些变量，还需要把 prompt 文件本身单独分析一轮。

## 13. 覆盖率与下一轮
### 13.1 本轮已覆盖
1. `droidrun/config_manager/config_manager.py`
2. `droidrun/config_manager/prompt_loader.py`
3. `droidrun/config_manager/path_resolver.py`
4. `droidrun/config_manager/migrations/__init__.py`
5. `droidrun/config_manager/migrations/v002_add_code_exec.py`
6. `droidrun/config_manager/migrations/v003_add_auto_setup.py`
7. `droidrun/config_manager/migrations/v004_remove_deprecated_agents.py`
8. `droidrun/config_manager/migrations/v005_remove_external_agents.py`

### 13.2 下一轮建议
1. `droidrun/agent/utils/chat_utils.py`
2. `droidrun/agent/utils/inference.py`
3. `droidrun/agent/utils/llm_loader.py`
4. `droidrun/agent/utils/llm_picker.py`

## 14. 小结
这一轮把配置层补齐了。到这里，你已经能从“配置长什么样”“Prompt 从哪来”“路径如何定位”“旧配置如何升级”四个角度理解 Droidrun 的运行准备过程。后面如果继续分析 LLM 工具链，就能把“配置如何真正转成模型调用”这条链路补完整。