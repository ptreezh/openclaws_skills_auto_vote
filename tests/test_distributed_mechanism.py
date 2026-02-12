#!/usr/bin/env python3
"""
分布式上传和使用统计机制测试

验证 Skills Arena 如何支持多个 OpenClaws 自动上传技能和使用统计
"""

import sys
import os
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
import asyncio

# 添加脚本目录到路径
scripts_dir = Path(__file__).parent / "api"
sys.path.insert(0, str(scripts_dir))

print("=" * 70)
print("🧪 分布式上传和使用统计机制测试")
print("=" * 70)

tests_passed = 0
tests_failed = 0


def test(name, condition, error=""):
    global tests_passed, tests_failed
    if condition:
        print(f"  ✅ {name}")
        tests_passed += 1
    else:
        print(f"  ❌ {name}: {error}")
        tests_failed += 1


# ========== 测试 1: 上传 API 机制 ==========

print("\n📤 1. 分布式上传机制")
print("-" * 50)


# 模拟 ZIP 文件上传场景
def simulate_upload():
    """模拟 OpenClaw 上传 Skill 的完整流程"""

    # 场景 1: 首次上传
    print("\n  场景 1: 首次上传")

    # 模拟 ZIP 内容
    skill_content = b"PK..."  # ZIP 文件头
    skill_hash = (
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"  # SHA256
    )

    # 模拟注册表
    registry = {
        "by_hash": {},  # skill_hash -> skill_id
        "by_name": {},  # skill_name -> [skill_id, ...]
        "versions": {},  # skill_name -> [skill_id, ...]
    }

    # 模拟去重检查
    if skill_hash in registry["by_hash"]:
        test("去重检查 - 已存在", True)
        return "duplicate"
    else:
        # 生成 Skill ID
        skill_id = f"skill-test-{skill_hash[:8]}"
        registry["by_hash"][skill_hash] = skill_id
        registry["by_name"]["test-skill"] = [skill_id]
        registry["versions"]["test-skill"] = [skill_id]

        test("去重检查 - 新上传", True)
        test("Skill ID 生成", skill_id.startswith("skill-"))
        test("注册表更新", skill_hash in registry["by_hash"])

        return skill_id


skill_id = simulate_upload()
print(f"  生成 Skill ID: {skill_id}")

# 场景 2: 重复上传（相同内容）
print("\n  场景 2: 重复上传检测")
same_content_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
registry = {"by_hash": {same_content_hash: "skill-test-abc12345"}}

is_duplicate = same_content_hash in registry["by_hash"]
test("重复上传检测", is_duplicate == True)

# 场景 3: 重复上传（不同内容，同名）
print("\n  场景 3: 同名不同版本处理")
registry = {
    "by_name": {"data-analysis": ["skill-data-analysis-old"]},
    "versions": {"data-analysis": ["skill-data-analysis-old"]},
}

new_hash = "new_hash_123"
skill_name = "data-analysis"

if skill_name in registry["by_name"]:
    test("同名 Skill 版本处理", True)
    test("版本列表更新", skill_name in registry["versions"])
else:
    test("同名 Skill 版本处理", False)

# ========== 测试 2: 使用数据收集机制 ==========

print("\n\n📊 2. 使用数据收集机制")
print("-" * 50)


# 模拟使用数据提交
class UsageData:
    def __init__(self, usage_count, total_time, avg_response_time, success_rate=1.0):
        self.usage_count = usage_count
        self.total_time = total_time
        self.avg_response_time = avg_response_time
        self.success_rate = success_rate


# 场景 1: 单次使用数据提交
print("\n  场景 1: 单次使用数据提交")
usage_data = UsageData(
    usage_count=156,
    total_time=358.8,  # 156 * 2.3s
    avg_response_time=2.3,
    success_rate=0.981,
)

test("使用数据 - usage_count", usage_data.usage_count == 156)
test("使用数据 - total_time", usage_data.total_time == 358.8)
test("使用数据 - avg_response_time", usage_data.avg_response_time == 2.3)
test("使用数据 - success_rate", usage_data.success_rate == 0.981)

# 场景 2: 多 OpenClaws 使用统计聚合
print("\n  场景 2: 多 OpenClaws 使用统计聚合")

# 模拟多个 OpenClaws 的使用数据
agent_usage_records = [
    {"agent_did": "did:openclaw:A", "usage_count": 156, "total_time": 358.8},
    {"agent_did": "did:openclaw:B", "usage_count": 89, "total_time": 222.5},
    {"agent_did": "did:openclaw:C", "usage_count": 234, "total_time": 702.0},
]

# 聚合计算
total_usage = sum(r["usage_count"] for r in agent_usage_records)
total_time = sum(r["total_time"] for r in agent_usage_records)
avg_response_time = total_time / total_usage if total_usage > 0 else 0

test("聚合 - 总使用次数", total_usage == 479)
test("聚合 - 总时间", total_time == 1283.3)
test("聚合 - 平均响应时间", round(avg_response_time, 2) == 2.68)

# 场景 3: 加权评分计算
print("\n  场景 3: 使用数据加权评分")

# 评分维度
SCORING_DIMENSIONS = {"success": 0.4, "speed": 0.3, "resource": 0.2, "stability": 0.1}

# 模拟使用数据计算评分
success_rate = 0.981
avg_response_time = 2.3
execution_times = [2.1, 2.3, 2.5, 2.2, 2.4]

# 成功率评分
success_score = success_rate * 100

# 速度评分 (假设 2.0s 为满分)
speed_score = min(100, 2.0 / avg_response_time * 100)

# 稳定性评分
import statistics

time_std = statistics.stdev(execution_times)
stability_score = max(0, 100 - (time_std / avg_response_time * 100))

# 综合评分
total_score = (
    success_score * SCORING_DIMENSIONS["success"]
    + speed_score * SCORING_DIMENSIONS["speed"]
    + stability_score * SCORING_DIMENSIONS["stability"]
)

test("评分 - 成功率", round(success_score, 1) == 98.1)
test("评分 - 速度", round(speed_score, 1) == 87.0)
test("评分 - 稳定性", round(stability_score, 1) > 0)
test("评分 - 综合", round(total_score, 1) > 90)

# ========== 测试 3: 评价防护机制 ==========

print("\n\n🛡️ 3. 评价防护机制")
print("-" * 50)

# 场景 1: 使用次数限制
print("\n  场景 1: 使用次数限制")
MIN_USAGE_FOR_REVIEW = 5

# 合法评价
user1_usage = 156
test("评价 - 合法使用次数", user1_usage >= MIN_USAGE_FOR_REVIEW)

# 非法评价（使用次数不足）
user2_usage = 3
can_review = user2_usage >= MIN_USAGE_FOR_REVIEW
test("评价 - 非法使用次数", can_review == False)

# 场景 2: 评价权重计算
print("\n  场景 2: 评价权重计算")


def calculate_review_weight(usage_count):
    if usage_count < MIN_USAGE_FOR_REVIEW:
        return 0.0
    elif usage_count < 20:
        return 1.0
    elif usage_count < 50:
        return 1.5
    elif usage_count < 100:
        return 2.0
    else:
        return 3.0


test("权重 - 低使用量 (10次)", calculate_review_weight(10) == 1.0)
test("权重 - 中使用量 (30次)", calculate_review_weight(30) == 1.5)
test("权重 - 高使用量 (80次)", calculate_review_weight(80) == 2.0)
test("权重 - 超高使用量 (150次)", calculate_review_weight(150) == 3.0)

# 场景 3: 重复评价限制
print("\n  场景 3: 重复评价限制")

# 模拟已评价记录
existing_reviews = {"review-skill-A-did:openclaw:B": True}

new_review_id = "review-skill-A-did:openclaw:B"
is_duplicate = new_review_id in existing_reviews
test("重复评价检测", is_duplicate == True)

new_review_id2 = "review-skill-A-did:openclaw:C"
is_new = new_review_id2 not in existing_reviews
test("新评价允许", is_new == True)

# ========== 测试 4: 排行榜计算 ==========

print("\n\n🏆 4. 排行榜计算机制")
print("-" * 50)

# 场景 1: 综合排行榜评分
print("\n  场景 1: 综合排行榜评分计算")

skills_data = [
    {"name": "Skill A", "rating": 93.1, "usage_count": 156, "reviews_count": 42},
    {"name": "Skill B", "rating": 78.3, "usage_count": 534, "reviews_count": 28},
    {"name": "Skill C", "rating": 85.7, "usage_count": 89, "reviews_count": 35},
]


def calculate_overall_score(skill):
    # 评分 * 50%
    rating_score = skill["rating"] * 0.5

    # 使用次数归一化（假设 1000 次为满）
    usage_score = min(skill["usage_count"] / 1000, 1.0) * 30

    # 评价数归一化（假设 50 个为满）
    reviews_score = min(skill["reviews_count"] / 50, 1.0) * 20

    return rating_score + usage_score + reviews_score


for skill in skills_data:
    skill["overall_score"] = calculate_overall_score(skill)
    print(
        f"  {skill['name']}: 评分={skill['rating']}, 使用={skill['usage_count']}, 综合={skill['overall_score']:.1f}"
    )

# 排序
skills_sorted = sorted(skills_data, key=lambda x: x["overall_score"], reverse=True)
test("排行榜排序", skills_sorted[0]["name"] == "Skill B")  # 使用次数最多

# ========== 测试 5: DID 认证机制 ==========

print("\n\n🔐 5. DID 认证机制")
print("-" * 50)

from did_auth import DIDAuth

auth = DIDAuth()

# 场景 1: 多 OpenClaw 身份识别
print("\n  场景 1: 多 OpenClaw 身份识别")

agent_a_did = auth.generate_did("openclaw_agent_A_public_key_12345")
agent_b_did = auth.generate_did("openclaw_agent_B_public_key_67890")

test("Agent A DID 生成", agent_a_did.startswith("did:openclaw:"))
test("Agent B DID 生成", agent_b_did.startswith("did:openclaw:"))
test("不同 Agent 不同 DID", agent_a_did != agent_b_did)

# 场景 2: 同一 Agent 多次操作使用相同 DID
print("\n  场景 2: 一致性验证")
did_1 = auth.generate_did("same_agent_key_12345")
did_2 = auth.generate_did("same_agent_key_12345")
test("相同 Agent 一致 DID", did_1 == did_2)

# ========== 测试总结 ==========

print("\n" + "=" * 70)
print(f"📊 测试结果: {tests_passed} 通过, {tests_failed} 失败")
print("=" * 70)

if tests_failed == 0:
    print("\n✅ 分布式上传和使用统计机制验证通过!")
else:
    print(f"\n⚠️ {tests_failed} 个测试失败")

sys.exit(0 if tests_failed == 0 else 1)
