# 38 Guides文档教程（Overview、CLI、DeviceSetup、Docker）

承接：`features/` 讲的是能力面，`guides/` 讲的则是上手路径。这个目录里的文档不是 API 参考，而是把“第一次接触 Droidrun 的人应该怎么开始、怎么连设备、怎么在 Docker 里跑起来”组织成一条完整的操作链。

## 1. 学习目标
1. 理解 `docs/guides/` 的主要职责是 onboarding 和操作流程，而不是概念讲解或源码索引。
2. 理解 `overview -> cli -> device-setup -> docker` 其实构成了一条递进式使用路径。
3. 理解这些页面如何把零散 CLI 命令、设备要求和容器环境约束收束成可执行步骤。

## 2. 分析范围
1. `docs/guides/overview.mdx`
2. `docs/guides/cli.mdx`
3. `docs/guides/device-setup.mdx`
4. `docs/guides/docker.mdx`

排除项：
1. `docs/quickstart.mdx` 顶层快速开始页
2. `docs/sdk/configuration.mdx` 的参数级配置详解
3. Portal Android 工程本身的实现细节

## 3. 结构定位
文字图：
1. `overview.mdx` 负责导览整组 guide。
2. `cli.mdx` 负责列出命令入口与常用参数。
3. `device-setup.mdx` 负责解决“设备怎么连起来”。
4. `docker.mdx` 负责解决“本机不装原生环境时怎么跑”。

这意味着 `guides/` 更像“使用流程设计”，不是简单按功能堆页面。

## 4. 文件级讲解
### 4.1 overview.mdx：导览页
1. 做什么：把 CLI、设备安装、配置系统以及 examples 仓库统一挂到一个入口。
2. 作用：帮助用户先形成全局地图，再决定深入哪个主题。
3. 特点：它不讲细节，重点是目录导航和学习路径设计。

### 4.2 cli.mdx：命令入口总表
1. 做什么：集中说明 `run`、`setup`、`devices`、`connect`、`disconnect`、`ping`、`device` 等命令与常见参数。
2. 作用：把 `droidrun` 当成一个可运维、可调试、可直连设备的 CLI 工具来介绍，而不只是一个 Python SDK。
3. 关键价值：它同时覆盖高层自然语言执行和低层 `device` 直控命令，体现出框架兼具 agent 模式与 direct tooling 模式。

### 4.3 device-setup.mdx：设备接入教程
1. 做什么：系统解释 Android Portal、ADB、TCP / Content Provider 两种通信方式、无线调试、多设备控制和常见故障处理。
2. 作用：把“Agent 为什么能控制设备”翻译成实际操作步骤。
3. 关键价值：这页不是产品宣传，而是在帮用户跨过真实的环境门槛，这比 API 文档更接近成功落地的关键路径。

### 4.4 docker.mdx：容器运行教程
1. 做什么：说明如何在容器里挂载手机、ADB key、USB 总线，以及为什么要写 udev 规则和杀掉宿主机 ADB server。
2. 作用：把 Docker 场景中最容易踩坑的“设备映射”提前讲清楚。
3. 关键价值：它补的是“部署约束”，不是 SDK 能力本身，但对 CI / 远程运行 / 隔离环境很关键。

## 5. 这组文档隐含的用户旅程
1. 先从 `overview` 知道有哪些入口。
2. 去 `cli` 学会怎么发命令。
3. 去 `device-setup` 解决设备与 Portal 连通问题。
4. 如果本机环境不方便，则转到 `docker` 方案。

所以这四页不是并列关系，而是明显带有用户成长顺序。

## 6. 与源码/工程层的对应关系
1. `cli.mdx` 对应 `droidrun/cli/` 子系统，以及第 10、21、22、30 轮里分析过的 CLI/TUI 路径。
2. `device-setup.mdx` 对应 Android Portal 安装、`AndroidDriver`、`PortalClient` 和设备发现逻辑，也关联第 16、18 轮。
3. `docker.mdx` 对应仓库根目录 `Dockerfile` 和宿主机 USB / ADB 约束，但更偏部署层文档。
4. `overview.mdx` 则是文档信息架构层，把这些能力组织成一条可学路径。

## 7. 初学者最容易忽略的点
1. `cli.mdx` 不只是命令参考，它在产品层明确区分了 reasoning、vision、trajectory、provider override 等运行模式。
2. `device-setup.mdx` 清晰区分 TCP 模式与 Content Provider 模式，而且说明它们是“按次运行可切换”的，不是一次性全局锁定。
3. `device-setup.mdx` 里的 troubleshooting 非常关键，因为 Droidrun 的主要失败点往往发生在环境接入，而不是 agent 逻辑本身。
4. `docker.mdx` 真正难点不是 `docker pull`，而是 USB 设备路径稳定化和宿主机 ADB 竞争问题。

## 8. 文档写法特点
1. 采用大量 step-by-step 操作块，而不是抽象说明。
2. 命令示例偏真实，可直接复制后修改。
3. 对常见故障给出明确诊断路径，而不是只写 happy path。
4. 与 `features/` 相比，这里更强调“怎么做”，少讲“为什么这样设计”。

## 9. 证据清单
1. `docs/guides/overview.mdx`
2. `docs/guides/cli.mdx`
3. `docs/guides/device-setup.mdx`
4. `docs/guides/docker.mdx`

## 10. [不确定] 项
1. [不确定] 未来是否会把 `quickstart` 与 `guides/overview` 进一步合并或重构，目前两者有一定导览层重叠。
2. [不确定] Docker 文档后续是否会补充 docker-compose / Kubernetes / 远程设备农场之类场景，目前还停留在单容器接手机模式。

## 11. 覆盖率与下一轮
### 11.1 本轮已覆盖
1. `docs/guides/overview.mdx`
2. `docs/guides/cli.mdx`
3. `docs/guides/device-setup.mdx`
4. `docs/guides/docker.mdx`

### 11.2 下一轮建议
1. `docs/sdk/` 的 API 参考层如何与前面已经分析过的源码对象建立一一映射。
2. `docs/features/`、`docs/guides/`、`docs/sdk/` 三层之间是否需要再补一轮“文档信息架构图”。

## 12. 小结
`docs/guides/` 的价值，在于它把 Droidrun 从“看起来很强的框架”变成“用户真的能装起来、连起来、跑起来的系统”。这一层离成功落地最近，所以虽然不是源码，但同样应该纳入分析。