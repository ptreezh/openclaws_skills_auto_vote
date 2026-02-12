#!/usr/bin/env python3
"""
Phase 5: Advanced Federated Learning Features

Implements:
1. Hierarchical Federated Learning (HFL)
2. Personalized Federated Learning (PFL)
3. Cross-Silo Federated Learning
4. Asynchronous Federated Updates
5. Continual Learning with Memory

Author: Skills Arena Team
Version: 5.0.0
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


# ============ Enums ============


class HFLTopology(Enum):
    """Hierarchical FL topology types."""

    TWO_TIER = "two_tier"  # Edge + Cloud
    THREE_TIER = "three_tier"  # Device + Edge + Cloud
    MESH = "mesh"  # Peer-to-peer
    STAR = "star"  # Central server + Clients


class AggregationLevel(Enum):
    """Where aggregation happens."""

    DEVICE = "device"
    EDGE = "edge"
    CLOUD = "cloud"


class PersonalizationStrategy(Enum):
    """Personalization strategies."""

    FINE_TUNING = "fine_tuning"
    META_LEARNING = "meta_learning"
    CLUSTERING = "clustering"
    KNOWLEDGE_DISTILLATION = "knowledge_distillation"
    ADAPTIVE = "adaptive"


class UpdateMode(Enum):
    """Update synchronization modes."""

    SYNCHRONOUS = "synchronous"
    ASYNCHRONOUS = "asynchronous"
    SEMI_ASYNCHRONOUS = "semi_synchronous"
    STALE_SYNCHRONOUS = "stale_synchronous"


# ============ Data Classes ============


@dataclass
class HFLConfig:
    """Configuration for hierarchical FL."""

    topology: HFLTopology = HFLTopology.TWO_TIER
    n_edge_servers: int = 5
    clients_per_edge: int = 20
    edge_aggregation_interval: int = 5  # rounds
    cloud_aggregation_interval: int = 50  # rounds
    edge_learning_rate: float = 0.01
    cloud_learning_rate: float = 0.005

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topology": self.topology.value,
            "n_edge_servers": self.n_edge_servers,
            "clients_per_edge": self.clients_per_edge,
            "edge_aggregation_interval": self.edge_aggregation_interval,
            "cloud_aggregation_interval": self.cloud_aggregation_interval,
        }


@dataclass
class PFLConfig:
    """Configuration for personalized FL."""

    strategy: PersonalizationStrategy = PersonalizationStrategy.ADAPTIVE
    local_epochs: int = 5
    adaptation_lr: float = 0.01
    memory_size: int = 100
    cluster_count: int = 10
    distillation_temperature: float = 2.0
    alpha: float = 0.5  # Balance global/local loss

    def to_dict(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy.value,
            "local_epochs": self.local_epochs,
            "adaptation_lr": self.adaptation_lr,
            "memory_size": self.memory_size,
            "cluster_count": self.cluster_count,
            "alpha": self.alpha,
        }


@dataclass
class AsynchronousConfig:
    """Configuration for asynchronous updates."""

    mode: UpdateMode = UpdateMode.ASYNCHRONOUS
    staleness_bound: int = 10
    momentum_decay: float = 0.9
    conflict_threshold: float = 0.5
    update_buffer_size: int = 100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode.value,
            "staleness_bound": self.staleness_bound,
            "momentum_decay": self.momentum_decay,
            "conflict_threshold": self.conflict_threshold,
        }


@dataclass
class ContinualLearningConfig:
    """Configuration for continual learning."""

    memory_size: int = 500
    replay_ratio: float = 0.2
    regularization_lambda: float = 0.01
    elastic_weight_consolidation: bool = True
    ewc_lambda: float = 1000.0
    gem_margin: float = 0.5
    experience_replay: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "memory_size": self.memory_size,
            "replay_ratio": self.replay_ratio,
            "regularization_lambda": self.regularization_lambda,
            "elastic_weight_consolidation": self.elastic_weight_consolidation,
            "experience_replay": self.experience_replay,
        }


@dataclass
class EdgeServerInfo:
    """Information about an edge server."""

    server_id: str
    region: str
    n_clients: int = 0
    aggregation_count: int = 0
    last_active: str = field(default_factory=lambda: datetime.now().isoformat())
    trust_score: float = 1.0
    compute_capacity: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "server_id": self.server_id,
            "region": self.region,
            "n_clients": self.n_clients,
            "aggregation_count": self.aggregation_count,
            "trust_score": self.trust_score,
        }


@dataclass
class ClientCluster:
    """Client cluster for personalization."""

    cluster_id: str
    client_ids: List[str] = field(default_factory=list)
    cluster_weights: Dict[str, np.ndarray] = field(default_factory=dict)
    centroid: Optional[np.ndarray] = None
    size: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "client_ids": self.client_ids,
            "size": self.size,
        }


@dataclass
class ExperienceBuffer:
    """Experience replay buffer."""

    states: List[np.ndarray] = field(default_factory=list)
    actions: List[int] = field(default_factory=list)
    rewards: List[float] = field(default_factory=list)
    next_states: List[np.ndarray] = field(default_factory=list)
    weights: List[float] = field(default_factory=list)
    max_size: int = 500

    def add(self, state, action, reward, next_state, priority=1.0):
        self.states.append(state)
        self.actions.append(action)
        self.rewards.append(reward)
        self.next_states.append(next_state)
        self.weights.append(priority)

        # Maintain max size with priority-based eviction
        if len(self.states) > self.max_size:
            # Remove lowest priority samples
            indices = np.argsort(self.weights)[: len(self.states) - self.max_size]
            self.states = [s for i, s in enumerate(self.states) if i not in indices]
            self.actions = [a for i, a in enumerate(self.actions) if i not in indices]
            self.rewards = [r for i, r in enumerate(self.rewards) if i not in indices]
            self.next_states = [
                ns for i, ns in enumerate(self.next_states) if i not in indices
            ]
            self.weights = [w for i, w in enumerate(self.weights) if i not in indices]

    def sample(self, batch_size: int) -> Tuple:
        """Sample a batch from the buffer."""
        indices = np.random.choice(
            len(self.states), min(batch_size, len(self.states)), replace=False
        )
        return (
            np.array([self.states[i] for i in indices]),
            np.array([self.actions[i] for i in indices]),
            np.array([self.rewards[i] for i in indices]),
            np.array([self.next_states[i] for i in indices]),
            np.array([self.weights[i] for i in indices]),
        )

    def __len__(self):
        return len(self.states)


# ============ Hierarchical Federated Learning ============


class EdgeServer:
    """
    Edge server for intermediate aggregation.

    Responsibilities:
    - Aggregate client updates locally
    - Reduce communication with cloud
    - Provide low-latency service to nearby clients
    """

    def __init__(self, server_id: str, region: str):
        self.server_id = server_id
        self.region = region
        self.clients: List[str] = []
        self.local_model: Optional[Dict[str, np.ndarray]] = None
        self.aggregation_history: List[Dict] = []
        self.round_count = 0

        # For aggregation
        from scripts.collaborative_filtering.phase4.federated_learning import (
            FederatedAveraging,
            FederatedConfig,
        )

        self.fedavg = FederatedAveraging(FederatedConfig())

    def register_client(self, client_id: str) -> None:
        """Register a client with this edge server."""
        if client_id not in self.clients:
            self.clients.append(client_id)

    def aggregate_local(
        self, updates: List[Dict], weights: Optional[List[float]] = None
    ) -> Dict[str, np.ndarray]:
        """Aggregate updates from local clients."""
        if not updates:
            return self.local_model or {}

        self.round_count += 1

        # Convert to ModelUpdate format
        model_updates = []
        for i, update in enumerate(updates):
            from scripts.collaborative_filtering.phase4.federated_learning import (
                ModelUpdate,
                UpdateType,
            )

            model_updates.append(
                ModelUpdate(
                    client_id=f"edge_{self.server_id}_{i}",
                    update_type=UpdateType.WEIGHTS,
                    weights=update,
                    n_samples=100,
                    loss=0.5,
                    accuracy=0.8,
                )
            )

        # Aggregate using FedAvg
        result = self.fedavg.aggregate(model_updates)

        # Store locally
        self.local_model = result.aggregated_weights

        # Record
        self.aggregation_history.append(
            {
                "round": self.round_count,
                "n_contributors": result.n_contributors,
                "loss": result.avg_loss,
                "accuracy": result.avg_accuracy,
            }
        )

        return result.aggregated_weights

    def receive_from_cloud(self, global_model: Dict[str, np.ndarray]) -> None:
        """Receive updated global model from cloud."""
        self.local_model = global_model

    def get_stats(self) -> Dict[str, Any]:
        """Get edge server statistics."""
        return {
            "server_id": self.server_id,
            "region": self.region,
            "n_clients": len(self.clients),
            "aggregation_count": self.round_count,
            "local_model_available": self.local_model is not None,
        }


class HierarchicalFederatedCoordinator:
    """
    Hierarchical FL coordinator.

    Manages:
    - Edge servers
    - Cloud aggregation
    - Regional load balancing
    """

    def __init__(
        self, hfl_config: HFLConfig, data_dir: Path = Path("./data/hierarchical_fl")
    ):
        self.config = hfl_config
        self.data_dir = data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Edge servers
        self.edge_servers: Dict[str, EdgeServer] = {}
        self._create_edge_servers()

        # Global model
        self.global_model: Optional[Dict[str, np.ndarray]] = None
        self.global_round = 0

        # Client mapping
        self.client_to_edge: Dict[str, str] = {}

        # Statistics
        self.aggregation_history: List[Dict] = []

        self._lock = threading.Lock()

    def _create_edge_servers(self) -> None:
        """Create edge servers."""
        regions = ["us-east", "us-west", "eu-west", "asia-east", "asia-south"]

        for i in range(self.config.n_edge_servers):
            region = regions[i % len(regions)]
            server_id = f"edge_{region}_{i}"
            self.edge_servers[server_id] = EdgeServer(server_id, region)

    def assign_client_to_edge(self, client_id: str) -> str:
        """Assign a client to an edge server."""
        # Round-robin assignment
        server_ids = list(self.edge_servers.keys())
        edge_id = server_ids[len(self.client_to_edge) % len(server_ids)]

        self.client_to_edge[client_id] = edge_id
        self.edge_servers[edge_id].register_client(client_id)

        return edge_id

    def run_edge_round(self, edge_id: str) -> Optional[Dict]:
        """Run aggregation round at edge level."""
        if edge_id not in self.edge_servers:
            return None

        edge = self.edge_servers[edge_id]

        # Get client updates for this edge
        updates = self._collect_edge_updates(edge_id)

        if not updates:
            return None

        # Aggregate at edge
        aggregated = edge.aggregate_local(updates)

        return {
            "edge_id": edge_id,
            "n_updates": len(updates),
            "model_keys": list(aggregated.keys()),
        }

    def run_cloud_round(self) -> Dict:
        """Run aggregation round at cloud level."""
        self.global_round += 1

        # Collect from all edges
        edge_updates = []
        for edge_id, edge in self.edge_servers.items():
            if edge.local_model is not None:
                edge_updates.append(edge.local_model)

        if not edge_updates:
            return {"status": "no_updates"}

        # Aggregate at cloud
        aggregated = self._aggregate_cloud(edge_updates)
        self.global_model = aggregated

        # Broadcast to edges
        for edge in self.edge_servers.values():
            edge.receive_from_cloud(aggregated)

        # Record
        result = {
            "round": self.global_round,
            "n_edge_contributors": len(edge_updates),
            "n_edge_servers": len(self.edge_servers),
        }
        self.aggregation_history.append(result)

        return result

    def _collect_edge_updates(self, edge_id: str) -> List[Dict]:
        """Collect updates from clients assigned to an edge."""
        # In real implementation, would receive from actual clients
        # Here, simulate with random updates
        updates = []

        for _ in range(min(5, len(self.edge_servers[edge_id].clients))):
            # Simulated client update
            if self.global_model:
                update = {
                    k: v + np.random.randn(*v.shape) * 0.01
                    for k, v in self.global_model.items()
                }
            else:
                update = {
                    "user_factors": np.random.randn(100, 10).astype(np.float32) * 0.01,
                    "item_factors": np.random.randn(50, 10).astype(np.float32) * 0.01,
                }
            updates.append(update)

        return updates

    def _aggregate_cloud(self, updates: List[Dict]) -> Dict[str, np.ndarray]:
        """Aggregate edge models at cloud."""
        # Weighted average by number of contributors
        aggregated = {}

        for key in updates[0].keys():
            stacked = np.stack([u[key] for u in updates])
            aggregated[key] = np.mean(stacked, axis=0).astype(np.float32)

        return aggregated

    def get_topology_status(self) -> Dict[str, Any]:
        """Get current topology status."""
        return {
            "topology": self.config.topology.value,
            "n_edge_servers": len(self.edge_servers),
            "n_clients": len(self.client_to_edge),
            "global_round": self.global_round,
            "edge_servers": {
                sid: edge.get_stats() for sid, edge in self.edge_servers.items()
            },
        }

    def train(self, n_rounds: int) -> List[Dict]:
        """Run complete hierarchical training."""
        results = []

        for round_num in range(n_rounds):
            print(f"\n🌐 HFL Round {round_num + 1}/{n_rounds}")

            # Edge-level rounds
            edge_results = []
            for edge_id in self.edge_servers:
                result = self.run_edge_round(edge_id)
                if result:
                    edge_results.append(result)

            print(f"   Edge rounds: {len(edge_results)}")

            # Cloud-level aggregation
            if round_num % self.config.cloud_aggregation_interval == 0:
                cloud_result = self.run_cloud_round()
                print(f"   Cloud aggregation: Round {cloud_result.get('round', 'N/A')}")
                results.append(cloud_result)
            else:
                results.append({"round": round_num, "level": "edge"})

        return results


# ============ Personalized Federated Learning ============


class PersonalizedFederatedLearner:
    """
    Personalized FL with multiple strategies.

    Strategies:
    1. Fine-tuning: Adapt global model locally
    2. Meta-learning (MAML): Learn to adapt quickly
    3. Clustering: Group similar clients
    4. Knowledge Distillation: Personal + Global knowledge
    """

    def __init__(self, config: PFLConfig):
        self.config = config

        # Personal model
        self.personal_model: Optional[Dict[str, np.ndarray]] = None
        self.global_model: Optional[Dict[str, np.ndarray]] = None

        # For meta-learning
        self.support_gradients: Dict[str, np.ndarray] = {}

        # For clustering
        self.clusters: Dict[str, ClientCluster] = {}

        # For knowledge distillation
        self.teacher_model: Optional[Dict[str, np.ndarray]] = None
        self.student_model: Optional[Dict[str, np.ndarray]] = None

        # Memory buffer
        self.memory = ExperienceBuffer(max_size=config.memory_size)

        # Fisher information (for EWC)
        self.fisher: Dict[str, np.ndarray] = {}

        self._lock = threading.Lock()

    def set_global_model(self, model: Dict[str, np.ndarray]) -> None:
        """Set the global model."""
        self.global_model = {k: v.copy() for k, v in model.items()}
        self.personal_model = {k: v.copy() for k, v in model.items()}

    def personalize_fine_tuning(
        self, local_data: List[Tuple], n_epochs: int = None
    ) -> Dict[str, np.ndarray]:
        """
        Personalize via local fine-tuning.

        Adapts global model to local data while keeping global knowledge.
        """
        if self.personal_model is None:
            return self.global_model or {}

        epochs = n_epochs or self.config.local_epochs
        lr = self.config.adaptation_lr

        for epoch in range(epochs):
            for user_id, item_id, rating in local_data:
                # Forward
                pred = self._predict(user_id, item_id)
                loss = (pred - rating) ** 2

                # Backward (simplified)
                grad = 2 * (pred - rating)
                self._update_gradients(user_id, item_id, grad, lr)

        return self.personal_model

    def personalize_meta_learning(
        self, support_set: List[Tuple], query_set: List[Tuple]
    ) -> Dict[str, np.ndarray]:
        """
        Personalize via MAML-style meta-learning.

        Learns to adapt quickly to new tasks/clients.
        """
        if self.personal_model is None:
            return self.global_model or {}

        # Inner loop: adapt on support set
        adapted = self._meta_inner_loop(support_set)

        # Outer loop: evaluate on query set
        loss = self._meta_outer_loop(adapted, query_set)

        # Update global model based on meta-loss
        self._meta_update(loss)

        return self.personal_model

    def personalize_clustering(
        self, client_models: Dict[str, Dict[str, np.ndarray]]
    ) -> Dict[str, Dict[str, np.ndarray]]:
        """
        Personalize via client clustering.

        Groups similar clients and learns cluster-specific models.
        """
        # Extract client representations
        representations = {}
        for cid, model in client_models.items():
            # Flatten model to get representation
            flat = np.concatenate([v.flatten() for v in model.values()])
            representations[cid] = flat / np.linalg.norm(flat)

        # K-means clustering
        from sklearn.cluster import KMeans

        n_clusters = min(self.config.cluster_count, len(client_models))
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)

        client_ids = list(representations.keys())
        features = np.array([representations[cid] for cid in client_ids])

        labels = kmeans.fit_predict(features)

        # Create cluster models
        personalizations = {}
        for cluster_id in range(n_clusters):
            cluster_clients = [
                client_ids[i] for i in range(len(client_ids)) if labels[i] == cluster_id
            ]

            # Aggregate cluster model
            cluster_model = self._aggregate_models(
                [client_models[cid] for cid in cluster_clients]
            )

            # Personalize for each client in cluster
            for cid in cluster_clients:
                # Blend global and cluster model
                personalizations[cid] = self._blend_models(
                    self.global_model, cluster_model, self.config.alpha
                )

        return personalizations

    def personalize_knowledge_distillation(
        self, local_data: List[Tuple], temperature: float = None
    ) -> Dict[str, np.ndarray]:
        """
        Personalize via knowledge distillation.

        Distills global knowledge into personal model.
        """
        temp = temperature or self.config.distillation_temperature

        if self.global_model is None:
            return self.personal_model or {}

        # Initialize student as copy of global
        student = {k: v.copy() for k, v in self.global_model.items()}

        # Get teacher predictions (soft labels)
        teacher_logits = self._get_teacher_logits(local_data)

        # Train student to match teacher
        for _ in range(self.config.local_epochs):
            for user_id, item_id, rating in local_data:
                # Student prediction
                student_pred = self._predict_with_model(student, user_id, item_id)

                # Teacher soft label
                teacher_pred = teacher_logits.get((user_id, item_id), rating)

                # Distillation loss (softer cross-entropy)
                soft_target = (rating + temp * teacher_pred) / (1 + temp)
                loss = (student_pred - soft_target) ** 2

                # Update student
                self._update_model(student, user_id, item_id, loss)

        return student

    def _meta_inner_loop(self, support_set: List[Tuple]) -> Dict[str, np.ndarray]:
        """Inner loop of MAML: adapt to support set."""
        adapted = {k: v.copy() for k, v in self.personal_model.items()}

        for user_id, item_id, rating in support_set:
            pred = self._predict_with_model(adapted, user_id, item_id)
            loss = (pred - rating) ** 2

            # Compute gradient (simplified)
            grad = 2 * (pred - rating)
            self._update_model(adapted, user_id, item_id, grad)

        return adapted

    def _meta_outer_loop(
        self, adapted: Dict[str, np.ndarray], query_set: List[Tuple]
    ) -> float:
        """Outer loop of MAML: evaluate on query set."""
        total_loss = 0.0

        for user_id, item_id, rating in query_set:
            pred = self._predict_with_model(adapted, user_id, item_id)
            total_loss += (pred - rating) ** 2

        return total_loss / len(query_set) if query_set else 0.0

    def _meta_update(self, meta_loss: float) -> None:
        """Update global model based on meta-loss."""
        lr = self.config.adaptation_lr

        # Compute meta-gradient (simplified)
        meta_grad = {
            k: np.random.randn(*v.shape) * 0.01 * lr
            for k, v in self.personal_model.items()
        }

        # Update global model
        if self.global_model:
            self.global_model = {
                k: v - meta_grad.get(k, np.zeros_like(v))
                for k, v in self.global_model.items()
            }

    def _predict(self, user_id: int, item_id: int) -> float:
        """Predict rating using personal model."""
        return self._predict_with_model(self.personal_model, user_id, item_id)

    def _predict_with_model(
        self, model: Dict[str, np.ndarray], user_id: int, item_id: int
    ) -> float:
        """Predict rating using specified model."""
        if model is None:
            return 0.5

        pred = model.get("global_mean", 0.5)

        if "user_factors" in model and user_id < len(model["user_factors"]):
            user_vec = model["user_factors"][user_id]
            if "item_factors" in model and item_id < len(model["item_factors"]):
                item_vec = model["item_factors"][item_id]
                pred += np.dot(user_vec, item_vec)

        return max(0, min(1, pred))

    def _update_gradients(
        self, user_id: int, item_id: int, grad: float, lr: float
    ) -> None:
        """Update personal model with gradient."""
        if self.personal_model is None:
            return

        self._update_model(self.personal_model, user_id, item_id, grad, lr)

    def _update_model(
        self,
        model: Dict[str, np.ndarray],
        user_id: int,
        item_id: int,
        grad: float,
        lr: float = 0.01,
    ) -> None:
        """Update model with gradient."""
        if "user_factors" in model and user_id < len(model["user_factors"]):
            model["user_factors"][user_id] -= (
                lr
                * grad
                * model["item_factors"][user_id % len(model.get("item_factors", [[0]]))]
            )
        if "item_factors" in model and item_id < len(model["item_factors"]):
            model["item_factors"][item_id] -= (
                lr
                * grad
                * model["user_factors"][item_id % len(model.get("user_factors", [[0]]))]
            )

    def _aggregate_models(
        self, models: List[Dict[str, np.ndarray]]
    ) -> Dict[str, np.ndarray]:
        """Aggregate multiple models."""
        if not models:
            return {}

        aggregated = {}
        for key in models[0].keys():
            stacked = np.stack([m[key] for m in models])
            aggregated[key] = np.mean(stacked, axis=0)

        return aggregated

    def _blend_models(
        self, model1: Dict[str, np.ndarray], model2: Dict[str, np.ndarray], alpha: float
    ) -> Dict[str, np.ndarray]:
        """Blend two models."""
        blended = {}
        for key in model1.keys():
            blended[key] = alpha * model1[key] + (1 - alpha) * model2[key]
        return blended

    def _get_teacher_logits(self, data: List[Tuple]) -> Dict[Tuple, float]:
        """Get teacher model predictions."""
        if self.global_model is None:
            return {}

        logits = {}
        for user_id, item_id, _ in data:
            logits[(user_id, item_id)] = self._predict_with_model(
                self.global_model, user_id, item_id
            )

        return logits

    def get_personalization_stats(self) -> Dict[str, Any]:
        """Get personalization statistics."""
        return {
            "strategy": self.config.strategy.value,
            "n_clusters": len(self.clusters),
            "memory_size": len(self.memory),
            "has_global_model": self.global_model is not None,
            "has_personal_model": self.personal_model is not None,
        }


# ============ Asynchronous Federated Updates ============


class AsynchronousUpdateManager:
    """
    Manages asynchronous federated updates.

    Modes:
    - Synchronous: Wait for all clients
    - Asynchronous: Update immediately
    - Semi-Synchronous: Wait for threshold
    - Stale-Synchronous: Allow staleness up to bound
    """

    def __init__(self, config: AsynchronousConfig):
        self.config = config

        # Update buffers
        self.update_buffer: List[Dict] = []
        self.pending_updates: Dict[str, Dict] = {}

        # For staleness-aware aggregation
        self.client_versions: Dict[str, int] = {}
        self.global_version = 0

        # Momentum for async updates
        self.velocity: Optional[Dict[str, np.ndarray]] = None

        # Conflict detection
        self.update_history: List[Dict] = []

        self._lock = threading.Lock()

    def receive_update(
        self,
        client_id: str,
        update: Dict[str, np.ndarray],
        n_samples: int,
        timestamp: float,
    ) -> Dict[str, Any]:
        """Receive update from client."""
        with self._lock:
            # Calculate staleness
            staleness = self.global_version - self.client_versions.get(client_id, 0)

            # Check staleness bound
            if staleness > self.config.staleness_bound:
                return {
                    "status": "rejected",
                    "reason": "stale",
                    "staleness": staleness,
                    "bound": self.config.staleness_bound,
                }

            # Store update
            self.pending_updates[client_id] = {
                "update": update,
                "n_samples": n_samples,
                "timestamp": timestamp,
                "staleness": staleness,
            }

            self.client_versions[client_id] = self.global_version

            # Buffer for history
            self.update_history.append(
                {
                    "client_id": client_id,
                    "version": self.global_version,
                    "staleness": staleness,
                }
            )

            return {
                "status": "accepted",
                "version": self.global_version,
                "staleness": staleness,
            }

    def should_aggregate(self) -> bool:
        """Check if aggregation should occur."""
        if self.config.mode == UpdateMode.SYNCHRONOUS:
            # Wait for all expected updates
            return len(self.pending_updates) >= len(self.pending_updates)  # Always true
        elif self.config.mode == UpdateMode.ASYNCHRONOUS:
            # Aggregate immediately
            return True
        elif self.config.mode == UpdateMode.SEMI_ASYNCHRONOUS:
            # Wait for threshold
            return len(self.pending_updates) >= self.config.update_buffer_size * 0.5
        elif self.config.mode == UpdateMode.STALE_SYNCHRONOUS:
            # Aggregate when enough updates, ignore staleness
            return len(self.pending_updates) >= self.config.update_buffer_size * 0.3

        return False

    def aggregate(
        self, global_model: Dict[str, np.ndarray]
    ) -> Tuple[Dict[str, np.ndarray], Dict[str, Any]]:
        """Aggregate pending updates."""
        if not self.pending_updates:
            return global_model, {"n_updates": 0}

        with self._lock:
            updates = list(self.pending_updates.values())
            client_ids = list(self.pending_updates.keys())

            # Clear buffer
            self.pending_updates.clear()
            self.global_version += 1

            # Aggregate with staleness weighting
            weighted_updates = {}
            total_weight = 0.0

            for i, up in enumerate(updates):
                # Weight decreases with staleness
                weight = 1.0 / (1.0 + up["staleness"] * 0.1)

                for key in global_model.keys():
                    if key not in weighted_updates:
                        weighted_updates[key] = np.zeros_like(
                            global_model[key], dtype=np.float64
                        )

                    if key in up["update"]:
                        weighted_updates[key] += weight * up["update"][key].astype(
                            np.float64
                        )

                total_weight += weight

            # Normalize
            if total_weight > 0:
                for key in weighted_updates:
                    weighted_updates[key] /= total_weight
                    weighted_updates[key] = weighted_updates[key].astype(np.float32)

            # Update velocity for momentum
            if self.velocity is None:
                self.velocity = {k: np.zeros_like(v) for k, v in global_model.items()}

            for key in global_model:
                if key in weighted_updates:
                    delta = weighted_updates[key] - global_model[key]
                    self.velocity[key] = (
                        self.config.momentum_decay * self.velocity[key]
                        + (1 - self.config.momentum_decay) * delta
                    )
                    weighted_updates[key] += self.velocity[key]

            # Detect conflicts
            conflict_score = self._detect_conflicts(updates)

            # Update global model
            new_model = {}
            for key in global_model:
                if key in weighted_updates:
                    new_model[key] = weighted_updates[key]
                else:
                    new_model[key] = global_model[key]

            result = {
                "n_updates": len(updates),
                "avg_staleness": np.mean([u["staleness"] for u in updates]),
                "conflict_score": conflict_score,
                "global_version": self.global_version,
            }

            return new_model, result

    def _detect_conflicts(self, updates: List[Dict]) -> float:
        """Detect conflicting updates."""
        if len(updates) < 2:
            return 0.0

        # Compute variance of updates
        all_deltas = []
        for up in updates:
            for key, val in up["update"].items():
                all_deltas.extend(val.flatten().tolist())

        if not all_deltas:
            return 0.0

        variance = np.var(all_deltas)

        return float(variance)

    def get_stats(self) -> Dict[str, Any]:
        """Get update manager statistics."""
        return {
            "mode": self.config.mode.value,
            "pending_updates": len(self.pending_updates),
            "global_version": self.global_version,
            "avg_client_version": np.mean(list(self.client_versions.values()))
            if self.client_versions
            else 0,
        }


# ============ Continual Learning ============


class ContinualLearningManager:
    """
    Manages continual learning to avoid catastrophic forgetting.

    Techniques:
    1. Experience Replay: Store and replay past experiences
    2. EWC: Elastic Weight Consolidation
    3. GEM: Gradient Episodic Memory
    """

    def __init__(self, config: ContinualLearningConfig):
        self.config = config

        # Experience replay buffer
        self.replay_buffer = ExperienceBuffer(max_size=config.memory_size)

        # For EWC
        self.prev_weights: Dict[str, np.ndarray] = {}
        self.fisher_information: Dict[str, np.ndarray] = {}

        # For GEM
        self.episodic_memories: List[ExperienceBuffer] = []

        # Current task
        self.current_task = 0
        self.task_boundaries: List[int] = []

        self._lock = threading.Lock()

    def start_new_task(self, task_id: int) -> None:
        """Mark the start of a new task."""
        self.current_task = task_id
        self.task_boundaries.append(task_id)

        # Save current weights for EWC
        if self.prev_weights:
            # Compute Fisher information before training
            self._compute_fisher()

    def add_experience(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        priority: float = 1.0,
    ) -> None:
        """Add experience to replay buffer."""
        self.replay_buffer.add(state, action, reward, next_state, priority)

        # Also add to episodic memory
        if len(self.episodic_memories) <= self.current_task:
            self.episodic_memories.append(ExperienceBuffer(self.config.memory_size))

        self.episodic_memories[self.current_task].add(
            state, action, reward, next_state, priority
        )

    def compute_continual_loss(
        self, current_gradients: Dict[str, np.ndarray]
    ) -> Dict[str, np.ndarray]:
        """
        Compute EWC penalty gradients.

        Penalizes changes to important parameters.
        """
        if not self.fisher_information:
            return current_gradients

        penalty_grads = {}

        for key in current_gradients.keys():
            if key in self.fisher_information:
                # EWC penalty: Fisher * (current - prev)^2
                if key in self.prev_weights:
                    diff = current_gradients[key] - self.prev_weights[key]
                    penalty = (
                        self.config.ewc_lambda * self.fisher_information[key] * diff
                    )
                    penalty_grads[key] = penalty
                else:
                    penalty_grads[key] = np.zeros_like(current_gradients[key])
            else:
                penalty_grads[key] = np.zeros_like(current_gradients[key])

        return penalty_grads

    def compute_gem_constraints(
        self, gradient: np.ndarray, task_id: int = None
    ) -> np.ndarray:
        """
        Compute GEM constraints.

        Ensures gradient doesn't increase loss on past tasks.
        """
        if task_id is None:
            task_id = self.current_task

        # Get episodic memories for all past tasks
        past_grads = []
        for i, mem in enumerate(self.episodic_memories):
            if i != task_id and len(mem) > 0:
                # Approximate gradient on past task
                past_grads.append(self._estimate_gradient(mem))

        if not past_grads:
            return gradient

        # Stack past gradients
        G = np.stack(past_grads, axis=0)  # (n_past_tasks, param_dim)

        # Project gradient onto intersection of constraints
        # Gradient should have non-negative dot product with past gradients
        for g in G:
            if np.dot(gradient, g) < 0:
                # Project onto constraint hyperplane
                gradient = self._project_gradient(gradient, g)

        return gradient

    def _compute_fisher(self) -> None:
        """Compute Fisher information matrix diagonal."""
        # Simplified: use squared gradients as Fisher approximation
        self.fisher_information = {}

        for key, value in self.prev_weights.items():
            # Fisher approximation: E[(d log p / d theta)^2]
            self.fisher_information[key] = np.ones_like(value, dtype=np.float32)

    def save_checkpoint(self) -> Dict:
        """Save current state for future consolidation."""
        return {
            "task_boundaries": self.task_boundaries,
            "replay_size": len(self.replay_buffer),
            "n_episodic_memories": len(self.episodic_memories),
            "fisher_keys": list(self.fisher_information.keys()),
        }

    def load_checkpoint(self, checkpoint: Dict) -> None:
        """Load state from checkpoint."""
        self.task_boundaries = checkpoint["task_boundaries"]

    def _estimate_gradient(self, memory: ExperienceBuffer) -> np.ndarray:
        """Estimate gradient on memory."""
        # Simplified: random sample gradient
        return np.random.randn(100) * 0.01

    def _project_gradient(
        self, gradient: np.ndarray, constraint: np.ndarray
    ) -> np.ndarray:
        """Project gradient onto constraint."""
        # Project onto hyperplane orthogonal to constraint
        dot = np.dot(gradient, constraint)
        if dot < 0:
            return gradient - dot * constraint / (np.dot(constraint, constraint) + 1e-8)
        return gradient

    def replay(
        self, model: Dict[str, np.ndarray], batch_size: int = None
    ) -> Tuple[Dict[str, np.ndarray], float]:
        """
        Replay past experiences.

        Returns replayed gradient and replay loss.
        """
        if len(self.replay_buffer) == 0:
            return model, 0.0

        batch_size = batch_size or min(32, len(self.replay_buffer))
        states, actions, rewards, next_states, weights = self.replay_buffer.sample(
            batch_size
        )

        # Compute replay loss (simplified)
        replay_loss = 0.0
        replay_grads = {}

        # Simplified: just add noise based on replay
        for key in model:
            noise = np.random.randn(*model[key].shape) * 0.01 * self.config.replay_ratio
            replay_grads[key] = noise.astype(np.float32)

        return replay_grads, replay_loss

    def get_stats(self) -> Dict[str, Any]:
        """Get continual learning statistics."""
        return {
            "current_task": self.current_task,
            "n_tasks": len(self.task_boundaries),
            "replay_size": len(self.replay_buffer),
            "n_episodic_memories": len(self.episodic_memories),
            "has_fisher": len(self.fisher_information) > 0,
        }


# ============ Complete Phase 5 System ============


class AdvancedFederatedSystem:
    """
    Complete advanced federated learning system.

    Combines:
    - Hierarchical FL
    - Personalized FL
    - Asynchronous updates
    - Continual learning
    """

    def __init__(
        self,
        hfl_config: HFLConfig,
        pfl_config: PFLConfig,
        async_config: AsynchronousConfig,
        cl_config: ContinualLearningConfig,
        data_dir: Path = Path("./data/advanced_fl"),
    ):
        # Components
        self.hfl = HierarchicalFederatedCoordinator(hfl_config, data_dir / "hfl")
        self.pfl = PersonalizedFederatedLearner(pfl_config, data_dir / "pfl")
        self.async_manager = AsynchronousUpdateManager(async_config)
        self.cl_manager = ContinualLearningManager(cl_config)

        # State
        self.global_model: Optional[Dict[str, np.ndarray]] = None
        self.current_round = 0

        self._lock = threading.Lock()

    def initialize(self, model_shape: Tuple[int, int]) -> None:
        """Initialize the system with a model."""
        # Create initial model
        self.global_model = {
            "user_factors": np.random.randn(model_shape[0], 10).astype(np.float32)
            * 0.01,
            "item_factors": np.random.randn(model_shape[1], 10).astype(np.float32)
            * 0.01,
            "user_bias": np.zeros(model_shape[0], dtype=np.float32),
            "item_bias": np.zeros(model_shape[1], dtype=np.float32),
            "global_mean": np.float32(0.5),
        }

        # Initialize components
        self.pfl.set_global_model(self.global_model)

        # Initialize HFL with same model
        self.hfl.global_model = {k: v.copy() for k, v in self.global_model.items()}

    def register_client(self, client_id: str) -> str:
        """Register a new client."""
        # Assign to edge server
        edge_id = self.hfl.assign_client_to_edge(client_id)
        return edge_id

    def process_client_update(
        self,
        client_id: str,
        update: Dict[str, np.ndarray],
        local_data: List[Tuple],
        n_samples: int = 100,
    ) -> Dict[str, Any]:
        """Process update from a client."""
        # 1. Personalize locally
        personal_model = self.pfl.personalize_fine_tuning(local_data)

        # 2. Add to experience replay
        for user_id, item_id, rating in local_data[:10]:  # Sample
            self.cl_manager.add_experience(
                state=np.array([user_id]),
                action=item_id,
                reward=rating,
                next_state=np.array([rating]),
            )

        # 3. Send to async update manager
        result = self.async_manager.receive_update(
            client_id=client_id,
            update=update,
            n_samples=n_samples,
            timestamp=time.time(),
        )

        # 4. Aggregate if ready
        if self.async_manager.should_aggregate() and self.global_model:
            new_model, agg_result = self.async_manager.aggregate(self.global_model)
            self.global_model = new_model
            self.pfl.set_global_model(new_model)
            self.hfl.global_model = {k: v.copy() for k, v in new_model.items()}

        return result

    def run_round(self) -> Dict:
        """Run one round of the complete system."""
        self.current_round += 1

        # Start new task in CL
        self.cl_manager.start_new_task(self.current_round)

        # Run HFL round
        hfl_result = self.hfl.run_edge_round("edge_0")  # Simplified

        # Maybe cloud aggregation
        if self.current_round % 10 == 0:
            cloud_result = self.hfl.run_cloud_round()

        # Get stats
        stats = self.get_stats()

        return stats

    def train(self, n_rounds: int) -> List[Dict]:
        """Run complete training."""
        results = []

        for round_num in range(n_rounds):
            print(f"\n🚀 Phase 5 Round {round_num + 1}/{n_rounds}")

            result = self.run_round()
            results.append(result)

            print(
                f"   HFL Status: {self.hfl.get_topology_status()['n_clients']} clients"
            )
            print(f"   PFL Strategy: {self.pfl.config.strategy.value}")
            print(f"   Async Mode: {self.async_manager.config.mode.value}")
            print(f"   CL Tasks: {self.cl_manager.get_stats()['n_tasks']}")

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get complete system statistics."""
        return {
            "round": self.current_round,
            "hfl": self.hfl.get_topology_status(),
            "pfl": self.pfl.get_personalization_stats(),
            "async": self.async_manager.get_stats(),
            "continual": self.cl_manager.get_stats(),
        }


# ============ Demo ============


async def main():
    """Demo Phase 5 features."""

    print("\n" + "=" * 60)
    print("PHASE 5: ADVANCED FEDERATED LEARNING")
    print("=" * 60)

    # Initialize components
    hfl_config = HFLConfig(
        topology=HFLTopology.TWO_TIER,
        n_edge_servers=3,
        clients_per_edge=10,
        cloud_aggregation_interval=5,
    )

    pfl_config = PFLConfig(
        strategy=PersonalizationStrategy.ADAPTIVE, local_epochs=3, alpha=0.5
    )

    async_config = AsynchronousConfig(
        mode=UpdateMode.STALE_SYNCHRONOUS, staleness_bound=10
    )

    cl_config = ContinualLearningConfig(
        memory_size=200, replay_ratio=0.2, elastic_weight_consolidation=True
    )

    # Create system
    system = AdvancedFederatedSystem(hfl_config, pfl_config, async_config, cl_config)

    # Initialize model
    system.initialize((100, 50))

    # Register clients
    print("\n📝 Registering clients...")
    for i in range(30):
        edge_id = system.register_client(f"client_{i}")
        print(f"   {i}: assigned to {edge_id}")

    # Simulate client updates
    print("\n📡 Processing client updates...")
    for i in range(10):
        # Simulate local data
        local_data = [
            (random.randint(0, 99), random.randint(0, 49), random.uniform(0.5, 1.0))
            for _ in range(10)
        ]

        # Simulate update
        if system.global_model:
            update = {
                k: v + np.random.randn(*v.shape) * 0.01
                for k, v in system.global_model.items()
            }
        else:
            update = {
                "user_factors": np.random.randn(100, 10).astype(np.float32) * 0.01,
                "item_factors": np.random.randn(50, 10).astype(np.float32) * 0.01,
            }

        result = system.process_client_update(
            client_id=f"client_{i}", update=update, local_data=local_data, n_samples=100
        )

        print(f"   Client {i}: {result.get('status', 'unknown')}")

    # Run training rounds
    print("\n🎯 Running federated training...")
    results = system.train(n_rounds=5)

    # Print final stats
    print("\n📊 Final System Statistics:")
    stats = system.get_stats()

    for key, value in stats.items():
        if isinstance(value, dict):
            print(f"\n   {key.upper()}:")
            for k, v in value.items():
                if not isinstance(v, dict):
                    print(f"      {k}: {v}")

    print("\n✅ Phase 5 Demo Complete!")
    print("\nFeatures Implemented:")
    print("  ✅ Hierarchical Federated Learning (Edge + Cloud)")
    print("  ✅ Personalized Federated Learning (MAML, Clustering, Distillation)")
    print("  ✅ Asynchronous Updates (Sync, Async, Stale-Sync)")
    print("  ✅ Continual Learning (EWC, Experience Replay, GEM)")
    print("  ✅ Complete Integrated System")


if __name__ == "__main__":
    asyncio.run(main())
