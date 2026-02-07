import logging

logger = logging.getLogger(__name__)


class TokenCounter:
    """
    Accurate token counting for billing.

    Uses real tokenizers:
    - tiktoken for OpenAI models
    - Anthropic SDK for Claude models

    Fallback: char/4 estimation with warning
    """

    def __init__(self):
        self._tiktoken_encoder = None
        self._anthropic_client = None

    @property
    def tiktoken_encoder(self):
        """Lazy load tiktoken encoder"""
        if self._tiktoken_encoder is None:
            try:
                import tiktoken
                self._tiktoken_encoder = tiktoken.encoding_for_model("gpt-4o")
            except Exception as e:
                logger.warning(f"Failed to load tiktoken: {e}")
        return self._tiktoken_encoder

    @property
    def anthropic_client(self):
        """Lazy load Anthropic client"""
        if self._anthropic_client is None:
            try:
                from anthropic import Anthropic
                self._anthropic_client = Anthropic()
            except Exception as e:
                logger.warning(f"Failed to load Anthropic client: {e}")
        return self._anthropic_client

    def count(self, text: str, model: str = "gpt-4o") -> int:
        """
        Count tokens accurately.

        Args:
            text: Text to count tokens for
            model: Model name (gpt-*, claude-*, text-embedding-*)

        Returns:
            Token count
        """
        if not text:
            return 0

        # OpenAI models
        if model.startswith("gpt-") or model.startswith("text-embedding"):
            if self.tiktoken_encoder:
                try:
                    return len(self.tiktoken_encoder.encode(text))
                except Exception as e:
                    logger.warning(f"tiktoken encoding failed: {e}")

        # Anthropic models
        elif model.startswith("claude-"):
            if self.anthropic_client:
                try:
                    return self.anthropic_client.count_tokens(text)
                except Exception as e:
                    logger.warning(f"Anthropic token count failed: {e}")

        # Fallback estimation
        estimated = len(text) // 4
        logger.debug(f"Using estimated tokens ({estimated}) for model {model}")
        return estimated

    def count_messages(self, messages: list, model: str = "gpt-4o") -> int:
        """
        Count tokens in a list of messages.

        Includes message overhead (~4 tokens per message).
        """
        total = 0

        for msg in messages:
            total += 4  # Message overhead

            for key, value in msg.items():
                if isinstance(value, str):
                    total += self.count(value, model)

        total += 2  # Reply priming
        return total
