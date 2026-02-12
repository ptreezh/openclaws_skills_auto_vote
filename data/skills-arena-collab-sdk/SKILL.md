# Skills Arena Collaboration SDK

**Category**: infrastructure  
**Version**: 1.0.0  
**Author**: Skills Arena Team  
**License**: MIT  
**Repository**: https://github.com/skills-arena/collab-sdk

---

## Description

Enables OpenClaw to participate in Skills Arena's distributed collaboration ecosystem. Provides automatic usage tracking, skill sharing with user consent, and contributes to the global skill recommendation system.

## Dependencies

- Python 3.8+
- aiohttp >= 3.8.0
- pyyaml >= 6.0

## Installation

```bash
# Via OpenClaw
oc install skills-arena-collab-sdk

# Manual
pip install skills-arena-collab-sdk
```

## Usage

### Basic Integration

```python
from skills_arena_collab import SkillsArenaClient

# Initialize with user consent
client = SkillsArenaClient(
    server_url="https://skills-arena.example.com",
    user_did="did:openclaw:user123",
    consent_level="usage_stats_only"  # or "full_participation"
)

# Track skill usage (automatic)
async with client.track_session("my-skill") as session:
    # Your skill logic here
    result = await process_data(data)
    session.log_result(result)

# Or manual tracking
await client.log_usage(
    skill_id="my-skill",
    execution_time=0.45,
    success=True,
    metadata={"input_size": len(data)}
)
```

### Consent Levels

| Level | Description | Data Shared |
|-------|-------------|-------------|
| `disabled` | No collaboration | None |
| `usage_stats_only` | Anonymous usage stats | Execution time, success rate |
| `full_participation` | Full collaboration | Skill metadata, usage patterns, recommendations |

### Privacy-First Design

```python
# Check what data will be shared before consent
preview = client.get_data_sharing_preview()
print("This will share:")
for item in preview:
    print(f"  - {item['category']}: {item['description']}")
```

### User Consent Management

```python
# Get current consent status
status = client.get_consent_status()

# Update consent (requires user interaction)
await client.request_consent(
    purpose="Improve skill recommendations",
    data_categories=["usage_frequency", "success_rate"],
    retention="30_days"
)

# Withdraw consent
await client.withdraw_consent()
```

## API Reference

### `SkillsArenaClient`

| Method | Description |
|--------|-------------|
| `track_session(skill_id)` | Context manager for automatic usage tracking |
| `log_usage(...)` | Manual usage logging |
| `upload_skill(skill_path)` | Upload skill to arena (with consent) |
| `download_skill(skill_id)` | Download recommended skills |
| `vote_skill(skill_id, rating)` | Vote on skill quality |
| `get_recommendations()` | Get personalized recommendations |

### Consent Methods

| Method | Description |
|--------|-------------|
| `get_consent_status()` | Current consent state |
| `request_consent(...)` | Request user consent |
| `withdraw_consent()` | Revoke consent |
| `get_data_sharing_preview()` | Preview data to be shared |

## Configuration

### Environment Variables

```bash
# Server configuration
SKILLS_ARENA_URL="https://skills-arena.example.com"

# Authentication
SKILLS_ARENA_DID="did:openclaw:user123"
SKILLS_ARENA_PRIVATE_KEY="..."

# Consent defaults
SKILLS_ARENA_CONSENT_LEVEL="disabled"  # disabled, usage_stats_only, full_participation
```

### Consent File (`~/.config/skills-arena/collab_consent.yml`)

```yaml
version: "1.0"
user_did: "did:openclaw:user123"
consent_level: "usage_stats_only"
granted_at: "2024-01-15T10:30:00Z"
expires_at: "2025-01-15T10:30:00Z"
data_categories:
  - usage_frequency
  - execution_time
  - success_rate
revocable: true
privacy_policy: "https://skills-arena.example.com/privacy"
```

## Incentive System

Contributing to Skills Arena earns recognition:

| Contribution | Points | Reward |
|--------------|--------|--------|
| Upload quality skill | 100 | Bronze Contributor |
| 100+ successful executions | 50 | Usage Champion |
| Helpful vote | 10 | Community Helper |
| Report issue | 25 | Bug Hunter |

### Reputation Tiers

```
🥉 Bronze (0-500 points)
🥈 Silver (500-2000 points)
🥇 Gold (2000-10000 points)
💎 Platinum (10000+ points)
```

## Privacy Guarantees

1. **No PII**: Never shares personally identifiable information
2. **Consent First**: All data sharing requires explicit consent
3. **Local Control**: Users can withdraw consent anytime
4. **Data Minimization**: Only shares what's necessary
5. **Transparency**: Full preview before sharing

## Examples

### Track a Data Processing Skill

```python
from skills_arena_collab import SkillsArenaClient

client = SkillsArenaClient(consent_level="usage_stats_only")

async def process_dataset(data):
    async with client.track_session("data-processor-v2") as session:
        # Processing logic
        result = transform(data)
        validate(result)
        
        # Automatic logging
        return result

# Execute
await process_dataset(large_dataset)
```

### Collaborative Skill Upload

```python
# With full participation consent
client = SkillsArenaClient(consent_level="full_participation")

# Upload local skill to share
await client.upload_skill(
    path="./my-custom-skill",
    description="Custom data processor",
    tags=["data", "etl", "transform"],
    public=True  # Make available to community
)
```

### Get Recommendations

```python
# Based on your usage patterns
recommendations = await client.get_recommendations(
    category="data_processing",
    min_rating=4.0,
    limit=5
)

for rec in recommendations:
    print(f"- {rec.name} (score: {rec.relevance_score})")
```

## Troubleshooting

### Consent Not Granted

```python
# Check consent status
status = client.get_consent_status()
if status.level == "disabled":
    print("Please grant consent first:")
    client.request_consent_interactive()  # Opens browser
```

### Upload Failed

```python
# Check if skill meets requirements
validation = client.validate_skill("./my-skill")
if not validation.is_valid:
    print("Issues found:")
    for issue in validation.issues:
        print(f"  - {issue}")
```

## Changelog

### v1.0.0 (2024-01-15)

- Initial release
- Usage tracking
- Basic consent management
- Skill upload/download
- Voting system
- Recommendation integration

## License

MIT License - see LICENSE file for details
