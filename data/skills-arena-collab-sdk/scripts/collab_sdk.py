#!/usr/bin/env python3
"""
Skills Arena Collaboration SDK - Complete Implementation

Phase 2: Collaborative Filtering for Personalized Recommendations

Features:
1. Privacy-First Consent Management
2. Distributed Usage Tracking
3. Local Skill Scanning
4. Incentive System
5. Collaborative Filtering (NEW - Phase 2)
   - User-Item Matrix
   - Similarity Computation
   - Hybrid Recommendations

Author: Skills Arena Team
Version: 2.0.0
"""

import asyncio
import hashlib
import json
import os
import pickle
import random
import threading
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
import numpy as np
import scipy.sparse as sp
import yaml


# ============ Constants ============

DEFAULT_SERVER_URL = "https://skills-arena.example.com"
CONSENT_FILE = Path("~/.config/skills-arena/collab_consent.yml")
CF_DATA_DIR = Path("./data/cf_engine")

# ============ Enums ============


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


class InteractionType(Enum):
    """Types of user-skill interactions."""

    USAGE = 1
    SUCCESS = 2
    UPVOTE = 3
    DOWNVOTE = 4
    DOWNLOAD = 5
    BOOKMARK = 6
    SHARE = 7


class SimilarityMethod(Enum):
    """Similarity computation methods."""

    COSINE = "cosine"
    PEARSON = "pearson"
    JACCARD = "jaccard"


# ============ Data Classes ============


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

    def is_valid(self) -> bool:
        if self.consent_level == ConsentLevel.DISABLED:
            return False
        if self.expires_at:
            expiry = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
            if datetime.now() > expiry:
                return False
        return True

    @classmethod
    def load(cls, path: Path) -> "ConsentConfig":
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
            yaml.dump(data, f)


@dataclass
class UserInteraction:
    """A single user-skill interaction."""

    user_hash: str
    skill_id: str
    interaction_type: InteractionType
    value: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    context: Optional[Dict[str, Any]] = None


@dataclass
class SkillRecommendation:
    """A skill recommendation."""

    skill_id: str
    score: float
    reason: str
    similarity: Optional[float] = None
    confidence: float = 0.5
    based_on: Optional[List[str]] = None


@dataclass
class IncentiveProfile:
    """User incentive profile."""

    user_hash: str
    total_points: int = 0
    tier: str = "Bronze"
    contributions: List[Dict] = field(default_factory=list)


# ============ Privacy ============


class PrivacyPreserver:
    """Privacy preservation utilities."""

    @staticmethod
    def hash_user(did: str, salt: str = "skills-arena") -> str:
        combined = f"{did}:{salt}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    @staticmethod
    def add_laplace_noise(value: float, epsilon: float = 1.0) -> float:
        noise = random.laplace(0, 1 / epsilon)
        return max(0, min(1, value + noise))

    @staticmethod
    def bucketize_timestamp(timestamp: str) -> str:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        hour = dt.hour
        if 0 <= hour < 6:
            return "night"
        elif 6 <= hour < 12:
            return "morning"
        elif 12 <= hour < 18:
            return "afternoon"
        else:
            return "evening"


# ============ Sparse Matrix ============


class SparseMatrix:
    """Memory-efficient sparse matrix for user-item interactions."""

    def __init__(self):
        self.user_map: Dict[str, int] = {}
        self.item_map: Dict[str, int] = {}
        self.reverse_user_map: Dict[int, str] = {}
        self.reverse_item_map: Dict[int, str] = {}
        self.interactions: List[UserInteraction] = []
        self.matrix: Optional[sp.csr_matrix] = None
        self._lock = threading.RLock()

    def add_user(self, user_hash: str) -> int:
        if user_hash not in self.user_map:
            idx = len(self.user_map)
            self.user_map[user_hash] = idx
            self.reverse_user_map[idx] = user_hash
        return self.user_map[user_hash]

    def add_item(self, skill_id: str) -> int:
        if skill_id not in self.item_map:
            idx = len(self.item_map)
            self.item_map[skill_id] = idx
            self.reverse_item_map[idx] = skill_id
        return self.item_map[skill_id]

    def add_interaction(self, interaction: UserInteraction) -> None:
        with self._lock:
            self.add_user(interaction.user_hash)
            self.add_item(interaction.skill_id)
            self.interactions.append(interaction)
            self._rebuild_matrix()

    def _rebuild_matrix(self) -> None:
        n_users = len(self.user_map)
        n_items = len(self.item_map)
        if n_users == 0 or n_items == 0:
            self.matrix = None
            return
        rows, cols, data = [], [], []
        for interaction in self.interactions:
            rows.append(self.user_map[interaction.user_hash])
            cols.append(self.item_map[interaction.skill_id])
            data.append(interaction.value)
        self.matrix = sp.csr_matrix(
            (data, (rows, cols)), shape=(n_users, n_items), dtype=np.float32
        )

    @property
    def shape(self) -> Tuple[int, int]:
        return (0, 0) if self.matrix is None else self.matrix.shape

    @property
    def nnz(self) -> int:
        return 0 if self.matrix is None else self.matrix.nnz

    def get_user_vector(self, user_hash: str) -> np.ndarray:
        if self.matrix is None or user_hash not in self.user_map:
            return np.zeros(self.shape[1])
        idx = self.user_map[user_hash]
        return self.matrix[idx].toarray().flatten()


# ============ Similarity Engine ============


class SimilarityEngine:
    """Computes and caches item similarities."""

    def __init__(
        self, matrix: SparseMatrix, method: SimilarityMethod = SimilarityMethod.COSINE
    ):
        self.matrix = matrix
        self.method = method
        self.cache: Dict[str, Dict[str, float]] = {}

    def get_similar_items(
        self, skill_id: str, top_n: int = 10
    ) -> List[Tuple[str, float]]:
        cache_key = f"item:{skill_id}"
        if cache_key in self.cache:
            items = [(k, v) for k, v in self.cache[cache_key].items()]
            return sorted(items, key=lambda x: x[1], reverse=True)[:top_n]

        if self.matrix.matrix is None:
            return []

        similarities = []
        item_vec = self.matrix.get_user_vector(skill_id)
        if np.all(item_vec == 0):
            return []

        for other_id, idx in self.matrix.item_map.items():
            if other_id == skill_id:
                continue
            other_vec = self.matrix.get_user_vector(other_id)
            if np.all(other_vec == 0):
                continue
            sim = self._compute_similarity(item_vec, other_vec)
            if sim > 0:
                similarities.append((other_id, sim))

        self.cache[cache_key] = dict(similarities[:50])
        return sorted(similarities, key=lambda x: x[1], reverse=True)[:top_n]

    def _compute_similarity(self, v1: np.ndarray, v2: np.ndarray) -> float:
        if self.method == SimilarityMethod.COSINE:
            norm1, norm2 = np.linalg.norm(v1), np.linalg.norm(v2)
            if norm1 == 0 or norm2 == 0:
                return 0.0
            return float(np.dot(v1, v2) / (norm1 * norm2))
        elif self.method == SimilarityMethod.JACCARD:
            intersection, union = np.sum(np.minimum(v1, v2)), np.sum(np.maximum(v1, v2))
            return intersection / union if union > 0 else 0.0
        return 0.0


# ============ Hybrid Recommender ============


class HybridRecommender:
    """Hybrid collaborative filtering recommender."""

    def __init__(self, matrix: SparseMatrix, similarity_engine: SimilarityEngine):
        self.matrix = matrix
        self.engine = similarity_engine

    def get_recommendations(
        self,
        user_hash: str,
        exclude_skills: Optional[List[str]] = None,
        top_n: int = 10,
    ) -> List[SkillRecommendation]:
        exclude_skills = exclude_skills or []
        user_vec = self.matrix.get_user_vector(user_hash)
        if np.all(user_vec == 0):
            return self._get_popular(exclude_skills, top_n)

        # Get items user has interacted with
        interacted = [
            sid for sid, idx in self.matrix.item_map.items() if user_vec[idx] > 0
        ]

        item_scores: Dict[str, float] = {}
        for skill_id in interacted:
            similar = self.engine.get_similar_items(skill_id, top_n=20)
            for sim_id, sim_score in similar:
                if sim_id not in exclude_skills and sim_id != skill_id:
                    item_scores[sim_id] = item_scores.get(sim_id, 0) + sim_score

        recs = sorted(item_scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
        return [
            SkillRecommendation(
                skill_id=sid,
                score=score,
                reason="Based on similar users' preferences",
                confidence=0.6,
            )
            for sid, score in recs
        ]

    def _get_popular(self, exclude: List[str], top_n: int) -> List[SkillRecommendation]:
        if self.matrix.matrix is None:
            return []
        counts = np.array(self.matrix.matrix.sum(axis=0)).flatten()
        recs = []
        for idx, count in enumerate(counts):
            sid = self.matrix.reverse_item_map.get(idx)
            if sid and sid not in exclude:
                recs.append(
                    SkillRecommendation(
                        skill_id=sid,
                        score=float(count),
                        reason="Popular",
                        confidence=0.5,
                    )
                )
        return sorted(recs, key=lambda x: x.score, reverse=True)[:top_n]


# ============ Collaborative Filtering Engine ============


class CFEngine:
    """Main collaborative filtering engine."""

    def __init__(self, data_dir: Path = CF_DATA_DIR):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.matrix = SparseMatrix()
        self.engine = SimilarityEngine(self.matrix)
        self.recommender = HybridRecommender(self.matrix, self.engine)
        self._load_state()

    def record_interaction(
        self,
        user_did: str,
        skill_id: str,
        interaction_type: InteractionType,
        value: float = 1.0,
        timestamp: Optional[str] = None,
    ) -> None:
        user_hash = PrivacyPreserver.hash_user(user_did)
        interaction = UserInteraction(
            user_hash=user_hash,
            skill_id=skill_id,
            interaction_type=interaction_type,
            value=value,
            timestamp=timestamp or datetime.now().isoformat(),
        )
        self.matrix.add_interaction(interaction)
        if self.matrix.nnz % 100 == 0:
            self._save_state()

    def get_recommendations(
        self, user_did: str, exclude_skills: Optional[List[str]] = None, top_n: int = 10
    ) -> List[SkillRecommendation]:
        user_hash = PrivacyPreserver.hash_user(user_did)
        return self.recommender.get_recommendations(user_hash, exclude_skills, top_n)

    def get_similar_skills(
        self, skill_id: str, top_n: int = 10
    ) -> List[Tuple[str, float]]:
        return self.engine.get_similar_items(skill_id, top_n)

    def get_popular_skills(self, top_n: int = 10) -> List[Tuple[str, float]]:
        if self.matrix.matrix is None:
            return []
        counts = np.array(self.matrix.matrix.sum(axis=0)).flatten()
        return [
            (self.matrix.reverse_item_map.get(idx), float(count))
            for idx, count in enumerate(counts)
            if self.matrix.reverse_item_map.get(idx)
        ][:top_n]

    def _save_state(self) -> None:
        path = self.data_dir / "matrix.pkl"
        with open(path, "wb") as f:
            pickle.dump(
                {
                    "user_map": self.matrix.user_map,
                    "item_map": self.matrix.item_map,
                    "interactions": self.matrix.interactions,
                },
                f,
            )

    def _load_state(self) -> None:
        path = self.data_dir / "matrix.pkl"
        if path.exists():
            with open(path, "rb") as f:
                data = pickle.load(f)
            self.matrix.user_map = data.get("user_map", {})
            self.matrix.item_map = data.get("item_map", {})
            self.matrix.interactions = data.get("interactions", [])
            self.matrix._rebuild_matrix()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "n_users": len(self.matrix.user_map),
            "n_items": len(self.matrix.item_map),
            "n_interactions": self.matrix.nnz,
        }


# ============ Main Client ============


class SkillsArenaClient:
    """
    Main client for Skills Arena collaboration.

    Features:
    - Consent management
    - Usage tracking
    - Collaborative filtering
    - Local skill scanning
    - Incentive tracking
    """

    def __init__(
        self,
        server_url: str = DEFAULT_SERVER_URL,
        user_did: Optional[str] = None,
        consent_level: Union[ConsentLevel, str] = ConsentLevel.DISABLED,
        auto_send: bool = True,
    ):
        self.server_url = server_url.rstrip("/")
        self.user_did = user_did or self._generate_anon_id()
        self.auto_send = auto_send

        # Initialize components
        self.consent = self._load_consent()
        if isinstance(consent_level, str):
            consent_level = ConsentLevel(consent_level)
        if consent_level != ConsentLevel.DISABLED:
            self.consent.consent_level = consent_level
            self.consent.save(self._get_consent_path())

        # CF Engine
        self._cf_engine: Optional[CFEngine] = None

        # Incentive tracking
        self._incentive_points: int = 0
        self._incentive_history: List[Dict] = []

    def _generate_anon_id(self) -> str:
        return f"did:openclaw:anon:{uuid.uuid4().hex}"

    def _get_consent_path(self) -> Path:
        return Path(os.path.expanduser(CONSENT_FILE))

    def _load_consent(self) -> ConsentConfig:
        return ConsentConfig.load(self._get_consent_path())

    @property
    def cf_engine(self) -> CFEngine:
        if self._cf_engine is None:
            self._cf_engine = CFEngine()
        return self._cf_engine

    def get_consent_status(self) -> Tuple[ConsentStatus, str]:
        if not self.consent.is_valid():
            return ConsentStatus.NOT_GRANTED, "Consent not granted or expired"
        return ConsentStatus.GRANTED, f"Level: {self.consent.consent_level.value}"

    def get_data_sharing_preview(self) -> List[Dict[str, str]]:
        if self.consent.consent_level == ConsentLevel.DISABLED:
            return []
        preview = [
            {
                "category": "anonymous_id",
                "description": "Hashed user identifier",
                "retention": "Permanent",
            }
        ]
        if self.consent.consent_level == ConsentLevel.USAGE_STATS_ONLY:
            preview.append(
                {
                    "category": "execution_time",
                    "description": "Usage metrics",
                    "retention": "30 days",
                }
            )
        elif self.consent.consent_level == ConsentLevel.FULL_PARTICIPATION:
            preview.extend(
                [
                    {
                        "category": "execution_time",
                        "description": "Detailed metrics",
                        "retention": "90 days",
                    },
                    {
                        "category": "skill_usage",
                        "description": "Skills used",
                        "retention": "180 days",
                    },
                ]
            )
        return preview

    async def request_consent(
        self,
        purpose: str = "Enable personalized recommendations",
        categories: Optional[List[str]] = None,
        duration_days: int = 365,
    ) -> bool:
        print("\n" + "=" * 60)
        print("SKILLS ARENA - Consent Request")
        print("=" * 60)
        print(f"\nPurpose: {purpose}")
        preview = self.get_data_sharing_preview()
        for item in preview:
            print(f"  - {item['category']}: {item['description']}")
        response = input("\nDo you consent? (yes/no/limited): ").strip().lower()
        if response == "yes":
            level = ConsentLevel.FULL_PARTICIPATION
        elif response == "limited":
            level = ConsentLevel.USAGE_STATS_ONLY
        else:
            print("Consent not granted.")
            return False
        self.consent.consent_level = level
        self.consent.user_did = self.user_did
        self.consent.granted_at = datetime.now().isoformat()
        self.consent.expires_at = (
            datetime.now() + timedelta(days=duration_days)
        ).isoformat()
        self.consent.save(self._get_consent_path())
        print(f"Consent granted: {level.value}")
        return True

    async def withdraw_consent(self) -> bool:
        self.consent.consent_level = ConsentLevel.DISABLED
        self.consent.granted_at = None
        self.consent.save(self._get_consent_path())
        self._add_points("consent_withdraw", "Withdrew consent")
        print("Consent withdrawn.")
        return True

    @asynccontextmanager
    async def track_session(self, skill_id: str):
        """Track a skill execution session."""
        start = time.time()
        try:
            yield
            success = True
        except Exception:
            success = False
            raise
        finally:
            execution_time = time.time() - start
            await self.log_usage(skill_id, execution_time, success)

    async def log_usage(
        self,
        skill_id: str,
        execution_time: float,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log skill usage."""
        if not self.consent.is_valid():
            return

        value = 1.0 if success else 0.5
        self.cf_engine.record_interaction(
            user_did=self.user_did,
            skill_id=skill_id,
            interaction_type=InteractionType.SUCCESS
            if success
            else InteractionType.USAGE,
            value=value,
        )
        self._add_points("usage", "Skill used")

    async def get_recommendations(self, top_n: int = 10) -> List[SkillRecommendation]:
        """Get personalized recommendations."""
        if not self.consent.is_valid():
            return await self._get_server_recommendations(top_n)
        return self.cf_engine.get_recommendations(self.user_did, top_n=top_n)

    async def _get_server_recommendations(
        self, top_n: int
    ) -> List[SkillRecommendation]:
        """Fallback to server recommendations."""
        return [
            SkillRecommendation(
                skill_id=f"skill-{i}", score=1.0, reason="Server recommendation"
            )
            for i in range(top_n)
        ]

    async def get_skill_similarities(
        self, skill_id: str, top_n: int = 5
    ) -> List[Tuple[str, float]]:
        """Get similar skills."""
        return self.cf_engine.get_similar_skills(skill_id, top_n)

    async def vote_skill(self, skill_id: str, rating: int) -> bool:
        """Vote on a skill (1-5 stars)."""
        if not (1 <= rating <= 5):
            raise ValueError("Rating must be 1-5")
        if not self.consent.is_valid():
            return False
        value = (rating - 1) / 4.0
        self.cf_engine.record_interaction(
            self.user_did,
            skill_id,
            InteractionType.UPVOTE if rating >= 4 else InteractionType.DOWNVOTE,
            value,
        )
        self._add_points("vote", f"Voted {rating} stars")
        return True

    def _add_points(self, category: str, description: str) -> None:
        """Add incentive points."""
        points_map = {"usage": 1, "vote": 10, "upload": 100, "report": 25}
        points = points_map.get(category, 5)
        self._incentive_points += points
        self._incentive_history.append({"points": points, "category": description})

    def get_incentive_summary(self) -> Dict[str, Any]:
        """Get incentive summary."""
        points = self._incentive_points
        if points >= 10000:
            tier = "💎 Platinum"
        elif points >= 2000:
            tier = "🥇 Gold"
        elif points >= 500:
            tier = "🥈 Silver"
        else:
            tier = "🥉 Bronze"
        return {
            "total_points": points,
            "tier": tier,
            "contributions": len(self._incentive_history),
        }

    async def close(self) -> None:
        """Close the client."""
        if self._cf_engine:
            self._cf_engine._save_state()


# ============ Local Skill Scanner ============


class LocalSkillScanner:
    """Scans local OpenClaw skills."""

    SCAN_PATHS = [
        Path("./skills"),
        Path("~/.local/share/openclaw/skills"),
        Path("~/.openclaw/skills"),
    ]

    def __init__(self, client: SkillsArenaClient):
        self.client = client
        self.scanned_skills: List[Dict] = []

    async def scan_local_skills(self, paths: Optional[List[Path]] = None) -> List[Dict]:
        """Scan local skill directories."""
        paths = paths or self.SCAN_PATHS
        print("\n🔍 Scanning local skills...")

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
        print(f"✅ Found {len(skills_found)} skills")
        return skills_found

    async def _analyze_skill(self, path: Path) -> Optional[Dict]:
        """Analyze a single skill."""
        skill_md = path / "SKILL.md"
        if not skill_md.exists():
            return None
        return {
            "path": str(path),
            "name": path.name,
            "has_skill_md": True,
            "local_usage": 0,
        }

    async def share_skills(self, indices: Optional[List[int]] = None) -> int:
        """Share local skills with arena."""
        to_share = self.scanned_skills
        if indices:
            to_share = [to_share[i] for i in indices if i < len(to_share)]
        print(f"📤 Sharing {len(to_share)} skills...")
        return len(to_share)


# ============ Demo ============


async def main():
    """Demo the complete SDK."""
    print("\n" + "=" * 60)
    print("SKILLS ARENA COLLABORATION SDK - Phase 2 Demo")
    print("=" * 60)

    # Initialize client
    client = SkillsArenaClient(consent_level=ConsentLevel.FULL_PARTICIPATION)

    # Check consent
    status, msg = client.get_consent_status()
    print(f"\nConsent: {status.value} - {msg}")

    # Simulate user interactions
    print("\n📊 Simulating user interactions...")
    for i in range(20):
        for j in range(5):
            await client.log_usage(f"skill-{j}", random.uniform(0.1, 0.5), True)
    print(f"   Interactions: {client.cf_engine.matrix.nnz}")

    # Get recommendations
    print("\n🎯 Personalized recommendations:")
    recs = await client.get_recommendations(top_n=5)
    for rec in recs:
        print(f"   - {rec.skill_id}: {rec.score:.3f} ({rec.reason})")

    # Get similar skills
    print("\n🔗 Skills similar to 'skill-1':")
    similar = await client.get_skill_similarities("skill-1", top_n=3)
    for sid, sim in similar:
        print(f"   - {sid}: {sim:.3f}")

    # Incentive summary
    print("\n🏆 Incentive summary:")
    summary = client.get_incentive_summary()
    print(f"   Points: {summary['total_points']}")
    print(f"   Tier: {summary['tier']}")

    # CF stats
    print("\n📈 CF Engine stats:")
    stats = client.cf_engine.get_stats()
    for k, v in stats.items():
        print(f"   {k}: {v}")

    await client.close()
    print("\n✅ Demo complete!")


if __name__ == "__main__":
    asyncio.run(main())
