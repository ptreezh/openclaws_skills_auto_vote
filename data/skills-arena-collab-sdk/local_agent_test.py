#!/usr/bin/env python3
"""
本地子智能体测试 ArenaSync Meta-Skill

测试步骤：
1. 子智能体下载 ArenaSync Meta-Skill
2. 第一次使用：询问用户是否参与协同进化
3. 用户选择"是"
4. 安装联邦学习钩子
5. 子智能体执行任务
6. 自动记录数据
7. 验证只询问一次，后续不再询问

Usage:
    python local_agent_test.py
"""

import asyncio
import sys
from pathlib import Path

# 添加 ArenaSync Skill 到路径
SKILL_PATH = Path(__file__).parent / "skills" / "arenasync" / "scripts"
sys.path.insert(0, str(SKILL_PATH))

from arenasync_meta_skill import ArenaSyncMetaSkill


# ============ 子智能体 ============


class LocalSubAgent:
    """
    本地子智能体
    - 可以下载和使用 Skills
    - 集成了 ArenaSync Meta-Skill
    - 会自动处理用户同意和联邦学习
    """

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.name = f"SubAgent-{agent_id}"

        # 集成 ArenaSync Meta-Skill
        self.arena_sync = ArenaSyncMetaSkill(agent_id=agent_id)

        print(f"[{self.name}] 初始化完成")

    async def execute_task(self, task: str) -> dict:
        """
        执行任务

        流程：
        1. 检查是否需要询问用户同意
        2. 执行任务（调用其他 Skills）
        3. 自动记录使用数据（如果已安装钩子）
        """
        print(f"\n[{self.name}] 开始执行任务: {task}")

        # 步骤1：检查是否需要询问用户
        if self.arena_sync.should_ask_user():
            print(f"\n[步骤1] 检测到第一次使用，显示用户同意 UI：")
            print("-" * 60)
            print(self.arena_sync.get_consent_ui())
            print("-" * 60)

            # 返回给调用方，让调用方处理用户输入
            return {
                "status": "need_consent",
                "agent": self.name,
                "task": task,
                "ui": self.arena_sync.get_consent_ui(),
            }

        # 步骤2：执行任务（模拟调用其他 Skills）
        print(f"\n[步骤2] 执行任务（模拟调用其他 Skills）...")
        result = await self._simulate_skill_execution(task)

        # 步骤3：包装执行函数（自动记录数据）
        print(f"\n[步骤3] 使用 ArenaSync Meta-Skill 包装执行...")

        wrapped_fn = self.arena_sync.wrap_execute(self._get_skill_executor(task))

        # 执行包装后的函数
        execution_result = await wrapped_fn(task)

        return {
            "status": "completed",
            "agent": self.name,
            "task": task,
            "result": result,
            "execution": execution_result,
        }

    async def handle_consent_response(self, response: str) -> dict:
        """
        处理用户同意响应
        """
        print(f"\n[{self.name}] 处理用户响应: {response}")

        should_install, message = await self.arena_sync.handle_user_response(response)

        if should_install:
            self.arena_sync.install_hook()
            print(f"[{self.name}] ✅ 已安装联邦学习钩子")

        return {
            "status": "consent_processed",
            "agent": self.name,
            "should_install_hook": should_install,
            "message": message,
        }

    async def check_and_show_status(self) -> dict:
        """
        检查并显示当前状态
        """
        status = self.arena_sync.get_status()

        print(f"\n[{self.name}] 当前状态：")
        print(f"  同意级别: {status['consent_level']}")
        print(f"  钩子已安装: {status['hook_installed']}")
        print(f"  本地记录数: {status['local_records']}")

        return status

    async def _simulate_skill_execution(self, task: str) -> dict:
        """
        模拟执行 Skill（实际项目中这里会调用真实的 Skill）
        """
        # 模拟执行时间
        await asyncio.sleep(0.1)

        return {
            "skill_used": "simulated-skill",
            "output": f"已完成任务: {task}",
            "execution_time_ms": 100,
            "success": True,
        }

    def _get_skill_executor(self, task: str):
        """
        返回 Skill 执行函数
        """

        async def executor(t):
            await asyncio.sleep(0.05)
            return {"task": t, "processed": True}

        return executor


# ============ 主测试流程 ============


async def main():
    """
    主测试流程

    测试场景：
    1. 创建 2 个子智能体
    2. 第一个子智能体：第一次使用，询问用户
    3. 用户选择"是"，安装钩子
    4. 子智能体执行任务
    5. 第二个子智能体：验证不再询问用户
    6. 显示最终状态
    """
    print("=" * 70)
    print("本地子智能体测试 - ArenaSync Meta-Skill")
    print("=" * 70)

    # 创建子智能体
    agents = [
        LocalSubAgent("001"),
        LocalSubAgent("002"),
    ]

    # ========== 测试场景 1 ==========
    print("\n" + "=" * 70)
    print("测试场景 1：第一个子智能体 - 第一次使用")
    print("=" * 70)

    agent1 = agents[0]

    # 执行任务（应该触发询问）
    result1 = await agent1.execute_task("写一个 Python 函数")

    if result1["status"] == "need_consent":
        print(f"\n✅ 正确：检测到第一次使用，需要用户同意")
    else:
        print(f"\n❌ 错误：应该触发用户同意询问")
        return

    # 处理用户响应（选择"是"）
    consent_result = await agent1.handle_consent_response("yes")

    if consent_result["should_install_hook"]:
        print(f"\n✅ 正确：用户同意参与，安装钩子")
    else:
        print(f"\n❌ 错误：应该安装钩子")
        return

    # 再次执行任务（应该不询问）
    result1b = await agent1.execute_task("分析数据")

    if result1b["status"] == "completed":
        print(f"\n✅ 正确：后续使用不再询问用户")
    else:
        print(f"\n❌ 错误：后续使用应该不询问")

    # ========== 测试场景 2 ==========
    print("\n" + "=" * 70)
    print("测试场景 2：第二个子智能体 - 也是第一次使用")
    print("=" * 70)

    agent2 = agents[1]

    # 这个也是第一次使用，应该询问
    result2 = await agent2.execute_task("研究 AI 趋势")

    if result2["status"] == "need_consent":
        print(f"\n✅ 正确：新的子智能体也是第一次使用")
    else:
        print(f"\n❌ 错误：新的子智能体应该第一次使用")

    # 第二个子智能体选择"否"
    consent_result2 = await agent2.handle_consent_response("no")

    if not consent_result2["should_install_hook"]:
        print(f"\n✅ 正确：用户选择'否'，不安装钩子")
    else:
        print(f"\n❌ 错误：不应该安装钩子")

    # ========== 测试场景 3 ==========
    print("\n" + "=" * 70)
    print("测试场景 3：验证'永不打扰'原则")
    print("=" * 70)

    # 第一个子智能体再次执行任务
    print(f"\n{agent1.name} 再次执行任务...")
    result3 = await agent1.execute_task("搜索资料")

    if result3["status"] == "completed":
        print(f"\n✅ 正确：已同意的用户后续使用不再询问")
    else:
        print(f"\n❌ 错误：应该直接执行，不询问")

    # 第二个子智能体再次执行任务
    print(f"\n{agent2.name} 再次执行任务...")
    result4 = await agent2.execute_task("写报告")

    if result4["status"] == "completed":
        print(f"\n✅ 正确：拒绝的用户也不再询问（沉默等待）")
    else:
        print(f"\n❌ 错误：应该直接执行")

    # ========== 最终状态 ==========
    print("\n" + "=" * 70)
    print("测试完成 - 显示所有子智能体状态")
    print("=" * 70)

    for agent in agents:
        await agent.check_and_show_status()

    print("\n" + "=" * 70)
    print("✅ 所有测试完成！")
    print("=" * 70)
    print("""
总结：
- ✅ 第一次使用：询问用户
- ✅ 肯定回答：安装钩子，参与协同进化
- ✅ 否定回答：沉默等待，不打扰
- ✅ 后续使用：永不主动询问
- ✅ 除非用户主动说"如何协同进化"
    """)


if __name__ == "__main__":
    asyncio.run(main())
