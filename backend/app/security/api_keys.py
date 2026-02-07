import hashlib
import secrets
import re
from typing import Tuple


class APIKeyManager:
    KEY_PATTERN = re.compile(r"^pk_(live|test)_[a-zA-Z0-9]{32}$")

    @staticmethod
    def generate(env: str = "test") -> Tuple[str, str, str]:
        """
        Generate a new API key.
        Returns: (raw_key, key_hash, key_prefix)
        """
        if env not in ("live", "test"):
            raise ValueError("env must be 'live' or 'test'")

        random_part = secrets.token_urlsafe(24)[:32]
        raw_key = f"pk_{env}_{random_part}"
        key_hash = APIKeyManager.hash_key(raw_key)
        key_prefix = f"pk_{env}_"

        return raw_key, key_hash, key_prefix

    @staticmethod
    def hash_key(raw_key: str) -> str:
        """Hash API key with SHA256."""
        return hashlib.sha256(raw_key.encode()).hexdigest()

    @staticmethod
    def validate_format(key: str) -> bool:
        """Validate API key format: pk_{env}_{32_random_chars}"""
        return bool(APIKeyManager.KEY_PATTERN.match(key))

    @staticmethod
    def get_prefix(raw_key: str) -> str:
        """Extract prefix from raw key."""
        parts = raw_key.split("_")
        if len(parts) >= 2:
            return f"{parts[0]}_{parts[1]}_"
        return ""
