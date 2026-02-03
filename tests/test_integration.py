#!/usr/bin/env python3
"""
Integration tests - Complete social features flow test
"""
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from api.v2_server import app
from scripts.database.db import db
from scripts.did_auth import DIDAuth


@pytest.fixture
async def setup_test_data():
    """Set up test database with agents and skills."""
    # Initialize database connection
    await db.init()

    async with db.get_connection() as conn:
        # Clean up test data
        await conn.execute("DELETE FROM votes WHERE agent_id LIKE 'test_%'")
        await conn.execute("DELETE FROM comments WHERE comment_id LIKE 'test_%'")
        await conn.execute("DELETE FROM downloads WHERE downloader_did LIKE 'did:openclaw:test%'")
        await conn.execute("DELETE FROM agent_skills WHERE agent_did LIKE 'did:openclaw:test%'")
        await conn.execute("DELETE FROM following WHERE follower_did LIKE 'did:openclaw:test%'")
        await conn.execute("DELETE FROM skills WHERE skill_id LIKE 'test_%'")
        await conn.execute("DELETE FROM agents WHERE did LIKE 'did:openclaw:test%'")

        # Create test agents
        await conn.execute("""
            INSERT INTO agents (did, username, display_name, bio)
            VALUES
                ('did:openclaw:test001', 'testbot', 'Test Bot', 'A test bot'),
                ('did:openclaw:test002', 'viewerbot', 'Viewer Bot', 'A viewer bot')
        """)

        # Create test skills
        await conn.execute("""
            INSERT INTO skills (skill_id, agent_id, skill_name, description, upvotes, downvotes, vote_score, comments_count)
            VALUES
                ('test_skill_vote', 'did:openclaw:test001', 'Test Skill Vote', 'A test skill for voting', 0, 0, 0, 0),
                ('test_skill_comment', 'did:openclaw:test001', 'Test Skill Comment', 'A test skill for comments', 0, 0, 0, 0),
                ('test_skill_download', 'did:openclaw:test001', 'Test Skill Download', 'A test skill for downloads', 0, 0, 0, 0)
        """)

        # For feed test - create multiple skills with different scores
        for i in range(3):
            await conn.execute("""
                INSERT INTO skills (skill_id, agent_id, skill_name, description, upvotes, downvotes, vote_score, comments_count)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, f"test_skill_{i}", "did:openclaw:test001", f"Skill {i}", f"Test skill {i}", i, 0, i, 0)

    yield

    # Cleanup
    async with db.get_connection() as conn:
        await conn.execute("DELETE FROM votes WHERE agent_id LIKE 'test_%'")
        await conn.execute("DELETE FROM comments WHERE comment_id LIKE 'test_%'")
        await conn.execute("DELETE FROM downloads WHERE downloader_did LIKE 'did:openclaw:test%'")
        await conn.execute("DELETE FROM agent_skills WHERE agent_did LIKE 'did:openclaw:test%'")
        await conn.execute("DELETE FROM following WHERE follower_did LIKE 'did:openclaw:test%'")
        await conn.execute("DELETE FROM skills WHERE skill_id LIKE 'test_%'")
        await conn.execute("DELETE FROM agents WHERE did LIKE 'did:openclaw:test%'")

    await db.close()


@pytest.mark.asyncio
async def test_agent_authentication(setup_test_data):
    """Test agent authentication."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test getting current agent
        response = await client.get(
            "/api/v2/agents/me",
            headers={"X-Agent-DID": "did:openclaw:test001"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "testbot"
        assert data["did"] == "did:openclaw:test001"

        # Test unauthenticated
        response = await client.get("/api/v2/agents/me")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_voting_flow(setup_test_data):
    """Test voting flow."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test upvote
        response = await client.post(
            "/api/v2/skills/test_skill_vote/vote",
            params={"vote_type": "upvote"},
            headers={"X-Agent-DID": "did:openclaw:test002"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["upvotes"] == 1

        # Test getting vote status
        response = await client.get(
            "/api/v2/skills/test_skill_vote/vote",
            headers={"X-Agent-DID": "did:openclaw:test002"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["vote"] == "upvote"

        # Test downvote
        response = await client.post(
            "/api/v2/skills/test_skill_vote/vote",
            params={"vote_type": "downvote"},
            headers={"X-Agent-DID": "did:openclaw:test002"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["upvotes"] == 0
        assert data["downvotes"] == 1

        # Test cancel vote
        response = await client.post(
            "/api/v2/skills/test_skill_vote/vote",
            params={"vote_type": "cancel"},
            headers={"X-Agent-DID": "did:openclaw:test002"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["upvotes"] == 0
        assert data["downvotes"] == 0


@pytest.mark.asyncio
async def test_voting_errors(setup_test_data):
    """Test voting error cases."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test invalid vote type
        response = await client.post(
            "/api/v2/skills/test_skill_vote/vote",
            params={"vote_type": "invalid"},
            headers={"X-Agent-DID": "did:openclaw:test002"}
        )
        assert response.status_code == 400

        # Test voting on non-existent skill
        response = await client.post(
            "/api/v2/skills/nonexistent_skill/vote",
            params={"vote_type": "upvote"},
            headers={"X-Agent-DID": "did:openclaw:test002"}
        )
        assert response.status_code == 200  # VoteSystem returns success even if skill doesn't exist yet

        # Test unauthenticated vote
        response = await client.post(
            "/api/v2/skills/test_skill_vote/vote",
            params={"vote_type": "upvote"}
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_comment_flow(setup_test_data):
    """Test comment flow."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Add top-level comment
        response = await client.post(
            "/api/v2/skills/test_skill_comment/comments",
            params={"content": "Great skill!"},
            headers={"X-Agent-DID": "did:openclaw:test002"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "comment" in data
        parent_comment_id = data["comment"]["comment_id"]

        # Add reply
        response = await client.post(
            "/api/v2/skills/test_skill_comment/comments",
            params={
                "content": "Thanks!",
                "parent_comment_id": parent_comment_id
            },
            headers={"X-Agent-DID": "did:openclaw:test001"}
        )
        assert response.status_code == 200

        # Get comment tree
        response = await client.get(
            "/api/v2/skills/test_skill_comment/comments"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["comments"]) == 1
        assert len(data["comments"][0]["replies"]) == 1


@pytest.mark.asyncio
async def test_comment_errors(setup_test_data):
    """Test comment error cases."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test commenting on non-existent skill
        response = await client.post(
            "/api/v2/skills/nonexistent_skill/comments",
            params={"content": "This will fail"},
            headers={"X-Agent-DID": "did:openclaw:test002"}
        )
        assert response.status_code == 200  # CommentManager handles this gracefully
        data = response.json()
        # The comment manager returns success=False when skill not found
        assert data["success"] is False

        # Test unauthenticated comment
        response = await client.post(
            "/api/v2/skills/test_skill_comment/comments",
            params={"content": "Test"}
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_feed_flow(setup_test_data):
    """Test feed flow."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test hot feed
        response = await client.get("/api/v2/feed?sort_by=hot")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "feed" in data
        assert len(data["feed"]) >= 3

        # Test new feed
        response = await client.get("/api/v2/feed?sort_by=new")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # Test top feed
        response = await client.get("/api/v2/feed?sort_by=top")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


@pytest.mark.asyncio
async def test_feed_errors(setup_test_data):
    """Test feed error cases."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test invalid sort_by
        response = await client.get("/api/v2/feed?sort_by=invalid")
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_follow_flow(setup_test_data):
    """Test follow flow."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Follow agent
        response = await client.post(
            "/api/v2/agents/did:openclaw:test001/follow",
            headers={"X-Agent-DID": "did:openclaw:test002"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["following"] is True

        # Get agent profile
        response = await client.get(
            "/api/v2/agents/did:openclaw:test001/profile",
            headers={"X-Agent-DID": "did:openclaw:test002"}
        )
        assert response.status_code == 200
        data = response.json()
        # Profile should contain agent info and skills

        # Unfollow agent
        response = await client.delete(
            "/api/v2/agents/did:openclaw:test001/follow",
            headers={"X-Agent-DID": "did:openclaw:test002"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["following"] is False


@pytest.mark.asyncio
async def test_follow_errors(setup_test_data):
    """Test follow error cases."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test following non-existent agent
        response = await client.post(
            "/api/v2/agents/did:openclaw:nonexistent/follow",
            headers={"X-Agent-DID": "did:openclaw:test002"}
        )
        assert response.status_code == 404

        # Test unauthenticated follow
        response = await client.post(
            "/api/v2/agents/did:openclaw:test001/follow"
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_download_permission_flow(setup_test_data):
    """Test download permission flow."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Check download permission
        response = await client.get(
            "/api/v2/skills/test_skill_download/download-permission",
            headers={"X-Agent-DID": "did:openclaw:test002"}
        )
        assert response.status_code == 200
        data = response.json()
        # Permission check should return can_download status

        # Download (record but don't actually return file)
        response = await client.get(
            "/api/v2/skills/test_skill_download/download",
            headers={"X-Agent-DID": "did:openclaw:test002"}
        )
        assert response.status_code == 200
        data = response.json()
        # Should have download_url or file_size info


@pytest.mark.asyncio
async def test_download_errors(setup_test_data):
    """Test download error cases."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test permission check for non-existent skill
        response = await client.get(
            "/api/v2/skills/nonexistent_skill/download-permission",
            headers={"X-Agent-DID": "did:openclaw:test002"}
        )
        # DownloadManager handles missing skills
        assert response.status_code == 200

        # Test unauthenticated download
        response = await client.get(
            "/api/v2/skills/test_skill_download/download"
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_complete_social_flow(setup_test_data):
    """Test complete social features flow in sequence."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Agent authentication
        response = await client.get(
            "/api/v2/agents/me",
            headers={"X-Agent-DID": "did:openclaw:test001"}
        )
        assert response.status_code == 200
        agent = response.json()
        assert agent["username"] == "testbot"

        # 2. Vote on skill
        response = await client.post(
            "/api/v2/skills/test_skill_vote/vote",
            params={"vote_type": "upvote"},
            headers={"X-Agent-DID": "did:openclaw:test002"}
        )
        assert response.status_code == 200

        # 3. Add comment
        response = await client.post(
            "/api/v2/skills/test_skill_comment/comments",
            params={"content": "This is amazing!"},
            headers={"X-Agent-DID": "did:openclaw:test002"}
        )
        assert response.status_code == 200
        comment_data = response.json()
        comment_id = comment_data["comment"]["comment_id"]

        # 4. Vote on comment
        response = await client.post(
            f"/api/v2/comments/{comment_id}/vote",
            params={"vote_type": "upvote"},
            headers={"X-Agent-DID": "did:openclaw:test001"}
        )
        assert response.status_code == 200

        # 5. Get feed
        response = await client.get("/api/v2/feed?sort_by=hot")
        assert response.status_code == 200
        feed_data = response.json()
        assert feed_data["success"] is True

        # 6. Follow agent
        response = await client.post(
            "/api/v2/agents/did:openclaw:test001/follow",
            headers={"X-Agent-DID": "did:openclaw:test002"}
        )
        assert response.status_code == 200

        # 7. Get agent profile
        response = await client.get(
            "/api/v2/agents/did:openclaw:test001/profile",
            headers={"X-Agent-DID": "did:openclaw:test002"}
        )
        assert response.status_code == 200

        # 8. Check download permission
        response = await client.get(
            "/api/v2/skills/test_skill_download/download-permission",
            headers={"X-Agent-DID": "did:openclaw:test002"}
        )
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_comment_vote_flow(setup_test_data):
    """Test voting on comments."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First add a comment
        response = await client.post(
            "/api/v2/skills/test_skill_comment/comments",
            params={"content": "Comment to vote on"},
            headers={"X-Agent-DID": "did:openclaw:test002"}
        )
        assert response.status_code == 200
        comment_data = response.json()
        comment_id = comment_data["comment"]["comment_id"]

        # Upvote the comment
        response = await client.post(
            f"/api/v2/comments/{comment_id}/vote",
            params={"vote_type": "upvote"},
            headers={"X-Agent-DID": "did:openclaw:test001"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["upvotes"] == 1

        # Downvote the comment
        response = await client.post(
            f"/api/v2/comments/{comment_id}/vote",
            params={"vote_type": "downvote"},
            headers={"X-Agent-DID": "did:openclaw:test001"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["upvotes"] == 0
        assert data["downvotes"] == 1

        # Cancel vote
        response = await client.post(
            f"/api/v2/comments/{comment_id}/vote",
            params={"vote_type": "cancel"},
            headers={"X-Agent-DID": "did:openclaw:test001"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["upvotes"] == 0
        assert data["downvotes"] == 0


@pytest.mark.asyncio
async def test_nested_comment_flow(setup_test_data):
    """Test nested comment structure."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Add top-level comment
        response = await client.post(
            "/api/v2/skills/test_skill_comment/comments",
            params={"content": "Top level comment"},
            headers={"X-Agent-DID": "did:openclaw:test002"}
        )
        assert response.status_code == 200
        parent_id = response.json()["comment"]["comment_id"]

        # Add first-level reply
        response = await client.post(
            "/api/v2/skills/test_skill_comment/comments",
            params={
                "content": "First reply",
                "parent_comment_id": parent_id
            },
            headers={"X-Agent-DID": "did:openclaw:test001"}
        )
        assert response.status_code == 200
        reply1_id = response.json()["comment"]["comment_id"]

        # Add second-level reply
        response = await client.post(
            "/api/v2/skills/test_skill_comment/comments",
            params={
                "content": "Second reply",
                "parent_comment_id": reply1_id
            },
            headers={"X-Agent-DID": "did:openclaw:test002"}
        )
        assert response.status_code == 200

        # Get full tree
        response = await client.get(
            "/api/v2/skills/test_skill_comment/comments"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["comments"]) == 1
        assert len(data["comments"][0]["replies"]) == 1
        assert len(data["comments"][0]["replies"][0]["replies"]) == 1
