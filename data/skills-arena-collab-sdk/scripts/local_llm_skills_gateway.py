#!/usr/bin/env python3
"""
Skills Arena Local LLM Gateway

Architecture:
┌─────────────────────────────────────────────────────────────────┐
│                      AI CLI (OpenClaw, etc.)                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                      Local LLM                          │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │    │
│  │  │ Skills  │  │Execute  │  │ Generate │  │ Evaluate │ │    │
│  │  │ Discovery│  │ Skills  │  │ Prompts │  │ Results │ │    │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘ │    │
│  └───────┼─────────────┼─────────────┼─────────────┼───────┘    │
│          │             │             │             │             │
│          └─────────────┴─────────────┴─────────────┘             │
│                         Local Gateway                            │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  • Skills Cache  • Execution Sandbox  • Result Validator  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                         │             │                          │
│                         ▼             ▼                          │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                  Skills Arena Platform                    │  │
│  │  (Periodic Sync: Skills Metadata, Ratings, FL Updates)   │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘

Key Features:
1. Local LLM executes Skills directly (no API calls during execution)
2. Gateway caches Skills metadata from Skills Arena platform
3. Periodic sync for ratings, recommendations, federated learning
4. Results validation before/after LLM execution

Author: Skills Arena Team
Version: 4.0.0
"""

import asyncio
import hashlib
import json
import os
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple

# ============ Enums ============


class ExecutionMode(Enum):
    """How LLM executes the skill."""

    LOCAL = "local"  # LLM generates code and executes locally
    SANDBOX = "sandbox"  # Isolated container execution
    INTERPRETED = "interpreted"  # LLM outputs instructions, human confirms


class SkillStatus(Enum):
    """Skill execution status."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


# ============ Data Classes ============


@dataclass
class SkillExecutionContext:
    """Context for skill execution."""

    skill_id: str
    skill_name: str
    skill_version: str
    parameters: Dict[str, Any]
    execution_mode: ExecutionMode = ExecutionMode.LOCAL
    timeout_seconds: int = 300
    validation_rules: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """Result of skill execution."""

    skill_id: str
    status: SkillStatus
    output: Optional[str] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    token_usage: int = 0
    cost_estimate: float = 0.0
    validated: bool = False
    validation_errors: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMSession:
    """Local LLM session for skill execution."""

    session_id: str
    model_name: str
    system_prompt: str
    created_at: datetime = field(default_factory=datetime.now)
    skills_accessed: List[str] = field(default_factory=list)
    total_executions: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0


@dataclass
class LocalSkill:
    """A skill available to the local LLM."""

    skill_id: str
    name: str
    description: str
    category: str
    version: str

    # Execution info
    execution_mode: ExecutionMode
    parameters: Dict[str, Any]
    required_capabilities: List[str]

    # Metadata from Skills Arena
    rating: float = 0.0
    rating_count: int = 0
    usage_count: int = 0
    author: str = ""
    tags: List[str] = field(default_factory=list)

    # Local cache info
    cached_at: Optional[str] = None
    local_path: Optional[str] = None

    # Consent info
    requires_consent: bool = False
    consent_granted: bool = False


# ============ Local Gateway ============


class LocalLLMSkillsGateway:
    """
    Gateway between local LLM and Skills Arena platform.

    Key Responsibilities:
    1. Cache Skills metadata from Skills Arena (periodic sync)
    2. Provide Skills discovery interface for LLM
    3. Execute Skills on behalf of LLM
    4. Track execution metrics
    5. Sync usage data back to Skills Arena
    """

    def __init__(
        self,
        skills_cache_dir: Path = Path("./data/skills_cache"),
        sync_interval_minutes: int = 30,
    ):
        self.cache_dir = skills_cache_dir
        self.sync_interval = timedelta(minutes=sync_interval_minutes)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Local skills cache
        self._skills: Dict[str, LocalSkill] = {}
        self._skills_index: Dict[str, List[str]] = {}  # category -> skill_ids

        # Execution tracking
        self._execution_history: List[ExecutionResult] = []
        self._session: Optional[LLMSession] = None

        # Sync state
        self._last_sync: Optional[datetime] = None

        # Load cached skills
        self._load_cache()

    @property
    def available_skills(self) -> List[LocalSkill]:
        """Get all available skills (cached)."""
        return list(self._skills.values())

    def get_skill(self, skill_id: str) -> Optional[LocalSkill]:
        """Get a specific skill by ID."""
        return self._skills.get(skill_id)

    def search_skills(self, query: str, limit: int = 10) -> List[LocalSkill]:
        """Search skills by query (local cache)."""
        query = query.lower()
        results = []

        for skill in self._skills.values():
            score = 0
            if query in skill.name.lower():
                score += 3
            if query in skill.description.lower():
                score += 2
            if query in skill.category.lower():
                score += 2
            if any(query in tag for tag in skill.tags):
                score += 1

            if score > 0:
                results.append((skill, score))

        # Sort by score and return top results
        results.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in results[:limit]]

    def get_skills_by_category(self, category: str) -> List[LocalSkill]:
        """Get skills in a specific category."""
        skill_ids = self._skills_index.get(category, [])
        return [self._skills[sid] for sid in skill_ids if sid in self._skills]

    async def execute_skill(
        self,
        skill_id: str,
        parameters: Dict[str, Any],
        execution_mode: ExecutionMode = ExecutionMode.LOCAL,
        timeout_seconds: int = 300,
    ) -> ExecutionResult:
        """Execute a skill on behalf of the LLM."""
        start_time = time.perf_counter()

        skill = self._skills.get(skill_id)
        if not skill:
            return ExecutionResult(
                skill_id=skill_id,
                status=SkillStatus.FAILED,
                error=f"Skill not found: {skill_id}",
            )

        # Create execution context
        context = SkillExecutionContext(
            skill_id=skill_id,
            skill_name=skill.name,
            skill_version=skill.version,
            parameters=parameters,
            execution_mode=execution_mode,
            timeout_seconds=timeout_seconds,
        )

        try:
            # Execute based on mode
            if execution_mode == ExecutionMode.LOCAL:
                result = await self._execute_locally(context, skill)
            elif execution_mode == ExecutionMode.SANDBOX:
                result = await self._execute_in_sandbox(context, skill)
            else:
                result = await self._execute_interpreted(context, skill)

        except Exception as e:
            result = ExecutionResult(
                skill_id=skill_id,
                status=SkillStatus.FAILED,
                error=str(e),
            )

        # Calculate execution time
        result.execution_time_ms = (time.perf_counter() - start_time) * 1000
        self._execution_history.append(result)

        # Update metrics
        self._session.total_executions += 1
        if result.status == SkillStatus.SUCCESS:
            self._session.skills_accessed.append(skill_id)

        return result

    async def _execute_locally(
        self, context: SkillExecutionContext, skill: LocalSkill
    ) -> ExecutionResult:
        """Execute skill in local mode (LLM generates code, we run it)."""
        # In this mode, the LLM would have already generated the execution
        # We just run the provided code/commands

        # Simulate execution (actual implementation would run the skill)
        await asyncio.sleep(0.1)

        # Validate result if rules provided
        validated = True
        validation_errors = []

        for rule in context.validation_rules:
            if not self._validate_rule(context, rule):
                validated = False
                validation_errors.append(f"Failed: {rule}")

        return ExecutionResult(
            skill_id=context.skill_id,
            status=SkillStatus.SUCCESS,
            output=f"Executed {skill.name} with {len(context.parameters)} parameters",
            validated=validated,
            validation_errors=validation_errors,
            token_usage=len(context.parameters) * 10,  # Estimate
            cost_estimate=0.01,  # Estimate
        )

    async def _execute_in_sandbox(
        self, context: SkillExecutionContext, skill: LocalSkill
    ) -> ExecutionResult:
        """Execute in isolated sandbox."""
        # Sandbox execution would use Docker/container
        await asyncio.sleep(0.2)

        return ExecutionResult(
            skill_id=context.skill_id,
            status=SkillStatus.SUCCESS,
            output="Sandbox execution completed",
            token_usage=len(context.parameters) * 12,
            cost_estimate=0.02,
        )

    async def _execute_interpreted(
        self, context: SkillExecutionContext, skill: LocalSkill
    ) -> ExecutionResult:
        """Interpreted mode - LLM outputs instructions, human confirms."""
        # This would generate a human-readable instruction set
        return ExecutionResult(
            skill_id=context.skill_id,
            status=SkillStatus.SUCCESS,
            output="Instructions generated for human execution",
            token_usage=len(context.parameters) * 8,
            cost_estimate=0.005,
        )

    def _validate_rule(self, context: SkillExecutionContext, rule: str) -> bool:
        """Validate execution result against a rule."""
        # Simple rule validation
        if "non_empty" in rule and not context.parameters:
            return False
        if "has_key" in rule:
            key = rule.split(":")[1] if ":" in rule else None
            if key and key not in context.parameters:
                return False
        return True

    def start_session(self, model_name: str, system_prompt: str) -> LLMSession:
        """Start a new LLM session."""
        self._session = LLMSession(
            session_id=f"session-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            model_name=model_name,
            system_prompt=system_prompt,
        )
        return self._session

    def end_session(self):
        """End the current session and return metrics."""
        if self._session:
            self._session.total_tokens = sum(
                r.token_usage for r in self._execution_history
            )
            self._session.total_cost = sum(
                r.cost_estimate for r in self._execution_history
            )
            return self._session
        return None

    # ============ Cache Management ============

    def _load_cache(self):
        """Load skills from local cache."""
        cache_file = self.cache_dir / "skills_cache.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r") as f:
                    data = json.load(f)
                    for item in data.get("skills", []):
                        skill = LocalSkill(**item)
                        self._skills[skill.skill_id] = skill
                        if skill.category not in self._skills_index:
                            self._skills_index[skill.category] = []
                        self._skills_index[skill.category].append(skill.skill_id)
            except Exception as e:
                print(f"Failed to load skills cache: {e}")

    def update_cache_from_platform(self, skills_data: List[Dict]):
        """Update local cache from Skills Arena platform data."""
        for item in skills_data:
            skill = LocalSkill(
                skill_id=item["skill_id"],
                name=item["name"],
                description=item["description"],
                category=item.get("category", "general"),
                version=item.get("version", "1.0"),
                execution_mode=ExecutionMode(item.get("execution_mode", "local")),
                parameters=item.get("parameters", {}),
                required_capabilities=item.get("capabilities", []),
                rating=item.get("rating", 0.0),
                rating_count=item.get("rating_count", 0),
                usage_count=item.get("usage_count", 0),
                author=item.get("author", ""),
                tags=item.get("tags", []),
                cached_at=datetime.now().isoformat(),
            )

            self._skills[skill.skill_id] = skill
            if skill.category not in self._skills_index:
                self._skills_index[skill.category] = []
            if skill.skill_id not in self._skills_index[skill.category]:
                self._skills_index[skill.category].append(skill.skill_id)

        # Save cache
        self._save_cache()
        self._last_sync = datetime.now()

    def _save_cache(self):
        """Save skills cache to disk."""
        cache_file = self.cache_dir / "skills_cache.json"
        data = {
            "updated_at": datetime.now().isoformat(),
            "skills": [
                {
                    "skill_id": s.skill_id,
                    "name": s.name,
                    "description": s.description,
                    "category": s.category,
                    "version": s.version,
                    "execution_mode": s.execution_mode.value,
                    "parameters": s.parameters,
                    "required_capabilities": s.required_capabilities,
                    "rating": s.rating,
                    "rating_count": s.rating_count,
                    "usage_count": s.usage_count,
                    "author": s.author,
                    "tags": s.tags,
                }
                for s in self._skills.values()
            ],
        }
        with open(cache_file, "w") as f:
            json.dump(data, f, indent=2)

    def get_session_summary(self) -> Dict:
        """Get current session summary."""
        if not self._session:
            return {"status": "no_active_session"}

        return {
            "session_id": self._session.session_id,
            "model_name": self._session.model_name,
            "created_at": self._session.created_at.isoformat(),
            "skills_accessed": list(set(self._session.skills_accessed)),
            "total_executions": self._session.total_executions,
            "total_tokens": self._session.total_tokens,
            "total_cost": self._session.total_cost,
            "cached_skills": len(self._skills),
            "last_sync": self._last_sync.isoformat() if self._last_sync else None,
        }


# ============ LLM Integration Helpers ============


class SkillsArenaPromptEngine:
    """Prompt engineering for LLM skill execution."""

    # System prompt for LLM with skills access
    DEFAULT_SYSTEM_PROMPT = """You are an AI assistant with access to a library of Skills.

Available Skills:
{skills_list}

How to use a Skill:
1. Identify which Skill best addresses the user's request
2. Call the skill using its ID with appropriate parameters
3. Execute the skill and integrate the results

When responding:
- Use your skills when they can help answer the user's question
- Explain what you're doing when using a skill
- Combine skill outputs with your own knowledge for best results

Current context: {context}
"""

    @staticmethod
    def format_skills_list(gateway: LocalLLMSkillsGateway, max_skills: int = 20) -> str:
        """Format available skills for LLM context."""
        skills = gateway.available_skills[:max_skills]

        lines = []
        for skill in skills:
            lines.append(
                f"- ID: {skill.skill_id}\n"
                f"  Name: {skill.name}\n"
                f"  Category: {skill.category}\n"
                f"  Description: {skill.description}\n"
                f"  Rating: {skill.rating:.1f}/5 ({skill.rating_count} votes)\n"
            )

        return "\n".join(lines)

    @staticmethod
    def generate_skill_call(
        skill_id: str,
        parameters: Dict[str, Any],
        explanation: str = "",
    ) -> str:
        """Generate a structured skill call for the LLM."""
        return f"""
<skill_call>
  <skill_id>{skill_id}</skill_id>
  <parameters>{json.dumps(parameters)}</parameters>
  <explanation>{explanation}</explanation>
</skill_call>
""".strip()

    @staticmethod
    def parse_skill_output(output: str) -> Dict:
        """Parse skill output from LLM response."""
        # Simple parsing - look for structured output
        if "<skill_result>" in output and "</skill_result>" in output:
            # Extract result
            import re

            match = re.search(r"<skill_result>(.*?)</skill_result>", output, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass
        return {"raw_output": output}


# ============ CLI Interface ============


class SkillsArenaCLI:
    """CLI for local LLM-Skills integration."""

    def __init__(self):
        self.gateway = LocalLLMSkillsGateway()
        self._session: Optional[LLMSession] = None

    def run(self):
        """Run interactive CLI."""
        print("\n" + "=" * 60)
        print("Skills Arena Local LLM Gateway")
        print("=" * 60)

        while True:
            command = input("\nskills-arena> ").strip()

            if command in ("exit", "quit", "q"):
                print("Goodbye!")
                break

            if not command:
                continue

            parts = command.split()
            cmd = parts[0].lower()
            args = parts[1:]

            try:
                self._execute_command(cmd, args)
            except Exception as e:
                print(f"Error: {e}")

    def _execute_command(self, cmd: str, args: List[str]):
        """Execute CLI command."""
        commands = {
            "session": self._cmd_session,
            "skills": self._cmd_skills,
            "search": self._cmd_search,
            "execute": self._cmd_execute,
            "list": self._cmd_list,
            "summary": self._cmd_summary,
            "sync": self._cmd_sync,
            "help": self._cmd_help,
        }

        if cmd not in commands:
            print(f"Unknown command: {cmd}")
            self._cmd_help([])
            return

        commands[cmd](args)

    def _cmd_session(self, args: List[str]):
        """Start a new LLM session."""
        if not args:
            model = "unknown-model"
            prompt = "You are an AI assistant with skills access."
        else:
            model = args[0]
            prompt = " ".join(args[1:]) if len(args) > 1 else "You are an AI assistant."

        self._session = self.gateway.start_session(model, prompt)
        print(f"✓ Session started: {self._session.session_id}")
        print(f"  Model: {model}")
        print(f"  Cached skills: {len(self.gateway.available_skills)}")

    def _cmd_skills(self, args: List[str]):
        """List available skills."""
        if args:
            category = args[0]
            skills = self.gateway.get_skills_by_category(category)
        else:
            skills = self.gateway.available_skills

        print(f"\nAvailable Skills ({len(skills)}):")
        print("-" * 60)
        for i, skill in enumerate(skills, 1):
            print(f"{i:2}. {skill.name}")
            print(f"    ID: {skill.skill_id}")
            print(f"    Category: {skill.category}")
            print(f"    Rating: {skill.rating:.1f}/5 ({skill.rating_count} votes)")
            print()

    def _cmd_search(self, args: List[str]):
        """Search for skills."""
        if not args:
            print("Usage: search <query>")
            return

        query = " ".join(args)
        results = self.gateway.search_skills(query)

        print(f"\nSearch Results for '{query}' ({len(results)}):")
        print("-" * 60)
        for i, skill in enumerate(results, 1):
            print(f"{i:2}. {skill.name} ({skill.category})")
            print(f"    {skill.description[:80]}...")
            print()

    def _cmd_execute(self, args: List[str]):
        """Execute a skill."""
        if len(args) < 2:
            print("Usage: execute <skill_id> <params_json>")
            return

        skill_id = args[0]
        try:
            params = json.loads(" ".join(args[1:]))
        except json.JSONDecodeError:
            params = {}

        result = asyncio.run(
            self.gateway.execute_skill(skill_id, params, ExecutionMode.LOCAL)
        )

        print(f"\nExecution Result:")
        print(f"  Status: {result.status.value}")
        print(f"  Time: {result.execution_time_ms:.2f}ms")
        if result.output:
            print(f"  Output: {result.output[:200]}")
        if result.error:
            print(f"  Error: {result.error}")

    def _cmd_list(self, args: List[str]):
        """List session information."""
        summary = self.gateway.get_session_summary()
        print("\nSession Summary:")
        print("-" * 60)
        for key, value in summary.items():
            print(f"  {key}: {value}")

    def _cmd_summary(self, args: List[str]):
        """Get detailed session summary."""
        summary = self.gateway.get_session_summary()
        print(json.dumps(summary, indent=2))

    def _cmd_sync(self, args: List[str]):
        """Sync skills from platform (mock)."""
        print("\nSyncing skills from Skills Arena platform...")
        print("(This would fetch latest skills metadata from the platform)")
        print(f"Currently cached: {len(self.gateway.available_skills)} skills")

    def _cmd_help(self, args: List[str]):
        """Show help."""
        print("\nAvailable Commands:")
        print("=" * 60)
        print("session [model] [prompt]  - Start new LLM session")
        print("skills [category]          - List available skills")
        print("search <query>            - Search for skills")
        print("execute <skill_id> <json> - Execute a skill")
        print("list                      - Show session info")
        print("summary                   - Show detailed session summary")
        print("sync                      - Sync skills from platform")
        print("help, ?                   - Show this help")
        print("exit, quit, q             - Exit CLI")


# ============ Main ============


async def demo_local_gateway():
    """Demonstrate local LLM-Skills gateway."""
    print("\n" + "=" * 60)
    print("Skills Arena Local LLM Gateway - Demo")
    print("=" * 60)

    # Create gateway
    gateway = LocalLLMSkillsGateway()

    # Start session
    session = gateway.start_session(
        model_name="claude-3-opus",
        system_prompt="You are a helpful AI with skills access.",
    )
    print(f"✓ Session started: {session.session_id}")

    # Simulate skills cache update (normally from platform)
    demo_skills = [
        {
            "skill_id": "skill-coding-001",
            "name": "Code Generator",
            "description": "Generate Python code based on requirements",
            "category": "coding",
            "rating": 4.5,
            "rating_count": 120,
            "version": "1.0",
        },
        {
            "skill_id": "skill-research-001",
            "name": "Web Researcher",
            "description": "Search and summarize web content",
            "category": "research",
            "rating": 4.2,
            "rating_count": 85,
            "version": "1.1",
        },
        {
            "skill_id": "skill-writing-001",
            "name": "Content Writer",
            "description": "Write and edit content",
            "category": "writing",
            "rating": 4.0,
            "rating_count": 200,
            "version": "2.0",
        },
    ]
    gateway.update_cache_from_platform(demo_skills)
    print(f"✓ Cached {len(gateway.available_skills)} skills")

    # Search for skills
    print("\nSearching for 'code'...")
    results = gateway.search_skills("code")
    for skill in results:
        print(f"  - {skill.name} ({skill.skill_id})")

    # Execute a skill
    print("\nExecuting skill...")
    result = await gateway.execute_skill(
        "skill-coding-001",
        {"requirements": "function to calculate fibonacci"},
        ExecutionMode.LOCAL,
    )
    print(f"  Status: {result.status.value}")
    print(f"  Time: {result.execution_time_ms:.2f}ms")

    # Get session summary
    summary = gateway.get_session_summary()
    print("\nSession Summary:")
    print(json.dumps(summary, indent=2))

    # End session
    final_session = gateway.end_session()
    print(f"\n✓ Session ended")
    print(f"  Total executions: {final_session.total_executions}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Skills Arena Local LLM Gateway")
    parser.add_argument(
        "--mode",
        choices=["cli", "demo", "api"],
        default="cli",
        help="Running mode",
    )
    parser.add_argument(
        "--model",
        default="claude-3-sonnet",
        help="LLM model name for session",
    )

    args = parser.parse_args()

    if args.mode == "cli":
        cli = SkillsArenaCLI()
        cli.run()

    elif args.mode == "demo":
        asyncio.run(demo_local_gateway())

    elif args.mode == "api":
        # Simple API server mode
        print("API server mode - not implemented")
        print("Use 'cli' or 'demo' mode instead")


if __name__ == "__main__":
    main()
