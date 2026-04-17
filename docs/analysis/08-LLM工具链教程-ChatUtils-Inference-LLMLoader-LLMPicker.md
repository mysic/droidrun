# 08 LLM 工具链教程（ChatUtils、Inference、LLMLoader、LLMPicker）

承接：上一轮已经把配置系统讲清了。这一轮继续把链路往下接，回答一个关键问题：配置里的 provider/model 是如何变成真正的模型对象，并最终发起请求的？

## 1. 学习目标
1. 理解消息如何从普通 dict 结构转换成 `ChatMessage`。
2. 理解模型调用为什么要统一封装重试和超时逻辑。
3. 理解 `load_agent_llms()` 与 `load_llm()` 的职责差异。
4. 看懂从配置到具体模型实例的完整装载链路。

## 2. 分析范围
1. `droidrun/agent/utils/chat_utils.py`
2. `droidrun/agent/utils/inference.py`
3. `droidrun/agent/utils/llm_loader.py`
4. `droidrun/agent/utils/llm_picker.py`

## 3. 一句话理解四个文件
1. `chat_utils.py` 负责“把消息整理成模型能吃的格式”。
2. `inference.py` 负责“稳妥地发起模型调用”。
3. `llm_loader.py` 负责“根据运行模式决定需要哪些模型”。
4. `llm_picker.py` 负责“真正实例化具体 provider 的 LLM 类”。

## 4. 消息准备层
### 4.1 chat_utils.py
它做什么：
1. 把普通字典消息转成 `ChatMessage`。
2. 把图片统一转成 bytes。
3. 过滤空消息。
4. 限制历史长度。

为什么重要：
不同 Agent 并不都直接操作 provider SDK，而是先把消息整理成 LlamaIndex 的统一消息结构。

## 5. 推理执行层
### 5.1 inference.py
它做什么：
1. 提供 `acall_with_retries()` 处理聊天调用。
2. 提供 `acompletion_with_retries()` 处理 completion 调用。
3. 提供 `astructured_predict_with_retries()` 处理结构化输出。
4. 统一处理超时、重试、流式输出和空返回检查。

为什么重要：
模型调用最容易出问题的地方就是超时、空结果、瞬时失败。这个文件相当于所有 Agent 的“抗抖动保护层”。

## 6. Agent 级 LLM 装载层
### 6.1 llm_loader.py
它做什么：
1. 根据 reasoning 模式决定需要哪些 profile。
2. 检查配置里是否缺少必须的模型配置。
3. 支持自定义 provider/model 覆盖全部 Agent。
4. 支持把用户传入的部分 llm dict 与配置补全合并。

教程式理解：
它像一个“LLM 编排器”，决定 Manager、Executor、FastAgent、app_opener、structured_output 各自该用哪个模型。

## 7. Provider 选择与实例化层
### 7.1 llm_picker.py
它做什么：
1. 根据 provider 名称选择对应类。
2. 处理 OAuth provider 特例。
3. 处理 MiniMax 到 OpenAILike 的兼容别名。
4. 从 `LLMProfile` 集合里批量构建实例。

最关键的一点：
这个文件是真正把“字符串 provider 名称”变成“可调用模型对象”的地方。

## 8. 完整链路
```text
config.yaml / 默认配置
-> DroidConfig.llm_profiles
-> load_agent_llms()
-> load_llms_from_profiles()
-> load_llm()
-> 得到各 Agent 对应的 LLM 实例

运行时：
messages / prompt
-> chat_utils 整理
-> inference.py 统一请求
-> provider SDK 真正发起调用
```

## 9. Python 知识点联动
### 9.1 TypeVar + 泛型
项目位置：`astructured_predict_with_retries`

作用：
让函数返回值与传入的 Pydantic 模型类型保持一致。

### 9.2 `getattr(..., default)`
项目位置：`inference.py` 中响应校验。

作用：
在不同 provider 返回对象不完全一致时更安全地读取属性。

### 9.3 `**kwargs`
项目位置：`load_llm`、`load_agent_llms`

作用：
让调用方灵活传入 provider 特有参数，而不需要把每个参数都写死。

### 9.4 列表裁剪与 preserve_first
项目位置：`limit_history`

作用：
控制上下文大小，同时保留首条系统/初始消息。

## 10. 源码注释落点
本轮已补充教程注释的位置：
1. `to_chat_messages` 与 `limit_history`
2. `acall_with_retries` 和结构化推理入口
3. `load_agent_llms`、`merge_llms_with_config`
4. `load_llm` 与 `load_llms_from_profiles`

## 11. 证据清单
1. `droidrun/agent/utils/chat_utils.py`：`to_chat_messages`、`limit_history`
2. `droidrun/agent/utils/inference.py`：`acall_with_retries`、`astructured_predict_with_retries`
3. `droidrun/agent/utils/llm_loader.py`：`load_agent_llms`、`merge_llms_with_config`
4. `droidrun/agent/utils/llm_picker.py`：`load_llm`、`load_llms_from_profiles`

## 12. [不确定] 项
1. [不确定] 某些 provider 在流式模式下的 raw/additional_kwargs 差异，还需要运行时抓包或 trace 验证。
2. [不确定] MiniMax 兼容路径的全部边界行为，还需要结合真实配置测试。

## 13. 覆盖率与下一轮
### 13.1 本轮已覆盖
1. `droidrun/agent/utils/chat_utils.py`
2. `droidrun/agent/utils/inference.py`
3. `droidrun/agent/utils/llm_loader.py`
4. `droidrun/agent/utils/llm_picker.py`

### 13.2 下一轮建议
1. `droidrun/app_cards/*`
2. `droidrun/agent/oneflows/*`
3. `droidrun/macro/*`

## 14. 小结
这一轮把“配置里的模型信息如何真正变成运行时模型调用”补齐了。到这里，Droidrun 的一条完整链路已经非常清楚：配置决定模型，消息整理成统一格式，请求通过推理保护层发出，最后由具体 provider 完成调用。