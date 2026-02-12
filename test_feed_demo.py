"""
Demonstration script for Feed Algorithm (without database).

This script demonstrates the hot score calculation logic
without requiring a running database.
"""
from datetime import datetime, timedelta
from scripts.feed_algorithm import FeedAlgorithm


def demonstrate_hot_algorithm():
    """Demonstrate the hot algorithm with sample data."""
    feed_algo = FeedAlgorithm()

    print("=" * 60)
    print("Reddit-Style Hot Algorithm Demonstration")
    print("=" * 60)
    print()

    # Sample skills with different vote patterns and ages
    skills = [
        {
            'name': 'Popular Old Skill',
            'upvotes': 100,
            'downvotes': 10,
            'age_hours': 48,
            'description': 'High votes, very old'
        },
        {
            'name': 'Trending New Skill',
            'upvotes': 50,
            'downvotes': 5,
            'age_hours': 2,
            'description': 'Medium votes, very new'
        },
        {
            'name': 'New Skill',
            'upvotes': 10,
            'downvotes': 2,
            'age_hours': 0.5,
            'description': 'Low votes, extremely new'
        },
        {
            'name': 'Unvoted Skill',
            'upvotes': 0,
            'downvotes': 0,
            'age_hours': 5,
            'description': 'No votes yet'
        },
        {
            'name': 'Controversial Skill',
            'upvotes': 50,
            'downvotes': 50,
            'age_hours': 24,
            'description': 'Equal upvotes/downvotes'
        }
    ]

    # Calculate hot scores
    print("Calculating hot scores...")
    print("-" * 60)
    print(f"{'Skill':<25} {'Score':<8} {'Age':<8} {'Hot Score':<10}")
    print("-" * 60)

    results = []
    for skill in skills:
        created_at = datetime.now() - timedelta(hours=skill['age_hours'])
        hot_score = feed_algo.calculate_hot_score(
            skill['upvotes'],
            skill['downvotes'],
            created_at
        )

        net_score = skill['upvotes'] - skill['downvotes']
        results.append({
            'name': skill['name'],
            'net_score': net_score,
            'age_hours': skill['age_hours'],
            'hot_score': hot_score,
            'description': skill['description']
        })

        print(f"{skill['name']:<25} {net_score:<8} {skill['age_hours']:<8.1f} {hot_score:<10.4f}")

    print("-" * 60)
    print()

    # Sort by hot score
    print("Feed Ranking (by hot score):")
    print("-" * 60)
    results.sort(key=lambda x: x['hot_score'], reverse=True)

    for i, result in enumerate(results, 1):
        print(f"{i}. {result['name']}")
        print(f"   {result['description']}")
        print(f"   Hot Score: {result['hot_score']:.4f}")
        print()

    print("=" * 60)
    print("Key Observations:")
    print("=" * 60)
    print("1. Popular Old Skill has highest hot score (high votes + age)")
    print("2. Trending New Skill ranks well despite being newer (good vote ratio)")
    print("3. Controversial Skill ranks low (net score = 0)")
    print("4. Age boosts all scores over time (time decay = age / 1.8)")
    print("5. Logarithmic scaling prevents vote spamming")
    print()

    # Demonstrate time decay
    print("=" * 60)
    print("Time Decay Demonstration")
    print("=" * 60)
    print("Same skill (50 upvotes, 5 downvotes) at different ages:")
    print("-" * 60)

    base_votes = {'upvotes': 50, 'downvotes': 5}
    ages = [0, 1, 6, 12, 24, 48, 72]

    print(f"{'Age (hours)':<15} {'Hot Score':<15} {'Increase':<15}")
    print("-" * 60)

    prev_score = None
    for age in ages:
        created_at = datetime.now() - timedelta(hours=age)
        score = feed_algo.calculate_hot_score(
            base_votes['upvotes'],
            base_votes['downvotes'],
            created_at
        )

        increase = ""
        if prev_score is not None:
            diff = score - prev_score
            increase = f"+{diff:.4f}"

        print(f"{age:<15} {score:<15.4f} {increase:<15}")
        prev_score = score

    print("-" * 60)
    print(f"Each hour adds approximately {1/feed_algo.GRAVITY:.4f} to hot score")
    print()


if __name__ == '__main__':
    demonstrate_hot_algorithm()
