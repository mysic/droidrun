# 31 凭证管理教程（CredentialManager、FileCredentialManager）

承接：第 27 轮讲过环境变量与配置加载，第 30 轮讲过 TUI 如何编辑配置。这一轮补上真正负责“把凭证名解析成密钥值”的子系统，也就是 credential_manager。

## 1. 学习目标
1. 理解为什么项目要把凭证解析抽象成独立接口。
2. 理解 FileCredentialManager 如何同时支持内存 dict、配置对象和 YAML 文件。
3. 理解“配置里引用密钥名”和“运行时得到真实密钥值”之间的边界。

## 2. 分析范围
1. droidrun/credential_manager/credential_manager.py
2. droidrun/credential_manager/file_credential_manager.py
3. droidrun/credential_manager/__init__.py

## 3. 抽象接口：credential_manager.py
它做什么：
1. 定义 `CredentialNotFoundError`，用于表达“请求的凭证不存在”。
2. 定义 `CredentialManager` 抽象基类。
3. 规定所有实现都必须支持 `resolve_key` 和 `get_keys` 两个异步接口。

教程式理解：
这一层像“凭证服务协议”。上层 Agent 或工具只需要知道“给我一个 key，我要值”，而不必知道这个值来自 YAML、环境变量映射，还是未来可能增加的远端密钥服务。

关键点：
1. 这里使用 `ABC` 和 `@abstractmethod`，说明设计者想强制不同实现遵守统一协议。
2. 接口被定义成 `async`，意味着未来即便接入网络密钥服务或数据库，也不用改上层调用方式。

## 4. 文件实现：file_credential_manager.py
它做什么：
1. `FileCredentialManager` 继承 `CredentialManager`。
2. `_load` 根据输入类型分发到不同加载路径。
3. `_load_from_dict` 处理内存字典形式的密钥。
4. `_load_from_file` 处理 YAML 文件，并支持 `enabled` 开关。
5. `resolve_key` 负责在运行时查找具体密钥值。
6. `get_keys` 暴露当前可用的密钥名列表。

教程式理解：
这个实现相当于“默认凭证后端”。它先把外部各种输入整理成统一的 `self.secrets` 字典，之后所有读取都只对这张表操作。

关键点：
1. `_load` 支持三种来源：原始 dict、`CredentialsConfig`、字符串文件路径，说明这个类同时面向测试场景和正式配置场景。
2. `_load_from_file` 先调用 `PathResolver.resolve`，表明凭证文件路径也遵循项目统一路径解析规则。
3. YAML 里既支持 `SIMPLE_KEY: value`，也支持带 `enabled` 和 `value` 的对象形式，说明项目在保留简洁写法的同时，也提供了按 secret 关闭的能力。
4. `resolve_key` 出错时会把当前可用 keys 一并放进异常信息，这在排查引用错误时很有帮助。
5. `has_credential` 和 `__repr__` 虽然简单，但对调试体验很重要：一个用于快速判断存在性，一个用于打印当前管理器状态。

## 5. 包级导出：credential_manager/__init__.py
它做什么：
1. 统一导出抽象接口、默认实现和异常类型。
2. 为调用方提供单入口导入路径。

教程式理解：
这和 telemetry 包的做法一致，属于典型“包级门面”模式: 外部尽量不直接依赖子文件路径，降低内部重构成本。

## 6. Python 知识点联动
### 6.1 抽象基类 ABC
项目位置：droidrun/credential_manager/credential_manager.py

作用：
把“必须实现的方法”写成协议，避免不同凭证后端各自为政。

### 6.2 异常类型分层
项目位置：droidrun/credential_manager/credential_manager.py

作用：
自定义 `CredentialNotFoundError` 比直接抛 `KeyError` 更清楚，调用方也更容易按语义捕获。

### 6.3 多来源统一归一化
项目位置：droidrun/credential_manager/file_credential_manager.py

作用：
先把不同来源的输入归一为同一种内部结构，再统一提供查询接口，这是常见的数据接入层设计。

### 6.4 YAML 配置解析
项目位置：droidrun/credential_manager/file_credential_manager.py

作用：
通过 `yaml.safe_load` 读取结构化配置，比手写文本解析更稳健，也更适合人编辑。

## 7. 源码注释落点
本轮已补充教程注释的位置：
1. credential_manager.py 的抽象接口职责
2. file_credential_manager.py 的总分发、dict/file 加载、resolve_key、get_keys
3. credential_manager/__init__.py 的包级导出意图

## 8. 证据清单
1. droidrun/credential_manager/credential_manager.py: `CredentialManager`, `CredentialNotFoundError`
2. droidrun/credential_manager/file_credential_manager.py: `_load`, `_load_from_dict`, `_load_from_file`, `resolve_key`, `get_keys`
3. droidrun/credential_manager/__init__.py: package exports

## 9. [不确定] 项
1. [不确定] 当前仓库是否还存在其他非文件型 CredentialManager 实现，如果后续新增远端密钥后端，需要再补一轮对比分析。
2. [不确定] 凭证 YAML 的热更新是否有需求；当前实现看起来更偏一次加载、长期使用。

## 10. 覆盖率与下一轮
### 10.1 本轮已覆盖
1. droidrun/credential_manager/credential_manager.py
2. droidrun/credential_manager/file_credential_manager.py
3. droidrun/credential_manager/__init__.py

### 10.2 下一轮建议
1. droidrun/agent/utils/signatures.py
2. droidrun/agent/oneflows/ 中尚未单独展开的标准化工作流
3. droidrun/agent/providers/setup_service.py 与 registry.py 的 provider 初始化链路

## 11. 小结
这一轮把凭证解析边界讲清楚了：`CredentialManager` 规定协议，`FileCredentialManager` 把不同来源归一为内存 secrets 表，`__init__.py` 提供稳定导出面。这样配置文件、TUI 设置和运行时取密钥之间的责任分层就完整了。