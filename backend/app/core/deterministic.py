from typing import Dict, List, Tuple
from dataclasses import dataclass
from ..schemas.canonical import CanonicalEvaluation
from ..cost.token_counter import TokenCounter


@dataclass
class DeterministicResult:
    """Result from Stage 1 deterministic checks"""
    issues: List[Dict]
    metrics: Dict
    confidence: float

    def has_p0_failures(self) -> bool:
        return any(issue["severity"] == "P0" for issue in self.issues)

    def has_p1_failures(self) -> bool:
        return any(issue["severity"] == "P1" for issue in self.issues)


class DeterministicChecker:
    """
    Stage 1: Free deterministic checks (0 LLM cost).

    Checks:
    - Empty response → P0 EMPTY_ANSWER
    - Empty context → P0 NO_CONTEXT
    - Token limit exceeded → P1 TOKEN_LIMIT_EXCEEDED

    Expected: 60% of evaluations complete at this stage.
    """

    MAX_TOKENS = 128000  # Claude/GPT-4 context limit

    def __init__(self):
        self.token_counter = TokenCounter()

    async def check(self, canonical: CanonicalEvaluation) -> DeterministicResult:
        """Run all deterministic checks"""
        issues = []
        metrics = {}

        # Check 1: Empty response (P0)
        if not canonical.response or len(canonical.response.strip()) < 10:
            issues.append({
                "code": "EMPTY_ANSWER",
                "severity": "P0",
                "message": "Response is empty or too short (<10 chars)"
            })

        # Check 2: Empty context (P0)
        if not canonical.context_chunks or all(
            len(chunk.text.strip()) < 10
            for chunk in canonical.context_chunks
        ):
            issues.append({
                "code": "NO_CONTEXT",
                "severity": "P0",
                "message": "No valid context chunks provided"
            })

        # Check 3: Token limit (P1)
        total_tokens = self._count_total_tokens(canonical)
        metrics["total_tokens"] = total_tokens

        if total_tokens > self.MAX_TOKENS:
            issues.append({
                "code": "TOKEN_LIMIT_EXCEEDED",
                "severity": "P1",
                "message": f"Total tokens ({total_tokens}) exceeds {self.MAX_TOKENS} limit"
            })

        # Collect latency metrics
        metrics["response_latency_ms"] = canonical.total_latency_ms or 0
        metrics["retrieval_latency_ms"] = canonical.retrieval_latency_ms
        metrics["generation_latency_ms"] = canonical.generation_latency_ms

        # Calculate confidence
        # P0 failures = 100% confidence (we're certain it's bad)
        # No issues = 60% confidence (need LLM to verify quality)
        if any(i["severity"] == "P0" for i in issues):
            confidence = 1.0
        elif issues:
            confidence = 0.5
        else:
            confidence = 0.6

        return DeterministicResult(
            issues=issues,
            metrics=metrics,
            confidence=confidence
        )

    def _count_total_tokens(self, canonical: CanonicalEvaluation) -> int:
        """Count total tokens in the evaluation"""
        model = canonical.metadata.get("model", "gpt-4o")

        query_tokens = self.token_counter.count(canonical.query, model)
        context_tokens = sum(
            self.token_counter.count(chunk.text, model)
            for chunk in canonical.context_chunks
        )
        response_tokens = self.token_counter.count(canonical.response, model)

        return query_tokens + context_tokens + response_tokens
