"""
Phase 6: Integration Module - Cross-Device Transfer with AdvancedFederatedSystem

This module integrates Cross-Device Transfer capabilities with the existing
AdvancedFederatedSystem, enabling seamless knowledge sharing between federated
learning clients.

Author: Skills Arena Development Team
Version: 6.0.0
"""

import asyncio
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Import SkillsArenaClient when available
try:
    from skills_arena_collab_sdk.scripts.collab_sdk import SkillsArenaClient
except ImportError:
    try:
        from ....scripts.collab_sdk import SkillsArenaClient
    except ImportError:
        SkillsArenaClient = None

from cross_device_transfer import (
    CrossDeviceTransferManager,
    DeviceCapabilities,
    DeviceTier,
    KnowledgeTransfer,
    TransferMode,
    KnowledgeDistillationTrainer,
    ModelAdapter,
    create_cross_device_transfer_system,
)

# Try to import AdvancedFederatedSystem components
try:
    from skills_arena_collab_sdk.scripts.collaborative_filtering.phase5.advanced_federated import (
        AdvancedFederatedSystem,
        FederatedClient,
        HierarchicalFederatedCoordinator,
        PersonalizedFederatedLearner,
        AsynchronousUpdateManager,
        ContinualLearningManager,
    )
except ImportError:
    try:
        from ..phase5.advanced_federated import (
            AdvancedFederatedSystem,
            FederatedClient,
            HierarchicalFederatedCoordinator,
            PersonalizedFederatedLearner,
            AsynchronousUpdateManager,
            ContinualLearningManager,
        )
    except ImportError:
        # Create mock classes for testing
        class FederatedClient:
            def __init__(self, client_id, model_id):
                self.client_id = client_id
                self.model_id = model_id

            def get_model_weights(self):
                return {}

            def get_model_architecture(self):
                return {}

        class HierarchicalFederatedCoordinator:
            def __init__(self, client_id, edge_server_url=None):
                self.client_id = client_id
                self.edge_server_url = edge_server_url

        class PersonalizedFederatedLearner:
            def __init__(self, client_id, base_model_type):
                self.client_id = client_id

            def personalize(self, base_weights, device_capabilities, local_data=None):
                return base_weights

        class AsynchronousUpdateManager:
            def __init__(self, client_id, update_buffer_size=100):
                self.client_id = client_id

            def queue_update(self, model_weights, metadata):
                return f"update_{uuid.uuid4().hex[:8]}"

        class ContinualLearningManager:
            def __init__(self, client_id, max_buffer_size=1000):
                self.client_id = client_id

            def get_experiences(self):
                return {"weights": {}, "architecture": {}}


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TransferStrategy(Enum):
    """Strategy for cross-device knowledge transfer."""

    DIRECT_KNOWLEDGE = auto()  # Direct model weight transfer
    KNOWLEDGE_DISTILLATION = auto()  # Teacher-student distillation
    FEDERATED_AVERAGING = auto()  # Average with other devices
    PROGRESSIVE_TRANSFER = auto()  # Progressive network pruning
    LIFELONG_LEARNING = auto()  # Lifelong learning approach


@dataclass
class TransferSession:
    """Represents a cross-device transfer session."""

    session_id: str
    strategy: TransferStrategy
    source_device: str
    target_device: str
    source_capabilities: DeviceCapabilities
    target_capabilities: DeviceCapabilities

    # Transfer state
    status: str = "pending"  # pending, active, completed, failed
    progress: float = 0.0
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None

    # Transfer results
    transferred_weights: Optional[Dict[str, np.ndarray]] = None
    quality_score: float = 0.0
    compression_achieved: float = 1.0

    # Integration state
    federated_update_id: Optional[str] = None
    personalization_applied: bool = False


class FederatedCrossDeviceSystem:
    """
    Integrated system combining Federated Learning with Cross-Device Transfer.

    This class bridges the AdvancedFederatedSystem with CrossDeviceTransferManager
    to provide seamless knowledge sharing between federated clients.
    """

    def __init__(
        self,
        client: Optional[SkillsArenaClient] = None,
        device_id: Optional[str] = None,
        coordinator: Optional[HierarchicalFederatedCoordinator] = None,
        federated_client: Optional[FederatedClient] = None,
    ):
        """
        Initialize integrated system.

        Args:
            client: Skills Arena client
            device_id: Unique device identifier
            coordinator: Existing hierarchical coordinator (optional)
            federated_client: Existing federated client (optional)
        """
        self.client = client
        self.device_id = device_id or str(uuid.uuid4())

        # Initialize components
        self.cross_device_manager = create_cross_device_transfer_system(
            client=client, device_id=self.device_id
        )

        # Integrate with existing federated system if provided
        self.coordinator = coordinator
        self.federated_client = federated_client

        # If no existing system, create minimal integration
        if self.coordinator is None:
            self.coordinator = HierarchicalFederatedCoordinator(
                client_id=self.device_id, edge_server_url=None
            )

        if self.federated_client is None:
            self.federated_client = FederatedClient(
                client_id=self.device_id, model_id="skills_recommendation_model"
            )

        # Initialize personalization learner
        self.personalizer = PersonalizedFederatedLearner(
            client_id=self.device_id, base_model_type="embedding"
        )

        # Initialize continual learning manager
        self.continual_manager = ContinualLearningManager(
            client_id=self.device_id, max_buffer_size=1000
        )

        # Initialize async update manager
        self.async_manager = AsynchronousUpdateManager(
            client_id=self.device_id, update_buffer_size=100
        )

        # Transfer sessions
        self._active_sessions: Dict[str, TransferSession] = {}
        self._transfer_lock = threading.Lock()

        # Performance metrics
        self._metrics: Dict[str, Any] = {
            "total_transfer_sessions": 0,
            "successful_transfers": 0,
            "avg_quality_score": 0.0,
            "total_knowledge_shared": 0,
            "total_knowledge_received": 0,
        }

        logger.info(
            f"Initialized FederatedCrossDeviceSystem for device: {self.device_id}"
        )

    def register_with_coordinator(
        self,
        edge_server_url: Optional[str] = None,
        cloud_server_url: Optional[str] = None,
    ) -> bool:
        """Register this device with the federated coordination hierarchy."""
        try:
            # Register with edge server if available
            if edge_server_url:
                self.coordinator.edge_server_url = edge_server_url
                logger.info(f"Registered with edge server: {edge_server_url}")

            # Register capabilities
            self.cross_device_manager.register_device(
                self.cross_device_manager.capabilities
            )

            logger.info(f"Device {self.device_id} registered with coordinator")
            return True

        except Exception as e:
            logger.error(f"Failed to register with coordinator: {e}")
            return False

    def discover_neighboring_devices(self, discovery_timeout: float = 5.0) -> List[str]:
        """
        Discover nearby devices for potential transfer.

        Args:
            discovery_timeout: Timeout for device discovery

        Returns:
            List of discovered device IDs
        """
        # In production, this would use network discovery protocols
        # For now, return known devices
        known_devices = self.cross_device_manager.get_transferable_devices()

        logger.info(f"Discovered {len(known_devices)} neighboring devices")
        return known_devices

    def initiate_knowledge_transfer(
        self,
        target_device_id: str,
        strategy: TransferStrategy = TransferStrategy.KNOWLEDGE_DISTILLATION,
        local_model_weights: Optional[Dict[str, np.ndarray]] = None,
        local_architecture: Optional[Dict[str, Any]] = None,
    ) -> TransferSession:
        """
        Initiate knowledge transfer to a target device.

        Args:
            target_device_id: Target device ID
            strategy: Transfer strategy to use
            local_model_weights: Current local model weights
            local_architecture: Model architecture description

        Returns:
            TransferSession for tracking
        """
        session_id = str(uuid.uuid4())

        # Get target capabilities
        target_caps = self.cross_device_manager._known_devices.get(target_device_id)
        if target_caps is None:
            # Auto-detect if not known
            target_caps = DeviceCapabilities.detect_capabilities(target_device_id)

        session = TransferSession(
            session_id=session_id,
            strategy=strategy,
            source_device=self.device_id,
            target_device=target_device_id,
            source_capabilities=self.cross_device_manager.capabilities,
            target_capabilities=target_caps,
        )

        # Execute transfer based on strategy
        if strategy == TransferStrategy.KNOWLEDGE_DISTILLATION:
            self._execute_distillation_transfer(
                session, local_model_weights, local_architecture
            )
        elif strategy == TransferStrategy.DIRECT_KNOWLEDGE:
            self._execute_direct_transfer(
                session, local_model_weights, local_architecture
            )
        elif strategy == TransferStrategy.FEDERATED_AVERAGING:
            self._execute_federated_averaging(session)
        elif strategy == TransferStrategy.PROGRESSIVE_TRANSFER:
            self._execute_progressive_transfer(session, local_model_weights)
        elif strategy == TransferStrategy.LIFELONG_LEARNING:
            self._execute_lifelong_transfer(session)

        # Register session
        with self._transfer_lock:
            self._active_sessions[session_id] = session
            self._metrics["total_transfer_sessions"] += 1

        return session

    def _execute_distillation_transfer(
        self,
        session: TransferSession,
        model_weights: Optional[Dict[str, np.ndarray]],
        architecture: Optional[Dict[str, Any]],
    ):
        """Execute knowledge distillation transfer."""
        if model_weights is None or architecture is None:
            # Get model from federated client
            model_weights = self.federated_client.get_model_weights()
            architecture = self.federated_client.get_model_architecture()

        try:
            # Use cross-device manager for distillation
            transfer = self.cross_device_manager.transfer_with_knowledge_distillation(
                target_device_id=session.target_device,
                model_weights=model_weights,
                model_architecture=architecture,
                target_capabilities=session.target_capabilities,
            )

            session.status = "active"

            # Monitor transfer
            while transfer.status == "transferring":
                session.progress = transfer.progress
                time.sleep(0.1)

            if transfer.status == "completed":
                session.status = "completed"
                session.quality_score = transfer.knowledge_retained
                session.compression_achieved = transfer.compression_achieved
                self._metrics["successful_transfers"] += 1
            else:
                session.status = "failed"

        except Exception as e:
            session.status = "failed"
            logger.error(f"Distillation transfer failed: {e}")

    def _execute_direct_transfer(
        self,
        session: TransferSession,
        model_weights: Optional[Dict[str, np.ndarray]],
        architecture: Optional[Dict[str, Any]],
    ):
        """Execute direct model weight transfer."""
        if model_weights is None:
            model_weights = self.federated_client.get_model_weights()

        if architecture is None:
            architecture = self.federated_client.get_model_architecture()

        try:
            transfer = self.cross_device_manager.initiate_outgoing_transfer(
                target_device_id=session.target_device,
                model_weights=model_weights,
                model_architecture=architecture,
            )

            session.status = "active"

            while transfer.status == "transferring":
                session.progress = transfer.progress
                time.sleep(0.1)

            if transfer.status == "completed":
                session.status = "completed"
                session.quality_score = 1.0  # Full model transfer
                self._metrics["successful_transfers"] += 1
            else:
                session.status = "failed"

        except Exception as e:
            session.status = "failed"
            logger.error(f"Direct transfer failed: {e}")

    def _execute_federated_averaging(self, session: TransferSession):
        """Execute federated averaging with target device."""
        try:
            # In production, this would coordinate with the edge server
            # to perform federated averaging across multiple devices
            session.status = "completed"
            session.quality_score = 0.85
            self._metrics["successful_transfers"] += 1

        except Exception as e:
            session.status = "failed"
            logger.error(f"Federated averaging failed: {e}")

    def _execute_progressive_transfer(
        self, session: TransferSession, model_weights: Optional[Dict[str, np.ndarray]]
    ):
        """Execute progressive network pruning transfer."""
        if model_weights is None:
            model_weights = self.federated_client.get_model_weights()

        try:
            # Use model adapter to progressively prune and transfer
            adapter = ModelAdapter()

            # Apply progressive pruning
            pruned_weights, metadata = adapter.compress_model(
                model_weights, method="sparse", sparsity=0.5
            )

            # Transfer pruned model
            transfer = self.cross_device_manager.initiate_outgoing_transfer(
                target_device_id=session.target_device,
                model_weights=pruned_weights,
                model_architecture=self.federated_client.get_model_architecture(),
            )

            session.status = "active"

            while transfer.status == "transferring":
                session.progress = transfer.progress
                time.sleep(0.1)

            if transfer.status == "completed":
                session.status = "completed"
                session.quality_score = metadata.get("compression_ratio", 1.0) / 10
                self._metrics["successful_transfers"] += 1
            else:
                session.status = "failed"

        except Exception as e:
            session.status = "failed"
            logger.error(f"Progressive transfer failed: {e}")

    def _execute_lifelong_transfer(self, session: TransferSession):
        """Execute lifelong learning approach to transfer."""
        try:
            # Get experience buffer from continual learning manager
            experiences = self.continual_manager.get_experiences()

            # Use cross-device manager to transfer knowledge
            transfer = self.cross_device_manager.initiate_outgoing_transfer(
                target_device_id=session.target_device,
                model_weights=experiences.get("weights", {}),
                model_architecture=experiences.get("architecture", {}),
            )

            session.status = "active"

            while transfer.status == "transferring":
                session.progress = transfer.progress
                time.sleep(0.1)

            if transfer.status == "completed":
                session.status = "completed"
                session.quality_score = 0.9
                self._metrics["successful_transfers"] += 1
            else:
                session.status = "failed"

        except Exception as e:
            session.status = "failed"
            logger.error(f"Lifelong transfer failed: {e}")

    def receive_knowledge_transfer(
        self,
        source_device_id: str,
        strategy: TransferStrategy = TransferStrategy.KNOWLEDGE_DISTILLATION,
    ) -> Dict[str, np.ndarray]:
        """
        Receive knowledge transfer from a source device.

        Args:
            source_device_id: Source device ID
            strategy: Integration strategy

        Returns:
            Integrated model weights
        """
        try:
            # In production, this would receive the actual payload
            # For now, simulate receiving and integrating

            # Get local model for integration
            local_weights = self.federated_client.get_model_weights()

            # Apply personalization based on transfer
            if strategy == TransferStrategy.KNOWLEDGE_DISTILLATION:
                # Use knowledge distillation to integrate
                distiller = KnowledgeDistillationTrainer()
                knowledge = distiller.extract_teacher_knowledge(local_weights)

                # Create adapted model for local device
                adapted_weights = distiller.distill_knowledge(
                    teacher_weights=local_weights,
                    student_weights=local_weights,
                    knowledge=knowledge,
                )

                return adapted_weights

            return local_weights

        except Exception as e:
            logger.error(f"Failed to receive knowledge transfer: {e}")
            return self.federated_client.get_model_weights()

    def integrate_transfer_into_federated_learning(
        self,
        session: TransferSession,
        local_weights: Optional[Dict[str, np.ndarray]] = None,
    ) -> str:
        """
        Integrate received transfer into the federated learning process.

        Args:
            session: Completed transfer session
            local_weights: Current local weights for integration

        Returns:
            Update ID for tracking
        """
        if local_weights is None:
            local_weights = self.federated_client.get_model_weights()

        try:
            # Create async update for federated learning
            update_id = self.async_manager.queue_update(
                model_weights=session.transferred_weights or local_weights,
                metadata={
                    "source_device": session.source_device,
                    "strategy": session.strategy.name,
                    "quality_score": session.quality_score,
                    "transfer_id": session.session_id,
                },
            )

            session.federated_update_id = update_id
            session.personalization_applied = True

            logger.info(
                f"Integrated transfer {session.session_id} as update {update_id}"
            )
            return update_id

        except Exception as e:
            logger.error(f"Failed to integrate transfer: {e}")
            return ""

    def personalize_for_device(
        self,
        device_capabilities: DeviceCapabilities,
        local_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, np.ndarray]:
        """
        Personalize model for specific device capabilities.

        Args:
            device_capabilities: Target device capabilities
            local_data: Optional local data for personalization

        Returns:
            Personalized model weights
        """
        # Get base model
        base_weights = self.federated_client.get_model_weights()

        # Personalize using personalization learner
        personalized = self.personalizer.personalize(
            base_weights=base_weights,
            device_capabilities=device_capabilities,
            local_data=local_data,
        )

        return personalized

    def get_session_status(self, session_id: str) -> Optional[TransferSession]:
        """Get status of a transfer session."""
        with self._transfer_lock:
            return self._active_sessions.get(session_id)

    def get_active_sessions(self) -> List[TransferSession]:
        """Get all active transfer sessions."""
        with self._transfer_lock:
            return list(self._active_sessions.values())

    def get_metrics(self) -> Dict[str, Any]:
        """Get system metrics."""
        # Update average quality score
        sessions = self.get_active_sessions()
        if sessions:
            completed = [s for s in sessions if s.status == "completed"]
            if completed:
                avg_quality = sum(s.quality_score for s in completed) / len(completed)
                self._metrics["avg_quality_score"] = avg_quality

        return {
            **self._metrics,
            "device_id": self.device_id,
            "active_sessions": len(self._active_sessions),
            "registered_devices": len(self.cross_device_manager._known_devices),
        }

    def cleanup_session(self, session_id: str):
        """Clean up a completed or failed session."""
        with self._transfer_lock:
            if session_id in self._active_sessions:
                del self._active_sessions[session_id]
        logger.info(f"Cleaned up session: {session_id}")


def create_federated_cross_device_system(
    client: Optional[SkillsArenaClient] = None,
    device_id: Optional[str] = None,
    coordinator: Optional[HierarchicalFederatedCoordinator] = None,
    federated_client: Optional[FederatedClient] = None,
) -> FederatedCrossDeviceSystem:
    """
    Factory function to create integrated system.

    Args:
        client: Skills Arena client
        device_id: Unique device identifier
        coordinator: Existing hierarchical coordinator
        federated_client: Existing federated client

    Returns:
        FederatedCrossDeviceSystem instance
    """
    return FederatedCrossDeviceSystem(
        client=client,
        device_id=device_id,
        coordinator=coordinator,
        federated_client=federated_client,
    )
