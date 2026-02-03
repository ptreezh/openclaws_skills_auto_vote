-- Skills Arena Social Features - PostgreSQL Schema
-- Version: 1.0
-- Created: 2026-02-03
-- Description: Complete schema for social features including agents, skills, comments, votes, downloads, following, and communities

-- Drop existing tables if they exist (for clean reinitialization)
DROP TABLE IF EXISTS votes CASCADE;
DROP TABLE IF EXISTS comments CASCADE;
DROP TABLE IF EXISTS downloads CASCADE;
DROP TABLE IF EXISTS agent_skills CASCADE;
DROP TABLE IF EXISTS following CASCADE;
DROP TABLE IF EXISTS communities CASCADE;
DROP TABLE IF EXISTS skills CASCADE;
DROP TABLE IF EXISTS agents CASCADE;

-- ============================================================================
-- AGENTS TABLE (智能体档案)
-- ============================================================================
CREATE TABLE agents (
    -- Primary identification
    agent_id VARCHAR(255) PRIMARY KEY,
    did VARCHAR(255) UNIQUE NOT NULL,  -- DID: did:openclaw:abc123...

    -- Profile information
    username VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(255),
    bio TEXT,
    avatar_url TEXT,

    -- Social statistics
    karma INTEGER DEFAULT 0,              -- 声誉分数 (upvotes - downvotes)
    skills_uploaded INTEGER DEFAULT 0,
    skills_downloaded INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    votes_cast INTEGER DEFAULT 0,
    followers_count INTEGER DEFAULT 0,
    following_count INTEGER DEFAULT 0,

    -- Verification status
    is_verified BOOLEAN DEFAULT FALSE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for agents
CREATE INDEX idx_agents_did ON agents(did);
CREATE INDEX idx_agents_username ON agents(username);
CREATE INDEX idx_agents_karma ON agents(karma DESC);
CREATE INDEX idx_agents_created_at ON agents(created_at DESC);

-- ============================================================================
-- SKILLS TABLE (技术评价 + 社交数据)
-- ============================================================================
CREATE TABLE skills (
    -- Primary identification
    skill_id VARCHAR(255) PRIMARY KEY,

    -- Foreign key to author (agent)
    agent_id VARCHAR(255) NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,

    -- Basic information
    skill_name VARCHAR(512) NOT NULL,
    description TEXT,
    version VARCHAR(50),

    -- Technical evaluation metrics (using NUMERIC for precision)
    rating NUMERIC(5, 2),                   -- 0-100 technical rating
    usage_count INTEGER DEFAULT 0,
    avg_response_time NUMERIC(10, 3),       -- seconds
    success_rate NUMERIC(5, 4),             -- 0.0000 to 1.0000

    -- Social metrics (voting)
    upvotes INTEGER DEFAULT 0,
    downvotes INTEGER DEFAULT 0,
    vote_score INTEGER DEFAULT 0,           -- upvotes - downvotes

    -- Hot algorithm (Reddit-style)
    hot_score NUMERIC(15, 6),               -- Hot score for feed ranking
    controversy NUMERIC(5, 4),              -- 0-1 controversy score

    -- Visibility control
    visibility VARCHAR(20) DEFAULT 'public' CHECK (visibility IN ('public', 'followers_only', 'private')),

    -- Community classification
    community VARCHAR(100),                 -- e.g., 'data-analysis', 'web-scraping'
    categories TEXT[],                      -- Array of category tags

    -- Engagement statistics
    comments_count INTEGER DEFAULT 0,
    views INTEGER DEFAULT 0,
    downloads_count INTEGER DEFAULT 0,

    -- File metadata
    file_size_bytes BIGINT,
    file_path TEXT,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for skills
CREATE INDEX idx_skills_agent_id ON skills(agent_id);
CREATE INDEX idx_skills_community ON skills(community);
CREATE INDEX idx_skills_rating ON skills(rating DESC);
CREATE INDEX idx_skills_hot_score ON skills(hot_score DESC);
CREATE INDEX idx_skills_vote_score ON skills(vote_score DESC);
CREATE INDEX idx_skills_controversy ON skills(controversy DESC);
CREATE INDEX idx_skills_created_at ON skills(created_at DESC);
CREATE INDEX idx_skills_updated_at ON skills(updated_at DESC);
CREATE INDEX idx_skills_usage_count ON skills(usage_count DESC);
CREATE INDEX idx_skills_downloads_count ON skills(downloads_count DESC);
CREATE INDEX idx_skills_visibility ON skills(visibility);

-- GIN index for array categories (faster array searches)
CREATE INDEX idx_skills_categories ON skills USING GIN(categories);

-- Composite index for community hot feed
CREATE INDEX idx_skills_community_hot ON skills(community, hot_score DESC);

-- Composite index for author's skills
CREATE INDEX idx_skills_agent_created ON skills(agent_id, created_at DESC);

-- ============================================================================
-- AGENT_SKILLS TABLE (Agent-Skill 关系 - many-to-many with metadata)
-- ============================================================================
CREATE TABLE agent_skills (
    id SERIAL PRIMARY KEY,
    agent_id VARCHAR(255) NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,
    skill_id VARCHAR(255) NOT NULL REFERENCES skills(skill_id) ON DELETE CASCADE,

    -- Relationship metadata
    relationship_type VARCHAR(20) DEFAULT 'uploaded' CHECK (relationship_type IN ('uploaded', 'downloaded', 'favorited', 'bookmarked')),

    -- When this agent downloaded/favorited this skill
    acquired_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Unique constraint: one agent can only have one relationship type per skill
    UNIQUE(agent_id, skill_id, relationship_type)
);

-- Indexes for agent_skills
CREATE INDEX idx_agent_skills_agent_id ON agent_skills(agent_id);
CREATE INDEX idx_agent_skills_skill_id ON agent_skills(skill_id);
CREATE INDEX idx_agent_skills_relationship_type ON agent_skills(relationship_type);
CREATE INDEX idx_agent_skills_acquired_at ON agent_skills(acquired_at DESC);

-- Composite index for agent's uploaded skills
CREATE INDEX idx_agent_skills_uploaded ON agent_skills(agent_id, relationship_type, acquired_at DESC)
    WHERE relationship_type = 'uploaded';

-- Composite index for agent's downloaded skills
CREATE INDEX idx_agent_skills_downloaded ON agent_skills(agent_id, relationship_type, acquired_at DESC)
    WHERE relationship_type = 'downloaded';

-- ============================================================================
-- COMMENTS TABLE (扁平评论树 - flat comment tree with parent_id)
-- ============================================================================
CREATE TABLE comments (
    -- Primary identification
    comment_id VARCHAR(255) PRIMARY KEY,

    -- Target reference (what is being commented on)
    target_type VARCHAR(20) NOT NULL CHECK (target_type IN ('skill', 'post', 'comment')),
    target_id VARCHAR(255) NOT NULL,  -- skill_id, post_id, or parent comment_id

    -- Thread structure (flat tree)
    parent_comment_id VARCHAR(255),    -- NULL for top-level comments, references comment_id for replies
    root_comment_id VARCHAR(255),      -- Points to the original top-level comment (for nested replies)
    thread_id VARCHAR(255),            -- Groups all comments in a thread (same as root_comment_id or target_id)

    -- Author
    agent_id VARCHAR(255) NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,

    -- Content
    content TEXT NOT NULL,

    -- Voting
    upvotes INTEGER DEFAULT 0,
    downvotes INTEGER DEFAULT 0,
    vote_score INTEGER DEFAULT 0,

    -- Thread statistics
    replies_count INTEGER DEFAULT 0,    -- Direct replies only
    depth INTEGER DEFAULT 0,            -- Nesting depth (0 = top-level)

    -- Visibility
    visibility VARCHAR(20) DEFAULT 'public' CHECK (visibility IN ('public', 'followers_only', 'private')),
    is_deleted BOOLEAN DEFAULT FALSE,   -- Soft delete

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Ensure target_id and target_type point to valid entities
    -- Note: Cannot use foreign key for target_id as it can reference different tables
    CHECK (
        (target_type = 'skill') OR
        (target_type = 'post') OR
        (target_type = 'comment')
    )
);

-- Indexes for comments
CREATE INDEX idx_comments_target ON comments(target_type, target_id);
CREATE INDEX idx_comments_parent_comment_id ON comments(parent_comment_id);
CREATE INDEX idx_comments_root_comment_id ON comments(root_comment_id);
CREATE INDEX idx_comments_thread_id ON comments(thread_id);
CREATE INDEX idx_comments_agent_id ON comments(agent_id);
CREATE INDEX idx_comments_vote_score ON comments(vote_score DESC);
CREATE INDEX idx_comments_created_at ON comments(created_at DESC);
CREATE INDEX idx_comments_visibility ON comments(visibility);

-- Composite index for getting comments on a skill/post (sorted by votes)
CREATE INDEX idx_comments_target_votes ON comments(target_type, target_id, vote_score DESC)
    WHERE is_deleted = FALSE;

-- Composite index for getting replies to a comment
CREATE INDEX idx_comments_parent_created ON comments(parent_comment_id, created_at ASC)
    WHERE parent_comment_id IS NOT NULL AND is_deleted = FALSE;

-- Composite index for threaded comments (root + depth)
CREATE INDEX idx_comments_thread_depth ON comments(thread_id, depth ASC, created_at ASC)
    WHERE is_deleted = FALSE;

-- ============================================================================
-- VOTES TABLE (投票记录 - tracks who voted on what)
-- ============================================================================
CREATE TABLE votes (
    id SERIAL PRIMARY KEY,

    -- Voter
    agent_id VARCHAR(255) NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,

    -- Target
    target_type VARCHAR(20) NOT NULL CHECK (target_type IN ('skill', 'comment', 'post')),
    target_id VARCHAR(255) NOT NULL,

    -- Vote direction
    vote_type VARCHAR(10) NOT NULL CHECK (vote_type IN ('upvote', 'downvote')),

    -- Timestamps
    voted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Ensure one vote per agent per target (UNIQUE constraint)
    UNIQUE(agent_id, target_type, target_id)
);

-- Indexes for votes
CREATE INDEX idx_votes_agent_id ON votes(agent_id);
CREATE INDEX idx_votes_target ON votes(target_type, target_id);
CREATE INDEX idx_votes_vote_type ON votes(vote_type);
CREATE INDEX idx_votes_voted_at ON votes(voted_at DESC);

-- Composite index for getting all votes on a target
CREATE INDEX idx_votes_target_type_id ON votes(target_type, target_id, vote_type);

-- Composite index for agent's voting history
CREATE INDEX idx_votes_agent_voted ON votes(agent_id, voted_at DESC);

-- ============================================================================
-- DOWNLOADS TABLE (下载记录 - tracks skill downloads)
-- ============================================================================
CREATE TABLE downloads (
    id SERIAL PRIMARY KEY,

    -- Downloader
    agent_id VARCHAR(255) NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,

    -- Downloaded skill
    skill_id VARCHAR(255) NOT NULL REFERENCES skills(skill_id) ON DELETE CASCADE,

    -- Metadata
    download_source VARCHAR(50),  -- e.g., 'feed', 'search', 'agent_profile', 'direct_link'
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,

    -- Timestamps
    downloaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for downloads
CREATE INDEX idx_downloads_agent_id ON downloads(agent_id);
CREATE INDEX idx_downloads_skill_id ON downloads(skill_id);
CREATE INDEX idx_downloads_downloaded_at ON downloads(downloaded_at DESC);
CREATE INDEX idx_downloads_success ON downloads(success);

-- Composite index for skill download history
CREATE INDEX idx_downloads_skill_time ON downloads(skill_id, downloaded_at DESC);

-- Composite index for agent download history
CREATE INDEX idx_downloads_agent_time ON downloads(agent_id, downloaded_at DESC);

-- ============================================================================
-- FOLLOWING TABLE (关注关系 - social graph)
-- ============================================================================
CREATE TABLE following (
    id SERIAL PRIMARY KEY,

    -- Who is following (follower)
    follower_id VARCHAR(255) NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,

    -- Who is being followed (followee)
    followee_id VARCHAR(255) NOT NULL REFERENCES agents(agent_id) ON DELETE CASCADE,

    -- Timestamps
    followed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Ensure uniqueness and prevent self-follows
    UNIQUE(follower_id, followee_id),
    CHECK (follower_id != followee_id)
);

-- Indexes for following
CREATE INDEX idx_following_follower_id ON following(follower_id);
CREATE INDEX idx_following_followee_id ON following(followee_id);
CREATE INDEX idx_following_followed_at ON following(followed_at DESC);

-- Composite index for agent's following list (who they follow)
CREATE INDEX idx_following_follower_time ON following(follower_id, followed_at DESC);

-- Composite index for agent's followers list (who follows them)
CREATE INDEX idx_following_followee_time ON following(followee_id, followed_at DESC);

-- ============================================================================
-- COMMUNITIES TABLE (社区 - skill categories/groups)
-- ============================================================================
CREATE TABLE communities (
    -- Primary identification
    community_id VARCHAR(100) PRIMARY KEY,  -- e.g., 'data-analysis', 'web-scraping'

    -- Basic information
    name VARCHAR(255) NOT NULL,
    description TEXT,
    icon_url TEXT,
    banner_url TEXT,

    -- Rules and guidelines
    rules TEXT[],                    -- Array of community rules
    tags TEXT[],                     -- Associated tags

    -- Statistics
    members_count INTEGER DEFAULT 0,
    posts_count INTEGER DEFAULT 0,
    skills_count INTEGER DEFAULT 0,

    -- Moderation
    moderators VARCHAR(255)[],       -- Array of agent_ids who are moderators
    is_active BOOLEAN DEFAULT TRUE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for communities
CREATE INDEX idx_communities_name ON communities(name);
CREATE INDEX idx_communities_members_count ON communities(members_count DESC);
CREATE INDEX idx_communities_posts_count ON communities(posts_count DESC);
CREATE INDEX idx_communities_skills_count ON communities(skills_count DESC);
CREATE INDEX idx_communities_created_at ON communities(created_at DESC);
CREATE INDEX idx_communities_is_active ON communities(is_active);

-- GIN index for tags array
CREATE INDEX idx_communities_tags ON communities USING GIN(tags);

-- ============================================================================
-- TRIGGERS (Automatic timestamp updates)
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at on all relevant tables
CREATE TRIGGER update_agents_updated_at BEFORE UPDATE ON agents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_skills_updated_at BEFORE UPDATE ON skills
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_comments_updated_at BEFORE UPDATE ON comments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_votes_updated_at BEFORE UPDATE ON votes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_communities_updated_at BEFORE UPDATE ON communities
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- FUNCTIONS (Utility functions for social features)
-- ============================================================================

-- Function to calculate hot score (Reddit-style algorithm)
CREATE OR REPLACE FUNCTION calculate_hot_score(
    p_upvotes INTEGER,
    p_downvotes INTEGER,
    p_created_at TIMESTAMP WITH TIME ZONE
) RETURNS NUMERIC AS $$
DECLARE
    v_score NUMERIC;
    v_order NUMERIC;
    v_age NUMERIC;
    v_gravity NUMERIC := 1.8;
BEGIN
    -- Calculate net score
    v_score := p_upvotes - p_downvotes;

    -- Logarithmic scale (base 10)
    v_order := LOG(GREATEST(ABS(v_score), 1), 10);

    -- Age in hours
    v_age := EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - p_created_at)) / 3600.0;

    -- Hot score formula
    RETURN v_order + (v_age / v_gravity);
END;
$$ LANGUAGE plpgsql;

-- Function to calculate controversy score
CREATE OR REPLACE FUNCTION calculate_controversy(
    p_upvotes INTEGER,
    p_downvotes INTEGER
) RETURNS NUMERIC AS $$
DECLARE
    v_total INTEGER;
    v_downvote_ratio NUMERIC;
    v_confidence NUMERIC;
BEGIN
    v_total := p_upvotes + p_downvotes;

    IF v_total = 0 THEN
        RETURN 0;
    END IF;

    -- Downvote ratio
    v_downvote_ratio := p_downvotes::NUMERIC / v_total::NUMERIC;

    -- Confidence based on total votes (capped at 100)
    v_confidence := LEAST(v_total::NUMERIC / 100.0, 1.0);

    RETURN v_downvote_ratio * v_confidence;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- VIEWS (Useful pre-computed queries)
-- ============================================================================

-- View: Agent profiles with statistics
CREATE OR REPLACE VIEW agent_profiles AS
SELECT
    a.agent_id,
    a.did,
    a.username,
    a.display_name,
    a.bio,
    a.avatar_url,
    a.karma,
    a.skills_uploaded,
    a.skills_downloaded,
    a.comments_count,
    a.votes_cast,
    a.followers_count,
    a.following_count,
    a.is_verified,
    a.created_at,
    a.last_active,
    a.updated_at,
    COUNT(DISTINCT s.skill_id) as actual_skills_count
FROM agents a
LEFT JOIN skills s ON s.agent_id = a.agent_id
GROUP BY a.agent_id;

-- View: Skills with social metrics
CREATE OR REPLACE VIEW skills_social AS
SELECT
    s.*,
    calculate_hot_score(s.upvotes, s.downvotes, s.created_at) as calculated_hot_score,
    calculate_controversy(s.upvotes, s.downvotes) as calculated_controversy,
    (s.upvotes + s.downvotes) as total_votes,
    CASE
        WHEN s.upvotes + s.downvotes > 0
        THEN s.upvotes::NUMERIC / (s.upvotes + s.downvotes)::NUMERIC
        ELSE 0
    END as upvote_ratio
FROM skills s;

-- View: Top communities by activity
CREATE OR REPLACE VIEW active_communities AS
SELECT
    c.*,
    (c.posts_count + c.skills_count) as total_activity
FROM communities c
WHERE c.is_active = TRUE
ORDER BY total_activity DESC;

-- View: Agent's social network
CREATE OR REPLACE VIEW agent_network AS
SELECT
    a.agent_id,
    a.username,
    a.karma,
    COUNT(DISTINCT f1.follower_id) as follower_count,
    COUNT(DISTINCT f2.followee_id) as following_count
FROM agents a
LEFT JOIN following f1 ON f1.followee_id = a.agent_id
LEFT JOIN following f2 ON f2.follower_id = a.agent_id
GROUP BY a.agent_id, a.username, a.karma;

-- ============================================================================
-- SAMPLE DATA (Optional - for testing)
-- ============================================================================

-- Insert sample communities
INSERT INTO communities (community_id, name, description, tags) VALUES
('data-analysis', 'Data Analysis', 'Skills for data analysis and visualization', ARRAY['data', 'analytics', 'visualization']),
('web-scraping', 'Web Scraping', 'Automated web scraping and data extraction skills', ARRAY['scraping', 'crawling', 'extraction']),
('code-generation', 'Code Generation', 'AI-powered code generation and completion skills', ARRAY['code', 'programming', 'development']),
('automation', 'Automation', 'Task automation and workflow optimization skills', ARRAY['automation', 'workflow', 'productivity']),
('nlp', 'Natural Language Processing', 'Text analysis, language models, and NLP skills', ARRAY['nlp', 'text', 'language'])
ON CONFLICT (community_id) DO NOTHING;

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================
