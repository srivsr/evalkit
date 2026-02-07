from typing import Dict, List, Callable, Optional
from dataclasses import dataclass
from ..schemas import CanonicalEvaluation


@dataclass
class AutoFixRule:
    name: str
    priority: int
    condition: Callable
    recommendation_generator: Callable

    def applies(self, canonical: CanonicalEvaluation, metrics: Dict) -> bool:
        try:
            return self.condition(canonical, metrics)
        except Exception:
            return False

    def generate(self, canonical: CanonicalEvaluation, metrics: Dict) -> Dict:
        return self.recommendation_generator(canonical, metrics)


class AutoFixEngine:
    def __init__(self):
        self.rules = self._init_rules()

    def _init_rules(self) -> List[AutoFixRule]:
        return [
            AutoFixRule(
                name="chunk_size_too_small",
                priority=10,
                condition=lambda c, m: (
                    m.get("faithfulness", 1.0) < 0.6 and
                    c.metadata.get("chunk_size", 512) < 200
                ),
                recommendation_generator=lambda c, m: {
                    "type": "chunk_size",
                    "current_value": c.metadata.get("chunk_size"),
                    "recommended_value": 512,
                    "expected_improvement": "+15-25% faithfulness",
                    "confidence": "high",
                    "evidence": {
                        "current_faithfulness": m.get("faithfulness"),
                        "chunk_fragmentation_detected": True
                    }
                }
            ),
            AutoFixRule(
                name="low_context_recall",
                priority=8,
                condition=lambda c, m: (
                    m.get("context_recall", 1.0) < 0.5 and
                    c.metadata.get("top_k", 5) <= 3
                ),
                recommendation_generator=lambda c, m: {
                    "type": "top_k",
                    "current_value": c.metadata.get("top_k"),
                    "recommended_value": c.metadata.get("top_k", 3) + 2,
                    "expected_improvement": "+10-20% context recall",
                    "confidence": "medium",
                    "evidence": {
                        "current_recall": m.get("context_recall"),
                        "relevant_chunks_missed": "estimated"
                    }
                }
            ),
            AutoFixRule(
                name="low_retrieval_scores",
                priority=9,
                condition=lambda c, m: (
                    len([ch for ch in c.context_chunks if ch.score]) > 0 and
                    sum(ch.score for ch in c.context_chunks if ch.score) /
                    len([ch for ch in c.context_chunks if ch.score]) < 0.5
                ),
                recommendation_generator=lambda c, m: {
                    "type": "embedding_model",
                    "current_value": c.metadata.get("embedding_model", "text-embedding-ada-002"),
                    "recommended_value": "text-embedding-3-large",
                    "expected_improvement": "+15-25% retrieval quality",
                    "confidence": "high",
                    "evidence": {
                        "avg_context_score": sum(ch.score for ch in c.context_chunks if ch.score) /
                                            len([ch for ch in c.context_chunks if ch.score]),
                        "sample_size": len(c.context_chunks)
                    }
                }
            ),
            AutoFixRule(
                name="high_hallucination",
                priority=10,
                condition=lambda c, m: (
                    m.get("hallucination_score", 0.0) > 0.3 and
                    not c.metadata.get("reranker")
                ),
                recommendation_generator=lambda c, m: {
                    "type": "reranker",
                    "current_value": None,
                    "recommended_value": "cohere-rerank-v3",
                    "expected_improvement": "-20-30% hallucination",
                    "confidence": "medium",
                    "evidence": {
                        "hallucination_score": m.get("hallucination_score"),
                        "reranker_currently_enabled": False
                    }
                }
            ),
            AutoFixRule(
                name="cost_too_high",
                priority=5,
                condition=lambda c, m: (
                    m.get("cost_per_query", 0.0) > 0.01 and
                    c.metadata.get("model", "").startswith("gpt-4")
                ),
                recommendation_generator=lambda c, m: {
                    "type": "model",
                    "current_value": c.metadata.get("model"),
                    "recommended_value": "gpt-4o-mini",
                    "expected_improvement": "-70% cost with minimal quality loss",
                    "confidence": "high",
                    "evidence": {
                        "current_cost": m.get("cost_per_query"),
                        "estimated_new_cost": m.get("cost_per_query", 0) * 0.3
                    }
                }
            ),
        ]

    def analyze(
        self,
        canonical: CanonicalEvaluation,
        metrics: Dict
    ) -> List[Dict]:
        recommendations = []

        for rule in sorted(self.rules, key=lambda r: -r.priority):
            if rule.applies(canonical, metrics):
                rec = rule.generate(canonical, metrics)
                rec["rule_name"] = rule.name
                recommendations.append(rec)

        return recommendations
