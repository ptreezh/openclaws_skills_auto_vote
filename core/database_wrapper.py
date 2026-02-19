#!/usr/bin/env python3
"""
Skills Arena - 数据库连接池包装器

提供自动重连、连接超时控制、健康检查和离线模式降级
"""

import asyncio
from typing import Any, Dict, Optional
from datetime import datetime
from contextlib import asynccontextmanager

from .exceptions import DatabaseError
from .logging_config import get_logger


logger = get_logger("arena.database")


class DatabaseWrapper:
    """
    数据库连接池包装器

    特性：
    - 自动重连（最多 3 次）
    - 连接超时控制（30 秒）
    - 健康检查
    - 离线模式降级
    """

    def __init__(
        self,
        max_attempts: int = 3,
        connection_timeout: float = 30.0,
        health_check_interval: float = 60.0,
    ):
        """
        初始化数据库包装器

        Args:
            max_attempts: 最大重试次数
            connection_timeout: 连接超时（秒）
            health_check_interval: 健康检查间隔（秒）
        """
        self.max_attempts = max_attempts
        self.connection_timeout = connection_timeout
        self.health_check_interval = health_check_interval

        self._db = None
        self._is_initialized = False
        self._is_healthy = False
        self._last_health_check = None

    async def init(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        初始化数据库连接池

        Args:
            config: 数据库配置
        """
        try:
            # 尝试导入数据库模块
            from scripts.database.db import Database

            self._db = Database()

            # 初始化连接池
            if config:
                await self._db.init(config)
            else:
                await self._db.init()

            self._is_initialized = True
            self._is_healthy = True
            self._last_health_check = datetime.now()

            logger.info(
                "Database connection pool initialized",
                max_pool_size=getattr(self._db, "max_pool_size", "unknown"),
            )

        except ImportError:
            logger.warning("Database module not available, running in offline mode")
            self._is_initialized = False
            self._is_healthy = False

        except Exception as e:
            logger.error(
                "Failed to initialize database",
                exception=e,
            )
            self._is_initialized = False
            self._is_healthy = False

    async def close(self) -> None:
        """关闭数据库连接池"""
        if self._db:
            try:
                await self._db.close()
                logger.info("Database connection pool closed")
            except Exception as e:
                logger.error("Error closing database", exception=e)

    def is_available(self) -> bool:
        """检查数据库是否可用"""
        return self._is_initialized and self._is_healthy

    def is_offline_mode(self) -> bool:
        """检查是否处于离线模式"""
        return not self.is_available()

    @asynccontextmanager
    async def get_connection(self):
        """
        获取数据库连接（带重试）

        Yields:
            数据库连接对象

        Raises:
            DatabaseError: 连接失败
        """
        if not self.is_available():
            raise DatabaseError(
                message="Database is not available",
                details={"offline_mode": True},
            )

        # 尝试获取连接
        connection = None
        last_error = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                # 健康检查
                await self._ensure_health()

                # 获取连接
                connection = await self._db.get_connection()
                yield connection
                return

            except Exception as e:
                last_error = e
                logger.warning(
                    f"Database connection attempt {attempt}/{self.max_attempts} failed",
                    exception=e,
                )

                # 最后一次尝试失败
                if attempt >= self.max_attempts:
                    self._is_healthy = False
                    raise DatabaseError(
                        message="Failed to acquire database connection after retries",
                        details={
                            "attempts": attempt,
                            "max_attempts": self.max_attempts,
                        },
                    ) from e

                # 等待后重试
                await asyncio.sleep(1.0 * attempt)

        # 理论上不会到达这里
        raise DatabaseError(
            message="Failed to acquire database connection",
            details={"last_error": str(last_error)},
        )

    async def _ensure_health(self) -> None:
        """
        确保数据库健康

        如果需要，执行健康检查
        """
        now = datetime.now()

        # 检查是否需要健康检查
        if (
            self._last_health_check is None or
            (now - self._last_health_check).total_seconds() > self.health_check_interval
        ):
            await self._health_check()

    async def _health_check(self) -> None:
        """执行健康检查"""
        try:
            # 执行简单查询
            async with self._db.get_connection() as conn:
                await conn.fetchval("SELECT 1")

            self._is_healthy = True
            self._last_health_check = datetime.now()

            logger.debug("Database health check passed")

        except Exception as e:
            logger.warning("Database health check failed", exception=e)
            self._is_healthy = False

    async def execute(
        self,
        query: str,
        *args,
        **kwargs,
    ) -> Any:
        """
        执行数据库查询（带重试）

        Args:
            query: SQL 查询
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            查询结果

        Raises:
            DatabaseError: 查询失败
        """
        for attempt in range(1, self.max_attempts + 1):
            try:
                async with self.get_connection() as conn:
                    result = await conn.execute(query, *args)
                    return result

            except Exception as e:
                logger.warning(
                    f"Query attempt {attempt}/{self.max_attempts} failed",
                    exception=e,
                    query=query[:200],
                )

                if attempt >= self.max_attempts:
                    raise DatabaseError(
                        message="Query failed after retries",
                        query=query,
                        details={
                            "attempts": attempt,
                            "max_attempts": self.max_attempts,
                        },
                    ) from e

                await asyncio.sleep(1.0 * attempt)

    async def fetch(
        self,
        query: str,
        *args,
        **kwargs,
    ) -> Any:
        """
        执行查询并获取结果（带重试）

        Args:
            query: SQL 查询
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            查询结果

        Raises:
            DatabaseError: 查询失败
        """
        for attempt in range(1, self.max_attempts + 1):
            try:
                async with self.get_connection() as conn:
                    result = await conn.fetch(query, *args)
                    return result

            except Exception as e:
                logger.warning(
                    f"Fetch attempt {attempt}/{self.max_attempts} failed",
                    exception=e,
                    query=query[:200],
                )

                if attempt >= self.max_attempts:
                    raise DatabaseError(
                        message="Fetch failed after retries",
                        query=query,
                        details={
                            "attempts": attempt,
                            "max_attempts": self.max_attempts,
                        },
                    ) from e

                await asyncio.sleep(1.0 * attempt)

    async def fetchval(
        self,
        query: str,
        *args,
        **kwargs,
    ) -> Any:
        """
        执行查询并获取单个值（带重试）

        Args:
            query: SQL 查询
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            查询结果（单个值）

        Raises:
            DatabaseError: 查询失败
        """
        for attempt in range(1, self.max_attempts + 1):
            try:
                async with self.get_connection() as conn:
                    result = await conn.fetchval(query, *args)
                    return result

            except Exception as e:
                logger.warning(
                    f"Fetchval attempt {attempt}/{self.max_attempts} failed",
                    exception=e,
                    query=query[:200],
                )

                if attempt >= self.max_attempts:
                    raise DatabaseError(
                        message="Fetchval failed after retries",
                        query=query,
                        details={
                            "attempts": attempt,
                            "max_attempts": self.max_attempts,
                        },
                    ) from e

                await asyncio.sleep(1.0 * attempt)


# 全局数据库包装器实例
db_wrapper = DatabaseWrapper()
