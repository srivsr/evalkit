import os
import logging
from decimal import Decimal
from typing import Dict, Any
from pathlib import Path
import yaml

from .token_counter import TokenCounter

logger = logging.getLogger(__name__)


class CostCalculator:
    """
    Calculate evaluation costs.

    Loads pricing from config/pricing.yaml (NOT hardcoded).
    Uses Decimal for precision.
    """

    def __init__(self, pricing_config_path: str = None):
        self.token_counter = TokenCounter()

        # Find pricing config
        if pricing_config_path:
            config_path = Path(pricing_config_path)
        else:
            # Look in standard locations
            possible_paths = [
                Path(__file__).parent / "pricing.yaml",
                Path(__file__).parent.parent / "config" / "pricing.yaml",
                Path("config/pricing.yaml"),
            ]
            config_path = None
            for p in possible_paths:
                if p.exists():
                    config_path = p
                    break

        # Load pricing
        if config_path and config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)
            self.pricing_version = config.get("pricing_version", "unknown")
            self._load_pricing(config.get("models", {}))
        else:
            logger.warning("Pricing config not found, using defaults")
            self.pricing_version = "default"
            self._load_defaults()

    def _load_pricing(self, models: Dict):
        """Load pricing from config"""
        self.pricing = {}
        for model, data in models.items():
            self.pricing[model] = {
                "input": Decimal(str(data.get("input_per_million", 0))) / Decimal("1000000"),
                "output": Decimal(str(data.get("output_per_million", 0))) / Decimal("1000000")
            }

    def _load_defaults(self):
        """Load default pricing (fallback)"""
        self.pricing = {
            "gpt-4o": {
                "input": Decimal("2.50") / Decimal("1000000"),
                "output": Decimal("10.00") / Decimal("1000000")
            },
            "gpt-4o-mini": {
                "input": Decimal("0.15") / Decimal("1000000"),
                "output": Decimal("0.60") / Decimal("1000000")
            },
            "claude-sonnet-4-20250514": {
                "input": Decimal("3.00") / Decimal("1000000"),
                "output": Decimal("15.00") / Decimal("1000000")
            },
            "claude-haiku-4-20250131": {
                "input": Decimal("0.80") / Decimal("1000000"),
                "output": Decimal("4.00") / Decimal("1000000")
            },
        }

    def calculate(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> Decimal:
        """
        Calculate cost for a single LLM call.

        Args:
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in dollars (Decimal)
        """
        if model not in self.pricing:
            logger.warning(f"Unknown model {model}, using gpt-4o-mini pricing")
            model = "gpt-4o-mini"

        prices = self.pricing[model]

        cost = (
            (Decimal(input_tokens) * prices["input"]) +
            (Decimal(output_tokens) * prices["output"])
        )

        return cost

    def estimate_evaluation_cost(
        self,
        query: str,
        context_texts: list,
        response: str,
        pipeline_stage: str,
        judge_model: str = "gpt-4o-mini"
    ) -> Dict[str, Any]:
        """
        Estimate cost for an evaluation.

        Returns cost breakdown by stage.
        """
        # Count tokens
        query_tokens = self.token_counter.count(query, judge_model)
        context_tokens = sum(
            self.token_counter.count(text, judge_model)
            for text in context_texts
        )
        response_tokens = self.token_counter.count(response, judge_model)

        # RAGAS makes ~5 LLM calls
        num_llm_calls = 5
        avg_input = query_tokens + context_tokens + response_tokens
        avg_output = 50  # Short judgments

        total_input = avg_input * num_llm_calls
        total_output = avg_output * num_llm_calls

        # Calculate by stage
        cost_breakdown = {
            "deterministic": Decimal("0"),
            "small_model": Decimal("0"),
            "large_model": Decimal("0")
        }

        if pipeline_stage in ["small_model", "large_model"]:
            cost_breakdown["small_model"] = self.calculate(
                "gpt-4o-mini",
                total_input,
                total_output
            )

        if pipeline_stage == "large_model":
            cost_breakdown["large_model"] = self.calculate(
                "gpt-4o",
                total_input,
                total_output
            )

        total_cost = sum(cost_breakdown.values())

        return {
            "deterministic_cost": float(cost_breakdown["deterministic"]),
            "small_model_cost": float(cost_breakdown["small_model"]),
            "large_model_cost": float(cost_breakdown["large_model"]),
            "total_cost": float(total_cost),
            "tokens_used": total_input + total_output,
            "pricing_version": self.pricing_version
        }
