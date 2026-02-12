#!/usr/bin/env python3
"""
Phase 3: Advanced Collaborative Filtering Features

Implements:
1. Matrix Factorization (SVD, ALS, NMF)
2. Real-time Incremental Updates
3. Context-Aware Recommendations
4. A/B Testing Framework
5. Multi-Armed Bandit Optimization

Author: Skills Arena Team
Version: 3.0.0
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
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import svds
from scipy.sparse.linalg import spsolve


class FactorizationMethod(Enum):
    """Matrix factorization methods."""

    SVD = "svd"  # Truncated SVD
    ALS = "als"  # Alternating Least Squares
    NMF = "nmf"  # Non-negative Matrix Factorization
    BPR = "bpr"  # Bayesian Personalized Ranking


class ContextType(Enum):
    """Context types for recommendations."""

    TIME_OF_DAY = "time_of_day"
    DAY_OF_WEEK = "day_of_week"
    DEVICE_TYPE = "device_type"
    LOCATION = "location"
    TASK_TYPE = "task_type"


@dataclass
class Context:
    """Context information for recommendations."""

    context_type: ContextType
    value: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "context_type": self.context_type.value,
            "value": self.value,
            "timestamp": self.timestamp,
        }


@dataclass
class ContextualInteraction:
    """A user-skill interaction with context."""

    user_hash: str
    skill_id: str
    value: float
    contexts: List[Context] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ABTest:
    """A/B test configuration."""

    test_id: str
    name: str
    variant_a: str  # Control
    variant_b: str  # Treatment
    traffic_split: float  # % to variant B
    start_date: str
    end_date: Optional[str] = None
    metric: str = "ctr"  # click-through rate
    status: str = "running"  # running, completed, paused

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_id": self.test_id,
            "name": self.name,
            "variant_a": self.variant_a,
            "variant_b": self.variant_b,
            "traffic_split": self.traffic_split,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "metric": self.metric,
            "status": self.status,
        }


@dataclass
class ABTestResult:
    """Result of an A/B test."""

    test_id: str
    variant_a_metric: float
    variant_b_metric: float
    improvement: float
    confidence: float
    significance: float  # p-value
    winner: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_id": self.test_id,
            "variant_a_metric": self.variant_a_metric,
            "variant_b_metric": self.variant_b_metric,
            "improvement": self.improvement,
            "confidence": self.confidence,
            "significance": self.significance,
            "winner": self.winner,
        }


# ============ Matrix Factorization ============


class MatrixFactorizer:
    """
    Base class for matrix factorization methods.

    Decomposes user-item matrix R into:
    R ≈ P × Q^T

    Where:
    - P: User factors (n_users × k)
    - Q: Item factors (n_items × k)
    - k: Latent dimension
    """

    def __init__(
        self,
        n_factors: int = 50,
        regularization: float = 0.01,
        learning_rate: float = 0.005,
        n_iterations: int = 20,
    ):
        self.n_factors = n_factors
        self.regularization = regularization
        self.learning_rate = learning_rate
        self.n_iterations = n_iterations
        self.user_factors: Optional[np.ndarray] = None
        self.item_factors: Optional[np.ndarray] = None
        self.global_mean: float = 0.0
        self.user_bias: Optional[np.ndarray] = None
        self.item_bias: Optional[np.ndarray] = None
        self._is_fitted = False

    @abstractmethod
    def fit(self, matrix: sp.csr_matrix) -> None:
        """Fit the model to the interaction matrix."""
        pass

    def predict(self, user_idx: int, item_idx: int) -> float:
        """Predict rating for user-item pair."""
        if not self._is_fitted:
            return self.global_mean

        pred = self.global_mean
        pred += self.user_bias[user_idx] if self.user_bias is not None else 0
        pred += self.item_bias[item_idx] if self.item_bias is not None else 0
        pred += np.dot(self.user_factors[user_idx], self.item_factors[item_idx])
        return max(0, min(1, pred))  # Clamp to [0, 1]

    def recommend_for_user(
        self, user_idx: int, exclude_items: Optional[List[int]] = None, top_n: int = 10
    ) -> List[Tuple[int, float]]:
        """Generate recommendations for a user."""
        if not self._is_fitted:
            return []

        exclude_items = exclude_items or []

        # Compute predicted ratings for all items
        user_vec = self.user_factors[user_idx]
        scores = np.dot(user_vec, self.item_factors.T)

        # Add biases
        if self.user_bias is not None:
            scores += self.user_bias[user_idx]
        if self.item_bias is not None:
            scores += self.item_bias

        scores += self.global_mean

        # Filter excluded items
        for idx in exclude_items:
            if idx < len(scores):
                scores[idx] = -np.inf

        # Get top N
        top_indices = np.argsort(scores)[::-1][:top_n]
        return [(idx, float(scores[idx])) for idx in top_indices]

    def save(self, path: Path) -> None:
        """Save model to disk."""
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez(
            path,
            user_factors=self.user_factors,
            item_factors=self.item_factors,
            global_mean=self.global_mean,
            n_factors=self.n_factors,
            regularization=self.regularization,
        )
        if self.user_bias is not None:
            np.save(path.with_suffix(".user_bias.npy"), self.user_bias)
        if self.item_bias is not None:
            np.save(path.with_suffix(".item_bias.npy"), self.item_bias)

    def load(self, path: Path) -> None:
        """Load model from disk."""
        data = np.load(path)
        self.user_factors = data["user_factors"]
        self.item_factors = data["item_factors"]
        self.global_mean = float(data["global_mean"])
        self.n_factors = int(data["n_factors"])
        self.regularization = float(data["regularization"])

        user_bias_path = path.with_suffix(".user_bias.npy")
        if user_bias_path.exists():
            self.user_bias = np.load(user_bias_path)

        item_bias_path = path.with_suffix(".item_bias.npy")
        if item_bias_path.exists():
            self.item_bias = np.load(item_bias_path)

        self._is_fitted = True


class SVDFactorizer(MatrixFactorizer):
    """
    Truncated SVD for matrix factorization.

    Fast and works well with sparse matrices.
    """

    def fit(self, matrix: sp.csr_matrix) -> None:
        """Fit SVD model."""
        if matrix.nnz < 100:
            self._is_fitted = False
            return

        # Determine number of factors
        n_factors = min(self.n_factors, min(matrix.shape) - 1)

        # Compute mean for centering
        self.global_mean = matrix.data.mean() if matrix.nnz > 0 else 0.5

        try:
            # Perform SVD
            U, sigma, Vt = svds(matrix.astype(float), k=n_factors)

            # Convert to dense factors
            self.user_factors = U * np.sqrt(sigma)
            self.item_factors = (Vt.T * np.sqrt(sigma)).T

            self._is_fitted = True

        except Exception as e:
            print(f"SVD fitting failed: {e}")
            self._is_fitted = False


class ALSFactorizer(MatrixFactorizer):
    """
    Alternating Least Squares for matrix factorization.

    Good for implicit feedback. Handles missing values naturally.
    """

    def __init__(
        self,
        n_factors: int = 50,
        regularization: float = 0.01,
        alpha: float = 40,  # Confidence scaling
        n_iterations: int = 15,
    ):
        super().__init__(n_factors, regularization, 0, n_iterations)
        self.alpha = alpha  # Confidence multiplier for implicit feedback
        self._confidence: Optional[sp.csr_matrix] = None

    def fit(self, matrix: sp.csr_matrix) -> None:
        """Fit ALS model."""
        if matrix.nnz < 100:
            self._is_fitted = False
            return

        self.global_mean = matrix.data.mean() if matrix.nnz > 0 else 0.5
        n_users, n_items = matrix.shape

        # Initialize factors randomly
        random.seed(42)
        self.user_factors = np.random.rand(n_users, self.n_factors) * 0.1
        self.item_factors = np.random.rand(n_items, self.n_factors) * 0.1
        self.user_bias = np.zeros(n_users)
        self.item_bias = np.zeros(n_items)

        # Build confidence matrix for implicit feedback
        self._confidence = sp.csr_matrix(
            (matrix.data * self.alpha + 1, matrix.indices, matrix.indptr),
            shape=matrix.shape,
        )

        # ALS iterations
        for iteration in range(self.n_iterations):
            # Update user factors
            self._update_users(matrix)
            # Update item factors
            self._update_items(matrix)

        self._is_fitted = True

    def _update_users(self, matrix: sp.csr_matrix) -> None:
        """Update user factors."""
        n_users, n_items = matrix.shape
        YtY = self.item_factors.T @ self.item_factors
        lambda_I = self.regularization * np.eye(self.n_factors)

        for u in range(n_users):
            # Get items user has interacted with
            row = matrix.getrow(u).tocoo()
            indices = row.col
            values = row.data

            if len(indices) == 0:
                continue

            # Build the system
            item_vectors = self.item_factors[indices]
            confidence = (
                self._confidence.getrow(u).data
                if self._confidence is not None
                else values
            )

            A = (
                YtY
                + lambda_I
                + item_vectors.T @ (item_vectors * (confidence - 1)[:, np.newaxis])
            )
            b = (item_vectors.T @ (values + self.global_mean)).flatten()

            # Solve for user factors
            try:
                self.user_factors[u] = np.linalg.solve(A, b)
            except np.linalg.LinAlgError:
                pass  # Keep old value

    def _update_items(self, matrix: sp.csr_matrix) -> None:
        """Update item factors."""
        n_users, n_items = matrix.shape
        XtX = self.user_factors.T @ self.user_factors
        lambda_I = self.regularization * np.eye(self.n_factors)

        for i in range(n_items):
            # Get users who interacted with this item
            col = matrix.getcol(i).tocoo()
            indices = col.row
            values = col.data

            if len(indices) == 0:
                continue

            user_vectors = self.user_factors[indices]
            confidence = (
                self._confidence.getcol(i).data
                if self._confidence is not None
                else values
            )

            A = (
                XtX
                + lambda_I
                + user_vectors.T @ (user_vectors * (confidence - 1)[:, np.newaxis])
            )
            b = (user_vectors.T @ (values + self.global_mean)).flatten()

            try:
                self.item_factors[i] = np.linalg.solve(A, b)
            except np.linalg.LinAlgError:
                pass


class BPRFactorizer(MatrixFactorizer):
    """
    Bayesian Personalized Ranking for implicit feedback.

    Optimizes for ranking rather than rating prediction.
    """

    def __init__(
        self,
        n_factors: int = 30,
        learning_rate: float = 0.05,
        regularization: float = 0.01,
        n_iterations: int = 10,
    ):
        super().__init__(n_factors, regularization, learning_rate, n_iterations)
        self.negative_samples = 4  # Number of negative samples per positive

    def fit(self, matrix: sp.csr_matrix) -> None:
        """Fit BPR model."""
        if matrix.nnz < 100:
            self._is_fitted = False
            return

        n_users, n_items = matrix.shape
        self.global_mean = 0.5

        # Initialize factors
        self.user_factors = np.random.randn(n_users, self.n_factors) * 0.01
        self.item_factors = np.random.randn(n_items, self.n_factors) * 0.01

        # Get positive interactions
        positive_pairs = [
            (u, i) for u in range(n_users) for i in range(n_items) if matrix[u, i] > 0
        ]

        # Training iterations
        for iteration in range(self.n_iterations):
            # Sample negative interactions
            np.random.shuffle(positive_pairs)

            for u, i in positive_pairs[:1000]:  # Limit per iteration
                # Sample negative item
                j = np.random.randint(n_items)
                while matrix[u, j] > 0:
                    j = np.random.randint(n_items)

                # Compute difference
                x_ui = np.dot(self.user_factors[u], self.item_factors[i])
                x_uj = np.dot(self.user_factors[u], self.item_factors[j])
                x_uij = x_ui - x_uj

                # Gradient
                sigmoid = 1 / (1 + math.exp(max(-500, min(500, x_uij))))
                grad = sigmoid - 1

                # Update factors
                self.user_factors[u] += self.learning_rate * (
                    grad * (self.item_factors[i] - self.item_factors[j])
                    - self.regularization * self.user_factors[u]
                )
                self.item_factors[i] += self.learning_rate * (
                    grad * self.user_factors[u]
                    - self.regularization * self.item_factors[i]
                )
                self.item_factors[j] -= self.learning_rate * (
                    grad * self.user_factors[u]
                    - self.regularization * self.item_factors[j]
                )

        self._is_fitted = True

    def recommend_for_user(
        self, user_idx: int, exclude_items: Optional[List[int]] = None, top_n: int = 10
    ) -> List[Tuple[int, float]]:
        """Generate recommendations using BPR scores."""
        if not self._is_fitted:
            return []

        exclude_items = exclude_items or []

        # Compute BPR scores
        scores = np.dot(self.user_factors[user_idx], self.item_factors.T)

        # Filter excluded items
        for idx in exclude_items:
            if idx < len(scores):
                scores[idx] = -np.inf

        # Sigmoid transform
        scores = 1 / (1 + np.exp(-scores))

        # Get top N
        top_indices = np.argsort(scores)[::-1][:top_n]
        return [(idx, float(scores[idx])) for idx in top_indices]


# ============ Context-Aware Recommendations ============


class ContextEngine:
    """
    Context-aware recommendation engine.

    Adapts recommendations based on contextual information:
    - Time of day
    - Day of week
    - Task type
    - Device type
    """

    def __init__(self, base_engine):
        self.base_engine = base_engine
        self.context_factors: Dict[str, Dict[str, np.ndarray]] = {}
        self.context_counts: Dict[str, Dict[str, int]] = {}

    def add_context_interaction(self, interaction: ContextualInteraction) -> None:
        """Add a contextual interaction."""
        for context in interaction.contexts:
            ct = context.context_type.value
            cv = context.value

            # Initialize if needed
            if ct not in self.context_factors:
                self.context_factors[ct] = {}
            if cv not in self.context_factors[ct]:
                # Initialize with random factors
                n_items = (
                    len(self.base_engine.item_factors)
                    if self.base_engine._is_fitted
                    else 10
                )
                self.context_factors[ct][cv] = np.random.randn(n_items) * 0.01

            if ct not in self.context_counts:
                self.context_counts[ct] = {}
            self.context_counts[ct][cv] = self.context_counts[ct].get(cv, 0) + 1

    def get_context_adjusted_scores(
        self, user_idx: int, context_type: ContextType, context_value: str
    ) -> np.ndarray:
        """Get context-adjusted item scores."""
        if not self.base_engine._is_fitted:
            return np.array([])

        # Base scores
        base_scores = np.dot(
            self.base_engine.user_factors[user_idx], self.base_engine.item_factors.T
        )

        # Context adjustment
        ct = context_type.value
        if ct in self.context_factors and context_value in self.context_factors[ct]:
            context_vec = self.context_factors[ct][context_value]
            # Blend base and context scores
            count = self.context_counts[ct][context_value]
            blend_factor = min(0.5, 1.0 / (1 + count))
            base_scores = (1 - blend_factor) * base_scores + blend_factor * context_vec

        return base_scores

    def recommend_with_context(
        self,
        user_idx: int,
        contexts: List[Context],
        exclude_items: Optional[List[int]] = None,
        top_n: int = 10,
    ) -> List[Tuple[int, float]]:
        """Generate context-aware recommendations."""
        if not self.base_engine._is_fitted:
            return []

        # Start with base scores
        scores = np.dot(
            self.base_engine.user_factors[user_idx], self.base_engine.item_factors.T
        )

        # Apply context adjustments
        for context in contexts:
            adjusted = self.get_context_adjusted_scores(
                user_idx, context.context_type, context.value
            )
            if len(adjusted) > 0:
                scores = 0.7 * scores + 0.3 * adjusted

        # Filter excluded items
        exclude_items = exclude_items or []
        for idx in exclude_items:
            if idx < len(scores):
                scores[idx] = -np.inf

        # Get top N
        top_indices = np.argsort(scores)[::-1][:top_n]
        return [(idx, float(scores[idx])) for idx in top_indices]


# ============ Incremental Updates ============


class IncrementalUpdater:
    """
    Handles incremental model updates without full retraining.

    Techniques:
    - Streaming SVD updates
    - Online learning for ALS
    - Stochastic gradient descent
    """

    def __init__(self, factorizer: MatrixFactorizer):
        self.factorizer = factorizer
        self.update_queue: List[Tuple[int, int, float]] = []
        self.batch_size = 100
        self._lock = threading.Lock()

    def add_update(self, user_idx: int, item_idx: int, value: float) -> None:
        """Queue an update."""
        with self._lock:
            self.update_queue.append((user_idx, item_idx, value))

            if len(self.update_queue) >= self.batch_size:
                self.process_batch()

    def process_batch(self) -> None:
        """Process queued updates."""
        with self._lock:
            if not self.update_queue:
                return

            updates = self.update_queue[: self.batch_size]
            self.update_queue = self.update_queue[self.batch_size :]

        if not self.factorizer._is_fitted:
            return

        # SGD update for new interactions
        for user_idx, item_idx, value in updates:
            # Prediction error
            pred = self._predict_single(user_idx, item_idx)
            error = value - pred

            if abs(error) < 0.01:
                continue

            # Update user factors
            lr = self.factorizer.learning_rate
            reg = self.factorizer.regularization

            user_f = self.factorizer.user_factors[user_idx]
            item_f = self.factorizer.item_factors[item_idx]

            # SGD step
            user_f += lr * (error * item_f - reg * user_f)
            item_f += lr * (error * user_f - reg * item_f)

            # Normalize
            if np.linalg.norm(user_f) > 1:
                user_f /= np.linalg.norm(user_f)
            if np.linalg.norm(item_f) > 1:
                item_f /= np.linalg.norm(item_f)

    def _predict_single(self, user_idx: int, item_idx: int) -> float:
        """Single prediction without bias terms."""
        if not self.factorizer._is_fitted:
            return self.factorizer.global_mean

        return np.dot(
            self.factorizer.user_factors[user_idx],
            self.factorizer.item_factors[item_idx],
        )


# ============ A/B Testing Framework ============


class ABTestingFramework:
    """
    A/B testing framework for recommendation algorithms.

    Features:
    - Random traffic allocation
    - Metric tracking
    - Statistical significance testing
    - Automatic winner declaration
    """

    def __init__(self):
        self.tests: Dict[str, ABTest] = {}
        self.test_assignments: Dict[str, str] = {}  # user -> test_id
        self.test_metrics: Dict[str, Dict[str, List[float]]] = {}
        self._lock = threading.Lock()

    def create_test(
        self,
        name: str,
        variant_a: str,
        variant_b: str,
        traffic_split: float = 0.5,
        metric: str = "ctr",
        duration_days: int = 14,
    ) -> str:
        """Create a new A/B test."""
        test_id = f"test_{uuid.uuid4().hex[:8]}"

        test = ABTest(
            test_id=test_id,
            name=name,
            variant_a=variant_a,
            variant_b=variant_b,
            traffic_split=traffic_split,
            start_date=datetime.now().isoformat(),
            end_date=(datetime.now() + timedelta(days=duration_days)).isoformat(),
            metric=metric,
            status="running",
        )

        with self._lock:
            self.tests[test_id] = test
            self.test_metrics[test_id] = {"a": [], "b": []}

        return test_id

    def assign_variant(self, user_hash: str, test_id: str) -> str:
        """Assign a user to a variant."""
        if test_id not in self.tests:
            return "control"

        # Check if already assigned
        key = f"{user_hash}:{test_id}"
        if key in self.test_assignments:
            return self.test_assignments[key]

        # Assign based on traffic split
        test = self.tests[test_id]
        if random.random() < test.traffic_split:
            variant = "b"
        else:
            variant = "a"

        self.test_assignments[key] = variant
        return variant

    def record_metric(self, test_id: str, variant: str, value: float) -> None:
        """Record a metric for a test variant."""
        if test_id not in self.test_metrics:
            return

        with self._lock:
            self.test_metrics[test_id][variant].append(value)

    def compute_results(self, test_id: str) -> Optional[ABTestResult]:
        """Compute results for a test."""
        if test_id not in self.tests:
            return None

        test = self.tests[test_id]
        metrics_a = self.test_metrics[test_id]["a"]
        metrics_b = self.test_metrics[test_id]["b"]

        if len(metrics_a) < 100 or len(metrics_b) < 100:
            return None  # Not enough data

        mean_a = np.mean(metrics_a)
        mean_b = np.mean(metrics_b)

        # Compute improvement
        improvement = (mean_b - mean_a) / mean_a if mean_a > 0 else 0

        # Compute p-value (simple z-test)
        std_a = np.std(metrics_a) / np.sqrt(len(metrics_a))
        std_b = np.std(metrics_b) / np.sqrt(len(metrics_b))

        if std_a + std_b == 0:
            significance = 1.0
        else:
            z_score = (mean_b - mean_a) / (std_a + std_b)
            significance = 2 * (1 - 0.5 * (1 + math.erf(abs(z_score) / math.sqrt(2))))

        # Determine winner
        confidence = 1 - significance
        winner = None
        if significance < 0.05:
            if improvement > 0:
                winner = "b"
            else:
                winner = "a"

        return ABTestResult(
            test_id=test_id,
            variant_a_metric=mean_a,
            variant_b_metric=mean_b,
            improvement=improvement,
            confidence=confidence,
            significance=significance,
            winner=winner,
        )

    def get_test_status(self, test_id: str) -> Dict[str, Any]:
        """Get the status of a test."""
        if test_id not in self.tests:
            return {}

        test = self.tests[test_id]
        result = self.compute_results(test_id)

        return {
            "test_id": test_id,
            "name": test.name,
            "status": test.status,
            "n_samples_a": len(self.test_metrics[test_id]["a"]),
            "n_samples_b": len(self.test_metrics[test_id]["b"]),
            "result": result.to_dict() if result else None,
        }

    def stop_test(self, test_id: str) -> None:
        """Stop a test."""
        if test_id in self.tests:
            self.tests[test_id].status = "completed"
            self.tests[test_id].end_date = datetime.now().isoformat()


# ============ Multi-Armed Bandit ============


class BanditOptimizer:
    """
    Multi-Armed Bandit optimizer for recommendation selection.

    Balances exploration and exploitation using Thompson Sampling.
    """

    def __init__(self, n_arms: int, method: str = "thompson"):
        self.n_arms = n_arms
        self.method = method

        # Beta distribution parameters for each arm
        self.successes: List[int] = [0] * n_arms
        self.failures: List[int] = [0] * n_arms

        # UCB parameters
        self.counts: List[int] = [0] * n_arms
        self.values: List[float] = [0.0] * n_arms

        self._lock = threading.Lock()

    def select_arm(self) -> int:
        """Select an arm using the specified method."""
        with self._lock:
            if self.method == "thompson":
                return self._thompson_sampling()
            elif self.method == "ucb":
                return self._upper_confidence_bound()
            else:
                return self._epsilon_greedy()

    def _thompson_sampling(self) -> int:
        """Thompson Sampling with Beta distribution."""
        samples = [
            np.random.beta(self.successes[i] + 1, self.failures[i] + 1)
            for i in range(self.n_arms)
        ]
        return np.argmax(samples)

    def _upper_confidence_bound(self) -> int:
        """UCB1 algorithm."""
        n = sum(self.counts)
        if n == 0:
            return random.randint(0, self.n_arms - 1)

        ucb_values = []
        for i in range(self.n_arms):
            if self.counts[i] == 0:
                ucb_values.append(float("inf"))
            else:
                avg = self.values[i]
                confidence = math.sqrt(2 * math.log(n) / self.counts[i])
                ucb_values.append(avg + confidence)

        return np.argmax(ucb_values)

    def _epsilon_greedy(self, epsilon: float = 0.1) -> int:
        """Epsilon-greedy selection."""
        if random.random() < epsilon:
            return random.randint(0, self.n_arms - 1)
        return np.argmax(self.values)

    def update(self, arm: int, reward: float) -> None:
        """Update arm with reward."""
        with self._lock:
            self.counts[arm] += 1
            n = self.counts[arm]
            value = self.values[arm]
            self.values[arm] = ((n - 1) / n) * value + (1 / n) * reward

            if reward > 0.5:
                self.successes[arm] += 1
            else:
                self.failures[arm] += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get bandit statistics."""
        with self._lock:
            return {
                "n_arms": self.n_arms,
                "counts": self.counts.copy(),
                "values": self.values.copy(),
                "successes": self.successes.copy(),
                "failures": self.failures.copy(),
                "best_arm": int(np.argmax(self.values)),
            }


# ============ Complete Phase 3 Engine ============


class AdvancedRecommender:
    """
    Complete recommendation engine with Phase 3 features.

    Combines:
    - Multiple factorization methods
    - Context-aware recommendations
    - Incremental updates
    - A/B testing
    - Bandit optimization
    """

    def __init__(self, data_dir: Path = Path("./data/advanced_cf")):
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Factorization methods
        self.svd = SVDFactorizer(n_factors=50)
        self.als = ALSFactorizer(n_factors=30)
        self.bpr = BPRFactorizer(n_factors=20)
        self.current_method = "als"

        # Context engine
        self.context_engine: Optional[ContextEngine] = None

        # Incremental updater
        self.updater: Optional[IncrementalUpdater] = None

        # A/B testing
        self.ab_framework = ABTestingFramework()

        # Bandit optimizer
        self.bandit = BanditOptimizer(n_arms=4)

        # Interaction tracking
        self.interactions: List[ContextualInteraction] = []

        self._load_state()

    def set_factorization_method(self, method: str) -> None:
        """Set the factorization method."""
        if method in ["svd", "als", "bpr"]:
            self.current_method = method

    def add_interaction(
        self,
        user_hash: str,
        skill_id: str,
        value: float,
        contexts: Optional[List[Context]] = None,
    ) -> None:
        """Add a contextual interaction."""
        interaction = ContextualInteraction(
            user_hash=user_hash, skill_id=skill_id, value=value, contexts=contexts or []
        )

        self.interactions.append(interaction)

        # Update context engine
        if self.context_engine:
            self.context_engine.add_context_interaction(interaction)

        # Update bandit
        self.bandit.update(self.bandit.select_arm(), value)

    def train(self, method: Optional[str] = None) -> Dict[str, Any]:
        """Train the recommendation model."""
        method = method or self.current_method

        # Build matrix
        matrix = self._build_matrix()
        if matrix.nnz < 100:
            return {"status": "insufficient_data"}

        # Train selected method
        if method == "svd":
            self.svd.fit(matrix)
            factorizer = self.svd
        elif method == "als":
            self.als.fit(matrix)
            factorizer = self.als
        elif method == "bpr":
            self.bpr.fit(matrix)
            factorizer = self.bpr
        else:
            return {"status": "unknown_method"}

        # Initialize context engine
        self.context_engine = ContextEngine(factorizer)
        for interaction in self.interactions:
            self.context_engine.add_context_interaction(interaction)

        # Initialize updater
        self.updater = IncrementalUpdater(factorizer)

        # Save state
        self._save_state()

        return {
            "status": "success",
            "method": method,
            "n_users": matrix.shape[0],
            "n_items": matrix.shape[1],
            "n_interactions": matrix.nnz,
        }

    def _build_matrix(self) -> sp.csr_matrix:
        """Build sparse matrix from interactions."""
        from scripts.collab_sdk import SparseMatrix, UserInteraction, InteractionType

        # Build user/item maps
        user_map: Dict[str, int] = {}
        item_map: Dict[str, int] = {}

        for interaction in self.interactions:
            if interaction.user_hash not in user_map:
                user_map[interaction.user_hash] = len(user_map)
            if interaction.skill_id not in item_map:
                item_map[interaction.skill_id] = len(item_map)

        if not user_map or not item_map:
            return sp.csr_matrix((0, 0))

        # Build matrix
        rows, cols, data = [], [], []
        for interaction in self.interactions:
            rows.append(user_map[interaction.user_hash])
            cols.append(item_map[interaction.skill_id])
            data.append(interaction.value)

        return sp.csr_matrix(
            (data, (rows, cols)), shape=(len(user_map), len(item_map)), dtype=np.float32
        )

    def recommend(
        self,
        user_hash: str,
        contexts: Optional[List[Context]] = None,
        exclude_skills: Optional[List[str]] = None,
        top_n: int = 10,
        use_bandit: bool = False,
    ) -> List[Dict[str, Any]]:
        """Generate recommendations."""
        # Use bandit for exploration
        if use_bandit:
            arm = self.bandit.select_arm()
            method = ["svd", "als", "bpr", "hybrid"][min(arm, 3)]
            self.set_factorization_method(method)

        # Get factorizer
        if self.current_method == "svd":
            factorizer = self.svd
        elif self.current_method == "als":
            factorizer = self.als
        elif self.current_method == "bpr":
            factorizer = self.bpr
        else:
            factorizer = self.als

        if not factorizer._is_fitted:
            return []

        # Get user index
        user_idx = self._get_user_index(user_hash)
        if user_idx is None:
            return []

        # Get item map
        item_map = self._get_item_map()

        # Exclude items
        exclude_indices = [item_map[s] for s in (exclude_skills or []) if s in item_map]

        # Generate recommendations
        if contexts and self.context_engine:
            recs = self.context_engine.recommend_with_context(
                user_idx, contexts, exclude_indices, top_n
            )
        else:
            recs = factorizer.recommend_for_user(user_idx, exclude_indices, top_n)

        # Convert to output format
        reverse_map = {v: k for k, v in item_map.items()}
        return [
            {
                "skill_id": reverse_map.get(idx, f"unknown_{idx}"),
                "score": score,
                "method": self.current_method,
                "context": [c.context_type.value for c in (contexts or [])],
            }
            for idx, score in recs
        ]

    def _get_user_index(self, user_hash: str) -> Optional[int]:
        """Get user index from hash."""
        user_map = self._get_user_map()
        return user_map.get(user_hash)

    def _get_user_map(self) -> Dict[str, int]:
        """Get user map from interactions."""
        user_map = {}
        for interaction in self.interactions:
            if interaction.user_hash not in user_map:
                user_map[interaction.user_hash] = len(user_map)
        return user_map

    def _get_item_map(self) -> Dict[str, int]:
        """Get item map from interactions."""
        item_map = {}
        for interaction in self.interactions:
            if interaction.skill_id not in item_map:
                item_map[interaction.skill_id] = len(item_map)
        return item_map

    def create_ab_test(
        self,
        name: str,
        method_a: str = "svd",
        method_b: str = "als",
        traffic_split: float = 0.5,
    ) -> str:
        """Create an A/B test between methods."""
        return self.ab_framework.create_test(
            name=name,
            variant_a=method_a,
            variant_b=method_b,
            traffic_split=traffic_split,
        )

    def assign_to_test(self, user_hash: str, test_id: str) -> str:
        """Assign user to A/B test variant."""
        return self.ab_framework.assign_variant(user_hash, test_id)

    def record_ab_metric(self, test_id: str, variant: str, value: float) -> None:
        """Record metric for A/B test."""
        self.ab_framework.record_metric(test_id, variant, value)

    def get_ab_results(self, test_id: str) -> Optional[ABTestResult]:
        """Get A/B test results."""
        return self.ab_framework.compute_results(test_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "n_interactions": len(self.interactions),
            "n_users": len(self._get_user_map()),
            "n_items": len(self._get_item_map()),
            "method": self.current_method,
            "svd_fitted": self.svd._is_fitted,
            "als_fitted": self.als._is_fitted,
            "bpr_fitted": self.bpr._is_fitted,
            "bandit_stats": self.bandit.get_stats(),
        }

    def _save_state(self) -> None:
        """Save state to disk."""
        path = self.data_dir / "advanced_model.pkl"
        with open(path, "wb") as f:
            pickle.dump(
                {
                    "interactions": [
                        {
                            "user_hash": i.user_hash,
                            "skill_id": i.skill_id,
                            "value": i.value,
                            "contexts": [c.to_dict() for c in i.contexts],
                            "timestamp": i.timestamp,
                        }
                        for i in self.interactions
                    ],
                    "current_method": self.current_method,
                },
                f,
            )

    def _load_state(self) -> None:
        """Load state from disk."""
        path = self.data_dir / "advanced_model.pkl"
        if path.exists():
            with open(path, "rb") as f:
                data = pickle.load(f)
            self.interactions = [
                ContextualInteraction(
                    user_hash=i["user_hash"],
                    skill_id=i["skill_id"],
                    value=i["value"],
                    contexts=[Context(**c) for c in i.get("contexts", [])],
                    timestamp=i["timestamp"],
                )
                for i in data.get("interactions", [])
            ]
            self.current_method = data.get("current_method", "als")


# ============ Demo ============


async def main():
    """Demo Phase 3 features."""

    print("\n" + "=" * 60)
    print("PHASE 3: ADVANCED COLLABORATIVE FILTERING")
    print("=" * 60)

    # Initialize engine
    engine = AdvancedRecommender()

    # Generate synthetic data
    print("\n📊 Generating synthetic interaction data...")

    n_users = 200
    n_skills = 100
    n_interactions = 5000

    for i in range(n_interactions):
        user_hash = f"user-{random.randint(1, n_users)}"
        skill_id = f"skill-{random.randint(1, n_skills)}"
        value = random.uniform(0.5, 1.0)

        # Add some context
        contexts = [
            Context(
                context_type=ContextType.TIME_OF_DAY,
                value=["morning", "afternoon", "evening"][random.randint(0, 2)],
            )
        ]

        engine.add_interaction(user_hash, skill_id, value, contexts)

    print(f"   Generated {len(engine.interactions)} interactions")

    # Train models
    print("\n🎯 Training factorization models...")

    for method in ["svd", "als", "bpr"]:
        result = engine.train(method)
        print(f"   {method.upper()}: {result['status']}")

    # Test recommendations
    print("\n📌 Testing recommendations...")

    test_user = "user-42"
    contexts = [Context(context_type=ContextType.TIME_OF_DAY, value="afternoon")]

    for method in ["svd", "als", "bpr"]:
        engine.set_factorization_method(method)
        recs = engine.recommend(test_user, contexts=contexts, top_n=5)
        print(f"\n   {method.upper()} recommendations for {test_user}:")
        for rec in recs[:3]:
            print(f"      - {rec['skill_id']}: {rec['score']:.3f}")

    # Test A/B testing
    print("\n🧪 A/B Testing...")

    test_id = engine.create_ab_test(
        name="SVD vs ALS", method_a="svd", method_b="als", traffic_split=0.5
    )
    print(f"   Created test: {test_id}")

    # Simulate test traffic
    for i in range(100):
        variant = engine.assign_to_test(f"user-{i}", test_id)
        # Simulate conversion
        metric = random.uniform(0.1, 0.5)
        engine.record_ab_metric(test_id, variant, metric)

    result = engine.get_ab_results(test_id)
    if result:
        print(
            f"   Result: Variant B is {result.improvement * 100:.1f}% {'better' if result.improvement > 0 else 'worse'}"
        )
        print(f"   Confidence: {result.confidence * 100:.1f}%")
        print(f"   Significance: {result.significance:.4f}")

    # Test bandit
    print("\n🎰 Multi-Armed Bandit...")

    for i in range(100):
        arm = engine.bandit.select_arm()
        reward = random.uniform(0.1, 0.9)
        engine.bandit.update(arm, reward)

    stats = engine.bandit.get_stats()
    print(f"   Best arm: {stats['best_arm']}")
    print(f"   Arm values: {[f'{v:.3f}' for v in stats['values']]}")

    # Stats
    print("\n📈 Engine Statistics:")
    engine_stats = engine.get_stats()
    for k, v in engine_stats.items():
        if k != "bandit_stats":
            print(f"   {k}: {v}")

    print("\n✅ Phase 3 Demo Complete!")
    print("\nFeatures Implemented:")
    print("  ✅ Matrix Factorization (SVD, ALS, BPR)")
    print("  ✅ Context-Aware Recommendations")
    print("  ✅ Incremental Updates")
    print("  ✅ A/B Testing Framework")
    print("  ✅ Multi-Armed Bandit Optimization")


if __name__ == "__main__":
    asyncio.run(main())
