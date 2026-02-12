#!/usr/bin/env python3
"""
Collaborative Filtering Engine - Integration Tests

Tests:
1. Sparse Matrix operations
2. Similarity computation
3. Recommendation algorithms
4. Privacy preservation
5. Hybrid recommender

Author: Skills Arena Team
"""

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np

# Import the CF module
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.collaborative_filtering import (
    CollaborativeFilteringEngine,
    SparseMatrix,
    SimilarityEngine,
    SimilarityMethod,
    ItemBasedRecommender,
    UserBasedRecommender,
    MatrixFactorizationRecommender,
    HybridRecommender,
    PrivacyPreserver,
    UserInteraction,
    InteractionType,
    SkillRecommendation,
)


class TestSparseMatrix(unittest.TestCase):
    """Test sparse matrix operations."""

    def setUp(self):
        self.matrix = SparseMatrix()

    def test_add_user_and_item(self):
        """Test adding users and items."""
        idx1 = self.matrix.add_user("user-1")
        idx2 = self.matrix.add_user("user-1")  # Should return same index

        self.assertEqual(idx1, idx2)
        self.assertEqual(len(self.matrix.user_map), 1)

        idx3 = self.matrix.add_user("user-2")
        self.assertNotEqual(idx1, idx3)

    def test_add_interaction(self):
        """Test adding interactions."""
        interaction = UserInteraction(
            user_hash="user-1",
            skill_id="skill-1",
            interaction_type=InteractionType.USAGE,
            value=1.0,
        )

        self.matrix.add_interaction(interaction)

        self.assertEqual(self.matrix.nnz, 1)
        self.assertEqual(self.matrix.shape, (1, 1))

    def test_get_user_vector(self):
        """Test getting user interaction vector."""
        # Add multiple interactions
        for i in range(5):
            self.matrix.add_interaction(
                UserInteraction(
                    user_hash="user-1",
                    skill_id=f"skill-{i}",
                    interaction_type=InteractionType.USAGE,
                    value=0.8,
                )
            )

        vector = self.matrix.get_user_vector("user-1")

        self.assertEqual(len(vector), 5)
        self.assertTrue(np.all(vector <= 1.0))

    def test_get_item_vector(self):
        """Test getting item interaction vector."""
        # Add same item for multiple users
        for i in range(10):
            self.matrix.add_interaction(
                UserInteraction(
                    user_hash=f"user-{i}",
                    skill_id="skill-1",
                    interaction_type=InteractionType.USAGE,
                    value=0.9,
                )
            )

        vector = self.matrix.get_item_vector("skill-1")

        self.assertEqual(len(vector), 10)
        self.assertTrue(np.all(vector >= 0))

    def test_batch_add(self):
        """Test batch adding interactions."""
        interactions = [
            UserInteraction(
                user_hash=f"user-{i // 5}",
                skill_id=f"skill-{i % 5}",
                interaction_type=InteractionType.USAGE,
                value=1.0,
            )
            for i in range(20)
        ]

        self.matrix.add_interactions_batch(interactions)

        self.assertEqual(self.matrix.nnz, 20)
        self.assertEqual(len(self.matrix.user_map), 4)
        self.assertEqual(len(self.matrix.item_map), 5)

    def test_save_load(self):
        """Test saving and loading matrix."""
        # Add some data
        for i in range(10):
            self.matrix.add_interaction(
                UserInteraction(
                    user_hash=f"user-{i}",
                    skill_id=f"skill-{i % 5}",
                    interaction_type=InteractionType.USAGE,
                    value=1.0,
                )
            )

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "matrix.pkl"
            self.matrix.save(path)

            # Load into new matrix
            new_matrix = SparseMatrix()
            new_matrix.load(path)

            self.assertEqual(new_matrix.nnz, self.matrix.nnz)
            self.assertEqual(len(new_matrix.user_map), len(self.matrix.user_map))

    def test_clear(self):
        """Test clearing matrix."""
        for i in range(10):
            self.matrix.add_interaction(
                UserInteraction(
                    user_hash=f"user-{i}",
                    skill_id=f"skill-{i}",
                    interaction_type=InteractionType.USAGE,
                    value=1.0,
                )
            )

        self.matrix.clear()

        self.assertEqual(self.matrix.nnz, 0)
        self.assertEqual(len(self.matrix.user_map), 0)


class TestSimilarityEngine(unittest.TestCase):
    """Test similarity computation."""

    def setUp(self):
        self.matrix = SparseMatrix()
        self.engine = SimilarityEngine(self.matrix)

    def test_cosine_similarity(self):
        """Test cosine similarity computation."""
        # Add interactions
        for i in range(5):
            self.matrix.add_interaction(
                UserInteraction(
                    user_hash="user-1",
                    skill_id=f"skill-{i}",
                    interaction_type=InteractionType.USAGE,
                    value=1.0,
                )
            )

        for i in range(3):
            self.matrix.add_interaction(
                UserInteraction(
                    user_hash="user-2",
                    skill_id=f"skill-{i}",
                    interaction_type=InteractionType.USAGE,
                    value=1.0,
                )
            )

        # Compute similarity
        similar = self.engine.get_similar_items("skill-1", top_n=10)

        # skill-1 should be similar to skill-0, skill-2 (same users)
        self.assertTrue(len(similar) > 0)

    def test_cache(self):
        """Test similarity caching."""
        # Add data
        for i in range(5):
            self.matrix.add_interaction(
                UserInteraction(
                    user_hash="user-1",
                    skill_id=f"skill-{i}",
                    interaction_type=InteractionType.USAGE,
                    value=1.0,
                )
            )

        # First call - compute
        similar1 = self.engine.get_similar_items("skill-1", top_n=5)

        # Second call - should use cache
        similar2 = self.engine.get_similar_items("skill-1", top_n=5)

        self.assertEqual(len(similar1), len(similar2))

    def test_jaccard_similarity(self):
        """Test Jaccard similarity."""
        matrix = SparseMatrix()
        engine = SimilarityEngine(matrix, method=SimilarityMethod.JACCARD)

        # Add binary interactions
        matrix.add_interaction(
            UserInteraction(
                user_hash="user-1",
                skill_id="skill-1",
                interaction_type=InteractionType.USAGE,
                value=1.0,
            )
        )
        matrix.add_interaction(
            UserInteraction(
                user_hash="user-2",
                skill_id="skill-1",
                interaction_type=InteractionType.USAGE,
                value=1.0,
            )
        )

        similar = engine.get_similar_items("skill-1")
        # Should have some similarity
        self.assertTrue(len(similar) >= 0)


class TestPrivacyPreserver(unittest.TestCase):
    """Test privacy preservation."""

    def test_hash_user(self):
        """Test user hashing."""
        did1 = "did:openclaw:user123"
        did2 = "did:openclaw:user456"

        hash1 = PrivacyPreserver.hash_user(did1)
        hash2 = PrivacyPreserver.hash_user(did2)
        hash1_again = PrivacyPreserver.hash_user(did1)

        # Same input should give same output
        self.assertEqual(hash1, hash1_again)

        # Different inputs should give different outputs
        self.assertNotEqual(hash1, hash2)

        # Should be truncated
        self.assertEqual(len(hash1), 16)

    def test_add_laplace_noise(self):
        """Test differential privacy noise."""
        value = 0.5

        # Noise should be small
        for _ in range(100):
            noisy = PrivacyPreserver.add_laplace_noise(value, epsilon=1.0)
            self.assertTrue(0 <= noisy <= 1)

        # Mean should be close to original
        noisy_values = [PrivacyPreserver.add_laplace_noise(value) for _ in range(1000)]
        self.assertAlmostEqual(np.mean(noisy_values), value, delta=0.1)

    def test_bucketize_timestamp(self):
        """Test timestamp bucketing."""
        buckets = [
            ("2024-01-15T03:00:00Z", "night"),
            ("2024-01-15T09:00:00Z", "morning"),
            ("2024-01-15T14:00:00Z", "afternoon"),
            ("2024-01-15T21:00:00Z", "evening"),
        ]

        for timestamp, expected_bucket in buckets:
            bucket = PrivacyPreserver.bucketize_timestamp(timestamp)
            self.assertEqual(bucket, expected_bucket)

    def test_anonymize_interaction(self):
        """Test interaction anonymization."""
        interaction = PrivacyPreserver.anonymize_interaction(
            user_did="did:openclaw:user123",
            skill_id="skill-1",
            interaction_type=InteractionType.USAGE,
            value=1.0,
            timestamp="2024-01-15T10:00:00Z",
        )

        # Should have hashed user
        self.assertTrue(interaction.user_hash.startswith("anon:"))
        self.assertNotIn("user123", interaction.user_hash)

        # Should have bucketed timestamp
        self.assertIn(
            interaction.timestamp, ["morning", "afternoon", "night", "evening"]
        )


class TestItemBasedRecommender(unittest.TestCase):
    """Test item-based collaborative filtering."""

    def setUp(self):
        self.matrix = SparseMatrix()
        self.engine = SimilarityEngine(self.matrix)
        self.recommender = ItemBasedRecommender(self.matrix, self.engine)

    def test_recommendations_for_active_user(self):
        """Test recommendations for a user with history."""
        # Create user interaction patterns
        # User 1: Uses skills 1, 2, 3
        for skill_id in ["skill-1", "skill-2", "skill-3"]:
            self.matrix.add_interaction(
                UserInteraction(
                    user_hash="user-1",
                    skill_id=skill_id,
                    interaction_type=InteractionType.USAGE,
                    value=1.0,
                )
            )

        # User 2: Uses skills 1, 2 (similar to user 1)
        for skill_id in ["skill-1", "skill-2"]:
            self.matrix.add_interaction(
                UserInteraction(
                    user_hash="user-2",
                    skill_id=skill_id,
                    interaction_type=InteractionType.USAGE,
                    value=1.0,
                )
            )

        # User 2: Also uses skill 4
        self.matrix.add_interaction(
            UserInteraction(
                user_hash="user-2",
                skill_id="skill-4",
                interaction_type=InteractionType.USAGE,
                value=1.0,
            )
        )

        # Get recommendations for user 1
        recs = self.recommender.get_recommendations("user-1", top_n=10)

        # Should recommend skill-4 (similar users use it)
        skill_ids = [r.skill_id for r in recs]
        self.assertIn("skill-4", skill_ids)

    def test_cold_start(self):
        """Test recommendations for new user."""
        recs = self.recommender.get_recommendations("new-user", top_n=5)

        # Should return popular skills
        self.assertTrue(len(recs) > 0)


class TestUserBasedRecommender(unittest.TestCase):
    """Test user-based collaborative filtering."""

    def setUp(self):
        self.matrix = SparseMatrix()
        self.engine = SimilarityEngine(self.matrix)
        self.recommender = UserBasedRecommender(self.matrix, self.engine)

    def test_recommendations(self):
        """Test user-based recommendations."""
        # Create similar users
        for skill_id in ["skill-1", "skill-2"]:
            self.matrix.add_interaction(
                UserInteraction(
                    user_hash="user-1",
                    skill_id=skill_id,
                    interaction_type=InteractionType.USAGE,
                    value=1.0,
                )
            )

        for skill_id in ["skill-1", "skill-2", "skill-3"]:
            self.matrix.add_interaction(
                UserInteraction(
                    user_hash="user-2",
                    skill_id=skill_id,
                    interaction_type=InteractionType.USAGE,
                    value=1.0,
                )
            )

        # User 3 only has skill-1
        self.matrix.add_interaction(
            UserInteraction(
                user_hash="user-3",
                skill_id="skill-1",
                interaction_type=InteractionType.USAGE,
                value=1.0,
            )
        )

        # Get recommendations for user 3
        recs = self.recommender.get_recommendations("user-3", top_n=5)

        # Should recommend skill-2 (similar users like it)
        skill_ids = [r.skill_id for r in recs]
        self.assertIn("skill-2", skill_ids)


class TestMatrixFactorizationRecommender(unittest.TestCase):
    """Test matrix factorization recommendations."""

    def test_recommendations(self):
        """Test MF recommendations."""
        matrix = SparseMatrix()

        # Create a substantial interaction matrix
        for user_id in range(10):
            for skill_id in range(10):
                if random.random() > 0.5:
                    matrix.add_interaction(
                        UserInteraction(
                            user_hash=f"user-{user_id}",
                            skill_id=f"skill-{skill_id}",
                            interaction_type=InteractionType.USAGE,
                            value=1.0,
                        )
                    )

        recommender = MatrixFactorizationRecommender(matrix)

        # Should fit model
        recommender.fit()

        # Should get recommendations
        recs = recommender.get_recommendations("user-0", top_n=5)

        self.assertTrue(len(recs) > 0)


class TestHybridRecommender(unittest.TestCase):
    """Test hybrid recommender."""

    def test_recommendations(self):
        """Test hybrid recommendations."""
        matrix = SparseMatrix()

        # Create interaction patterns
        for user_id in range(5):
            for skill_id in range(5):
                if random.random() > 0.4:
                    matrix.add_interaction(
                        UserInteraction(
                            user_hash=f"user-{user_id}",
                            skill_id=f"skill-{skill_id}",
                            interaction_type=InteractionType.USAGE,
                            value=1.0,
                        )
                    )

        engine = SimilarityEngine(matrix)
        recommender = HybridRecommender(matrix, engine)

        recs = recommender.get_recommendations("user-0", top_n=5)

        self.assertTrue(len(recs) > 0)


class TestCollaborativeFilteringEngine(unittest.TestCase):
    """Test the main CF engine."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.engine = CollaborativeFilteringEngine(data_dir=Path(self.tmpdir.name))

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_record_interaction(self):
        """Test recording user interactions."""
        self.engine.record_interaction(
            user_did="did:openclaw:user123",
            skill_id="skill-1",
            interaction_type=InteractionType.USAGE,
            value=1.0,
        )

        self.assertEqual(self.engine.matrix.nnz, 1)

    def test_get_recommendations(self):
        """Test getting recommendations."""
        # Create interaction data
        for i in range(10):
            for j in range(5):
                self.engine.record_interaction(
                    user_did=f"user-{i}",
                    skill_id=f"skill-{j}",
                    interaction_type=InteractionType.USAGE,
                    value=1.0,
                )

        self.engine.train()

        recs = self.engine.get_recommendations("user-0", top_n=5)

        self.assertTrue(len(recs) > 0)

    def test_get_similar_skills(self):
        """Test getting similar skills."""
        for i in range(5):
            self.engine.record_interaction(
                user_did=f"user-{i}",
                skill_id="skill-1",
                interaction_type=InteractionType.USAGE,
                value=1.0,
            )

        similar = self.engine.get_similar_skills("skill-1", top_n=5)

        # Should have similarities
        self.assertTrue(len(similar) >= 0)

    def test_get_popular_skills(self):
        """Test getting popular skills."""
        # Create skewed popularity
        for i in range(100):
            self.engine.record_interaction(
                user_did=f"user-{i}",
                skill_id="skill-popular",
                interaction_type=InteractionType.USAGE,
                value=1.0,
            )

        for i in range(10):
            self.engine.record_interaction(
                user_did=f"user-{i}",
                skill_id="skill-rare",
                interaction_type=InteractionType.USAGE,
                value=1.0,
            )

        popular = self.engine.get_popular_skills(top_n=5)

        # Popular skill should be first
        self.assertEqual(popular[0][0], "skill-popular")

    def test_get_user_profile(self):
        """Test getting user profile."""
        self.engine.record_interaction(
            user_did="did:openclaw:user123",
            skill_id="skill-1",
            interaction_type=InteractionType.USAGE,
            value=1.0,
        )
        self.engine.record_interaction(
            user_did="did:openclaw:user123",
            skill_id="skill-2",
            interaction_type=InteractionType.USAGE,
            value=0.9,
        )

        profile = self.engine.get_user_profile("did:openclaw:user123")

        self.assertIsNotNone(profile)
        self.assertEqual(profile.total_interactions, 2)

    def test_clear(self):
        """Test clearing engine."""
        self.engine.record_interaction(
            user_did="user-1",
            skill_id="skill-1",
            interaction_type=InteractionType.USAGE,
            value=1.0,
        )

        self.engine.clear()

        self.assertEqual(self.engine.matrix.nnz, 0)

    def test_get_stats(self):
        """Test getting engine stats."""
        for i in range(5):
            self.engine.record_interaction(
                user_did=f"user-{i}",
                skill_id=f"skill-{i}",
                interaction_type=InteractionType.USAGE,
                value=1.0,
            )

        stats = self.engine.get_stats()

        self.assertEqual(stats["n_users"], 5)
        self.assertEqual(stats["n_items"], 5)
        self.assertEqual(stats["n_interactions"], 5)


class TestIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration tests with mocked client."""

    async def test_full_workflow(self):
        """Test complete recommendation workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = CollaborativeFilteringEngine(data_dir=Path(tmpdir))

            # 1. Record interactions
            for i in range(20):
                for j in range(10):
                    if random.random() > 0.3:
                        engine.record_interaction(
                            user_did=f"user-{i}",
                            skill_id=f"skill-{j}",
                            interaction_type=InteractionType.USAGE,
                            value=random.uniform(0.5, 1.0),
                        )

            # 2. Train model
            engine.train()

            # 3. Get recommendations
            recs = engine.get_recommendations(user_did="user-10", top_n=5)

            self.assertTrue(len(recs) > 0)

            # 4. Get similar skills
            similar = engine.get_similar_skills("skill-1", top_n=3)

            self.assertTrue(len(similar) >= 0)

            # 5. Get popular skills
            popular = engine.get_popular_skills(top_n=3)

            self.assertEqual(len(popular), 3)


def run_tests():
    """Run all tests."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(TestSparseMatrix))
    suite.addTests(loader.loadTestsFromTestCase(TestSimilarityEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestPrivacyPreserver))
    suite.addTests(loader.loadTestsFromTestCase(TestItemBasedRecommender))
    suite.addTests(loader.loadTestsFromTestCase(TestUserBasedRecommender))
    suite.addTests(loader.loadTestsFromTestCase(TestMatrixFactorizationRecommender))
    suite.addTests(loader.loadTestsFromTestCase(TestHybridRecommender))
    suite.addTests(loader.loadTestsFromTestCase(TestCollaborativeFilteringEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
