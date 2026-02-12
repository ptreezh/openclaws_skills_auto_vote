#!/usr/bin/env python3
"""
Skills Arena Collaboration SDK

Enables OpenClaw to participate in Skills Arena's distributed collaboration ecosystem.
Provides automatic usage tracking, skill sharing with user consent, and contributes
to the global skill recommendation system.

Author: Skills Arena Team
Version: 1.0.0
"""

import asyncio
import hashlib
import json
import os
import time
import uuid
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple, Union

import aiohttp
import yaml


class ConsentLevel(Enum):
    """User consent levels for data sharing."""

    DISABLED = "disabled"
    USAGE_STATS_ONLY = "usage_stats_only"
    FULL_PARTICIPATION = "full_participation"


class ConsentStatus(Enum):
    """Consent grant status."""

    NOT_GRANTED = "not_granted"
    PENDING = "pending"
    GRANTED = "granted"
    REVOKED = "revoked"
    EXPIRED = "expired"


@dataclass
class ConsentConfig:
    """User consent configuration."""

    version: str = "1.0"
    user_did: str = ""
    consent_level: ConsentLevel = ConsentLevel.DISABLED
    granted_at: Optional[str] = None
    expires_at: Optional[str] = None
    data_categories: List[str] = field(default_factory=list)
    revocable: bool = True
    privacy_policy_url: str = "https://skills-arena.example.com/privacy"

    @classmethod
    def load(cls, path: Path) -> "ConsentConfig":
        """Load consent config from file."""
        if not path.exists():
            return cls()

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        return cls(
            version=data.get("version", "1.0"),
            user_did=data.get("user_did", ""),
            consent_level=ConsentLevel(data.get("consent_level", "disabled")),
            granted_at=data.get("granted_at"),
            expires_at=data.get("expires_at"),
            data_categories=data.get("data_categories", []),
            revocable=data.get("revocable", True),
            privacy_policy_url=data.get(
                "privacy_policy", "https://skills-arena.example.com/privacy"
            ),
        )

    def save(self, path: Path) -> None:
        """Save consent config to file."""
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "version": self.version,
            "user_did": self.user_did,
            "consent_level": self.consent_level.value,
            "granted_at": self.granted_at,
            "expires_at": self.expires_at,
            "data_categories": self.data_categories,
            "revocable": self.revocable,
            "privacy_policy": self.privacy_policy_url,
        }

        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False)

    def is_valid(self) -> bool:
        """Check if consent is currently valid."""
        if self.consent_level == ConsentLevel.DISABLED:
            return False

        if self.expires_at:
            expiry = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
            if datetime.now() > expiry:
                return False

        return True


@dataclass
class UsageData:
    """Usage data for a single execution."""

    skill_id: str
    execution_time: float
    success: bool
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API submission."""
        return {
            "skill_id": self.skill_id,
            "execution_time": self.execution_time,
            "success": self.success,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
            "metadata": self.metadata,
        }


@dataclass
class SkillMetadata:
    """Skill metadata for upload."""

    name: str
    description: str
    version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)
    category: str = "general"
    author_did: str = ""
    public: bool = True
    skill_path: Optional[Path] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "tags": self.tags,
            "category": self.category,
            "author_did": self.author_did,
            "public": self.public,
        }


class ConsentManager:
    """Manages user consent for data sharing."""

    CONSENT_FILE = Path("~/.config/skills-arena/collab_consent.yml")
    DATA_CATEGORIES = {
        "usage_frequency": "How often skills are used",
        "execution_time": "Time taken to execute skills",
        "success_rate": "Success/failure rates",
        "skill_metadata": "Names and descriptions of skills used",
        "usage_patterns": "Patterns in skill usage over time",
        "recommendations": "Skill recommendations received and used",
    }

    def __init__(self, user_did: str, consent_path: Optional[Path] = None):
        self.user_did = user_did
        self.consent_path = consent_path or self._get_default_consent_path()
        self._config: Optional[ConsentConfig] = None

    def _get_default_consent_path(self) -> Path:
        """Get default consent file path."""
        return Path(os.path.expanduser(self.CONSENT_FILE))

    @property
    def config(self) -> ConsentConfig:
        """Load and cache consent config."""
        if self._config is None:
            self._config = ConsentConfig.load(self.consent_path)
        return self._config

    def get_status(self) -> Tuple[ConsentStatus, str]:
        """Get current consent status."""
        if not self.config.is_valid():
            return ConsentStatus.NOT_GRANTED, "Consent not granted or expired"

        if self.config.consent_level == ConsentLevel.DISABLED:
            return ConsentStatus.NOT_GRANTED, "Consent disabled by user"

        if not self.config.granted_at:
            return ConsentStatus.NOT_GRANTED, "Consent not granted"

        return ConsentStatus.GRANTED, f"Consent granted at {self.config.granted_at}"

    def get_data_sharing_preview(self) -> List[Dict[str, str]]:
        """Get preview of data that will be shared."""
        level = self.config.consent_level

        if level == ConsentLevel.DISABLED:
            return []

        preview = []

        # Always shared
        preview.append(
            {
                "category": "anonymous_id",
                "description": "Anonymous user identifier (DID hash)",
                "retention": "Permanent",
            }
        )

        if level == ConsentLevel.USAGE_STATS_ONLY:
            preview.extend(
                [
                    {
                        "category": "execution_time",
                        "description": "Skill execution time",
                        "retention": "30 days",
                    },
                    {
                        "category": "success",
                        "description": "Success/failure status",
                        "retention": "30 days",
                    },
                ]
            )

        elif level == ConsentLevel.FULL_PARTICIPATION:
            preview.extend(
                [
                    {
                        "category": "execution_time",
                        "description": "Detailed execution timing",
                        "retention": "90 days",
                    },
                    {
                        "category": "success",
                        "description": "Success/failure with error types",
                        "retention": "90 days",
                    },
                    {
                        "category": "skill_usage",
                        "description": "Which skills were used",
                        "retention": "180 days",
                    },
                    {
                        "category": "context",
                        "description": "Usage context (non-PII)",
                        "retention": "90 days",
                    },
                ]
            )

        return preview

    async def request_consent(
        self,
        purpose: str = "Improve skill recommendations and help the community",
        categories: Optional[List[str]] = None,
        duration_days: int = 365,
    ) -> bool:
        """Request user consent (opens interactive prompt)."""

        # Build consent request
        preview = self.get_data_sharing_preview()

        consent_data = {
            "purpose": purpose,
            "categories": categories or list(self.DATA_CATEGORIES.keys()),
            "preview": preview,
            "duration": duration_days,
            "user_did": self.user_did,
        }

        print("\n" + "=" * 60)
        print("SKILLS ARENA - Consent Request")
        print("=" * 60)
        print(f"\nPurpose: {purpose}")
        print(f"\nData to be shared:")

        for item in preview:
            print(f"  - {item['category']}: {item['description']}")
            print(f"    Retention: {item['retention']}")

        print(f"\nDuration: {duration_days} days")
        print("\nPrivacy Policy: " + self.config.privacy_policy_url)
        print("\n" + "-" * 60)

        # Interactive consent (simplified - in production would open browser)
        response = input("\nDo you consent? (yes/no/limited): ").strip().lower()

        if response == "yes":
            level = ConsentLevel.FULL_PARTICIPATION
        elif response == "limited":
            level = ConsentLevel.USAGE_STATS_ONLY
        else:
            print("Consent not granted.")
            return False

        # Save consent
        self.config.consent_level = level
        self.config.user_did = self.user_did
        self.config.granted_at = datetime.now().isoformat()
        self.config.expires_at = datetime.now() + timedelta(days=duration_days)
        self.config.data_categories = categories or list(self.DATA_CATEGORIES.keys())

        self.config.save(self.consent_path)
        print(f"\nConsent granted at level: {level.value}")
        return True

    async def withdraw_consent(self) -> bool:
        """Withdraw previously granted consent."""
        if not self.config.revocable:
            print("Consent is not revocable for this account.")
            return False

        self.config.consent_level = ConsentLevel.DISABLED
        self.config.granted_at = None
        self.config.expires_at = None
        self.config.data_categories = []

        self.config.save(self.consent_path)
        print("Consent withdrawn successfully.")
        return True


class UsageTracker:
    """Tracks skill usage locally before sending to server."""

    def __init__(self, max_queue_size: int = 100):
        self.queue: List[UsageData] = []
        self.max_queue_size = max_queue_size
        self.current_session: Optional[str] = None

    def log(
        self,
        skill_id: str,
        execution_time: float,
        success: bool,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UsageData:
        """Log a usage event."""
        data = UsageData(
            skill_id=skill_id,
            execution_time=execution_time,
            success=success,
            metadata=metadata or {},
        )

        self.queue.append(data)

        # Keep queue bounded
        if len(self.queue) > self.max_queue_size:
            self.queue = self.queue[-self.max_queue_size :]

        return data

    def get_queue(self) -> List[UsageData]:
        """Get current queue."""
        return self.queue.copy()

    def clear(self) -> None:
        """Clear the queue."""
        self.queue.clear()

    def __len__(self) -> int:
        return len(self.queue)


class Session:
    """Context manager for tracking a skill execution session."""

    def __init__(
        self,
        client: "SkillsArenaClient",
        skill_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.client = client
        self.skill_id = skill_id
        self.metadata = metadata or {}
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.result: Optional[Any] = None
        self.error: Optional[Exception] = None

    async def __aenter__(self) -> "Session":
        self.start_time = time.time()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        self.end_time = time.time()
        execution_time = self.end_time - self.start_time

        if exc_type is not None:
            self.error = exc_val
            await self.client._log_usage(
                self.skill_id, execution_time, success=False, metadata=self.metadata
            )
        else:
            await self.client._log_usage(
                self.skill_id, execution_time, success=True, metadata=self.metadata
            )

    def set_result(self, result: Any) -> None:
        """Set the result of the session."""
        self.result = result


class SkillsArenaClient:
    """
    Main client for Skills Arena collaboration.

    Example:
        client = SkillsArenaClient(
            server_url="https://skills-arena.example.com",
            user_did="did:openclaw:user123"
        )

        # Track usage
        async with client.track_session("my-skill") as session:
            result = await process_data(data)
            session.set_result(result)
    """

    def __init__(
        self,
        server_url: str = "https://skills-arena.example.com",
        user_did: Optional[str] = None,
        consent_level: Union[ConsentLevel, str] = ConsentLevel.DISABLED,
        auto_send: bool = True,
        send_interval: float = 60.0,
    ):
        self.server_url = server_url.rstrip("/")
        self.user_did = user_did or self._generate_anon_id()
        self.auto_send = auto_send
        self.send_interval = send_interval

        # Initialize components
        self.consent = ConsentManager(self.user_did)
        self.tracker = UsageTracker()
        self._session: Optional[aiohttp.ClientSession] = None
        self._send_task: Optional[asyncio.Task] = None

        # Set initial consent level
        if isinstance(consent_level, str):
            consent_level = ConsentLevel(consent_level)

        if consent_level != ConsentLevel.DISABLED:
            self.consent.config.consent_level = consent_level
            self.consent.config.user_did = self.user_did
            self.consent.config.save(self.consent.consent_path)

    def _generate_anon_id(self) -> str:
        """Generate anonymous user ID."""
        import secrets

        anon_id = secrets.token_hex(16)
        return f"did:openclaw:anon:{anon_id}"

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self) -> None:
        """Close the client and send pending data."""
        if self._send_task:
            self._send_task.cancel()
            try:
                await self._send_task
            except asyncio.CancelledError:
                pass

        if self._session:
            await self._session.close()

    def get_consent_status(self) -> Tuple[ConsentStatus, str]:
        """Get current consent status."""
        return self.consent.get_status()

    def get_data_sharing_preview(self) -> List[Dict[str, str]]:
        """Get preview of data that will be shared."""
        return self.consent.get_data_sharing_preview()

    async def request_consent(
        self,
        purpose: str = "Improve skill recommendations",
        categories: Optional[List[str]] = None,
        duration_days: int = 365,
    ) -> bool:
        """Request user consent."""
        return await self.consent.request_consent(purpose, categories, duration_days)

    async def withdraw_consent(self) -> bool:
        """Withdraw consent."""
        result = await self.consent.withdraw_consent()
        if result:
            await self._send_pending_data()  # Send final data before stopping
        return result

    @asynccontextmanager
    async def track_session(
        self, skill_id: str, metadata: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Session, None]:
        """
        Track a skill execution session.

        Example:
            async with client.track_session("data-processor") as session:
                result = await process_data(data)
                session.set_result(result)
        """
        session = Session(self, skill_id, metadata)
        await session.__aenter__()
        try:
            yield session
        finally:
            await session.__aexit__(None, None, None)

    async def _log_usage(
        self,
        skill_id: str,
        execution_time: float,
        success: bool,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log usage data locally."""
        self.tracker.log(skill_id, execution_time, success, metadata)

        if self.auto_send:
            await self._maybe_send_data()

    async def log_usage(
        self,
        skill_id: str,
        execution_time: float,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log usage data directly (outside session)."""
        await self._log_usage(skill_id, execution_time, success, metadata)

    async def _maybe_send_data(self) -> None:
        """Send data if conditions are met."""
        if not self.consent.config.is_valid():
            return

        if len(self.tracker) >= 10 or (
            self._send_task is None or self._send_task.done()
        ):
            self._send_task = asyncio.create_task(self._send_pending_data())

    async def _send_pending_data(self) -> None:
        """Send pending usage data to server."""
        if not self.consent.config.is_valid():
            return

        data_to_send = self.tracker.get_queue()
        if not data_to_send:
            return

        session = await self._get_session()

        try:
            async with session.post(
                f"{self.server_url}/api/v2/skills/usage",
                json={
                    "user_did": self._anonimize(self.user_did),
                    "usage_data": [d.to_dict() for d in data_to_send],
                },
            ) as response:
                if response.status == 200:
                    self.tracker.clear()
                    print(f"Sent {len(data_to_send)} usage records")
                else:
                    print(f"Failed to send data: {response.status}")
        except Exception as e:
            print(f"Error sending data: {e}")

    def _anonimize(self, did: str) -> str:
        """Create anonymous version of DID."""
        # Hash the DID to create anonymous identifier
        hash_bytes = hashlib.sha256(did.encode()).digest()
        return f"anon:{hash_bytes[:8].hex()}"

    async def upload_skill(
        self,
        skill_path: Union[str, Path],
        metadata: Optional[SkillMetadata] = None,
        auto_register: bool = True,
    ) -> Dict[str, Any]:
        """
        Upload a skill to the arena.

        Requires FULL_PARTICIPATION consent level.
        """
        if not self.consent.config.is_valid():
            raise PermissionError("Consent not granted or expired")

        if self.consent.config.consent_level != ConsentLevel.FULL_PARTICIPATION:
            raise PermissionError("Skill upload requires full_participation consent")

        path = Path(skill_path)
        if not path.exists():
            raise FileNotFoundError(f"Skill path not found: {skill_path}")

        # Validate skill
        validation = await self._validate_skill(path)
        if not validation["valid"]:
            raise ValueError(f"Skill validation failed: {validation['errors']}")

        # Get metadata
        skill_meta = metadata or await self._extract_metadata(path)

        # Create upload request
        session = await self._get_session()

        try:
            async with session.post(
                f"{self.server_url}/api/v2/skills/upload", json=skill_meta.to_dict()
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"Skill uploaded: {result.get('skill_id')}")
                    return result
                else:
                    error = await response.text()
                    raise RuntimeError(f"Upload failed: {error}")
        except Exception as e:
            print(f"Upload error: {e}")
            raise

    async def _validate_skill(self, path: Path) -> Dict[str, Any]:
        """Validate a skill before upload."""
        errors = []

        # Check required files
        skill_md = path / "SKILL.md"
        scripts_dir = path / "scripts"

        if not skill_md.exists():
            errors.append("Missing SKILL.md")
        if not scripts_dir.exists():
            errors.append("Missing scripts/ directory")
        elif not list(scripts_dir.glob("*.py")):
            errors.append("No Python scripts in scripts/")

        # Check SKILL.md structure
        if skill_md.exists():
            with open(skill_md, "r", encoding="utf-8") as f:
                content = f.read()
                required_fields = ["# ", "## Description", "## Usage"]
                for field in required_fields:
                    if field not in content:
                        errors.append(f"Missing section in SKILL.md: {field}")

        return {"valid": len(errors) == 0, "errors": errors}

    async def _extract_metadata(self, path: Path) -> SkillMetadata:
        """Extract metadata from skill directory."""
        skill_md = path / "SKILL.md"

        if not skill_md.exists():
            return SkillMetadata(
                name=path.name, description="Uploaded skill", author_did=self.user_did
            )

        with open(skill_md, "r", encoding="utf-8") as f:
            content = f.read()

        # Simple extraction (in production, use proper markdown parsing)
        name = path.name
        description = ""

        if content.startswith("# "):
            name = content.split("\n")[0][2:].strip()

        # Extract description (first paragraph after header)
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if line.strip() and not line.startswith("#"):
                description = line.strip()
                break

        # Extract tags
        tags = []
        for line in lines:
            if "## Tags" in line or "Tags:" in line:
                tag_content = line.split(":", 1)[-1].strip()
                tags = [t.strip() for t in tag_content.split(",")]
                break

        return SkillMetadata(
            name=name, description=description, tags=tags, author_did=self.user_did
        )

    async def download_skill(self, skill_id: str, dest: Path) -> bool:
        """Download a skill from the arena."""
        session = await self._get_session()

        try:
            async with session.get(
                f"{self.server_url}/api/v2/skills/{skill_id}/download"
            ) as response:
                if response.status != 200:
                    return False

                content = await response.read()
                dest.mkdir(parents=True, exist_ok=True)

                zip_path = dest / f"{skill_id}.zip"
                with open(zip_path, "wb") as f:
                    f.write(content)

                # Extract
                import zipfile

                with zipfile.ZipFile(zip_path, "r") as z:
                    z.extractall(dest)

                zip_path.unlink()  # Remove zip
                return True

        except Exception as e:
            print(f"Download error: {e}")
            return False

    async def vote_skill(
        self, skill_id: str, rating: int, comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """Vote on a skill (1-5 stars)."""
        if not (1 <= rating <= 5):
            raise ValueError("Rating must be between 1 and 5")

        if not self.consent.config.is_valid():
            raise PermissionError("Consent not granted")

        session = await self._get_session()

        try:
            async with session.post(
                f"{self.server_url}/api/v2/skills/{skill_id}/vote",
                json={
                    "rating": rating,
                    "comment": comment,
                    "user_did": self._anonimize(self.user_did),
                },
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    raise RuntimeError(f"Vote failed: {response.status}")
        except Exception as e:
            print(f"Vote error: {e}")
            raise

    async def get_recommendations(
        self, category: Optional[str] = None, min_rating: float = 0.0, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get personalized skill recommendations."""
        if not self.consent.config.is_valid():
            # Return popular skills only
            params = {"sort": "popular", "limit": limit}
        else:
            # Use personalization
            params = {
                "user_did": self._anonimize(self.user_did),
                "min_rating": min_rating,
                "limit": limit,
            }
            if category:
                params["category"] = category

        session = await self._get_session()

        try:
            async with session.get(
                f"{self.server_url}/api/v2/skills/search", params=params
            ) as response:
                if response.status == 200:
                    return await response.json()
                return []
        except Exception as e:
            print(f"Recommendations error: {e}")
            return []


# ============ Incentive System ============


class IncentiveTracker:
    """Tracks user contributions for incentive system."""

    POINTS = {
        "upload": 100,
        "execution_100": 50,
        "execution_500": 100,
        "execution_1000": 200,
        "helpful_vote": 10,
        "report_issue": 25,
        "referral": 75,
    }

    def __init__(self, user_did: str):
        self.user_did = user_did
        self._points: int = 0
        self._contributions: List[Dict[str, Any]] = []

    @property
    def total_points(self) -> int:
        return self._points

    @property
    def tier(self) -> str:
        if self._points >= 10000:
            return "💎 Platinum"
        elif self._points >= 2000:
            return "🥇 Gold"
        elif self._points >= 500:
            return "🥈 Silver"
        else:
            return "🥉 Bronze"

    def add_points(self, category: str, description: str) -> None:
        """Add points for a contribution."""
        points = self.POINTS.get(category, 0)
        if points > 0:
            self._points += points
            self._contributions.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "category": category,
                    "description": description,
                    "points": points,
                }
            )
            print(f"+{points} points: {description} (Total: {self._points})")

    def get_summary(self) -> Dict[str, Any]:
        """Get incentive summary."""
        return {
            "user_did": self.user_did,
            "total_points": self._points,
            "tier": self.tier,
            "contributions": self._contributions[-20:],  # Last 20
        }


# ============ Local Skill Scanner ============


class LocalSkillScanner:
    """
    Scans local OpenClaw skills for participation in collaboration.

    Requires explicit user consent before scanning or sharing.
    """

    SCAN_PATHS = [
        Path("./skills"),
        Path("~/.local/share/openclaw/skills"),
        Path("~/.openclaw/skills"),
        Path("~/.config/openclaw/skills"),
    ]

    def __init__(self, client: SkillsArenaClient):
        self.client = client
        self.scanned_skills: List[Dict[str, Any]] = []

    async def scan_local_skills(
        self, paths: Optional[List[Path]] = None
    ) -> List[Dict[str, Any]]:
        """Scan local skill directories."""
        paths = paths or self.SCAN_PATHS

        print("\n" + "=" * 60)
        print("LOCAL SKILL SCANNER")
        print("=" * 60)
        print(f"\nPaths to scan:")
        for p in paths:
            expanded = Path(os.path.expanduser(p))
            print(f"  - {expanded}")

        # Check consent first
        status, _ = self.client.get_consent_status()
        if status != ConsentStatus.GRANTED:
            print("\n⚠️  Consent required before scanning!")
            print("Run: await client.request_consent()")
            return []

        print("\n🔍 Scanning...")
        skills_found = []

        for scan_path in paths:
            expanded = Path(os.path.expanduser(scan_path))
            if not expanded.exists():
                continue

            for skill_path in expanded.iterdir():
                if skill_path.is_dir():
                    skill_info = await self._analyze_skill(skill_path)
                    if skill_info:
                        skills_found.append(skill_info)

        self.scanned_skills = skills_found
        print(f"\n✅ Found {len(skills_found)} skills")

        return skills_found

    async def _analyze_skill(self, path: Path) -> Optional[Dict[str, Any]]:
        """Analyze a single skill directory."""
        skill_md = path / "SKILL.md"

        if not skill_md.exists():
            return None

        with open(skill_md, "r", encoding="utf-8") as f:
            content = f.read()

        # Extract basic info
        name = path.name
        description = ""

        if content.startswith("# "):
            name = content.split("\n")[0][2:].strip()

        # Check for usage statistics
        usage_file = path / ".usage_stats"
        local_usage = {}
        if usage_file.exists():
            with open(usage_file, "r") as f:
                local_usage = json.load(f)

        return {
            "path": str(path),
            "name": name,
            "description": description,
            "local_usage": local_usage,
            "ready_to_share": local_usage.get("total_executions", 0) > 0,
        }

    def get_share_preview(self) -> List[Dict[str, Any]]:
        """Get preview of skills ready to share."""
        return [s for s in self.scanned_skills if s["ready_to_share"]]

    async def share_skills(self, skill_indices: Optional[List[int]] = None) -> int:
        """Share selected skills with the arena."""
        to_share = self.get_share_preview()

        if skill_indices:
            to_share = [to_share[i] for i in skill_indices if i < len(to_share)]

        if not to_share:
            print("No skills ready to share")
            return 0

        print(f"\n📤 Sharing {len(to_share)} skills with Skills Arena...")
        shared = 0

        for skill in to_share:
            try:
                await self.client.upload_skill(
                    Path(skill["path"]),
                    metadata=SkillMetadata(
                        name=skill["name"],
                        description=skill["description"],
                        author_did=self.client.user_did,
                        public=True,
                    ),
                )
                shared += 1
            except Exception as e:
                print(f"  ❌ Failed to share {skill['name']}: {e}")

        print(f"\n✅ Successfully shared {shared}/{len(to_share)} skills")
        return shared


# ============ Main Entry Point ============


async def main():
    """Demo the Skills Arena Collaboration SDK."""

    print("\n" + "=" * 60)
    print("SKILLS ARENA COLLABORATION SDK - Demo")
    print("=" * 60)

    # Initialize client
    client = SkillsArenaClient(
        server_url="https://skills-arena.example.com",
        consent_level=ConsentLevel.DISABLED,  # Start with no consent
    )

    # Check consent status
    status, message = client.get_consent_status()
    print(f"\nConsent Status: {status.value}")
    print(f"Message: {message}")

    # Get data sharing preview
    preview = client.get_data_sharing_preview()
    if preview:
        print("\nData that would be shared:")
        for item in preview:
            print(f"  - {item['category']}: {item['description']}")

    # Simulate skill usage tracking
    print("\n📊 Simulating skill usage...")
    for i in range(5):
        await client.log_usage(
            skill_id=f"example-skill-{i}",
            execution_time=0.1 * (i + 1),
            success=True,
            metadata={"iteration": i},
        )

    print(f"\n📦 Tracked {len(client.tracker)} usage events")

    # Show incentive tracker
    incentive = IncentiveTracker(client.user_did)
    incentive.add_points("execution_100", "Reached 100 executions")
    incentive.add_points("helpful_vote", "Voted on 3 skills")
    incentive.add_points("upload", "Uploaded custom skill")

    print(f"\n🏆 Incentive Summary:")
    print(f"   Points: {incentive.total_points}")
    print(f"   Tier: {incentive.tier}")

    # Show local scanner
    print("\n🔍 Local Skill Scanner:")
    scanner = LocalSkillScanner(client)

    # Note: Actual scanning requires consent
    print("   (Run scanner.request_consent() first)")

    await client.close()
    print("\n✅ Demo complete!")


if __name__ == "__main__":
    asyncio.run(main())
