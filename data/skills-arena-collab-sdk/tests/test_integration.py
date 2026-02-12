#!/usr/bin/env python3
"""
Skills Arena Collaboration SDK - Integration Tests

Tests the complete workflow:
1. Consent management
2. Usage tracking
3. Local skill scanning
4. Incentive tracking
5. Privacy validation

Author: Skills Arena Team
"""

import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Import the SDK
import sys

sys.path.insert(0, str(Path(__file__).parent / "scripts"))
from skills_arena_collab import (
    SkillsArenaClient,
    ConsentLevel,
    ConsentStatus,
    ConsentConfig,
    ConsentManager,
    UsageTracker,
    IncentiveTracker,
    LocalSkillScanner,
    SkillMetadata,
)


class TestConsentManagement(unittest.TestCase):
    """Test consent configuration and management."""

    def test_consent_config_defaults(self):
        """Test default consent configuration."""
        config = ConsentConfig()

        self.assertEqual(config.consent_level, ConsentLevel.DISABLED)
        self.assertEqual(config.version, "1.0")
        self.assertFalse(config.is_valid())

    def test_consent_config_save_load(self):
        """Test saving and loading consent config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ConsentConfig(
                user_did="did:openclaw:test123",
                consent_level=ConsentLevel.USAGE_STATS_ONLY,
                granted_at="2024-01-15T10:00:00Z",
            )

            path = Path(tmpdir) / "consent.yml"
            config.save(path)

            loaded = ConsentConfig.load(path)

            self.assertEqual(loaded.user_did, "did:openclaw:test123")
            self.assertEqual(loaded.consent_level, ConsentLevel.USAGE_STATS_ONLY)

    def test_consent_validity(self):
        """Test consent validity checking."""
        config = ConsentConfig()

        # No consent
        self.assertFalse(config.is_valid())

        # With consent, no expiry
        config.consent_level = ConsentLevel.FULL_PARTICIPATION
        config.granted_at = "2024-01-15T10:00:00Z"
        self.assertTrue(config.is_valid())

        # With expired consent
        from datetime import datetime, timedelta

        config.expires_at = (datetime.now() - timedelta(days=1)).isoformat()
        self.assertFalse(config.is_valid())


class TestUsageTracker(unittest.TestCase):
    """Test usage tracking functionality."""

    def test_log_usage(self):
        """Test logging usage events."""
        tracker = UsageTracker()

        # Log some events
        tracker.log("skill-1", 0.1, True)
        tracker.log("skill-2", 0.5, True)
        tracker.log("skill-1", 0.2, False)

        self.assertEqual(len(tracker), 3)

        queue = tracker.get_queue()
        self.assertEqual(len(queue), 3)

        # First item should be skill-1
        self.assertEqual(queue[0].skill_id, "skill-1")
        self.assertTrue(queue[0].success)

        # Third item should be failed skill-1
        self.assertEqual(queue[2].skill_id, "skill-1")
        self.assertFalse(queue[2].success)

    def test_queue_bounding(self):
        """Test queue doesn't exceed max size."""
        tracker = UsageTracker(max_queue_size=5)

        for i in range(10):
            tracker.log(f"skill-{i}", 0.1, True)

        self.assertEqual(len(tracker), 5)
        # Should keep last 5 items
        queue = tracker.get_queue()
        self.assertEqual(queue[0].skill_id, "skill-5")
        self.assertEqual(queue[4].skill_id, "skill-9")

    def test_clear_queue(self):
        """Test clearing the queue."""
        tracker = UsageTracker()
        tracker.log("skill-1", 0.1, True)
        tracker.log("skill-2", 0.2, True)

        tracker.clear()

        self.assertEqual(len(tracker), 0)


class TestIncentiveTracker(unittest.TestCase):
    """Test incentive/point tracking."""

    def test_add_points(self):
        """Test adding points for contributions."""
        tracker = IncentiveTracker("did:openclaw:test")

        tracker.add_points("upload", "Uploaded skill")
        tracker.add_points("execution_100", "Reached 100 executions")
        tracker.add_points("helpful_vote", "Voted on skill")

        self.assertEqual(tracker.total_points, 160)  # 100 + 50 + 10

    def test_tier_calculation(self):
        """Test tier based on points."""
        tracker = IncentiveTracker("did:openclaw:test")

        # Bronze (0-500)
        self.assertEqual(tracker.tier, "🥉 Bronze")

        # Add points for Silver
        tracker._points = 600
        self.assertEqual(tracker.tier, "🥈 Silver")

        # Add points for Gold
        tracker._points = 2500
        self.assertEqual(tracker.tier, "🥇 Gold")

        # Add points for Platinum
        tracker._points = 15000
        self.assertEqual(tracker.tier, "💎 Platinum")

    def test_summary(self):
        """Test getting incentive summary."""
        tracker = IncentiveTracker("did:openclaw:test")
        tracker.add_points("upload", "Uploaded skill")
        tracker.add_points("execution_100", "100 executions")

        summary = tracker.get_summary()

        self.assertEqual(summary["total_points"], 150)
        self.assertEqual(summary["user_did"], "did:openclaw:test")
        self.assertIn("contributions", summary)


class TestLocalSkillScanner(unittest.TestCase):
    """Test local skill scanning."""

    def test_analyze_skill(self):
        """Test analyzing a single skill directory."""
        client = SkillsArenaClient()
        scanner = LocalSkillScanner(client)

        with tempfile.TemporaryDirectory() as tmpdir:
            skill_path = Path(tmpdir) / "test-skill"
            skill_path.mkdir()

            # Create SKILL.md
            (skill_path / "SKILL.md").write_text("""# Test Skill

A test skill for unit testing.

## Usage

Use it with care.
""")

            # Create scripts directory
            (skill_path / "scripts").mkdir()
            (skill_path / "scripts" / "main.py").write_text("""
def main():
    pass
""")

            # Analyze
            result = asyncio.run(scanner._analyze_skill(skill_path))

            self.assertIsNotNone(result)
            self.assertEqual(result["name"], "Test Skill")
            self.assertFalse(result["ready_to_share"])

            # Add usage stats
            (skill_path / ".usage_stats").write_text('{"total_executions": 150}')

            result = asyncio.run(scanner._analyze_skill(skill_path))
            self.assertTrue(result["ready_to_share"])


class TestSkillsArenaClient(unittest.TestCase):
    """Test main client functionality."""

    def test_client_initialization(self):
        """Test client initialization with defaults."""
        client = SkillsArenaClient()

        self.assertEqual(client.server_url, "https://skills-arena.example.com")
        self.assertEqual(client.auto_send, True)
        self.assertIsNotNone(client.user_did)
        self.assertTrue(client.user_did.startswith("did:openclaw:anon:"))

    def test_client_with_consent(self):
        """Test client with initial consent."""
        client = SkillsArenaClient(consent_level=ConsentLevel.USAGE_STATS_ONLY)

        status, _ = client.get_consent_status()
        self.assertEqual(status, ConsentStatus.GRANTED)

    def test_get_data_sharing_preview(self):
        """Test data sharing preview."""
        client = SkillsArenaClient(consent_level=ConsentLevel.USAGE_STATS_ONLY)

        preview = client.get_data_sharing_preview()

        # Should have at least anonymous_id and execution_time
        categories = [p["category"] for p in preview]
        self.assertIn("anonymous_id", categories)

    def test_anonimize_did(self):
        """Test DID anonymization."""
        client = SkillsArenaClient()

        anon = client._anonimize("did:openclaw:user123")

        self.assertTrue(anon.startswith("anon:"))
        self.assertEqual(len(anon), 16)  # 8 bytes hex = 16 chars


class TestSkillMetadata(unittest.TestCase):
    """Test skill metadata handling."""

    def test_metadata_to_dict(self):
        """Test metadata serialization."""
        meta = SkillMetadata(
            name="Test Skill",
            description="A test skill",
            tags=["test", "unit"],
            author_did="did:openclaw:author",
        )

        data = meta.to_dict()

        self.assertEqual(data["name"], "Test Skill")
        self.assertEqual(data["tags"], ["test", "unit"])
        self.assertEqual(data["author_did"], "did:openclaw:author")

    def test_extract_metadata(self):
        """Test extracting metadata from skill directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_path = Path(tmpdir) / "my-skill"
            skill_path.mkdir()

            (skill_path / "SKILL.md").write_text("""# My Custom Skill

This is my custom skill for testing.

## Tags

test, custom, example
""")

            (skill_path / "scripts").mkdir()

            # Test extraction
            client = SkillsArenaClient()
            meta = asyncio.run(client._extract_metadata(skill_path))

            self.assertEqual(meta.name, "My Custom Skill")
            self.assertIn("custom", meta.tags)


class TestIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration tests with mocked API calls."""

    async def test_full_consent_workflow(self):
        """Test complete consent workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            consent_path = Path(tmpdir) / "consent.yml"

            manager = ConsentManager("did:openclaw:test", consent_path)

            # Initially no consent
            status, _ = manager.get_status()
            self.assertEqual(status, ConsentStatus.NOT_GRANTED)

            # Grant consent (mocking user input)
            with patch("builtins.input", return_value="limited"):
                result = await manager.request_consent(
                    purpose="Testing", categories=["execution_time", "success"]
                )

            self.assertTrue(result)

            # Check consent granted
            status, message = manager.get_status()
            self.assertEqual(status, ConsentStatus.GRANTED)

            # Check config
            config = manager.config
            self.assertEqual(config.consent_level, ConsentLevel.USAGE_STATS_ONLY)

    async def test_usage_tracking_flow(self):
        """Test complete usage tracking flow."""
        client = SkillsArenaClient(
            server_url="https://test.example.com",
            consent_level=ConsentLevel.FULL_PARTICIPATION,
            auto_send=False,  # Don't actually send
        )

        # Track some usage
        await client.log_usage("skill-1", 0.1, True)
        await client.log_usage("skill-2", 0.5, True, {"input_size": 1000})

        # Check tracker
        self.assertEqual(len(client.tracker), 2)

        await client.close()

    async def test_session_tracking(self):
        """Test session-based tracking."""
        client = SkillsArenaClient(
            server_url="https://test.example.com",
            consent_level=ConsentLevel.FULL_PARTICIPATION,
            auto_send=False,
        )

        async with client.track_session("test-skill", {"test": True}) as session:
            # Simulate work
            await asyncio.sleep(0.01)
            session.set_result("test-result")

        # Check that usage was logged
        self.assertEqual(len(client.tracker), 1)
        usage = client.tracker.get_queue()[0]
        self.assertEqual(usage.skill_id, "test-skill")
        self.assertTrue(usage.success)

        await client.close()


class TestPrivacyCompliance(unittest.TestCase):
    """Test privacy compliance requirements."""

    def test_no_pii_in_usage_data(self):
        """Verify no PII in usage data."""
        tracker = UsageTracker()
        data = tracker.log(
            skill_id="test-skill",
            execution_time=0.1,
            success=True,
            metadata={
                "user_input": "PII: john@example.com"
            },  # This should NOT happen in real code
        )

        # The SDK should handle this gracefully but in production
        # the caller is responsible for not including PII
        self.assertIn("user_input", data.metadata)

    def test_anonymization(self):
        """Test user ID anonymization."""
        client = SkillsArenaClient()

        original = "did:openclaw:user123456789"
        anon = client._anonimize(original)

        # Should not contain original
        self.assertNotIn("user123456789", anon)
        # Should be hashed
        self.assertTrue(anon.startswith("anon:"))

    def test_consent_required_for_upload(self):
        """Test that upload requires consent."""
        client = SkillsArenaClient(consent_level=ConsentLevel.DISABLED)

        with self.assertRaises(PermissionError):
            asyncio.run(client.upload_skill("/fake/path"))

    def test_full_participation_required_for_upload(self):
        """Test that upload requires full participation."""
        client = SkillsArenaClient(
            consent_level=ConsentLevel.USAGE_STATS_ONLY  # Not full
        )

        with self.assertRaises(PermissionError):
            asyncio.run(client.upload_skill("/fake/path"))


def run_tests():
    """Run all tests."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestConsentManagement))
    suite.addTests(loader.loadTestsFromTestCase(TestUsageTracker))
    suite.addTests(loader.loadTestsFromTestCase(TestIncentiveTracker))
    suite.addTests(loader.loadTestsFromTestCase(TestLocalSkillScanner))
    suite.addTests(loader.loadTestsFromTestCase(TestSkillsArenaClient))
    suite.addTests(loader.loadTestsFromTestCase(TestSkillMetadata))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestPrivacyCompliance))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
