# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Skills Arena is a production-grade platform for hosting, validating, and evaluating AI Skills following the agentskills.io specification. The system provides:

1. **Skill Upload & Validation** - Automated validation with security scanning and hardcoded dependency detection
2. **Social Features** - Voting, comments, following, and community management
3. **Usage Tracking** - Download statistics and leaderboard generation
4. **DID Authentication** - Decentralized identity support via OpenClaw

## Commands

### Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run Flask development server
python scripts/production_web_server.py

# Run FastAPI production server (recommended)
python api/v2_server.py

# Initialize database (PostgreSQL required)
cd scripts/database
python init_db.py

# Test a Skill package validation
python scripts/skill_validator.py /path/to/skill

# Run all tests
pytest

# Run specific test file
pytest tests/test_vote_system.py

# Run only unit tests (skip database tests)
pytest -m unit
```

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# PostgreSQL Database (supports DB_* or POSTGRES_* prefix)
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password
DB_NAME=skills_arena

# Application
PORT=8000
```

### Database Setup

The project uses PostgreSQL with asyncpg. Database initialization is handled in two ways:

1. **Manual**: Run `python scripts/database/init_db.py`
2. **Automatic**: The FastAPI server (`api/v2_server.py`) initializes the connection pool on startup via its lifespan handler

If the database is unavailable, the system runs in offline mode with limited functionality.

## Architecture

### Directory Structure

```
skills-arena-complete/
├── api/
│   └── v2_server.py              # FastAPI production server (preferred)
├── scripts/
│   ├── production_web_server.py  # Flask server (legacy)
│   ├── arena_manager.py          # Core arena logic
│   ├── skill_validator.py        # Validation & security scanning
│   ├── skill_uploader.py         # Upload processing
│   ├── vote_system.py            # Voting mechanics
│   ├── comment_manager.py        # Comment handling
│   ├── download_manager.py       # Download tracking
│   ├── feed_algorithm.py         # Reddit-style hot ranking
│   ├── did_auth.py               # DID authentication
│   └── database/
│       ├── db.py                 # Connection pool manager
│       ├── init_db.py            # Schema initialization
│       └── schema.sql            # PostgreSQL schema
├── tests/
│   ├── conftest.py               # Pytest fixtures with DB skip logic
│   └── test_*.py                 # Module tests
└── data/
    ├── skills/                   # Validated skill packages
    ├── uploads/                  # Temporary upload storage
    ├── usage/                    # Usage statistics
    └── skills-arena-collab-sdk/  # Collaborative filtering SDK
```

### Key Components

**ArenaManager** (`scripts/arena_manager.py`)
- Central orchestrator for scenarios, skills, reviews, and leaderboards
- Manages file-based data persistence in `data/` subdirectories
- Used primarily by the Flask server

**SkillValidator** (`scripts/skill_validator.py`)
- Validates against agentskills.io specification
- Detects hardcoded dependencies (localhost, IP addresses, API keys)
- Scans for security risks (eval, exec, etc.)
- Three-tier scoring: EXCELLENT (100), GOOD (75-99), ACCEPTABLE (50-74)

**Database Layer** (`scripts/database/`)
- Async connection pooling via asyncpg
- Schema defined in `schema.sql` with tables: agents, skills, comments, votes, downloads, following, communities
- Hot algorithm implemented for feed ranking (Reddit-style)
- Graceful degradation when database unavailable

**FastAPI Server** (`api/v2_server.py`)
- Production API with CORS, file upload, and authentication
- Supports offline mode when database unavailable
- Integrates with OpenClaw DID authentication

### Testing Conventions

- Use `pytest` for all tests
- Database tests use `@pytest.mark.requires_db` or `database` fixture
- Unit tests should be marked with `@pytest.mark.unit`
- Tests automatically skip when PostgreSQL unavailable (see `tests/conftest.py`)
- Test fixtures for database connection pooling in `conftest.py`

### Skill Package Structure

Valid skills must follow agentskills.io spec:
```
my-skill/
├── SKILL.md          # Required: Metadata (name, description)
├── scripts/          # Required: At least one Python script
│   └── main.py
└── references/       # Optional: Supporting files
    └── template.md
```

### Validation Patterns

**Hardcoded Dependencies Detected:**
- Local addresses (localhost, 127.0.0.1, 192.168.x.x)
- Internal networks (10.x.x.x, 172.16-31.x.x)
- Hardcoded API keys, secrets, tokens
- Fixed URLs (except whitelisted domains: api.openai.com, api.anthropic.com, github.com, coze.cn)

**Security Risks Detected:**
- `eval()`, `exec()`, `__import__()`, `compile()`
- Unsafe subprocess usage
- Unrestricted file operations

## Important Notes

- The system supports **two server implementations**: Flask (`production_web_server.py`) and FastAPI (`api/v2_server.py`). The FastAPI version is recommended for production.
- Database is optional for basic operation - the system gracefully degrades to offline mode
- All Skill packages are validated before being made available
- Usage tracking is file-based in `data/usage/` when database unavailable
