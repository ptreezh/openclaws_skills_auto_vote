#!/usr/bin/env python3
"""
Skills Arena - Flask 错误处理装饰器

为 Flask 路由提供统一的错误处理机制
"""

from functools import wraps
from typing import Any, Callable, Dict, Union
from flask import jsonify, request

from .exceptions import ArenaException
from .logging_config import get_logger


logger = get_logger("arena.error_handler")


def handle_errors(f: Callable) -> Callable:
    """
    Flask 路由错误处理装饰器

    自动捕获异常并转换为标准 JSON 响应

    Args:
        f: Flask 路由函数

    Returns:
        包装后的路由函数

    Examples:
        >>> @app.route("/api/skills", methods=["POST"])
        >>> @handle_errors
        >>> def create_skill():
        ...     # 路由逻辑
        ...     pass
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            # 执行路由函数
            result = f(*args, **kwargs)

            # 如果是 ArenaException，直接转换
            if isinstance(result, ArenaException):
                return _convert_arena_exception(
                    result,
                    request.path,
                    request.method
                )

            return result

        except ArenaException as e:
            # 处理 ArenaException
            return _convert_arena_exception(e, request.path, request.method)

        except Exception as e:
            # 处理未捕获的异常
            return _convert_generic_exception(e, request.path, request.method)

    return wrapper


def _convert_arena_exception(
    exc: ArenaException,
    path: str,
    method: str,
) -> tuple:
    """
    将 ArenaException 转换为 Flask 响应

    Args:
        exc: ArenaException 异常
        path: 请求路径
        method: 请求方法

    Returns:
        (响应字典, HTTP状态码)
    """
    # 记录错误日志
    logger.error(
        f"[{exc.error_code}] {exc.message}",
        exception=exc,
        path=path,
        method=method,
    )

    # 返回 JSON 响应
    return jsonify(exc.to_dict()), exc.http_status


def _convert_generic_exception(
    exc: Exception,
    path: str,
    method: str,
) -> tuple:
    """
    将普通异常转换为 Flask 响应

    Args:
        exc: 普通异常
        path: 请求路径
        method: 请求方法

    Returns:
        (响应字典, HTTP状态码)
    """
    # 记录严重错误
    logger.critical(
        f"Unhandled exception: {type(exc).__name__}",
        exception=exc,
        path=path,
        method=method,
    )

    # 返回通用错误响应
    error_response = {
        "success": False,
        "error": {
            "code": "ARENA_INTERNAL_ERROR",
            "message": "An internal server error occurred",
            "details": {
                "type": type(exc).__name__,
            },
            "timestamp": None,
        }
    }

    return jsonify(error_response), 500


def register_flask_error_handlers(app) -> None:
    """
    为 Flask 应用注册全局错误处理器

    Args:
        app: Flask 应用实例

    Examples:
        >>> from flask import Flask
        >>> app = Flask(__name__)
        >>> register_flask_error_handlers(app)
    """
    from werkzeug.exceptions import HTTPException

    @app.errorhandler(ArenaException)
    def handle_arena_exception(exc: ArenaException):
        """处理 ArenaException"""
        return _convert_arena_exception(exc, request.path, request.method)

    @app.errorhandler(HTTPException)
    def handle_http_exception(exc: HTTPException):
        """处理 HTTPException"""
        logger.warning(
            f"HTTP {exc.code}: {exc.description}",
            path=request.path,
            method=request.method,
        )

        response = {
            "success": False,
            "error": {
                "code": f"ARENA_HTTP_{exc.code}",
                "message": str(exc.description),
                "details": {},
                "timestamp": None,
            }
        }

        return jsonify(response), exc.code

    @app.errorhandler(Exception)
    def handle_generic_exception(exc: Exception):
        """处理所有未捕获的异常"""
        return _convert_generic_exception(exc, request.path, request.method)

    logger.info("Flask error handlers registered")
