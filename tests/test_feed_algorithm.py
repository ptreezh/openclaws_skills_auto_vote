"""
Tests for Reddit-style hot algorithm and feed system.
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from scripts.feed_algorithm import FeedAlgorithm
from scripts.database.db import db


@pytest.fixture
async def setup_test_data():
    """Set up test database with agents and skills for feed testing."""
    # Initialize database connection
    await db.init()

    async with db.get_connection() as conn:
        # Clean up any existing test data
        await conn.execute("DELETE FROM votes WHERE agent_id LIKE 'feed_test_%'")
        await conn.execute("DELETE FROM comments WHERE comment_id LIKE 'feed_test_%'")
        await conn.execute("DELETE FROM skills WHERE skill_id LIKE 'feed_test_%'")
        await conn.execute("DELETE FROM agents WHERE agent_id LIKE 'feed_test_%'")

        # Create test agents
        await conn.execute("""
            INSERT INTO agents (agent_id, did, username, display_name)
            VALUES
                ('feed_test_agent_1', 'did:openclaw:00000000000000000000000000000001', 'feeduser1', 'Feed User 1'),
                ('feed_test_agent_2', 'did:openclaw:00000000000000000000000000000002', 'feeduser2', 'Feed User 2'),
                ('feed_test_agent_3', 'did:openclaw:00000000000000000000000000000003', 'feeduser3', 'Feed User 3')
        """)

        # Create test skills with different vote patterns and ages
        # Skill 1: High votes, old (should have high hot score)
        await conn.execute("""
            INSERT INTO skills (
                skill_id, agent_id, skill_name, description,
                upvotes, downvotes, vote_score, community,
                visibility, created_at
            )
            VALUES (
                'feed_test_skill_1', 'feed_test_agent_1', 'Popular Old Skill',
                'This skill has many upvotes and is old',
                100, 10, 90, 'data-analysis',
                'public', NOW() - INTERVAL '48 hours'
            )
        """)

        # Skill 2: Medium votes, new (should compete with skill 1)
        await conn.execute("""
            INSERT INTO skills (
                skill_id, agent_id, skill_name, description,
                upvotes, downvotes, vote_score, community,
                visibility, created_at
            )
            VALUES (
                'feed_test_skill_2', 'feed_test_agent_2', 'Trending New Skill',
                'This skill is new and getting votes',
                50, 5, 45, 'web-scraping',
                'public', NOW() - INTERVAL '2 hours'
            )
        """)

        # Skill 3: Low votes, very new (lower hot score)
        await conn.execute("""
            INSERT INTO skills (
                skill_id, agent_id, skill_name, description,
                upvotes, downvotes, vote_score, community,
                visibility, created_at
            )
            VALUES (
                'feed_test_skill_3', 'feed_test_agent_3', 'New Skill',
                'This skill is very new',
                10, 2, 8, 'data-analysis',
                'public', NOW() - INTERVAL '30 minutes'
            )
        """)

        # Skill 4: Zero votes, medium age (lowest hot score)
        await conn.execute("""
            INSERT INTO skills (
                skill_id, agent_id, skill_name, description,
                upvotes, downvotes, vote_score, community,
                visibility, created_at
            )
            VALUES (
                'feed_test_skill_4', 'feed_test_agent_1', 'Unvoted Skill',
                'This skill has no votes yet',
                0, 0, 0, 'machine-learning',
                'public', NOW() - INTERVAL '5 hours'
            )
        """)

        # Skill 5: Private skill (should not appear in feed)
        await conn.execute("""
            INSERT INTO skills (
                skill_id, agent_id, skill_name, description,
                upvotes, downvotes, vote_score, community,
                visibility, created_at
            )
            VALUES (
                'feed_test_skill_5', 'feed_test_agent_2', 'Private Skill',
                'This skill is private',
                1000, 0, 1000, 'data-analysis',
                'private', NOW() - INTERVAL '1 hour'
            )
        """)

    yield

    # Cleanup
    async with db.get_connection() as conn:
        await conn.execute("DELETE FROM votes WHERE agent_id LIKE 'feed_test_%'")
        await conn.execute("DELETE FROM comments WHERE comment_id LIKE 'feed_test_%'")
        await conn.execute("DELETE FROM skills WHERE skill_id LIKE 'feed_test_%'")
        await conn.execute("DELETE FROM agents WHERE agent_id LIKE 'feed_test_%'")

    await db.close()


def test_calculate_hot_score():
    """Test hot score calculation with various vote patterns."""
    feed_algo = FeedAlgorithm()

    # Test 1: Zero votes with some age (baseline)
    # Use a skill that's at least 1 hour old so age contributes to score
    hour_ago = datetime.now() - timedelta(hours=1)
    score = feed_algo.calculate_hot_score(0, 0, hour_ago)
    assert score > 0  # Should have positive score from age
    assert score < 10  # But not too high

    # Test 2: High upvotes, very recent
    now = datetime.now()
    score = feed_algo.calculate_hot_score(100, 10, now)
    expected_order = __import__('math').log10(90)  # log10(90)
    # Score should be close to order since age is near 0
    assert abs(score - expected_order) < 1.0

    # Test 3: Same votes but older (should have higher score)
    older_time = now - timedelta(hours=10)
    score_new = feed_algo.calculate_hot_score(50, 5, now)
    score_old = feed_algo.calculate_hot_score(50, 5, older_time)
    assert score_old > score_new  # Older posts should have higher hot score

    # Test 4: Negative score (more downvotes than upvotes)
    score = feed_algo.calculate_hot_score(10, 50, datetime.now())
    # Should use absolute value, so log(40) + age
    assert score > 0  # Should still be positive due to log(abs(score))


def test_hot_score_time_decay():
    """Test that hot score increases with age (time decay)."""
    feed_algo = FeedAlgorithm()

    base_time = datetime.now() - timedelta(hours=10)
    votes = {'upvotes': 20, 'downvotes': 5}  # score = 15

    # Calculate scores at different ages
    score_10h = feed_algo.calculate_hot_score(
        votes['upvotes'],
        votes['downvotes'],
        base_time
    )

    score_20h = feed_algo.calculate_hot_score(
        votes['upvotes'],
        votes['downvotes'],
        base_time - timedelta(hours=10)
    )

    score_30h = feed_algo.calculate_hot_score(
        votes['upvotes'],
        votes['downvotes'],
        base_time - timedelta(hours=20)
    )

    # Hot score should increase with age
    assert score_30h > score_20h > score_10h

    # Difference should be approximately age/gravity
    diff_10_to_20 = score_20h - score_10h
    diff_20_to_30 = score_30h - score_20h
    expected_diff = 10 / feed_algo.GRAVITY  # 10 hours / 1.8

    # Each 10-hour difference should add ~5.56 to the score
    assert abs(diff_10_to_20 - expected_diff) < 0.1
    assert abs(diff_20_to_30 - expected_diff) < 0.1


@pytest.mark.asyncio
async def test_get_feed_hot(setup_test_data):
    """Test retrieving hot feed (sorted by hot score)."""
    feed_algo = FeedAlgorithm()

    # First update hot scores
    await feed_algo.update_hot_scores()

    # Get hot feed
    feed = await feed_algo.get_feed(sort_by='hot', limit=10)

    # Verify feed structure
    assert len(feed) == 5  # All public skills
    assert feed[0]['uploader_name'] == 'feeduser1'

    # Verify all required fields are present
    required_fields = [
        'skill_id', 'skill_name', 'description',
        'upvotes', 'downvotes', 'vote_score', 'hot_score',
        'uploader_name', 'uploader_display_name', 'uploader_id',
        'community', 'created_at', 'visibility'
    ]

    for skill in feed:
        for field in required_fields:
            assert field in skill

    # Verify sorting by hot score (descending)
    for i in range(len(feed) - 1):
        assert feed[i]['hot_score'] >= feed[i + 1]['hot_score']

    # Verify private skill is not in feed
    skill_ids = [s['skill_id'] for s in feed]
    assert 'feed_test_skill_5' not in skill_ids


@pytest.mark.asyncio
async def test_get_feed_new(setup_test_data):
    """Test retrieving new feed (sorted by creation time)."""
    feed_algo = FeedAlgorithm()

    # Get new feed
    feed = await feed_algo.get_feed(sort_by='new', limit=10)

    # Verify sorting by created_at (descending - newest first)
    for i in range(len(feed) - 1):
        assert feed[i]['created_at'] >= feed[i + 1]['created_at']

    # Newest skill should be feed_test_skill_3 (30 minutes old)
    # or feed_test_skill_2 (2 hours old) or feed_test_skill_5 (1 hour, but private)
    # So it should be feed_test_skill_3
    assert feed[0]['skill_id'] == 'feed_test_skill_3'


@pytest.mark.asyncio
async def test_get_feed_top(setup_test_data):
    """Test retrieving top feed (sorted by vote score)."""
    feed_algo = FeedAlgorithm()

    # Get top feed
    feed = await feed_algo.get_feed(sort_by='top', limit=10)

    # Verify sorting by vote_score (descending)
    for i in range(len(feed) - 1):
        assert feed[i]['vote_score'] >= feed[i + 1]['vote_score']

    # Top skill should be feed_test_skill_1 (90 votes)
    assert feed[0]['skill_id'] == 'feed_test_skill_1'
    assert feed[0]['vote_score'] == 90


@pytest.mark.asyncio
async def test_get_feed_with_community_filter(setup_test_data):
    """Test feed filtering by community."""
    feed_algo = FeedAlgorithm()

    # Update hot scores first
    await feed_algo.update_hot_scores()

    # Get feed filtered by data-analysis community
    feed = await feed_algo.get_feed(
        sort_by='hot',
        community='data-analysis',
        limit=10
    )

    # Should only return data-analysis skills
    assert len(feed) == 2  # skill_1 and skill_3
    for skill in feed:
        assert skill['community'] == 'data-analysis'

    # Get feed filtered by web-scraping community
    feed = await feed_algo.get_feed(
        sort_by='hot',
        community='web-scraping',
        limit=10
    )

    assert len(feed) == 1  # only skill_2
    assert feed[0]['skill_id'] == 'feed_test_skill_2'


@pytest.mark.asyncio
async def test_get_feed_with_pagination(setup_test_data):
    """Test feed pagination with limit and offset."""
    feed_algo = FeedAlgorithm()

    # Update hot scores first
    await feed_algo.update_hot_scores()

    # Get first page
    page1 = await feed_algo.get_feed(sort_by='hot', limit=2, offset=0)
    assert len(page1) == 2

    # Get second page
    page2 = await feed_algo.get_feed(sort_by='hot', limit=2, offset=2)
    assert len(page2) == 2

    # Get third page
    page3 = await feed_algo.get_feed(sort_by='hot', limit=2, offset=4)
    assert len(page3) == 1  # Only 1 item left

    # Verify no duplicates across pages
    all_ids = [s['skill_id'] for s in page1 + page2 + page3]
    assert len(all_ids) == len(set(all_ids))  # All unique

    # Verify fourth page is empty
    page4 = await feed_algo.get_feed(sort_by='hot', limit=2, offset=5)
    assert len(page4) == 0


@pytest.mark.asyncio
async def test_get_feed_invalid_sort_by(setup_test_data):
    """Test that invalid sort_by parameter raises ValueError."""
    feed_algo = FeedAlgorithm()

    with pytest.raises(ValueError, match="Invalid sort_by"):
        await feed_algo.get_feed(sort_by='invalid_sort')


@pytest.mark.asyncio
async def test_update_hot_scores(setup_test_data):
    """Test batch updating of hot scores."""
    feed_algo = FeedAlgorithm()

    # Update all hot scores
    result = await feed_algo.update_hot_scores()

    # Verify result
    assert 'updated' in result
    assert result['updated'] == 5  # All 5 public skills

    # Verify scores were actually updated in database
    async with db.get_connection() as conn:
        skills = await conn.fetch("""
            SELECT skill_id, hot_score
            FROM skills
            WHERE skill_id LIKE 'feed_test_%'
            ORDER BY skill_id
        """)

        # All should have hot scores now
        for skill in skills:
            assert skill['hot_score'] is not None
            assert skill['hot_score'] > 0


@pytest.mark.asyncio
async def test_get_feed_includes_uploader_info(setup_test_data):
    """Test that feed includes uploader (agent) information."""
    feed_algo = FeedAlgorithm()

    # Get feed
    feed = await feed_algo.get_feed(sort_by='hot', limit=10)

    # Verify uploader info is present and correct
    skill1 = next((s for s in feed if s['skill_id'] == 'feed_test_skill_1'), None)
    assert skill1 is not None
    assert skill1['uploader_name'] == 'feeduser1'
    assert skill1['uploader_display_name'] == 'Feed User 1'
    assert skill1['uploader_id'] == 'feed_test_agent_1'

    skill2 = next((s for s in feed if s['skill_id'] == 'feed_test_skill_2'), None)
    assert skill2 is not None
    assert skill2['uploader_name'] == 'feeduser2'


@pytest.mark.asyncio
async def test_hot_score_formula_accuracy():
    """Test that hot score formula matches Reddit's algorithm exactly."""
    feed_algo = FeedAlgorithm()

    # Test with known values
    # score = 100 - 10 = 90
    # order = log10(90) ≈ 1.9542
    # age = 48 hours
    # hot = 1.9542 + (48 / 1.8) = 1.9542 + 26.6667 ≈ 28.6209
    created_at = datetime.now() - timedelta(hours=48)
    score = feed_algo.calculate_hot_score(100, 10, created_at)

    # Calculate expected value
    import math
    expected_order = math.log10(90)
    expected_hot = expected_order + (48 / 1.8)

    # Should be very close (within rounding error)
    assert abs(score - expected_hot) < 0.01
