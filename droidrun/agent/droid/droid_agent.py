"""
DroidAgent - A wrapper class that coordinates the planning and execution of tasks
to achieve a user's goal on a mobile device.

Architecture:
- When reasoning=False: Uses FastAgent directly
- When reasoning=True: Uses Manager (planning) + Executor (action) workflows
"""

import logging
import os
import traceback
from typing import TYPE_CHECKING, Awaitable, Type, Union

from llama_index.core.llms.llm import LLM
from llama_index.core.workflow import Context, StartEvent, StopEvent, Workflow, step
from opentelemetry import trace
from pydantic import BaseModel
from workflows.events import Event
from workflows.handler import WorkflowHandler

from droidrun.agent.action_context import ActionContext
from droidrun.agent.fast_agent import FastAgent
from droidrun.agent.fast_agent.events import FastAgentOutputEvent
from droidrun.agent.common.events import RecordUIStateEvent, ScreenshotEvent
from droidrun.agent.droid.events import (
    ExecutorInputEvent,
    ExecutorResultEvent,
    ExternalUserMessageDroppedEvent,
    FastAgentExecuteEvent,
    FastAgentResultEvent,
    FinalizeEvent,
    ManagerInputEvent,
    ManagerPlanEvent,
    ResultEvent,
)
from droidrun.agent.droid.state import DroidAgentState, QueuedUserMessage
from droidrun.agent.executor import ExecutorAgent
from droidrun.agent.external import load_agent
from droidrun.agent.manager import ManagerAgent, StatelessManagerAgent
from droidrun.agent.oneflows.structured_output_agent import StructuredOutputAgent
from droidrun.agent.trajectory import TrajectoryWriter
from droidrun.agent.utils.llm_loader import (
    load_agent_llms,
    merge_llms_with_config,
)
from droidrun.agent.utils.prompt_resolver import PromptResolver
from droidrun.agent.utils.signatures import build_tool_registry
from droidrun.agent.utils.tracing_setup import (
    apply_session_context,
    record_langfuse_screenshot,
    setup_tracing,
)
from droidrun.agent.utils.trajectory import Trajectory
from droidrun.config_manager.config_manager import (
    AgentConfig,
    CredentialsConfig,
    DeviceConfig,
    DroidConfig,
    LoggingConfig,
    TelemetryConfig,
    ToolsConfig,
    TracingConfig,
)
from droidrun.credential_manager import CredentialManager, FileCredentialManager
from droidrun.log_handlers import CLILogHandler, configure_logging
from droidrun.mcp.adapter import mcp_to_droidrun_tools
from droidrun.mcp.client import MCPClientManager
from droidrun.mcp.config import MCPConfig
from droidrun.telemetry import (
    DroidAgentFinalizeEvent,
    DroidAgentInitEvent,
    capture,
    flush,
)
from droidrun.tools.driver.base import DeviceDisconnectedError
from droidrun.tools.driver.factory import create_driver_from_device_config
from droidrun.tools.driver.recording import RecordingDriver
from droidrun.tools.driver.stealth import StealthDriver
from droidrun.tools.filters import ConciseFilter, DetailedFilter
from droidrun.tools.formatters import IndexedFormatter
from droidrun.tools.ui.ios_provider import IOSStateProvider
from droidrun.tools.ui.provider import AndroidStateProvider

if TYPE_CHECKING:
    from droidrun.tools.driver.base import DeviceDriver
    from droidrun.tools.ui.provider import StateProvider

logger = logging.getLogger("droidrun")
# 业务: `logger` 是本模块使用的日志记录器（用于输出运行信息、警告和错误），便于运维和调试。
# 语法: 这一行调用 `logging.getLogger` 返回一个 Logger 对象。后续代码使用 `logger.info/debug/warning/error` 方法记录不同级别的日志。


# 教程注释：DroidAgent 是整个框架的总协调器，决定用哪种模式执行任务，并把工具、状态、驱动都串起来。
class DroidAgent(Workflow):
    """
    A wrapper class that coordinates between agents to achieve a user's goal.

    Reasoning modes:
    - reasoning=False: Uses FastAgent directly for immediate execution
    - reasoning=True: Uses ManagerAgent (planning) + ExecutorAgent (actions)
    """

    @staticmethod
    def _configure_default_logging(debug: bool = False):
        """
        Configure default logging for DroidAgent if no real handler is present.
        """
        has_real_handler = any(
            not isinstance(h, logging.NullHandler) for h in logger.handlers
        )
        if not has_real_handler:
            handler = CLILogHandler()
            handler.setFormatter(
                logging.Formatter("%(asctime)s %(levelname)s: %(message)s", "%H:%M:%S")
                if debug
                else logging.Formatter("%(message)s")
            )
            configure_logging(debug=debug, handler=handler)

    # 教程注释：构造阶段会装配配置、LLM、共享状态、子 Agent 和工具上下文，是总协调器的初始化中心。
    def __init__(
        self,
        goal: str,
        config: DroidConfig | None = None,
        llms: dict[str, LLM] | LLM | None = None,
        custom_tools: dict = None,
        credentials: Union[dict, "CredentialManager", None] = None,
        variables: dict | None = None,
        output_model: Type[BaseModel] | None = None,
        prompts: dict[str, str] | None = None,
        driver: "DeviceDriver | None" = None,
        state_provider: "StateProvider | None" = None,
        timeout: int = 1000,
        *args,
        **kwargs,
    ):
        # 业务: 存储调用者提供的用户标识，便于遥测/事件关联（例如多用户运行时区分）。
        # 语法: `kwargs.pop` 从可变关键字参数 `kwargs` 中取出 `user_id` 并从字典中移除；如果不存在则返回 `None`。
        self.user_id = kwargs.pop("user_id", None)
        self.runtype = kwargs.pop("runtype", "developer")
        self.shared_state = DroidAgentState(
            instruction=goal,
            err_to_manager_thresh=2,
            user_id=self.user_id,
            runtype=self.runtype,
        )
        # 业务: `shared_state` 持有 Agent 的运行时共享状态（指令、历史、错误计数等），在整个工作流中传递和更新。
        # 语法: 这里通过调用 `DroidAgentState(...)` 实例化一个对象，并将其赋值给 `self.shared_state`，以便类的其他方法访问。
        self.output_model = output_model

        # Initialize prompt resolver for custom prompts
        # 业务: 解析并管理用户自定义的 Prompt 模板，允许在运行时替换变量并加载自定义提示词。
        # 语法: 通过调用 `PromptResolver(...)` 创建对象并赋值给实例属性 `self.prompt_resolver`。
        self.prompt_resolver = PromptResolver(custom_prompts=prompts)

        # Store custom variables in shared state
        if variables:
            self.shared_state.custom_variables = variables

        # Load credential manager (supports both config and direct dict)
        credentials_source = (
            credentials
            if credentials is not None
            else (config.credentials if config else None)
        )

        if isinstance(credentials_source, CredentialManager):
            self.credential_manager = credentials_source
        elif credentials_source is not None:
            cm = FileCredentialManager(credentials_source)
            self.credential_manager = cm if cm.secrets else None
        else:
            self.credential_manager = None

        # 业务: 解析设备配置（如串口、平台等），用于后续连接真实设备或模拟器。
        # 语法: 这是一个条件表达式（ternary），如果 `config` 为真则取 `config.device`，否则创建默认 `DeviceConfig()`。
        self.resolved_device_config = config.device if config else DeviceConfig()

        self.config = DroidConfig(
            agent=config.agent if config else AgentConfig(),
            device=self.resolved_device_config,
            tools=config.tools if config else ToolsConfig(),
            logging=config.logging if config else LoggingConfig(),
            tracing=config.tracing if config else TracingConfig(),
            telemetry=config.telemetry if config else TelemetryConfig(),
            llm_profiles=config.llm_profiles if config else {},
            credentials=config.credentials if config else CredentialsConfig(),
            external_agents=config.external_agents if config else {},
            mcp=config.mcp if config else MCPConfig(),
        )

        # These are populated in start_handler (unless injected via __init__)
        self._injected_driver = driver
        self._injected_state_provider = state_provider
        self.driver = None
        self.registry = None
        self.action_ctx = None
        self.state_provider = None

        # 语法: 调用父类 `Workflow` 的构造函数，传入可变参数和超时配置，初始化工作流框架。
        super().__init__(*args, timeout=timeout, **kwargs)

        self._configure_default_logging(debug=self.config.logging.debug)

        # 业务: 根据配置初始化追踪（例如 Phoenix 或 Langfuse），用于收集 LLM 调用和执行路径。
        # 语法: 调用模块级函数 `setup_tracing`，传入追踪配置对象和当前 Agent（self）。
        setup_tracing(self.config.tracing, agent=self)

        # Check if using external agent - skip LLM loading
        self._using_external_agent = self.config.agent.name != "droidrun"

        self._stream_screenshots = os.environ.get(
            "DROIDRUN_STREAM_SCREENSHOTS", ""
        ).lower() in ("1", "true")

        self.timeout = timeout

        # Store user custom tools
        self.user_custom_tools = custom_tools or {}

        # Initialize MCP manager (connections made lazily in start_handler)
        self.mcp_manager = None

        # Only load LLMs for native Droidrun agents
        if not self._using_external_agent:
            if llms is None:
                if config is None:
                    raise ValueError(
                        "Either 'llms' or 'config' must be provided. "
                        "If llms is not provided, config is required to load LLMs from profiles."
                    )

                logger.debug("🔄 Loading LLMs from config (llms not provided)...")

                llms = load_agent_llms(
                    config=self.config, output_model=output_model, **kwargs
                )
            if isinstance(llms, dict):
                llms = merge_llms_with_config(
                    self.config, llms, output_model=output_model, **kwargs
                )
            elif isinstance(llms, LLM):
                pass
            else:
                raise ValueError(f"Invalid LLM type: {type(llms)}")

            if isinstance(llms, dict):
                self.manager_llm = llms.get("manager")
                self.executor_llm = llms.get("executor")
                self.fast_agent_llm = llms.get("fast_agent")
                self.app_opener_llm = llms.get("app_opener")
                self.structured_output_llm = llms.get(
                    "structured_output", self.fast_agent_llm
                )
            else:
                self.manager_llm = llms
                self.executor_llm = llms
                self.fast_agent_llm = llms
                self.app_opener_llm = llms
                self.structured_output_llm = llms
        else:
            logger.debug(f"🔄 Using external agent: {self.config.agent.name}")
            self.manager_llm = None
            self.executor_llm = None
            self.fast_agent_llm = None
            self.app_opener_llm = None
            self.structured_output_llm = None

        if (
            not self._using_external_agent
            and self.config.logging.save_trajectory != "none"
        ):
            self.trajectory = Trajectory(
                goal=self.shared_state.instruction,
                base_path=self.config.logging.trajectory_path,
            )
            self.trajectory_writer = TrajectoryWriter(queue_size=300)
            self.shared_state.output_dir = str(self.trajectory.trajectory_folder)
        else:
            self.trajectory = None
            self.trajectory_writer = None
            self.shared_state.output_dir = ""
        # 业务: 如果启用了轨迹记录（trajectory），创建轨迹对象与异步写入器，用于保存截图和 UI 状态。
        # 语法: `Trajectory(...)` 是类实例化；`TrajectoryWriter(queue_size=300)` 创建负责异步写文件的帮助对象。

        # Sub-agents are created in __init__ but wired up in start_handler
        # 以下代码负责根据配置创建 Manager/Executor/FastAgent 等子 Agent 实例（但会在 start_handler 中完成工具注入）。
        if self._using_external_agent:
            self.manager_agent = None
            self.executor_agent = None
        elif self.config.agent.reasoning:
            if self.config.agent.manager.stateless:
                # 教程注释：开启 stateless 后，顶层会改用“每轮重建上下文”的规划器，适合控制历史体积或做更强可重复规划。
                ManagerClass = StatelessManagerAgent
            else:
                # 教程注释：默认使用有状态 ManagerAgent，它会持续积累 message_history 进行多轮规划。
                ManagerClass = ManagerAgent

            # Pass None for tools-related params — wired up in start_handler
            self.manager_agent = ManagerClass(
                llm=self.manager_llm,
                action_ctx=None,
                state_provider=None,
                save_trajectory=self.config.logging.save_trajectory,
                shared_state=self.shared_state,
                agent_config=self.config.agent,
                registry=None,
                output_model=self.output_model,
                prompt_resolver=self.prompt_resolver,
                tracing_config=self.config.tracing,
                timeout=self.timeout,
            )
            self.executor_agent = ExecutorAgent(
                llm=self.executor_llm,
                registry=None,
                action_ctx=None,
                shared_state=self.shared_state,
                agent_config=self.config.agent,
                prompt_resolver=self.prompt_resolver,
                timeout=self.timeout,
            )
        else:
            self.manager_agent = None
            self.executor_agent = None
        # 业务: 到这里完成了 Agent 的基本组装（LLM、shared_state、子 Agent 实例），但未绑定驱动或工具注册表。
        # 语法: `self.manager_agent` 和 `self.executor_agent` 是对象引用，可在方法间共享。

        # Telemetry init event is fired in start_handler after registry is built.
        self._init_prompts = prompts  # stash for telemetry
        self._init_timeout = timeout

        logger.debug("✅ DroidAgent initialized successfully.")

    # 教程注释：run 只是工作流启动入口，真正复杂的资源准备和分支决策在后面的 start_handler 里完成。
    def run(self, *args, **kwargs) -> Awaitable[ResultEvent] | WorkflowHandler:
        # 业务: 运行工作流前先把追踪/遥测会话上下文应用到当前执行上下文（可见于 tracing/backends）。
        # 语法: `apply_session_context()` 是函数调用；`super().run(...)` 调用父类实现并返回一个 handler（可用于事件流处理）。
        apply_session_context()
        handler = super().run(*args, **kwargs)  # type: ignore[assignment]
        return handler

    # ========================================================================
    # start_handler — creates driver, registry, action_ctx
    # ========================================================================

    @step
    async def start_handler(
        self, ctx: Context, ev: StartEvent
    ) -> FastAgentExecuteEvent | ManagerInputEvent:
        # 业务: `start_handler` 是工作流的入口，负责建立设备驱动、状态提供器、工具注册表，并选择执行模式（直连或推理）。
        # 语法: 使用 `@step` 装饰器表示这是工作流的一个步骤，参数为上下文 `ctx` 和事件 `ev`，并会返回事件用于下一步分支。
        logger.info(
            f"🚀 Running DroidAgent to achieve goal: {self.shared_state.instruction}"
        )
        ctx.write_event_to_stream(ev)

        if self.trajectory_writer:
            await self.trajectory_writer.start()

        # ── 0. External agent — early exit ────────────────────────────
        # 业务: 如果配置为使用外部 agent（非内置 droidrun），早期加载外部模块并委托执行，随后直接返回 FinalizeEvent。
        if self._using_external_agent:
            agent_name = self.config.agent.name

            # Load the agent module
            agent_module = load_agent(agent_name)
            if not agent_module:
                from droidrun.agent.external import list_agents

                available = list_agents()
                if available:
                    agents_str = ", ".join(available)
                    raise ValueError(
                        f"Failed to load external agent '{agent_name}'.\n"
                        f"Available agents: {agents_str}"
                    )
                raise ValueError(
                    f"External agent '{agent_name}' not found.\n"
                    "No external agents are currently installed.\n"
                    "Run: droidrun run --help  to see available agents."
                )

            # Resolve config — missing section is fine, agent may use DEFAULT_CONFIG or env vars
            agent_config = self.config.external_agents.get(agent_name) or {}
            final_config = {**agent_module["config"], **agent_config}

            # 业务: 解析设备序列号并获取原始 ADB 设备对象以传递给外部 agent。
            # 语法: `await adb.list()` 是异步调用，返回设备列表；`adb.device(serial=...)` 获取特定设备。
            device_serial = self.resolved_device_config.serial
            if device_serial is None:
                devices = await adb.list()
                if not devices:
                    raise ValueError("No connected Android devices found.")
                device_serial = devices[0].serial

            adb_device = await adb.device(serial=device_serial)

            logger.info(f"🤖 Using external agent: {agent_name}")

            result = await agent_module["run"](
                device=adb_device,
                instruction=self.shared_state.instruction,
                config=final_config,
                max_steps=self.config.agent.max_steps,
            )

            return FinalizeEvent(success=result["success"], reason=result["reason"])

        # ── 1. Create driver ──────────────────────────────────────────
        # 业务: 根据配置决定视觉（截图）是否启用 —— 推理模式由 manager 控制，直连模式由 fast_agent 控制。
        if self.config.agent.reasoning:
            vision_enabled = self.config.agent.manager.vision
        else:
            vision_enabled = self.config.agent.fast_agent.vision

        # 语法/业务: 支持注入 `driver`（用于测试），否则根据平台实例化对应驱动（iOS/Android）。
        if self._injected_driver is not None:
            driver = self._injected_driver
        else:
            driver, _ = await create_driver_from_device_config(
                self.resolved_device_config,
                debug=self.config.logging.debug,
            )

        is_ios = driver.platform.lower() == "ios"

        # Wrap with StealthDriver if stealth mode enabled
        # 业务: 当启用 stealth 功能时，使用 `StealthDriver` 包装底层驱动以隐藏自动化痕迹。
        stealth_enabled = self.config.tools and self.config.tools.stealth
        if stealth_enabled and not is_ios:
            driver = StealthDriver(driver)

        # Wrap with RecordingDriver if trajectory saving enabled
        # 业务: 如果启用了轨迹持久化，使用 `RecordingDriver` 包装驱动以记录日志和截图供后续保存。
        if self.config.logging.save_trajectory != "none":
            if not isinstance(driver, RecordingDriver):
                driver = RecordingDriver(driver)

        # 语法: 将本地 `driver` 引用保存到 `self.driver`，并把平台信息记录到共享状态。
        self.driver = driver
        self.shared_state.platform = driver.platform

        # ── 2. Create state provider ──────────────────────────────────
        # 业务: 创建 `state_provider`，用于在每步读取设备的 UI 树（元素层级），并可能进行格式化/过滤以降低噪音。
        if self._injected_state_provider is not None:
            self.state_provider = self._injected_state_provider
        elif is_ios:
            self.state_provider = IOSStateProvider(
                driver,
                use_normalized=self.config.agent.use_normalized_coordinates,
            )
        else:
            tree_filter = ConciseFilter() if vision_enabled else DetailedFilter()
            tree_formatter = IndexedFormatter()
            self.state_provider = AndroidStateProvider(
                driver,
                tree_filter=tree_filter,
                tree_formatter=tree_formatter,
                use_normalized=self.config.agent.use_normalized_coordinates,
                stealth=stealth_enabled,
            )

        # ── 3. Build tool registry ────────────────────────────────────
        # 业务: 根据驱动能力和平台构建工具注册表（可用的点击、滑动、键入等工具都会在这里被注册）。
        registry, standard_tool_names = await build_tool_registry(
            supported_buttons=driver.supported_buttons,
            credential_manager=self.credential_manager,
            platform="ios" if is_ios else "android",
        )

        # User custom tools
        # 语法: 如果用户提供了自定义工具字典，注册到现有工具注册表中。
        if self.user_custom_tools:
            registry.register_from_dict(self.user_custom_tools)

        # MCP tools
        # 业务: 如果启用了 MCP（远程工具），创建 MCP 客户端并发现远程工具，然后将其转换并注册到工具表。
        if self.config.mcp and self.config.mcp.enabled:
            self.mcp_manager = MCPClientManager(self.config.mcp)
            await self.mcp_manager.discover_tools()
            mcp_tools = mcp_to_droidrun_tools(self.mcp_manager)
            if mcp_tools:
                registry.register_from_dict(mcp_tools)

        # Capability-based filtering (deps vs driver+provider supported)
        # 业务: 根据驱动和状态提供者支持的能力过滤不支持的工具，避免运行时调用失败。
        capabilities = driver.supported | self.state_provider.supported
        registry.disable_unsupported(capabilities)

        # Config-level filtering
        disabled_tools = (
            self.config.tools.disabled_tools
            if self.config.tools and self.config.tools.disabled_tools
            else []
        )
        if disabled_tools:
            registry.disable(disabled_tools)

        self.registry = registry
        self.standard_tool_names = standard_tool_names

        # ── 4. Create ActionContext ────────────────────────────────────
        # 业务: `ActionContext` 聚合驱动、共享状态、状态提供者等，用作执行动作时的上下文。
        # 语法: 通过关键字参数实例化 `ActionContext` 并保存到 `self.action_ctx`。
        self.action_ctx = ActionContext(
            driver=driver,
            ui=None,  # populated each step by state_provider
            shared_state=self.shared_state,
            state_provider=self.state_provider,
            app_opener_llm=self.app_opener_llm,
            credential_manager=self.credential_manager,
            streaming=self.config.agent.streaming,
        )

        # ── 5. Wire up sub-agents ─────────────────────────────────────
        # 业务: 将 `manager_agent` 和 `executor_agent` 绑定到运行时上下文（registry、action_ctx、state_provider 等）。
        if self.config.agent.reasoning and self.executor_agent:
            self.manager_agent.action_ctx = self.action_ctx
            self.manager_agent.state_provider = self.state_provider
            self.manager_agent.registry = self.registry
            self.manager_agent.save_trajectory = self.config.logging.save_trajectory
            self.manager_agent.standard_tool_names = self.standard_tool_names
            self.executor_agent.registry = self.registry
            self.executor_agent.action_ctx = self.action_ctx

        # ── 6. Fetch device date once ─────────────────────────────────
        # 语法: 异步调用设备驱动获取设备时间并记录到共享状态（可能用于日志/时间戳）。
        self.shared_state.device_date = await driver.get_date()

        # ── 7. Telemetry init event ───────────────────────────────────
        # 业务: 触发一次初始化的遥测事件（DroidAgentInitEvent），上报当前配置和所选 LLM，用于监控/统计。
        capture(
            DroidAgentInitEvent(
                goal=self.shared_state.instruction,
                llms={
                    "manager": (
                        self.manager_llm.class_name() if self.manager_llm else "None"
                    ),
                    "executor": (
                        self.executor_llm.class_name() if self.executor_llm else "None"
                    ),
                    "fast_agent": (
                        self.fast_agent_llm.class_name()
                        if self.fast_agent_llm
                        else "None"
                    ),
                    "app_opener": (
                        self.app_opener_llm.class_name()
                        if self.app_opener_llm
                        else "None"
                    ),
                },
                tools=",".join(sorted(standard_tool_names)),
                max_steps=self.config.agent.max_steps,
                timeout=self._init_timeout,
                vision={
                    "manager": self.config.agent.manager.vision,
                    "executor": self.config.agent.executor.vision,
                    "fast_agent": self.config.agent.fast_agent.vision,
                },
                reasoning=self.config.agent.reasoning,
                enable_tracing=self.config.tracing.enabled,
                debug=self.config.logging.debug,
                save_trajectories=self.config.logging.save_trajectory,
                runtype=self.runtype,
                custom_prompts=self._init_prompts,
            ),
            self.user_id,
        )

        if self.config.logging.save_trajectory != "none":
            self.trajectory_writer.write(self.trajectory, stage="init")

        # 业务: 根据 `agent.reasoning` 配置决定运行模式：
        # - 直连模式（reasoning=False）：直接触发 `FastAgentExecuteEvent` 进入 `execute_task` 步骤
        # - 推理模式（reasoning=True）：触发 `ManagerInputEvent` 进入 Manager/Executor 工作流
        if not self.config.agent.reasoning:
            logger.debug(
                f"🔄 Direct execution mode - executing goal: {self.shared_state.instruction}"
            )
            event = FastAgentExecuteEvent(instruction=self.shared_state.instruction)
            ctx.write_event_to_stream(event)
            return event

        logger.debug("🧠 Reasoning mode - initializing Manager/Executor workflow")
        event = ManagerInputEvent()
        ctx.write_event_to_stream(event)
        return event

    # ========================================================================
    # External user message injection
    # ========================================================================

    # 教程注释：这个公开方法允许调用方在任务运行中追加新指令，实际只入队，不会立刻打断当前 step。
    def send_user_message(self, message: str) -> QueuedUserMessage:
        queued = self.shared_state.queue_user_message(message)
        logger.info(
            f"📩 External user message queued [id={queued.id}] "
            f"(queue length: {len(self.shared_state.pending_user_messages)})",
            extra={"color": "cyan"},
        )
        return queued

    # ========================================================================
    # execute_task — FastAgent
    # ========================================================================

    @step
    async def execute_task(
        self, ctx: Context, ev: FastAgentExecuteEvent
    ) -> FastAgentResultEvent:
        """Execute a single task using FastAgent."""

        # 业务: 该步骤在“直连模式”下执行真实任务，把当前指令交给 `FastAgent`，并将过程事件转发到外层流。
        # 语法: `async def` 定义异步函数；返回类型注解 `-> FastAgentResultEvent` 仅用于类型提示，不改变运行行为。
        logger.debug(f"🔧 Executing task: {ev.instruction}")

        try:
            # 业务: 构造 FastAgent，并注入执行所需资源（LLM、工具、状态、配置）。
            # 语法: 通过关键字参数实例化类，得到对象 `agent`。
            agent = FastAgent(
                llm=self.fast_agent_llm,
                agent_config=self.config.agent,
                registry=self.registry,
                action_ctx=self.action_ctx,
                state_provider=self.state_provider,
                save_trajectory=self.config.logging.save_trajectory,
                debug=self.config.logging.debug,
                shared_state=self.shared_state,
                output_model=self.output_model,
                prompt_resolver=self.prompt_resolver,
                timeout=self.timeout,
                tracing_config=self.config.tracing,
            )

            # 业务: 启动 FastAgent 的内部工作流；`remembered_info` 把历史记忆传给本轮执行。
            # 语法: `agent.run(...)` 返回一个 handler（可迭代事件、可 await 得到最终结果）。
            handler = agent.run(
                input=ev.instruction,
                remembered_info=self.shared_state.fast_memory,
            )

            # 业务: 持续消费并转发子工作流事件，确保外部（CLI/TUI/日志）能看到实时进度。
            # 语法: `async for` 用于异步迭代器；每次循环拿到一个 `nested_ev`。
            async for nested_ev in handler.stream_events():
                self.handle_stream_event(nested_ev, ctx)

                if isinstance(nested_ev, FastAgentOutputEvent):
                    if self.config.logging.save_trajectory != "none":
                        self.trajectory_writer.write(
                            self.trajectory,
                            stage=f"fast_agent_step_{self.shared_state.step_number}",
                        )

            # 语法: `await handler` 等待异步任务完成，并取得最终结果字典。
            result = await handler

            # 业务: 将子 Agent 的结果统一封装为 `FastAgentResultEvent` 交给下一步处理。
            return FastAgentResultEvent(
                success=result.get("success", False),
                reason=result["reason"],
                instruction=ev.instruction,
            )

        except DeviceDisconnectedError as e:
            # 业务: 设备断开属于可预期故障，转为失败事件返回，而不是让流程崩溃。
            # 语法: `except Xxx as e` 捕获指定异常，并把异常对象绑定到变量 `e`。
            logger.error(f"Device disconnected: {e}")
            return FastAgentResultEvent(
                success=False,
                reason=f"Device disconnected: {e}",
                instruction=ev.instruction,
            )

        except Exception as e:
            # 业务: 兜底异常处理，避免单次错误中断整个外层工作流。
            logger.error(f"Error during task execution: {e}")
            if self.config.logging.debug:
                logger.error(traceback.format_exc())
            return FastAgentResultEvent(
                success=False, reason=f"Error: {str(e)}", instruction=ev.instruction
            )

    @step
    async def handle_fast_agent_result(
        self, ctx: Context, ev: FastAgentResultEvent
    ) -> FinalizeEvent:
        try:
            # 业务: 将 FastAgent 的最终结果直接映射成流程终止事件 `FinalizeEvent`。
            # 语法: 这里 `ctx` 未直接使用，但保留参数是为了匹配工作流 step 的签名规范。
            return FinalizeEvent(success=ev.success, reason=ev.reason)

        except Exception as e:
            logger.error(f"❌ Error during DroidAgent execution: {e}")
            if self.config.logging.debug:
                logger.error(traceback.format_exc())
            return FinalizeEvent(
                success=False,
                reason=str(e),
            )

    # ========================================================================
    # Manager/Executor Workflow Steps
    # ========================================================================

    @step
    async def run_manager(
        self, ctx: Context, ev: ManagerInputEvent
    ) -> ManagerPlanEvent | FinalizeEvent:
        """Run Manager planning phase."""
        # 业务: `run_manager` 负责“规划”环节：生成当前子目标、计划和思考。
        # 语法: 返回联合类型 `A | B` 表示这个函数可能返回两种事件之一。
        if self.shared_state.step_number >= self.config.agent.max_steps:
            # 教程注释：如果 planning 已触顶，尚未消费的外部消息会显式标记为 dropped，而不是悄悄消失。
            logger.warning(f"⚠️ Reached maximum steps ({self.config.agent.max_steps})")
            pending = self.shared_state.drain_user_messages()
            if pending:
                logger.warning(
                    f"⚠️ Dropping {len(pending)} external user message(s) at max steps"
                )
                ctx.write_event_to_stream(
                    ExternalUserMessageDroppedEvent(
                        message_ids=[m.id for m in pending],
                        reason="max_steps_reached",
                        step_number=self.shared_state.step_number,
                    )
                )
            return FinalizeEvent(
                success=False,
                reason=f"Reached maximum steps ({self.config.agent.max_steps})",
            )

        self.shared_state.step_number += 1
        logger.info(
            f"🔄 Step {self.shared_state.step_number}/{self.config.agent.max_steps}"
        )

        try:
            # 业务: 运行 Manager 子工作流，拿到规划结果。
            handler = self.manager_agent.run()

            # 语法: 异步流式读取 Manager 内部事件并转发。
            async for nested_ev in handler.stream_events():
                self.handle_stream_event(nested_ev, ctx)

            result = await handler
        except DeviceDisconnectedError as e:
            logger.error(f"Device disconnected: {e}")
            return FinalizeEvent(success=False, reason=f"Device disconnected: {e}")

        event = ManagerPlanEvent(
            plan=result["plan"],
            current_subgoal=result["current_subgoal"],
            thought=result["thought"],
            answer=result.get("answer", ""),
            success=result.get("success"),
        )
        # 业务: 将 Manager 的结构化输出包成 `ManagerPlanEvent`，推动后续分支决策。
        ctx.write_event_to_stream(event)
        return event

    @step
    async def handle_manager_plan(
        self, ctx: Context, ev: ManagerPlanEvent
    ) -> ExecutorInputEvent | FinalizeEvent | ManagerInputEvent:
        """Process Manager output and decide next step."""
        # 业务: 这是关键路由器：决定“结束流程”还是“进入 Executor 执行动作”或“回到 Manager 重规划”。
        # Check for answer-type termination
        if ev.answer.strip():
            # 教程注释：若 Manager 想结束但队列里还有外部消息，顶层会强制回到 Manager 再规划一次，优先消费新指令。
            if self.shared_state.pending_user_messages:
                logger.info(
                    "⏸️ Manager tried to finish but external messages pending, "
                    "looping back to Manager",
                    extra={"color": "cyan"},
                )
                return ManagerInputEvent()
            success = ev.success if ev.success is not None else True
            self.shared_state.progress_summary = f"Answer: {ev.answer}"
            return FinalizeEvent(success=success, reason=ev.answer)

        logger.debug(f"▶️  Proceeding to Executor with subgoal: {ev.current_subgoal}")
        # 语法: 通过构造并返回 `ExecutorInputEvent`，把 `current_subgoal` 作为下游输入传递。
        return ExecutorInputEvent(current_subgoal=ev.current_subgoal)

    @step
    async def run_executor(
        self, ctx: Context, ev: ExecutorInputEvent
    ) -> ExecutorResultEvent:
        """Run Executor action phase."""
        # 业务: `run_executor` 负责“执行”环节：真正调用工具执行子目标。
        logger.debug("⚡ Running Executor for action...")

        handler = self.executor_agent.run(subgoal=ev.current_subgoal)

        async for nested_ev in handler.stream_events():
            self.handle_stream_event(nested_ev, ctx)

        result = await handler

        # Update coordination state after execution
        # 业务: 把执行结果写入共享状态历史，供下一轮 Manager 规划和错误恢复使用。
        # 语法: `list.append(...)` 向列表尾部追加元素，保持时间顺序。
        self.shared_state.action_history.append(result["action"])
        self.shared_state.summary_history.append(result["summary"])
        self.shared_state.action_outcomes.append(result["outcome"])
        self.shared_state.error_descriptions.append(result["error"])
        self.shared_state.last_action = result["action"]
        self.shared_state.last_summary = result["summary"]

        return ExecutorResultEvent(
            action=result["action"],
            outcome=result["outcome"],
            error=result["error"],
            summary=result["summary"],
        )

    @step
    async def handle_executor_result(
        self, ctx: Context, ev: ExecutorResultEvent
    ) -> ManagerInputEvent:
        """Process Executor result and continue."""
        # 业务: 根据最近执行结果判断是否触发错误升级，并决定返回 Manager 进入下一轮规划。
        err_thresh = self.shared_state.err_to_manager_thresh

        if len(self.shared_state.action_outcomes) >= err_thresh:
            latest = self.shared_state.action_outcomes[-err_thresh:]
            error_count = sum(1 for o in latest if not o)
            if error_count == err_thresh:
                logger.warning(f"⚠️ Error escalation: {err_thresh} consecutive errors")
                self.shared_state.error_flag_plan = True
            else:
                if self.shared_state.error_flag_plan:
                    logger.debug("✅ Error resolved - resetting error flag")
                self.shared_state.error_flag_plan = False

        if self.config.logging.save_trajectory != "none":
            # 业务: 每完成一轮 Executor 都写一次轨迹快照，便于回放。
            self.trajectory_writer.write(
                self.trajectory, stage=f"step_{self.shared_state.step_number}"
            )

        # 语法: 返回 `ManagerInputEvent()` 让工作流回到 `run_manager`，形成循环（计划->执行->计划...）。
        return ManagerInputEvent()

    # ========================================================================
    # Finalize
    # ========================================================================

    @step
    async def finalize(self, ctx: Context, ev: FinalizeEvent) -> ResultEvent:
        # 业务: `finalize` 是收尾步骤，负责落库/上报/截图/轨迹写盘以及资源清理。
        self.shared_state.workflow_completed = True
        ctx.write_event_to_stream(ev)
        capture(
            DroidAgentFinalizeEvent(
                success=ev.success,
                reason=ev.reason,
                steps=self.shared_state.step_number,
                unique_packages_count=len(self.shared_state.visited_packages),
                unique_activities_count=len(self.shared_state.visited_activities),
            ),
            self.user_id,
        )
        await flush()

        # Base result with answer
        # 语法: 先构建一个基础结果对象，后续可再补充结构化输出字段。
        result = ResultEvent(
            success=ev.success,
            reason=ev.reason,
            steps=self.shared_state.step_number,
            structured_output=None,
        )

        # Extract structured output if model was provided
        if self.output_model is not None and ev.reason:
            logger.debug("🔄 Running structured output extraction...")

            try:
                # 教程注释：主 Agent 在最终收尾阶段再触发 StructuredOutputAgent，避免中途步骤被 schema 约束干扰。
                structured_agent = StructuredOutputAgent(
                    llm=self.structured_output_llm,
                    pydantic_model=self.output_model,
                    answer_text=ev.reason,
                    timeout=self.timeout,
                )

                # 教程注释：这里沿用嵌套 workflow 的事件流转发，保证 CLI/TUI 仍能看到内部提取过程。
                handler = structured_agent.run()

                async for nested_ev in handler.stream_events():
                    self.handle_stream_event(nested_ev, ctx)

                extraction_result = await handler

                if extraction_result["success"]:
                    # 业务: 抽取成功时，把结构化对象挂到最终返回结果上。
                    result.structured_output = extraction_result["structured_output"]
                    logger.debug("✅ Structured output added to final result")
                else:
                    logger.warning(
                        f"⚠️  Structured extraction failed: {extraction_result['error_message']}"
                    )

            except Exception as e:
                logger.error(f"❌ Error during structured extraction: {e}")
                if self.config.logging.debug:
                    logger.error(traceback.format_exc())

        # Capture final screenshot and UI state (independent of trajectory persistence)
        vision_any = (
            self.config.agent.manager.vision
            or self.config.agent.executor.vision
            or self.config.agent.fast_agent.vision
        )
        if (
            vision_any
            or self._stream_screenshots
            or self.config.logging.save_trajectory != "none"
        ):
            try:
                # 业务: 收尾阶段补采一张最终截图并发到事件流/追踪系统，帮助定位最终界面状态。
                screenshot = await self.action_ctx.driver.screenshot()
                if screenshot:
                    ctx.write_event_to_stream(ScreenshotEvent(screenshot=screenshot))
                    parent_span = trace.get_current_span()
                    record_langfuse_screenshot(
                        screenshot,
                        parent_span=parent_span,
                        screenshots_enabled=self.config.tracing.langfuse_screenshots,
                        vision_enabled=vision_any,
                    )
                    logger.debug("📸 Final screenshot captured")
            except Exception as e:
                logger.warning(f"Failed to capture final screenshot: {e}")

            try:
                # 业务: 同时采集最终 UI 树，便于离线分析“最后停在哪个页面”。
                ui_state = await self.state_provider.get_state()
                ctx.write_event_to_stream(
                    RecordUIStateEvent(ui_state=ui_state.elements)
                )
                logger.debug("📋 Final UI state captured")
            except Exception as e:
                logger.warning(f"Failed to capture final UI state: {e}")

        # Save trajectory to disk
        if self.config.logging.save_trajectory != "none":
            # Populate macro data from RecordingDriver log
            if isinstance(self.driver, RecordingDriver):
                self.trajectory.macro = list(self.driver.log)

            self.trajectory_writer.write_final(
                self.trajectory, self.config.logging.trajectory_gifs
            )
            await self.trajectory_writer.stop()
            logger.info(f"📁 Trajectory saved: {self.trajectory.trajectory_folder}")

        # Cleanup MCP connections
        if self.mcp_manager:
            try:
                # 业务: 关闭 MCP 连接，避免连接泄漏和后台资源占用。
                await self.mcp_manager.disconnect_all()
            except Exception as e:
                logger.warning(f"MCP cleanup error: {e}")

        return result

    # ========================================================================
    # Event streaming
    # ========================================================================

    def handle_stream_event(self, ev: Event, ctx: Context):
        # 业务: 统一事件转发口，把子流程事件上抛到外层，同时把关键事件写进轨迹缓存。
        # 语法: `isinstance(ev, StopEvent)` 用于类型判断；`if not ...` 表示过滤掉 StopEvent。
        if not isinstance(ev, StopEvent):
            ctx.write_event_to_stream(ev)

            if self.trajectory:
                if isinstance(ev, ScreenshotEvent):
                    self.trajectory.screenshot_queue.append(ev.screenshot)
                    self.trajectory.screenshot_count += 1
                elif isinstance(ev, RecordUIStateEvent):
                    self.trajectory.ui_states.append(ev.ui_state)
                else:
                    self.trajectory.events.append(ev)
