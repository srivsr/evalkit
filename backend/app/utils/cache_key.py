import hashlib
import json
from typing import List, Tuple
from ..schemas import ContextChunk


def generate_cache_key(
    query: str,
    context_chunks: List[ContextChunk],
    response: str,
    policy_version: int,
    judge_model: str = "gpt-4o-mini",
    evaluator_version: str = "3"
) -> Tuple[str, str, str]:
    cache_namespace = f"schema_v1|eval_v{evaluator_version}|policy_{policy_version}|judge_{judge_model}"

    data = {
        "query": query,
        "context_chunks": [c.model_dump() for c in context_chunks],
        "response": response
    }

    input_hash = hashlib.sha256(
        json.dumps(data, sort_keys=True, default=str).encode()
    ).hexdigest()

    cache_key = f"eval:{cache_namespace}:{input_hash}"
    return cache_key, input_hash, cache_namespace
