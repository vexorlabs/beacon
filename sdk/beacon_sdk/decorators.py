from __future__ import annotations

import functools
import inspect
from typing import Any, Callable, TypeVar, overload

from beacon_sdk.models import SpanStatus, SpanType

F = TypeVar("F", bound=Callable[..., Any])


@overload
def observe(func: F) -> F: ...


@overload
def observe(
    *,
    name: str | None = None,
    span_type: str | SpanType = SpanType.CUSTOM,
) -> Callable[[F], F]: ...


def observe(
    func: F | None = None,
    *,
    name: str | None = None,
    span_type: str | SpanType = SpanType.CUSTOM,
) -> F | Callable[[F], F]:
    """Decorator that wraps a function in a Beacon span.

    Usage:
        @observe
        def my_func(): ...

        @observe(name="custom name", span_type="agent_step")
        def my_func(): ...

        @observe
        async def my_async_func(): ...
    """

    def decorator(fn: F) -> F:
        resolved_name = name or fn.__qualname__
        resolved_type = (
            SpanType(span_type) if isinstance(span_type, str) else span_type
        )

        if inspect.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                from beacon_sdk import _get_tracer

                tracer = _get_tracer()
                if tracer is None:
                    return await fn(*args, **kwargs)

                span, token = tracer.start_span(
                    name=resolved_name, span_type=resolved_type
                )
                try:
                    result = await fn(*args, **kwargs)
                    tracer.end_span(span, token, status=SpanStatus.OK)
                    return result
                except Exception as exc:
                    tracer.end_span(
                        span,
                        token,
                        status=SpanStatus.ERROR,
                        error_message=str(exc),
                    )
                    raise

            return async_wrapper  # type: ignore[return-value]
        else:

            @functools.wraps(fn)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                from beacon_sdk import _get_tracer

                tracer = _get_tracer()
                if tracer is None:
                    return fn(*args, **kwargs)

                span, token = tracer.start_span(
                    name=resolved_name, span_type=resolved_type
                )
                try:
                    result = fn(*args, **kwargs)
                    tracer.end_span(span, token, status=SpanStatus.OK)
                    return result
                except Exception as exc:
                    tracer.end_span(
                        span,
                        token,
                        status=SpanStatus.ERROR,
                        error_message=str(exc),
                    )
                    raise

            return sync_wrapper  # type: ignore[return-value]

    if func is not None:
        return decorator(func)

    return decorator  # type: ignore[return-value]
