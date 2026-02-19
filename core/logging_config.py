#!/usr/bin/env python3
"""
Skills Arena - 统一日志系统

提供结构化日志记录，支持 JSON 格式、文件轮转、上下文信息
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
from contextlib import contextmanager
import traceback


class JSONFormatter(logging.Formatter):
    """
    JSON 格式化器

    输出结构化 JSON 日志，便于日志解析和分析
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        格式化日志记录为 JSON

        Args:
            record: 日志记录

        Returns:
            JSON 字符串
        """
        # 基础日志信息
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 添加自定义字段
        if hasattr(record, "context"):
            log_data["context"] = record.context

        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        return json.dumps(log_data, ensure_ascii=False)


class ArenaLogger:
    """
    Skills Arena 统一日志记录器

    特性：
    - 结构化 JSON 日志
    - 文件和控制台双输出
    - 自动记录异常堆栈
    - 支持上下文信息传递
    """

    def __init__(
        self,
        name: str = "arena",
        log_dir: Optional[Path] = None,
        log_level: int = logging.INFO,
        enable_json: bool = True,
    ):
        """
        初始化日志记录器

        Args:
            name: 日志记录器名称
            log_dir: 日志文件目录
            log_level: 日志级别
            enable_json: 是否使用 JSON 格式
        """
        self.name = name
        self.log_dir = log_dir
        self.enable_json = enable_json

        # 创建日志记录器
        self.logger = logging.getLogger(name)
        self.logger.setLevel(log_level)
        self.logger.handlers.clear()  # 清除现有处理器

        # 创建格式化器
        if enable_json:
            formatter = JSONFormatter()
        else:
            formatter = logging.Formatter(
                fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )

        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # 文件处理器（如果指定了目录）
        if log_dir:
            log_dir.mkdir(parents=True, exist_ok=True)

            # 主日志文件
            main_log = log_dir / f"{name}.log"
            file_handler = logging.FileHandler(main_log, encoding="utf-8")
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)

            # 错误日志文件
            error_log = log_dir / f"{name}-error.log"
            error_handler = logging.FileHandler(error_log, encoding="utf-8")
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(formatter)
            self.logger.addHandler(error_handler)

    def _log(
        self,
        level: int,
        message: str,
        exception: Optional[Exception] = None,
        **kwargs,
    ) -> None:
        """
        内部日志记录方法

        Args:
            level: 日志级别
            message: 日志消息
            exception: 异常对象
            **kwargs: 上下文信息
        """
        # 准备额外信息
        extra = {}
        if kwargs:
            extra["context"] = kwargs

        # 记录日志
        if exception:
            self.logger.log(
                level,
                message,
                exc_info=(type(exception), exception, exception.__traceback__),
                extra=extra,
            )
        else:
            self.logger.log(level, message, extra=extra)

    def debug(self, message: str, **kwargs) -> None:
        """记录 DEBUG 级别日志"""
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        """记录 INFO 级别日志"""
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """记录 WARNING 级别日志"""
        self._log(logging.WARNING, message, **kwargs)

    def error(
        self,
        message: str,
        exception: Optional[Exception] = None,
        **kwargs,
    ) -> None:
        """记录 ERROR 级别日志"""
        self._log(logging.ERROR, message, exception=exception, **kwargs)

    def critical(
        self,
        message: str,
        exception: Optional[Exception] = None,
        **kwargs,
    ) -> None:
        """记录 CRITICAL 级别日志"""
        self._log(logging.CRITICAL, message, exception=exception, **kwargs)

    @contextmanager
    def log_context(self, **kwargs):
        """
        日志上下文管理器

        Args:
            **kwargs: 上下文信息

        Examples:
            >>> with logger.log_context(user_id="123", action="upload"):
            ...     logger.info("Processing upload")
        """
        # 保存旧的上下文（如果需要嵌套）
        old_context = getattr(self.logger, "context", {})
        self.logger.context = {**old_context, **kwargs}

        try:
            yield self
        finally:
            # 恢复旧上下文
            self.logger.context = old_context


# 全局日志记录器实例
_loggers: Dict[str, ArenaLogger] = {}


def get_logger(
    name: str = "arena",
    log_dir: Optional[Path] = None,
    log_level: int = logging.INFO,
    enable_json: bool = True,
) -> ArenaLogger:
    """
    获取日志记录器实例（单例模式）

    Args:
        name: 日志记录器名称
        log_dir: 日志文件目录
        log_level: 日志级别
        enable_json: 是否使用 JSON 格式

    Returns:
        ArenaLogger 实例
    """
    if name not in _loggers:
        _loggers[name] = ArenaLogger(
            name=name,
            log_dir=log_dir,
            log_level=log_level,
            enable_json=enable_json,
        )
    return _loggers[name]


def setup_logging(
    log_dir: Optional[Path] = None,
    log_level: int = logging.INFO,
    enable_json: bool = True,
) -> None:
    """
    设置全局日志配置

    Args:
        log_dir: 日志文件目录
        log_level: 日志级别
        enable_json: 是否使用 JSON 格式
    """
    # 创建默认日志目录
    if log_dir is None:
        base_dir = Path(__file__).parent.parent
        log_dir = base_dir / "logs"

    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 清除现有处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 创建默认日志记录器
    get_logger(
        name="arena",
        log_dir=log_dir,
        log_level=log_level,
        enable_json=enable_json,
    )
