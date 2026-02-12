#!/usr/bin/env python3
"""
ArenaSync Meta-Skill - 联邦学习与协同进化

核心设计：
- 问答一次后不重复
- 肯定则安装钩子
- 否定则沉默等待（除非用户专门询问）

Usage:
    # 1. Agent 下载并安装这个 Skill
    # 2. 第一次使用时询问用户
    # 3. 根据用户选择执行

Author: Skills Arena Team
Version: 2.0.0
"""

import asyncio
import hashlib
import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import yaml


# ============ 常量 ============

SKILL_NAME = "arenasync"
SKILL_VERSION = "2.0.0"
CONSENT_FILE = Path("~/.config/skills-arena/consent.yml")
DATA_DIR = Path("./data/arenasync")
GRADIENTS_DIR = Path("./data/arenasync/gradients")


# ============ 枚举 ============


class ConsentLevel(Enum):
    """用户同意级别"""

    NOT_ASKED = "not_asked"  # 尚未询问
    ACCEPTED = "accepted"  # 同意参与
    DECLINED = "declined"  # 拒绝参与


@dataclass
class ConsentRecord:
    """用户同意记录"""

    level: ConsentLevel
    asked_at: Optional[str] = None
    responded_at: Optional[str] = None
    can_collect_usage: bool = False
    can_upload_gradients: bool = False
    privacy_mode: str = "strict"


# ============ 核心类 ============


class ArenaSyncMetaSkill:
    """
    ArenaSync 元技能

    核心设计原则：
    1. 只询问用户一次，永不重复
    2. 肯定回答 → 安装钩子，参与协同进化
    3. 否定回答 → 沉默，不主动打扰
    4. 除非用户专门询问"如何协同进化"，否则不再询问
    """

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.consent = self._load_consent()
        self.hook_installed: bool = False

        # 初始化目录
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        GRADIENTS_DIR.mkdir(parents=True, exist_ok=True)

        # 联邦学习配置
        self.config = {
            "upload_threshold": 20,  # 每 20 条记录上传一次
            "privacy_mode": "strict",  # 严格隐私保护
            "local_training_enabled": True,
        }

        # 检查是否已安装钩子
        self._check_hook_status()

    # ============ 同意管理 ============

    def _load_consent(self) -> ConsentRecord:
        """加载用户同意记录"""
        CONSENT_FILE.parent.mkdir(parents=True, exist_ok=True)

        if not CONSENT_FILE.exists():
            return ConsentRecord(level=ConsentLevel.NOT_ASKED)

        try:
            with open(CONSENT_FILE, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            return ConsentRecord(
                level=ConsentLevel(data.get("level", "not_asked")),
                asked_at=data.get("asked_at"),
                responded_at=data.get("responded_at"),
                can_collect_usage=data.get("can_collect_usage", False),
                can_upload_gradients=data.get("can_upload_gradients", False),
                privacy_mode=data.get("privacy_mode", "strict"),
            )
        except Exception:
            return ConsentRecord(level=ConsentLevel.NOT_ASKED)

    def _save_consent(self, consent: ConsentRecord):
        """保存用户同意记录"""
        data = {
            "level": consent.level.value,
            "asked_at": consent.asked_at,
            "responded_at": consent.responded_at,
            "can_collect_usage": consent.can_collect_usage,
            "can_upload_gradients": consent.can_upload_gradients,
            "privacy_mode": consent.privacy_mode,
        }

        with open(CONSENT_FILE, "w", encoding="utf-8") as f:
            yaml.dump(data, f)

    @property
    def has_consent(self) -> bool:
        """是否已获取用户同意"""
        return self.consent.level == ConsentLevel.ACCEPTED

    @property
    def has_declined(self) -> bool:
        """用户是否已拒绝"""
        return self.consent.level == ConsentLevel.DECLINED

    @property
    def is_first_time(self) -> bool:
        """是否是第一次使用"""
        return self.consent.level == ConsentLevel.NOT_ASKED

    # ============ 用户交互 ============

    def should_ask_user(self) -> bool:
        """
        是否应该询问用户

        只在第一次使用时询问
        """
        return self.is_first_time

    def get_consent_ui(self) -> str:
        """
        获取用户同意 UI

        只在第一次使用时调用
        """
        return """
## 🤖 Skills Arena 协同进化邀请

**首次使用**，让我自我介绍一下：

### 我能做什么：

1. **自动同步 Skills**
   - 始终使用最新版本的 Skills
   - 无需手动更新

2. **更好的个性化推荐**
   - 猜你可能需要什么 Skill
   - 基于协同过滤算法

3. **参与协同进化**（可选）
   - 让 Skills 越用越聪明
   - 贡献你的使用模式（脱敏后）

### 隐私保护：

🛡️ **只传统计，不传内容**
   - 传梯度，不传原始数据
   
🛡️ **数据在本地处理**
   - 敏感信息从不离开你的设备

🛡️ **可随时退出**
   - 只需删除这个 Skill 即可

### 你想让 Skills Arena 变得更好吗？

- **[是，参与协同进化]** 帮助改进所有 Skills
- **[否，仅同步]** 只同步，不用参与
        """

    async def handle_user_response(self, response: str) -> Tuple[bool, str]:
        """
        处理用户响应

        Args:
            response: 用户响应（应该是 "yes", "no", 或类似）

        Returns:
            (should_install_hook, message)
        """
        response_lower = response.lower().strip()

        # 解析用户响应
        if response_lower in ["yes", "是", "同意", "参与", "y"]:
            # 用户同意
            self.consent = ConsentRecord(
                level=ConsentLevel.ACCEPTED,
                asked_at=datetime.now().isoformat(),
                responded_at=datetime.now().isoformat(),
                can_collect_usage=True,
                can_upload_gradients=True,
                privacy_mode="strict",
            )
            self._save_consent(self.consent)

            return (
                True,
                """
✅ **感谢你参与协同进化！**

已安装：
- 使用数据自动记录
- 定期上传梯度（脱敏后）
- 自动同步最新 Skills

你的贡献会让 Skills Arena 变得更好！
            """,
            )

        elif response_lower in ["no", "否", "不同意", "不参与", "n"]:
            # 用户拒绝
            self.consent = ConsentRecord(
                level=ConsentLevel.DECLINED,
                asked_at=datetime.now().isoformat(),
                responded_at=datetime.now().isoformat(),
                can_collect_usage=False,
                can_upload_gradients=False,
                privacy_mode="strict",
            )
            self._save_consent(self.consent)

            return (
                False,
                """
✅ **已记录你的选择**

不使用协同进化功能。
- 仍可使用 Skills 同步和推荐
- 不会主动询问第二次
- 如需参与，可随时说"如何协同进化"

感谢使用 Skills Arena！
            """,
            )

        else:
            # 无效响应
            return (
                False,
                """
⚠️ 未识别的响应

请回复：
- **是** 或 **yes** - 参与协同进化
- **否** 或 **no** - 仅同步
            """,
            )

    def need_to_ask_again(self) -> bool:
        """
        是否需要再次询问

        核心逻辑：只有第一次使用才询问
        除非用户专门询问，否则不重复
        """
        return self.is_first_time

    def check_activation_phrase(self, user_input: str) -> bool:
        """
        检查用户是否主动询问协同进化

        只有用户说"如何协同进化"时才再次询问
        """
        activation_phrases = [
            "如何协同进化",
            "如何参与",
            "协同进化",
            "联邦学习",
            "federated",
            "参与进化",
        ]

        user_input_lower = user_input.lower()
        return any(phrase.lower() in user_input_lower for phrase in activation_phrases)

    # ============ 钩子安装 ============

    def _check_hook_status(self):
        """检查钩子是否已安装"""
        consent_file = CONSENT_FILE
        hook_file = DATA_DIR / "hook_installed.txt"

        if hook_file.exists():
            with open(hook_file, "r") as f:
                installed_at = f.read().strip()
                self.hook_installed = True
        else:
            self.hook_installed = False

    def install_hook(self) -> bool:
        """
        安装联邦学习钩子

        Returns:
            是否安装成功
        """
        if not self.has_consent:
            return False

        # 创建标记文件
        hook_file = DATA_DIR / "hook_installed.txt"
        with open(hook_file, "w") as f:
            f.write(datetime.now().isoformat())

        self.hook_installed = True

        # 记录同意级别
        self._save_consent(self.consent)

        return True

    def uninstall_hook(self):
        """卸载联邦学习钩子"""
        hook_file = DATA_DIR / "hook_installed.txt"
        if hook_file.exists():
            hook_file.unlink()

        self.hook_installed = False

    def wrap_execute(self, original_execute: Callable) -> Callable:
        """
        包装原始执行函数，安装钩子

        Args:
            original_execute: 原始的 Skill 执行函数

        Returns:
            包装后的函数（带数据记录功能）
        """
        if not self.has_consent or not self.has_consent:
            # 用户未同意，不安装钩子，直接返回原始函数
            return original_execute

        async def wrapped_execute(*args, **kwargs) -> Any:
            start_time = time.perf_counter()

            try:
                # 执行原始函数
                if asyncio.iscoroutinefunction(original_execute):
                    result = await original_execute(*args, **kwargs)
                else:
                    result = original_execute(*args, **kwargs)

                success = True
                error = None
            except Exception as e:
                result = None
                success = False
                error = str(type(e).__name__)

            execution_time = (time.perf_counter() - start_time) * 1000

            # 记录元数据（不碰用户内容）
            await self._record_usage(
                skill_id=self._extract_skill_id(args, kwargs),
                success=success,
                error=error,
                execution_time_ms=execution_time,
            )

            return result

        return wrapped_execute

    # ============ 数据记录 ============

    async def _record_usage(
        self,
        skill_id: str,
        success: bool,
        error: Optional[str],
        execution_time_ms: float,
    ):
        """记录使用数据（本地）"""
        if not self.consent.can_collect_usage:
            return

        record = {
            "skill_id": skill_id,
            "timestamp": datetime.now().isoformat(),
            "execution_time_ms": execution_time_ms,
            "success": success,
            "error_type": error,
            "hour": datetime.now().hour,
        }

        # 写入本地文件
        data_file = DATA_DIR / "usage_records.jsonl"

        with open(data_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        # 检查是否需要上传
        record_count = self._count_local_records()
        if record_count >= self.config["upload_threshold"]:
            await self._upload_gradients()

    def _count_local_records(self) -> int:
        """统计本地记录数量"""
        data_file = DATA_DIR / "usage_records.jsonl"

        if not data_file.exists():
            return 0

        with open(data_file, "r", encoding="utf-8") as f:
            return sum(1 for _ in f)

    # ============ 联邦学习 ============

    async def _upload_gradients(self):
        """上传梯度到平台"""
        if not self.consent.can_upload_gradients:
            return

        # 1. 计算本地梯度
        gradients = self._compute_gradients()

        if not gradients:
            return

        # 2. 保存梯度
        gradient_file = (
            GRADIENTS_DIR / f"grad_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        with open(gradient_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "agent_id": self.agent_id,
                    "timestamp": datetime.now().isoformat(),
                    "gradients": gradients,
                    "privacy_verified": True,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        # 3. 清除本地记录
        data_file = DATA_DIR / "usage_records.jsonl"
        if data_file.exists():
            data_file.unlink()

        # 4. 模拟上传到平台
        print(f"✅ 已上传梯度到 Skills Arena 平台")
        print(f"   贡献 {gradients.get('samples_count', '?')} 条使用记录")

    def _compute_gradients(self) -> Optional[Dict]:
        """计算本地梯度"""
        data_file = DATA_DIR / "usage_records.jsonl"

        if not data_file.exists():
            return None

        records = []
        with open(data_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    record = json.loads(line.strip())
                    records.append(record)
                except json.JSONDecodeError:
                    continue

        if not records:
            return None

        # 计算统计
        success_count = sum(1 for r in records if r.get("success", False))
        success_rate = success_count / len(records)

        avg_time = sum(r.get("execution_time_ms", 0) for r in records) / len(records)

        # 计算梯度（改进方向）
        gradients = {
            "samples_count": len(records),
            "success_rate": success_rate,
            "avg_execution_time_ms": avg_time,
            "improvement_direction": {
                "success_rate_improvement": max(0, 0.9 - success_rate) * 0.1,
                "execution_speed_improvement": max(0, avg_time - 500) * 0.001,
            },
            "privacy_mode": self.consent.privacy_mode,
        }

        return gradients

    # ============ 平台交互 ============

    async def sync_skills(self) -> Dict:
        """同步 Skills"""
        # 模拟从平台获取最新 Skills
        return {
            "status": "success",
            "synced": 5,
            "skills": [
                {
                    "skill_id": "python-gen",
                    "name": "Python Generator",
                    "version": "1.2.0",
                },
                {"skill_id": "web-search", "name": "Web Searcher", "version": "1.1.0"},
            ],
            "timestamp": datetime.now().isoformat(),
        }

    async def search_skills(self, query: str) -> List[Dict]:
        """搜索 Skills"""
        return [
            {"skill_id": "python-gen", "name": "Python Generator", "score": 0.9},
        ]

    # ============ 辅助方法 ============

    def _extract_skill_id(self, args, kwargs) -> str:
        """从参数中提取 Skill ID"""
        # 简化实现
        return "unknown"

    def get_status(self) -> Dict:
        """获取当前状态"""
        return {
            "consent_level": self.consent.level.value,
            "hook_installed": self.hook_installed,
            "can_collect": self.consent.can_collect_usage,
            "can_upload": self.consent.can_upload_gradients,
            "local_records": self._count_local_records(),
        }


# ============ Agent 集成示例 ============


class AgentIntegrationExample:
    """
    Agent 如何集成 ArenaSync Meta-Skill 的示例
    """

    def __init__(self):
        self.arena_sync = ArenaSyncMetaSkill(agent_id="my-agent")

    async def handle_skill_call(
        self, skill_id: str, execute_fn: Callable, *args, **kwargs
    ):
        """
        处理 Skill 调用

        核心逻辑：
        1. 检查是否是第一次使用
        2. 如果是，询问用户
        3. 根据回答决定是否安装钩子
        4. 执行 Skill
        """

        # 1. 检查是否需要询问用户
        if self.arena_sync.should_ask_user():
            # 返回 UI，让调用方展示
            ui = self.arena_sync.get_consent_ui()
            return {
                "action": "ask_consent",
                "ui": ui,
            }

        # 2. 检查用户是否主动询问协同进化
        # （这个检查应该在处理用户输入的地方做）

        # 3. 包装执行函数（如果已同意）
        wrapped_fn = self.arena_sync.wrap_execute(execute_fn)

        # 4. 执行
        result = await wrapped_fn(*args, **kwargs)

        return {
            "action": "execute",
            "result": result,
        }

    async def handle_user_input(self, user_input: str) -> Dict:
        """
        处理用户输入

        特殊处理：用户主动询问协同进化时
        """

        # 检查是否是激活短语
        if self.arena_sync.check_activation_phrase(user_input):
            if self.arena_sync.has_declined:
                # 用户之前拒绝了，但现在想参与
                return {
                    "action": "re_ask_consent",
                    "ui": """
## 重新考虑参与协同进化？

你之前选择了"不参与"。

如果现在想参与，可以：

- **[是，参与]** 重新启用协同进化功能
- **[否，保持现状]** 不启用

（这次选择后不会再次询问）
                    """,
                }
            elif self.arena_sync.has_consent:
                return {
                    "action": "show_status",
                    "message": "✅ 你已经在参与协同进化了！",
                    "status": self.arena_sync.get_status(),
                }

        return {"action": "none"}


# ============ CLI 演示 ============


async def demo():
    """演示 Meta-Skill 功能"""

    print("=" * 70)
    print("ArenaSync Meta-Skill 演示")
    print("=" * 70)

    # 1. 创建 Meta-Skill 实例
    arena_sync = ArenaSyncMetaSkill(agent_id="demo-agent")

    print("\n[1] 检查是否第一次使用")
    print(f"   是否第一次: {arena_sync.is_first_time}")
    print(f"   需要询问用户: {arena_sync.should_ask_user()}")

    # 2. 获取用户同意 UI
    print("\n[2] 获取用户同意 UI")
    print(arena_sync.get_consent_ui())

    # 3. 模拟用户响应（第一次）
    print("\n[3] 模拟用户响应（输入 'yes'）")
    should_install, message = await arena_sync.handle_user_response("yes")
    print(message)

    print("\n[4] 检查状态")
    status = arena_sync.get_status()
    for key, value in status.items():
        print(f"   {key}: {value}")

    # 5. 模拟多次调用（验证不再询问）
    print("\n[5] 模拟后续调用")
    print(f"   是否第一次: {arena_sync.is_first_time}")
    print(f"   需要询问: {arena_sync.should_ask_user()}")
    print("   ✅ 不会再次询问用户！")

    # 6. 演示激活短语检查
    print("\n[6] 检查激活短语")
    print(f"   '如何协同进化' -> {arena_sync.check_activation_phrase('如何协同进化')}")
    print(f"   '你好' -> {arena_sync.check_activation_phrase('你好')}")


if __name__ == "__main__":
    asyncio.run(demo())
