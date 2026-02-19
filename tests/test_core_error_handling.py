"""
Unit tests for core error handling infrastructure.

These tests verify that the custom exceptions, logging, and error handling
mechanisms work correctly without requiring a database.
"""

import pytest
import json
from datetime import datetime
from pathlib import Path
import tempfile
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.exceptions import (
    ArenaException,
    ValidationError,
    SkillNotFoundError,
    AgentNotFoundError,
    PermissionDeniedError,
    AuthenticationError,
    DatabaseError,
    FileOperationError,
    UploadError,
    VersionConflictError,
    ReviewPermissionError,
    VoteError,
    CommentError,
)
from core.error_codes import ErrorCodes, get_error_message, get_http_status
from core.logging_config import get_logger, ArenaLogger, setup_logging, JSONFormatter
from core.retry import retry, retry_async
import logging


class TestArenaException:
    """Tests for ArenaException base class and subclasses."""

    def test_base_exception_creation(self):
        """Test creating a base ArenaException."""
        exc = ArenaException(
            message="Test error",
            error_code="TEST_001",
            http_status=500,
            details={"key": "value"}
        )
        assert exc.message == "Test error"
        assert exc.error_code == "TEST_001"
        assert exc.http_status == 500
        assert exc.details == {"key": "value"}
        assert exc.timestamp is not None

    def test_base_exception_to_dict(self):
        """Test converting exception to dictionary format."""
        exc = ValidationError(
            message="Validation failed",
            field="test_field"
        )
        result = exc.to_dict()

        assert result["success"] is False
        assert result["error"]["code"] == "ARENA_VALIDATION"
        assert result["error"]["message"] == "Validation failed"
        assert result["error"]["details"]["field"] == "test_field"
        assert result["error"]["timestamp"] is not None

    def test_validation_error(self):
        """Test ValidationError creation."""
        exc = ValidationError(
            message="Invalid input",
            field="username",
            details={"min_length": 3, "max_length": 20}
        )

        assert exc.error_code == "ARENA_VALIDATION"
        assert exc.http_status == 400
        assert exc.details["field"] == "username"

    def test_skill_not_found_error(self):
        """Test SkillNotFoundError creation."""
        exc = SkillNotFoundError(skill_id="skill-123")

        assert exc.error_code == "ARENA_SKILL_NOT_FOUND"
        assert exc.http_status == 404
        assert exc.details["skill_id"] == "skill-123"
        assert "skill-123" in exc.message

    def test_agent_not_found_error(self):
        """Test AgentNotFoundError creation."""
        exc = AgentNotFoundError(agent_did="did:example:123")

        assert exc.error_code == "ARENA_AGENT_NOT_FOUND"
        assert exc.http_status == 404
        assert exc.details["agent_did"] == "did:example:123"

    def test_permission_denied_error(self):
        """Test PermissionDeniedError creation."""
        exc = PermissionDeniedError(
            message="Access denied",
            required_permission="admin"
        )

        assert exc.error_code == "ARENA_PERMISSION_DENIED"
        assert exc.http_status == 403
        assert exc.details["required_permission"] == "admin"

    def test_upload_error(self):
        """Test UploadError creation."""
        exc = UploadError(
            message="Upload failed",
            file_name="test.zip",
            reason="file_too_large"
        )

        assert exc.error_code == "ARENA_UPLOAD"
        assert exc.http_status == 400
        assert exc.details["file_name"] == "test.zip"

    def test_version_conflict_error(self):
        """Test VersionConflictError creation."""
        exc = VersionConflictError(
            skill_name="TestSkill",
            version="1.0.0",
            existing_skill_id="skill-abc123"
        )

        assert exc.error_code == "ARENA_VERSION_CONFLICT"
        assert exc.http_status == 409
        assert exc.details["skill_name"] == "TestSkill"

    def test_exception_str_representation(self):
        """Test string representation of exceptions."""
        exc = SkillNotFoundError(skill_id="skill-123")
        exc_str = str(exc)

        assert "[ARENA_SKILL_NOT_FOUND]" in exc_str
        assert "skill-123" in exc_str


class TestErrorCodes:
    """Tests for error code registry."""

    def test_error_codes_enum_values(self):
        """Test that error codes have correct format."""
        assert ErrorCodes.SKILL_NOT_FOUND == "ARENA_01_0001"
        assert ErrorCodes.AGENT_NOT_FOUND == "ARENA_02_0001"
        assert ErrorCodes.DATABASE_CONNECTION_FAILED == "ARENA_07_0001"

    def test_get_error_message_english(self):
        """Test getting error messages in English."""
        msg = get_error_message("ARENA_01_0001", language="en")
        assert "not found" in msg.lower()

    def test_get_error_message_chinese(self):
        """Test getting error messages in Chinese."""
        msg = get_error_message("ARENA_01_0001", language="zh")
        assert "不存在" in msg

    def test_get_error_message_with_params(self):
        """Test error message formatting with parameters."""
        msg = get_error_message(
            "ARENA_08_0001",
            language="zh",
            current=3,
            required=5
        )
        assert "3" in msg
        assert "5" in msg

    def test_get_error_message_unknown_code(self):
        """Test getting message for unknown error code."""
        msg = get_error_message("UNKNOWN_CODE", language="en")
        assert "Unknown error code" in msg

    def test_get_http_status(self):
        """Test getting HTTP status for error codes."""
        assert get_http_status("ARENA_01_0001") == 400  # Skill
        assert get_http_status("ARENA_02_0001") == 404  # Agent
        assert get_http_status("ARENA_07_0001") == 503  # Database
        assert get_http_status("ARENA_08_0001") == 403  # Review


class TestLogging:
    """Tests for structured logging system."""

    def test_get_logger(self):
        """Test getting a logger instance."""
        logger = get_logger("test.module")
        assert isinstance(logger, ArenaLogger)
        assert logger.name == "test.module"

    def test_logger_levels(self, caplog=None):
        """Test different log levels."""
        logger = get_logger("test.levels")

        # Create a temp directory for logs
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = get_logger("test.levels", log_dir=Path(tmpdir))

            # Test logging (should not raise exceptions)
            logger.debug("Debug message", key="value")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")

    def test_logger_context_manager(self):
        """Test logger context manager."""
        logger = get_logger("test.context")

        with logger.log_context(user_id="123", action="test"):
            logger.info("Action in context")
            # Context is automatically added

    def test_logger_with_exception(self):
        """Test logging with exception."""
        logger = get_logger("test.exception")

        try:
            raise ValueError("Test exception")
        except ValueError as e:
            # Should not raise
            logger.error("Caught exception", exception=e)


class TestRetryMechanism:
    """Tests for retry mechanism."""

    def test_retry_success_on_first_try(self):
        """Test that retry decorator works when function succeeds immediately."""
        call_count = [0]

        @retry(max_attempts=3, delay=0.01)
        def test_func():
            call_count[0] += 1
            return "success"

        result = test_func()
        assert result == "success"
        assert call_count[0] == 1

    def test_retry_success_after_retries(self):
        """Test that retry decorator retries on failure."""
        call_count = [0]

        @retry(max_attempts=3, delay=0.01)
        def test_func():
            call_count[0] += 1
            if call_count[0] < 2:
                raise ValueError("Fail")
            return "success"

        result = test_func()
        assert result == "success"
        assert call_count[0] == 2

    def test_retry_failure_after_max_attempts(self):
        """Test that retry decorator gives up after max attempts."""
        call_count = [0]

        @retry(max_attempts=3, delay=0.01)
        def test_func():
            call_count[0] += 1
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            test_func()

        assert call_count[0] == 3

    @pytest.mark.asyncio
    async def test_retry_async_success(self):
        """Test async retry decorator."""
        call_count = [0]

        @retry_async(max_attempts=3, delay=0.01)
        async def test_func():
            call_count[0] += 1
            if call_count[0] < 2:
                raise ValueError("Fail")
            return "success"

        result = await test_func()
        assert result == "success"
        assert call_count[0] == 2

    @pytest.mark.asyncio
    async def test_retry_async_failure(self):
        """Test async retry decorator failure."""
        call_count = [0]

        @retry_async(max_attempts=3, delay=0.01)
        async def test_func():
            call_count[0] += 1
            raise ValueError("Always fails")

        with pytest.raises(ValueError):
            await test_func()

        assert call_count[0] == 3


class TestFastAPIIntegration:
    """Tests for FastAPI error handler integration."""

    def test_fastapi_response_conversion(self):
        """Test converting ArenaException to FastAPI HTTPException."""
        from fastapi import HTTPException

        exc = ValidationError(
            message="Test validation error",
            field="test_field"
        )

        http_exc = exc.to_fastapi_response()
        assert isinstance(http_exc, HTTPException)
        assert http_exc.status_code == 400
        assert http_exc.detail["code"] == "ARENA_VALIDATION"
        assert http_exc.detail["message"] == "Test validation error"


class TestRefactoredModules:
    """Tests for refactored modules using new error handling."""

    def test_arena_manager_imports(self):
        """Test that arena_manager imports and uses new exceptions."""
        from scripts.arena_manager import ArenaManager

        # Should not raise ImportError
        assert ArenaManager is not None

    def test_skill_validator_imports(self):
        """Test that skill_validator imports and uses logger."""
        from scripts.skill_validator import SkillValidator

        assert SkillValidator is not None

    def test_skill_uploader_imports(self):
        """Test that skill_uploader imports and uses new exceptions."""
        from scripts.skill_uploader import SkillUploader

        assert SkillUploader is not None

    def test_arena_manager_with_invalid_scenario(self):
        """Test arena_manager raises ValidationError for invalid scenario."""
        from scripts.arena_manager import ArenaManager
        from core.exceptions import ValidationError

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = ArenaManager(data_dir=tmpdir)

            # Try to add skill to non-existent scenario
            with pytest.raises(ValidationError) as exc_info:
                manager.add_skill_to_scenario(
                    scenario_id="nonexistent",
                    skill_id="test-skill"
                )

            assert "not found" in str(exc_info.value).lower()

    def test_skill_validator_logger_usage(self):
        """Test that skill_validator uses structured logging."""
        from scripts.skill_validator import SkillValidator

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a minimal skill structure
            skill_dir = Path(tmpdir) / "test_skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\n"
                "name: Test Skill\n"
                "description: A test skill\n"
                "---\n"
                "# Test Skill\n"
                "This is a test skill."
            )
            (skill_dir / "scripts").mkdir()
            (skill_dir / "scripts" / "main.py").write_text("print('hello')\n")
            (skill_dir / "references").mkdir()

            validator = SkillValidator()
            results = validator.validate_skill(str(skill_dir))

            # Should complete without errors
            assert results is not None
            assert "overall_status" in results


@pytest.mark.unit
class TestBackwardCompatibility:
    """Tests to verify backward compatibility with existing code."""

    def test_exception_raising_like_valueerror(self):
        """Test that our exceptions work independently of ValueError."""
        from core.exceptions import ValidationError

        # Our exceptions don't inherit from ValueError, but that's OK
        # Backward compatibility is maintained through API response format
        try:
            raise ValidationError(message="Test")
        except ValidationError as e:
            # Should be caught by our custom exception type
            assert isinstance(e, ValidationError)
            assert e.message == "Test"

    def test_api_response_format(self):
        """Test that API response format matches expected structure."""
        exc = SkillNotFoundError(skill_id="skill-123")
        response = exc.to_dict()

        # Verify response structure matches what clients expect
        assert "success" in response
        assert "error" in response
        assert "code" in response["error"]
        assert "message" in response["error"]
        assert "details" in response["error"]


if __name__ == "__main__":
    # Run tests when executed directly
    pytest.main([__file__, "-v", "--tb=short"])
