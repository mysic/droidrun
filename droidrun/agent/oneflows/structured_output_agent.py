"""
StructuredOutputAgent - Extract structured data from final answers.

Takes a raw text answer and a Pydantic model, uses structured_predict()
to extract structured data from the text.
"""

import logging
from typing import Type

from llama_index.core.llms.llm import LLM
from llama_index.core.prompts import PromptTemplate
from llama_index.core.workflow import Context, StartEvent, StopEvent, Workflow, step
from pydantic import BaseModel

from droidrun.agent.utils.inference import astructured_predict_with_retries

logger = logging.getLogger("droidrun")


# 教程注释：StructuredOutputAgent 专门负责把最终自然语言答案提取成结构化 Pydantic 对象。
class StructuredOutputAgent(Workflow):
    """
    Agent that extracts structured output from text answers.

    Uses LLM.structured_predict() to parse text into Pydantic models.
    """

    def __init__(
        self,
        llm: LLM,
        pydantic_model: Type[BaseModel],
        answer_text: str,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.llm = llm
        self.pydantic_model = pydantic_model
        self.answer_text = answer_text

    # 教程注释：这一步通过 structured_predict 做类型约束提取，成功返回结构化结果，失败返回错误信息。
    @step
    async def extract_structured_output(
        self, ctx: Context, ev: StartEvent
    ) -> StopEvent:
        """
        Extract structured output using structured_predict().
        """
        logger.debug("🔍 Extracting structured output from final answer...")

        try:
            # 教程注释：Prompt 很短，因为真正的约束主要来自 pydantic_model 的 schema。
            prompt = PromptTemplate(
                "Extract structured information from the following text:\n\n{text}"
            )

            # Use structured_predict to extract data
            logger.info("🔍 StructuredOutput response:", extra={"color": "magenta"})
            structured_output = await astructured_predict_with_retries(
                self.llm, self.pydantic_model, prompt, text=self.answer_text
            )

            logger.debug("✅ Successfully extracted structured output")

            return StopEvent(
                result={
                    "structured_output": structured_output,
                    "success": True,
                    "error_message": "",
                }
            )

        except Exception as e:
            # 教程注释：这里不抛异常给主 Agent，而是把失败包装成结果，避免最终回答链整体失败。
            logger.error(f"❌ Failed to extract structured output: {e}")

            return StopEvent(
                result={
                    "structured_output": None,
                    "success": False,
                    "error_message": str(e),
                }
            )
