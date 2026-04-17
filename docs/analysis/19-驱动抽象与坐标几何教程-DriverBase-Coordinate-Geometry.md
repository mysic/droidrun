# 19 驱动抽象与坐标几何教程（DriverBase、Coordinate、Geometry）

承接：第 18 轮讲了 Android Portal 通信，这一轮补齐“最底层公共基础”：驱动抽象契约与坐标/几何工具函数。

## 1. 学习目标
1. 理解 DeviceDriver 作为跨平台能力契约的作用。
2. 理解归一化坐标与像素坐标的双向转换。
3. 理解遮挡判断与可点击点搜索的几何算法。

## 2. 分析范围
1. droidrun/tools/driver/base.py
2. droidrun/tools/helpers/coordinate.py
3. droidrun/tools/helpers/geometry.py

## 3. Driver 抽象：tools/driver/base.py
它做什么：
1. 定义设备驱动统一接口（连接、输入、应用管理、状态观察）。
2. 通过 `supported` 与 `supported_buttons` 声明能力边界。
3. 通过 `DeviceDisconnectedError` 统一设备断连异常语义。

教程式理解：
这是“平台隔离层”的最小契约。AndroidDriver、IOSDriver 只是不同实现，上层 Agent 面向同一接口编程。

## 4. 坐标转换：tools/helpers/coordinate.py
它做什么：
1. `to_absolute`：归一化坐标 -> 像素坐标。
2. `to_normalized`：像素坐标 -> 归一化坐标。
3. `bounds_to_normalized`：矩形边界字符串批量转换。

关键点：
1. 使用统一比例尺 [0,1000]，提升跨分辨率轨迹可迁移性。
2. 无屏幕尺寸时主动抛错，避免悄悄计算出无效坐标。

## 5. 几何工具：tools/helpers/geometry.py
它做什么：
1. `rects_overlap`：判断两个矩形是否重叠。
2. `find_clear_point`：在目标区域内递归查找不被遮挡的可点击点。

算法直觉：
1. 优先尝试中心点。
2. 若被遮挡，递归四分区域。
3. 选择可用且面积更大的候选区域，直到达到深度阈值。

## 6. Python 知识点联动
### 6.1 抽象契约与多态
项目位置：droidrun/tools/driver/base.py

作用：
固定接口、释放实现，便于新增平台驱动。

### 6.2 纯函数工具模块
项目位置：droidrun/tools/helpers/coordinate.py、droidrun/tools/helpers/geometry.py

作用：
无副作用、易测试、可在多个层重复复用。

### 6.3 递归搜索
项目位置：find_clear_point

作用：
在复杂遮挡场景中寻找更稳定点击点。

## 7. 源码注释落点
本轮已补充教程注释的位置：
1. DeviceDriver 类定位与按键能力裁剪说明
2. coordinate.py 的双向坐标转换入口
3. geometry.py 的重叠检测与四分递归搜索入口

## 8. 证据清单
1. droidrun/tools/driver/base.py: DeviceDriver
2. droidrun/tools/helpers/coordinate.py: to_absolute, to_normalized
3. droidrun/tools/helpers/geometry.py: rects_overlap, find_clear_point

## 9. [不确定] 项
1. [不确定] 当前归一化比例尺在极端长宽比设备上的点击精度损失边界仍可量化评估。
2. [不确定] 四分递归深度阈值在高密度遮挡页面是否需要动态调参，建议结合真实失败样本调优。

## 10. 覆盖率与下一轮
### 10.1 本轮已覆盖
1. droidrun/tools/driver/base.py
2. droidrun/tools/helpers/coordinate.py
3. droidrun/tools/helpers/geometry.py

### 10.2 下一轮建议
1. droidrun/tools/helpers/log_parser.py
2. droidrun/tools/helpers/screenshot.py
3. droidrun/tools/helpers/wait_utils.py

## 11. 小结
这一轮补齐了执行链最底层公共能力：统一驱动契约保证跨平台一致性，坐标与几何工具保证动作落点更稳定可控。