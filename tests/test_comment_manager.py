"""
Tests for comment manager.
"""
import pytest
import asyncio
from scripts.comment_manager import CommentManager
from scripts.database.db import db


@pytest.fixture
async def setup_test_data():
    """Set up test database with agents and skills."""
    # Initialize database connection
    await db.init()

    async with db.get_connection() as conn:
        # Clean up any existing test data
        await conn.execute("DELETE FROM votes WHERE agent_id LIKE 'test_%'")
        await conn.execute("DELETE FROM comments WHERE comment_id LIKE 'test_%' OR comment_id LIKE 'comment_%'")
        await conn.execute("DELETE FROM skills WHERE skill_id LIKE 'test_%'")
        await conn.execute("DELETE FROM agents WHERE agent_id LIKE 'test_%'")

        # Create test agents
        await conn.execute("""
            INSERT INTO agents (agent_id, did, username, display_name, comments_count)
            VALUES
                ('test_agent_1', 'did:openclaw:00000000000000000000000000000001', 'agent1', 'Agent 1', 0),
                ('test_agent_2', 'did:openclaw:00000000000000000000000000000002', 'agent2', 'Agent 2', 0)
        """)

        # Create test skills
        await conn.execute("""
            INSERT INTO skills (skill_id, agent_id, skill_name, description, upvotes, downvotes, vote_score, comments_count)
            VALUES
                ('test_skill_1', 'test_agent_1', 'Test Skill 1', 'Description 1', 0, 0, 0, 0),
                ('test_skill_2', 'test_agent_1', 'Test Skill 2', 'Description 2', 0, 0, 0, 0)
        """)

    yield

    # Cleanup
    async with db.get_connection() as conn:
        await conn.execute("DELETE FROM votes WHERE agent_id LIKE 'test_%'")
        await conn.execute("DELETE FROM comments WHERE comment_id LIKE 'test_%' OR comment_id LIKE 'comment_%'")
        await conn.execute("DELETE FROM skills WHERE skill_id LIKE 'test_%'")
        await conn.execute("DELETE FROM agents WHERE agent_id LIKE 'test_%'")

    await db.close()


@pytest.mark.asyncio
async def test_add_comment(setup_test_data):
    """Test adding a top-level comment."""
    comment_manager = CommentManager()

    # Add a top-level comment
    result = await comment_manager.add_comment(
        skill_id='test_skill_1',
        author_did='did:openclaw:00000000000000000000000000000002',
        content='Great skill! Very useful.'
    )

    # Verify result
    assert result['success'] is True
    assert result['comment_id'] is not None
    assert result['depth'] == 0
    assert 'successfully' in result['message'].lower()

    # Verify database state
    async with db.get_connection() as conn:
        comment = await conn.fetchrow(
            """SELECT comment_id, content, depth, parent_comment_id, replies_count
               FROM comments WHERE comment_id = $1""",
            result['comment_id']
        )
        assert comment is not None
        assert comment['content'] == 'Great skill! Very useful.'
        assert comment['depth'] == 0
        assert comment['parent_comment_id'] is None
        assert comment['replies_count'] == 0

        # Verify skill's comments_count was updated
        skill = await conn.fetchrow(
            "SELECT comments_count FROM skills WHERE skill_id = 'test_skill_1'"
        )
        assert skill['comments_count'] == 1

        # Verify agent's comments_count was updated
        agent = await conn.fetchrow(
            "SELECT comments_count FROM agents WHERE agent_id = 'test_agent_2'"
        )
        assert agent['comments_count'] == 1


@pytest.mark.asyncio
async def test_add_reply(setup_test_data):
    """Test adding a reply to a comment."""
    comment_manager = CommentManager()

    # First, add a top-level comment
    parent_result = await comment_manager.add_comment(
        skill_id='test_skill_1',
        author_did='did:openclaw:00000000000000000000000000000002',
        content='Great skill!'
    )

    parent_comment_id = parent_result['comment_id']

    # Now add a reply
    reply_result = await comment_manager.add_comment(
        skill_id='test_skill_1',
        author_did='did:openclaw:00000000000000000000000000000001',
        content='Thanks! I worked hard on it.',
        parent_comment_id=parent_comment_id
    )

    # Verify reply result
    assert reply_result['success'] is True
    assert reply_result['comment_id'] is not None
    assert reply_result['depth'] == 1
    assert 'successfully' in reply_result['message'].lower()

    # Verify database state
    async with db.get_connection() as conn:
        reply = await conn.fetchrow(
            """SELECT comment_id, content, depth, parent_comment_id
               FROM comments WHERE comment_id = $1""",
            reply_result['comment_id']
        )
        assert reply is not None
        assert reply['content'] == 'Thanks! I worked hard on it.'
        assert reply['depth'] == 1
        assert reply['parent_comment_id'] == parent_comment_id

        # Verify parent's replies_count was updated
        parent = await conn.fetchrow(
            "SELECT replies_count FROM comments WHERE comment_id = $1",
            parent_comment_id
        )
        assert parent['replies_count'] == 1


@pytest.mark.asyncio
async def test_add_nested_reply(setup_test_data):
    """Test adding a nested reply (reply to a reply)."""
    comment_manager = CommentManager()

    # Add top-level comment
    parent_result = await comment_manager.add_comment(
        skill_id='test_skill_1',
        author_did='did:openclaw:00000000000000000000000000000002',
        content='Great skill!'
    )

    parent_comment_id = parent_result['comment_id']

    # Add first-level reply
    reply1_result = await comment_manager.add_comment(
        skill_id='test_skill_1',
        author_did='did:openclaw:00000000000000000000000000000001',
        content='Thanks!',
        parent_comment_id=parent_comment_id
    )

    # Add second-level reply
    reply2_result = await comment_manager.add_comment(
        skill_id='test_skill_1',
        author_did='did:openclaw:00000000000000000000000000000002',
        content='You\'re welcome!',
        parent_comment_id=reply1_result['comment_id']
    )

    # Verify depth
    assert reply2_result['depth'] == 2

    # Verify database state
    async with db.get_connection() as conn:
        reply2 = await conn.fetchrow(
            """SELECT comment_id, depth, parent_comment_id
               FROM comments WHERE comment_id = $1""",
            reply2_result['comment_id']
        )
        assert reply2 is not None
        assert reply2['depth'] == 2
        assert reply2['parent_comment_id'] == reply1_result['comment_id']


@pytest.mark.asyncio
async def test_get_comments_tree(setup_test_data):
    """Test getting comment tree with nested structure."""
    comment_manager = CommentManager()

    # Add top-level comment
    comment1 = await comment_manager.add_comment(
        skill_id='test_skill_1',
        author_did='did:openclaw:00000000000000000000000000000002',
        content='First comment'
    )

    # Add reply to first comment
    reply1 = await comment_manager.add_comment(
        skill_id='test_skill_1',
        author_did='did:openclaw:00000000000000000000000000000001',
        content='Reply to first',
        parent_comment_id=comment1['comment_id']
    )

    # Add another top-level comment
    comment2 = await comment_manager.add_comment(
        skill_id='test_skill_1',
        author_did='did:openclaw:00000000000000000000000000000001',
        content='Second comment'
    )

    # Get comment tree
    tree = await comment_manager.get_comments_tree('test_skill_1')

    # Verify structure
    assert len(tree) == 2  # Two top-level comments

    # Find first comment in tree
    first_comment = next((c for c in tree if c['comment_id'] == comment1['comment_id']), None)
    assert first_comment is not None
    assert first_comment['content'] == 'First comment'
    assert first_comment['username'] == 'agent2'
    assert first_comment['display_name'] == 'Agent 2'
    assert first_comment['depth'] == 0
    assert len(first_comment['replies']) == 1

    # Verify nested reply
    first_reply = first_comment['replies'][0]
    assert first_reply['comment_id'] == reply1['comment_id']
    assert first_reply['content'] == 'Reply to first'
    assert first_reply['username'] == 'agent1'
    assert first_reply['display_name'] == 'Agent 1'
    assert first_reply['depth'] == 1
    assert len(first_reply['replies']) == 0

    # Verify second comment has no replies
    second_comment = next((c for c in tree if c['comment_id'] == comment2['comment_id']), None)
    assert second_comment is not None
    assert second_comment['content'] == 'Second comment'
    assert len(second_comment['replies']) == 0


@pytest.mark.asyncio
async def test_get_comments_tree_empty(setup_test_data):
    """Test getting comment tree when no comments exist."""
    comment_manager = CommentManager()

    # Get comment tree for skill with no comments
    tree = await comment_manager.get_comments_tree('test_skill_1')

    # Verify empty list
    assert tree == []


@pytest.mark.asyncio
async def test_vote_comment(setup_test_data):
    """Test voting on a comment."""
    comment_manager = CommentManager()

    # Add a comment
    comment_result = await comment_manager.add_comment(
        skill_id='test_skill_1',
        author_did='did:openclaw:00000000000000000000000000000002',
        content='Great skill!'
    )

    comment_id = comment_result['comment_id']

    # Upvote the comment
    vote_result = await comment_manager.vote_comment(
        comment_id=comment_id,
        agent_did='did:openclaw:00000000000000000000000000000001',
        vote_type='upvote'
    )

    # Verify vote result
    assert vote_result['success'] is True
    assert vote_result['upvotes'] == 1
    assert vote_result['downvotes'] == 0
    assert vote_result['vote_score'] == 1

    # Verify database state
    async with db.get_connection() as conn:
        comment = await conn.fetchrow(
            "SELECT upvotes, downvotes, vote_score FROM comments WHERE comment_id = $1",
            comment_id
        )
        assert comment['upvotes'] == 1
        assert comment['downvotes'] == 0
        assert comment['vote_score'] == 1


@pytest.mark.asyncio
async def test_vote_comment_not_found(setup_test_data):
    """Test voting on non-existent comment."""
    comment_manager = CommentManager()

    # Try to vote on non-existent comment
    result = await comment_manager.vote_comment(
        comment_id='nonexistent_comment',
        agent_did='did:openclaw:00000000000000000000000000000001',
        vote_type='upvote'
    )

    # Verify failure
    assert result['success'] is False
    assert 'not found' in result['message'].lower()


@pytest.mark.asyncio
async def test_add_comment_empty_content(setup_test_data):
    """Test adding comment with empty content."""
    comment_manager = CommentManager()

    # Try to add comment with empty content
    with pytest.raises(ValueError, match="Comment content cannot be empty"):
        await comment_manager.add_comment(
            skill_id='test_skill_1',
            author_did='did:openclaw:00000000000000000000000000000002',
            content=''
        )

    # Try to add comment with whitespace only
    with pytest.raises(ValueError, match="Comment content cannot be empty"):
        await comment_manager.add_comment(
            skill_id='test_skill_1',
            author_did='did:openclaw:00000000000000000000000000000002',
            content='   '
        )


@pytest.mark.asyncio
async def test_add_comment_skill_not_found(setup_test_data):
    """Test adding comment to non-existent skill."""
    comment_manager = CommentManager()

    # Try to add comment to non-existent skill
    result = await comment_manager.add_comment(
        skill_id='nonexistent_skill',
        author_did='did:openclaw:00000000000000000000000000000002',
        content='Great skill!'
    )

    # Verify failure
    assert result['success'] is False
    assert result['comment_id'] is None
    assert 'not found' in result['message'].lower()


@pytest.mark.asyncio
async def test_add_comment_agent_not_found(setup_test_data):
    """Test adding comment with non-existent agent."""
    comment_manager = CommentManager()

    # Try to add comment with non-existent agent
    result = await comment_manager.add_comment(
        skill_id='test_skill_1',
        author_did='did:openclaw:ffffffffffffffffffffffffffffffff',
        content='Great skill!'
    )

    # Verify failure
    assert result['success'] is False
    assert result['comment_id'] is None
    assert 'not found' in result['message'].lower()


@pytest.mark.asyncio
async def test_add_reply_parent_not_found(setup_test_data):
    """Test adding reply to non-existent parent comment."""
    comment_manager = CommentManager()

    # Try to add reply to non-existent parent
    result = await comment_manager.add_comment(
        skill_id='test_skill_1',
        author_did='did:openclaw:00000000000000000000000000000002',
        content='This is a reply',
        parent_comment_id='nonexistent_parent'
    )

    # Verify failure
    assert result['success'] is False
    assert result['comment_id'] is None
    assert 'not found' in result['message'].lower()


@pytest.mark.asyncio
async def test_get_single_comment(setup_test_data):
    """Test getting a single comment by ID."""
    comment_manager = CommentManager()

    # Add a comment
    comment_result = await comment_manager.add_comment(
        skill_id='test_skill_1',
        author_did='did:openclaw:00000000000000000000000000000002',
        content='Test comment'
    )

    # Get the comment
    comment = await comment_manager.get_comment(comment_result['comment_id'])

    # Verify comment data
    assert comment is not None
    assert comment['comment_id'] == comment_result['comment_id']
    assert comment['content'] == 'Test comment'
    assert comment['username'] == 'agent2'
    assert comment['display_name'] == 'Agent 2'
    assert comment['depth'] == 0
    assert comment['parent_comment_id'] is None


@pytest.mark.asyncio
async def test_get_single_comment_not_found(setup_test_data):
    """Test getting non-existent comment."""
    comment_manager = CommentManager()

    # Try to get non-existent comment
    comment = await comment_manager.get_comment('nonexistent_comment')

    # Verify None returned
    assert comment is None


@pytest.mark.asyncio
async def test_complex_comment_tree(setup_test_data):
    """Test a complex nested comment tree structure."""
    comment_manager = CommentManager()

    # Build a tree like this:
    # Comment 1
    #   Reply 1.1
    #     Reply 1.1.1
    #   Reply 1.2
    # Comment 2

    comment1 = await comment_manager.add_comment(
        skill_id='test_skill_1',
        author_did='did:openclaw:00000000000000000000000000000002',
        content='Comment 1'
    )

    reply11 = await comment_manager.add_comment(
        skill_id='test_skill_1',
        author_did='did:openclaw:00000000000000000000000000000001',
        content='Reply 1.1',
        parent_comment_id=comment1['comment_id']
    )

    reply111 = await comment_manager.add_comment(
        skill_id='test_skill_1',
        author_did='did:openclaw:00000000000000000000000000000002',
        content='Reply 1.1.1',
        parent_comment_id=reply11['comment_id']
    )

    reply12 = await comment_manager.add_comment(
        skill_id='test_skill_1',
        author_did='did:openclaw:00000000000000000000000000000001',
        content='Reply 1.2',
        parent_comment_id=comment1['comment_id']
    )

    comment2 = await comment_manager.add_comment(
        skill_id='test_skill_1',
        author_did='did:openclaw:00000000000000000000000000000002',
        content='Comment 2'
    )

    # Get the tree
    tree = await comment_manager.get_comments_tree('test_skill_1')

    # Verify structure
    assert len(tree) == 2

    # Find Comment 1
    c1 = next((c for c in tree if c['content'] == 'Comment 1'), None)
    assert c1 is not None
    assert len(c1['replies']) == 2

    # Verify Reply 1.1
    r11 = next((r for r in c1['replies'] if r['content'] == 'Reply 1.1'), None)
    assert r11 is not None
    assert len(r11['replies']) == 1
    assert r11['depth'] == 1

    # Verify Reply 1.1.1
    r111 = r11['replies'][0]
    assert r111['content'] == 'Reply 1.1.1'
    assert r111['depth'] == 2
    assert len(r111['replies']) == 0

    # Verify Reply 1.2
    r12 = next((r for r in c1['replies'] if r['content'] == 'Reply 1.2'), None)
    assert r12 is not None
    assert len(r12['replies']) == 0

    # Find Comment 2
    c2 = next((c for c in tree if c['content'] == 'Comment 2'), None)
    assert c2 is not None
    assert len(c2['replies']) == 0
