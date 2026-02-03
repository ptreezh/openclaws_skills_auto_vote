"""
Comment manager for Skills Arena.

Handles flat comment tree structure with parent_id references:
- Add comments and replies
- Retrieve comment trees with nested structure
- Vote on comments
- Support for threaded discussions on skills
"""
from typing import Dict, List, Optional, Any
from scripts.database.db import db
from scripts.vote_system import VoteSystem


class CommentManager:
    """Manages comment operations for skills."""

    def __init__(self):
        """Initialize the comment manager with vote system."""
        self.vote_system = VoteSystem()

    async def add_comment(
        self,
        skill_id: str,
        author_did: str,
        content: str,
        parent_comment_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add a comment or reply to a skill.

        Args:
            skill_id: ID of the skill being commented on
            author_did: DID of the agent creating the comment
            content: Comment content/text
            parent_comment_id: ID of parent comment (None for top-level comments)

        Returns:
            Dict with operation results including:
                - success: bool
                - comment_id: str
                - message: str
                - depth: int (nesting depth)

        Raises:
            ValueError: If invalid parameters provided
        """
        if not content or not content.strip():
            raise ValueError("Comment content cannot be empty")

        if not skill_id:
            raise ValueError("skill_id is required")

        async with db.get_connection() as conn:
            async with conn.transaction():
                # Get agent_id from did
                agent_id = await conn.fetchval(
                    "SELECT agent_id FROM agents WHERE did = $1",
                    author_did
                )

                if not agent_id:
                    return {
                        "success": False,
                        "message": "Agent not found",
                        "comment_id": None,
                        "depth": 0
                    }

                # Verify skill exists
                skill_exists = await conn.fetchval(
                    "SELECT skill_id FROM skills WHERE skill_id = $1",
                    skill_id
                )

                if not skill_exists:
                    return {
                        "success": False,
                        "message": "Skill not found",
                        "comment_id": None,
                        "depth": 0
                    }

                # Determine depth and thread structure
                depth = 0
                root_comment_id = None
                thread_id = None

                if parent_comment_id:
                    # Verify parent comment exists
                    parent = await conn.fetchrow(
                        """SELECT comment_id, depth, root_comment_id, thread_id
                           FROM comments
                           WHERE comment_id = $1""",
                        parent_comment_id
                    )

                    if not parent:
                        return {
                            "success": False,
                            "message": "Parent comment not found",
                            "comment_id": None,
                            "depth": 0
                        }

                    # Child is one level deeper than parent
                    depth = parent['depth'] + 1

                    # Inherit root_comment_id and thread_id from parent
                    root_comment_id = parent['root_comment_id'] or parent['comment_id']
                    thread_id = parent['thread_id'] or root_comment_id
                else:
                    # Top-level comment: thread_id is the comment_id itself
                    # We'll set this after generating the comment_id
                    pass

                # Generate comment_id (simple approach: use timestamp + random)
                import time
                import random
                comment_id = f"comment_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"

                # For top-level comments, thread_id = comment_id
                if not parent_comment_id:
                    thread_id = comment_id
                    root_comment_id = comment_id

                # Insert the comment
                await conn.execute(
                    """INSERT INTO comments
                       (comment_id, target_type, target_id, parent_comment_id,
                        root_comment_id, thread_id, agent_id, content, depth)
                       VALUES ($1, 'skill', $2, $3, $4, $5, $6, $7, $8)""",
                    comment_id, skill_id, parent_comment_id,
                    root_comment_id, thread_id, agent_id, content, depth
                )

                # Update skill's comments_count
                await conn.execute(
                    "UPDATE skills SET comments_count = comments_count + 1 WHERE skill_id = $1",
                    skill_id
                )

                # If this is a reply, update parent's replies_count
                if parent_comment_id:
                    await conn.execute(
                        "UPDATE comments SET replies_count = replies_count + 1 WHERE comment_id = $1",
                        parent_comment_id
                    )

                # Update agent's comments_count
                await conn.execute(
                    "UPDATE agents SET comments_count = comments_count + 1 WHERE agent_id = $1",
                    agent_id
                )

                return {
                    "success": True,
                    "comment_id": comment_id,
                    "message": "Comment added successfully",
                    "depth": depth
                }

    async def get_comments_tree(self, skill_id: str) -> List[Dict[str, Any]]:
        """
        Get all comments for a skill as a nested tree structure.

        Fetches all comments in a single query, then builds the tree in memory.
        Includes username and display_name from agents table.

        Args:
            skill_id: ID of the skill to get comments for

        Returns:
            List of top-level comments with nested 'replies' arrays.
            Each comment includes:
                - comment_id, content, depth, created_at
                - upvotes, downvotes, vote_score
                - username, display_name (from agents table)
                - replies: [] (array of nested replies)
        """
        async with db.get_connection() as conn:
            # Single query to fetch all comments for this skill with author info
            # Only fetch non-deleted comments
            rows = await conn.fetch(
                """SELECT
                    c.comment_id,
                    c.parent_comment_id,
                    c.content,
                    c.depth,
                    c.upvotes,
                    c.downvotes,
                    c.vote_score,
                    c.replies_count,
                    c.created_at,
                    a.agent_id,
                    a.username,
                    a.display_name
                   FROM comments c
                   JOIN agents a ON c.agent_id = a.agent_id
                   WHERE c.target_type = 'skill'
                   AND c.target_id = $1
                   AND c.is_deleted = FALSE
                   ORDER BY c.created_at ASC""",
                skill_id
            )

            # Convert to dict format for easier processing
            comments = []
            for row in rows:
                comments.append({
                    'comment_id': row['comment_id'],
                    'parent_comment_id': row['parent_comment_id'],
                    'content': row['content'],
                    'depth': row['depth'],
                    'upvotes': row['upvotes'],
                    'downvotes': row['downvotes'],
                    'vote_score': row['vote_score'],
                    'replies_count': row['replies_count'],
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                    'agent_id': row['agent_id'],
                    'username': row['username'],
                    'display_name': row['display_name'],
                    'replies': []
                })

            # Build tree structure in memory using parent -> children mapping
            # First, create a mapping of parent_id to children
            children_map: Dict[str, List[Dict]] = {}
            top_level_comments = []

            for comment in comments:
                parent_id = comment['parent_comment_id']

                if parent_id is None:
                    # This is a top-level comment
                    top_level_comments.append(comment)
                else:
                    # This is a reply - add to parent's children list
                    if parent_id not in children_map:
                        children_map[parent_id] = []
                    children_map[parent_id].append(comment)

            # Now recursively build the nested structure
            def build_tree(comment_list: List[Dict]) -> List[Dict]:
                """Recursively build nested comment tree."""
                for comment in comment_list:
                    comment_id = comment['comment_id']
                    if comment_id in children_map:
                        # Attach children as nested replies
                        comment['replies'] = build_tree(children_map[comment_id])
                    else:
                        # No replies
                        comment['replies'] = []
                return comment_list

            # Build the tree starting from top-level comments
            build_tree(top_level_comments)

            return top_level_comments

    async def vote_comment(
        self,
        comment_id: str,
        agent_did: str,
        vote_type: str
    ) -> Dict[str, Any]:
        """
        Vote on a comment (upvote or downvote).

        Uses the VoteSystem to handle voting logic.

        Args:
            comment_id: ID of the comment to vote on
            agent_did: DID of the agent casting the vote
            vote_type: Type of vote ('upvote', 'downvote', or 'cancel')

        Returns:
            Dict with operation results from VoteSystem.vote()
        """
        # Verify comment exists
        async with db.get_connection() as conn:
            comment_exists = await conn.fetchval(
                "SELECT comment_id FROM comments WHERE comment_id = $1",
                comment_id
            )

            if not comment_exists:
                return {
                    "success": False,
                    "message": "Comment not found",
                    "upvotes": 0,
                    "downvotes": 0,
                    "vote_score": 0
                }

        # Delegate to VoteSystem
        return await self.vote_system.vote(
            target_type='comment',
            target_id=comment_id,
            agent_did=agent_did,
            vote_type=vote_type
        )

    async def get_comment(
        self,
        comment_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a single comment by ID with author information.

        Args:
            comment_id: ID of the comment

        Returns:
            Dict with comment data or None if not found
        """
        async with db.get_connection() as conn:
            row = await conn.fetchrow(
                """SELECT
                    c.comment_id,
                    c.parent_comment_id,
                    c.target_id,
                    c.content,
                    c.depth,
                    c.upvotes,
                    c.downvotes,
                    c.vote_score,
                    c.replies_count,
                    c.created_at,
                    a.agent_id,
                    a.username,
                    a.display_name
                   FROM comments c
                   JOIN agents a ON c.agent_id = a.agent_id
                   WHERE c.comment_id = $1
                   AND c.is_deleted = FALSE""",
                comment_id
            )

            if not row:
                return None

            return {
                'comment_id': row['comment_id'],
                'parent_comment_id': row['parent_comment_id'],
                'target_id': row['target_id'],
                'content': row['content'],
                'depth': row['depth'],
                'upvotes': row['upvotes'],
                'downvotes': row['downvotes'],
                'vote_score': row['vote_score'],
                'replies_count': row['replies_count'],
                'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                'agent_id': row['agent_id'],
                'username': row['username'],
                'display_name': row['display_name']
            }
