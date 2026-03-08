"""EvalKit configuration — from EVALKIT_MASTER_SPEC_v2.md Section 11."""
from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings


class ThresholdConfig(BaseSettings):
    recall_poor: float = 0.3
    precision_poor: float = 0.2
    faithfulness_low: float = 0.5
    relevance_low: float = 0.5
    claim_hallucination: float = 0.3
    claim_evidence_not_used: float = 0.5
    answerability_strong: float = 0.8
    answerability_partial: float = 0.4
    answerability_recall_high: float = 0.7
    answerability_recall_mid: float = 0.3
    answerability_recall_unanswerable: float = 0.2
    false_refusal_recall: float = 0.6
    regression_pct: float = 0.10
    anomaly_regression_pct: float = 0.20
    relevance_label_threshold: float = 0.5


class Settings(BaseSettings):
    db_path: str = "./evalkit.db"
    default_judge: str = "gpt-4o"
    judge_timeout_ms: int = 30000
    judge_max_tokens: int = 2048
    cost_cap_usd: Optional[float] = None

    @field_validator("cost_cap_usd", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        if v == "":
            return None
        return v

    log_level: str = "INFO"
    thresholds: ThresholdConfig = ThresholdConfig()
    chunk_min_words: int = 20
    chunk_max_words: int = 500
    default_embedding_model: str = "text-embedding-3-small"

    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    # Auth
    clerk_secret_key: Optional[str] = None
    clerk_publishable_key: Optional[str] = None
    environment: str = "development"

    # Payment - PayPal
    paypal_client_id: Optional[str] = None
    paypal_client_secret: Optional[str] = None
    paypal_mode: str = "sandbox"

    # Payment - Razorpay
    razorpay_key_id: Optional[str] = None
    razorpay_key_secret: Optional[str] = None

    # Payment - Payoneer
    payoneer_partner_id: Optional[str] = None
    payoneer_api_key: Optional[str] = None

    # Rate limiting
    rate_limit_requests_per_minute: int = 100
    rate_limit_evaluate_per_hour: int = 20

    # Frontend
    frontend_url: str = "http://localhost:3003"
    cors_origins: str = "http://localhost:3000,http://localhost:3003,http://localhost:3004,http://localhost:3005"

    # Webhook secrets
    paypal_webhook_id: Optional[str] = None
    razorpay_webhook_secret: Optional[str] = None

    model_config = {
        "env_prefix": "EVALKIT_",
        "env_file": ".env",
        "extra": "ignore",
    }


settings = Settings()
