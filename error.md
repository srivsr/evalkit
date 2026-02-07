docker-compose logs api --tail 30
api-1 | File "/usr/local/lib/python3.11/site-packages/starlette/routing.py", line 297, in handle
api-1 | await self.app(scope, receive, send)
api-1 | File "/usr/local/lib/python3.11/site-packages/starlette/routing.py", line 77, in app
api-1 | await wrap_app_handling_exceptions(app, request)(scope, receive, send)
api-1 | File "/usr/local/lib/python3.11/site-packages/starlette/\_exception_handler.py", line 64, in wrapped_app
api-1 | raise exc
api-1 | File "/usr/local/lib/python3.11/site-packages/starlette/\_exception_handler.py", line 53, in wrapped_app
api-1 | await app(scope, receive, sender)
api-1 | File "/usr/local/lib/python3.11/site-packages/starlette/routing.py", line 72, in app
api-1 | response = await func(request)
api-1 | ^^^^^^^^^^^^^^^^^^^
api-1 | File "/usr/local/lib/python3.11/site-packages/fastapi/routing.py", line 299, in app
api-1 | raise e
api-1 | File "/usr/local/lib/python3.11/site-packages/fastapi/routing.py", line 294, in app
api-1 | raw_response = await run_endpoint_function(
api-1 | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
api-1 | File "/usr/local/lib/python3.11/site-packages/fastapi/routing.py", line 191, in run_endpoint_function
api-1 | return await dependant.call(**values)
api-1 | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
api-1 | File "/app/app/api/v1/evaluate.py", line 96, in evaluate
api-1 | return EvaluateResponse(**cached_result)
api-1 | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
api-1 | File "/usr/local/lib/python3.11/site-packages/pydantic/main.py", line 164, in **init**
api-1 | **pydantic_self**.**pydantic_validator**.validate_python(data, self_instance=**pydantic_self**)
api-1 | pydantic_core.\_pydantic_core.ValidationError: 1 validation error for EvaluateResponse
api-1 | metrics
api-1 | Input should be a valid dictionary or instance of MetricsResponse [type=model_type, input_value="faithfulness=Decimal('0....y=Decimal('0.00017325')", input_type=str]
api-1 | For further information visit https://errors.pydantic.dev/2.5/v/model_type  
api-1 | INFO: 172.19.0.1:46938 - "POST /v1/evaluate HTTP/1.1" 422 Unprocessable Entity  
api-1 | INFO: 172.19.0.1:34966 - "POST /v1/evaluate HTTP/1.1" 422 Unprocessable Entity
