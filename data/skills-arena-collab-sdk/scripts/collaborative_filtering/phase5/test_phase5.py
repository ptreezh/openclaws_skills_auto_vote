#!/usr/bin/env python3
"""
Phase 5: Advanced Federated Learning - Tests

Tests:
1. Hierarchical Federated Learning
2. Personalized Federated Learning
3. Asynchronous Updates
4. Continual Learning
5. Complete System Integration

Author: Skills Arena Team
"""

import asyncio
import tempfile
import unittest
from pathlib import Path
import random
import numpy as np

import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from scripts.collaborative_filtering.phase5.advanced_federated import (
    HFLTopology,
    PersonalizationStrategy,
    UpdateMode,
    HFLConfig,
    PFLConfig,
    AsynchronousConfig,
    ContinualLearningConfig,
    EdgeServer,
    HierarchicalFederatedCoordinator,
    PersonalizedFederatedLearner,
    AsynchronousUpdateManager,
    ContinualLearningManager,
    ExperienceBuffer,
    AdvancedFederatedSystem,
)


class TestHFLConfig(unittest.TestCase):
    """Test HFL configuration."""

    def test_defaults(self):
        config = HFLConfig()
        self.assertEqual(config.topology, HFLTopology.TWO_TIER)
        self.assertEqual(config.n_edge_servers, 5)
        self.assertEqual(config.clients_per_edge, 20)

    def test_to_dict(self):
        config = HFLConfig(topology=HFLTopology.THREE_TIER, n_edge_servers=10)
        data = config.to_dict()
        self.assertEqual(data["topology"], "three_tier")
        self.assertEqual(data["n_edge_servers"], 10)


class TestEdgeServer(unittest.TestCase):
    """Test edge server."""

    def test_register_client(self):
        server = EdgeServer("edge-1", "us-east")

        server.register_client("client-1")
        server.register_client("client-2")

        self.assertEqual(len(server.clients), 2)

    def test_aggregate_local(self):
        server = EdgeServer("edge-1", "us-east")

        # Create updates
        updates = [
            {"user_factors": np.ones((10, 5)), "item_factors": np.ones((5, 3))},
            {"user_factors": np.ones((10, 5)) * 2, "item_factors": np.ones((5, 3)) * 2},
        ]

        aggregated = server.aggregate_local(updates)

        self.assertIn("user_factors", aggregated)
        self.assertEqual(server.round_count, 1)

    def test_get_stats(self):
        server = EdgeServer("edge-1", "eu-west")
        server.register_client("client-1")

        stats = server.get_stats()

        self.assertEqual(stats["server_id"], "edge-1")
        self.assertEqual(stats["region"], "eu-west")
        self.assertEqual(stats["n_clients"], 1)


class TestHierarchicalFederatedCoordinator(unittest.TestCase):
    """Test HFL coordinator."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        config = HFLConfig(
            topology=HFLTopology.TWO_TIER, n_edge_servers=3, clients_per_edge=5
        )
        self.coordinator = HierarchicalFederatedCoordinator(
            config, data_dir=Path(self.tmpdir.name)
        )

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_assign_client_to_edge(self):
        edge_id = self.coordinator.assign_client_to_edge("client-1")

        self.assertTrue(edge_id.startswith("edge_"))
        self.assertIn("client-1", self.coordinator.client_to_edge)

    def test_get_topology_status(self):
        self.coordinator.assign_client_to_edge("client-1")

        status = self.coordinator.get_topology_status()

        self.assertEqual(status["topology"], "two_tier")
        self.assertEqual(status["n_edge_servers"], 3)
        self.assertEqual(status["n_clients"], 1)


class TestPFLConfig(unittest.TestCase):
    """Test PFL configuration."""

    def test_defaults(self):
        config = PFLConfig()
        self.assertEqual(config.strategy, PersonalizationStrategy.ADAPTIVE)
        self.assertEqual(config.local_epochs, 5)
        self.assertEqual(config.memory_size, 100)

    def test_strategies(self):
        for strategy in PersonalizationStrategy:
            config = PFLConfig(strategy=strategy)
            self.assertEqual(config.strategy, strategy)


class TestPersonalizedFederatedLearner(unittest.TestCase):
    """Test PFL learner."""

    def setUp(self):
        config = PFLConfig(strategy=PersonalizationStrategy.FINE_TUNING, local_epochs=2)
        self.learner = PersonalizedFederatedLearner(config)

        # Set global model
        self.global_model = {
            "user_factors": np.random.randn(100, 10).astype(np.float32) * 0.01,
            "item_factors": np.random.randn(50, 10).astype(np.float32) * 0.01,
            "global_mean": np.float32(0.5),
        }
        self.learner.set_global_model(self.global_model)

    def test_personalize_fine_tuning(self):
        local_data = [
            (random.randint(0, 99), random.randint(0, 49), random.uniform(0.5, 1.0))
            for _ in range(10)
        ]

        personal = self.learner.personalize_fine_tuning(local_data)

        self.assertIsNotNone(personal)
        self.assertIn("user_factors", personal)

    def test_personalize_clustering(self):
        client_models = {}
        for i in range(5):
            client_models[f"client-{i}"] = {
                "user_factors": np.random.randn(100, 10).astype(np.float32) * 0.01,
                "item_factors": np.random.randn(50, 10).astype(np.float32) * 0.01,
            }

        personalizations = self.learner.personalize_clustering(client_models)

        self.assertEqual(len(personalizations), 5)

    def test_get_stats(self):
        stats = self.learner.get_personalization_stats()

        self.assertEqual(stats["strategy"], "fine_tuning")
        self.assertTrue(stats["has_global_model"])
        self.assertTrue(stats["has_personal_model"])


class TestAsynchronousConfig(unittest.TestCase):
    """Test asynchronous configuration."""

    def test_defaults(self):
        config = AsynchronousConfig()
        self.assertEqual(config.mode, UpdateMode.ASYNCHRONOUS)
        self.assertEqual(config.staleness_bound, 10)

    def test_modes(self):
        for mode in UpdateMode:
            config = AsynchronousConfig(mode=mode)
            self.assertEqual(config.mode, mode)


class TestAsynchronousUpdateManager(unittest.TestCase):
    """Test async update manager."""

    def setUp(self):
        config = AsynchronousConfig(
            mode=UpdateMode.STALE_SYNCHRONOUS, staleness_bound=5
        )
        self.manager = AsynchronousUpdateManager(config)

        self.global_model = {
            "user_factors": np.random.randn(100, 10).astype(np.float32),
            "item_factors": np.random.randn(50, 10).astype(np.float32),
        }

    def test_receive_update(self):
        update = {
            "user_factors": np.random.randn(100, 10).astype(np.float32) * 0.01,
            "item_factors": np.random.randn(50, 10).astype(np.float32) * 0.01,
        }

        result = self.manager.receive_update(
            client_id="client-1", update=update, n_samples=100, timestamp=time.time()
        )

        self.assertEqual(result["status"], "accepted")
        self.assertEqual(result["staleness"], 0)

    def test_aggregate(self):
        # Add updates
        for i in range(3):
            update = {
                "user_factors": np.ones((100, 10)).astype(np.float32) * (i + 1),
                "item_factors": np.ones((50, 10)).astype(np.float32) * (i + 1),
            }
            self.manager.receive_update(f"client-{i}", update, 100, time.time())

        new_model, agg_result = self.manager.aggregate(self.global_model)

        self.assertEqual(agg_result["n_updates"], 3)
        self.assertEqual(agg_result["global_version"], 1)

    def test_staleness_rejection(self):
        # Set high version
        self.manager.global_version = 10

        update = {
            "user_factors": np.random.randn(10, 5).astype(np.float32),
            "item_factors": np.random.randn(5, 3).astype(np.float32),
        }

        result = self.manager.receive_update("client-1", update, 100, time.time())

        self.assertEqual(result["status"], "rejected")
        self.assertEqual(result["reason"], "stale")

    def test_get_stats(self):
        stats = self.manager.get_stats()

        self.assertEqual(stats["mode"], "stale_synchronous")


class TestContinualLearningConfig(unittest.TestCase):
    """Test continual learning configuration."""

    def test_defaults(self):
        config = ContinualLearningConfig()
        self.assertEqual(config.memory_size, 500)
        self.assertTrue(config.elastic_weight_consolidation)
        self.assertTrue(config.experience_replay)


class TestExperienceBuffer(unittest.TestCase):
    """Test experience replay buffer."""

    def test_add_and_sample(self):
        buffer = ExperienceBuffer(max_size=100)

        # Add experiences
        for i in range(50):
            buffer.add(
                state=np.array([i]),
                action=i % 10,
                reward=random.uniform(0, 1),
                next_state=np.array([i + 1]),
                priority=1.0,
            )

        self.assertEqual(len(buffer), 50)

        # Sample
        batch = buffer.sample(10)
        self.assertEqual(len(batch[0]), 10)

    def test_max_size_enforcement(self):
        buffer = ExperienceBuffer(max_size=20)

        for i in range(30):
            buffer.add(
                state=np.array([i]), action=i, reward=0.5, next_state=np.array([i + 1])
            )

        self.assertEqual(len(buffer), 20)


class TestContinualLearningManager(unittest.TestCase):
    """Test continual learning manager."""

    def setUp(self):
        config = ContinualLearningConfig(memory_size=100)
        self.manager = ContinualLearningManager(config)

    def test_start_new_task(self):
        self.manager.start_new_task(1)

        self.assertEqual(self.manager.current_task, 1)
        self.assertEqual(len(self.manager.task_boundaries), 1)

    def test_add_experience(self):
        self.manager.start_new_task(0)

        for i in range(10):
            self.manager.add_experience(
                state=np.array([i]), action=i, reward=0.5, next_state=np.array([i + 1])
            )

        self.assertEqual(len(self.manager.replay_buffer), 10)
        self.assertEqual(len(self.manager.episodic_memories), 1)

    def test_compute_ewc_penalty(self):
        # Set up previous weights and Fisher
        self.manager.prev_weights = {
            "user_factors": np.ones((10, 5)).astype(np.float32),
            "item_factors": np.ones((5, 3)).astype(np.float32),
        }
        self.manager.fisher_information = {
            "user_factors": np.ones((10, 5)).astype(np.float32),
            "item_factors": np.ones((5, 3)).astype(np.float32),
        }

        current_grads = {
            "user_factors": np.random.randn(10, 5).astype(np.float32),
            "item_factors": np.random.randn(5, 3).astype(np.float32),
        }

        penalty = self.manager.compute_continual_loss(current_grads)

        self.assertIn("user_factors", penalty)
        self.assertEqual(penalty["user_factors"].shape, (10, 5))

    def test_get_stats(self):
        stats = self.manager.get_stats()

        self.assertEqual(stats["current_task"], 0)
        self.assertEqual(stats["n_tasks"], 0)


class TestAdvancedFederatedSystem(unittest.TestCase):
    """Test complete advanced FL system."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()

        hfl_config = HFLConfig(n_edge_servers=2, clients_per_edge=5)
        pfl_config = PFLConfig()
        async_config = AsynchronousConfig()
        cl_config = ContinualLearningConfig()

        self.system = AdvancedFederatedSystem(
            hfl_config,
            pfl_config,
            async_config,
            cl_config,
            data_dir=Path(self.tmpdir.name) / "test",
        )

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_initialize(self):
        self.system.initialize((100, 50))

        self.assertIsNotNone(self.system.global_model)
        self.assertIn("user_factors", self.system.global_model)

    def test_register_client(self):
        self.system.initialize((100, 50))

        edge_id = self.system.register_client("client-1")

        self.assertTrue(edge_id.startswith("edge_"))

    def test_process_client_update(self):
        self.system.initialize((100, 50))

        local_data = [
            (random.randint(0, 99), random.randint(0, 49), random.uniform(0.5, 1.0))
            for _ in range(10)
        ]

        update = {
            "user_factors": np.random.randn(100, 10).astype(np.float32) * 0.01,
            "item_factors": np.random.randn(50, 10).astype(np.float32) * 0.01,
        }

        result = self.system.process_client_update(
            client_id="client-1", update=update, local_data=local_data
        )

        self.assertEqual(result["status"], "accepted")

    def test_run_round(self):
        self.system.initialize((100, 50))

        for i in range(5):
            self.system.register_client(f"client_{i}")

        result = self.system.run_round()

        self.assertEqual(result["round"], 1)


class TestIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration tests."""

    async def test_full_system(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup
            hfl_config = HFLConfig(n_edge_servers=2, clients_per_edge=5)
            pfl_config = PFLConfig(strategy=PersonalizationStrategy.FINE_TUNING)
            async_config = AsynchronousConfig(mode=UpdateMode.ASYNCHRONOUS)
            cl_config = ContinualLearningConfig()

            system = AdvancedFederatedSystem(
                hfl_config, pfl_config, async_config, cl_config, data_dir=Path(tmpdir)
            )

            # Initialize
            system.initialize((100, 50))

            # Register clients
            for i in range(5):
                system.register_client(f"client_{i}")

            # Process updates
            for i in range(5):
                local_data = [
                    (
                        random.randint(0, 99),
                        random.randint(0, 49),
                        random.uniform(0.5, 1.0),
                    )
                    for _ in range(10)
                ]

                if system.global_model:
                    update = {
                        k: v + np.random.randn(*v.shape) * 0.01
                        for k, v in system.global_model.items()
                    }
                else:
                    update = {
                        "user_factors": np.random.randn(100, 10).astype(np.float32)
                        * 0.01,
                        "item_factors": np.random.randn(50, 10).astype(np.float32)
                        * 0.01,
                    }

                system.process_client_update(f"client_{i}", update, local_data)

            # Run rounds
            results = system.train(n_rounds=3)

            self.assertEqual(len(results), 3)


def run_tests():
    import sys

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestHFLConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeServer))
    suite.addTests(loader.loadTestsFromTestCase(TestHierarchicalFederatedCoordinator))
    suite.addTests(loader.loadTestsFromTestCase(TestPFLConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestPersonalizedFederatedLearner))
    suite.addTests(loader.loadTestsFromTestCase(TestAsynchronousConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestAsynchronousUpdateManager))
    suite.addTests(loader.loadTestsFromTestCase(TestContinualLearningConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestExperienceBuffer))
    suite.addTests(loader.loadTestsFromTestCase(TestContinualLearningManager))
    suite.addTests(loader.loadTestsFromTestCase(TestAdvancedFederatedSystem))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
