"""
Judge abstraction layer — from EVALKIT_MASTER_SPEC_v2.md Section 6 (Layer B).

All LLM calls for evaluation go through this interface.
Prompt templates match the spec exactly.
"""
from abc import ABC, abstractmethod
import json
import logging
import re

from evalkit.layers.cost_tracker import estimate_tokens

logger = logging.getLogger(__name__)

PROMPT_VERSION = "1.0.0"

MAX_INPUT_TOKENS = 100_000

_circuit_registry: dict[str, dict] = {}


def _get_circuit(model_name: str) -> dict:
    if model_name not in _circuit_registry:
        _circuit_registry[model_name] = {"failure_count": 0, "open": False, "max_failures": 5}
    return _circuit_registry[model_name]

FAITHFULNESS_PROMPT = """You are evaluating whether a response is faithful to the provided context.

CONTEXT:
{contexts_joined}

QUERY:
{query}

RESPONSE:
{response}

TASK:
1. List every factual claim in the response (as a JSON array)
2. For each claim, determine if it is SUPPORTED, PARTIALLY_SUPPORTED, or UNSUPPORTED by the context
3. Return a faithfulness score (supported_claims / total_claims)

EXAMPLES:

Example 1 (High faithfulness):
Query: "What is the capital of France?"
Response: "The capital of France is Paris."
Context: "Paris is the capital and largest city of France."
Output: {{"claims": [{{"text": "The capital of France is Paris", "support": "supported", "evidence_span": "Paris is the capital and largest city of France"}}], "faithfulness_score": 1.0}}

Example 2 (Low faithfulness):
Query: "When was the company founded?"
Response: "The company was founded in 1842 and has 500 employees."
Context: "Acme Corp was established in 2001."
Output: {{"claims": [{{"text": "The company was founded in 1842", "support": "unsupported", "evidence_span": ""}}, {{"text": "has 500 employees", "support": "unsupported", "evidence_span": ""}}], "faithfulness_score": 0.0}}

OUTPUT FORMAT (strict JSON, no other text):
{{
  "claims": [
    {{"text": "...", "support": "supported|partial|unsupported", "evidence_span": "..."}}
  ],
  "faithfulness_score": 0.0
}}"""

RELEVANCE_PROMPT = """You are evaluating whether a response directly addresses the user's query.

QUERY:
{query}

RESPONSE:
{response}

TASK:
Score 0.0-1.0 on how well the response addresses the query.
1.0 = perfectly addresses the question
0.5 = partially addresses but misses key aspects
0.0 = completely off-topic

EXAMPLES:

Example 1 (High relevance):
Query: "What are the side effects of aspirin?"
Response: "Common side effects of aspirin include stomach irritation, nausea, and increased bleeding risk."
Output: {{"answer_relevance": 0.95, "reasoning": "Response directly lists side effects as asked."}}

Example 2 (Low relevance):
Query: "What are the side effects of aspirin?"
Response: "Aspirin was first synthesized in 1897 by Felix Hoffmann at Bayer."
Output: {{"answer_relevance": 0.1, "reasoning": "Response discusses history, not side effects."}}

OUTPUT FORMAT (strict JSON, no other text):
{{
  "answer_relevance": 0.0,
  "reasoning": "..."
}}"""


def parse_json_response(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return {}


class BaseJudge(ABC):

    def __init__(self):
        self._last_usage: dict | None = None

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...

    @abstractmethod
    async def _call_llm(self, prompt: str) -> str:
        ...

    def _check_circuit(self):
        circuit = _get_circuit(self.model_name)
        if circuit["open"]:
            raise RuntimeError(
                f"Circuit breaker open for {self.model_name} "
                f"after {circuit['max_failures']} consecutive failures"
            )

    def _record_success(self):
        circuit = _get_circuit(self.model_name)
        circuit["failure_count"] = 0
        circuit["open"] = False

    def _record_failure(self):
        circuit = _get_circuit(self.model_name)
        circuit["failure_count"] += 1
        if circuit["failure_count"] >= circuit["max_failures"]:
            circuit["open"] = True

    def _truncate_contexts(self, contexts_joined: str, query: str, response: str) -> str:
        full_input = contexts_joined + query + response
        estimated = estimate_tokens(full_input)
        if estimated > MAX_INPUT_TOKENS:
            max_context_chars = (MAX_INPUT_TOKENS - estimate_tokens(query + response) - 200) * 4
            logger.warning(
                f"Input exceeds {MAX_INPUT_TOKENS} tokens ({estimated}), truncating contexts"
            )
            return contexts_joined[:max(0, max_context_chars)]
        return contexts_joined

    async def evaluate_faithfulness(
        self,
        query: str,
        response: str,
        contexts: list[str],
    ) -> dict:
        self._check_circuit()
        contexts_joined = "\n\n---\n\n".join(contexts)
        contexts_joined = self._truncate_contexts(contexts_joined, query, response)
        prompt = FAITHFULNESS_PROMPT.format(
            contexts_joined=contexts_joined,
            query=query,
            response=response,
        )

        try:
            raw = await self._call_llm(prompt)
            self._record_success()
        except Exception:
            self._record_failure()
            raise

        parsed = parse_json_response(raw)

        return {
            "faithfulness": parsed.get("faithfulness_score", 0.0),
            "claims": parsed.get("claims", []),
            "raw_response": raw,
            "prompt_version": PROMPT_VERSION,
        }

    async def evaluate_relevance(
        self,
        query: str,
        response: str,
    ) -> dict:
        self._check_circuit()
        prompt = RELEVANCE_PROMPT.format(
            query=query,
            response=response,
        )

        try:
            raw = await self._call_llm(prompt)
            self._record_success()
        except Exception:
            self._record_failure()
            raise

        parsed = parse_json_response(raw)

        return {
            "answer_relevance": parsed.get("answer_relevance", 0.0),
            "reasoning": parsed.get("reasoning", ""),
            "raw_response": raw,
            "prompt_version": PROMPT_VERSION,
        }
