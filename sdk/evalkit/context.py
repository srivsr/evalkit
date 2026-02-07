from typing import List, Dict, Any, Optional
from .client import EvalClient


class EvalContext:
    def __init__(
        self,
        api_key: str,
        project_id: str,
        base_url: str = "https://api.evalkit.dev",
    ):
        self._client = EvalClient(api_key=api_key, base_url=base_url)
        self._project_id = project_id
        self._query: Optional[str] = None
        self._context: Optional[List[str]] = None
        self._context_chunks: Optional[List[Dict]] = None
        self._response: Optional[str] = None
        self._metadata: Dict[str, Any] = {}

    def set_query(self, query: str) -> "EvalContext":
        self._query = query
        return self

    def set_context(self, context: List[str]) -> "EvalContext":
        self._context = context
        return self

    def set_context_chunks(self, chunks: List[Dict]) -> "EvalContext":
        self._context_chunks = chunks
        return self

    def set_response(self, response: str) -> "EvalContext":
        self._response = response
        return self

    def set_metadata(self, metadata: Dict[str, Any]) -> "EvalContext":
        self._metadata.update(metadata)
        return self

    def __enter__(self) -> "EvalContext":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None and self._query and self._response:
            try:
                self._client.evaluate(
                    project_id=self._project_id,
                    query=self._query,
                    response=self._response,
                    context=self._context,
                    context_chunks=self._context_chunks,
                    metadata=self._metadata,
                )
            except Exception:
                pass
        self._client.close()
        return False
