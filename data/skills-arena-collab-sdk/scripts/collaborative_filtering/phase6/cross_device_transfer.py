"""
Phase 6: Cross-Device Transfer for Federated Learning

This module enables knowledge sharing between federated learning clients with:
- Privacy preservation (no raw data transfer)
- Device heterogeneity handling (different hardware, OS, capabilities)
- Efficient model transfer protocols
- Knowledge distillation for heterogeneous model architectures

Author: Skills Arena Development Team
Version: 6.0.0
"""

import asyncio
import hashlib
import json
import logging
import os
import pickle
import struct
import threading
import time
import uuid
import zlib
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union, BinaryIO
from pathlib import Path
import numpy as np

# Import SkillsArenaClient when available, otherwise use mock
try:
    from skills_arena_collab_sdk.scripts.collab_sdk import SkillsArenaClient
except ImportError:
    try:
        from ....scripts.collab_sdk import SkillsArenaClient
    except ImportError:
        SkillsArenaClient = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DeviceTier(Enum):
    """Device capability tiers for transfer optimization."""

    TIER_1_EMBEDDED = auto()  # Very limited (microcontrollers)
    TIER_2_EDGE = auto()  # Limited (Raspberry Pi, mobile)
    TIER_3_STANDARD = auto()  # Standard laptop/desktop
    TIER_4_HIGH_PERFORMANCE = auto()  # Gaming/Workstation
    TIER_5_SERVER = auto()  # Server-grade


class TransferMode(Enum):
    """Mode for cross-device knowledge transfer."""

    DIRECT_P2P = auto()  # Direct device-to-device
    EDGE_ASSISTED = auto()  # Via edge server
    CLOUD_COORDINATED = auto()  # Via cloud coordinator
    HYBRID = auto()  # Mixed approach


class ModelFormat(Enum):
    """Format for model transfer."""

    FULL_MODEL = auto()  # Complete model weights
    DIFF_UPDATE = auto()  # Differential updates
    GRADIENT_COMPRESSION = auto()  # Compressed gradients
    KNOWLEDGE_DISTILLATION = auto()  # Teacher-student transfer
    SPARSE_UPDATE = auto()  # Sparse parameter updates
    QUANTIZED = auto()  # Quantized weights (INT8/FP16)


class CompressionType(Enum):
    """Compression algorithms for model transfer."""

    NO_COMPRESSION = auto()
    ZLIB = auto()
    LZ4 = auto()
    ZSTD = auto()
    BROTLI = auto()
    QUANTIZATION = auto()


@dataclass
class DeviceCapabilities:
    """Represents the capabilities of a federated learning client device."""

    device_id: str
    device_tier: DeviceTier

    # Hardware capabilities
    cpu_cores: int
    cpu_frequency_mhz: float
    ram_gb: float
    storage_gb: float
    has_gpu: bool
    gpu_memory_gb: float = 0.0
    gpu_compute_capability: float = 0.0

    # Network capabilities
    max_upload_speed_mbps: float = 100.0
    max_download_speed_mbps: float = 100.0
    network_type: str = "wifi"  # wifi, cellular, ethernet

    # Model compatibility
    supported_precision: List[str] = field(default_factory=lambda: ["float32"])
    max_model_size_mb: float = 500.0
    supported_operations: List[str] = field(default_factory=list)

    # Power constraints
    batteryPowered: bool = False
    max_power_watts: float = 100.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "device_id": self.device_id,
            "device_tier": self.device_tier.name,
            "cpu_cores": self.cpu_cores,
            "cpu_frequency_mhz": self.cpu_frequency_mhz,
            "ram_gb": self.ram_gb,
            "storage_gb": self.storage_gb,
            "has_gpu": self.has_gpu,
            "gpu_memory_gb": self.gpu_memory_gb,
            "max_upload_speed_mbps": self.max_upload_speed_mbps,
            "max_download_speed_mbps": self.max_download_speed_mbps,
            "network_type": self.network_type,
            "supported_precision": self.supported_precision,
            "max_model_size_mb": self.max_model_size_mb,
            "supported_operations": self.supported_operations,
            "batteryPowered": self.batteryPowered,
            "max_power_watts": self.max_power_watts,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeviceCapabilities":
        """Create from dictionary."""
        return cls(
            device_id=data["device_id"],
            device_tier=DeviceTier[data["device_tier"]],
            cpu_cores=data["cpu_cores"],
            cpu_frequency_mhz=data["cpu_frequency_mhz"],
            ram_gb=data["ram_gb"],
            storage_gb=data["storage_gb"],
            has_gpu=data["has_gpu"],
            gpu_memory_gb=data.get("gpu_memory_gb", 0.0),
            max_upload_speed_mbps=data.get("max_upload_speed_mbps", 100.0),
            max_download_speed_mbps=data.get("max_download_speed_mbps", 100.0),
            network_type=data.get("network_type", "wifi"),
            supported_precision=data.get("supported_precision", ["float32"]),
            max_model_size_mb=data.get("max_model_size_mb", 500.0),
            supported_operations=data.get("supported_operations", []),
            batteryPowered=data.get("batteryPowered", False),
            max_power_watts=data.get("max_power_watts", 100.0),
        )

    @classmethod
    def detect_capabilities(cls, device_id: str) -> "DeviceCapabilities":
        """
        Auto-detect device capabilities.

        This is a simplified implementation. In production, use platform-specific
        APIs (psutil, GPUtil, platform, etc.) for accurate detection.
        """
        import platform
        import os

        # Detect tier based on available information
        system = platform.system()
        machine = platform.machine()

        # Simple tier detection (in production, use more sophisticated heuristics)
        if machine in ["armv6l", "armv7l"]:
            tier = DeviceTier.TIER_2_EDGE
            cpu_cores = os.cpu_count() or 1
            ram_gb = 1.0  # Assume limited
        elif machine in ["aarch64"]:
            tier = DeviceTier.TIER_2_EDGE
            cpu_cores = os.cpu_count() or 4
            ram_gb = 2.0
        else:
            # Assume standard x86_64 system
            tier = DeviceTier.TIER_3_STANDARD
            cpu_cores = os.cpu_count() or 8
            ram_gb = 16.0

        return cls(
            device_id=device_id,
            device_tier=tier,
            cpu_cores=cpu_cores,
            cpu_frequency_mhz=2000.0,  # Default assumption
            ram_gb=ram_gb,
            storage_gb=256.0,  # Default assumption
            has_gpu=False,  # In production, detect via CUDA_VISIBLE_DEVICES
            max_upload_speed_mbps=50.0,
            max_download_speed_mbps=100.0,
            supported_precision=["float32", "float16"]
            if tier.value >= DeviceTier.TIER_3_STANDARD.value
            else ["float32"],
            supported_operations=["matrix_multiply", "convolution"]
            if tier.value >= DeviceTier.TIER_3_STANDARD.value
            else ["matrix_multiply"],
        )


@dataclass
class TransferPayload:
    """Represents a knowledge transfer payload between devices."""

    payload_id: str
    source_device: str
    target_device: str
    transfer_mode: TransferMode
    model_format: ModelFormat

    # Model data
    model_weights: Optional[bytes] = None
    model_architecture: Optional[Dict[str, Any]] = None
    model_metadata: Optional[Dict[str, Any]] = None

    # Transfer metadata
    compression: CompressionType = CompressionType.ZLIB
    compression_ratio: float = 1.0
    checksum: str = ""

    # Privacy guarantees
    differential_privacy_epsilon: float = 0.0
    secure_aggregation: bool = False

    # Transfer state
    created_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 3600)
    chunk_count: int = 0
    chunk_size: int = 65536  # 64KB chunks

    def to_bytes(self) -> bytes:
        """Serialize payload to bytes."""
        data = {
            "payload_id": self.payload_id,
            "source_device": self.source_device,
            "target_device": self.target_device,
            "transfer_mode": self.transfer_mode.name,
            "model_format": self.model_format.name,
            "model_architecture": self.model_architecture,
            "model_metadata": self.model_metadata,
            "compression": self.compression.name,
            "compression_ratio": self.compression_ratio,
            "checksum": self.checksum,
            "differential_privacy_epsilon": self.differential_privacy_epsilon,
            "secure_aggregation": self.secure_aggregation,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "chunk_count": self.chunk_count,
            "chunk_size": self.chunk_size,
            "model_weights": None
            if self.model_weights is None
            else len(self.model_weights),
        }
        return pickle.dumps(data)

    @classmethod
    def from_bytes(cls, data: bytes) -> "TransferPayload":
        """Deserialize payload from bytes."""
        obj = pickle.loads(data)
        return cls(**obj)


@dataclass
class KnowledgeTransfer:
    """Represents a knowledge transfer session between devices."""

    transfer_id: str
    source_device: str
    target_device: str
    source_capabilities: DeviceCapabilities
    target_capabilities: DeviceCapabilities
    transfer_mode: TransferMode
    model_format: ModelFormat

    # Transfer progress
    status: str = "pending"  # pending, transferring, completed, failed
    progress: float = 0.0
    bytes_transferred: int = 0
    total_bytes: int = 0

    # Transfer quality metrics
    transfer_quality: float = 0.0  # 0-1 score
    knowledge_retained: float = 0.0  # 0-1 score
    compression_achieved: float = 1.0

    # Timing
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    # Error tracking
    error_message: Optional[str] = None
    retry_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class KnowledgeDistillationTrainer:
    """
    Implements knowledge distillation for cross-device transfer.

    Knowledge distillation transfers "dark knowledge" from a teacher model
    to a student model, enabling efficient transfer even when model
    architectures differ significantly.
    """

    def __init__(self, temperature: float = 4.0, alpha: float = 0.5):
        """
        Initialize knowledge distillation trainer.

        Args:
            temperature: Softmax temperature for softening probability distributions
            alpha: Balance between hard and soft targets
        """
        self.temperature = temperature
        self.alpha = alpha
        self.teacher_outputs: Dict[str, np.ndarray] = {}
        self.student_outputs: Dict[str, np.ndarray] = {}

    def extract_teacher_knowledge(
        self, model_weights: Dict[str, np.ndarray], inputs: Optional[np.ndarray] = None
    ) -> Dict[str, np.ndarray]:
        """
        Extract knowledge from teacher model.

        In federated learning context, this extracts:
        - Learned embeddings
        - Attention patterns
        - Output distributions
        - Intermediate representations
        """
        knowledge = {}

        # Extract embedding knowledge
        if "embeddings" in model_weights:
            embeddings = model_weights["embeddings"]
            knowledge["embeddings"] = self._normalize_embeddings(embeddings)

        # Extract weight statistics (pruned for privacy)
        for name, weight in model_weights.items():
            if name.endswith("_weight") or name.endswith("_kernel"):
                knowledge[f"{name}_stats"] = {
                    "mean": float(np.mean(weight)),
                    "std": float(np.std(weight)),
                    "sparsity": float(np.sum(weight == 0) / weight.size),
                    "quantiles": self._compute_quantiles(weight),
                }

        # Extract layer-wise statistics
        knowledge["layer_stats"] = {
            "num_layers": len(
                [k for k in model_weights.keys() if "weight" in k or "bias" in k]
            ),
            "total_parameters": sum(
                w.size for w in model_weights.values() if isinstance(w, np.ndarray)
            ),
            "trainable_layers": len(model_weights),
        }

        return knowledge

    def create_student_model(
        self,
        source_capabilities: DeviceCapabilities,
        target_capabilities: DeviceCapabilities,
        original_architecture: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create a student model architecture suitable for the target device.

        This reduces model size while preserving knowledge.
        """
        # Calculate size reduction based on device tier difference
        source_tier_value = source_capabilities.device_tier.value
        target_tier_value = target_capabilities.device_tier.value

        # If target is less capable, reduce model size
        reduction_factor = 1.0
        if target_tier_value < source_tier_value:
            reduction_factor = max(0.1, target_tier_value / source_tier_value)

        # Create scaled architecture
        student_architecture = original_architecture.copy()

        if "hidden_size" in student_architecture:
            student_architecture["hidden_size"] = max(
                32, int(original_architecture["hidden_size"] * reduction_factor)
            )

        if "num_layers" in student_architecture:
            student_architecture["num_layers"] = max(
                1, int(original_architecture["num_layers"] * reduction_factor)
            )

        if "embedding_dim" in student_architecture:
            student_architecture["embedding_dim"] = max(
                16, int(original_architecture["embedding_dim"] * reduction_factor)
            )

        # Add knowledge transfer metadata
        student_architecture["distillation_source"] = {
            "original_size": original_architecture.get("hidden_size", 256),
            "compression_ratio": reduction_factor,
            "temperature": self.temperature,
            "alpha": self.alpha,
        }

        return student_architecture

    def distill_knowledge(
        self,
        teacher_weights: Dict[str, np.ndarray],
        student_weights: Dict[str, np.ndarray],
        knowledge: Dict[str, np.ndarray],
    ) -> Dict[str, np.ndarray]:
        """
        Perform knowledge distillation to transfer knowledge from teacher to student.

        Args:
            teacher_weights: Original model weights (teacher)
            student_weights: Initial student model weights
            knowledge: Extracted knowledge from teacher

        Returns:
            Updated student weights with distilled knowledge
        """
        distilled_weights = student_weights.copy()

        # Transfer embedding knowledge
        if "embeddings" in knowledge and "embeddings" in student_weights:
            teacher_emb = knowledge["embeddings"]
            student_emb = student_weights["embeddings"]

            # Match dimensions if necessary
            if teacher_emb.shape != student_emb.shape:
                teacher_emb = self._resize_embeddings(teacher_emb, student_emb.shape)

            # Blend teacher knowledge into student embeddings
            distilled_weights["embeddings"] = self._blend_embeddings(
                student_emb, teacher_emb, alpha=0.7
            )

        # Transfer weight statistics knowledge
        for key, stats in knowledge.items():
            if key.endswith("_stats") and key.replace("_stats", "") in student_weights:
                param_name = key.replace("_stats", "")
                original_weight = student_weights[param_name]

                # Adjust weight distribution to match teacher's statistics
                distilled_weights[param_name] = self._match_statistics(
                    original_weight, mean=stats["mean"], std=stats["std"]
                )

        return distilled_weights

    def compute_distillation_loss(
        self,
        student_outputs: np.ndarray,
        teacher_outputs: np.ndarray,
        hard_targets: Optional[np.ndarray] = None,
    ) -> Tuple[float, Dict[str, float]]:
        """
        Compute knowledge distillation loss.

        Combines soft targets (from teacher) with hard targets (ground truth).
        """
        # Soft targets loss (KL divergence)
        soft_student = student_outputs / self.temperature
        soft_teacher = teacher_outputs / self.temperature

        # Softmax with temperature
        soft_student = self._softmax(soft_student)
        soft_teacher = self._softmax(soft_teacher)

        # KL divergence loss
        kl_loss = np.sum(
            soft_teacher * np.log(soft_teacher / (soft_student + 1e-10) + 1e-10)
        )

        losses = {"kl_divergence": kl_loss}

        # Hard targets loss if available
        if hard_targets is not None:
            hard_loss = np.mean(-hard_targets * np.log(student_outputs + 1e-10))
            losses["hard_loss"] = hard_loss

            # Combined loss
            total_loss = (1 - self.alpha) * hard_loss + self.alpha * kl_loss * (
                self.temperature**2
            )
            losses["total"] = total_loss
        else:
            losses["total"] = kl_loss * (self.temperature**2)

        return losses["total"], losses

    def _normalize_embeddings(self, embeddings: np.ndarray) -> np.ndarray:
        """Normalize embeddings to unit norm."""
        norms = np.linalg.norm(embeddings, axis=-1, keepdims=True)
        return embeddings / (norms + 1e-10)

    def _compute_quantiles(
        self, arr: np.ndarray, num_quantiles: int = 100
    ) -> List[float]:
        """Compute quantiles for weight distribution."""
        return [
            float(np.percentile(arr, q)) for q in np.linspace(0, 100, num_quantiles)
        ]

    def _resize_embeddings(
        self, source: np.ndarray, target_shape: Tuple[int, ...]
    ) -> np.ndarray:
        """Resize embeddings to match target shape."""
        if len(target_shape) == 1:
            # Just adjust embedding dimension
            if source.shape[0] >= target_shape[0]:
                return source[: target_shape[0]]
            else:
                return np.pad(source, ((0, target_shape[0] - source.shape[0]), (0, 0)))
        return source

    def _blend_embeddings(
        self, student: np.ndarray, teacher: np.ndarray, alpha: float = 0.7
    ) -> np.ndarray:
        """Blend student and teacher embeddings."""
        # Normalize both
        student_norm = self._normalize_embeddings(student)
        teacher_norm = self._normalize_embeddings(teacher)

        # Blend
        result = alpha * teacher_norm + (1 - alpha) * student_norm

        # Renormalize
        return self._normalize_embeddings(result)

    def _match_statistics(
        self, weights: np.ndarray, mean: float, std: float
    ) -> np.ndarray:
        """Match weight distribution to target statistics."""
        # Center
        centered = weights - np.mean(weights)
        # Scale
        scaled = centered * (std / (np.std(weights) + 1e-10))
        # Shift
        return scaled + mean

    def _softmax(self, x: np.ndarray) -> np.ndarray:
        """Softmax with numerical stability."""
        x = x - np.max(x, axis=-1, keepdims=True)
        exp_x = np.exp(x)
        return exp_x / np.sum(exp_x, axis=-1, keepdims=True)


class ModelAdapter:
    """
    Fast model adapter for heterogeneous device architectures.

    Converts model representations between different formats and precision
    levels while maintaining model semantics.
    """

    def __init__(self):
        """Initialize model adapter."""
        self.precision_converters: Dict[str, Callable] = {
            "float32": self._to_float32,
            "float16": self._to_float16,
            "int8": self._to_int8,
            "bfloat16": self._to_bfloat16,
        }

        self.format_converters: Dict[str, Callable] = {
            "numpy": self._from_numpy,
            "onnx": self._from_onnx,
            "torch": self._from_torch,
            "tensorflow": self._from_tensorflow,
        }

    def adapt_model(
        self,
        model_weights: Dict[str, np.ndarray],
        target_precision: str,
        target_format: str = "numpy",
    ) -> Dict[str, np.ndarray]:
        """
        Adapt model to target precision and format.

        Args:
            model_weights: Original model weights
            target_precision: Target precision (float32, float16, int8)
            target_format: Target format (numpy, onnx, torch, tensorflow)

        Returns:
            Adapted model weights
        """
        adapted = {}

        # Apply precision conversion
        converter = self.precision_converters.get(target_precision, self._to_float32)

        for name, weights in model_weights.items():
            if isinstance(weights, np.ndarray):
                adapted[name] = converter(weights)
            else:
                adapted[name] = weights

        return adapted

    def quantize_model(
        self,
        model_weights: Dict[str, np.ndarray],
        target_bits: int = 8,
        method: str = "symmetric",
    ) -> Dict[str, np.ndarray]:
        """
        Quantize model weights to lower precision.

        Args:
            model_weights: Full precision model weights
            target_bits: Target bit width (8, 4, 2)
            method: Quantization method (symmetric, asymmetric)

        Returns:
            Quantized weights
        """
        quantized = {}

        for name, weights in model_weights.items():
            if not isinstance(weights, np.ndarray) or weights.dtype == np.int8:
                quantized[name] = weights
                continue

            if method == "symmetric":
                quantized[name] = self._symmetric_quantize(weights, target_bits)
            else:
                quantized[name] = self._asymmetric_quantize(weights, target_bits)

        return quantized

    def dequantize_model(
        self, model_weights: Dict[str, np.ndarray]
    ) -> Dict[str, np.ndarray]:
        """Dequantize model back to float32."""
        dequantized = {}

        for name, weights in model_weights.items():
            if isinstance(weights, np.ndarray) and weights.dtype in [
                np.int8,
                np.int4,
                np.uint8,
            ]:
                scale = getattr(weights, "scale", 1.0)
                zero_point = getattr(weights, "zero_point", 0)

                if weights.dtype == np.int8:
                    dequantized[name] = weights.astype(np.float32) * scale + zero_point
                else:
                    dequantized[name] = weights.astype(np.float32) * scale
            else:
                dequantized[name] = weights

        return dequantized

    def compress_model(
        self,
        model_weights: Dict[str, np.ndarray],
        method: str = "sparse",
        sparsity: float = 0.9,
    ) -> Tuple[Dict[str, np.ndarray], Dict[str, Any]]:
        """
        Compress model using various techniques.

        Args:
            model_weights: Model weights to compress
            method: Compression method (sparse, prune, factorize)
            sparsity: Target sparsity ratio

        Returns:
            Compressed weights and metadata
        """
        compressed = {}
        metadata = {"method": method, "original_size": 0, "compressed_size": 0}

        total_original = 0
        total_compressed = 0

        for name, weights in model_weights.items():
            if not isinstance(weights, np.ndarray):
                compressed[name] = weights
                total_original += 0
                total_compressed += 0
                continue

            total_original += weights.nbytes

            if method == "sparse":
                compressed[name] = self._apply_sparsity(weights, sparsity)
            elif method == "prune":
                compressed[name] = self._prune_weights(weights, sparsity)
            elif method == "factorize":
                compressed[name], rank = self._matrix_factorize(weights)
                metadata[f"{name}_rank"] = rank
            else:
                compressed[name] = weights

            total_compressed += (
                compressed[name].nbytes if hasattr(compressed[name], "nbytes") else 0
            )

        metadata["original_size"] = total_original
        metadata["compressed_size"] = total_compressed
        metadata["compression_ratio"] = total_original / (total_compressed + 1)

        return compressed, metadata

    def _to_float32(self, arr: np.ndarray) -> np.ndarray:
        """Convert to float32."""
        if arr.dtype == np.float32:
            return arr
        return arr.astype(np.float32)

    def _to_float16(self, arr: np.ndarray) -> np.ndarray:
        """Convert to float16."""
        return arr.astype(np.float16)

    def _to_int8(self, arr: np.ndarray) -> np.ndarray:
        """Convert to int8 with symmetric quantization."""
        return self._symmetric_quantize(arr, 8)

    def _to_bfloat16(self, arr: np.ndarray) -> np.ndarray:
        """Convert to bfloat16."""
        # Simple bfloat16 conversion (in production, use proper conversion)
        return arr.astype(np.float32)  # Placeholder

    def _symmetric_quantize(self, arr: np.ndarray, bits: int) -> np.ndarray:
        """Symmetric quantization."""
        max_val = np.max(np.abs(arr))
        if max_val == 0:
            return arr.astype(np.int8)

        scale = (2 ** (bits - 1) - 1) / max_val
        quantized = np.round(arr * scale).astype(np.int8)

        return quantized

    def _asymmetric_quantize(self, arr: np.ndarray, bits: int) -> np.ndarray:
        """Asymmetric quantization."""
        min_val = np.min(arr)
        max_val = np.max(arr)

        if max_val == min_val:
            return arr.astype(np.int8)

        scale = (2**bits - 1) / (max_val - min_val)
        zero_point = -min_val * scale

        quantized = np.round(arr * scale + zero_point).astype(np.uint8)

        return quantized

    def _apply_sparsity(self, arr: np.ndarray, sparsity: float) -> np.ndarray:
        """Apply magnitude-based sparsity."""
        threshold = np.percentile(np.abs(arr), sparsity * 100)
        sparse = arr.copy()
        sparse[np.abs(sparse) < threshold] = 0
        return sparse

    def _prune_weights(self, arr: np.ndarray, pruning_ratio: float) -> np.ndarray:
        """Prune weights below magnitude threshold."""
        return self._apply_sparsity(arr, pruning_ratio)

    def _matrix_factorize(self, arr: np.ndarray) -> Tuple[Dict[str, np.ndarray], int]:
        """Low-rank matrix factorization for compression."""
        # Simplified SVD-based factorization
        if arr.ndim != 2:
            return arr, arr.size

        try:
            U, s, Vh = np.linalg.svd(arr, full_matrices=False)
            rank = min(len(s), max(1, int(len(s) * (1 - 0.5))))  # 50% reduction

            return {
                "U": U[:, :rank],
                "singular_values": s[:rank],
                "Vh": Vh[:rank, :],
            }, rank
        except np.linalg.LinAlgError:
            return arr, arr.shape[0]

    def _from_numpy(self, model: Any) -> Any:
        """Convert from numpy format."""
        return model

    def _from_onnx(self, model: Any) -> Any:
        """Convert from ONNX format."""
        # Placeholder for ONNX conversion
        return model

    def _from_torch(self, model: Any) -> Any:
        """Convert from PyTorch format."""
        # Placeholder for PyTorch conversion
        return model

    def _from_tensorflow(self, model: Any) -> Any:
        """Convert from TensorFlow format."""
        # Placeholder for TensorFlow conversion
        return model


class DeviceToDeviceProtocol:
    """
    Implements device-to-device model transfer protocol.

    Provides secure, efficient transfer of model knowledge between
    federated learning clients.
    """

    def __init__(
        self,
        compression: CompressionType = CompressionType.ZLIB,
        chunk_size: int = 65536,
        max_retries: int = 3,
    ):
        """
        Initialize D2D transfer protocol.

        Args:
            compression: Compression algorithm for transfer
            chunk_size: Size of transfer chunks in bytes
            max_retries: Maximum retry attempts for failed transfers
        """
        self.compression = compression
        self.chunk_size = chunk_size
        self.max_retries = max_retries

        self._compressors: Dict[CompressionType, Callable] = {
            CompressionType.NO_COMPRESSION: lambda x: x,
            CompressionType.ZLIB: zlib.compress,
            CompressionType.LZ4: self._lz4_compress,
            CompressionType.ZSTD: self._zstd_compress,
            CompressionType.BROTLI: self._brotli_compress,
            CompressionType.QUANTIZATION: self._quantize_for_transfer,
        }

        self._decompressors: Dict[CompressionType, Callable] = {
            CompressionType.NO_COMPRESSION: lambda x: x,
            CompressionType.ZLIB: zlib.decompress,
            CompressionType.LZ4: self._lz4_decompress,
            CompressionType.ZSTD: self._zstd_decompress,
            CompressionType.BROTLI: self._brotli_decompress,
            CompressionType.QUANTIZATION: self._dequantize_for_transfer,
        }

        # Transfer registry
        self._active_transfers: Dict[str, KnowledgeTransfer] = {}
        self._transfer_lock = threading.Lock()

        # Callbacks for integration
        self.on_transfer_start: Optional[Callable] = None
        self.on_transfer_progress: Optional[Callable] = None
        self.on_transfer_complete: Optional[Callable] = None
        self.on_transfer_error: Optional[Callable] = None

    def initiate_transfer(
        self,
        source_device: str,
        target_device: str,
        source_capabilities: DeviceCapabilities,
        target_capabilities: DeviceCapabilities,
        model_weights: Dict[str, np.ndarray],
        model_architecture: Dict[str, Any],
        privacy_settings: Optional[Dict[str, Any]] = None,
    ) -> KnowledgeTransfer:
        """
        Initiate a knowledge transfer between devices.

        Args:
            source_device: Source device ID
            target_device: Target device ID
            source_capabilities: Source device capabilities
            target_capabilities: Target device capabilities
            model_weights: Model weights to transfer
            model_architecture: Model architecture description
            privacy_settings: Privacy configuration

        Returns:
            KnowledgeTransfer instance for tracking
        """
        transfer_id = str(uuid.uuid4())

        # Determine optimal transfer mode
        transfer_mode = self._select_transfer_mode(
            source_capabilities, target_capabilities
        )

        # Determine optimal model format
        model_format = self._select_model_format(
            source_capabilities, target_capabilities
        )

        transfer = KnowledgeTransfer(
            transfer_id=transfer_id,
            source_device=source_device,
            target_device=target_device,
            source_capabilities=source_capabilities,
            target_capabilities=target_capabilities,
            transfer_mode=transfer_mode,
            model_format=model_format,
            status="pending",
        )

        # Register transfer
        with self._transfer_lock:
            self._active_transfers[transfer_id] = transfer

        # Execute transfer asynchronously
        threading.Thread(
            target=self._execute_transfer,
            args=(transfer, model_weights, model_architecture, privacy_settings),
            daemon=True,
        ).start()

        return transfer

    def _select_transfer_mode(
        self, source: DeviceCapabilities, target: DeviceCapabilities
    ) -> TransferMode:
        """Select optimal transfer mode based on device capabilities."""
        # Direct P2P if both devices are on same network
        if source.network_type == target.network_type:
            return TransferMode.DIRECT_P2P

        # Use edge assistance if available
        if source.device_tier.value >= DeviceTier.TIER_3_STANDARD.value:
            return TransferMode.EDGE_ASSISTED

        # Fall back to cloud coordination
        return TransferMode.CLOUD_COORDINATED

    def _select_model_format(
        self, source: DeviceCapabilities, target: DeviceCapabilities
    ) -> ModelFormat:
        """Select optimal model format for transfer."""
        # Use quantization for limited devices
        if target.device_tier.value <= DeviceTier.TIER_2_EDGE.value:
            if target.has_gpu:
                return ModelFormat.QUANTIZED
            return ModelFormat.SPARSE_UPDATE

        # Use differential updates for similar devices
        if source.device_tier == target.device_tier:
            return ModelFormat.DIFF_UPDATE

        # Use knowledge distillation for very different devices
        if abs(source.device_tier.value - target.device_tier.value) > 2:
            return ModelFormat.KNOWLEDGE_DISTILLATION

        # Default to full model
        return ModelFormat.FULL_MODEL

    def _execute_transfer(
        self,
        transfer: KnowledgeTransfer,
        model_weights: Dict[str, np.ndarray],
        model_architecture: Dict[str, Any],
        privacy_settings: Optional[Dict[str, Any]] = None,
    ):
        """Execute knowledge transfer."""
        try:
            transfer.status = "transferring"
            transfer.started_at = time.time()

            # Serialize model weights
            weights_bytes = pickle.dumps(model_weights)

            # Apply compression
            compressor = self._compressors.get(
                self.compression, self._compressors[CompressionType.ZLIB]
            )
            compressed_weights = compressor(weights_bytes)

            # Create payload
            payload = TransferPayload(
                payload_id=transfer.transfer_id,
                source_device=transfer.source_device,
                target_device=transfer.target_device,
                transfer_mode=transfer.transfer_mode,
                model_format=transfer.model_format,
                model_weights=compressed_weights,
                model_architecture=model_architecture,
                model_metadata={
                    "original_size": len(weights_bytes),
                    "compressed_size": len(compressed_weights),
                    "compression_type": self.compression.name,
                    "timestamp": time.time(),
                },
                compression=self.compression,
                compression_ratio=len(weights_bytes) / max(1, len(compressed_weights)),
                checksum=self._compute_checksum(compressed_weights),
            )

            transfer.total_bytes = len(compressed_weights)

            # Chunk and transfer
            chunks = self._chunk_data(compressed_weights, self.chunk_size)
            payload.chunk_count = len(chunks)

            transferred = 0
            for i, chunk in enumerate(chunks):
                # Simulate chunk transfer
                self._transfer_chunk(chunk, transfer)
                transferred += len(chunk)

                transfer.bytes_transferred = transferred
                transfer.progress = transferred / transfer.total_bytes

                if self.on_transfer_progress:
                    self.on_transfer_progress(transfer)

            # Mark complete
            transfer.status = "completed"
            transfer.completed_at = time.time()
            transfer.progress = 1.0
            transfer.knowledge_retained = 0.95  # Assuming 95% retention
            transfer.compression_achieved = transfer.total_bytes / max(
                1, len(weights_bytes)
            )

            if self.on_transfer_complete:
                self.on_transfer_complete(transfer)

        except Exception as e:
            transfer.status = "failed"
            transfer.error_message = str(e)
            transfer.retry_count += 1

            if self.on_transfer_error:
                self.on_transfer_error(transfer, e)

            logger.error(f"Transfer failed: {e}")

    def _transfer_chunk(self, chunk: bytes, transfer: KnowledgeTransfer):
        """Simulate chunk transfer (in production, implement actual network transfer)."""
        # In production, this would:
        # 1. Establish P2P connection or route through edge/cloud
        # 2. Send chunk with sequence number
        # 3. Wait for acknowledgment
        # 4. Handle retransmission if needed

        time.sleep(0.001)  # Simulate network latency

    def _chunk_data(self, data: bytes, chunk_size: int) -> List[bytes]:
        """Split data into chunks."""
        return [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]

    def _compute_checksum(self, data: bytes) -> str:
        """Compute checksum for data integrity."""
        return hashlib.sha256(data).hexdigest()

    def _quantize_for_transfer(self, data: bytes) -> bytes:
        """Quantize weights for transfer."""
        # Simplified quantization for transfer
        return data

    def _lz4_compress(self, data: bytes) -> bytes:
        """LZ4 compression placeholder."""
        # In production, use lz4 library
        return zlib.compress(data)

    def _lz4_decompress(self, data: bytes) -> bytes:
        """LZ4 decompression placeholder."""
        return zlib.decompress(data)

    def _zstd_compress(self, data: bytes) -> bytes:
        """ZSTD compression placeholder."""
        return zlib.compress(data)

    def _zstd_decompress(self, data: bytes) -> bytes:
        """ZSTD decompression placeholder."""
        return zlib.decompress(data)

    def _brotli_compress(self, data: bytes) -> bytes:
        """Brotli compression placeholder."""
        return zlib.compress(data)

    def _brotli_decompress(self, data: bytes) -> bytes:
        """Brotli decompression placeholder."""
        return zlib.decompress(data)

    def _quantize_for_transfer(self, data: bytes) -> bytes:
        """Quantize data for transfer."""
        return data

    def _dequantize_for_transfer(self, data: bytes) -> bytes:
        """Dequantize data after transfer."""
        return data

    def get_transfer_status(self, transfer_id: str) -> Optional[KnowledgeTransfer]:
        """Get status of a transfer."""
        with self._transfer_lock:
            return self._active_transfers.get(transfer_id)

    def retry_transfer(self, transfer_id: str) -> bool:
        """Retry a failed transfer."""
        with self._transfer_lock:
            transfer = self._active_transfers.get(transfer_id)
            if transfer and transfer.retry_count < self.max_retries:
                transfer.retry_count += 1
                transfer.status = "pending"
                transfer.progress = 0.0
                transfer.bytes_transferred = 0

                threading.Thread(
                    target=self._execute_transfer,
                    args=(
                        transfer,
                        {},  # Would need to store model weights
                        {},  # Would need to store architecture
                        None,
                    ),
                    daemon=True,
                ).start()
                return True
        return False


class CrossDeviceTransferManager:
    """
    Main orchestrator for cross-device knowledge transfer.

    Integrates all components for complete cross-device transfer
    with privacy preservation and device heterogeneity handling.
    """

    def __init__(
        self,
        client: Optional[SkillsArenaClient] = None,
        device_id: Optional[str] = None,
    ):
        """
        Initialize cross-device transfer manager.

        Args:
            client: Skills Arena client for coordination
            device_id: Unique identifier for this device
        """
        self.client = client
        self.device_id = device_id or str(uuid.uuid4())

        # Initialize components
        self.capabilities = DeviceCapabilities.detect_capabilities(self.device_id)
        self.knowledge_distiller = KnowledgeDistillationTrainer()
        self.model_adapter = ModelAdapter()
        self.d2d_protocol = DeviceToDeviceProtocol()

        # Device registry
        self._known_devices: Dict[str, DeviceCapabilities] = {}
        self._transfer_history: List[KnowledgeTransfer] = []

        # Performance metrics
        self._metrics: Dict[str, Any] = {
            "total_transfers": 0,
            "successful_transfers": 0,
            "total_bytes_transferred": 0,
            "average_transfer_time": 0.0,
            "average_quality_score": 0.0,
        }

    def register_device(self, capabilities: DeviceCapabilities):
        """Register a known device for transfer."""
        self._known_devices[capabilities.device_id] = capabilities
        logger.info(f"Registered device: {capabilities.device_id}")

    def unregister_device(self, device_id: str):
        """Unregister a device."""
        if device_id in self._known_devices:
            del self._known_devices[device_id]
            logger.info(f"Unregistered device: {device_id}")

    def get_transferable_devices(
        self, min_capabilities: Optional[DeviceCapabilities] = None
    ) -> List[str]:
        """
        Get list of devices suitable for transfer.

        Args:
            min_capabilities: Minimum required capabilities

        Returns:
            List of device IDs suitable for transfer
        """
        candidates = []

        for device_id, caps in self._known_devices.items():
            if device_id == self.device_id:
                continue

            # Check minimum capabilities if specified
            if min_capabilities:
                if caps.cpu_cores < min_capabilities.cpu_cores:
                    continue
                if caps.ram_gb < min_capabilities.ram_gb:
                    continue

            candidates.append(device_id)

        return candidates

    def initiate_outgoing_transfer(
        self,
        target_device_id: str,
        model_weights: Dict[str, np.ndarray],
        model_architecture: Dict[str, Any],
        privacy_settings: Optional[Dict[str, Any]] = None,
    ) -> KnowledgeTransfer:
        """
        Initiate transfer of model knowledge to target device.

        Args:
            target_device_id: Target device ID
            model_weights: Model weights to transfer
            model_architecture: Model architecture description
            privacy_settings: Privacy configuration

        Returns:
            KnowledgeTransfer for tracking
        """
        if target_device_id not in self._known_devices:
            raise ValueError(f"Unknown device: {target_device_id}")

        target_capabilities = self._known_devices[target_device_id]

        # Create transfer
        transfer = self.d2d_protocol.initiate_transfer(
            source_device=self.device_id,
            target_device=target_device_id,
            source_capabilities=self.capabilities,
            target_capabilities=target_capabilities,
            model_weights=model_weights,
            model_architecture=model_architecture,
            privacy_settings=privacy_settings,
        )

        self._transfer_history.append(transfer)
        self._metrics["total_transfers"] += 1

        return transfer

    def receive_incoming_transfer(
        self,
        payload: TransferPayload,
        local_model_weights: Optional[Dict[str, np.ndarray]] = None,
    ) -> Dict[str, np.ndarray]:
        """
        Receive and integrate incoming model knowledge.

        Args:
            payload: Transfer payload containing model knowledge
            local_model_weights: Current local model weights for integration

        Returns:
            Updated model weights
        """
        # Decompress payload
        decompressor = self.d2d_protocol._decompressors.get(
            payload.compression, lambda x: x
        )

        weights_bytes = decompressor(payload.model_weights)
        model_weights = pickle.loads(weights_bytes)

        # If we have a local model, integrate knowledge
        if (
            local_model_weights
            and payload.model_format == ModelFormat.KNOWLEDGE_DISTILLATION
        ):
            # Perform knowledge distillation
            knowledge = self.knowledge_distiller.extract_teacher_knowledge(
                model_weights
            )
            model_weights = self.knowledge_distiller.distill_knowledge(
                teacher_weights=model_weights,
                student_weights=local_model_weights,
                knowledge=knowledge,
            )

        # Adapt to local device capabilities
        if self.capabilities.device_tier.value <= DeviceTier.TIER_3_STANDARD.value:
            # Adapt to device precision
            model_weights = self.model_adapter.adapt_model(
                model_weights, target_precision=self.capabilities.supported_precision[0]
            )

        return model_weights

    def transfer_with_knowledge_distillation(
        self,
        target_device_id: str,
        model_weights: Dict[str, np.ndarray],
        model_architecture: Dict[str, Any],
        target_capabilities: Optional[DeviceCapabilities] = None,
    ) -> KnowledgeTransfer:
        """
        Transfer model knowledge using distillation for heterogeneous devices.

        Args:
            target_device_id: Target device ID
            model_weights: Teacher model weights
            model_architecture: Model architecture description
            target_capabilities: Target device capabilities (auto-detected if not provided)

        Returns:
            KnowledgeTransfer for tracking
        """
        if target_capabilities is None:
            if target_device_id not in self._known_devices:
                raise ValueError(f"Unknown device: {target_device_id}")
            target_capabilities = self._known_devices[target_device_id]

        # Create student model architecture for target device
        student_architecture = self.knowledge_distiller.create_student_model(
            source_capabilities=self.capabilities,
            target_capabilities=target_capabilities,
            original_architecture=model_architecture,
        )

        # Extract teacher knowledge
        knowledge = self.knowledge_distiller.extract_teacher_knowledge(model_weights)

        # Create minimal student model (placeholder weights)
        student_weights = {
            "embeddings": np.random.randn(
                student_architecture.get("embedding_dim", 64), 768
            ).astype(np.float32)
            * 0.01
        }

        # Distill knowledge into student
        distilled_weights = self.knowledge_distiller.distill_knowledge(
            teacher_weights=model_weights,
            student_weights=student_weights,
            knowledge=knowledge,
        )

        # Transfer distilled model
        return self.initiate_outgoing_transfer(
            target_device_id=target_device_id,
            model_weights=distilled_weights,
            model_architecture=student_architecture,
            privacy_settings={"method": "knowledge_distillation"},
        )

    def get_metrics(self) -> Dict[str, Any]:
        """Get transfer metrics."""
        return {
            **self._metrics,
            "device_id": self.device_id,
            "device_tier": self.capabilities.device_tier.name,
            "registered_devices": len(self._known_devices),
            "transfer_history_count": len(self._transfer_history),
        }

    def reset_metrics(self):
        """Reset transfer metrics."""
        self._metrics = {
            "total_transfers": 0,
            "successful_transfers": 0,
            "total_bytes_transferred": 0,
            "average_transfer_time": 0.0,
            "average_quality_score": 0.0,
        }


def create_cross_device_transfer_system(
    client: Optional[SkillsArenaClient] = None, device_id: Optional[str] = None
) -> CrossDeviceTransferManager:
    """
    Factory function to create cross-device transfer system.

    Args:
        client: Skills Arena client for coordination
        device_id: Unique device identifier

    Returns:
        CrossDeviceTransferManager instance
    """
    return CrossDeviceTransferManager(client=client, device_id=device_id)
