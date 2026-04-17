# 36 Manager提示词模板教程（system、stateless、rev1、trained）

承接：第 35 轮刚把 `config/` 资源层整体补齐，这一轮继续下钻到当前这个文件夹 `droidrun/config/prompts/manager/`，专门解释 Manager 规划器的 4 份模板分别在做什么、彼此差异在哪里，以及它们与 Python 侧 `ManagerAgent` / `StatelessManagerAgent` 的对应关系。

## 1. 学习目标
1. 理解 `manager/` 文件夹里的 4 个模板不是重复文案，而是不同 planning 风格与阶段的资源版本。
2. 理解 `system.jinja2` 与 `stateless.jinja2` 分别服务于有状态/无状态规划器。
3. 理解 `rev1.jinja2` 与 `trained.jinja2` 更像历史/实验模板，为什么仍值得分析。
4. 理解这些模板如何通过 Jinja2 变量直接影响 Manager 的规划行为与输出协议。

## 2. 分析范围
1. `droidrun/config/prompts/manager/system.jinja2`
2. `droidrun/config/prompts/manager/stateless.jinja2`
3. `droidrun/config/prompts/manager/rev1.jinja2`
4. `droidrun/config/prompts/manager/trained.jinja2`

排除项：
1. `PromptLoader` 的渲染实现
2. `parse_manager_response()` 的 Python 正则解析细节
3. `Executor` / `FastAgent` 的模板文件

## 3. 架构/流程总览
文字图：
1. `DroidAgent` 根据配置选择 `ManagerAgent` 或 `StatelessManagerAgent`。
2. Python 侧把变量字典传给 `PromptLoader`。
3. 当前 Manager 模板被渲染成最终 system prompt。
4. LLM 按模板要求输出 `<thought>`、`<plan>`、`<request_accomplished>` 等结构化标签。
5. `parse_manager_response()` 再把这些标签转回结构化 planning 结果。

## 4. 文件级讲解（按职责分组）
### 4.1 默认有状态模板：system.jinja2
1. 文件：`droidrun/config/prompts/manager/system.jinja2`
2. 做什么：定义默认 `ManagerAgent` 的 planning 协议，强调实时评估当前状态、利用 memory、生成 plan，并在完成时输出 `<request_accomplished>`。
3. 关键符号：`instruction`、`device_date`、`app_card`、`error_history`、`custom_tools_descriptions`、`available_secrets`、`output_schema`
4. 调用关系：`ManagerAgent._build_system_prompt()` -> `PromptLoader.load_prompt()` -> 渲染本模板 -> LLM 规划输出
5. 初学者易错点：
   - 它虽然名叫 `system`，但本质上是“有状态 Manager 的系统提示词模板”，不是整个项目唯一 system prompt。
   - 模板里明确要求使用 `<thought> / <plan> / <request_accomplished>`，这直接决定了 `parse_manager_response()` 的解析协议。
   - `external_user_message` 的说明写在模板里，意味着“运行中插队消息”是否被正确吸收，部分依赖 prompt 侧的规则声明。

### 4.2 无状态模板：stateless.jinja2
1. 文件：`droidrun/config/prompts/manager/stateless.jinja2`
2. 做什么：为 `StatelessManagerAgent` 提供更适合“每轮重建上下文”的 planning 模板。
3. 关键符号：`previous_plan`、`previous_state`、`memory`、`last_thought`、`progress_summary`、`action_history`、`current_state`
4. 调用关系：`StatelessManagerAgent._build_prompt()` -> `PromptLoader.load_prompt()` -> 渲染本模板 -> 无状态规划
5. 初学者易错点：
   - 这个模板不依赖完整 `message_history`，而是显式把前一轮计划、前一轮状态、压缩动作历史塞进 prompt。
   - 输出协议与有状态版本略有不同：这里用 `<progress_summary>` 和 `<answer success="...">` 这种更贴近“每轮快照总结”的结构。
   - 它不是简化版 `system.jinja2`，而是与 `StatelessManagerAgent` 的状态组织方式一一对应。

### 4.3 旧版 / 修订版模板：rev1.jinja2
1. 文件：`droidrun/config/prompts/manager/rev1.jinja2`
2. 做什么：展示一个更早期或修订版的 planning prompt 形态，便于理解 Manager 模板是如何演进的。
3. 关键符号：整体结构、标签命名、规则密度、与当前 `system.jinja2` 的差异
4. 调用关系：当前主运行路径未直接显示引用它，但它保留了历史 prompt 设计线索
5. 初学者易错点：
   - 这类文件不一定处于当前默认运行路径，但仍有分析价值，因为它能帮助你看出项目如何不断调 prompt 协议。
   - 不能简单把它当无用旧文件；它可能是实验、回滚或比较基线。

### 4.4 训练化版本：trained.jinja2
1. 文件：`droidrun/config/prompts/manager/trained.jinja2`
2. 做什么：看名字更像“经过针对性调优”的 Manager 模板版本，通常会更强调特定输出纪律或行为风格。
3. 关键符号：更严格的规则、不同的表达风格、可能更接近一组已验证策略
4. 调用关系：同样未在当前主路径里直接看到默认引用，但它属于 prompt 资源库的一部分
5. 初学者易错点：
   - `trained` 不是 Python 训练产物，而更像“已经过实践调优的模板版本”。
   - 这种文件即便没走默认路径，也对理解项目 prompt engineering 很重要。

## 5. 关键差异总结
### 5.1 system.jinja2 vs stateless.jinja2
1. `system.jinja2` 偏“持续对话式规划”，适合 `ManagerAgent` 的多轮 message history。
2. `stateless.jinja2` 偏“快照重建式规划”，适合 `StatelessManagerAgent` 每轮重新拼上下文。
3. 前者强调 `<request_accomplished>`，后者更明显引入 `<progress_summary>` 和 `<answer success="...">` 这一类按轮总结格式。

### 5.2 rev1.jinja2 / trained.jinja2 的价值
1. 它们像 prompt 设计的“历史分支”或“实验分支”。
2. 对源码阅读者来说，这些模板能帮助理解当前默认模板为什么会写成现在这样。
3. 对后续改 prompt 的人来说，它们也是现成的对照样本。

## 6. Python 知识点联动
1. 语法/关键字/内置函数：Jinja2 变量插值、条件块、循环块、模板协议设计
2. 在本项目中的位置：`{{ instruction }}`、`{% if app_card %}`、`{% for error in error_history %}`、按条件插入 `<available_secrets>` / `<output_requirements>`
3. 为什么这样写：
   - 把 prompt 做成模板而不是硬编码字符串，便于在不同 Agent、不同运行模式、不同实验版本之间快速切换。
   - 用条件块控制信息注入，能避免每次把空字段硬塞给模型，减少噪音。
   - 用固定 XML 风格标签输出，可以让 Python 解析器稳定地抽取 planning 结果。
4. 最小示例：
```jinja2
{% if error_history %}
<potentially_stuck>
{% for error in error_history %}
- Attempt: {{ error.action }} | Feedback: {{ error.error }}
{% endfor %}
</potentially_stuck>
{% endif %}
```
5. 常见错误与修正：
   - 错误：把 prompt 模板当普通说明文字阅读。
   - 修正：把它当“行为协议”，重点看输入变量、输出格式和规则约束。
   - 错误：认为 `stateless.jinja2` 只是名字不同。
   - 修正：它和 `StatelessManagerAgent` 的上下文组织方式强绑定。

## 7. 证据清单
1. `droidrun/config/prompts/manager/system.jinja2`
2. `droidrun/config/prompts/manager/stateless.jinja2`
3. `droidrun/config/prompts/manager/rev1.jinja2`
4. `droidrun/config/prompts/manager/trained.jinja2`
5. `droidrun/agent/manager/manager_agent.py`：`_build_system_prompt`
6. `droidrun/agent/manager/stateless_manager_agent.py`：`_build_prompt`
7. `droidrun/agent/manager/prompts.py`：`parse_manager_response`

## 8. [不确定] 项
1. [不确定] `rev1.jinja2` 与 `trained.jinja2` 当前是否仍会被用户通过自定义 prompt 路径主动引用，仓库主路径里没有直接证明。
2. [不确定] 有状态模板和无状态模板是否已经完全与各自解析协议同步，还需要结合更多运行样本验证边界输出格式。

## 9. 覆盖率与下一轮
### 9.1 本轮已覆盖
1. `droidrun/config/prompts/manager/system.jinja2`
2. `droidrun/config/prompts/manager/stateless.jinja2`
3. `droidrun/config/prompts/manager/rev1.jinja2`
4. `droidrun/config/prompts/manager/trained.jinja2`

### 9.2 下一轮建议
1. `droidrun/agent/providers/registry.py`、`setup_service.py`、`cli/configure_wizard.py`、`cli/tui/settings/data.py` 的 provider 配置联动链
2. `droidrun/tools/__init__.py`、`droidrun/tools/driver/__init__.py`、`droidrun/tools/helpers/__init__.py` 的包级导出门面
3. `docs/concepts/` 与 `docs/analysis/` 的映射关系整理

## 10. 小结
这个文件夹里的文件本质上是在定义“Manager 应该怎样思考、怎样总结、怎样宣布完成”。`system.jinja2` 是默认有状态规划模板，`stateless.jinja2` 是无状态规划模板，`rev1.jinja2` 和 `trained.jinja2` 则更像 prompt 设计演进过程中保留下来的对照版本。理解这一层，才能真正看懂为什么 `ManagerAgent` 在运行时会输出现在这样的结构化 planning 文本。
