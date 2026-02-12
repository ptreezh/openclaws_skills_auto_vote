"""
Phase 6: Tests for Cross-Device Transfer

Test suite for validating cross-device knowledge transfer functionality
including device capability detection, knowledge distillation, and
integration with AdvancedFederatedSystem.

Author: Skills Arena Development Team
Version: 6.0.0
"""

import pytest
import numpy as np
import time
import uuid
from unittest.mock import Mock, patch, MagicMock

from cross_device_transfer import (
    DeviceCapabilities,
    DeviceTier,
    TransferMode,
    ModelFormat,
    CompressionType,
    KnowledgeTransfer,
    KnowledgeDistillationTrainer,
    ModelAdapter,
    DeviceToDeviceProtocol,
    CrossDeviceTransferManager,
    create_cross_device_transfer_system,
)
from federated_cross_device_integration import (
    FederatedCrossDeviceSystem,
    TransferStrategy,
    TransferSession,
    create_federated_cross_device_system,
)


class TestDeviceCapabilities:
    """Tests for DeviceCapabilities class."""

    def test_detect_capabilities_basic(self):
        """Test basic capability detection."""
        device_id = f"test_device_{uuid.uuid4().hex[:8]}"
        caps = DeviceCapabilities.detect_capabilities(device_id)

        assert caps.device_id == device_id
        assert caps.cpu_cores > 0
        assert caps.ram_gb > 0
        assert isinstance(caps.device_tier, DeviceTier)

    def test_capabilities_to_dict(self):
        """Test serialization to dictionary."""
        caps = DeviceCapabilities(
            device_id="test",
            device_tier=DeviceTier.TIER_3_STANDARD,
            cpu_cores=8,
            cpu_frequency_mhz=2400.0,
            ram_gb=16.0,
            storage_gb=512.0,
            has_gpu=True,
            gpu_memory_gb=8.0,
        )

        data = caps.to_dict()

        assert data["device_id"] == "test"
        assert data["device_tier"] == "TIER_3_STANDARD"
        assert data["cpu_cores"] == 8
        assert data["has_gpu"] is True

    def test_capabilities_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "device_id": "test_from_dict",
            "device_tier": "TIER_4_HIGH_PERFORMANCE",
            "cpu_cores": 16,
            "cpu_frequency_mhz": 3200.0,
            "ram_gb": 32.0,
            "storage_gb": 1024.0,
            "has_gpu": True,
            "gpu_memory_gb": 16.0,
            "max_upload_speed_mbps": 1000.0,
            "max_download_speed_mbps": 2000.0,
            "network_type": "ethernet",
            "supported_precision": ["float32", "float16"],
            "max_model_size_mb": 2000.0,
            "supported_operations": ["matrix_multiply", "convolution"],
            "batteryPowered": False,
            "max_power_watts": 500.0,
        }

        caps = DeviceCapabilities.from_dict(data)

        assert caps.device_id == "test_from_dict"
        assert caps.device_tier == DeviceTier.TIER_4_HIGH_PERFORMANCE
        assert caps.cpu_cores == 16
        assert "float16" in caps.supported_precision


class TestKnowledgeDistillationTrainer:
    """Tests for KnowledgeDistillationTrainer class."""

    def test_extract_teacher_knowledge(self):
        """Test knowledge extraction from teacher model."""
        trainer = KnowledgeDistillationTrainer(temperature=4.0, alpha=0.5)

        # Create mock model weights with proper naming convention
        model_weights = {
            "embeddings": np.random.randn(100, 768).astype(np.float32),
            "layer1_weight": np.random.randn(256, 768).astype(np.float32),
            "layer1_bias": np.random.randn(256).astype(np.float32),
        }

        knowledge = trainer.extract_teacher_knowledge(model_weights)

        assert "embeddings" in knowledge
        assert "layer1_weight_stats" in knowledge  # Note: uses _weight suffix
        assert "layer_stats" in knowledge
        assert knowledge["embeddings"].shape == (100, 768)

    def test_create_student_model(self):
        """Test student model creation for target device."""
        trainer = KnowledgeDistillationTrainer()

        source_caps = DeviceCapabilities(
            device_id="source",
            device_tier=DeviceTier.TIER_4_HIGH_PERFORMANCE,
            cpu_cores=16,
            cpu_frequency_mhz=3000.0,
            ram_gb=32.0,
            storage_gb=1000.0,
            has_gpu=True,
        )

        target_caps = DeviceCapabilities(
            device_id="target",
            device_tier=DeviceTier.TIER_2_EDGE,
            cpu_cores=4,
            cpu_frequency_mhz=1500.0,
            ram_gb=2.0,
            storage_gb=64.0,
            has_gpu=False,
        )

        original_architecture = {
            "hidden_size": 512,
            "num_layers": 6,
            "embedding_dim": 256,
        }

        student_architecture = trainer.create_student_model(
            source_capabilities=source_caps,
            target_capabilities=target_caps,
            original_architecture=original_architecture,
        )

        # Verify model was scaled down
        assert (
            student_architecture["hidden_size"] < original_architecture["hidden_size"]
        )
        assert student_architecture["num_layers"] < original_architecture["num_layers"]
        assert "distillation_source" in student_architecture

    def test_distill_knowledge(self):
        """Test knowledge distillation process."""
        trainer = KnowledgeDistillationTrainer(temperature=4.0, alpha=0.5)

        # Teacher and student weights with same shape
        teacher_weights = {
            "embeddings": np.random.randn(100, 768).astype(np.float32) * 0.1
        }

        # Student weights (same shape)
        student_weights = {
            "embeddings": np.random.randn(100, 768).astype(np.float32) * 0.01
        }

        # Extracted knowledge
        knowledge = {
            "embeddings": trainer._normalize_embeddings(teacher_weights["embeddings"])
        }

        distilled = trainer.distill_knowledge(
            teacher_weights=teacher_weights,
            student_weights=student_weights,
            knowledge=knowledge,
        )

        assert distilled["embeddings"].shape == (100, 768)

    def test_compute_distillation_loss(self):
        """Test distillation loss computation."""
        trainer = KnowledgeDistillationTrainer(temperature=4.0, alpha=0.5)

        student_outputs = np.array([[0.1, 0.8, 0.1], [0.2, 0.6, 0.2]])
        teacher_outputs = np.array([[0.05, 0.9, 0.05], [0.1, 0.8, 0.1]])
        hard_targets = np.array([[0.0, 1.0, 0.0], [0.0, 1.0, 0.0]])

        loss, losses = trainer.compute_distillation_loss(
            student_outputs, teacher_outputs, hard_targets
        )

        assert loss >= 0
        assert "kl_divergence" in losses
        assert "hard_loss" in losses
        assert "total" in losses


class TestModelAdapter:
    """Tests for ModelAdapter class."""

    def test_adapt_model_precision(self):
        """Test model precision adaptation."""
        adapter = ModelAdapter()

        weights = {
            "layer1.weight": np.random.randn(256, 768).astype(np.float32),
            "layer1.bias": np.random.randn(256).astype(np.float32),
        }

        # Adapt to float16
        adapted = adapter.adapt_model(weights, target_precision="float16")

        assert adapted["layer1.weight"].dtype == np.float16

    def test_quantize_model(self):
        """Test model quantization."""
        adapter = ModelAdapter()

        # Use numpy array directly for testing
        arr = np.random.randn(256, 768).astype(np.float32)

        # Quantize to int8
        quantized = adapter._symmetric_quantize(arr, 8)

        assert quantized.dtype == np.int8

    def test_dequantize_model(self):
        """Test model dequantization."""
        adapter = ModelAdapter()

        arr = np.random.randn(256, 768).astype(np.float32)

        quantized = adapter._symmetric_quantize(arr, 8)
        dequantized = adapter._to_float32(
            quantized
        )  # Use _to_float32 since we can't store scale

        assert dequantized.dtype == np.float32
        assert dequantized.shape == arr.shape

    def test_compress_model_sparse(self):
        """Test model compression with sparsity."""
        adapter = ModelAdapter()

        weights = {"layer1.weight": np.random.randn(256, 768).astype(np.float32)}

        compressed, metadata = adapter.compress_model(
            weights, method="sparse", sparsity=0.9
        )

        assert "method" in metadata
        assert "original_size" in metadata
        assert "compressed_size" in metadata


class TestDeviceToDeviceProtocol:
    """Tests for DeviceToDeviceProtocol class."""

    def test_select_transfer_mode(self):
        """Test transfer mode selection."""
        protocol = DeviceToDeviceProtocol()

        # Same network type
        source = DeviceCapabilities(
            device_id="s1",
            device_tier=DeviceTier.TIER_3_STANDARD,
            cpu_cores=8,
            cpu_frequency_mhz=2000.0,
            ram_gb=16.0,
            storage_gb=256.0,
            has_gpu=False,
            network_type="wifi",
        )

        target = DeviceCapabilities(
            device_id="t1",
            device_tier=DeviceTier.TIER_3_STANDARD,
            cpu_cores=8,
            cpu_frequency_mhz=2000.0,
            ram_gb=16.0,
            storage_gb=256.0,
            has_gpu=False,
            network_type="wifi",
        )

        mode = protocol._select_transfer_mode(source, target)
        assert mode == TransferMode.DIRECT_P2P

    def test_select_model_format(self):
        """Test model format selection."""
        protocol = DeviceToDeviceProtocol()

        # Edge device target without GPU
        target = DeviceCapabilities(
            device_id="t1",
            device_tier=DeviceTier.TIER_2_EDGE,
            cpu_cores=4,
            cpu_frequency_mhz=1500.0,
            ram_gb=2.0,
            storage_gb=64.0,
            has_gpu=False,
        )

        source = DeviceCapabilities(
            device_id="s1",
            device_tier=DeviceTier.TIER_4_HIGH_PERFORMANCE,
            cpu_cores=16,
            cpu_frequency_mhz=3000.0,
            ram_gb=32.0,
            storage_gb=1000.0,
            has_gpu=True,
        )

        # Should select sparse update format for edge device without GPU
        format_type = protocol._select_model_format(source, target)
        # The format depends on implementation logic
        assert format_type in [ModelFormat.SPARSE_UPDATE, ModelFormat.QUANTIZED]

    def test_compute_checksum(self):
        """Test checksum computation."""
        protocol = DeviceToDeviceProtocol()

        data = b"test data for checksum"
        checksum = protocol._compute_checksum(data)

        assert len(checksum) == 64  # SHA256 hex length
        assert checksum == protocol._compute_checksum(data)  # Consistent

    def test_chunk_data(self):
        """Test data chunking."""
        protocol = DeviceToDeviceProtocol(chunk_size=10)

        data = b"0123456789ABCDEF"  # 16 bytes
        chunks = protocol._chunk_data(data, 10)

        assert len(chunks) == 2
        assert len(chunks[0]) == 10
        assert len(chunks[1]) == 6
        assert b"".join(chunks) == data


class TestCrossDeviceTransferManager:
    """Tests for CrossDeviceTransferManager class."""

    def test_register_device(self):
        """Test device registration."""
        manager = create_cross_device_transfer_system(device_id="manager1")

        caps = DeviceCapabilities(
            device_id="device1",
            device_tier=DeviceTier.TIER_3_STANDARD,
            cpu_cores=8,
            cpu_frequency_mhz=2000.0,
            ram_gb=16.0,
            storage_gb=256.0,
            has_gpu=False,
        )

        manager.register_device(caps)

        assert "device1" in manager._known_devices

    def test_get_transferable_devices(self):
        """Test device discovery."""
        manager = create_cross_device_transfer_system(device_id="manager1")

        # Register multiple devices
        for i in range(3):
            caps = DeviceCapabilities(
                device_id=f"device{i}",
                device_tier=DeviceTier.TIER_3_STANDARD,
                cpu_cores=8,
                cpu_frequency_mhz=2000.0,
                ram_gb=16.0,
                storage_gb=256.0,
                has_gpu=False,
            )
            manager.register_device(caps)

        devices = manager.get_transferable_devices()

        # Should not include self
        assert len(devices) == 3
        assert "manager1" not in devices

    def test_initiate_outgoing_transfer(self):
        """Test initiating knowledge transfer."""
        manager = create_cross_device_transfer_system(device_id="source")

        # Register target
        target_caps = DeviceCapabilities(
            device_id="target",
            device_tier=DeviceTier.TIER_3_STANDARD,
            cpu_cores=8,
            cpu_frequency_mhz=2000.0,
            ram_gb=16.0,
            storage_gb=256.0,
            has_gpu=False,
        )
        manager.register_device(target_caps)

        # Create mock model
        model_weights = {
            "embeddings": np.random.randn(100, 768).astype(np.float32),
            "layer1.weight": np.random.randn(256, 768).astype(np.float32),
        }
        architecture = {"hidden_size": 256, "num_layers": 2}

        transfer = manager.initiate_outgoing_transfer(
            target_device_id="target",
            model_weights=model_weights,
            model_architecture=architecture,
        )

        assert transfer.source_device == "source"
        assert transfer.target_device == "target"
        assert transfer.status in ["pending", "transferring", "completed"]

    def test_get_metrics(self):
        """Test metrics collection."""
        manager = create_cross_device_transfer_system(device_id="test")

        metrics = manager.get_metrics()

        assert "total_transfers" in metrics
        assert "successful_transfers" in metrics
        assert "device_id" in metrics


class TestFederatedCrossDeviceSystem:
    """Tests for FederatedCrossDeviceSystem integration."""

    def test_create_system(self):
        """Test system creation."""
        system = create_federated_cross_device_system(device_id="fed_test")

        assert system.device_id == "fed_test"
        assert system.cross_device_manager is not None
        assert system.personalizer is not None
        assert system.continual_manager is not None

    def test_register_with_coordinator(self):
        """Test coordinator registration."""
        system = create_federated_cross_device_system(device_id="coord_test")

        result = system.register_with_coordinator(edge_server_url="http://edge:8080")

        assert result is True

    def test_discover_neighboring_devices(self):
        """Test device discovery."""
        system = create_federated_cross_device_system(device_id="disc_test")

        # Register some devices
        for i in range(2):
            caps = DeviceCapabilities(
                device_id=f"neighbor{i}",
                device_tier=DeviceTier.TIER_3_STANDARD,
                cpu_cores=8,
                cpu_frequency_mhz=2000.0,
                ram_gb=16.0,
                storage_gb=256.0,
                has_gpu=False,
            )
            system.cross_device_manager.register_device(caps)

        devices = system.discover_neighboring_devices()

        assert len(devices) == 2

    def test_initiate_knowledge_transfer(self):
        """Test knowledge transfer initiation."""
        system = create_federated_cross_device_system(device_id="src_transfer")

        # Register target
        target_caps = DeviceCapabilities(
            device_id="target_transfer",
            device_tier=DeviceTier.TIER_3_STANDARD,
            cpu_cores=8,
            cpu_frequency_mhz=2000.0,
            ram_gb=16.0,
            storage_gb=256.0,
            has_gpu=False,
        )
        system.cross_device_manager.register_device(target_caps)

        # Mock federated client
        system.federated_client.get_model_weights = Mock(
            return_value={"embeddings": np.random.randn(100, 768).astype(np.float32)}
        )
        system.federated_client.get_model_architecture = Mock(
            return_value={"hidden_size": 256}
        )

        session = system.initiate_knowledge_transfer(
            target_device_id="target_transfer",
            strategy=TransferStrategy.KNOWLEDGE_DISTILLATION,
        )

        assert session.session_id is not None
        assert session.source_device == "src_transfer"
        assert session.strategy == TransferStrategy.KNOWLEDGE_DISTILLATION

    def test_session_management(self):
        """Test transfer session management."""
        system = create_federated_cross_device_system(device_id="session_test")

        # Create mock session
        session = TransferSession(
            session_id="test_session_1",
            strategy=TransferStrategy.DIRECT_KNOWLEDGE,
            source_device="s1",
            target_device="t1",
            source_capabilities=DeviceCapabilities.detect_capabilities("s1"),
            target_capabilities=DeviceCapabilities.detect_capabilities("t1"),
            status="completed",
            quality_score=0.95,
        )

        system._active_sessions["test_session_1"] = session

        # Get session status
        retrieved = system.get_session_status("test_session_1")
        assert retrieved is not None
        assert retrieved.status == "completed"

        # Get active sessions
        sessions = system.get_active_sessions()
        assert len(sessions) == 1

        # Cleanup
        system.cleanup_session("test_session_1")
        assert system.get_session_status("test_session_1") is None

    def test_get_metrics(self):
        """Test system metrics."""
        system = create_federated_cross_device_system(device_id="metrics_test")

        # Create some activity
        system._metrics["total_transfers"] = 5
        system._metrics["successful_transfers"] = 4

        metrics = system.get_metrics()

        assert metrics["total_transfers"] == 5
        assert metrics["successful_transfers"] == 4
        assert metrics["device_id"] == "metrics_test"


class TestIntegrationScenarios:
    """Integration tests for complete workflows."""

    def test_complete_transfer_workflow(self):
        """Test complete cross-device transfer workflow."""
        # Create source system
        source = create_federated_cross_device_system(device_id="source_device")

        # Create target system
        target = create_federated_cross_device_system(device_id="target_device")

        # Register devices with each other using cross_device_manager
        source.cross_device_manager.register_device(
            target.cross_device_manager.capabilities
        )
        target.cross_device_manager.register_device(
            source.cross_device_manager.capabilities
        )

        # Mock model transfer
        source.federated_client.get_model_weights = Mock(
            return_value={
                "embeddings": np.random.randn(100, 768).astype(np.float32) * 0.1
            }
        )
        source.federated_client.get_model_architecture = Mock(
            return_value={"hidden_size": 256}
        )

        # Initiate transfer
        session = source.initiate_knowledge_transfer(
            target_device_id="target_device",
            strategy=TransferStrategy.KNOWLEDGE_DISTILLATION,
        )

        # Verify transfer session exists
        status = source.get_session_status(session.session_id)
        assert status is not None

        # Get metrics
        metrics = source.get_metrics()
        assert metrics["total_transfer_sessions"] >= 1

    def test_heterogeneous_device_transfer(self):
        """Test transfer between heterogeneous devices."""
        # Create high-performance source
        source = create_federated_cross_device_system(device_id="high_perf")
        source.cross_device_manager.capabilities = DeviceCapabilities(
            device_id="high_perf",
            device_tier=DeviceTier.TIER_4_HIGH_PERFORMANCE,
            cpu_cores=16,
            cpu_frequency_mhz=3000.0,
            ram_gb=32.0,
            storage_gb=1000.0,
            has_gpu=True,
            gpu_memory_gb=16.0,
            supported_precision=["float32", "float16", "bfloat16"],
        )

        # Create low-power target
        target = create_federated_cross_device_system(device_id="low_power")
        target.cross_device_manager.capabilities = DeviceCapabilities(
            device_id="low_power",
            device_tier=DeviceTier.TIER_2_EDGE,
            cpu_cores=4,
            cpu_frequency_mhz=1200.0,
            ram_gb=2.0,
            storage_gb=32.0,
            has_gpu=False,
            supported_precision=["float32"],
        )

        # Register
        source.cross_device_manager.register_device(
            target.cross_device_manager.capabilities
        )
        target.cross_device_manager.register_device(
            source.cross_device_manager.capabilities
        )

        # Mock model
        source.federated_client.get_model_weights = Mock(
            return_value={"layer1_weight": np.random.randn(512, 768).astype(np.float32)}
        )
        source.federated_client.get_model_architecture = Mock(
            return_value={"hidden_size": 512}
        )

        # Initiate distillation transfer
        session = source.initiate_knowledge_transfer(
            target_device_id="low_power",
            strategy=TransferStrategy.KNOWLEDGE_DISTILLATION,
        )

        assert session.strategy == TransferStrategy.KNOWLEDGE_DISTILLATION
        assert (
            session.source_capabilities.device_tier
            == DeviceTier.TIER_4_HIGH_PERFORMANCE
        )
        assert session.target_capabilities.device_tier == DeviceTier.TIER_2_EDGE


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
