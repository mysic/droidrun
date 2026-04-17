# 35 Config资源层教程（Prompts、AppCards、CredentialsExample）

承接：前几轮主要分析 Python 模块和 workflow 逻辑，但 `droidrun/config/` 其实同样重要。它虽然不是“可执行源码”，却直接决定 Agent 如何说话、如何规划、如何执行，以及如何给特定 App 注入操作知识。所以这一层也应该被分析，而且要用“资源配置层”视角来讲，而不是把它当普通 Python 文件来讲。

## 1. 学习目标
1. 理解为什么 `config/` 虽然不是 Python 代码，仍然属于必须讲解的运行时核心资源。
2. 理解 prompt 模板如何分别驱动 Manager、Stateless Manager、Executor、FastAgent。
3. 理解 app cards 和凭证示例文件为什么是“行为配置”，而不只是静态文档。

## 2. 分析范围
1. `droidrun/config/credentials_example.yaml`
2. `droidrun/config/app_cards/app_cards.json`
3. `droidrun/config/app_cards/gmail.md`
4. `droidrun/config/app_cards/README.md`
5. `droidrun/config/prompts/executor/system.jinja2`
6. `droidrun/config/prompts/fast_agent/system.jinja2`
7. `droidrun/config/prompts/fast_agent/user.jinja2`
8. `droidrun/config/prompts/manager/system.jinja2`
9. `droidrun/config/prompts/manager/stateless.jinja2`
10. `droidrun/config/prompts/manager/rev1.jinja2`
11. `droidrun/config/prompts/manager/trained.jinja2`

排除项：
1. `PromptLoader`、`PathResolver` 的实现细节
2. `app_cards` provider 的 Python 读取逻辑
3. `CredentialManager` 的文件解析实现

## 3. 架构/流程总览
文字图：
1. Python 代码从 `config_manager` 读取配置与模板路径。
2. `PromptLoader` 渲染 `config/prompts/*.jinja2`，生成真正喂给 LLM 的系统/用户提示词。
3. `ManagerAgent`、`StatelessManagerAgent`、`ExecutorAgent`、`FastAgent` 各自使用不同模板。
4. `app_cards.json` 决定当前包名映射到哪个 markdown 指南。
5. `gmail.md` 这类 app card 在运行期被注入 prompt，改变模型对特定 App 的操作策略。
6. `credentials_example.yaml` 给用户声明凭证文件格式，从而影响 `type_secret` 等能力如何被实际配置。

## 4. 文件级讲解（按职责分组）
### 4.1 Prompt 模板族
1. 文件：`droidrun/config/prompts/manager/system.jinja2`、`stateless.jinja2`、`rev1.jinja2`、`trained.jinja2`
2. 做什么：定义规划器如何理解当前任务、设备状态、memory、历史动作和完成条件。
3. 关键符号：Jinja2 变量如 `instruction`、`app_card`、`error_history`、`output_schema`、`current_state`
4. 调用关系：`PromptResolver` / `PromptLoader` -> Manager 类 workflow -> LLM planning
5. 初学者易错点：
   - 这些模板不是“注释文案”，而是直接改变 LLM 推理方式的运行时策略。
   - `system.jinja2` 和 `stateless.jinja2` 对应的是两条不同的 planning 模式，不只是文件名不同。
   - `rev1.jinja2`、`trained.jinja2` 更像历史/实验版本，也值得记录，因为它们透露了 prompt 演进方向。

### 4.2 Executor / FastAgent 提示词
1. 文件：`droidrun/config/prompts/executor/system.jinja2`、`droidrun/config/prompts/fast_agent/system.jinja2`、`user.jinja2`
2. 做什么：约束执行器和快速代理怎样把高层任务转成具体工具调用。
3. 关键符号：原子动作说明、工具 XML/JSON 输出约束、行为规则、`available_secrets`、`tool_descriptions`
4. 调用关系：Executor/FastAgent workflow -> `PromptLoader` 渲染 -> LLM 输出动作调用
5. 初学者易错点：
   - Executor prompt 偏“机械执行当前 subgoal”，FastAgent prompt 偏“闭环自驱动代理”，两者定位不同。
   - 这类模板文本本身就是“行为协议”，和代码里的 parser、ToolRegistry 是一组配套设计。

### 4.3 App Cards 资源
1. 文件：`droidrun/config/app_cards/app_cards.json`、`gmail.md`、`README.md`
2. 做什么：建立包名到 markdown 指南的映射，并为特定应用注入操作领域知识。
3. 关键符号：`com.google.android.gm` -> `gmail.md`
4. 调用关系：当前包名 -> app card provider -> markdown 内容 -> Manager/FastAgent prompt 注入
5. 初学者易错点：
   - `app_cards.json` 不是普通示例数据，它直接决定某个 App 是否会被加载专属指导。
   - `gmail.md` 这类内容不是给人类读的帮助文档，而是写给 Agent 的任务先验知识。
   - `README.md` 解释了 path resolution、组织方式和最佳实践，属于“资源系统规范文档”。

### 4.4 凭证示例资源
1. 文件：`droidrun/config/credentials_example.yaml`
2. 做什么：定义用户应该如何组织 secrets 文件，从而让 `CredentialManager` 和 `type_secret` 工具在运行时真正可用。
3. 关键符号：`secrets:`、dict 形式 `value/enabled`、简单字符串形式、`type_secret` 用法示例
4. 调用关系：用户复制并填写示例 -> `config/credentials.yaml` -> `FileCredentialManager` 加载 -> Agent 获得安全输入能力
5. 初学者易错点：
   - 这是“配置契约示例”，不是无关说明文档；它实际定义了用户该如何提供运行时密钥。
   - `enabled: false` 这类字段会直接影响 secret 是否被加载。

## 5. Python 知识点联动
1. 语法/关键字/内置函数：Jinja2 模板变量、条件分支、循环、资源映射、YAML 结构约定
2. 在本项目中的位置：`*.jinja2` 中的 `{% if %}` / `{% for %}`、`app_cards.json` 映射、`credentials_example.yaml` 的两种 secrets 写法
3. 为什么这样写：
   - 把 prompt 放到模板资源层，便于运行时覆写和实验迭代，而不必频繁改 Python 代码。
   - 把 app-specific 知识放到 markdown 资源中，便于独立扩展和版本化管理。
   - 用示例 YAML 声明凭证契约，能降低用户配置成本并减少错误格式输入。
4. 最小示例：
```jinja2
{% if app_card %}
<app_card>
{{ app_card }}
</app_card>
{% endif %}
```
5. 常见错误与修正：
   - 错误：把 prompt 模板当成普通文档，不纳入行为分析。
   - 修正：把它们视为 Agent 行为协议的一部分。
   - 错误：以为 app card 只是示例说明，不会影响模型。
   - 修正：它会在运行时被注入 prompt，直接影响决策。

## 6. 证据清单
1. `droidrun/config/prompts/manager/system.jinja2`
2. `droidrun/config/prompts/manager/stateless.jinja2`
3. `droidrun/config/prompts/manager/rev1.jinja2`
4. `droidrun/config/prompts/manager/trained.jinja2`
5. `droidrun/config/prompts/executor/system.jinja2`
6. `droidrun/config/prompts/fast_agent/system.jinja2`
7. `droidrun/config/prompts/fast_agent/user.jinja2`
8. `droidrun/config/app_cards/app_cards.json`
9. `droidrun/config/app_cards/gmail.md`
10. `droidrun/config/app_cards/README.md`
11. `droidrun/config/credentials_example.yaml`

## 7. [不确定] 项
1. [不确定] `rev1.jinja2` 与 `trained.jinja2` 当前是否仍被正式运行路径使用，还是主要作为历史/实验模板保留。
2. [不确定] prompt 资源未来是否会进一步从包内默认模板迁移到用户工作目录优先的配置模式，这取决于实际使用习惯。

## 8. 覆盖率与下一轮
### 8.1 本轮已覆盖
1. `droidrun/config/credentials_example.yaml`
2. `droidrun/config/app_cards/app_cards.json`
3. `droidrun/config/app_cards/gmail.md`
4. `droidrun/config/app_cards/README.md`
5. `droidrun/config/prompts/executor/system.jinja2`
6. `droidrun/config/prompts/fast_agent/system.jinja2`
7. `droidrun/config/prompts/fast_agent/user.jinja2`
8. `droidrun/config/prompts/manager/system.jinja2`
9. `droidrun/config/prompts/manager/stateless.jinja2`
10. `droidrun/config/prompts/manager/rev1.jinja2`
11. `droidrun/config/prompts/manager/trained.jinja2`

### 8.2 下一轮建议
1. `droidrun/agent/providers/registry.py`、`setup_service.py`、`cli/configure_wizard.py`、`cli/tui/settings/data.py` 的 provider 配置联动链
2. `droidrun/tools/__init__.py`、`droidrun/tools/driver/__init__.py`、`droidrun/tools/helpers/__init__.py` 的包级导出门面
3. `droidrun/cli/tui/settings/` 下各页签组件的更细粒度配置映射

## 9. 小结
所以，`config/` 目录不仅需要分析，而且非常值得单独讲。它不是 Python 执行逻辑层，而是 Droidrun 的“运行时资源层”：prompt 模板决定 LLM 行为，app cards 提供领域知识，凭证示例定义用户如何把安全输入能力接进系统。忽略这一层，会漏掉一大块真正影响 Agent 行为的机制。
