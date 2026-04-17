# 03 动作系统教程（Actions、UIState、StateProvider）

承接：前两轮已经讲清了“谁来规划、谁来执行”。这一轮进入更底层的一层，回答一个更具体的问题：当 Agent 决定“点击某个元素”时，代码到底是怎么把这个决策变成真实设备动作的？

## 1. 学习目标
1. 看懂动作函数 `actions.py` 的职责和分类。
2. 理解 `UIState` 如何把 UI 树变成“可点击元素 + 坐标”。
3. 理解 `StateProvider` 如何从设备抓取状态并加工成 Agent 可消费的快照。
4. 理解 `ActionResult` 为什么是动作系统里的统一返回结构。

## 2. 分析范围
1. 包含：`droidrun/agent/utils/actions.py`
2. 包含：`droidrun/tools/ui/provider.py`
3. 包含：`droidrun/tools/ui/state.py`
4. 包含：`droidrun/agent/action_result.py`
5. 包含：`droidrun/agent/common/events.py`、`droidrun/agent/common/constants.py`
6. 排除：更底层的 PortalClient、几何工具函数、坐标帮助函数实现细节。

## 3. 一句话先记住
1. `actions.py` 负责“定义动作”。
2. `UIState` 负责“理解界面元素”。
3. `StateProvider` 负责“从设备抓状态并整理成 UIState”。
4. `ActionResult` 负责“统一动作执行结果”。

## 4. 从模型决策到真实动作的链路
```text
LLM 产出动作名 + 参数
-> ToolRegistry.execute(...)
-> actions.py 中某个动作函数
-> ctx.ui 解析元素 / 坐标
-> ctx.driver 执行真实设备操作
-> 返回 ActionResult
-> 上层 Agent 再决定下一步
```

## 5. 文件级讲解
### 5.1 actions.py：动作函数总表
文件：`droidrun/agent/utils/actions.py`

它做什么：
1. 定义所有“可被 Agent 调用”的标准动作。
2. 通过 `ctx.driver` 真正操作设备。
3. 通过 `ctx.ui` 做索引到坐标、区域到绝对坐标的转换。
4. 每个动作都统一返回 `ActionResult`。

动作可以分成三类：
1. 核心 UI 动作：`click`、`long_press`、`click_at`、`click_area`、`swipe`、`type_text`
2. 应用和系统动作：`open_app`、`open_bundle_id`、`system_button`
3. 状态和流程动作：`remember`、`complete`、`wait`、`type_secret`

最重要的设计点：
1. 这些函数不直接持有设备对象，而是通过 `ctx` 访问依赖。
2. 这样动作函数更容易复用，也更容易测试。
3. 每个动作都负责把错误转换成统一的失败结果，而不是直接把异常抛给最上层。

### 5.2 ActionResult：动作系统的统一返回值
文件：`droidrun/agent/action_result.py`

它做什么：
1. 用 `success + summary` 统一描述动作结果。
2. 让上层 Agent 不用关心底层动作到底返回字符串、元组还是别的对象。

教程式理解：
这很像后端服务里统一的 `Result<T>`，上层只看“成功没成功”和“总结信息是什么”。

### 5.3 UIState：把 UI 树变成可操作对象
文件：`droidrun/tools/ui/state.py`

它做什么：
1. 保存当前这一帧的元素树、格式化文本、焦点文本、屏幕尺寸、手机状态。
2. 提供 `get_element`、`get_element_coords`、`get_element_info` 等方法。
3. 负责把“元素索引”转成“可点击坐标”。
4. 在归一化坐标模式下，负责把相对点转换成绝对像素点。

这很关键，因为模型并不直接认识 Android View 对象，它只认识“第几个元素”“哪个 bounds”。UIState 就是这两者之间的翻译层。

### 5.4 StateProvider：状态抓取与恢复机制
文件：`droidrun/tools/ui/provider.py`

它做什么：
1. 调 driver 读取原始 UI 数据。
2. 在失败时重试，并在必要时触发 recovery。
3. 对 UI 树做 filter 和 formatter。
4. 最终返回 `UIState` 或 `StealthUIState`。

最重要的函数：
1. `fetch_state_with_retry`
2. `AndroidStateProvider.get_state`
3. `AndroidStateProvider._recover_portal`

教程式理解：
它像一个“状态采集器 + 修复器”。如果 Portal 或无障碍状态偶发失败，它不会立刻放弃，而是会重试、必要时重启相关能力。

### 5.5 事件与常量：动作系统周边配套
文件：`droidrun/agent/common/events.py`、`droidrun/agent/common/constants.py`

它们做什么：
1. `ToolExecutionEvent` 用来把工具执行结果写入工作流事件流。
2. `LLM_HISTORY_LIMIT` 控制历史消息裁剪上限。

这说明动作系统不是孤立存在的，它和上层 Agent 的事件流、Prompt 长度控制是连在一起的。

## 6. 典型动作执行过程
### 6.1 点击某个索引元素
1. Agent 生成动作：`{"action": "click", "index": 5}`
2. `ToolRegistry.execute` 找到 `click` 函数
3. `click()` 调 `ctx.ui.get_element_coords(5)`
4. `UIState` 根据元素 bounds 算出中心点
5. `click()` 调 `ctx.driver.tap(x, y)`
6. 返回 `ActionResult(success=True, summary=...)`

### 6.2 滑动操作
1. Agent 提供两个点位列表
2. `swipe()` 检查参数格式是否合法
3. `ctx.ui.convert_point()` 把点位变成绝对像素
4. `ctx.driver.swipe(...)` 真正执行
5. 返回滑动结果

### 6.3 输入文本
1. `type_text()` 可先通过 index 聚焦输入框
2. 然后调用 `ctx.driver.input_text(text, clear)`
3. 根据底层返回值组装成功或失败结果

## 7. Python 知识点联动
### 7.1 关键字参数 `*, ctx`
项目位置：几乎所有动作函数。

作用：
强制 `ctx` 只能以关键字方式传入，避免参数位置混乱。

最小示例：
```python
def demo(x, *, ctx):
    return x, ctx
```

### 7.2 `@dataclass`
项目位置：`ActionResult`

作用：
快速定义数据承载对象，省掉手写 `__init__`。

### 7.3 `Optional` / `Tuple` / `List` / `Dict`
项目位置：`UIState`、`StateProvider`

作用：
描述复杂结构，让“元素列表”“屏幕坐标”“手机状态”这些概念更清晰。

### 7.4 `@classmethod`
这一轮虽然不是主角，但和前面的 `ConfigLoader` 类似，说明 Python 里“类方法”和“实例方法”是有明确分工的。

### 7.5 异步重试
项目位置：`fetch_state_with_retry`

作用：
当外部设备状态不稳定时，不立刻失败，而是按计划重试并可触发恢复动作。

## 8. 源码注释落点
本轮已将教程式注释补到这些起始位置前：
1. `actions.py` 中模块入口、核心动作区块和代表性动作函数
2. `action_result.py` 中 `ActionResult`
3. `provider.py` 中 `fetch_state_with_retry`、`StateProvider`、`AndroidStateProvider`
4. `state.py` 中 `UIState`、关键元素解析函数
5. `events.py` 与 `constants.py` 的核心定义处

## 9. 证据清单
1. `droidrun/agent/utils/actions.py`：`click`、`type_text`、`swipe`、`complete`
2. `droidrun/agent/action_result.py`：`ActionResult`
3. `droidrun/tools/ui/provider.py`：`fetch_state_with_retry`、`AndroidStateProvider.get_state`
4. `droidrun/tools/ui/state.py`：`UIState.get_element_coords`、`UIState.convert_point`
5. `droidrun/agent/common/events.py`：`ToolExecutionEvent`
6. `droidrun/agent/common/constants.py`：`LLM_HISTORY_LIMIT`

## 10. [不确定] 项
1. [不确定] `tree_filter` 和 `tree_formatter` 的具体裁剪/格式化策略还未深入到实现文件。
2. [不确定] `AppStarter` 工作流的内部打开应用逻辑还未展开。

## 11. 覆盖率与下一轮
### 11.1 本轮已覆盖
1. `droidrun/agent/utils/actions.py`
2. `droidrun/agent/action_result.py`
3. `droidrun/tools/ui/provider.py`
4. `droidrun/tools/ui/state.py`
5. `droidrun/tools/ui/__init__.py`
6. `droidrun/agent/common/events.py`
7. `droidrun/agent/common/constants.py`

### 11.2 下一轮建议
1. `droidrun/tools/filters/*`
2. `droidrun/tools/formatters/*`
3. `droidrun/cli/event_handler.py`
4. `droidrun/agent/droid/events.py`
5. `droidrun/mcp/*`

## 12. 小结
到这一轮为止，你已经能把“Agent 做决定”拆解到“动作函数如何执行”和“UI 状态如何提供坐标依据”的层级了。接下来如果继续下钻到 filters 和 formatters，你就能完整看懂从 Portal 原始 UI 树到最终提示文本的全链路。