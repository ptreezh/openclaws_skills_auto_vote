#!/usr/bin/env python3
"""
Skills Arena - 重试机制

提供同步和异步重试装饰器，支持指数退避
"""

import asyncio
import functools
from typing import Any, Callable, Optional, Type, Tuple
from .logging_config import get_logger


logger = get_logger("arena.retry")


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
    """
    同步重试装饰器

    Args:
        max_attempts: 最大尝试次数
        delay: 初始延迟（秒）
        backoff: 退避因子（每次重试延迟乘以该因子）
        exceptions: 需要重试的异常类型

    Returns:
        装饰器函数

    Examples:
        >>> @retry(max_attempts=3, delay=1.0, backoff=2.0)
        >>> def unstable_operation():
        ...     # 可能失败的操作
        ...     pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)

                except exceptions as e:
                    last_exception = e

                    if attempt >= max_attempts:
                        logger.error(
                            f"Function {func.__name__} failed after {max_attempts} attempts",
                            exception=e,
                        )
                        raise

                    logger.warning(
                        f"Function {func.__name__} attempt {attempt}/{max_attempts} failed, retrying in {current_delay}s",
                        exception=e,
                    )

                    # 等待后重试
                    import time
                    time.sleep(current_delay)
                    current_delay *= backoff

            # 理论上不会到达这里
            raise last_exception

        return wrapper
    return decorator


def retry_async(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
    """
    异步重试装饰器

    Args:
        max_attempts: 最大尝试次数
        delay: 初始延迟（秒）
        backoff: 退避因子（每次重试延迟乘以该因子）
        exceptions: 需要重试的异常类型

    Returns:
        装饰器函数

    Examples:
        >>> @retry_async(max_attempts=3, delay=1.0, backoff=2.0)
        >>> async def unstable_async_operation():
        ...     # 可能失败的异步操作
        ...     pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)

                except exceptions as e:
                    last_exception = e

                    if attempt >= max_attempts:
                        logger.error(
                            f"Async function {func.__name__} failed after {max_attempts} attempts",
                            exception=e,
                        )
                        raise

                    logger.warning(
                        f"Async function {func.__name__} attempt {attempt}/{max_attempts} failed, retrying in {current_delay}s",
                        exception=e,
                    )

                    # 等待后重试
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff

            # 理论上不会到达这里
            raise last_exception

        return wrapper
    return decorator


def retry_on_exception(
    exception_type: Type[Exception],
    max_attempts: int = 3,
):
    """
    针对特定异常的重试装饰器（简化版）

    Args:
        exception_type: 需要重试的异常类型
        max_attempts: 最大尝试次数

    Returns:
        装饰器函数

    Examples:
        >>> @retry_on_exception(ConnectionError, max_attempts=5)
        >>> def fetch_data():
        ...     # 可能因连接问题失败的操作
        ...     pass
    """
    return retry(max_attempts=max_attempts, exceptions=(exception_type,))


def retry_async_on_exception(
    exception_type: Type[Exception],
    max_attempts: int = 3,
):
    """
    针对特定异常的异步重试装饰器（简化版）

    Args:
        exception_type: 需要重试的异常类型
        max_attempts: 最大尝试次数

    Returns:
        装饰器函数

    Examples:
        >>> @retry_async_on_exception(asyncio.TimeoutError, max_attempts=5)
        >>> async def fetch_async_data():
        ...     # 可能因超时失败的异步操作
        ...     pass
    """
    return retry_async(max_attempts=max_attempts, exceptions=(exception_type,))
