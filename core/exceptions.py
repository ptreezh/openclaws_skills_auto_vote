#!/usr/bin/env python3
"""
Skills Arena - 自定义异常类体系

提供统一的异常处理框架，支持错误码、结构化响应和国际化
"""

from typing import Any, Dict, Optional
from datetime import datetime


class ArenaException(Exception):
    """
    基类：所有自定义异常的父类

    特性：
    - 支持错误码
    - 支持结构化详情
    - 可转换为 API 响应
    - 可转换为 HTTPException
    """

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        http_status: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self._default_error_code()
        self.http_status = http_status
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()

    def _default_error_code(self) -> str:
        """生成默认错误码"""
        class_name = self.__class__.__name__
        # 移除 Error 后缀并转为大写
        base = class_name.replace("Error", "").upper()
        return f"ARENA_{base}"

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式（用于 API 响应）

        Returns:
            标准化的错误响应字典
        """
        return {
            "success": False,
            "error": {
                "code": self.error_code,
                "message": self.message,
                "details": self.details,
                "timestamp": self.timestamp,
            }
        }

    def to_fastapi_response(self):
        """
        转换为 FastAPI HTTPException

        Returns:
            HTTPException 对象
        """
        from fastapi import HTTPException

        return HTTPException(
            status_code=self.http_status,
            detail={
                "code": self.error_code,
                "message": self.message,
                "details": self.details,
            },
        )

    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(code={self.error_code}, message={self.message!r})"


# ==================== 业务异常子类 ====================


class ValidationError(ArenaException):
    """
    验证错误（400 Bad Request）

    用于：
    - 参数验证失败
    - 数据格式错误
    - 业务规则验证失败
    """

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        full_details = details or {}
        if field:
            full_details["field"] = field

        super().__init__(
            message=message,
            error_code="ARENA_VALIDATION",
            http_status=400,
            details=full_details,
        )


class SkillNotFoundError(ArenaException):
    """
    Skill 不存在（404 Not Found）

    用于：
    - 查询的 Skill ID 不存在
    - Skill 文件丢失
    """

    def __init__(
        self,
        skill_id: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        full_details = details or {}
        full_details["skill_id"] = skill_id

        super().__init__(
            message=f"Skill not found: {skill_id}",
            error_code="ARENA_SKILL_NOT_FOUND",
            http_status=404,
            details=full_details,
        )


class AgentNotFoundError(ArenaException):
    """
    Agent 不存在（404 Not Found）

    用于：
    - 查询的 Agent DID 不存在
    - Agent 未注册
    """

    def __init__(
        self,
        agent_did: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        full_details = details or {}
        full_details["agent_did"] = agent_did

        super().__init__(
            message=f"Agent not found: {agent_did}",
            error_code="ARENA_AGENT_NOT_FOUND",
            http_status=404,
            details=full_details,
        )


class PermissionDeniedError(ArenaException):
    """
    权限不足（403 Forbidden）

    用于：
    - 用户无权访问资源
    - 操作权限不足
    """

    def __init__(
        self,
        message: str = "Permission denied",
        required_permission: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        full_details = details or {}
        if required_permission:
            full_details["required_permission"] = required_permission

        super().__init__(
            message=message,
            error_code="ARENA_PERMISSION_DENIED",
            http_status=403,
            details=full_details,
        )


class AuthenticationError(ArenaException):
    """
    认证失败（401 Unauthorized）

    用于：
    - Token 无效
    - 认证信息缺失
    - DID 验证失败
    """

    def __init__(
        self,
        message: str = "Authentication failed",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="ARENA_AUTHENTICATION",
            http_status=401,
            details=details,
        )


class DatabaseError(ArenaException):
    """
    数据库错误（503 Service Unavailable）

    用于：
    - 数据库连接失败
    - 查询执行失败
    - 事务回滚
    """

    def __init__(
        self,
        message: str,
        query: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        full_details = details or {}
        if query:
            # 截断过长的查询语句
            full_details["query"] = query[:200] if len(query) > 200 else query

        super().__init__(
            message=message,
            error_code="ARENA_DATABASE",
            http_status=503,
            details=full_details,
        )


class FileOperationError(ArenaException):
    """
    文件操作错误（500 Internal Server Error）

    用于：
    - 文件读取失败
    - 文件写入失败
    - 文件格式错误
    """

    def __init__(
        self,
        message: str,
        file_path: Optional[str] = None,
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        full_details = details or {}
        if file_path:
            full_details["file_path"] = file_path
        if operation:
            full_details["operation"] = operation

        super().__init__(
            message=message,
            error_code="ARENA_FILE_OPERATION",
            http_status=500,
            details=full_details,
        )


class UploadError(ArenaException):
    """
    上传错误（400 Bad Request）

    用于：
    - 文件格式不支持
    - 文件大小超限
    - 上传验证失败
    """

    def __init__(
        self,
        message: str,
        file_name: Optional[str] = None,
        reason: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        full_details = details or {}
        if file_name:
            full_details["file_name"] = file_name
        if reason:
            full_details["reason"] = reason

        super().__init__(
            message=message,
            error_code="ARENA_UPLOAD",
            http_status=400,
            details=full_details,
        )


class VersionConflictError(ArenaException):
    """
    版本冲突（409 Conflict）

    用于：
    - 同名同版本已存在
    - 版本号格式错误
    """

    def __init__(
        self,
        skill_name: str,
        version: str,
        existing_skill_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        full_details = details or {}
        full_details["skill_name"] = skill_name
        full_details["version"] = version
        if existing_skill_id:
            full_details["existing_skill_id"] = existing_skill_id

        super().__init__(
            message=f"Version conflict: {skill_name} v{version} already exists",
            error_code="ARENA_VERSION_CONFLICT",
            http_status=409,
            details=full_details,
        )


class ReviewPermissionError(ArenaException):
    """
    评价权限错误（403 Forbidden）

    用于：
    - 使用次数不足
    - 未使用过该 Skill
    - 重复评价
    """

    def __init__(
        self,
        message: str,
        skill_id: Optional[str] = None,
        current_usage: Optional[int] = None,
        required_usage: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        full_details = details or {}
        if skill_id:
            full_details["skill_id"] = skill_id
        if current_usage is not None:
            full_details["current_usage"] = current_usage
        if required_usage is not None:
            full_details["required_usage"] = required_usage

        super().__init__(
            message=message,
            error_code="ARENA_REVIEW_PERMISSION",
            http_status=403,
            details=full_details,
        )


class VoteError(ArenaException):
    """
    投票错误（400 Bad Request）

    用于：
    - 无效的投票类型
    - 重复投票
    - 投票权限不足
    """

    def __init__(
        self,
        message: str,
        vote_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        full_details = details or {}
        if vote_type:
            full_details["vote_type"] = vote_type

        super().__init__(
            message=message,
            error_code="ARENA_VOTE",
            http_status=400,
            details=full_details,
        )


class CommentError(ArenaException):
    """
    评论错误（400 Bad Request）

    用于：
    - 评论内容为空
    - 父评论不存在
    - 评论权限不足
    """

    def __init__(
        self,
        message: str,
        comment_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        full_details = details or {}
        if comment_id:
            full_details["comment_id"] = comment_id

        super().__init__(
            message=message,
            error_code="ARENA_COMMENT",
            http_status=400,
            details=full_details,
        )
