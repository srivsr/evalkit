from decimal import Decimal

PRICING = {
    "gpt-4o": {"input": Decimal("2.50"), "output": Decimal("10.00")},
    "gpt-4o-mini": {"input": Decimal("0.15"), "output": Decimal("0.60")},
    "gpt-4-turbo": {"input": Decimal("10.00"), "output": Decimal("30.00")},
    "claude-sonnet-4-20250514": {"input": Decimal("3.00"), "output": Decimal("15.00")},
    "claude-3-5-haiku-20241022": {"input": Decimal("1.00"), "output": Decimal("5.00")},
}


class CostCalculator:
    def calculate(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> Decimal:
        pricing = PRICING.get(model, PRICING["gpt-4o-mini"])
        input_cost = (Decimal(input_tokens) / Decimal(1_000_000)) * pricing["input"]
        output_cost = (Decimal(output_tokens) / Decimal(1_000_000)) * pricing["output"]
        return input_cost + output_cost
