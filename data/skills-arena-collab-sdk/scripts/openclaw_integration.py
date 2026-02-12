#!/usr/bin/env python3
"""
OpenClaw Integration with Skills Arena

This demonstrates how a real AI CLI (like OpenClaw) integrates with Skills Arena.

Architecture:
┌─────────────────────────────────────────────────────────────────────┐
│                         OpenClaw CLI                                │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │  OpenClaw Agent                                                 ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ ││
│  │  │ User Input  │→│ Intent      │→│ Route to:                │ ││
│  │  │             │  │ Classification│  │ • Built-in capability   │ ││
│  │  │             │  │             │  │ • Skill (Skills Arena)  │ ││
│  │  └─────────────┘  └─────────────┘  │ • External tool          │ ││
│  └─────────────────────────────────────────────────────────────────┘│
│                              │                                        │
│                              ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────┐│
│  │                    Skills Arena Gateway                         ││
│  │  • Discover available skills                                   ││
│  │  • Execute skills locally (LLM + sandbox)                      ││
│  │  • Cache skills metadata                                       ││
│  │  • Sync with Skills Arena platform                             ││
│  └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘

Key Points:
1. Skills are NOT called via API - LLM executes them locally
2. Skills Arena platform provides discovery, ratings, FL updates
3. Gateway handles caching and execution
4. Usage data synced back periodically

Author: Skills Arena Team
Version: 4.0.0
"""

import asyncio
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ============ OpenClaw Types ============


class IntentType(Enum):
    """User intent classification."""

    CODE_GENERATION = "code_generation"
    RESEARCH = "research"
    WRITING = "writing"
    ANALYSIS = "analysis"
    CONVERSATION = "conversation"
    SKILL_REQUEST = "skill_request"
    UNKNOWN = "unknown"


@dataclass
class UserInput:
    """User input to OpenClaw."""

    text: str
    timestamp: datetime = field(default_factory=datetime.now)
    context: Dict[str, Any] = field(default_factory=dict)
    user_id: Optional[str] = None


@dataclass
class AgentResponse:
    """Agent response to user."""

    text: str
    skill_used: Optional[str] = None
    execution_time_ms: float = 0.0
    tokens_used: int = 0
    confidence: float = 0.0
    skill_output: Optional[str] = None


# ============ Skills Arena Gateway for OpenClaw ============


class OpenClawSkillsGateway:
    """
    Gateway for OpenClaw to access Skills Arena.

    This is NOT an API client - it's a local gateway that:
    1. Caches skills metadata (synced from Skills Arena)
    2. Executes skills locally on behalf of the LLM
    3. Tracks usage and syncs back to platform
    """

    def __init__(self):
        # Skills cache (synced from Skills Arena)
        self._skills: Dict[str, Dict] = {}
        self._skills_by_category: Dict[str, List[str]] = {}

        # Usage tracking
        self._usage_log: List[Dict] = []

        # Session state
        self._session_id: Optional[str] = None
        self._user_id: Optional[str] = None

    @property
    def skills(self) -> Dict[str, Dict]:
        """Get all cached skills."""
        return self._skills

    def sync_skills_from_platform(self, skills_data: List[Dict]):
        """Sync skills metadata from Skills Arena platform."""
        self._skills.clear()
        self._skills_by_category.clear()

        for skill in skills_data:
            self._skills[skill["skill_id"]] = skill
            category = skill.get("category", "general")
            if category not in self._skills_by_category:
                self._skills_by_category[category] = []
            self._skills_by_category[category].append(skill["skill_id"])

        print(f"Synced {len(self._skills)} skills from Skills Arena")

    def get_skill(self, skill_id: str) -> Optional[Dict]:
        """Get a specific skill by ID."""
        return self._skills.get(skill_id)

    def find_best_skill(
        self, intent: IntentType, parameters: Dict[str, Any]
    ) -> Optional[Dict]:
        """Find the best skill for an intent."""
        category_map = {
            IntentType.CODE_GENERATION: ["coding", "programming"],
            IntentType.RESEARCH: ["research", "search"],
            IntentType.WRITING: ["writing", "editing"],
            IntentType.ANALYSIS: ["analysis", "data"],
        }

        categories = category_map.get(intent, ["general"])
        skills = []

        for category in categories:
            if category in self._skills_by_category:
                for skill_id in self._skills_by_category[category]:
                    skill = self._skills.get(skill_id)
                    if skill:
                        skills.append(skill)

        if not skills:
            return None

        # Return highest rated
        return max(skills, key=lambda s: s.get("rating", 0))

    def execute_skill(
        self, skill_id: str, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a skill locally.

        IMPORTANT: This is NOT an API call.
        The skill runs locally in the LLM context or sandbox.
        """
        skill = self._skills.get(skill_id)
        if not skill:
            return {"status": "error", "error": f"Skill not found: {skill_id}"}

        start_time = datetime.now()

        # Simulate skill execution (actual implementation would run the skill)
        result = {
            "skill_id": skill_id,
            "skill_name": skill.get("name", skill_id),
            "status": "success",
            "output": f"Executed {skill.get('name', skill_id)} with parameters: {parameters}",
            "execution_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
        }

        # Log usage
        self._usage_log.append(
            {
                "skill_id": skill_id,
                "parameters": parameters,
                "timestamp": datetime.now().isoformat(),
                "session_id": self._session_id,
                "user_id": self._user_id,
            }
        )

        return result

    def log_usage_to_platform(self) -> Dict:
        """Prepare usage data to sync to Skills Arena platform."""
        return {
            "session_id": self._session_id,
            "user_id": self._user_id,
            "usage_events": self._usage_log,
            "timestamp": datetime.now().isoformat(),
        }


# ============ OpenClaw Agent ============


class OpenClawAgent:
    """
    OpenClaw Agent with Skills Arena integration.

    This is a simplified version showing the key integration points.
    """

    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.gateway = OpenClawSkillsGateway()

        # Intent classifier (simplified)
        self._intent_keywords = {
            IntentType.CODE_GENERATION: [
                "write",
                "code",
                "program",
                "function",
                "class",
            ],
            IntentType.RESEARCH: [
                "search",
                "find",
                "look up",
                "research",
                "information",
            ],
            IntentType.WRITING: ["write", "edit", "draft", "compose", "create"],
            IntentType.ANALYSIS: [
                "analyze",
                "evaluate",
                "compare",
                "assess",
                "examine",
            ],
            IntentType.CONVERSATION: ["hello", "how are you", "what is", "explain"],
        }

    def classify_intent(self, user_input: str) -> IntentType:
        """Classify user intent."""
        input_lower = user_input.lower()

        best_intent = IntentType.UNKNOWN
        best_score = 0

        for intent, keywords in self._intent_keywords.items():
            score = sum(1 for kw in keywords if kw in input_lower)
            if score > best_score:
                best_score = score
                best_intent = intent

        return best_intent

    async def process_input(self, user_input: str) -> AgentResponse:
        """
        Process user input and generate response.

        Flow:
        1. Classify intent
        2. Check if skill should be used
        3. Execute skill if needed
        4. Generate response
        """
        import time

        start_time = time.perf_counter()

        # Step 1: Classify intent
        intent = self.classify_intent(user_input)

        # Step 2: Check for skill usage
        skill_output = None
        skill_used = None

        if intent in [
            IntentType.CODE_GENERATION,
            IntentType.RESEARCH,
            IntentType.WRITING,
            IntentType.ANALYSIS,
        ]:
            # Find best skill
            parameters = {"request": user_input}
            skill = self.gateway.find_best_skill(intent, parameters)

            if skill:
                skill_used = skill["skill_id"]
                # Execute skill (local execution, NOT API call)
                skill_result = self.gateway.execute_skill(skill["skill_id"], parameters)
                skill_output = skill_result.get("output")

        # Step 3: Generate response (this is where local LLM would run)
        execution_time = (time.perf_counter() - start_time) * 1000

        response = AgentResponse(
            text=self._generate_response(intent, skill_output),
            skill_used=skill_used,
            execution_time_ms=execution_time,
            confidence=0.9 if skill_used else 0.7,
            skill_output=skill_output,
        )

        return response

    def _generate_response(
        self, intent: IntentType, skill_output: Optional[str]
    ) -> str:
        """Generate response text."""
        if skill_output:
            return f"Using skills from Skills Arena:\n\n{skill_output}"

        intent_responses = {
            IntentType.CODE_GENERATION: "I'd help you write code, but I don't have a coding skill loaded.",
            IntentType.RESEARCH: "I'd help you research, but I don't have a research skill loaded.",
            IntentType.WRITING: "I'd help you write, but I don't have a writing skill loaded.",
            IntentType.ANALYSIS: "I'd help you analyze, but I don't have an analysis skill loaded.",
            IntentType.CONVERSATION: "Hello! I'm OpenClaw with Skills Arena integration.",
            IntentType.UNKNOWN: "I'm not sure how to help with that.",
        }

        return intent_responses.get(intent, "How can I help you?")


# ============ Skills Loader ============


class SkillsArenaPlatformSync:
    """
    Sync manager for Skills Arena platform.

    This handles periodic synchronization of:
    - Skills metadata
    - Ratings and reviews
    - Federated learning updates
    - Usage statistics
    """

    def __init__(self, gateway: OpenClawSkillsGateway):
        self.gateway = gateway
        self._last_sync: Optional[datetime] = None

    def fetch_skills_metadata(self) -> List[Dict]:
        """
        Fetch skills metadata from Skills Arena platform.

        NOTE: This is a MOCK implementation.
        Real implementation would call Skills Arena API.
        """
        # Mock data - in reality, this comes from Skills Arena API
        return [
            {
                "skill_id": "skill-python-coder",
                "name": "Python Coder",
                "description": "Write and debug Python code",
                "category": "coding",
                "version": "1.0.0",
                "rating": 4.5,
                "rating_count": 150,
                "author": "skills-arena",
                "tags": ["python", "coding", "programming"],
                "execution_mode": "local",
            },
            {
                "skill_id": "skill-web-searcher",
                "name": "Web Searcher",
                "description": "Search the web for information",
                "category": "research",
                "version": "1.1.0",
                "rating": 4.2,
                "rating_count": 85,
                "author": "skills-arena",
                "tags": ["search", "research", "web"],
                "execution_mode": "local",
            },
            {
                "skill_id": "skill-data-analyzer",
                "name": "Data Analyzer",
                "description": "Analyze and visualize data",
                "category": "analysis",
                "version": "2.0.0",
                "rating": 4.0,
                "rating_count": 200,
                "author": "skills-arena",
                "tags": ["data", "analysis", "visualization"],
                "execution_mode": "sandbox",
            },
            {
                "skill_id": "skill-content-writer",
                "name": "Content Writer",
                "description": "Write and edit content",
                "category": "writing",
                "version": "1.5.0",
                "rating": 4.3,
                "rating_count": 320,
                "author": "skills-arena",
                "tags": ["writing", "content", "editing"],
                "execution_mode": "local",
            },
        ]

    def sync_with_platform(self) -> Dict:
        """
        Perform full sync with Skills Arena platform.

        Flow:
        1. Fetch latest skills metadata
        2. Fetch ratings updates
        3. Fetch FL model updates
        4. Upload usage statistics
        """
        # Fetch skills
        skills = self.fetch_skills_metadata()
        self.gateway.sync_skills_from_platform(skills)

        # In real implementation:
        # - Fetch ratings/reviews
        # - Fetch FL model updates
        # - Upload usage statistics

        self._last_sync = datetime.now()

        return {
            "status": "success",
            "skills_synced": len(skills),
            "timestamp": self._last_sync.isoformat(),
        }

    def get_sync_status(self) -> Dict:
        """Get current sync status."""
        return {
            "last_sync": self._last_sync.isoformat() if self._last_sync else None,
            "cached_skills": len(self.gateway.skills),
            "pending_uploads": len(self.gateway._usage_log),
        }


# ============ Demo ============


async def demo_openclaw_integration():
    """Demonstrate OpenClaw integration with Skills Arena."""
    print("\n" + "=" * 60)
    print("OpenClaw + Skills Arena Integration Demo")
    print("=" * 60)

    # Create components
    gateway = OpenClawSkillsGateway()
    sync_manager = SkillsArenaPlatformSync(gateway)

    # Sync skills from platform
    print("\n1. Syncing skills from Skills Arena platform...")
    result = sync_manager.sync_with_platform()
    print(f"   ✓ Synced {result['skills_synced']} skills")

    # Create OpenClaw agent
    agent = OpenClawAgent(user_id="demo-user")

    # Process some user inputs
    test_inputs = [
        "Write a Python function to calculate fibonacci",
        "Search the web for latest AI news",
        "Analyze this dataset",
        "Write a blog post about technology",
        "Hello, how are you?",
    ]

    print("\n2. Processing user inputs...")
    print("-" * 60)

    for user_input in test_inputs:
        print(f"\nUser: {user_input}")

        response = await agent.process_input(user_input)

        print(f"Intent: {response.skill_used or 'conversation'}")
        print(f"Time: {response.execution_time_ms:.2f}ms")
        print(f"Response preview: {response.text[:100]}...")

    # Show usage log
    print("\n3. Usage log (synced back to Skills Arena):")
    print("-" * 60)
    usage = gateway.log_usage_to_platform()
    print(f"Session: {usage['session_id']}")
    print(f"Events: {len(usage['usage_events'])}")

    # Show sync status
    print("\n4. Sync status:")
    print("-" * 60)
    status = sync_manager.get_sync_status()
    for key, value in status.items():
        print(f"   {key}: {value}")


async def demo_federated_learning():
    """Demonstrate federated learning integration."""
    print("\n" + "=" * 60)
    print("Federated Learning Integration Demo")
    print("=" * 60)

    gateway = OpenClawSkillsGateway()
    sync_manager = SkillsArenaPlatformSync(gateway)

    # Sync skills (includes FL info)
    sync_manager.sync_with_platform()

    print("\nFederated Learning Flow:")
    print("-" * 60)
    print("""
1. Agent uses a skill → generates local model updates
2. Local updates aggregated periodically (privacy-preserving)
3. Aggregated model sent back to Skills Arena
4. Platform combines updates from all agents
5. Improved model pushed to agents

Key Points:
- Raw data NEVER leaves the device
- Only model gradients/weights are shared
- Differential privacy applied
- User consent required for participation
    """)

    # Show how FL participation would work
    print("\nFL Participation Example:")
    print("-" * 60)

    # Simulate local training
    local_update = {
        "round_id": "fl-round-001",
        "agent_id": "demo-agent",
        "model_version": "1.0.0",
        "gradients": [0.1, 0.2, 0.3, 0.4, 0.5],  # Mock gradients
        "samples_processed": 1000,
        "accuracy_improvement": 0.02,
    }

    print(f"Local model update generated:")
    print(f"  Round: {local_update['round_id']}")
    print(f"  Samples: {local_update['samples_processed']}")
    print(f"  Accuracy gain: {local_update['accuracy_improvement'] * 100:.1f}%")
    print(f"\n  → Will be synced to Skills Arena platform")


# ============ Main ============


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="OpenClaw + Skills Arena Integration")
    parser.add_argument(
        "--demo",
        choices=["basic", "fl", "all"],
        default="all",
        help="Demo to run",
    )

    args = parser.parse_args()

    if args.demo in ["basic", "all"]:
        await demo_openclaw_integration()

    if args.demo in ["fl", "all"]:
        await demo_federated_learning()

    print("\n" + "=" * 60)
    print("Demo Complete!")
    print("=" * 60)
    print("""
Key Takeaways:
1. Skills execute LOCALLY (LLM context or sandbox)
2. Skills Arena platform provides discovery/ratings
3. Usage synced back periodically
4. Federated learning aggregates model updates
5. Privacy preserved - raw data never leaves device
    """)


if __name__ == "__main__":
    asyncio.run(main())
