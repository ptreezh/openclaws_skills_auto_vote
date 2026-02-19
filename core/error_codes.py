#!/usr/bin/env python3
"""
Skills Arena - 错误码注册表

错误码格式: ARENA_XX_YYYY
- XX: 模块代码 (00=通用, 01=Skill, 02=Agent, 03=投票, 04=评论, 05=上传, 06=验证, 07=数据库)
- YYYY: 具体错误编号

支持多语言消息扩展
"""

from typing import Dict, Optional
from enum import Enum


class ErrorCodes(str, Enum):
    """
    错误码枚举

    格式: ARENA_XX_YYYY
    - XX: 模块代码
    - YYYY: 错误编号
    """

    # ==================== 通用错误 (00) ====================
    UNKNOWN = "ARENA_00_0001"
    INTERNAL_ERROR = "ARENA_00_0002"
    INVALID_REQUEST = "ARENA_00_0003"
    METHOD_NOT_ALLOWED = "ARENA_00_0004"
    RATE_LIMIT_EXCEEDED = "ARENA_00_0005"

    # ==================== Skill 错误 (01) ====================
    SKILL_NOT_FOUND = "ARENA_01_0001"
    SKILL_ALREADY_EXISTS = "ARENA_01_0002"
    SKILL_INVALID_FORMAT = "ARENA_01_0003"
    SKILL_VALIDATION_FAILED = "ARENA_01_0004"
    SKILL_MD_MISSING = "ARENA_01_0005"
    SKILL_MD_INVALID = "ARENA_01_0006"
    SKILL_NAME_MISSING = "ARENA_01_0007"
    SKILL_VERSION_INVALID = "ARENA_01_0008"
    SKILL_VERSION_CONFLICT = "ARENA_01_0009"
    SKILL_UPLOAD_FAILED = "ARENA_01_0010"
    SKILL_DOWNLOAD_FAILED = "ARENA_01_0011"
    SKILL_DELETE_FAILED = "ARENA_01_0012"

    # ==================== Agent 错误 (02) ====================
    AGENT_NOT_FOUND = "ARENA_02_0001"
    AGENT_ALREADY_EXISTS = "ARENA_02_0002"
    AGENT_INVALID_DID = "ARENA_02_0003"
    AGENT_AUTHENTICATION_FAILED = "ARENA_02_0004"
    AGENT_PERMISSION_DENIED = "ARENA_02_0005"

    # ==================== 投票错误 (03) ====================
    VOTE_TYPE_INVALID = "ARENA_03_0001"
    VOTE_ALREADY_CAST = "ARENA_03_0002"
    VOTE_TARGET_NOT_FOUND = "ARENA_03_0003"
    VOTE_PERMISSION_DENIED = "ARENA_03_0004"

    # ==================== 评论错误 (04) ====================
    COMMENT_EMPTY = "ARENA_04_0001"
    COMMENT_NOT_FOUND = "ARENA_04_0002"
    COMMENT_PARENT_NOT_FOUND = "ARENA_04_0003"
    COMMENT_PERMISSION_DENIED = "ARENA_04_0004"
    COMMENT_TOO_LONG = "ARENA_04_0005"

    # ==================== 上传错误 (05) ====================
    UPLOAD_FILE_INVALID = "ARENA_05_0001"
    UPLOAD_FILE_TOO_LARGE = "ARENA_05_0002"
    UPLOAD_UNSUPPORTED_FORMAT = "ARENA_05_0003"
    UPLOAD_VALIDATION_FAILED = "ARENA_05_0004"

    # ==================== 验证错误 (06) ====================
    VALIDATION_FIELD_MISSING = "ARENA_06_0001"
    VALIDATION_FIELD_INVALID = "ARENA_06_0002"
    VALIDATION_RULE_FAILED = "ARENA_06_0003"
    VALIDATION_TYPE_MISMATCH = "ARENA_06_0004"

    # ==================== 数据库错误 (07) ====================
    DATABASE_CONNECTION_FAILED = "ARENA_07_0001"
    DATABASE_QUERY_FAILED = "ARENA_07_0002"
    DATABASE_TRANSACTION_FAILED = "ARENA_07_0003"
    DATABASE_TIMEOUT = "ARENA_07_0004"
    DATABASE_OFFLINE_MODE = "ARENA_07_0005"

    # ==================== 评价错误 (08) ====================
    REVIEW_USAGE_INSUFFICIENT = "ARENA_08_0001"
    REVIEW_ALREADY_SUBMITTED = "ARENA_08_0002"
    REVIEW_RATING_INVALID = "ARENA_08_0003"
    REVIEW_PERMISSION_DENIED = "ARENA_08_0004"

    # ==================== 文件操作错误 (09) ====================
    FILE_NOT_FOUND = "ARENA_09_0001"
    FILE_READ_FAILED = "ARENA_09_0002"
    FILE_WRITE_FAILED = "ARENA_09_0003"
    FILE_DELETE_FAILED = "ARENA_09_0004"
    FILE_PERMISSION_DENIED = "ARENA_09_0005"


# 错误消息模板（支持多语言扩展）
_ERROR_MESSAGES: Dict[str, Dict[str, str]] = {
    "en": {
        ErrorCodes.UNKNOWN: "An unknown error occurred",
        ErrorCodes.INTERNAL_ERROR: "Internal server error",
        ErrorCodes.INVALID_REQUEST: "Invalid request",
        ErrorCodes.METHOD_NOT_ALLOWED: "Method not allowed",
        ErrorCodes.RATE_LIMIT_EXCEEDED: "Rate limit exceeded",

        # Skill errors
        ErrorCodes.SKILL_NOT_FOUND: "Skill not found",
        ErrorCodes.SKILL_ALREADY_EXISTS: "Skill already exists",
        ErrorCodes.SKILL_INVALID_FORMAT: "Invalid skill format",
        ErrorCodes.SKILL_VALIDATION_FAILED: "Skill validation failed",
        ErrorCodes.SKILL_MD_MISSING: "SKILL.md file is missing",
        ErrorCodes.SKILL_MD_INVALID: "SKILL.md is invalid",
        ErrorCodes.SKILL_NAME_MISSING: "Skill name is missing",
        ErrorCodes.SKILL_VERSION_INVALID: "Skill version is invalid",
        ErrorCodes.SKILL_VERSION_CONFLICT: "Skill version already exists",
        ErrorCodes.SKILL_UPLOAD_FAILED: "Skill upload failed",
        ErrorCodes.SKILL_DOWNLOAD_FAILED: "Skill download failed",
        ErrorCodes.SKILL_DELETE_FAILED: "Skill delete failed",

        # Agent errors
        ErrorCodes.AGENT_NOT_FOUND: "Agent not found",
        ErrorCodes.AGENT_ALREADY_EXISTS: "Agent already exists",
        ErrorCodes.AGENT_INVALID_DID: "Invalid Agent DID",
        ErrorCodes.AGENT_AUTHENTICATION_FAILED: "Agent authentication failed",
        ErrorCodes.AGENT_PERMISSION_DENIED: "Agent permission denied",

        # Vote errors
        ErrorCodes.VOTE_TYPE_INVALID: "Invalid vote type",
        ErrorCodes.VOTE_ALREADY_CAST: "Vote already cast",
        ErrorCodes.VOTE_TARGET_NOT_FOUND: "Vote target not found",
        ErrorCodes.VOTE_PERMISSION_DENIED: "Vote permission denied",

        # Comment errors
        ErrorCodes.COMMENT_EMPTY: "Comment cannot be empty",
        ErrorCodes.COMMENT_NOT_FOUND: "Comment not found",
        ErrorCodes.COMMENT_PARENT_NOT_FOUND: "Parent comment not found",
        ErrorCodes.COMMENT_PERMISSION_DENIED: "Comment permission denied",
        ErrorCodes.COMMENT_TOO_LONG: "Comment is too long",

        # Upload errors
        ErrorCodes.UPLOAD_FILE_INVALID: "Invalid file",
        ErrorCodes.UPLOAD_FILE_TOO_LARGE: "File is too large",
        ErrorCodes.UPLOAD_UNSUPPORTED_FORMAT: "Unsupported file format",
        ErrorCodes.UPLOAD_VALIDATION_FAILED: "Upload validation failed",

        # Validation errors
        ErrorCodes.VALIDATION_FIELD_MISSING: "Required field is missing",
        ErrorCodes.VALIDATION_FIELD_INVALID: "Field value is invalid",
        ErrorCodes.VALIDATION_RULE_FAILED: "Validation rule failed",
        ErrorCodes.VALIDATION_TYPE_MISMATCH: "Field type mismatch",

        # Database errors
        ErrorCodes.DATABASE_CONNECTION_FAILED: "Database connection failed",
        ErrorCodes.DATABASE_QUERY_FAILED: "Database query failed",
        ErrorCodes.DATABASE_TRANSACTION_FAILED: "Database transaction failed",
        ErrorCodes.DATABASE_TIMEOUT: "Database timeout",
        ErrorCodes.DATABASE_OFFLINE_MODE: "Database is in offline mode",

        # Review errors
        ErrorCodes.REVIEW_USAGE_INSUFFICIENT: "Insufficient usage to review",
        ErrorCodes.REVIEW_ALREADY_SUBMITTED: "Review already submitted",
        ErrorCodes.REVIEW_RATING_INVALID: "Invalid rating value",
        ErrorCodes.REVIEW_PERMISSION_DENIED: "Review permission denied",

        # File operation errors
        ErrorCodes.FILE_NOT_FOUND: "File not found",
        ErrorCodes.FILE_READ_FAILED: "Failed to read file",
        ErrorCodes.FILE_WRITE_FAILED: "Failed to write file",
        ErrorCodes.FILE_DELETE_FAILED: "Failed to delete file",
        ErrorCodes.FILE_PERMISSION_DENIED: "File permission denied",
    },
    "zh": {
        ErrorCodes.UNKNOWN: "发生未知错误",
        ErrorCodes.INTERNAL_ERROR: "内部服务器错误",
        ErrorCodes.INVALID_REQUEST: "无效请求",
        ErrorCodes.METHOD_NOT_ALLOWED: "不允许的方法",
        ErrorCodes.RATE_LIMIT_EXCEEDED: "超出频率限制",

        # Skill 错误
        ErrorCodes.SKILL_NOT_FOUND: "Skill 不存在",
        ErrorCodes.SKILL_ALREADY_EXISTS: "Skill 已存在",
        ErrorCodes.SKILL_INVALID_FORMAT: "Skill 格式无效",
        ErrorCodes.SKILL_VALIDATION_FAILED: "Skill 验证失败",
        ErrorCodes.SKILL_MD_MISSING: "缺少 SKILL.md 文件",
        ErrorCodes.SKILL_MD_INVALID: "SKILL.md 无效",
        ErrorCodes.SKILL_NAME_MISSING: "缺少 Skill 名称",
        ErrorCodes.SKILL_VERSION_INVALID: "Skill 版本无效",
        ErrorCodes.SKILL_VERSION_CONFLICT: "Skill 版本已存在",
        ErrorCodes.SKILL_UPLOAD_FAILED: "Skill 上传失败",
        ErrorCodes.SKILL_DOWNLOAD_FAILED: "Skill 下载失败",
        ErrorCodes.SKILL_DELETE_FAILED: "Skill 删除失败",

        # Agent 错误
        ErrorCodes.AGENT_NOT_FOUND: "Agent 不存在",
        ErrorCodes.AGENT_ALREADY_EXISTS: "Agent 已存在",
        ErrorCodes.AGENT_INVALID_DID: "无效的 Agent DID",
        ErrorCodes.AGENT_AUTHENTICATION_FAILED: "Agent 认证失败",
        ErrorCodes.AGENT_PERMISSION_DENIED: "Agent 权限不足",

        # 投票错误
        ErrorCodes.VOTE_TYPE_INVALID: "无效的投票类型",
        ErrorCodes.VOTE_ALREADY_CAST: "已经投过票",
        ErrorCodes.VOTE_TARGET_NOT_FOUND: "投票目标不存在",
        ErrorCodes.VOTE_PERMISSION_DENIED: "投票权限不足",

        # 评论错误
        ErrorCodes.COMMENT_EMPTY: "评论不能为空",
        ErrorCodes.COMMENT_NOT_FOUND: "评论不存在",
        ErrorCodes.COMMENT_PARENT_NOT_FOUND: "父评论不存在",
        ErrorCodes.COMMENT_PERMISSION_DENIED: "评论权限不足",
        ErrorCodes.COMMENT_TOO_LONG: "评论过长",

        # 上传错误
        ErrorCodes.UPLOAD_FILE_INVALID: "无效文件",
        ErrorCodes.UPLOAD_FILE_TOO_LARGE: "文件过大",
        ErrorCodes.UPLOAD_UNSUPPORTED_FORMAT: "不支持的文件格式",
        ErrorCodes.UPLOAD_VALIDATION_FAILED: "上传验证失败",

        # 验证错误
        ErrorCodes.VALIDATION_FIELD_MISSING: "缺少必需字段",
        ErrorCodes.VALIDATION_FIELD_INVALID: "字段值无效",
        ErrorCodes.VALIDATION_RULE_FAILED: "验证规则失败",
        ErrorCodes.VALIDATION_TYPE_MISMATCH: "字段类型不匹配",

        # 数据库错误
        ErrorCodes.DATABASE_CONNECTION_FAILED: "数据库连接失败",
        ErrorCodes.DATABASE_QUERY_FAILED: "数据库查询失败",
        ErrorCodes.DATABASE_TRANSACTION_FAILED: "数据库事务失败",
        ErrorCodes.DATABASE_TIMEOUT: "数据库超时",
        ErrorCodes.DATABASE_OFFLINE_MODE: "数据库处于离线模式",

        # 评价错误
        ErrorCodes.REVIEW_USAGE_INSUFFICIENT: "使用次数不足以评价",
        ErrorCodes.REVIEW_ALREADY_SUBMITTED: "已经评价过",
        ErrorCodes.REVIEW_RATING_INVALID: "评分值无效",
        ErrorCodes.REVIEW_PERMISSION_DENIED: "评价权限不足",

        # 文件操作错误
        ErrorCodes.FILE_NOT_FOUND: "文件不存在",
        ErrorCodes.FILE_READ_FAILED: "读取文件失败",
        ErrorCodes.FILE_WRITE_FAILED: "写入文件失败",
        ErrorCodes.FILE_DELETE_FAILED: "删除文件失败",
        ErrorCodes.FILE_PERMISSION_DENIED: "文件权限不足",
    },
}


def get_error_message(
    error_code: str,
    language: str = "zh",
    **kwargs
) -> str:
    """
    获取错误消息

    Args:
        error_code: 错误码
        language: 语言 (en/zh)
        **kwargs: 消息格式化参数

    Returns:
        错误消息字符串

    Examples:
        >>> get_error_message("ARENA_01_0001", "zh", skill_id="skill-123")
        'Skill 不存在 (skill_id: skill-123)'

        >>> get_error_message("ARENA_08_0001", "zh", current=3, required=5)
        '使用次数不足以评价 (当前: 3, 需要: 5)'
    """
    # 查找错误码枚举
    try:
        code_enum = ErrorCodes(error_code)
    except ValueError:
        return f"Unknown error code: {error_code}"

    # 获取基础消息
    language = language if language in _ERROR_MESSAGES else "en"
    base_message = _ERROR_MESSAGES[language].get(code_enum, code_enum.value)

    # 如果有格式化参数，添加到消息
    if kwargs:
        details = ", ".join(f"{k}: {v}" for k, v in kwargs.items())
        return f"{base_message} ({details})"

    return base_message


def get_http_status(error_code: str) -> int:
    """
    根据错误码获取 HTTP 状态码

    Args:
        error_code: 错误码

    Returns:
        HTTP 状态码
    """
    # 根据模块代码映射
    module = int(error_code.split("_")[1])

    status_map = {
        0: 500,  # 通用
        1: 400,  # Skill
        2: 404,  # Agent
        3: 400,  # 投票
        4: 400,  # 评论
        5: 400,  # 上传
        6: 400,  # 验证
        7: 503,  # 数据库
        8: 403,  # 评价
        9: 500,  # 文件操作
    }

    return status_map.get(module, 500)
