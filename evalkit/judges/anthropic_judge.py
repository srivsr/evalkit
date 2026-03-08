"""Anthropic judge implementation."""
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from evalkit.judges.base import BaseJudge
from evalkit.config import settings


class AnthropicJudge(BaseJudge):

    def __init__(self, model: str = "claude-sonnet-4-20250514", api_key: str | None = None):
        super().__init__()
        self._model = model
        self._api_key = api_key or settings.anthropic_api_key
        self._client = None

    @property
    def model_name(self) -> str:
        return self._model

    def _get_client(self):
        if self._client is None:
            if not self._api_key:
                raise RuntimeError("ANTHROPIC_API_KEY not configured")
            try:
                from anthropic import AsyncAnthropic
                self._client = AsyncAnthropic(api_key=self._api_key)
            except ImportError:
                raise ImportError("anthropic package required: pip install anthropic")
        return self._client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((TimeoutError, ConnectionError, OSError)),
        reraise=True,
    )
    async def _call_llm(self, prompt: str) -> str:
        client = self._get_client()
        timeout_s = settings.judge_timeout_ms / 1000

        try:
            response = await asyncio.wait_for(
                client.messages.create(
                    model=self._model,
                    max_tokens=settings.judge_max_tokens,
                    system="You are an evaluation judge. Always respond with valid JSON only. No markdown, no explanation — just JSON.",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0,
                ),
                timeout=timeout_s,
            )
            if hasattr(response, "usage") and response.usage:
                self._last_usage = {
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                }
            if response.content:
                texts = [block.text for block in response.content if hasattr(block, "text")]
                return "\n".join(texts)
            return ""
        except asyncio.TimeoutError:
            raise TimeoutError(f"Anthropic judge timed out after {timeout_s}s")
        except Exception as e:
            err_type = type(e).__name__
            raise RuntimeError(f"Anthropic judge error ({err_type}): {e}")
