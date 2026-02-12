#!/usr/bin/env python3
"""
Phase 4: Federated Learning - Tests

Tests:
1. Federated Averaging
2. Secure Aggregation
3. Differential Privacy
4. Client Selection
5. Compression
6. Federated Coordinator
"""

import asyncio
import tempfile
import unittest
from pathlib import Path
import random
import numpy as np

import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from scripts.collaborative_filtering.phase4.federated_learning import (
    AggregationMethod,
    UpdateType,
    ClientStatus,
    FederatedConfig,
    ClientInfo,
    ModelUpdate,
    SecureAggregator,
    FederatedPrivacyMechanism,
    ClientSelector,
    FederatedAveraging,
    CompressionScheduler,
    FederatedCoordinator,
    FederatedClient,
)


class TestFederatedConfig(unittest.TestCase):
    def test_config_defaults(self):
        config = FederatedConfig()
        self.assertEqual(config.aggregation_method, AggregationMethod.FED_AVG)
        self.assertEqual(config.n_clients_per_round, 10)
        self.assertEqual(config.learning_rate, 0.01)

    def test_config_to_dict(self):
        config = FederatedConfig(
            aggregation_method=AggregationMethod.FED_AVG, n_clients_per_round=5
        )
        data = config.to_dict()
        self.assertEqual(data["aggregation_method"], "fed_avg")
        self.assertEqual(data["n_clients_per_round"], 5)


class TestSecureAggregator(unittest.TestCase):
    def test_generate_keys(self):
        aggregator = SecureAggregator()
        encrypted, public = aggregator.generate_client_keys("client-1")
        self.assertIsNotNone(encrypted)
        self.assertTrue(public.startswith(b"-----BEGIN PUBLIC KEY-----"))

    def test_encrypt_decrypt(self):
        aggregator = SecureAggregator()
        update = ModelUpdate(
            client_id="client-1",
            update_type=UpdateType.WEIGHTS,
            weights={"layer1": np.random.randn(10, 5)},
            n_samples=100,
            loss=0.5,
            accuracy=0.8,
        )
        encrypted = aggregator.encrypt_update(update, "client-1")
        decrypted = aggregator.decrypt_update(encrypted)
        self.assertEqual(decrypted.client_id, "client-1")
        self.assertTrue(
            np.allclose(decrypted.weights["layer1"], update.weights["layer1"])
        )


class TestFederatedPrivacyMechanism(unittest.TestCase):
    def test_clip_gradients(self):
        privacy = FederatedPrivacyMechanism(epsilon=1.0, clip_norm=1.0)
        gradients = {"layer1": np.random.randn(100, 50) * 2}
        clipped = privacy.clip_gradients(gradients)
        total_norm = sum(np.sum(g**2) for g in clipped.values()) ** 0.5
        self.assertLessEqual(total_norm, privacy.clip_norm * 1.1)

    def test_privacy_report(self):
        privacy = FederatedPrivacyMechanism(epsilon=1.0, delta=1e-5)
        report = privacy.create_privacy_report(10)
        self.assertEqual(report["round"], 10)


class TestClientSelector(unittest.TestCase):
    def test_select_random(self):
        selector = ClientSelector(strategy="random")
        clients = [
            ClientInfo(client_id=f"client-{i}", n_samples=100) for i in range(10)
        ]
        selected = selector.select_clients(clients, n_select=5)
        self.assertEqual(len(selected), 5)

    def test_select_power_of_choice(self):
        selector = ClientSelector(strategy="power_of_choice")
        clients = [
            ClientInfo(client_id=f"client-{i}", n_samples=100 * (i + 1))
            for i in range(5)
        ]
        selected = selector.select_clients(clients, n_select=3)
        self.assertEqual(selected[0].n_samples, 500)


class TestFederatedAveraging(unittest.TestCase):
    def test_initialize_weights(self):
        fedavg = FederatedAveraging(FederatedConfig())
        fedavg.initialize_weights((100, 50))
        self.assertIsNotNone(fedavg.global_weights)
        self.assertIn("user_factors", fedavg.global_weights)

    def test_fed_avg(self):
        fedavg = FederatedAveraging(FederatedConfig())
        fedavg.initialize_weights((100, 50))
        updates = []
        for i in range(3):
            update = ModelUpdate(
                client_id=f"client-{i}",
                update_type=UpdateType.WEIGHTS,
                weights={
                    "user_factors": np.ones((100, 50)) * (i + 1),
                    "item_factors": np.ones((50, 10)) * 0.5,
                    "user_bias": np.zeros(100),
                    "item_bias": np.zeros(50),
                    "global_mean": np.float32(0.5),
                },
                n_samples=100,
                loss=0.5,
                accuracy=0.8,
            )
            updates.append(update)
        result = fedavg.aggregate(updates, AggregationMethod.FED_AVG)
        self.assertEqual(result.total_samples, 300)
        self.assertTrue(np.allclose(result.aggregated_weights["user_factors"], 2.0))


class TestCompressionScheduler(unittest.TestCase):
    def test_sparsify(self):
        compressor = CompressionScheduler(compression_ratio=0.1)
        weights = {"layer1": np.random.randn(100, 50)}
        sparse, masks = compressor.sparsify(weights)
        kept = sum(m.sum() for m in masks.values())
        self.assertLess(kept / 5000, 0.2)

    def test_quantize(self):
        compressor = CompressionScheduler(use_quantization=True, n_bits=8)
        weights = {"layer1": np.random.randn(10, 5) * 10}
        quantized = compressor.quantize(weights)
        self.assertEqual(quantized["layer1"].dtype, np.uint8)


class TestFederatedCoordinator(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.coordinator = FederatedCoordinator(
            FederatedConfig(n_clients_per_round=3, min_clients=2),
            data_dir=Path(self.tmpdir.name),
        )

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_register_client(self):
        client = self.coordinator.register_client("client-1", n_samples=100)
        self.assertEqual(client.client_id, "client-1")
        self.assertIn("client-1", self.coordinator.clients)

    def test_run_round(self):
        for i in range(5):
            self.coordinator.register_client(f"client-{i}", n_samples=100)
        for i in range(5):
            update = ModelUpdate(
                client_id=f"client-{i}",
                update_type=UpdateType.WEIGHTS,
                weights={
                    "user_factors": np.random.randn(100, 10),
                    "item_factors": np.random.randn(50, 10),
                    "user_bias": np.zeros(100),
                    "item_bias": np.zeros(50),
                    "global_mean": np.float32(0.5),
                },
                n_samples=100,
                loss=0.5,
                accuracy=0.8,
            )
            self.coordinator.submit_update(update)
        result = self.coordinator.run_round()
        self.assertIsNotNone(result)
        self.assertEqual(result.round_number, 1)


class TestFederatedClient(unittest.TestCase):
    def test_train_local(self):
        client = FederatedClient("client-1")
        client.set_local_data(
            user_ids=list(range(50)),
            item_ids=list(range(50)),
            ratings=[0.5 + random.random() * 0.5 for _ in range(50)],
        )
        update = client.train_local()
        self.assertEqual(update.client_id, "client-1")
        self.assertEqual(update.n_samples, 50)


class TestIntegration(unittest.IsolatedAsyncioTestCase):
    async def test_full_workflow(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            coordinator = FederatedCoordinator(
                FederatedConfig(n_clients_per_round=3, min_clients=2),
                data_dir=Path(tmpdir),
            )
            for i in range(5):
                coordinator.register_client(f"client-{i}", n_samples=100)
            for round_num in range(3):
                for i in range(5):
                    update = ModelUpdate(
                        client_id=f"client-{i}",
                        update_type=UpdateType.WEIGHTS,
                        weights={
                            "user_factors": np.random.randn(100, 10),
                            "item_factors": np.random.randn(50, 10),
                            "user_bias": np.zeros(100),
                            "item_bias": np.zeros(50),
                            "global_mean": np.float32(0.5),
                        },
                        n_samples=100,
                        loss=0.5,
                        accuracy=0.8,
                    )
                    coordinator.submit_update(update)
                coordinator.run_round()
            self.assertEqual(coordinator.current_round, 3)


def run_tests():
    import sys

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestFederatedConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestSecureAggregator))
    suite.addTests(loader.loadTestsFromTestCase(TestFederatedPrivacyMechanism))
    suite.addTests(loader.loadTestsFromTestCase(TestClientSelector))
    suite.addTests(loader.loadTestsFromTestCase(TestFederatedAveraging))
    suite.addTests(loader.loadTestsFromTestCase(TestCompressionScheduler))
    suite.addTests(loader.loadTestsFromTestCase(TestFederatedCoordinator))
    suite.addTests(loader.loadTestsFromTestCase(TestFederatedClient))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
