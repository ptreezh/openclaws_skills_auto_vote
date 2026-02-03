"""
Tests for voting system.
"""
import pytest
import asyncio
from scripts.vote_system import VoteSystem
from scripts.database.db import db


@pytest.fixture
async def setup_test_data():
    """Set up test database with agents and skills."""
    # Initialize database connection
    await db.init()

    async with db.get_connection() as conn:
        # Clean up any existing test data
        await conn.execute("DELETE FROM votes WHERE agent_id LIKE 'test_%'")
        await conn.execute("DELETE FROM comments WHERE comment_id LIKE 'test_%'")
        await conn.execute("DELETE FROM skills WHERE skill_id LIKE 'test_%'")
        await conn.execute("DELETE FROM agents WHERE agent_id LIKE 'test_%'")

        # Create test agents
        await conn.execute("""
            INSERT INTO agents (agent_id, did, username, display_name)
            VALUES
                ('test_agent_1', 'did:openclaw:00000000000000000000000000000001', 'agent1', 'Agent 1'),
                ('test_agent_2', 'did:openclaw:00000000000000000000000000000002', 'agent2', 'Agent 2')
        """)

        # Create test skills
        await conn.execute("""
            INSERT INTO skills (skill_id, agent_id, skill_name, description, upvotes, downvotes, vote_score)
            VALUES
                ('test_skill_1', 'test_agent_1', 'Test Skill 1', 'Description 1', 0, 0, 0),
                ('test_skill_2', 'test_agent_1', 'Test Skill 2', 'Description 2', 0, 0, 0)
        """)

        # Create test comments
        await conn.execute("""
            INSERT INTO comments (comment_id, target_type, target_id, agent_id, content, upvotes, downvotes, vote_score)
            VALUES
                ('test_comment_1', 'skill', 'test_skill_1', 'test_agent_2', 'Great skill!', 0, 0, 0)
        """)

    yield

    # Cleanup
    async with db.get_connection() as conn:
        await conn.execute("DELETE FROM votes WHERE agent_id LIKE 'test_%'")
        await conn.execute("DELETE FROM comments WHERE comment_id LIKE 'test_%'")
        await conn.execute("DELETE FROM skills WHERE skill_id LIKE 'test_%'")
        await conn.execute("DELETE FROM agents WHERE agent_id LIKE 'test_%'")

    await db.close()


@pytest.mark.asyncio
async def test_upvote_skill(setup_test_data):
    """Test upvoting a skill."""
    vote_system = VoteSystem()

    # Upvote a skill
    result = await vote_system.vote(
        target_type='skill',
        target_id='test_skill_1',
        agent_did='did:openclaw:00000000000000000000000000000002',
        vote_type='upvote'
    )

    # Verify result
    assert result['success'] is True
    assert result['upvotes'] == 1
    assert result['downvotes'] == 0
    assert result['vote_score'] == 1
    assert 'successfully upvoted' in result['message'].lower()

    # Verify database state
    async with db.get_connection() as conn:
        skill = await conn.fetchrow(
            "SELECT upvotes, downvotes, vote_score FROM skills WHERE skill_id = 'test_skill_1'"
        )
        assert skill['upvotes'] == 1
        assert skill['downvotes'] == 0
        assert skill['vote_score'] == 1

        # Verify vote record exists
        vote = await conn.fetchrow(
            "SELECT vote_type FROM votes WHERE target_type = 'skill' AND target_id = 'test_skill_1' AND agent_id = 'test_agent_2'"
        )
        assert vote is not None
        assert vote['vote_type'] == 'upvote'


@pytest.mark.asyncio
async def test_downvote_skill(setup_test_data):
    """Test downvoting a skill."""
    vote_system = VoteSystem()

    # Downvote a skill
    result = await vote_system.vote(
        target_type='skill',
        target_id='test_skill_1',
        agent_did='did:openclaw:00000000000000000000000000000002',
        vote_type='downvote'
    )

    # Verify result
    assert result['success'] is True
    assert result['upvotes'] == 0
    assert result['downvotes'] == 1
    assert result['vote_score'] == -1
    assert 'successfully downvoted' in result['message'].lower()

    # Verify database state
    async with db.get_connection() as conn:
        skill = await conn.fetchrow(
            "SELECT upvotes, downvotes, vote_score FROM skills WHERE skill_id = 'test_skill_1'"
        )
        assert skill['upvotes'] == 0
        assert skill['downvotes'] == 1
        assert skill['vote_score'] == -1


@pytest.mark.asyncio
async def test_cancel_vote(setup_test_data):
    """Test canceling a vote."""
    vote_system = VoteSystem()

    # First, upvote a skill
    await vote_system.vote(
        target_type='skill',
        target_id='test_skill_1',
        agent_did='did:openclaw:00000000000000000000000000000002',
        vote_type='upvote'
    )

    # Now cancel the vote
    result = await vote_system.vote(
        target_type='skill',
        target_id='test_skill_1',
        agent_did='did:openclaw:00000000000000000000000000000002',
        vote_type='cancel'
    )

    # Verify result
    assert result['success'] is True
    assert result['upvotes'] == 0
    assert result['downvotes'] == 0
    assert result['vote_score'] == 0
    assert 'cancel' in result['message'].lower()

    # Verify database state
    async with db.get_connection() as conn:
        skill = await conn.fetchrow(
            "SELECT upvotes, downvotes, vote_score FROM skills WHERE skill_id = 'test_skill_1'"
        )
        assert skill['upvotes'] == 0
        assert skill['downvotes'] == 0
        assert skill['vote_score'] == 0

        # Verify vote record was deleted
        vote = await conn.fetchrow(
            "SELECT vote_type FROM votes WHERE target_type = 'skill' AND target_id = 'test_skill_1' AND agent_id = 'test_agent_2'"
        )
        assert vote is None


@pytest.mark.asyncio
async def test_change_vote(setup_test_data):
    """Test changing vote type (upvote -> downvote and vice versa)."""
    vote_system = VoteSystem()

    # First, upvote a skill
    await vote_system.vote(
        target_type='skill',
        target_id='test_skill_1',
        agent_did='did:openclaw:00000000000000000000000000000002',
        vote_type='upvote'
    )

    # Change to downvote
    result = await vote_system.vote(
        target_type='skill',
        target_id='test_skill_1',
        agent_did='did:openclaw:00000000000000000000000000000002',
        vote_type='downvote'
    )

    # Verify result
    assert result['success'] is True
    assert result['upvotes'] == 0
    assert result['downvotes'] == 1
    assert result['vote_score'] == -1
    assert 'changed from upvote to downvote' in result['message'].lower()

    # Change back to upvote
    result2 = await vote_system.vote(
        target_type='skill',
        target_id='test_skill_1',
        agent_did='did:openclaw:00000000000000000000000000000002',
        vote_type='upvote'
    )

    # Verify result
    assert result2['success'] is True
    assert result2['upvotes'] == 1
    assert result2['downvotes'] == 0
    assert result2['vote_score'] == 1
    assert 'changed from downvote to upvote' in result2['message'].lower()

    # Verify database state
    async with db.get_connection() as conn:
        skill = await conn.fetchrow(
            "SELECT upvotes, downvotes, vote_score FROM skills WHERE skill_id = 'test_skill_1'"
        )
        assert skill['upvotes'] == 1
        assert skill['downvotes'] == 0
        assert skill['vote_score'] == 1


@pytest.mark.asyncio
async def test_duplicate_upload_upvote(setup_test_data):
    """Test automatic upvote for duplicate uploads."""
    vote_system = VoteSystem()

    # Simulate duplicate upload (agent 2 uploads skill 1, which already exists)
    result = await vote_system.handle_duplicate_upload(
        skill_id='test_skill_1',
        agent_did='did:openclaw:00000000000000000000000000000002'
    )

    # Verify it's an upvote
    assert result['success'] is True
    assert result['upvotes'] == 1
    assert result['downvotes'] == 0
    assert result['vote_score'] == 1

    # Verify database state
    async with db.get_connection() as conn:
        skill = await conn.fetchrow(
            "SELECT upvotes, downvotes, vote_score FROM skills WHERE skill_id = 'test_skill_1'"
        )
        assert skill['upvotes'] == 1
        assert skill['downvotes'] == 0
        assert skill['vote_score'] == 1

        # Verify vote record exists
        vote = await conn.fetchrow(
            "SELECT vote_type FROM votes WHERE target_type = 'skill' AND target_id = 'test_skill_1' AND agent_id = 'test_agent_2'"
        )
        assert vote is not None
        assert vote['vote_type'] == 'upvote'


@pytest.mark.asyncio
async def test_vote_on_comment(setup_test_data):
    """Test voting on comments."""
    vote_system = VoteSystem()

    # Upvote a comment
    result = await vote_system.vote(
        target_type='comment',
        target_id='test_comment_1',
        agent_did='did:openclaw:00000000000000000000000000000001',
        vote_type='upvote'
    )

    # Verify result
    assert result['success'] is True
    assert result['upvotes'] == 1
    assert result['downvotes'] == 0
    assert result['vote_score'] == 1

    # Verify database state
    async with db.get_connection() as conn:
        comment = await conn.fetchrow(
            "SELECT upvotes, downvotes, vote_score FROM comments WHERE comment_id = 'test_comment_1'"
        )
        assert comment['upvotes'] == 1
        assert comment['downvotes'] == 0
        assert comment['vote_score'] == 1


@pytest.mark.asyncio
async def test_invalid_target_type(setup_test_data):
    """Test that invalid target type raises ValueError."""
    vote_system = VoteSystem()

    with pytest.raises(ValueError, match="Invalid target_type"):
        await vote_system.vote(
            target_type='invalid',
            target_id='test_skill_1',
            agent_did='did:openclaw:00000000000000000000000000000002',
            vote_type='upvote'
        )


@pytest.mark.asyncio
async def test_invalid_vote_type(setup_test_data):
    """Test that invalid vote type raises ValueError."""
    vote_system = VoteSystem()

    with pytest.raises(ValueError, match="Invalid vote_type"):
        await vote_system.vote(
            target_type='skill',
            target_id='test_skill_1',
            agent_did='did:openclaw:00000000000000000000000000000002',
            vote_type='invalid'
        )


@pytest.mark.asyncio
async def test_agent_not_found(setup_test_data):
    """Test voting with non-existent agent."""
    vote_system = VoteSystem()

    result = await vote_system.vote(
        target_type='skill',
        target_id='test_skill_1',
        agent_did='did:openclaw:ffffffffffffffffffffffffffffffff',
        vote_type='upvote'
    )

    # Verify result indicates failure
    assert result['success'] is False
    assert 'not found' in result['message'].lower()


@pytest.mark.asyncio
async def test_multiple_votes_different_agents(setup_test_data):
    """Test multiple agents voting on the same skill."""
    vote_system = VoteSystem()

    # Agent 2 upvotes
    await vote_system.vote(
        target_type='skill',
        target_id='test_skill_1',
        agent_did='did:openclaw:00000000000000000000000000000002',
        vote_type='upvote'
    )

    # Agent 1 downvotes (the skill author can also vote)
    result = await vote_system.vote(
        target_type='skill',
        target_id='test_skill_1',
        agent_did='did:openclaw:00000000000000000000000000000001',
        vote_type='downvote'
    )

    # Verify result
    assert result['success'] is True
    assert result['upvotes'] == 1
    assert result['downvotes'] == 1
    assert result['vote_score'] == 0

    # Verify database state
    async with db.get_connection() as conn:
        skill = await conn.fetchrow(
            "SELECT upvotes, downvotes, vote_score FROM skills WHERE skill_id = 'test_skill_1'"
        )
        assert skill['upvotes'] == 1
        assert skill['downvotes'] == 1
        assert skill['vote_score'] == 0


@pytest.mark.asyncio
async def test_same_vote_type_twice(setup_test_data):
    """Test voting the same way twice (should be idempotent)."""
    vote_system = VoteSystem()

    # Upvote once
    result1 = await vote_system.vote(
        target_type='skill',
        target_id='test_skill_1',
        agent_did='did:openclaw:00000000000000000000000000000002',
        vote_type='upvote'
    )

    # Try to upvote again
    result2 = await vote_system.vote(
        target_type='skill',
        target_id='test_skill_1',
        agent_did='did:openclaw:00000000000000000000000000000002',
        vote_type='upvote'
    )

    # Both should succeed with same counts
    assert result1['success'] is True
    assert result2['success'] is True
    assert result2['upvotes'] == 1
    assert result2['downvotes'] == 0
    assert result2['vote_score'] == 1
    assert 'already upvoted' in result2['message'].lower()


@pytest.mark.asyncio
async def test_cancel_without_voting(setup_test_data):
    """Test canceling a vote when no vote exists."""
    vote_system = VoteSystem()

    # Try to cancel without having voted
    result = await vote_system.vote(
        target_type='skill',
        target_id='test_skill_1',
        agent_did='did:openclaw:00000000000000000000000000000002',
        vote_type='cancel'
    )

    # Should succeed but indicate no vote to cancel
    assert result['success'] is True
    assert result['upvotes'] == 0
    assert result['downvotes'] == 0
    assert result['vote_score'] == 0
    assert 'no vote to cancel' in result['message'].lower()
