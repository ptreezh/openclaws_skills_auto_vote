"""
Tests for DID authentication system.
"""
import pytest
from scripts.did_auth import DIDAuth


class TestDIDAuth:
    """Test cases for DID authentication."""

    def test_generate_did(self):
        """Test DID generation format and length."""
        did_auth = DIDAuth()

        # Test with a sample public key
        public_key = "test_public_key_123"
        did = did_auth.generate_did(public_key)

        # Check format
        assert did.startswith("did:openclaw:")

        # Check that after prefix we have exactly 32 hex characters
        hash_part = did.split(":")[-1]
        assert len(hash_part) == 32
        assert all(c in "0123456789abcdef" for c in hash_part)

        # Test that same public key generates same DID
        did2 = did_auth.generate_did(public_key)
        assert did == did2

        # Test that different public keys generate different DIDs
        different_public_key = "different_key_456"
        did3 = did_auth.generate_did(different_public_key)
        assert did != did3

    def test_generate_did_format(self):
        """Test DID format specification."""
        did_auth = DIDAuth()

        # Test various public keys
        test_keys = [
            "",
            "a",
            "very_long_public_key_with_many_characters_123456789",
            "special!@#$%^&*()characters",
        ]

        for key in test_keys:
            did = did_auth.generate_did(key)
            # Verify format: did:openclaw:{32-char-hex}
            assert did.startswith("did:openclaw:")
            hash_part = did.split(":")[-1]
            assert len(hash_part) == 32
            assert all(c in "0123456789abcdef" for c in hash_part)

    @pytest.mark.asyncio
    async def test_register_agent(self):
        """Test agent registration functionality."""
        # Note: This test requires database connection
        # It's marked as async but will need database setup to run
        did_auth = DIDAuth()

        # Test that we can instantiate and call methods
        # (actual database tests would require test database setup)
        public_key = "test_agent_key"
        did = did_auth.generate_did(public_key)

        # Verify DID was generated correctly
        assert did.startswith("did:openclaw:")
        assert len(did.split(":")[-1]) == 32

        # We can't test actual registration without database connection
        # but we can verify the method exists and is callable
        assert hasattr(did_auth, "register_agent")
        assert callable(did_auth.register_agent)
