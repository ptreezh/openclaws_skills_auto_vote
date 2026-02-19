#!/usr/bin/env python3
"""
Skills Arena - FastAPI 错误处理中间件

提供统一的异常处理机制，将自定义异常转换为标准 HTTP 响应
"""

from typing import Any, Dict, Union
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .exceptions import ArenaException
from .logging_config import get_logger


logger = get_logger("arena.error_handler")


async def arena_exception_handler(
    request: Request,
    exc: ArenaException,
) -> JSONResponse:
    """
    处理 ArenaException 及其子类

    Args:
        request: 请求对象
        exc: ArenaException 异常

    Returns:
        标准化的 JSON 错误响应
    """
    # 记录错误日志
    logger.error(
        f"[{exc.error_code}] {exc.message}",
        exception=exc,
        path=request.url.path,
        method=request.method,
    )

    # 返回标准响应
    return JSONResponse(
        status_code=exc.http_status,
        content=exc.to_dict(),
    )


async def validation_exception_handler(
    request: Request,
    exc: Union[RequestValidationError, ValidationError],
) -> JSONResponse:
    """
    处理 Pydantic 验证错误

    Args:
        request: 请求对象
        exc: 验证错误

    Returns:
        标准化的 JSON 错误响应
    """
    # 提取验证错误详情
    errors = []
    if isinstance(exc, RequestValidationError):
        errors = exc.errors()
    else:
        errors = exc.errors()

    # 格式化错误消息
    formatted_errors = []
    for error in errors:
        formatted_errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        })

    # 记录警告
    logger.warning(
        "Validation failed",
        path=request.url.path,
        method=request.method,
        errors=formatted_errors,
    )

    # 返回响应
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "error": {
                "code": "ARENA_VALIDATION",
                "message": "Request validation failed",
                "details": {
                    "errors": formatted_errors,
                },
                "timestamp": exc.body.get("timestamp") if isinstance(exc, RequestValidationError) else None,
            }
        },
    )


async def http_exception_handler(
    request: Request,
    exc: Union[HTTPException, StarletteHTTPException],
) -> JSONResponse:
    """
    处理 HTTPException

    Args:
        request: 请求对象
        exc: HTTPException 异常

    Returns:
        标准化的 JSON 错误响应
    """
    # 记录错误
    logger.warning(
        f"HTTP {exc.status_code}: {exc.detail}",
        path=request.url.path,
        method=request.method,
    )

    # 返回响应
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": f"ARENA_HTTP_{exc.status_code}",
                "message": str(exc.detail),
                "details": {},
                "timestamp": None,
            }
        },
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """
    处理所有未捕获的异常

    Args:
        request: 请求对象
        exc: 未捕获的异常

    Returns:
        标准化的 JSON 错误响应
    """
    # 记录严重错误
    logger.critical(
        f"Unhandled exception: {type(exc).__name__}",
        exception=exc,
        path=request.url.path,
        method=request.method,
    )

    # 返回通用错误响应（不泄露内部错误详情）
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "ARENA_INTERNAL_ERROR",
                "message": "An internal server error occurred",
                "details": {
                    "type": type(exc).__name__,
                },
                "timestamp": None,
            }
        },
    )


def setup_error_handlers(app) -> None:
    """
    为 FastAPI 应用设置所有异常处理器

    Args:
        app: FastAPI 应用实例

    Examples:
        >>> from fastapi import FastAPI
        >>> app = FastAPI()
        >>> setup_error_handlers(app)
    """
    from fastapi.exceptions import RequestValidationError

    # ArenaException 处理器
    app.add_exception_handler(ArenaException, arena_exception_handler)

    # Pydantic 验证错误处理器
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)

    # HTTPException 处理器
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)

    # 通用异常处理器
    app.add_exception_handler(Exception, generic_exception_handler)

    logger.info("Error handlers registered")
