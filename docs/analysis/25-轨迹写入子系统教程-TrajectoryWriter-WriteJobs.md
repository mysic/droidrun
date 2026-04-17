# 25 轨迹写入子系统教程（TrajectoryWriter、WriteJobs）

承接：第 24 轮讲了 trajectory 的读取与统计，这一轮下钻到写入实现，解释轨迹数据如何异步落盘并生成截图 GIF。

## 1. 学习目标
1. 理解 write job 模型如何拆分不同写入任务。
2. 理解 WriterWorker 的队列消费与容错机制。
3. 理解 TrajectoryWriter 如何做快照、入队和最终收尾。

## 2. 分析范围
1. droidrun/agent/trajectory/writer.py
2. droidrun/agent/trajectory/__init__.py

## 3. 写入任务模型：WriteJob 家族
它做什么：
1. 抽象基类 `WriteJob` 统一异步执行接口。
2. 子类分别处理 events/macro/screenshot/gif/ui_state。
3. 每个 job 在创建时就持有快照数据，避免并发写入时读到脏数据。

关键点：
1. 任务对象不可变（frozen dataclass），降低并发修改风险。
2. GIF job 在后台线程执行图像合成，避免阻塞事件循环。

## 4. Worker 层：WriterWorker
它做什么：
1. 维护有界异步队列。
2. 串行消费任务并执行写入。
3. 统计写入成功数与错误数。
4. stop 时优先等待队列 drain，超时后告警。

教程式理解：
这是“写入泵”，确保 I/O 慢时不会拖慢主执行链。

## 5. 编排层：TrajectoryWriter
它做什么：
1. `start/stop` 管理后台 worker 生命周期。
2. `write` 对 trajectory 数据做快照并分解成 jobs。
3. `write_final` 在最终阶段补充 GIF 生成任务。

关键点：
1. 先快照再入队，避免运行中列表继续变化导致写入不一致。
2. 截图按固定编号写盘，保证 GIF 顺序稳定。
3. screenshot_queue 在入队后清空，避免重复写入。

## 6. 导出层：trajectory/__init__.py
它做什么：
1. 统一导出 `TrajectoryWriter` 与 `make_serializable`。
2. 对外暴露稳定导入入口，隐藏内部实现细节。

## 7. Python 知识点联动
### 7.1 有界队列与背压
项目位置：WriterWorker

作用：
限制瞬时写入峰值，降低内存风险。

### 7.2 不可变任务对象
项目位置：WriteJob dataclass

作用：
增强并发安全，减少任务执行时状态漂移。

### 7.3 事件循环与线程池协作
项目位置：GifWriteJob

作用：
把 CPU/IO 重任务放到 executor，保护异步主流程。

## 8. 源码注释落点
本轮已补充教程注释的位置：
1. WriterWorker 的队列上限说明
2. TrajectoryWriter.write 的快照策略说明
3. 截图任务编号写盘说明

## 9. 证据清单
1. droidrun/agent/trajectory/writer.py: WriteJob, WriterWorker, TrajectoryWriter.write
2. droidrun/agent/trajectory/writer.py: _create_screenshot_jobs, _create_gif_job
3. droidrun/agent/trajectory/__init__.py: module exports

## 10. [不确定] 项
1. [不确定] 极长轨迹下 screenshot 队列峰值与磁盘吞吐之间的平衡参数仍可进一步调优。
2. [不确定] GIF 合成在超大分辨率批量截图下的内存峰值需要压力测试验证。

## 11. 覆盖率与下一轮
### 11.1 本轮已覆盖
1. droidrun/agent/trajectory/writer.py
2. droidrun/agent/trajectory/__init__.py

### 11.2 下一轮建议
1. droidrun/mcp/adapter.py
2. droidrun/mcp/client.py
3. droidrun/mcp/config.py（串联回顾）

## 12. 小结
这一轮把 trajectory 的异步写入管线讲清楚了：通过 job 快照 + 有界队列 + 后台 worker，实现“主流程不阻塞、数据可复盘”的稳定落盘机制。