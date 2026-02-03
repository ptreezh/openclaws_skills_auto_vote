"""
DID authentication manager for Skills Arena.
"""
import hashlib
from typing import Optional, Dict, Any
from scripts.database.db import db


class DIDAuth:
    """Decentralized Identifier (DID) authentication manager."""

    @staticmethod
    def generate_did(public_key: str) -> str:
        """
        Generate a DID from a public key.

        Args:
            public_key: The public key string to hash.

        Returns:
            A DID in the format "did:openclaw:{32-char-hex}"
        """
        # Hash the public key using SHA-256
        hash_bytes = hashlib.sha256(public_key.encode()).hexdigest()
        # Return DID format with first 32 characters of the hash
        return f"did:openclaw:{hash_bytes[:32]}"

    async def register_agent(
        self, did: str, username: str, display_name: str, bio: str = ""
    ) -> Dict[str, Any]:
        """
        Register an agent with their DID. Returns existing agent if already registered.

        Args:
            did: The agent's DID.
            username: Unique username.
            display_name: Display name for the agent.
            bio: Optional biography.

        Returns:
            Dictionary containing agent information (id, did, username, display_name, bio).
        """
        async with db.get_connection() as conn:
            # Try to get existing agent
            existing = await conn.fetchrow(
                "SELECT id, did, username, display_name, bio FROM agents WHERE did = $1",
                did
            )

            if existing:
                return dict(existing)

            # Register new agent
            agent_id = await conn.fetchval(
                """INSERT INTO agents (did, username, display_name, bio)
                   VALUES ($1, $2, $3, $4)
                   RETURNING id""",
                did, username, display_name, bio
            )

            return {
                "id": agent_id,
                "did": did,
                "username": username,
                "display_name": display_name,
                "bio": bio,
            }

    async def get_agent(self, did: str) -> Optional[Dict[str, Any]]:
        """
        Get agent information by DID.

        Args:
            did: The agent's DID.

        Returns:
            Dictionary containing agent information or None if not found.
        """
        async with db.get_connection() as conn:
            agent = await conn.fetchrow(
                """SELECT id, did, username, display_name, bio, created_at, last_active_at
                   FROM agents WHERE did = $1""",
                did
            )

            if agent:
                return dict(agent)
            return None

    async def update_last_active(self, did: str) -> None:
        """
        Update the last_active timestamp for an agent.

        Args:
            did: The agent's DID.
        """
        async with db.get_connection() as conn:
            await conn.execute(
                "UPDATE agents SET last_active_at = CURRENT_TIMESTAMP WHERE did = $1",
                did
            )
