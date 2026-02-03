"""
Tests for download manager.
"""
import pytest
import asyncio
from scripts.download_manager import DownloadManager
from scripts.database.db import db


@pytest.fixture
async def setup_test_data():
    """Set up test database with agents, skills, and following relationships."""
    # Initialize database connection
    await db.init()

    async with db.get_connection() as conn:
        # Clean up any existing test data
        await conn.execute("DELETE FROM downloads WHERE agent_id LIKE 'test_%'")
        await conn.execute("DELETE FROM agent_skills WHERE agent_id LIKE 'test_%'")
        await conn.execute("DELETE FROM following WHERE follower_id LIKE 'test_%' OR followee_id LIKE 'test_%'")
        await conn.execute("DELETE FROM skills WHERE skill_id LIKE 'test_%'")
        await conn.execute("DELETE FROM agents WHERE agent_id LIKE 'test_%'")

        # Create test agents
        await conn.execute("""
            INSERT INTO agents (agent_id, did, username, display_name, skills_uploaded, skills_downloaded, karma)
            VALUES
                ('test_agent_1', 'did:openclaw:00000000000000000000000000000001', 'agent1', 'Agent 1', 0, 0, 100),
                ('test_agent_2', 'did:openclaw:00000000000000000000000000000002', 'agent2', 'Agent 2', 0, 0, 50),
                ('test_agent_3', 'did:openclaw:00000000000000000000000000000003', 'agent3', 'Agent 3', 0, 0, 25)
        """)

        # Create test skills with different visibility levels
        await conn.execute("""
            INSERT INTO skills (
                skill_id, agent_id, skill_name, description,
                visibility, file_size_bytes, file_path,
                upvotes, downvotes, vote_score, downloads_count
            )
            VALUES
                ('test_skill_public', 'test_agent_1', 'Public Skill', 'A public skill',
                 'public', 1024000, '/skills/public.zip', 10, 2, 8, 5),
                ('test_skill_followers', 'test_agent_1', 'Followers Only', 'Followers only skill',
                 'followers_only', 2048000, '/skills/followers.zip', 5, 0, 5, 2),
                ('test_skill_private', 'test_agent_1', 'Private Skill', 'Private skill',
                 'private', 512000, '/skills/private.zip', 0, 0, 0, 0),
                ('test_skill_agent2', 'test_agent_2', 'Agent2 Skill', 'Skill by agent2',
                 'public', 3072000, '/skills/agent2.zip', 3, 1, 2, 1)
        """)

        # Create following relationships: agent2 follows agent1, agent3 follows agent2
        await conn.execute("""
            INSERT INTO following (follower_id, followee_id)
            VALUES
                ('test_agent_2', 'test_agent_1'),
                ('test_agent_3', 'test_agent_2')
        """)

    yield

    # Cleanup
    async with db.get_connection() as conn:
        await conn.execute("DELETE FROM downloads WHERE agent_id LIKE 'test_%'")
        await conn.execute("DELETE FROM agent_skills WHERE agent_id LIKE 'test_%'")
        await conn.execute("DELETE FROM following WHERE follower_id LIKE 'test_%' OR followee_id LIKE 'test_%'")
        await conn.execute("DELETE FROM skills WHERE skill_id LIKE 'test_%'")
        await conn.execute("DELETE FROM agents WHERE agent_id LIKE 'test_%'")

    await db.close()


@pytest.mark.asyncio
async def test_check_download_permission_public(setup_test_data):
    """Test download permission for public skill."""
    download_manager = DownloadManager()

    # Public skill: anyone can download
    result = await download_manager.check_download_permission(
        skill_id='test_skill_public',
        agent_did='did:openclaw:00000000000000000000000000000002'
    )

    assert result['can_download'] is True
    assert result['reason'] == 'public_skill'
    assert result['download_url'] == '/skills/public.zip'
    assert result['file_size'] == 1024000


@pytest.mark.asyncio
async def test_check_download_permission_followers_only_allowed(setup_test_data):
    """Test download permission for followers_only skill - follower can download."""
    download_manager = DownloadManager()

    # agent2 follows agent1, so can download followers_only skill
    result = await download_manager.check_download_permission(
        skill_id='test_skill_followers',
        agent_did='did:openclaw:00000000000000000000000000000002'
    )

    assert result['can_download'] is True
    assert result['reason'] == 'followers_only_skill'
    assert result['download_url'] == '/skills/followers.zip'
    assert result['file_size'] == 2048000


@pytest.mark.asyncio
async def test_check_download_permission_followers_only_denied(setup_test_data):
    """Test download permission for followers_only skill - non-follower cannot download."""
    download_manager = DownloadManager()

    # agent3 does NOT follow agent1, so cannot download
    result = await download_manager.check_download_permission(
        skill_id='test_skill_followers',
        agent_did='did:openclaw:00000000000000000000000000000003'
    )

    assert result['can_download'] is False
    assert result['reason'] == 'followers_only_restricted'
    assert result['download_url'] is None
    assert result['file_size'] is None


@pytest.mark.asyncio
async def test_check_download_permission_private_owner(setup_test_data):
    """Test download permission for private skill - owner can download."""
    download_manager = DownloadManager()

    # Owner can download their private skill
    result = await download_manager.check_download_permission(
        skill_id='test_skill_private',
        agent_did='did:openclaw:00000000000000000000000000000001'
    )

    assert result['can_download'] is True
    assert result['reason'] == 'private_skill_owner'
    assert result['download_url'] == '/skills/private.zip'
    assert result['file_size'] == 512000


@pytest.mark.asyncio
async def test_check_download_permission_private_denied(setup_test_data):
    """Test download permission for private skill - non-owner cannot download."""
    download_manager = DownloadManager()

    # Non-owner cannot download private skill
    result = await download_manager.check_download_permission(
        skill_id='test_skill_private',
        agent_did='did:openclaw:00000000000000000000000000000002'
    )

    assert result['can_download'] is False
    assert result['reason'] == 'private_restricted'
    assert result['download_url'] is None
    assert result['file_size'] is None


@pytest.mark.asyncio
async def test_check_download_permission_skill_not_found(setup_test_data):
    """Test download permission for non-existent skill."""
    download_manager = DownloadManager()

    result = await download_manager.check_download_permission(
        skill_id='nonexistent_skill',
        agent_did='did:openclaw:00000000000000000000000000000001'
    )

    assert result['can_download'] is False
    assert result['reason'] == 'skill_not_found'
    assert result['download_url'] is None
    assert result['file_size'] is None


@pytest.mark.asyncio
async def test_record_download_success(setup_test_data):
    """Test recording a download successfully."""
    download_manager = DownloadManager()

    # Record download
    result = await download_manager.record_download(
        skill_id='test_skill_public',
        downloader_did='did:openclaw:00000000000000000000000000000002',
        download_source='feed'
    )

    assert result['success'] is True
    assert result['download_count'] == 6  # Started with 5, now 6
    assert 'successfully' in result['message'].lower()

    # Verify database state
    async with db.get_connection() as conn:
        # Check downloads table
        download = await conn.fetchrow(
            """SELECT * FROM downloads
               WHERE skill_id = 'test_skill_public'
               AND agent_id = 'test_agent_2'
               ORDER BY downloaded_at DESC
               LIMIT 1"""
        )
        assert download is not None
        assert download['skill_id'] == 'test_skill_public'
        assert download['agent_id'] == 'test_agent_2'
        assert download['download_source'] == 'feed'

        # Check skills table
        skill = await conn.fetchrow(
            "SELECT downloads_count FROM skills WHERE skill_id = 'test_skill_public'"
        )
        assert skill['downloads_count'] == 6

        # Check agent_skills table
        agent_skill = await conn.fetchrow(
            """SELECT * FROM agent_skills
               WHERE agent_id = 'test_agent_2'
               AND skill_id = 'test_skill_public'
               AND relationship_type = 'downloaded'"""
        )
        assert agent_skill is not None

        # Check agents table
        agent = await conn.fetchrow(
            "SELECT skills_downloaded FROM agents WHERE agent_id = 'test_agent_2'"
        )
        assert agent['skills_downloaded'] == 1


@pytest.mark.asyncio
async def test_record_download_agent_not_found(setup_test_data):
    """Test recording download with non-existent agent."""
    download_manager = DownloadManager()

    result = await download_manager.record_download(
        skill_id='test_skill_public',
        downloader_did='did:openclaw:ffffffffffffffffffffffffffffffff'
    )

    assert result['success'] is False
    assert 'not found' in result['message'].lower()
    assert result['download_count'] == 0


@pytest.mark.asyncio
async def test_record_download_skill_not_found(setup_test_data):
    """Test recording download for non-existent skill."""
    download_manager = DownloadManager()

    result = await download_manager.record_download(
        skill_id='nonexistent_skill',
        downloader_did='did:openclaw:00000000000000000000000000000001'
    )

    assert result['success'] is False
    assert 'not found' in result['message'].lower()
    assert result['download_count'] == 0


@pytest.mark.asyncio
async def test_record_download_duplicate(setup_test_data):
    """Test recording the same download multiple times."""
    download_manager = DownloadManager()

    # First download
    result1 = await download_manager.record_download(
        skill_id='test_skill_public',
        downloader_did='did:openclaw:00000000000000000000000000000002'
    )
    assert result1['success'] is True
    assert result1['download_count'] == 6

    # Second download (should add another record)
    result2 = await download_manager.record_download(
        skill_id='test_skill_public',
        downloader_did='did:openclaw:00000000000000000000000000000002'
    )
    assert result2['success'] is True
    assert result2['download_count'] == 7

    # Verify both downloads were recorded
    async with db.get_connection() as conn:
        count = await conn.fetchval(
            """SELECT COUNT(*) FROM downloads
               WHERE skill_id = 'test_skill_public'
               AND agent_id = 'test_agent_2'"""
        )
        assert count == 2


@pytest.mark.asyncio
async def test_get_agent_skills_success(setup_test_data):
    """Test getting agent's skills successfully."""
    download_manager = DownloadManager()

    result = await download_manager.get_agent_skills(
        agent_did='did:openclaw:00000000000000000000000000000001',
        visitor_did='did:openclaw:00000000000000000000000000000002',
        limit=10
    )

    assert result is not None
    assert 'stats' in result
    assert 'skills' in result

    # Check stats
    stats = result['stats']
    assert stats['did'] == 'did:openclaw:00000000000000000000000000000001'
    assert stats['username'] == 'agent1'
    assert stats['display_name'] == 'Agent 1'
    assert stats['karma'] == 100
    assert stats['skills_uploaded_count'] == 0
    assert stats['followers_count'] == 1  # agent2 follows agent1

    # Check skills
    skills = result['skills']
    assert len(skills) == 3  # agent1 has 3 skills (all but agent2's skill)
    skill_ids = [s['skill_id'] for s in skills]
    assert 'test_skill_public' in skill_ids
    assert 'test_skill_followers' in skill_ids
    assert 'test_skill_private' in skill_ids


@pytest.mark.asyncio
async def test_get_agent_skills_no_visitor(setup_test_data):
    """Test getting agent's skills without visitor interaction states."""
    download_manager = DownloadManager()

    result = await download_manager.get_agent_skills(
        agent_did='did:openclaw:00000000000000000000000000000001',
        visitor_did=None,
        limit=10
    )

    assert result is not None
    assert 'stats' in result
    assert 'skills' in result

    # Check that all interaction states are False when no visitor
    skills = result['skills']
    for skill in skills:
        assert skill['visitor_uploaded'] is False
        assert skill['visitor_downloaded'] is False
        assert skill['visitor_favorited'] is False


@pytest.mark.asyncio
async def test_get_agent_skills_with_visitor_interactions(setup_test_data):
    """Test getting agent's skills with visitor who has interacted."""
    download_manager = DownloadManager()

    # First, have visitor download a skill
    await download_manager.record_download(
        skill_id='test_skill_public',
        downloader_did='did:openclaw:00000000000000000000000000000002'
    )

    # Get agent's skills
    result = await download_manager.get_agent_skills(
        agent_did='did:openclaw:00000000000000000000000000000001',
        visitor_did='did:openclaw:00000000000000000000000000000002',
        limit=10
    )

    assert result is not None
    skills = result['skills']

    # Find the public skill
    public_skill = next((s for s in skills if s['skill_id'] == 'test_skill_public'), None)
    assert public_skill is not None

    # Visitor should have downloaded it
    assert public_skill['visitor_downloaded'] is True
    assert public_skill['visitor_uploaded'] is False
    assert public_skill['visitor_favorited'] is False


@pytest.mark.asyncio
async def test_get_agent_skills_visibility_filtering(setup_test_data):
    """Test that private skills are filtered for non-owners."""
    download_manager = DownloadManager()

    # Get agent1's skills as agent3 (not following agent1)
    result = await download_manager.get_agent_skills(
        agent_did='did:openclaw:00000000000000000000000000000001',
        visitor_did='did:openclaw:00000000000000000000000000000003',
        limit=10
    )

    assert result is not None
    skills = result['skills']

    # Should only see public and followers_only skills (not private)
    # Note: followers_only is still visible in the list, permission check happens at download
    skill_visibilities = [s['visibility'] for s in skills]
    assert 'public' in skill_visibilities
    # Private should not be in the list
    assert 'private' not in skill_visibilities


@pytest.mark.asyncio
async def test_get_agent_skills_pagination(setup_test_data):
    """Test pagination of agent skills."""
    download_manager = DownloadManager()

    # Get only 2 skills
    result = await download_manager.get_agent_skills(
        agent_did='did:openclaw:00000000000000000000000000000001',
        visitor_did=None,
        limit=2
    )

    assert result is not None
    skills = result['skills']
    assert len(skills) == 2  # Limited to 2


@pytest.mark.asyncio
async def test_get_agent_skills_not_found(setup_test_data):
    """Test getting skills for non-existent agent."""
    download_manager = DownloadManager()

    result = await download_manager.get_agent_skills(
        agent_did='did:openclaw:ffffffffffffffffffffffffffffffff',
        visitor_did=None,
        limit=10
    )

    assert result is None


@pytest.mark.asyncio
async def test_check_download_permission_all_visibility_levels(setup_test_data):
    """Test all visibility levels in one comprehensive test."""
    download_manager = DownloadManager()

    # Test as agent1 (owner of all skills)
    public_result = await download_manager.check_download_permission(
        'test_skill_public',
        'did:openclaw:00000000000000000000000000000001'
    )
    assert public_result['can_download'] is True
    assert public_result['reason'] == 'public_skill'

    followers_result = await download_manager.check_download_permission(
        'test_skill_followers',
        'did:openclaw:00000000000000000000000000000001'
    )
    assert followers_result['can_download'] is True
    assert followers_result['reason'] == 'followers_only_skill'

    private_result = await download_manager.check_download_permission(
        'test_skill_private',
        'did:openclaw:00000000000000000000000000000001'
    )
    assert private_result['can_download'] is True
    assert private_result['reason'] == 'private_skill_owner'

    # Test as agent2 (follower of agent1)
    public_result2 = await download_manager.check_download_permission(
        'test_skill_public',
        'did:openclaw:00000000000000000000000000000002'
    )
    assert public_result2['can_download'] is True
    assert public_result2['reason'] == 'public_skill'

    followers_result2 = await download_manager.check_download_permission(
        'test_skill_followers',
        'did:openclaw:00000000000000000000000000000002'
    )
    assert followers_result2['can_download'] is True
    assert followers_result2['reason'] == 'followers_only_skill'

    private_result2 = await download_manager.check_download_permission(
        'test_skill_private',
        'did:openclaw:00000000000000000000000000000002'
    )
    assert private_result2['can_download'] is False
    assert private_result2['reason'] == 'private_restricted'

    # Test as agent3 (not following agent1)
    public_result3 = await download_manager.check_download_permission(
        'test_skill_public',
        'did:openclaw:00000000000000000000000000000003'
    )
    assert public_result3['can_download'] is True

    followers_result3 = await download_manager.check_download_permission(
        'test_skill_followers',
        'did:openclaw:00000000000000000000000000000003'
    )
    assert followers_result3['can_download'] is False
    assert followers_result3['reason'] == 'followers_only_restricted'


@pytest.mark.asyncio
async def test_record_download_updates_agent_stats(setup_test_data):
    """Test that recording download updates all agent statistics correctly."""
    download_manager = DownloadManager()

    # Record multiple downloads
    await download_manager.record_download(
        skill_id='test_skill_public',
        downloader_did='did:openclaw:00000000000000000000000000000002'
    )
    await download_manager.record_download(
        skill_id='test_skill_agent2',
        downloader_did='did:openclaw:00000000000000000000000000000002'
    )

    # Check agent stats
    async with db.get_connection() as conn:
        agent = await conn.fetchrow(
            "SELECT skills_downloaded FROM agents WHERE agent_id = 'test_agent_2'"
        )
        assert agent['skills_downloaded'] == 2

        # Check skill stats
        skill1 = await conn.fetchrow(
            "SELECT downloads_count FROM skills WHERE skill_id = 'test_skill_public'"
        )
        assert skill1['downloads_count'] == 6

        skill2 = await conn.fetchrow(
            "SELECT downloads_count FROM skills WHERE skill_id = 'test_skill_agent2'"
        )
        assert skill2['downloads_count'] == 2


@pytest.mark.asyncio
async def test_get_agent_skills_includes_all_fields(setup_test_data):
    """Test that agent skills response includes all required fields."""
    download_manager = DownloadManager()

    result = await download_manager.get_agent_skills(
        agent_did='did:openclaw:00000000000000000000000000000001',
        visitor_did=None,
        limit=10
    )

    assert result is not None
    stats = result['stats']

    # Check all stats fields
    required_stats_fields = [
        'did', 'username', 'display_name', 'bio', 'avatar_url',
        'karma', 'skills_uploaded_count', 'skills_downloaded_count',
        'comments_count', 'votes_cast', 'followers_count', 'following_count',
        'is_verified', 'created_at', 'last_active'
    ]
    for field in required_stats_fields:
        assert field in stats

    # Check skills
    skills = result['skills']
    if len(skills) > 0:
        skill = skills[0]
        required_skill_fields = [
            'skill_id', 'skill_name', 'description', 'version',
            'rating', 'usage_count', 'avg_response_time', 'success_rate',
            'upvotes', 'downvotes', 'vote_score', 'hot_score', 'controversy',
            'visibility', 'community', 'categories', 'comments_count',
            'views', 'downloads_count', 'file_size_bytes', 'file_path',
            'created_at', 'updated_at', 'visitor_uploaded',
            'visitor_downloaded', 'visitor_favorited'
        ]
        for field in required_skill_fields:
            assert field in skill
