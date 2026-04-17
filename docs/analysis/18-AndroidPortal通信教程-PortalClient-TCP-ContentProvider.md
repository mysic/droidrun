# 18 Android Portal 通信教程（PortalClient、TCP、ContentProvider）

承接：第 17 轮讲了 UI 树过滤与格式化，这一轮继续向下聚焦 Android 侧“Portal 通信层”，解释统一通道、鉴权与回退策略。

## 1. 学习目标
1. 理解 PortalClient 如何屏蔽 TCP 与 content provider 差异。
2. 理解 token 获取与 401/403 重试机制。
3. 理解状态、输入、截图等能力的降级路径。

## 2. 分析范围
1. droidrun/tools/android/portal_client.py
2. droidrun/tools/android/__init__.py

## 3. PortalClient 的定位
它做什么：
1. 为 AndroidDriver 提供统一 Portal 调用接口。
2. 在连接阶段尽力启用 TCP 高性能通道。
3. 失败时自动回退到 content provider，保证可用性优先。

教程式理解：
PortalClient 是“通信适配器 + 回退控制器”。上层只关心业务动作，不关心底层通道。

## 4. 连接与鉴权流程
关键流程：
1. connect：按 prefer_tcp 决定是否尝试 TCP。
2. _fetch_auth_token：通过 content provider 拉取 HTTP Bearer token。
3. _try_enable_tcp：
   - 复用现有端口转发，找不到则创建
   - 测试 /ping 连通
   - 如失败尝试启动 socket server，再测一次
4. _tcp_request：统一处理 401/403，自动刷新 token 并重试。

关键点：
1. token 获取通道和 HTTP 通道分离，安全且清晰。
2. 所有 TCP 请求共用同一重试策略，降低重复代码和行为分叉。

## 5. 核心能力与回退路径
### 5.1 get_state
1. 优先 `_get_state_tcp`。
2. 失败回退 `_get_state_content_provider`。
3. 输出目标是统一结构：a11y_tree / phone_state / device_context。

### 5.2 input_text
1. 优先 TCP `/keyboard/input`。
2. 失败回退 content insert 命令。

### 5.3 take_screenshot
1. 优先 TCP `/screenshot` 返回 base64。
2. 失败回退 ADB `screenshot_bytes`。

### 5.4 get_apps / get_version / ping
1. 兼容新旧返回格式（result/data）。
2. ping 还会额外验证 state 关键字段，判断 Portal 协议是否兼容。

## 6. Python 知识点联动
### 6.1 渐进降级策略
项目位置：droidrun/tools/android/portal_client.py

作用：
先追求性能（TCP），再保底可用（content provider/ADB）。

### 6.2 单一请求入口
项目位置：_tcp_request

作用：
将鉴权重试集中在一个 choke-point，避免多处实现不一致。

### 6.3 容错解析
项目位置：_parse_content_provider_output

作用：
兼容多种历史响应形态，减轻服务端变更影响。

## 7. 源码注释落点
本轮已补充教程注释的位置：
1. PortalClient 类定位说明
2. _try_enable_tcp（TCP 优先与降级）
3. _tcp_request（鉴权重试统一入口）
4. get_state / input_text / take_screenshot（双通道选择策略）

## 8. 证据清单
1. droidrun/tools/android/portal_client.py: _try_enable_tcp
2. droidrun/tools/android/portal_client.py: _tcp_request
3. droidrun/tools/android/portal_client.py: get_state
4. droidrun/tools/android/portal_client.py: input_text
5. droidrun/tools/android/portal_client.py: take_screenshot

## 9. [不确定] 项
1. [不确定] 不同厂商 ROM 下 content provider 输出格式是否还存在额外分支，建议继续积累现场样本。
2. [不确定] 大量并发请求时 token 刷新竞争是否会导致瞬时重复重试，可在高并发压测后评估。

## 10. 覆盖率与下一轮
### 10.1 本轮已覆盖
1. droidrun/tools/android/portal_client.py
2. droidrun/tools/android/__init__.py

### 10.2 下一轮建议
1. droidrun/tools/driver/base.py
2. droidrun/tools/helpers/coordinate.py
3. droidrun/tools/helpers/geometry.py

## 11. 小结
这一轮完成了 Android Portal 通信底座的讲解：统一接口、自动鉴权、通道切换与故障降级都在 PortalClient 内集中实现，确保上层动作链路稳定可用。