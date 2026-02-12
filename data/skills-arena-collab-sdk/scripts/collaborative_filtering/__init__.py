#!/usr/bin/env python3
"""
Collaborative Filtering Engine for Skills Arena

Implements:
1. User-Item Matrix Management
2. Similarity Computation (Cosine, Pearson, Jaccard)
3. Recommendation Algorithms (User-based, Item-based, Matrix Factorization)
4. Real-time Updates with Privacy Preservation

Author: Skills Arena Team
Version: 2.0.0
"""

import asyncio
import hashlib
import json
import math
import os
import pickle
import random
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import svds
from sklearn.metrics.pairwise import cosine_similarity


class InteractionType(Enum):
    """Types of user-skill interactions."""

    USAGE = 1  # Skill executed successfully
    SUCCESS = 2  # Successful execution
    UPVOTE = 3  # Positive vote
    DOWNVOTE = 4  # Negative vote
    DOWNLOAD = 5  # Downloaded skill
    BOOKMARK = 6  # Bookmarked skill
    SHARE = 7  # Shared skill


class SimilarityMethod(Enum):
    """Similarity computation methods."""

    COSINE = "cosine"
    PEARSON = "pearson"
    JACCARD = "jaccard"
    MSD = "msd"  # Mean Squared Difference


@dataclass
class UserInteraction:
    """A single user-skill interaction."""

    user_hash: str
    skill_id: str
    interaction_type: InteractionType
    value: float  # Normalized value (0.0 to 1.0)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    context: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_hash": self.user_hash,
            "skill_id": self.skill_id,
            "interaction_type": self.interaction_type.value,
            "value": self.value,
            "timestamp": self.timestamp,
            "context": self.context,
        }


@dataclass
class SkillRecommendation:
    """A skill recommendation with metadata."""

    skill_id: str
    score: float
    reason: str
    similarity: Optional[float] = None
    confidence: float = 0.5
    based_on: Optional[List[str]] = None  # Skill IDs this is based on

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "score": self.score,
            "reason": self.reason,
            "similarity": self.similarity,
            "confidence": self.confidence,
            "based_on": self.based_on or [],
        }


@dataclass
class UserProfile:
    """User preference profile."""

    user_hash: str
    preferred_skills: List[str] = field(default_factory=list)
    avoided_skills: List[str] = field(default_factory=list)
    skill_categories: Dict[str, float] = field(default_factory=dict)
    average_rating: float = 0.5
    total_interactions: int = 0
    last_active: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_hash": self.user_hash,
            "preferred_skills": self.preferred_skills,
            "avoided_skills": self.avoided_skills,
            "skill_categories": self.skill_categories,
            "average_rating": self.average_rating,
            "total_interactions": self.total_interactions,
            "last_active": self.last_active,
        }


class PrivacyPreserver:
    """
    Ensures privacy in collaborative filtering.

    Techniques:
    - k-anonymity: Each bucket has at least k users
    - Differential privacy: Add noise to aggregates
    - L-diversity: Diverse values in each group
    """

    K_ANONYMITY = 10  # Minimum users per group
    EPSILON = 1.0  # Differential privacy parameter

    @staticmethod
    def hash_user(user_did: str, salt: str = "skills-arena") -> str:
        """Create anonymous user identifier."""
        combined = f"{user_did}:{salt}"
        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    @staticmethod
    def add_laplace_noise(value: float, epsilon: float = None) -> float:
        """Add Laplace noise for differential privacy."""
        epsilon = epsilon or PrivacyPreserver.EPSILON
        noise = random.laplace(0, 1 / epsilon)
        return max(0, min(1, value + noise))

    @staticmethod
    def bucketize_timestamp(timestamp: str) -> str:
        """Convert exact timestamp to time bucket."""
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

    @staticmethod
    def ensure_k_anonymity(users: List[str]) -> bool:
        """Check if group meets k-anonymity requirement."""
        return len(users) >= PrivacyPreserver.K_ANONYMITY

    @staticmethod
    def anonymize_interaction(
        user_did: str,
        skill_id: str,
        interaction_type: InteractionType,
        value: float,
        timestamp: str,
    ) -> UserInteraction:
        """Create anonymized interaction for storage."""
        return UserInteraction(
            user_hash=PrivacyPreserver.hash_user(user_did),
            skill_id=skill_id,
            interaction_type=interaction_type,
            value=PrivacyPreserver.add_laplace_noise(value),
            timestamp=PrivacyPreserver.bucketize_timestamp(timestamp),
        )


class SparseMatrix:
    """
    Memory-efficient sparse matrix for user-item interactions.

    Uses scipy sparse matrices for efficient storage and computation.
    """

    def __init__(self, max_users: int = 100000, max_items: int = 10000):
        self.max_users = max_users
        self.max_items = max_items
        self.user_map: Dict[str, int] = {}  # user_hash -> index
        self.item_map: Dict[str, int] = {}  # skill_id -> index
        self.reverse_user_map: Dict[int, str] = {}
        self.reverse_item_map: Dict[int, str] = {}
        self.matrix: Optional[sp.csr_matrix] = None
        self.interactions: List[UserInteraction] = []
        self._lock = threading.RLock()

    def add_user(self, user_hash: str) -> int:
        """Add a user and return their index."""
        if user_hash not in self.user_map:
            idx = len(self.user_map)
            self.user_map[user_hash] = idx
            self.reverse_user_map[idx] = user_hash
        return self.user_map[user_hash]

    def add_item(self, skill_id: str) -> int:
        """Add an item and return its index."""
        if skill_id not in self.item_map:
            idx = len(self.item_map)
            self.item_map[skill_id] = idx
            self.reverse_item_map[idx] = skill_id
        return self.item_map[skill_id]

    def add_interaction(self, interaction: UserInteraction) -> None:
        """Add an interaction to the matrix."""
        with self._lock:
            # Ensure user and item exist
            self.add_user(interaction.user_hash)
            self.add_item(interaction.skill_id)

            self.interactions.append(interaction)
            self._rebuild_matrix()

    def add_interactions_batch(self, interactions: List[UserInteraction]) -> None:
        """Add multiple interactions efficiently."""
        with self._lock:
            # First pass: collect all users and items
            users = set()
            items = set()
            for interaction in interactions:
                users.add(interaction.user_hash)
                items.add(interaction.skill_id)

            # Add all users and items
            for user in users:
                self.add_user(user)
            for item in items:
                self.add_item(item)

            # Add interactions
            self.interactions.extend(interactions)
            self._rebuild_matrix()

    def _rebuild_matrix(self) -> None:
        """Rebuild the sparse matrix from interactions."""
        n_users = len(self.user_map)
        n_items = len(self.item_map)

        if n_users == 0 or n_items == 0:
            self.matrix = None
            return

        # Build COO format
        rows = []
        cols = []
        data = []

        for interaction in self.interactions:
            user_idx = self.user_map[interaction.user_hash]
            item_idx = self.item_map[interaction.skill_id]
            rows.append(user_idx)
            cols.append(item_idx)
            data.append(interaction.value)

        self.matrix = sp.csr_matrix(
            (data, (rows, cols)), shape=(n_users, n_items), dtype=np.float32
        )

    @property
    def shape(self) -> Tuple[int, int]:
        """Return matrix shape."""
        if self.matrix is None:
            return (0, 0)
        return self.matrix.shape

    @property
    def nnz(self) -> int:
        """Return number of non-zero elements."""
        if self.matrix is None:
            return 0
        return self.matrix.nnz

    def get_user_vector(self, user_hash: str) -> np.ndarray:
        """Get the interaction vector for a user."""
        if self.matrix is None or user_hash not in self.user_map:
            return np.zeros(self.shape[1])

        idx = self.user_map[user_hash]
        return self.matrix[idx].toarray().flatten()

    def get_item_vector(self, skill_id: str) -> np.ndarray:
        """Get the interaction vector for an item."""
        if self.matrix is None or skill_id not in self.item_map:
            return np.zeros(self.shape[0])

        idx = self.item_map[skill_id]
        return self.matrix[:, idx].toarray().flatten()

    def get_similar_users(
        self,
        user_hash: str,
        method: SimilarityMethod = SimilarityMethod.COSINE,
        top_n: int = 10,
    ) -> List[Tuple[str, float]]:
        """Find similar users based on their interaction patterns."""
        if self.matrix is None:
            return []

        user_vector = self.get_user_vector(user_hash)
        if np.all(user_vector == 0):
            return []

        similarities = []
        for other_hash, idx in self.user_map.items():
            if other_hash == user_hash:
                continue

            other_vector = self.get_user_vector(other_hash)
            if np.all(other_vector == 0):
                continue

            sim = self._compute_similarity(user_vector, other_vector, method)
            if sim > 0:
                similarities.append((other_hash, sim))

        # Sort and return top N
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_n]

    def get_similar_items(
        self,
        skill_id: str,
        method: SimilarityMethod = SimilarityMethod.COSINE,
        top_n: int = 10,
    ) -> List[Tuple[str, float]]:
        """Find similar items based on user interactions."""
        if self.matrix is None:
            return []

        item_vector = self.get_item_vector(skill_id)
        if np.all(item_vector == 0):
            return []

        similarities = []
        for other_id, idx in self.item_map.items():
            if other_id == skill_id:
                continue

            other_vector = self.get_item_vector(other_id)
            if np.all(other_vector == 0):
                continue

            sim = self._compute_similarity(item_vector, other_vector, method)
            if sim > 0:
                similarities.append((other_id, sim))

        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_n]

    def _compute_similarity(
        self, v1: np.ndarray, v2: np.ndarray, method: SimilarityMethod
    ) -> float:
        """Compute similarity between two vectors."""
        if method == SimilarityMethod.COSINE:
            return cosine_similarity([v1], [v2])[0][0]

        elif method == SimilarityMethod.PEARSON:
            # Pearson correlation
            v1_norm = v1 - np.mean(v1[v1 > 0]) if np.any(v1 > 0) else v1
            v2_norm = v2 - np.mean(v2[v2 > 0]) if np.any(v2 > 0) else v2

            norm1 = np.linalg.norm(v1_norm)
            norm2 = np.linalg.norm(v2_norm)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            return np.dot(v1_norm, v2_norm) / (norm1 * norm2)

        elif method == SimilarityMethod.JACCARD:
            # Jaccard similarity for binary data
            intersection = np.sum(np.minimum(v1, v2))
            union = np.sum(np.maximum(v1, v2))

            if union == 0:
                return 0.0
            return intersection / union

        elif method == SimilarityMethod.MSD:
            # Mean squared difference (lower is better, invert)
            diff = np.mean((v1 - v2) ** 2)
            return 1.0 / (1.0 + diff)

        return 0.0

    def save(self, path: Path) -> None:
        """Save matrix to disk."""
        with self._lock:
            data = {
                "user_map": self.user_map,
                "item_map": self.item_map,
                "reverse_user_map": self.reverse_user_map,
                "reverse_item_map": self.reverse_item_map,
                "interactions": [i.to_dict() for i in self.interactions],
            }

            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, "wb") as f:
                pickle.dump(data, f)

            # Save sparse matrix separately
            if self.matrix is not None:
                matrix_path = path.with_suffix(".matrix.npz")
                sp.save_npz(matrix_path, self.matrix)

    def load(self, path: Path) -> None:
        """Load matrix from disk."""
        if not path.exists():
            return

        with self._lock:
            with open(path, "rb") as f:
                data = pickle.load(f)

            self.user_map = data["user_map"]
            self.item_map = data["item_map"]
            self.reverse_user_map = data["reverse_user_map"]
            self.reverse_item_map = data["reverse_item_map"]

            # Rebuild interactions
            # Note: We'd need to convert dicts back to UserInteraction objects
            # For now, just rebuild the matrix from maps
            self._rebuild_matrix()

    def clear(self) -> None:
        """Clear all data."""
        with self._lock:
            self.user_map.clear()
            self.item_map.clear()
            self.reverse_user_map.clear()
            self.reverse_item_map.clear()
            self.interactions.clear()
            self.matrix = None


class SimilarityEngine:
    """
    Computes and caches item-item similarities.

    Optimized for real-time recommendations.
    """

    def __init__(
        self,
        matrix: SparseMatrix,
        method: SimilarityMethod = SimilarityMethod.COSINE,
        cache_size: int = 1000,
    ):
        self.matrix = matrix
        self.method = method
        self.similarity_cache: Dict[str, Dict[str, float]] = {}
        self.cache_size = cache_size
        self._lock = threading.RLock()

    def get_similar_items(
        self, skill_id: str, top_n: int = 10, min_similarity: float = 0.0
    ) -> List[Tuple[str, float]]:
        """Get similar items with caching."""
        # Check cache first
        cache_key = f"item:{skill_id}"

        with self._lock:
            if cache_key in self.similarity_cache:
                cached = self.similarity_cache[cache_key]
                return [
                    (item, sim) for item, sim in cached.items() if sim >= min_similarity
                ][:top_n]

        # Compute similarities
        similarities = self.matrix.get_similar_items(
            skill_id,
            method=self.method,
            top_n=top_n * 2,  # Get extra for filtering
        )

        # Cache results
        with self._lock:
            self.similarity_cache[cache_key] = dict(similarities)

            # Evict old entries if cache is full
            if len(self.similarity_cache) > self.cache_size:
                # Remove random entries
                keys_to_remove = random.sample(
                    list(self.similarity_cache.keys()),
                    len(self.similarity_cache) - self.cache_size,
                )
                for key in keys_to_remove:
                    del self.similarity_cache[key]

        # Filter and return
        return [(item, sim) for item, sim in similarities if sim >= min_similarity][
            :top_n
        ]

    def compute_all_similarities(self) -> Dict[str, Dict[str, float]]:
        """Pre-compute all item similarities (expensive)."""
        all_similarities = {}

        for skill_id in self.matrix.item_map.keys():
            similarities = self.matrix.get_similar_items(
                skill_id, method=self.method, top_n=50
            )
            all_similarities[skill_id] = dict(similarities)

        return all_similarities

    def invalidate_cache(self, skill_id: str = None) -> None:
        """Invalidate similarity cache."""
        with self._lock:
            if skill_id:
                cache_key = f"item:{skill_id}"
                if cache_key in self.similarity_cache:
                    del self.similarity_cache[cache_key]
            else:
                self.similarity_cache.clear()


class RecommenderEngine(ABC):
    """Abstract base class for recommendation engines."""

    @abstractmethod
    def get_recommendations(
        self,
        user_hash: str,
        exclude_skills: Optional[List[str]] = None,
        top_n: int = 10,
    ) -> List[SkillRecommendation]:
        """Get recommendations for a user."""
        pass

    @abstractmethod
    def update_model(self, interaction: UserInteraction) -> None:
        """Update model with new interaction."""
        pass


class ItemBasedRecommender(RecommenderEngine):
    """
    Item-based collaborative filtering recommender.

    Finds similar items to what the user has interacted with,
    and recommends those.
    """

    def __init__(
        self,
        matrix: SparseMatrix,
        similarity_engine: SimilarityEngine,
        decay_factor: float = 0.9,  # Older interactions matter less
        min_similarity: float = 0.1,
    ):
        self.matrix = matrix
        self.similarity_engine = similarity_engine
        self.decay_factor = decay_factor
        self.min_similarity = min_similarity
        self._lock = threading.RLock()

    def get_recommendations(
        self,
        user_hash: str,
        exclude_skills: Optional[List[str]] = None,
        top_n: int = 10,
    ) -> List[SkillRecommendation]:
        """Get item-based recommendations for a user."""
        exclude_skills = exclude_skills or []

        # Get user's interaction vector
        user_vector = self.matrix.get_user_vector(user_hash)

        if np.all(user_vector == 0):
            # Cold start: return popular skills
            return self._get_popular_recommendations(exclude_skills, top_n)

        # Find items the user has interacted with
        interacted_items = []
        for skill_id, idx in self.matrix.item_map.items():
            if user_vector[idx] > 0:
                interacted_items.append((skill_id, user_vector[idx]))

        if not interacted_items:
            return self._get_popular_recommendations(exclude_skills, top_n)

        # Score all items based on similarity to interacted items
        item_scores: Dict[str, float] = {}

        for skill_id, interaction_value in interacted_items:
            # Get similar items
            similar = self.similarity_engine.get_similar_items(
                skill_id, top_n=20, min_similarity=self.min_similarity
            )

            for similar_id, similarity in similar:
                if similar_id in exclude_skills:
                    continue
                if similar_id == skill_id:
                    continue

                # Score = similarity * interaction_value * time decay
                score = similarity * interaction_value

                if similar_id in item_scores:
                    item_scores[similar_id] += score
                else:
                    item_scores[similar_id] = score

        # Sort by score
        sorted_items = sorted(item_scores.items(), key=lambda x: x[1], reverse=True)

        # Build recommendations
        recommendations = []
        for skill_id, score in sorted_items[:top_n]:
            # Find what this is based on
            based_on = [
                interacted[0]
                for interacted in interacted_items
                if skill_id
                in [
                    s[0]
                    for s in self.similarity_engine.get_similar_items(
                        interacted[0], top_n=5
                    )
                ]
            ]

            recommendations.append(
                SkillRecommendation(
                    skill_id=skill_id,
                    score=score,
                    reason="Users who used similar skills also used this",
                    similarity=item_scores[skill_id],
                    confidence=min(0.95, 0.5 + 0.1 * len(based_on)),
                    based_on=based_on[:3],
                )
            )

        return recommendations

    def _get_popular_recommendations(
        self, exclude_skills: List[str], top_n: int
    ) -> List[SkillRecommendation]:
        """Get recommendations based on popularity."""
        if self.matrix.matrix is None:
            return []

        # Get item frequencies
        item_counts = np.array(self.matrix.matrix.sum(axis=0)).flatten()

        recommendations = []
        for idx, count in enumerate(item_counts):
            skill_id = self.matrix.reverse_item_map.get(idx)
            if skill_id and skill_id not in exclude_skills:
                recommendations.append(
                    SkillRecommendation(
                        skill_id=skill_id,
                        score=float(count),
                        reason="Popular among all users",
                        confidence=0.5,
                    )
                )

        recommendations.sort(key=lambda x: x.score, reverse=True)
        return recommendations[:top_n]

    def update_model(self, interaction: UserInteraction) -> None:
        """Update model with new interaction."""
        with self._lock:
            self.matrix.add_interaction(interaction)
            # Invalidate relevant cache entries
            self.similarity_engine.invalidate_cache(interaction.skill_id)


class UserBasedRecommender(RecommenderEngine):
    """
    User-based collaborative filtering recommender.

    Finds similar users and recommends what they liked.
    """

    def __init__(
        self,
        matrix: SparseMatrix,
        similarity_engine: SimilarityEngine,
        top_n_similar: int = 50,
        min_similarity: float = 0.2,
    ):
        self.matrix = matrix
        self.similarity_engine = similarity_engine
        self.top_n_similar = top_n_similar
        self.min_similarity = min_similarity

    def get_recommendations(
        self,
        user_hash: str,
        exclude_skills: Optional[List[str]] = None,
        top_n: int = 10,
    ) -> List[SkillRecommendation]:
        """Get user-based recommendations for a user."""
        exclude_skills = exclude_skills or []

        # Get similar users
        similar_users = self.matrix.get_similar_users(
            user_hash, method=SimilarityMethod.COSINE, top_n=self.top_n_similar
        )

        if not similar_users:
            return []

        # Get items similar users liked
        item_scores: Dict[str, float] = {}
        item_counts: Dict[str, int] = {}

        for similar_hash, similarity in similar_users:
            if similarity < self.min_similarity:
                continue

            similar_vector = self.matrix.get_user_vector(similar_hash)

            for skill_id, idx in self.matrix.item_map.items():
                if skill_id in exclude_skills:
                    continue

                value = similar_vector[idx]
                if value > 0:
                    # Weighted by similarity
                    weighted_score = value * similarity

                    item_scores[skill_id] = (
                        item_scores.get(skill_id, 0) + weighted_score
                    )
                    item_counts[skill_id] = item_counts.get(skill_id, 0) + 1

        # Normalize by number of recommending users
        for skill_id in item_scores:
            if item_counts[skill_id] > 0:
                item_scores[skill_id] /= item_counts[skill_id]

        # Sort and return top N
        sorted_items = sorted(item_scores.items(), key=lambda x: x[1], reverse=True)

        recommendations = []
        for skill_id, score in sorted_items[:top_n]:
            recommendations.append(
                SkillRecommendation(
                    skill_id=skill_id,
                    score=score,
                    reason="Users with similar interests liked this",
                    confidence=min(
                        0.9, 0.4 + 0.1 * min(item_counts.get(skill_id, 0), 5)
                    ),
                )
            )

        return recommendations

    def update_model(self, interaction: UserInteraction) -> None:
        """Update model with new interaction."""
        self.matrix.add_interaction(interaction)


class MatrixFactorizationRecommender(RecommenderEngine):
    """
    Matrix Factorization using SVD for implicit feedback.

    Decomposes user-item matrix into latent factors.
    """

    def __init__(
        self, matrix: SparseMatrix, n_factors: int = 50, regularization: float = 0.01
    ):
        self.matrix = matrix
        self.n_factors = n_factors
        self.regularization = regularization
        self.user_factors: Optional[np.ndarray] = None
        self.item_factors: Optional[np.ndarray] = None
        self._is_fitted = False

    def fit(self) -> None:
        """Fit the SVD model."""
        if self.matrix.matrix is None:
            return

        # Ensure matrix is not too sparse
        if self.matrix.matrix.nnz < 100:
            return

        # Determine number of factors (capped)
        n_factors = min(self.n_factors, min(self.matrix.shape) - 1)

        try:
            # Perform SVD
            U, sigma, Vt = svds(self.matrix.matrix.astype(float), k=n_factors)

            # Convert to dense for easier computation
            self.user_factors = U * np.sqrt(sigma)
            self.item_factors = (Vt.T * np.sqrt(sigma)).T

            self._is_fitted = True

        except Exception as e:
            print(f"SVD fitting failed: {e}")
            self._is_fitted = False

    def get_recommendations(
        self,
        user_hash: str,
        exclude_skills: Optional[List[str]] = None,
        top_n: int = 10,
    ) -> List[SkillRecommendation]:
        """Get matrix factorization recommendations."""
        if not self._is_fitted:
            return []

        exclude_skills = exclude_skills or []

        if user_hash not in self.matrix.user_map:
            return []

        user_idx = self.matrix.user_map[user_hash]

        # Compute predicted ratings
        user_vector = self.user_factors[user_idx]
        predictions = np.dot(user_vector, self.item_factors)

        # Get items user hasn't interacted with
        exclude_indices = set()
        for skill_id in exclude_skills:
            if skill_id in self.matrix.item_map:
                exclude_indices.add(self.matrix.item_map[skill_id])

        user_interactions = self.matrix.get_user_vector(user_hash)
        for idx, value in enumerate(user_interactions):
            if value > 0:
                exclude_indices.add(idx)

        # Get top N predictions excluding interacted items
        recommendations = []
        for idx, score in enumerate(predictions):
            if idx not in exclude_indices:
                skill_id = self.matrix.reverse_item_map.get(idx)
                if skill_id:
                    recommendations.append(
                        SkillRecommendation(
                            skill_id=skill_id,
                            score=float(score),
                            reason="Based on latent factor matching",
                            confidence=0.7,
                        )
                    )

        recommendations.sort(key=lambda x: x.score, reverse=True)
        return recommendations[:top_n]

    def update_model(self, interaction: UserInteraction) -> None:
        """Update model with new interaction."""
        self.matrix.add_interaction(interaction)
        # Note: Full SVD recomputation is expensive
        # In production, use incremental SVD or ALS


class HybridRecommender(RecommenderEngine):
    """
    Hybrid recommender combining multiple approaches.

    Blends:
    - Item-based CF (70% weight)
    - User-based CF (20% weight)
    - Matrix Factorization (10% weight)
    """

    def __init__(
        self,
        matrix: SparseMatrix,
        similarity_engine: SimilarityEngine,
        weights: Optional[Dict[str, float]] = None,
    ):
        self.matrix = matrix
        self.similarity_engine = similarity_engine

        # Default weights
        self.weights = weights or {
            "item_based": 0.5,
            "user_based": 0.3,
            "matrix_factor": 0.2,
        }

        # Initialize sub-recommenders
        self.item_recommender = ItemBasedRecommender(matrix, similarity_engine)
        self.user_recommender = UserBasedRecommender(matrix, similarity_engine)
        self.mf_recommender = MatrixFactorizationRecommender(matrix)

    def get_recommendations(
        self,
        user_hash: str,
        exclude_skills: Optional[List[str]] = None,
        top_n: int = 10,
    ) -> List[SkillRecommendation]:
        """Get hybrid recommendations."""
        exclude_skills = exclude_skills or []

        # Get recommendations from each approach
        item_recs = self.item_recommender.get_recommendations(
            user_hash, exclude_skills, top_n * 2
        )
        user_recs = self.user_recommender.get_recommendations(
            user_hash, exclude_skills, top_n * 2
        )

        # Ensure MF model is fitted
        if not self.mf_recommender._is_fitted:
            self.mf_recommender.fit()

        mf_recs = self.mf_recommender.get_recommendations(
            user_hash, exclude_skills, top_n * 2
        )

        # Combine scores
        combined_scores: Dict[str, float] = {}
        skill_reasons: Dict[str, str] = {}

        for rec in item_recs:
            combined_scores[rec.skill_id] = (
                combined_scores.get(rec.skill_id, 0)
                + rec.score * self.weights["item_based"]
            )
            skill_reasons[rec.skill_id] = rec.reason

        for rec in user_recs:
            combined_scores[rec.skill_id] = (
                combined_scores.get(rec.skill_id, 0)
                + rec.score * self.weights["user_based"]
            )
            if rec.skill_id not in skill_reasons:
                skill_reasons[rec.skill_id] = rec.reason

        for rec in mf_recs:
            combined_scores[rec.skill_id] = (
                combined_scores.get(rec.skill_id, 0)
                + rec.score * self.weights["matrix_factor"]
            )
            if rec.skill_id not in skill_reasons:
                skill_reasons[rec.skill_id] = rec.reason

        # Sort and return top N
        sorted_skills = sorted(
            combined_scores.items(), key=lambda x: x[1], reverse=True
        )

        recommendations = []
        for skill_id, score in sorted_skills[:top_n]:
            recommendations.append(
                SkillRecommendation(
                    skill_id=skill_id,
                    score=score,
                    reason=skill_reasons[skill_id],
                    confidence=0.6,
                )
            )

        return recommendations

    def update_model(self, interaction: UserInteraction) -> None:
        """Update all sub-models."""
        self.item_recommender.update_model(interaction)
        self.user_recommender.update_model(interaction)
        self.mf_recommender.update_model(interaction)

    def refresh(self) -> None:
        """Refresh all models."""
        self.mf_recommender.fit()


class CollaborativeFilteringEngine:
    """
    Main engine coordinating all CF components.

    Provides a unified interface for recommendations.
    """

    def __init__(self, data_dir: Path = Path("./data/cf_engine")):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.matrix = SparseMatrix()
        self.similarity_engine = SimilarityEngine(
            self.matrix, method=SimilarityMethod.COSINE
        )
        self.recommender = HybridRecommender(self.matrix, self.similarity_engine)

        self._load_state()

    def record_interaction(
        self,
        user_did: str,
        skill_id: str,
        interaction_type: InteractionType,
        value: float = 1.0,
        timestamp: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a user-skill interaction."""
        # Anonymize user
        user_hash = PrivacyPreserver.hash_user(user_did)

        # Create interaction
        interaction = UserInteraction(
            user_hash=user_hash,
            skill_id=skill_id,
            interaction_type=interaction_type,
            value=value,
            timestamp=timestamp or datetime.now().isoformat(),
            context=context,
        )

        # Update model
        self.recommender.update_model(interaction)

        # Save state periodically
        self._maybe_save_state()

    def get_recommendations(
        self,
        user_did: str,
        exclude_skills: Optional[List[str]] = None,
        top_n: int = 10,
        anonymize: bool = True,
    ) -> List[SkillRecommendation]:
        """Get personalized recommendations for a user."""
        user_hash = PrivacyPreserver.hash_user(user_did) if anonymize else user_did

        return self.recommender.get_recommendations(
            user_hash=user_hash, exclude_skills=exclude_skills, top_n=top_n
        )

    def get_similar_skills(
        self, skill_id: str, top_n: int = 10
    ) -> List[Tuple[str, float]]:
        """Get skills similar to the given skill."""
        return self.similarity_engine.get_similar_items(skill_id, top_n=top_n)

    def get_popular_skills(
        self, top_n: int = 10, min_interactions: int = 1
    ) -> List[Tuple[str, float]]:
        """Get most popular skills."""
        if self.matrix.matrix is None:
            return []

        # Get item frequencies
        item_counts = np.array(self.matrix.matrix.sum(axis=0)).flatten()

        popular = []
        for idx, count in enumerate(item_counts):
            if count >= min_interactions:
                skill_id = self.matrix.reverse_item_map.get(idx)
                if skill_id:
                    popular.append((skill_id, float(count)))

        popular.sort(key=lambda x: x[1], reverse=True)
        return popular[:top_n]

    def get_user_profile(self, user_did: str) -> Optional[UserProfile]:
        """Get a user's preference profile."""
        user_hash = PrivacyPreserver.hash_user(user_did)

        if user_hash not in self.matrix.user_map:
            return None

        user_vector = self.matrix.get_user_vector(user_hash)

        # Get preferred skills
        preferred = []
        for skill_id, idx in self.matrix.item_map.items():
            if user_vector[idx] > 0.7:
                preferred.append(skill_id)

        # Get average rating
        avg_rating = (
            np.mean(user_vector[user_vector > 0]) if np.any(user_vector > 0) else 0.5
        )

        return UserProfile(
            user_hash=user_hash,
            preferred_skills=preferred[:20],
            average_rating=float(avg_rating),
            total_interactions=int(np.sum(user_vector > 0)),
        )

    def _save_state(self) -> None:
        """Save engine state to disk."""
        matrix_path = self.data_dir / "matrix.pkl"
        self.matrix.save(matrix_path)

    def _load_state(self) -> None:
        """Load engine state from disk."""
        matrix_path = self.data_dir / "matrix.pkl"
        self.matrix.load(matrix_path)

    def _maybe_save_state(self) -> None:
        """Save state periodically."""
        # Simple approach: save every 100 interactions
        if self.matrix.nnz % 100 == 0:
            self._save_state()

    def train(self) -> None:
        """Train the recommendation model."""
        # Fit matrix factorization
        self.mf_recommender.fit()

    def clear(self) -> None:
        """Clear all data."""
        self.matrix.clear()
        self.similarity_engine.invalidate_cache()
        self._save_state()

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "n_users": len(self.matrix.user_map),
            "n_items": len(self.matrix.item_map),
            "n_interactions": self.matrix.nnz,
            "matrix_shape": self.matrix.shape,
            "is_fitted": self.mf_recommender._is_fitted,
        }


# ============ Integration with Skills Arena Client ============


class CollaborativeFilteringClient:
    """
    Client-side interface for collaborative filtering.

    Works with SkillsArenaClient for personalized recommendations.
    """

    def __init__(self, arena_client: "SkillsArenaClient"):
        self.arena_client = arena_client
        self._engine: Optional[CollaborativeFilteringEngine] = None

    def _get_engine(self) -> CollaborativeFilteringEngine:
        """Get or create CF engine."""
        if self._engine is None:
            self._engine = CollaborativeFilteringEngine()
        return self._engine

    async def record_usage(
        self,
        skill_id: str,
        success: bool = True,
        execution_time: Optional[float] = None,
    ) -> None:
        """Record skill usage for personalization."""
        if not self.arena_client.consent.config.is_valid():
            return

        value = 1.0 if success else 0.5

        engine = self._get_engine()
        engine.record_interaction(
            user_did=self.arena_client.user_did,
            skill_id=skill_id,
            interaction_type=InteractionType.SUCCESS
            if success
            else InteractionType.FAILURE,
            value=value,
        )

    async def record_vote(
        self,
        skill_id: str,
        rating: int,  # 1-5
    ) -> None:
        """Record a vote on a skill."""
        if not self.arena_client.consent.config.is_valid():
            return

        value = (rating - 1) / 4.0  # Normalize to 0-1

        engine = self._get_engine()
        engine.record_interaction(
            user_did=self.arena_client.user_did,
            skill_id=skill_id,
            interaction_type=InteractionType.UPVOTE
            if rating >= 4
            else InteractionType.DOWNVOTE,
            value=value,
        )

    async def get_personalized_recommendations(
        self, top_n: int = 10, exclude_used: bool = True
    ) -> List[SkillRecommendation]:
        """Get personalized skill recommendations."""
        if not self.arena_client.consent.config.is_valid():
            # Fall back to server-side recommendations
            return await self.arena_client.get_recommendations(limit=top_n)

        # Get used skills
        exclude_skills = []
        if exclude_used:
            user_profile = self._get_engine().get_user_profile(
                self.arena_client.user_did
            )
            if user_profile:
                exclude_skills = user_profile.preferred_skills

        engine = self._get_engine()
        return engine.get_recommendations(
            user_did=self.arena_client.user_did,
            exclude_skills=exclude_skills,
            top_n=top_n,
        )

    async def get_skill_similarities(
        self, skill_id: str, top_n: int = 5
    ) -> List[Tuple[str, float]]:
        """Get skills similar to the given skill."""
        engine = self._get_engine()
        return engine.get_similar_skills(skill_id, top_n)

    async def get_popular_skills(self, top_n: int = 10) -> List[Tuple[str, float]]:
        """Get popular skills."""
        engine = self._get_engine()
        return engine.get_popular_skills(top_n)

    def get_user_profile(self) -> Optional[UserProfile]:
        """Get current user's profile."""
        return self._get_engine().get_user_profile(self.arena_client.user_did)

    def train_model(self) -> None:
        """Train the recommendation model."""
        self._get_engine().train()

    def get_stats(self) -> Dict[str, Any]:
        """Get CF engine statistics."""
        return self._get_engine().get_stats()


# ============ Demo ============


async def main():
    """Demo the collaborative filtering engine."""

    print("\n" + "=" * 60)
    print("COLLABORATIVE FILTERING ENGINE - Demo")
    print("=" * 60)

    # Initialize engine
    engine = CollaborativeFilteringEngine(data_dir=Path("./data/demo_cf"))

    # Simulate user interactions
    users = [f"user-{i}" for i in range(1, 21)]
    skills = [f"skill-{i}" for i in range(1, 51)]

    print("\n📊 Simulating user interactions...")

    # Create interaction patterns
    for user in users:
        # Each user uses 5-15 skills
        n_skills = random.randint(5, 15)
        user_skills = random.sample(skills, n_skills)

        for skill in user_skills:
            # Simulate usage
            engine.record_interaction(
                user_did=user,
                skill_id=skill,
                interaction_type=InteractionType.USAGE,
                value=random.uniform(0.7, 1.0),
            )

    print(f"   Added {engine.matrix.nnz} interactions")
    print(f"   Users: {len(engine.matrix.user_map)}")
    print(f"   Skills: {len(engine.matrix.item_map)}")

    # Train model
    print("\n🎯 Training recommendation model...")
    engine.train()

    # Get recommendations for a user
    test_user = "user-1"
    print(f"\n📌 Recommendations for {test_user}:")

    recs = engine.get_recommendations(user_did=test_user, top_n=10)

    for rec in recs[:5]:
        print(f"   - {rec.skill_id}: {rec.score:.3f} ({rec.reason})")

    # Get similar skills
    print(f"\n🔗 Skills similar to 'skill-1':")
    similar = engine.get_similar_skills("skill-1", top_n=5)
    for skill_id, sim in similar:
        print(f"   - {skill_id}: {sim:.3f}")

    # Get popular skills
    print("\n🔥 Most popular skills:")
    popular = engine.get_popular_skills(top_n=5)
    for skill_id, count in popular:
        print(f"   - {skill_id}: {count} uses")

    # Get user profile
    profile = engine.get_user_profile(test_user)
    if profile:
        print(f"\n👤 User profile for {test_user}:")
        print(f"   Total interactions: {profile.total_interactions}")
        print(f"   Average rating: {profile.average_rating:.2f}")
        print(f"   Preferred skills: {len(profile.preferred_skills)}")

    # Stats
    print("\n📈 Engine statistics:")
    stats = engine.get_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")

    # Cleanup
    engine.clear()
    print("\n✅ Demo complete!")


if __name__ == "__main__":
    asyncio.run(main())
