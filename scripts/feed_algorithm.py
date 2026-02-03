"""
Reddit-style Hot Algorithm and Feed System for Skills Arena.

This module implements the feed ranking algorithm used to display skills
in various orders (hot, new, top) similar to Reddit's feed system.
"""
import math
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from scripts.database.db import db


class FeedAlgorithm:
    """
    Reddit-style feed algorithm for ranking skills.

    Uses the Hot algorithm: log(|score|) + age/gravity
    where score = upvotes - downvotes and gravity = 1.8
    """

    GRAVITY = 1.8

    def __init__(self):
        """Initialize the feed algorithm."""
        pass

    def calculate_hot_score(self, upvotes: int, downvotes: int, created_at: datetime) -> float:
        """
        Calculate the hot score for a skill using Reddit's algorithm.

        The hot score combines the vote score with time decay to promote
        new and popular content while preventing older posts from dominating.

        Formula: log(|score|) + age/gravity
        - score = upvotes - downvotes
        - order = log10(max(abs(score), 1))
        - age = hours since creation
        - hot = order + (age / gravity)

        Args:
            upvotes: Number of upvotes
            downvotes: Number of downvotes
            created_at: Timestamp when the skill was created

        Returns:
            float: The calculated hot score rounded to 4 decimal places
        """
        # Calculate the net score
        score = upvotes - downvotes

        # Calculate the order (logarithmic scale for vote score)
        # Using max(abs(score), 1) to avoid log(0) and handle negative scores
        order = math.log(max(abs(score), 1), 10)

        # Calculate the age in hours
        age = (datetime.now() - created_at).total_seconds() / 3600

        # Calculate hot score with time decay
        hot = order + (age / self.GRAVITY)

        return round(hot, 4)

    async def update_hot_scores(self) -> Dict[str, int]:
        """
        Batch update all skills' hot scores in the database.

        This should be called periodically (e.g., every few minutes)
        to keep hot scores current as skills age and receive votes.

        Returns:
            dict with 'updated' count of skills processed
        """
        async with db.get_connection() as conn:
            # Fetch all skills with their vote counts and creation time
            rows = await conn.fetch("""
                SELECT skill_id, upvotes, downvotes, created_at
                FROM skills
                WHERE visibility = 'public'
            """)

            updated_count = 0

            # Update each skill's hot score
            for row in rows:
                hot_score = self.calculate_hot_score(
                    upvotes=row['upvotes'],
                    downvotes=row['downvotes'],
                    created_at=row['created_at']
                )

                await conn.execute("""
                    UPDATE skills
                    SET hot_score = $1
                    WHERE skill_id = $2
                """, hot_score, row['skill_id'])

                updated_count += 1

            return {'updated': updated_count}

    async def get_feed(
        self,
        sort_by: str = 'hot',
        community: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """
        Get a feed of skills with uploader information.

        Args:
            sort_by: How to sort the feed - 'hot', 'new', or 'top'
                - 'hot': Sort by hot score (Reddit algorithm)
                - 'new': Sort by creation time (newest first)
                - 'top': Sort by vote score (most upvoted)
            community: Optional filter by community/category
            limit: Maximum number of skills to return (default: 50)
            offset: Number of skills to skip for pagination (default: 0)

        Returns:
            List of dictionaries containing skill data with uploader_name

        Raises:
            ValueError: If sort_by is not one of 'hot', 'new', 'top'
        """
        # Validate sort_by parameter
        valid_sort_options = ['hot', 'new', 'top']
        if sort_by not in valid_sort_options:
            raise ValueError(
                f"Invalid sort_by '{sort_by}'. Must be one of: {', '.join(valid_sort_options)}"
            )

        # Determine sort column and direction
        if sort_by == 'hot':
            order_by = "hot_score DESC"
        elif sort_by == 'new':
            order_by = "created_at DESC"
        elif sort_by == 'top':
            order_by = "vote_score DESC"

        # Build the query with community filter if provided
        community_filter = ""
        params = [limit, offset]

        if community:
            community_filter = "AND s.community = $3"
            params.insert(0, community)

        async with db.get_connection() as conn:
            query = f"""
                SELECT
                    s.skill_id,
                    s.skill_name,
                    s.description,
                    s.upvotes,
                    s.downvotes,
                    s.vote_score,
                    s.hot_score,
                    s.created_at,
                    s.community,
                    s.categories,
                    s.visibility,
                    s.rating,
                    s.usage_count,
                    s.comments_count,
                    s.views,
                    s.downloads_count,
                    a.username AS uploader_name,
                    a.display_name AS uploader_display_name,
                    a.agent_id AS uploader_id
                FROM skills s
                JOIN agents a ON s.agent_id = a.agent_id
                WHERE s.visibility = 'public'
                {community_filter}
                ORDER BY {order_by}
                LIMIT $1 OFFSET $2
            """

            rows = await conn.fetch(query, *params)

            # Convert to list of dictionaries
            feed = [dict(row) for row in rows]

            return feed


# Singleton instance
feed_algorithm = FeedAlgorithm()
