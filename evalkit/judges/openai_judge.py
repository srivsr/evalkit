"""OpenAI judge implementation."""
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from evalkit.judges.base import BaseJudge
from evalkit.config import settings


class OpenAIJudge(BaseJudge):

    def __init__(self, model: str = "gpt-4o", api_key: str | None = None):
        super().__init__()
        self._model = model
        self._api_key = api_key or settings.openai_api_key
        self._client = None

    @property
    def model_name(self) -> str:
        return self._model

    def _get_client(self):
        if self._client is None:
            if not self._api_key:
                raise RuntimeError("OPENAI_API_KEY not configured")
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key=self._api_key)
            except ImportError:
                raise ImportError("openai package required: pip install openai")
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
                client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": "You are an evaluation judge. Always respond with valid JSON only."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.0,
                    response_format={"type": "json_object"},
                ),
                timeout=timeout_s,
            )
            usage = response.usage
            if usage:
                self._last_usage = {
                    "prompt_tokens": usage.prompt_tokens,
                    "completion_tokens": usage.completion_tokens,
                }
            return response.choices[0].message.content or ""
        except asyncio.TimeoutError:
            raise TimeoutError(f"OpenAI judge timed out after {timeout_s}s")
        except Exception as e:
            err_type = type(e).__name__
            raise RuntimeError(f"OpenAI judge error ({err_type}): {e}")
