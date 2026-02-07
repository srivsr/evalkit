from typing import Callable, Any, Optional, Dict
from functools import wraps
from .client import EvalClient


def observe(
    api_key: str,
    project_id: str,
    extract_context: Optional[Callable[[Any], Any]] = None,
    extract_response: Optional[Callable[[Any], str]] = None,
    extract_query: Optional[Callable[[tuple, dict], str]] = None,
    base_url: str = "https://api.evalkit.dev",
    async_mode: bool = True,
):
    def decorator(func: Callable) -> Callable:
        client = EvalClient(api_key=api_key, base_url=base_url)

        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            if extract_query:
                query = extract_query(args, kwargs)
            else:
                query = args[0] if args else kwargs.get("query", "")

            if extract_response:
                response = extract_response(result)
            elif isinstance(result, dict):
                response = result.get("response", str(result))
            else:
                response = str(result)

            if extract_context:
                context_data = extract_context(result)
                if isinstance(context_data, list) and context_data:
                    if isinstance(context_data[0], dict):
                        context_chunks = context_data
                        context = None
                    else:
                        context = context_data
                        context_chunks = None
                else:
                    context = None
                    context_chunks = None
            else:
                context = None
                context_chunks = None

            try:
                client.evaluate(
                    project_id=project_id,
                    query=query,
                    response=response,
                    context=context,
                    context_chunks=context_chunks,
                )
            except Exception:
                pass

            return result

        return wrapper

    return decorator
