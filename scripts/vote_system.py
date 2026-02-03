"""
Voting system for Skills Arena.

Handles voting on skills and comments, including:
- Upvoting and downvoting
- Vote cancellation
- Vote type changes (upvote -> downvote and vice versa)
- Automatic upvote for duplicate uploads
"""
from typing import Dict, Optional, Tuple
from scripts.database.db import db


class VoteSystem:
    """Manages voting operations for skills and comments."""

    async def vote(
        self,
        target_type: str,
        target_id: str,
        agent_did: str,
        vote_type: str
    ) -> Dict[str, any]:
        """
        Main voting method - handles new votes, changes, and cancellation.

        Args:
            target_type: Type of target ('skill' or 'comment')
            target_id: ID of the skill or comment
            agent_did: DID of the agent casting the vote
            vote_type: Type of vote ('upvote', 'downvote', or 'cancel')

        Returns:
            Dict with operation results including:
                - success: bool
                - message: str
                - upvotes: int (new count)
                - downvotes: int (new count)
                - vote_score: int (new score)

        Raises:
            ValueError: If invalid parameters provided
        """
        # Validate inputs
        if target_type not in ['skill', 'comment']:
            raise ValueError(f"Invalid target_type: {target_type}. Must be 'skill' or 'comment'")

        if vote_type not in ['upvote', 'downvote', 'cancel']:
            raise ValueError(f"Invalid vote_type: {vote_type}. Must be 'upvote', 'downvote', or 'cancel'")

        async with db.get_connection() as conn:
            async with conn.transaction():
                # Get agent_id from did
                agent_id = await conn.fetchval(
                    "SELECT agent_id FROM agents WHERE did = $1",
                    agent_did
                )

                if not agent_id:
                    return {
                        "success": False,
                        "message": "Agent not found",
                        "upvotes": 0,
                        "downvotes": 0,
                        "vote_score": 0
                    }

                # Check for existing vote
                existing_vote = await conn.fetchrow(
                    "SELECT vote_type FROM votes WHERE agent_id = $1 AND target_type = $2 AND target_id = $3",
                    agent_id, target_type, target_id
                )

                # Handle different scenarios
                if vote_type == 'cancel':
                    return await self._cancel_vote(conn, existing_vote, target_type, target_id, agent_id)
                elif existing_vote:
                    return await self._change_vote(conn, existing_vote, target_type, target_id, agent_id, vote_type)
                else:
                    return await self._new_vote(conn, target_type, target_id, agent_id, vote_type)

    async def _new_vote(
        self,
        conn,
        target_type: str,
        target_id: str,
        agent_id: str,
        vote_type: str
    ) -> Dict[str, any]:
        """Handle a new vote."""
        # Insert vote record
        await conn.execute(
            """INSERT INTO votes (agent_id, target_type, target_id, vote_type)
               VALUES ($1, $2, $3, $4)""",
            agent_id, target_type, target_id, vote_type
        )

        # Update target table (skills or comments)
        if target_type == 'skill':
            table = 'skills'
            id_column = 'skill_id'
        else:  # comment
            table = 'comments'
            id_column = 'comment_id'

        if vote_type == 'upvote':
            await conn.execute(
                f"""UPDATE {table}
                    SET upvotes = upvotes + 1,
                        vote_score = vote_score + 1
                    WHERE {id_column} = $1""",
                target_id
            )
        else:  # downvote
            await conn.execute(
                f"""UPDATE {table}
                    SET downvotes = downvotes + 1,
                        vote_score = vote_score - 1
                    WHERE {id_column} = $1""",
                target_id
            )

        # Get updated counts
        stats = await self.get_votes(conn, target_type, target_id)

        return {
            "success": True,
            "message": f"Successfully {vote_type}d",
            **stats
        }

    async def _change_vote(
        self,
        conn,
        existing_vote,
        target_type: str,
        target_id: str,
        agent_id: str,
        new_vote_type: str
    ) -> Dict[str, any]:
        """Handle changing an existing vote."""
        old_vote_type = existing_vote['vote_type']

        # If same vote type, no change needed
        if old_vote_type == new_vote_type:
            stats = await self.get_votes(conn, target_type, target_id)
            return {
                "success": True,
                "message": f"Already {new_vote_type}d",
                **stats
            }

        # Update vote record
        await conn.execute(
            """UPDATE votes
               SET vote_type = $1, updated_at = CURRENT_TIMESTAMP
               WHERE agent_id = $2 AND target_type = $3 AND target_id = $4""",
            new_vote_type, agent_id, target_type, target_id
        )

        # Update target table (skills or comments)
        if target_type == 'skill':
            table = 'skills'
            id_column = 'skill_id'
        else:  # comment
            table = 'comments'
            id_column = 'comment_id'

        # Adjust counts: remove old vote, add new vote
        if old_vote_type == 'upvote' and new_vote_type == 'downvote':
            # upvote -> downvote: decrease upvote, increase downvote, net change = -2
            await conn.execute(
                f"""UPDATE {table}
                    SET upvotes = upvotes - 1,
                        downvotes = downvotes + 1,
                        vote_score = vote_score - 2
                    WHERE {id_column} = $1""",
                target_id
            )
        else:  # downvote -> upvote
            # downvote -> upvote: decrease downvote, increase upvote, net change = +2
            await conn.execute(
                f"""UPDATE {table}
                    SET downvotes = downvotes - 1,
                        upvotes = upvotes + 1,
                        vote_score = vote_score + 2
                    WHERE {id_column} = $1""",
                target_id
            )

        # Get updated counts
        stats = await self.get_votes(conn, target_type, target_id)

        return {
            "success": True,
            "message": f"Changed from {old_vote_type} to {new_vote_type}",
            **stats
        }

    async def _cancel_vote(
        self,
        conn,
        existing_vote,
        target_type: str,
        target_id: str,
        agent_id: str
    ) -> Dict[str, any]:
        """Handle vote cancellation."""
        if not existing_vote:
            stats = await self.get_votes(conn, target_type, target_id)
            return {
                "success": True,
                "message": "No vote to cancel",
                **stats
            }

        old_vote_type = existing_vote['vote_type']

        # Delete vote record
        await conn.execute(
            "DELETE FROM votes WHERE agent_id = $1 AND target_type = $2 AND target_id = $3",
            agent_id, target_type, target_id
        )

        # Update target table (skills or comments)
        if target_type == 'skill':
            table = 'skills'
            id_column = 'skill_id'
        else:  # comment
            table = 'comments'
            id_column = 'comment_id'

        # Adjust counts
        if old_vote_type == 'upvote':
            await conn.execute(
                f"""UPDATE {table}
                    SET upvotes = upvotes - 1,
                        vote_score = vote_score - 1
                    WHERE {id_column} = $1""",
                target_id
            )
        else:  # downvote
            await conn.execute(
                f"""UPDATE {table}
                    SET downvotes = downvotes - 1,
                        vote_score = vote_score + 1
                    WHERE {id_column} = $1""",
                target_id
            )

        # Get updated counts
        stats = await self.get_votes(conn, target_type, target_id)

        return {
            "success": True,
            "message": "Vote cancelled",
            **stats
        }

    async def get_votes(
        self,
        conn,
        target_type: str,
        target_id: str
    ) -> Dict[str, int]:
        """
        Get vote statistics for a target.

        Args:
            conn: Database connection
            target_type: Type of target ('skill' or 'comment')
            target_id: ID of the skill or comment

        Returns:
            Dict with upvotes, downvotes, and vote_score counts
        """
        if target_type == 'skill':
            table = 'skills'
            id_column = 'skill_id'
        else:  # comment
            table = 'comments'
            id_column = 'comment_id'

        row = await conn.fetchrow(
            f"SELECT upvotes, downvotes, vote_score FROM {table} WHERE {id_column} = $1",
            target_id
        )

        if not row:
            return {
                "upvotes": 0,
                "downvotes": 0,
                "vote_score": 0
            }

        return {
            "upvotes": row['upvotes'],
            "downvotes": row['downvotes'],
            "vote_score": row['vote_score']
        }

    async def handle_duplicate_upload(
        self,
        skill_id: str,
        agent_did: str
    ) -> Dict[str, any]:
        """
        Handle automatic upvote for duplicate uploads.

        When an agent uploads a skill that already exists (same skill_id),
        automatically upvote the original skill.

        Args:
            skill_id: ID of the skill that was duplicated
            agent_did: DID of the agent who uploaded the duplicate

        Returns:
            Dict with operation results from vote()
        """
        return await self.vote(
            target_type='skill',
            target_id=skill_id,
            agent_did=agent_did,
            vote_type='upvote'
        )
