# 27 配置加载与密钥解析教程（EnvKeys、Loader、PathResolver）

承接：第 26 轮讲完 MCP 接入，这一轮回到配置底座，专门讲 config_manager 中“密钥来源、配置迁移、路径解析优先级”三条主链。

## 1. 学习目标
1. 理解 API key 在 shell 与文件间的优先级策略。
2. 理解配置加载与迁移的触发时机。
3. 理解路径解析如何支持“用户覆盖内置资源”。

## 2. 分析范围
1. droidrun/config_manager/env_keys.py
2. droidrun/config_manager/loader.py
3. droidrun/config_manager/path_resolver.py

## 3. 密钥解析层：env_keys.py
它做什么：
1. 维护 provider slot 到环境变量名的映射。
2. 分离读取 shell 与 saved 文件两种来源（ApiKeySources）。
3. 按 source 参数返回 env/file/auto 模式结果。
4. 保存时回写 auth_profiles，并同步当前进程环境变量。

关键点：
1. 默认读取是 saved > shell，保证向导写入结果优先。
2. 保存使用临时文件 + 原子替换，避免中断导致配置损坏。
3. 目标文件权限尝试设为 600，降低泄露风险。

## 4. 配置加载层：loader.py
它做什么：
1. 按优先级解析配置来源：参数 > 环境变量 > 用户目录 > 首次初始化。
2. 加载用户配置后执行版本迁移。
3. 迁移后若版本变化自动回写。

关键点：
1. 缺少 _version 会被判定为过期配置并抛出明确错误。
2. save 时统一写入当前版本号，形成可持续迁移基线。

## 5. 路径解析层：path_resolver.py
它做什么：
1. 统一处理绝对路径与相对路径。
2. 读取模式优先工作目录，其次包内目录。
3. 创建模式优先工作目录。

教程式理解：
PathResolver 把“查找规则”集中化，避免各模块各写一套路径拼接逻辑。

## 6. Python 知识点联动
### 6.1 原子文件写入
项目位置：droidrun/config_manager/env_keys.py

作用：
提升配置写入可靠性，避免半写文件。

### 6.2 配置迁移策略
项目位置：droidrun/config_manager/loader.py

作用：
保证版本升级后配置结构可自动演进。

### 6.3 资源覆盖优先级
项目位置：droidrun/config_manager/path_resolver.py

作用：
支持用户本地覆盖内置模板而不改包源码。

## 7. 源码注释落点
本轮已补充教程注释的位置：
1. env_keys.py 的读取优先级与原子写入说明
2. loader.py 的迁移后自动回写说明
3. path_resolver.py 的工作目录优先覆盖说明

## 8. 证据清单
1. droidrun/config_manager/env_keys.py: load_env_keys, save_env_keys
2. droidrun/config_manager/loader.py: load, _load_user_config
3. droidrun/config_manager/path_resolver.py: resolve

## 9. [不确定] 项
1. [不确定] 多进程并发写 auth_profiles 时是否需要显式文件锁，当前实现主要覆盖单进程场景。
2. [不确定] 路径覆盖策略在非常规工作目录启动方式下的用户预期一致性仍可补文档说明。

## 10. 覆盖率与下一轮
### 10.1 本轮已覆盖
1. droidrun/config_manager/env_keys.py
2. droidrun/config_manager/loader.py
3. droidrun/config_manager/path_resolver.py

### 10.2 下一轮建议
1. droidrun/telemetry/events.py
2. droidrun/telemetry/tracker.py（联动回顾）
3. droidrun/telemetry/__init__.py

## 11. 小结
这一轮把配置系统最关键的底层逻辑串起来了：密钥来源可控、配置迁移可持续、路径解析可覆盖，三者一起保证配置体验稳健可维护。