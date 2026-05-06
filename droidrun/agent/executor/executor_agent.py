"""
ExecutorAgent - Action execution workflow.

This agent is responsible for:
- Taking a specific subgoal from the Manager
- Analyzing the current UI state
- Selecting and executing appropriate actions
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from llama_index.core.base.llms.types import ChatMessage, ImageBlock, TextBlock
from llama_index.core.llms.llm import LLM
from llama_index.core.workflow import Context, StartEvent, StopEvent, Workflow, step
from PIL import Image, ImageDraw

from droidrun.agent.executor.events import (
    ExecutorActionEvent,
    ExecutorActionResultEvent,
    ExecutorContextEvent,
    ExecutorResponseEvent,
)
from droidrun.agent.executor.prompts import parse_executor_response
from droidrun.agent.usage import get_usage_from_response
from droidrun.agent.utils.inference import acall_with_retries
from droidrun.agent.utils.prompt_resolver import PromptResolver
from droidrun.tools.helpers.coordinate import (
    NORMALIZED_MAX,
    to_absolute,
    to_normalized,
)
from droidrun.config_manager.config_manager import AgentConfig
from droidrun.config_manager.prompt_loader import PromptLoader

if TYPE_CHECKING:
    from droidrun.agent.action_context import ActionContext
    from droidrun.agent.droid import DroidAgentState
    from droidrun.agent.tool_registry import ToolRegistry

logger = logging.getLogger("droidrun")


# 教程注释：ExecutorAgent 是“执行器”，接收一个明确子目标后，负责选择并执行一次最合适的动作。
class ExecutorAgent(Workflow):
    """
    Action execution agent that performs specific actions.

    Single-turn agent: receives subgoal, selects action, executes it.
    Uses ChatMessage objects directly for LLM calls.
    """

    # Flow-control tools hidden from executor's LLM prompt
    _EXCLUDE_TOOLS = {"remember", "complete"}

    def __init__(
        self,
        llm: LLM,
        registry: "ToolRegistry | None",
        action_ctx: "ActionContext | None",
        shared_state: "DroidAgentState",
        agent_config: AgentConfig,
        prompt_resolver: Optional[PromptResolver] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.llm = llm
        self.agent_config = agent_config
        self.config = agent_config.executor
        self.vision = agent_config.executor.vision
        self.registry = registry
        self.action_ctx = action_ctx
        self.shared_state = shared_state
        self.prompt_resolver = prompt_resolver or PromptResolver()

        logger.debug("ExecutorAgent initialized.")

    @staticmethod
    def _extract_json_object(text: str) -> dict:
        """Extract the first JSON object from free-form model output."""
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise ValueError("No JSON object found in grounding response")
        return json.loads(text[start : end + 1])

    @staticmethod
    def _subgoal_has_explicit_coordinates(subgoal: str) -> bool:
        """Return whether the subgoal already specifies literal coordinates."""
        if not subgoal:
            return False
        patterns = [
            r"\b\d{2,4}\s*,\s*\d{2,4}\b",
            r"\bx\s*[:=]\s*\d{2,4}.*\by\s*[:=]\s*\d{2,4}\b",
            r"\b坐标\b.*\d{2,4}.*\d{2,4}",
        ]
        return any(re.search(pattern, subgoal, re.IGNORECASE) for pattern in patterns)

    @staticmethod
    def _extract_required_targets(text: str) -> list[str]:
        """Extract explicit target texts from instruction/subgoal text."""
        if not text:
            return []

        matches = re.findall(r'[“"\']([^”"\']{1,20})[”"\']', text)
        targets: list[str] = []
        for match in matches:
            candidate = match.strip()
            if candidate and candidate not in targets:
                targets.append(candidate)
        return targets

    def _ui_contains_target(self, target: str) -> bool:
        """Return whether the current formatted device state exposes target text."""
        if not target:
            return False
        return target in (self.shared_state.formatted_device_state or "")

    def _click_index_matches_target(self, index: int, target: str) -> bool:
        """Check whether an index-based click is actually targeting the requested text."""
        if not self.action_ctx or not self.action_ctx.ui:
            return False
        info = self.action_ctx.ui.get_element_info(index)
        haystacks = [str(info.get("text", "") or "")]
        haystacks.extend(str(item) for item in info.get("child_texts", []) or [])
        return any(target in value for value in haystacks if value)

    def _iter_ui_elements(self) -> list[dict]:
        """Flatten the current UI tree for local target matching."""
        if not self.action_ctx or not self.action_ctx.ui:
            return []

        result: list[dict] = []

        def _walk(elements: list[dict]) -> None:
            for element in elements:
                result.append(element)
                children = element.get("children") or []
                if children:
                    _walk(children)

        _walk(self.action_ctx.ui.elements or [])
        return result

    def _find_target_index_in_ui(self, target: str) -> Optional[int]:
        """Return the best matching UI index for a target text, if present."""
        if not target:
            return None

        best_score = -1
        best_index: Optional[int] = None
        target_lower = target.lower()

        for element in self._iter_ui_elements():
            index = element.get("index")
            if not isinstance(index, int):
                continue

            candidates = []
            text = element.get("text")
            if text:
                candidates.append(str(text))
            for child in element.get("children") or []:
                child_text = child.get("text")
                if child_text:
                    candidates.append(str(child_text))

            score = -1
            for candidate in candidates:
                candidate_lower = candidate.lower()
                if candidate == target:
                    score = max(score, 4)
                elif candidate_lower == target_lower:
                    score = max(score, 3)
                elif target in candidate or candidate in target:
                    score = max(score, 2)
                elif target_lower in candidate_lower or candidate_lower in target_lower:
                    score = max(score, 1)

            if score > best_score:
                best_score = score
                best_index = index

        return best_index if best_score >= 0 else None

    def _save_grounding_annotation(
        self,
        screenshot: bytes,
        x: int,
        y: int,
        *,
        target_x: Optional[int] = None,
        target_y: Optional[int] = None,
    ) -> None:
        """Persist screenshot with target-analysis and click markers."""
        output_dir = (self.shared_state.output_dir or "").strip()
        if not output_dir:
            logger.debug("Skipping grounding annotation: no output_dir configured")
            return

        screenshots_dir = Path(output_dir) / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)

        screenshot_index = len(self.shared_state.action_history)
        screen_path = screenshots_dir / f"{screenshot_index:04d}.png"
        marked_path = screenshots_dir / f"{screenshot_index:04d}_marked.png"

        screen_path.write_bytes(screenshot)

        image = Image.open(BytesIO(screenshot)).convert("RGBA")
        draw = ImageDraw.Draw(image)
        radius = 20
        if target_x is not None and target_y is not None:
            draw.ellipse(
                (target_x - radius, target_y - radius, target_x + radius, target_y + radius),
                outline="lime",
                width=5,
            )
        draw.ellipse(
            (x - radius, y - radius, x + radius, y + radius),
            outline="red",
            width=5,
        )
        image.save(marked_path)
        logger.info(
            f"🖍️ Saved grounded screenshot annotation: {marked_path} (source: {screen_path}, target=green, click=red)"
        )

    def _save_index_click_annotation(self, index: int) -> None:
        """Save a marked screenshot for a successful index-based click action."""
        screenshot = self.shared_state.screenshot
        if screenshot is None or not self.action_ctx or not self.action_ctx.ui:
            return

        try:
            ui_x, ui_y = self.action_ctx.ui.get_element_coords(index)
            abs_x, abs_y = self.action_ctx.ui.convert_point(ui_x, ui_y)

            screenshot_width, screenshot_height = Image.open(BytesIO(screenshot)).size
            screen_width = getattr(self.action_ctx.ui, "screen_width", None)
            screen_height = getattr(self.action_ctx.ui, "screen_height", None)

            if (
                isinstance(screen_width, int)
                and isinstance(screen_height, int)
                and screen_width > 0
                and screen_height > 0
            ):
                norm_x, norm_y = to_normalized(abs_x, abs_y, screen_width, screen_height)
                mark_x, mark_y = to_absolute(
                    norm_x,
                    norm_y,
                    screenshot_width,
                    screenshot_height,
                )
            else:
                mark_x, mark_y = abs_x, abs_y

            self._save_grounding_annotation(screenshot, mark_x, mark_y)
        except Exception as e:
            logger.debug(f"Skipping index click annotation for index {index}: {e}")

    def _save_click_at_annotation(self, x: int, y: int) -> None:
        """Save a marked screenshot for a successful click_at action."""
        screenshot = self.shared_state.screenshot
        if screenshot is None or not self.action_ctx or not self.action_ctx.ui:
            return

        try:
            screenshot_width, screenshot_height = Image.open(BytesIO(screenshot)).size
            use_normalized = bool(getattr(self.action_ctx.ui, "use_normalized", False))

            if use_normalized:
                if 0 <= x <= NORMALIZED_MAX and 0 <= y <= NORMALIZED_MAX:
                    mark_x, mark_y = to_absolute(
                        x, y, screenshot_width, screenshot_height
                    )
                else:
                    # Explicit click_at values may be raw screenshot/device pixels.
                    mark_x, mark_y = x, y
            else:
                screen_width = getattr(self.action_ctx.ui, "screen_width", None)
                screen_height = getattr(self.action_ctx.ui, "screen_height", None)
                if (
                    isinstance(screen_width, int)
                    and isinstance(screen_height, int)
                    and screen_width > 0
                    and screen_height > 0
                ):
                    norm_x, norm_y = to_normalized(x, y, screen_width, screen_height)
                    mark_x, mark_y = to_absolute(
                        norm_x,
                        norm_y,
                        screenshot_width,
                        screenshot_height,
                    )
                else:
                    mark_x, mark_y = x, y

            self._save_grounding_annotation(screenshot, mark_x, mark_y)
        except Exception as e:
            logger.debug(f"Skipping click_at annotation for ({x}, {y}): {e}")

    async def _ground_click_at_with_screenshot(
        self,
        subgoal: str,
        proposed_action: dict,
    ) -> dict:
        """Resolve click_at coordinates from screenshot before executing the tap.

        This prevents guessed coordinates from being executed without an explicit
        vision grounding pass.
        """
        screenshot = self.shared_state.screenshot
        if screenshot is None:
            raise ValueError("No screenshot available for click_at grounding")

        ui_state_text = (self.shared_state.formatted_device_state or "").strip()
        use_normalized = bool(getattr(getattr(self.action_ctx, "ui", None), "use_normalized", False))
        screen_width = getattr(getattr(self.action_ctx, "ui", None), "screen_width", None)
        screen_height = getattr(getattr(self.action_ctx, "ui", None), "screen_height", None)
        proposed_x = proposed_action.get("x")
        proposed_y = proposed_action.get("y")
        screenshot_width, screenshot_height = Image.open(BytesIO(screenshot)).size

        def _build_grounding_prompt(*, screenshot_only: bool, extra_hint: str = "") -> str:
            ui_tree_note = (
                "Current UI tree text below is incomplete and may omit icon-only or styled navigation entries. "
                "Do NOT conclude the target is absent merely because its text is missing from the UI tree.\n"
                f"Current UI tree text:\n{ui_state_text or '[empty UI tree]'}\n\n"
                if not screenshot_only
                else ""
            )
            return (
                "You are grounding a mobile tap target from a screenshot.\n"
                f"Target subgoal: {subgoal}\n"
                f"Proposed coordinate from planner: ({proposed_x}, {proposed_y})\n"
                f"Actual device screen size: {screen_width}x{screen_height}\n"
                f"Screenshot image size: {screenshot_width}x{screenshot_height}\n\n"
                f"{ui_tree_note}"
                "Instructions:\n"
                "1. Base your answer primarily on the screenshot, not on UI-tree text.\n"
                "2. The target may be a visual icon/button whose text is not present in the UI tree.\n"
                "3. Treat the proposed planner coordinate as untrusted context only. If it conflicts with the screenshot, ignore it.\n"
                "4. If the intended target is visually present, return the best coordinate near its center in SCREENSHOT PIXELS.\n"
                f"5. Screenshot pixel coordinates must satisfy 0 <= x <= {screenshot_width} and 0 <= y <= {screenshot_height}.\n"
                "6. If it is not present or genuinely uncertain after inspecting the screenshot, return found=false.\n"
                "7. Never substitute another navigation item.\n"
                "8. Do NOT return normalized coordinates unless you also include the pixel x/y fields.\n\n"
                f"{extra_hint}"
                'Return JSON only: {"found": true|false, "x": 0, "y": 0, "reason": "..."}'
            )

        def _candidate_screenshot_point(parsed: dict) -> tuple[Optional[int], Optional[int]]:
            px = parsed.get("x")
            py = parsed.get("y")
            if isinstance(px, int) and isinstance(py, int):
                return px, py

            nx = parsed.get("x_norm")
            ny = parsed.get("y_norm")
            if isinstance(nx, int) and isinstance(ny, int):
                if 0 <= nx <= NORMALIZED_MAX and 0 <= ny <= NORMALIZED_MAX:
                    return to_absolute(nx, ny, screenshot_width, screenshot_height)
                if 0 <= nx <= screenshot_width and 0 <= ny <= screenshot_height:
                    return nx, ny

            return None, None

        async def _run_grounding_prompt(prompt: str) -> dict:
            messages = [
                ChatMessage(
                    role="user",
                    blocks=[TextBlock(text=prompt), ImageBlock(image=screenshot)],
                )
            ]
            response = await acall_with_retries(
                self.llm,
                messages,
                stream=self.agent_config.streaming,
            )
            return self._extract_json_object(str(response))

        logger.info("🔎 Grounding click_at target from screenshot before execution")
        parsed = await _run_grounding_prompt(
            _build_grounding_prompt(screenshot_only=False)
        )

        reason_text = str(parsed.get("reason", "") or "")
        ui_tree_bias_markers = [
            "ui tree",
            "ui元素",
            "ui树",
            "not present in the provided ui tree",
            "未在提供的ui元素",
            "未在提供的ui树",
            "not explicitly mentioned",
        ]
        if not parsed.get("found") and any(
            marker in reason_text.lower() for marker in ui_tree_bias_markers
        ):
            logger.info(
                "🔁 Grounding response relied on UI-tree absence; retrying with screenshot-only instructions"
            )
            parsed = await _run_grounding_prompt(
                _build_grounding_prompt(screenshot_only=True)
            )

        bottom_region_markers = [
            "bottom navigation",
            "navigation bar",
            "bottom bar",
            "tab bar",
            "底部",
            "底栏",
            "底部导航",
            "导航栏",
            "底部标签",
        ]
        subgoal_lower = (subgoal or "").lower()
        candidate_x, candidate_y = _candidate_screenshot_point(parsed)
        if parsed.get("found") and any(
            marker in subgoal_lower for marker in bottom_region_markers
        ) and candidate_y is not None and candidate_y < int(screenshot_height * 0.75):
            logger.info(
                "🔁 Grounding point is not in the bottom region; retrying with bottom-region constraint"
            )
            parsed = await _run_grounding_prompt(
                _build_grounding_prompt(
                    screenshot_only=True,
                    extra_hint=(
                        "Additional constraint: the target is in the bottom navigation region. "
                        f"Return a point in the bottom 25% of the screenshot (y >= {int(screenshot_height * 0.75)}).\n\n"
                    ),
                )
            )

        if not parsed.get("found"):
            reason = parsed.get("reason", "target not found on screenshot")
            raise ValueError(f"Screenshot grounding failed: {reason}")

        screenshot_abs_x = parsed.get("x")
        screenshot_abs_y = parsed.get("y")
        grounded_x_norm = parsed.get("x_norm")
        grounded_y_norm = parsed.get("y_norm")

        if isinstance(screenshot_abs_x, int) and isinstance(screenshot_abs_y, int):
            if not (
                0 <= screenshot_abs_x <= screenshot_width
                and 0 <= screenshot_abs_y <= screenshot_height
            ):
                raise ValueError(f"Out-of-range screenshot grounded coordinates: {parsed}")
            grounded_x_norm, grounded_y_norm = to_normalized(
                screenshot_abs_x,
                screenshot_abs_y,
                screenshot_width,
                screenshot_height,
            )
            mark_x, mark_y = screenshot_abs_x, screenshot_abs_y
        elif isinstance(grounded_x_norm, int) and isinstance(grounded_y_norm, int):
            if (
                0 <= grounded_x_norm <= NORMALIZED_MAX
                and 0 <= grounded_y_norm <= NORMALIZED_MAX
            ):
                mark_x, mark_y = to_absolute(
                    grounded_x_norm,
                    grounded_y_norm,
                    screenshot_width,
                    screenshot_height,
                )
            elif (
                0 <= grounded_x_norm <= screenshot_width
                and 0 <= grounded_y_norm <= screenshot_height
            ):
                # Some models put screenshot pixels into x_norm/y_norm fields.
                mark_x, mark_y = grounded_x_norm, grounded_y_norm
                grounded_x_norm, grounded_y_norm = to_normalized(
                    grounded_x_norm,
                    grounded_y_norm,
                    screenshot_width,
                    screenshot_height,
                )
                logger.info(
                    "🧭 Interpreting out-of-range x_norm/y_norm as screenshot pixels: "
                    f"pixels=({mark_x}, {mark_y}) -> normalized=({grounded_x_norm}, {grounded_y_norm})"
                )
            else:
                raise ValueError(f"Out-of-range normalized grounded coordinates: {parsed}")
        else:
            raise ValueError(f"Invalid grounded coordinates: {parsed}")

        if use_normalized:
            action_x, action_y = grounded_x_norm, grounded_y_norm
        else:
            if screen_width is None or screen_height is None:
                raise ValueError("Screen dimensions unavailable for absolute grounding")
            action_x, action_y = to_absolute(
                grounded_x_norm,
                grounded_y_norm,
                screen_width,
                screen_height,
            )

        logger.info(
            "🎯 Screenshot grounding selected coordinate "
            f"normalized=({grounded_x_norm}, {grounded_y_norm}), "
            f"action=({action_x}, {action_y}), "
            f"screenshot=({mark_x}, {mark_y})"
        )
        if use_normalized:
            click_mark_x, click_mark_y = to_absolute(
                action_x,
                action_y,
                screenshot_width,
                screenshot_height,
            )
        else:
            if (
                isinstance(screen_width, int)
                and isinstance(screen_height, int)
                and screen_width > 0
                and screen_height > 0
            ):
                click_norm_x, click_norm_y = to_normalized(
                    action_x,
                    action_y,
                    screen_width,
                    screen_height,
                )
                click_mark_x, click_mark_y = to_absolute(
                    click_norm_x,
                    click_norm_y,
                    screenshot_width,
                    screenshot_height,
                )
            else:
                click_mark_x, click_mark_y = mark_x, mark_y

        self._save_grounding_annotation(
            screenshot,
            click_mark_x,
            click_mark_y,
            target_x=mark_x,
            target_y=mark_y,
        )
        return {"x": action_x, "y": action_y, "reason": parsed.get("reason", "")}

    # 教程注释：先把当前设备状态、计划、历史动作拼成执行 Prompt，让模型知道“此刻该完成哪一步”。
    @step
    async def prepare_context(
        self, ctx: Context, ev: StartEvent
    ) -> ExecutorContextEvent:
        """Prepare executor context and prompt."""
        subgoal = ev.get("subgoal", "")
        logger.debug(f"🧠 Executor thinking about action for: {subgoal}")

        # Build action history (last 5)
        action_history = []
        if self.shared_state.action_history:
            n = min(5, len(self.shared_state.action_history))
            action_history = [
                {"action": act, "summary": summ, "outcome": outcome, "error": err}
                for act, summ, outcome, err in zip(
                    self.shared_state.action_history[-n:],
                    self.shared_state.summary_history[-n:],
                    self.shared_state.action_outcomes[-n:],
                    self.shared_state.error_descriptions[-n:],
                    strict=True,
                )
            ]

        # Get available secrets (only if type_secret is actually in the registry)
        available_secrets = []
        if (
            self.registry
            and "type_secret" in self.registry.tools
            and self.action_ctx
            and self.action_ctx.credential_manager
        ):
            available_secrets = await self.action_ctx.credential_manager.get_keys()

        # Build prompt variables
        variables = {
            "instruction": self.shared_state.instruction,
            "app_card": "",
            "device_state": self.shared_state.formatted_device_state,
            "plan": self.shared_state.plan,
            "subgoal": subgoal,
            "progress_status": self.shared_state.progress_summary,
            "atomic_actions": self.registry.get_signatures(exclude=self._EXCLUDE_TOOLS),
            "action_history": action_history,
            "available_secrets": available_secrets,
            "variables": self.shared_state.custom_variables,
            "platform": self.shared_state.platform,
        }

        custom_prompt = self.prompt_resolver.get_prompt("executor_system")
        if custom_prompt:
            prompt_text = PromptLoader.render_template(custom_prompt, variables)
        else:
            prompt_text = await PromptLoader.load_prompt(
                self.agent_config.get_executor_system_prompt_path(),
                variables,
            )

        # Build message
        messages = [ChatMessage(role="user", blocks=[TextBlock(text=prompt_text)])]

        # Add screenshot if vision enabled
        if self.vision:
            screenshot = self.shared_state.screenshot
            if screenshot is not None:
                messages[0].blocks.append(ImageBlock(image=screenshot))
                logger.debug("📸 Using screenshot for Executor")
            else:
                logger.warning("⚠️ Vision enabled but no screenshot available")
        await ctx.store.set("executor_messages", messages)
        await ctx.store.set("subgoal", subgoal)
        event = ExecutorContextEvent(subgoal=subgoal)
        ctx.write_event_to_stream(event)
        return event

    # 教程注释：这一阶段只做一件事，就是向 LLM 请求“下一步动作建议”，还不真正执行。
    @step
    async def get_response(
        self, ctx: Context, ev: ExecutorContextEvent
    ) -> ExecutorResponseEvent:
        """Get LLM response."""
        logger.debug("Executor getting LLM response...")

        # Get messages from context
        messages = await ctx.store.get("executor_messages")

        try:
            logger.info("Executor response:", extra={"color": "green"})
            response = await acall_with_retries(
                self.llm, messages, stream=self.agent_config.streaming
            )
            response_text = str(response)
        except ValueError as e:
            logger.warning(f"Executor LLM returned empty response: {e}")
            error_response = (
                "### Thought\nExecutor failed to respond, try again\n"
                '### Action\n{"action": "invalid"}\n'
                "### Description\nExecutor failed to respond, try again"
            )
            event = ExecutorResponseEvent(response=error_response, usage=None)
            ctx.write_event_to_stream(event)
            return event
        except Exception as e:
            raise RuntimeError(f"Error calling LLM in executor: {e}") from e

        # Extract usage
        usage = None
        try:
            usage = get_usage_from_response(self.llm.class_name(), response)
        except Exception as e:
            logger.warning(f"Could not get usage: {e}")

        event = ExecutorResponseEvent(response=response_text, usage=usage)
        ctx.write_event_to_stream(event)
        return event

    # 教程注释：把模型返回的文本解析成 thought、description 和 action JSON，准备进入真实执行。
    @step
    async def process_response(
        self, ctx: Context, ev: ExecutorResponseEvent
    ) -> ExecutorActionEvent:
        """Parse LLM response and extract action."""
        logger.debug("⚙️ Processing executor response...")

        response_text = ev.response

        try:
            parsed = parse_executor_response(response_text)
        except Exception as e:
            logger.error(f"❌ Failed to parse executor response: {e}")
            return ExecutorActionEvent(
                action_json=json.dumps({"action": "invalid"}),
                thought=f"Failed to parse response: {str(e)}",
                description="Invalid response format from LLM",
                full_response=response_text,
            )

        # Update unified state
        self.shared_state.last_thought = parsed["thought"]

        event = ExecutorActionEvent(
            action_json=parsed["action"],
            thought=parsed["thought"],
            description=parsed["description"],
            full_response=response_text,
        )

        ctx.write_event_to_stream(event)
        return event

    # 教程注释：这里把 action JSON 分发给 ToolRegistry，相当于把“模型决策”转成“程序动作”。
    @step
    async def execute(
        self, ctx: Context, ev: ExecutorActionEvent
    ) -> ExecutorActionResultEvent:
        """Execute the action."""
        logger.debug(f"⚡ Executing action: {ev.description}")

        try:
            action_dict = json.loads(ev.action_json)
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse action JSON: {e}")
            event = ExecutorActionResultEvent(
                action={"action": "invalid"},
                success=False,
                error=f"Invalid action JSON: {str(e)}",
                summary="Failed to parse action",
                thought=ev.thought,
                full_response=ev.full_response,
            )
            ctx.write_event_to_stream(event)
            return event

        # Extract action type and args, dispatch via registry
        action_type = action_dict.get("action", "unknown")
        action_args = {k: v for k, v in action_dict.items() if k != "action"}

        if action_type == "click_at":
            raw_x = action_args.get("x")
            raw_y = action_args.get("y")
            use_normalized = bool(
                getattr(getattr(self.action_ctx, "ui", None), "use_normalized", False)
            )
            screen_width = getattr(getattr(self.action_ctx, "ui", None), "screen_width", None)
            screen_height = getattr(getattr(self.action_ctx, "ui", None), "screen_height", None)

            if isinstance(raw_x, int) and isinstance(raw_y, int) and use_normalized:
                if not (0 <= raw_x <= NORMALIZED_MAX and 0 <= raw_y <= NORMALIZED_MAX):
                    if (
                        isinstance(screen_width, int)
                        and isinstance(screen_height, int)
                        and screen_width > 0
                        and screen_height > 0
                    ):
                        norm_x, norm_y = to_normalized(
                            raw_x,
                            raw_y,
                            screen_width,
                            screen_height,
                        )
                        norm_x = max(0, min(NORMALIZED_MAX, norm_x))
                        norm_y = max(0, min(NORMALIZED_MAX, norm_y))
                        logger.info(
                            f"🧭 Converted click_at pixels ({raw_x}, {raw_y}) to normalized ({norm_x}, {norm_y})"
                        )
                        action_args["x"] = norm_x
                        action_args["y"] = norm_y
                        action_dict["x"] = norm_x
                        action_dict["y"] = norm_y

        subgoal = ""
        try:
            subgoal = await ctx.store.get("subgoal")
        except Exception:
            subgoal = ""

        subgoal_targets = self._extract_required_targets(subgoal or "")
        subgoal_has_explicit_coordinates = self._subgoal_has_explicit_coordinates(
            subgoal or ""
        )

        click_at_grounded = False

        # If subgoal names a concrete target (e.g. "赚钱"), always ground click_at
        # from screenshot to avoid executing stale guessed coordinates.
        if action_type == "click_at" and (
            (not subgoal_has_explicit_coordinates) or bool(subgoal_targets)
        ):
            try:
                grounded = await self._ground_click_at_with_screenshot(
                    subgoal=subgoal or "",
                    proposed_action=action_dict,
                )
                action_args["x"] = grounded["x"]
                action_args["y"] = grounded["y"]
                action_dict["x"] = grounded["x"]
                action_dict["y"] = grounded["y"]
                click_at_grounded = True
            except Exception as e:
                logger.warning(f"click_at grounding blocked execution: {e}")
                event = ExecutorActionResultEvent(
                    action=action_dict,
                    success=False,
                    error=str(e),
                    summary=f"Blocked ungrounded click_at: {e}",
                    thought=ev.thought,
                    full_response=ev.full_response,
                )
                ctx.write_event_to_stream(event)
                return event

        required_targets = self._extract_required_targets(subgoal or "")
        if not required_targets:
            required_targets = self._extract_required_targets(
                self.shared_state.instruction
            )
        matched_target = next(
            (
                target
                for target in required_targets
                if self._find_target_index_in_ui(target) is not None
            ),
            None,
        )
        matched_index = (
            self._find_target_index_in_ui(matched_target) if matched_target else None
        )

        if matched_target is not None and matched_index is not None:
            if action_type == "click_at":
                logger.info(
                    f"🎯 Rewriting click_at to click(index={matched_index}) because target '{matched_target}' exists in UI tree"
                )
                action_type = "click"
                action_args = {"index": matched_index}
                action_dict = {"action": "click", "index": matched_index}
            elif action_type == "click":
                click_index = action_args.get("index")
                if click_index != matched_index:
                    logger.info(
                        f"🎯 Rewriting click(index={click_index}) to click(index={matched_index}) for target '{matched_target}' found in UI tree"
                    )
                    action_args = {"index": matched_index}
                    action_dict = {"action": "click", "index": matched_index}

        missing_targets = [
            target for target in required_targets if not self._ui_contains_target(target)
        ]
        if missing_targets and action_type in {"click", "swipe"}:
            target_list = ", ".join(missing_targets)
            if action_type == "click":
                click_index = action_args.get("index")
                if isinstance(click_index, int) and any(
                    self._click_index_matches_target(click_index, target)
                    for target in missing_targets
                ):
                    pass
                else:
                    reason = (
                        f"Required target(s) [{target_list}] not found in UI tree. "
                        "Must analyze screenshot first and use click_at coordinates instead of clicking unrelated elements."
                    )
                    event = ExecutorActionResultEvent(
                        action=action_dict,
                        success=False,
                        error=reason,
                        summary=f"Blocked fallback click: {reason}",
                        thought=ev.thought,
                        full_response=ev.full_response,
                    )
                    ctx.write_event_to_stream(event)
                    return event
            else:
                reason = (
                    f"Required target(s) [{target_list}] not found in UI tree. "
                    "Must analyze screenshot first and use click_at coordinates instead of swiping to explore."
                )
                event = ExecutorActionResultEvent(
                    action=action_dict,
                    success=False,
                    error=reason,
                    summary=f"Blocked fallback swipe: {reason}",
                    thought=ev.thought,
                    full_response=ev.full_response,
                )
                ctx.write_event_to_stream(event)
                return event

        result = await self.registry.execute(
            action_type, action_args, self.action_ctx, workflow_ctx=ctx
        )

        if result.success and action_type == "click":
            click_index = action_args.get("index")
            if isinstance(click_index, int):
                self._save_index_click_annotation(click_index)
        elif result.success and action_type == "click_at" and not click_at_grounded:
            tap_x = action_args.get("x")
            tap_y = action_args.get("y")
            if isinstance(tap_x, int) and isinstance(tap_y, int):
                self._save_click_at_annotation(tap_x, tap_y)

        await asyncio.sleep(self.agent_config.after_sleep_action)

        logger.debug(
            f"{'✅' if result.success else '❌'} Execution complete: {result.summary}"
        )

        event = ExecutorActionResultEvent(
            action=action_dict,
            success=result.success,
            error="" if result.success else result.summary,
            summary=result.summary,
            thought=ev.thought,
            full_response=ev.full_response,
        )
        ctx.write_event_to_stream(event)
        return event

    # 教程注释：执行器最后把本轮动作结果打包返回给父工作流，供 Manager 或上层控制器继续判断。
    @step
    async def finalize(self, ctx: Context, ev: ExecutorActionResultEvent) -> StopEvent:
        """Return executor results to parent workflow."""
        logger.debug("✅ Executor execution complete")

        return StopEvent(
            result={
                "action": ev.action,
                "outcome": ev.success,
                "error": ev.error,
                "summary": ev.summary,
                "thought": ev.thought,
            }
        )
