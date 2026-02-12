#!/usr/bin/env python3
"""
Phase 3: Advanced Collaborative Filtering - Tests

Tests:
1. Matrix Factorization (SVD, ALS, BPR)
2. Context-Aware Recommendations
3. Incremental Updates
4. A/B Testing Framework
5. Multi-Armed Bandit

Author: Skills Arena Team
"""

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import scipy.sparse as sp

import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from scripts.collaborative_filtering.phase3.matrix_factorization import (
    FactorizationMethod,
    ContextType,
    Context,
    ABTest,
    ABTestResult,
    SVDFactorizer,
    ALSFactorizer,
    BPRFactorizer,
    ContextEngine,
    IncrementalUpdater,
    ABTestingFramework,
    BanditOptimizer,
    AdvancedRecommender,
)


class TestSVDFactorizer(unittest.TestCase):
    """Test SVD factorization."""

    def test_svd_fit(self):
        """Test SVD model fitting."""
        factorizer = SVDFactorizer(n_factors=10)

        # Create test matrix
        np.random.seed(42)
        matrix = sp.random(100, 50, density=0.1, format="csr")

        factorizer.fit(matrix)

        self.assertTrue(factorizer._is_fitted)
        self.assertEqual(factorizer.user_factors.shape[1], 10)
        self.assertEqual(factorizer.item_factors.shape[1], 10)

    def test_svd_predict(self):
        """Test rating prediction."""
        factorizer = SVDFactorizer(n_factors=10)

        np.random.seed(42)
        factorizer.user_factors = np.random.rand(10, 5)
        factorizer.item_factors = np.random.rand(20, 5)
        factorizer.global_mean = 0.5
        factorizer._is_fitted = True

        pred = factorizer.predict(0, 0)

        self.assertTrue(0 <= pred <= 1)

    def test_svd_recommendations(self):
        """Test recommendation generation."""
        factorizer = SVDFactorizer(n_factors=10)

        np.random.seed(42)
        factorizer.user_factors = np.random.rand(10, 5)
        factorizer.item_factors = np.random.rand(20, 5)
        factorizer.global_mean = 0.5
        factorizer._is_fitted = True

        recs = factorizer.recommend_for_user(0, top_n=5)

        self.assertEqual(len(recs), 5)
        self.assertTrue(all(isinstance(i, int) for i, _ in recs))
        self.assertTrue(all(0 <= s <= 1 for _, s in recs))


class TestALSFactorizer(unittest.TestCase):
    """Test ALS factorization."""

    def test_als_fit(self):
        """Test ALS model fitting."""
        factorizer = ALSFactorizer(n_factors=10, n_iterations=5)

        np.random.seed(42)
        matrix = sp.random(50, 30, density=0.2, format="csr")

        factorizer.fit(matrix)

        self.assertTrue(factorizer._is_fitted)
        self.assertEqual(factorizer.user_factors.shape[1], 10)
        self.assertEqual(factorizer.item_factors.shape[1], 10)

    def test_als_bias(self):
        """Test that ALS has bias terms."""
        factorizer = ALSFactorizer(n_factors=10)

        np.random.seed(42)
        matrix = sp.random(20, 15, density=0.3, format="csr")

        factorizer.fit(matrix)

        self.assertIsNotNone(factorizer.user_bias)
        self.assertIsNotNone(factorizer.item_bias)


class TestBPRFactorizer(unittest.TestCase):
    """Test BPR factorization."""

    def test_bpr_fit(self):
        """Test BPR model fitting."""
        factorizer = BPRFactorizer(n_factors=10, n_iterations=5)

        np.random.seed(42)
        matrix = sp.random(50, 30, density=0.3, format="csr")

        factorizer.fit(matrix)

        self.assertTrue(factorizer._is_fitted)

    def test_bpr_recommendations(self):
        """Test BPR recommendations."""
        factorizer = BPRFactorizer(n_factors=10)

        np.random.seed(42)
        factorizer.user_factors = np.random.randn(10, 5)
        factorizer.item_factors = np.random.randn(20, 5)
        factorizer._is_fitted = True

        recs = factorizer.recommend_for_user(0, top_n=5)

        self.assertEqual(len(recs), 5)
        # BPR scores should be between 0 and 1 (sigmoid)
        self.assertTrue(all(0 <= s <= 1 for _, s in recs))


class TestContextEngine(unittest.TestCase):
    """Test context-aware recommendations."""

    def test_context_interaction(self):
        """Test adding contextual interactions."""
        factorizer = SVDFactorizer(n_factors=5)
        factorizer._is_fitted = True
        factorizer.user_factors = np.random.rand(10, 5)
        factorizer.item_factors = np.random.rand(20, 5)

        engine = ContextEngine(factorizer)

        # Create contextual interaction
        from scripts.collaborative_filtering.phase3.matrix_factorization import (
            ContextualInteraction,
        )

        interaction = ContextualInteraction(
            user_hash="user-1",
            skill_id="skill-1",
            value=1.0,
            contexts=[Context(context_type=ContextType.TIME_OF_DAY, value="morning")],
        )

        engine.add_context_interaction(interaction)

        self.assertIn("time_of_day", engine.context_factors)
        self.assertIn("morning", engine.context_factors["time_of_day"])

    def test_context_recommendations(self):
        """Test context-aware recommendations."""
        factorizer = SVDFactorizer(n_factors=5)
        factorizer._is_fitted = True
        factorizer.user_factors = np.random.rand(10, 5)
        factorizer.item_factors = np.random.rand(20, 5)

        engine = ContextEngine(factorizer)

        contexts = [Context(context_type=ContextType.TIME_OF_DAY, value="afternoon")]

        recs = engine.recommend_with_context(0, contexts, top_n=5)

        self.assertEqual(len(recs), 5)


class TestIncrementalUpdater(unittest.TestCase):
    """Test incremental updates."""

    def test_add_update(self):
        """Test adding updates to queue."""
        factorizer = SVDFactorizer(n_factors=5)
        factorizer._is_fitted = True
        factorizer.user_factors = np.random.rand(10, 5)
        factorizer.item_factors = np.random.rand(20, 5)

        updater = IncrementalUpdater(factorizer)

        # Add some updates
        for i in range(50):
            updater.add_update(
                random.randint(0, 9), random.randint(0, 19), random.uniform(0.5, 1.0)
            )

        # Should have processed batch
        self.assertLessEqual(len(updater.update_queue), 50)


class TestABTestingFramework(unittest.TestCase):
    """Test A/B testing framework."""

    def test_create_test(self):
        """Test creating an A/B test."""
        framework = ABTestingFramework()

        test_id = framework.create_test(
            name="Test SVD vs ALS", variant_a="svd", variant_b="als", traffic_split=0.5
        )

        self.assertIn(test_id, framework.tests)
        self.assertEqual(framework.tests[test_id].name, "Test SVD vs ALS")

    def test_assign_variant(self):
        """Test variant assignment."""
        framework = ABTestingFramework()

        test_id = framework.create_test(
            name="Test", variant_a="a", variant_b="b", traffic_split=0.5
        )

        # Assign same user twice - should be consistent
        variant1 = framework.assign_variant("user-1", test_id)
        variant2 = framework.assign_variant("user-1", test_id)

        self.assertEqual(variant1, variant2)

    def test_record_metric(self):
        """Test recording metrics."""
        framework = ABTestingFramework()

        test_id = framework.create_test(name="Test", variant_a="a", variant_b="b")

        # Record metrics
        for _ in range(100):
            framework.record_metric(test_id, "a", random.uniform(0.1, 0.5))
            framework.record_metric(test_id, "b", random.uniform(0.1, 0.5))

        self.assertEqual(len(framework.test_metrics[test_id]["a"]), 100)
        self.assertEqual(len(framework.test_metrics[test_id]["b"]), 100)

    def test_compute_results(self):
        """Test computing test results."""
        framework = ABTestingFramework()

        test_id = framework.create_test(
            name="Test", variant_a="a", variant_b="b", traffic_split=0.5
        )

        # Record metrics with clear winner
        for _ in range(200):
            framework.record_metric(test_id, "a", 0.3)
            framework.record_metric(test_id, "b", 0.5)

        result = framework.compute_results(test_id)

        self.assertIsNotNone(result)
        self.assertGreater(result.variant_b_metric, result.variant_a_metric)
        self.assertGreater(result.improvement, 0)


class TestBanditOptimizer(unittest.TestCase):
    """Test multi-armed bandit."""

    def test_thompson_sampling(self):
        """Test Thompson Sampling selection."""
        bandit = BanditOptimizer(n_arms=4, method="thompson")

        # Select a few arms
        selections = [bandit.select_arm() for _ in range(10)]

        self.assertTrue(all(0 <= s < 4 for s in selections))

    def test_update(self):
        """Test bandit update."""
        bandit = BanditOptimizer(n_arms=4)

        arm = bandit.select_arm()
        bandit.update(arm, 0.8)

        stats = bandit.get_stats()
        self.assertEqual(stats["counts"][arm], 1)
        self.assertEqual(stats["successes"][arm], 1)

    def test_exploitation(self):
        """Test that bandit learns best arm."""
        bandit = BanditOptimizer(n_arms=3)

        # Train: arm 1 is clearly best
        for _ in range(100):
            arm = bandit.select_arm()
            if arm == 1:
                bandit.update(arm, 0.9)  # Reward for arm 1
            else:
                bandit.update(arm, 0.1)  # Low reward for others

        stats = bandit.get_stats()

        # Arm 1 should have highest value
        self.assertEqual(stats["best_arm"], 1)


class TestAdvancedRecommender(unittest.TestCase):
    """Test the complete advanced recommender."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.engine = AdvancedRecommender(data_dir=Path(self.tmpdir.name))

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_add_interaction(self):
        """Test adding interactions."""
        self.engine.add_interaction(user_hash="user-1", skill_id="skill-1", value=1.0)

        self.assertEqual(len(self.engine.interactions), 1)

    def test_train(self):
        """Test training the model."""
        # Add enough interactions
        for i in range(50):
            for j in range(20):
                self.engine.add_interaction(
                    user_hash=f"user-{i}",
                    skill_id=f"skill-{j}",
                    value=random.uniform(0.5, 1.0),
                )

        result = self.engine.train(method="als")

        self.assertEqual(result["status"], "success")
        self.assertTrue(self.engine.als._is_fitted)

    def test_recommend(self):
        """Test generating recommendations."""
        # Add interactions
        for i in range(30):
            for j in range(15):
                self.engine.add_interaction(
                    user_hash=f"user-{i}",
                    skill_id=f"skill-{j}",
                    value=random.uniform(0.5, 1.0),
                )

        # Train
        self.engine.train(method="als")

        # Get recommendations
        recs = self.engine.recommend("user-5", top_n=5)

        self.assertEqual(len(recs), 5)
        self.assertTrue(all("skill_id" in r for r in recs))
        self.assertTrue(all("score" in r for r in recs))

    def test_ab_test(self):
        """Test A/B testing integration."""
        test_id = self.engine.create_ab_test(
            name="Test SVD vs ALS", method_a="svd", method_b="als"
        )

        self.assertIsNotNone(test_id)

        # Assign and record
        for i in range(20):
            variant = self.engine.assign_to_test(f"user-{i}", test_id)
            self.engine.record_ab_metric(test_id, variant, random.uniform(0.1, 0.5))

        result = self.engine.get_ab_results(test_id)
        self.assertIsNotNone(result)

    def test_get_stats(self):
        """Test getting engine statistics."""
        # Add some data
        for i in range(10):
            self.engine.add_interaction(
                user_hash=f"user-{i}", skill_id=f"skill-{i}", value=0.8
            )

        stats = self.engine.get_stats()

        self.assertEqual(stats["n_interactions"], 10)
        self.assertEqual(stats["n_users"], 10)
        self.assertEqual(stats["n_items"], 10)


class TestIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration tests."""

    async def test_full_workflow(self):
        """Test complete Phase 3 workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = AdvancedRecommender(data_dir=Path(tmpdir))

            # Add contextual interactions
            for i in range(50):
                contexts = [
                    Context(
                        context_type=ContextType.TIME_OF_DAY,
                        value=["morning", "afternoon", "evening"][i % 3],
                    )
                ]
                engine.add_interaction(
                    user_hash=f"user-{i % 30}",
                    skill_id=f"skill-{i % 20}",
                    value=random.uniform(0.5, 1.0),
                    contexts=contexts,
                )

            # Train all methods
            for method in ["svd", "als", "bpr"]:
                result = engine.train(method)
                self.assertEqual(result["status"], "success")

            # Test recommendations
            recs = engine.recommend("user-5", top_n=5)
            self.assertEqual(len(recs), 5)

            # Test A/B test
            test_id = engine.create_ab_test("Test", "svd", "als")
            for i in range(50):
                variant = engine.assign_to_test(f"user-{i}", test_id)
                engine.record_ab_metric(test_id, variant, random.uniform(0.1, 0.5))

            result = engine.get_ab_results(test_id)
            self.assertIsNotNone(result)


def run_tests():
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestSVDFactorizer))
    suite.addTests(loader.loadTestsFromTestCase(TestALSFactorizer))
    suite.addTests(loader.loadTestsFromTestCase(TestBPRFactorizer))
    suite.addTests(loader.loadTestsFromTestCase(TestContextEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestIncrementalUpdater))
    suite.addTests(loader.loadTestsFromTestCase(TestABTestingFramework))
    suite.addTests(loader.loadTestsFromTestCase(TestBanditOptimizer))
    suite.addTests(loader.loadTestsFromTestCase(TestAdvancedRecommender))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
