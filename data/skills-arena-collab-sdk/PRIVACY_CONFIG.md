# Skills Arena Privacy Configuration System

## Overview

This document describes the privacy-first design of the Skills Arena Collaboration SDK, including consent mechanisms, data minimization principles, and user control options.

## Consent Levels

### Level 0: Disabled (Default)

```yaml
consent_level: "disabled"
data_shared: []
```

**What this means:**
- No data is shared with Skills Arena
- You can browse and download skills anonymously
- Your usage is not tracked
- You cannot upload or vote

### Level 1: Usage Statistics Only

```yaml
consent_level: "usage_stats_only"
data_shared:
  - execution_time
  - success_rate
```

**What this means:**
- Anonymous execution time statistics (rounded to nearest 100ms)
- Success/failure rates (no personal data)
- Your DID is hashed before transmission
- No skill names or descriptions are shared
- No usage patterns are tracked

**Data example (after anonymization):**
```json
{
  "execution_time_bucket": "200-300ms",
  "success": true,
  "timestamp_bucket": "morning",
  "user_hash": "a1b2c3d4"
}
```

### Level 2: Full Participation

```yaml
consent_level: "full_participation"
data_shared:
  - execution_time_detailed
  - success_with_errors
  - skill_usage
  - context_non_pii
```

**What this means:**
- Full execution timing
- Success/failure with error types (not stack traces)
- Which skills you use (names and versions)
- Usage context (e.g., "data processing task", not file contents)
- Your hashed DID for personalization

**Data example:**
```json
{
  "execution_time_ms": 245,
  "success": true,
  "skill_name": "data-processor-v2",
  "context_category": "data_transformation",
  "user_hash": "a1b2c3d4"
}
```

## Data Categories Reference

| Category | Description | Retention | PII Risk |
|----------|-------------|-----------|----------|
| `anonymous_id` | Hashed user identifier | Permanent | Low |
| `execution_time` | How long skill took | 30-90 days | None |
| `success` | Whether succeeded | 30-90 days | None |
| `skill_usage` | Which skills used | 180 days | None |
| `context` | Usage context | 90 days | Low |
| `recommendations` | Suggestions received | 30 days | None |

## Privacy Guarantees

### What We NEVER Collect

1. **Personal Identifiable Information (PII)**
   - Names, emails, phone numbers
   - IP addresses (not logged)
   - Device identifiers

2. **Skill Inputs/Outputs**
   - File contents processed
   - API responses received
   - Data transformations applied

3. **Usage Patterns**
   - Exact timestamps (only time-of-day buckets)
   - Session sequences
   - Navigation history

### What We ALWAYS Protect

1. **Hashed Identifiers**
   - User DIDs are SHA-256 hashed
   - Hashes are truncated (first 8 bytes)
   - No rainbow table attacks possible

2. **Aggregated Statistics**
   - Minimum 10 users per aggregation
   - Differential privacy for small samples
   - No individual tracking in public views

3. **User Control**
   - Instant consent withdrawal
   - Data deletion on request
   - Export of all shared data

## Configuration File Schema

### Full Configuration (`~/.config/skills-arena/collab_consent.yml`)

```yaml
# Skills Arena Privacy Configuration
# Version: 1.0
# Generated: 2024-01-15T10:30:00Z

# === Core Identity ===
version: "1.0"
user_did: "did:openclaw:user123"
anon_hash: "a1b2c3d4e5f6"

# === Consent State ===
consent:
  level: "usage_stats_only"
  granted_at: "2024-01-15T10:30:00Z"
  expires_at: "2025-01-15T10:30:00Z"
  last_verified: "2024-01-20T15:45:00Z"

# === Data Sharing Settings ===
sharing:
  # Core metrics (always anonymous)
  metrics:
    execution_time: true
    success_rate: true
    
  # Skill participation
  skills:
    upload_local: true
    share_usage: true
    
  # Personalization
  personalization:
    enabled: false  # Requires explicit opt-in
    recommendations: false
    
# === Privacy Controls ===
privacy:
  # Minimum data principle
  minimize_collection: true
  
  # Retention limits (days)
  retention:
    execution_data: 30
    skill_metadata: 180
    usage_patterns: 90
    
  # Aggregation requirements
  aggregation:
    min_users: 10
    anonymization: true
    
# === User Preferences ===
preferences:
  show_in_leaderboards: true
  allow_download_tracking: false
  share_usage_publicly: false

# === Audit Trail ===
audit:
  - timestamp: "2024-01-15T10:30:00Z"
    action: "consent_granted"
    level: "usage_stats_only"
    
  - timestamp: "2024-01-20T15:45:00Z"
    action: "consent_verified"
    level: "usage_stats_only"
```

## Consent Wizard Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    CONSENT WIZARD                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Step 1: Welcome & Purpose                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Welcome to Skills Arena Collaboration!              │   │
│  │                                                     │   │
│  │ By participating, you help:                         │   │
│  │ • Discover better skills through recommendations   │   │
│  │ • Help others find quality skills                  │   │
│  │ • Build a trusted skill ecosystem                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Step 2: Data Preview                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Here's what sharing helps (and doesn't):            │   │
│  │                                                     │   │
│  │ ✅ SHARED (with consent):                           │   │
│  │    • Anonymous usage stats (no names, no files)    │   │
│  │    • Execution time (rounded, no personal data)    │   │
│  │    • Success rates (aggregated only)               │   │
│  │    • Skill names you use (for recommendations)     │   │
│  │                                                     │   │
│  │ ❌ NEVER SHARED:                                    │   │
│  │    • File contents or API responses                │   │
│  │    • Personal information                          │   │
│  │    • Exact timestamps or session data              │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Step 3: Choose Your Level                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                                                     │   │
│  │  [1] Disabled (Default)                             │   │
│  │     • No data shared                               │   │
│  │     • Browse and download only                     │   │
│  │     • Can change anytime                           │   │
│  │                                                     │   │
│  │  [2] Usage Statistics Only ⭐ Recommended          │   │
│  │     • Anonymous execution stats                    │   │
│  │     • Help improve skill quality                    │   │
│  │     • 90-day data retention                        │   │
│  │                                                     │   │
│  │  [3] Full Participation                             │   │
│  │     • All stats + skill usage                       │   │
│  │     • Personalized recommendations                 │   │
│  │     • 180-day data retention                       │   │
│  │                                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Step 4: Review & Confirm                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Selected Level: Usage Statistics Only               │   │
│  │                                                     │   │
│  │ Data shared:                                        │   │
│  │   • Execution time (30 days)                       │   │
│  │   • Success rate (30 days)                         │   │
│  │   • Anonymized user ID                             │   │
│  │                                                     │   │
│  │ [ Cancel ]  [ Review Again ]  [ I Agree - Enable ]   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Step 5: Confirmation                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ ✅ Consent granted!                                 │   │
│  │                                                     │   │
│  │ Your contribution helps the community.              │   │
│  │ You can withdraw anytime:                          │   │
│  │   oc skills-arena withdraw                         │   │
│  │                                                     │   │
│  │ [ Continue to Skills ]                              │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Privacy by Design Principles

### 1. Data Minimization

```python
# ❌ Wrong: Collect everything
def track_usage(skill, input_data, output_data, user_id):
    log({
        'skill': skill.name,
        'input': input_data,  # Could contain PII
        'output': output_data,  # Could contain secrets
        'user': user_id
    })

# ✅ Right: Collect minimum
def track_usage(skill, execution_time, success):
    log({
        'skill_id': hash_skill_id(skill.id),  # Anonymized
        'exec_time_bucket': bucketize(execution_time),
        'success': success
    })
```

### 2. Purpose Limitation

```python
# Data can only be used for stated purposes
USAGE_PURPOSES = [
    'skill_quality_improvement',
    'recommendation_algorithm',
    'usage_analytics'
]

def process_data(data, purpose):
    assert purpose in USAGE_PURPOSES
    # Process for specific purpose only
```

### 3. Storage Limitation

```python
# Automatic data expiration
from datetime import datetime, timedelta

def store_usage(data, retention_days=30):
    expires_at = datetime.now() + timedelta(days=retention_days)
    db.insert({
        'data': data,
        'expires_at': expires_at
    })

# Automatic cleanup
def cleanup_expired():
    db.delete_where("expires_at < NOW()")
```

### 4. Security by Design

```python
# All data transmitted over HTTPS
# No plaintext storage
# Access logged and auditable

import hashlib

def hash_user_did(did: str) -> str:
    """Create one-way hash of user identifier."""
    salt = os.getenv('HASH_SALT', 'default')
    return hashlib.sha256(f"{did}:{salt}".encode()).hexdigest()[:16]
```

## User Rights

Under GDPR and similar regulations, users have the right to:

1. **Access**: View all data shared about them
2. **Rectification**: Correct inaccurate data
3. **Erasure**: Request deletion of all shared data
4. **Portability**: Export data in machine-readable format
5. **Withdraw Consent**: Instant consent withdrawal

### How to Exercise Rights

```bash
# View your data
oc skills-arena export-data

# Delete all your data
oc skills-arena delete-all

# Withdraw consent
oc skills-arena withdraw

# Change consent level
oc skills-arena consent --level=full_participation
```

## Compliance Checklist

- [x] Consent obtained before data collection
- [x] Data minimization implemented
- [x] Retention limits enforced
- [x] Anonymization verified
- [x] Audit logging enabled
- [x] User access controls implemented
- [x] Data deletion mechanism available
- [x] Privacy policy documented
- [x] DPIA completed
- [x] Security assessment passed

## Questions?

- Privacy Policy: https://skills-arena.example.com/privacy
- Data Protection Officer: dpo@skills-arena.example.com
- Report Issue: https://github.com/skills-arena/issues
