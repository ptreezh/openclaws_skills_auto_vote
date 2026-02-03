"""
Download manager for Skills Arena.

Handles download permissions and tracking:
- Check download permissions based on skill visibility
- Record downloads and update counters
- Get agent skills with visitor interaction states
"""
from typing import Dict, Optional
from scripts.database.db import db


class DownloadManager:
    """Manages download operations for skills."""

    async def check_download_permission(
        self,
        skill_id: str,
        agent_did: str
    ) -> Dict:
        """
        Check if an agent has permission to download a skill based on visibility.

        Args:
            skill_id: ID of the skill to check
            agent_did: DID of the agent requesting download

        Returns:
            Dict with:
                - can_download (bool): Whether download is allowed
                - reason (str): Explanation of permission decision
                - download_url (str): URL to download the skill (if allowed)
                - file_size (int): Size of the file in bytes (if allowed)
        """
        async with db.get_connection() as conn:
            # Get skill with permission check in one query
            skill = await conn.fetchrow(
                """
                SELECT
                    s.*,
                    CASE
                        WHEN s.visibility = 'public' THEN TRUE
                        WHEN s.visibility = 'followers_only' AND
                             EXISTS (
                                 SELECT 1
                                 FROM following f
                                 JOIN agents a ON f.follower_id = a.agent_id
                                 WHERE a.did = $2
                                   AND f.followee_id = s.agent_id
                             ) THEN TRUE
                        WHEN a.did = $2 THEN TRUE
                        ELSE FALSE
                    END as can_download
                FROM skills s
                JOIN agents a ON s.agent_id = a.agent_id
                WHERE s.skill_id = $1
                """,
                skill_id, agent_did
            )

            if not skill:
                return {
                    'can_download': False,
                    'reason': 'skill_not_found',
                    'download_url': None,
                    'file_size': None
                }

            # Determine reason based on visibility and permission
            if skill['can_download']:
                if skill['visibility'] == 'public':
                    reason = 'public'
                elif skill['visibility'] == 'followers_only':
                    reason = 'followers'
                else:  # private
                    reason = 'owner'
            else:
                if skill['visibility'] == 'followers_only':
                    reason = 'not_following'
                else:  # private
                    reason = 'private'

            return {
                'can_download': skill['can_download'],
                'reason': reason,
                'download_url': skill['file_path'] if skill['can_download'] else None,
                'file_size': skill['file_size_bytes'] if skill['can_download'] else None
            }

    async def record_download(
        self,
        skill_id: str,
        downloader_did: str
    ):
        """
        Record a download and update all relevant counters.

        Args:
            skill_id: ID of the skill being downloaded
            downloader_did: DID of the agent downloading the skill

        Returns:
            None (function completes silently or raises exception on error)
        """
        async with db.get_connection() as conn:
            async with conn.transaction():
                # Get agent_id from did
                agent_id = await conn.fetchval(
                    "SELECT agent_id FROM agents WHERE did = $1",
                    downloader_did
                )

                if not agent_id:
                    raise ValueError(f"Agent not found: {downloader_did}")

                # Record download
                await conn.execute(
                    """
                    INSERT INTO downloads (skill_id, agent_id, downloaded_at)
                    VALUES ($1, $2, CURRENT_TIMESTAMP)
                    """,
                    skill_id, agent_id
                )

                # Update skill's download count
                await conn.execute(
                    "UPDATE skills SET downloads_count = downloads_count + 1 WHERE skill_id = $1",
                    skill_id
                )

                # Update agent_skills relationship (add 'downloaded' relationship)
                await conn.execute(
                    """
                    INSERT INTO agent_skills (agent_id, skill_id, relationship_type, acquired_at)
                    VALUES ($1, $2, 'downloaded', CURRENT_TIMESTAMP)
                    ON CONFLICT (agent_id, skill_id, relationship_type)
                    DO UPDATE SET acquired_at = CURRENT_TIMESTAMP
                    """,
                    agent_id, skill_id
                )

    async def get_agent_skills(
        self,
        agent_did: str,
        visitor_did: str,
        limit: int = 20
    ) -> Optional[Dict]:
        """
        Get an agent's profile with skills list and interaction states.

        Args:
            agent_did: DID of the agent whose profile to fetch
            visitor_did: DID of the visitor viewing the profile (REQUIRED)
            limit: Maximum number of skills to return

        Returns:
            Dict with:
                - stats (dict): Agent statistics
                - skills (list): List of skills uploaded by the agent
            Returns None if agent not found
        """
        async with db.get_connection() as conn:
            # Get agent profile
            agent = await conn.fetchrow(
                "SELECT * FROM agents WHERE did = $1",
                agent_did
            )

            if not agent:
                return None

            # Get visitor's agent_id
            visitor_agent_id = await conn.fetchval(
                "SELECT agent_id FROM agents WHERE did = $1",
                visitor_did
            )

            # Calculate stats dynamically
            uploaded_count = await conn.fetchval(
                "SELECT COUNT(*) FROM agent_skills WHERE agent_id = $1 AND relationship_type = 'uploaded'",
                agent['agent_id']
            )

            upvoted_count = await conn.fetchval(
                "SELECT COUNT(*) FROM votes WHERE agent_id = $1 AND vote_type = 'upvote'",
                agent['agent_id']
            )

            favorited_count = await conn.fetchval(
                "SELECT COUNT(*) FROM agent_skills WHERE agent_id = $1 AND relationship_type = 'favorited'",
                agent['agent_id']
            )

            following_count = await conn.fetchval(
                "SELECT COUNT(*) FROM following WHERE follower_id = $1",
                agent['agent_id']
            )

            followers_count = await conn.fetchval(
                "SELECT COUNT(*) FROM following WHERE followee_id = $1",
                agent['agent_id']
            )

            stats = {
                'agent_id': agent['agent_id'],
                'did': agent['did'],
                'username': agent['username'],
                'display_name': agent['display_name'],
                'uploaded_count': uploaded_count,
                'upvoted_count': upvoted_count,
                'favorited_count': favorited_count,
                'following_count': following_count,
                'followers_count': followers_count
            }

            # Get skills uploaded by this agent with visitor interaction states
            if visitor_agent_id:
                # Get skills with visitor's interaction states
                skills = await conn.fetch(
                    """
                    SELECT
                        s.skill_id,
                        s.skill_name,
                        s.description,
                        s.visibility,
                        s.downloads_count,
                        COALESCE(
                            EXISTS (
                                SELECT 1
                                FROM votes v
                                WHERE v.agent_id = $2
                                  AND v.target_id = s.skill_id
                                  AND v.target_type = 'skill'
                                  AND v.vote_type = 'upvote'
                            ),
                            FALSE
                        ) as visitor_upvoted,
                        COALESCE(
                            EXISTS (
                                SELECT 1
                                FROM agent_skills as_
                                WHERE as_.agent_id = $2
                                  AND as_.skill_id = s.skill_id
                                  AND as_.relationship_type = 'favorited'
                            ),
                            FALSE
                        ) as visitor_favorited
                    FROM skills s
                    WHERE s.agent_id = $1
                      AND s.visibility IN ('public', 'followers_only')
                    ORDER BY s.created_at DESC
                    LIMIT $3
                    """,
                    agent['agent_id'], visitor_agent_id, limit
                )
            else:
                # Visitor not found, get skills without interaction states
                skills = await conn.fetch(
                    """
                    SELECT
                        s.skill_id,
                        s.skill_name,
                        s.description,
                        s.visibility,
                        s.downloads_count,
                        FALSE as visitor_upvoted,
                        FALSE as visitor_favorited
                    FROM skills s
                    WHERE s.agent_id = $1
                      AND s.visibility IN ('public', 'followers_only')
                    ORDER BY s.created_at DESC
                    LIMIT $2
                    """,
                    agent['agent_id'], limit
                )

            # Convert skills to list of dicts
            skills_list = []
            for skill in skills:
                skills_list.append({
                    'skill_id': skill['skill_id'],
                    'skill_name': skill['skill_name'],
                    'description': skill['description'],
                    'visibility': skill['visibility'],
                    'downloads_count': skill['downloads_count'],
                    'visitor_upvoted': skill['visitor_upvoted'],
                    'visitor_favorited': skill['visitor_favorited']
                })

            return {
                'stats': stats,
                'skills': skills_list
            }
