#!/usr/bin/env python3
"""
Skills Arena Manager - 核心管理器

管理擂台评比的所有核心逻辑：
- 场景管理
- Skill 注册
- 用户评价收集
- 排行榜生成
"""

import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


class ArenaManager:
    """
    Skills 擂台管理器

    核心功能：
    1. 场景管理：创建、查询、更新评比场景
    2. Skill 管理：注册、查询 Skills
    3. 评价管理：收集、存储、统计用户评价
    4. 排行榜：基于评分生成 Skills 排名
    """

    def __init__(self, data_dir: str = "./skills-arena/data"):
        """
        初始化管理器

        Args:
            data_dir: 数据存储目录
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # 子目录
        self.scenarios_dir = self.data_dir / "scenarios"
        self.scenarios_dir.mkdir(exist_ok=True)

        self.skills_dir = self.data_dir / "skills"
        self.skills_dir.mkdir(exist_ok=True)

        self.reviews_dir = self.data_dir / "reviews"
        self.reviews_dir.mkdir(exist_ok=True)

        self.leaderboards_dir = self.data_dir / "leaderboards"
        self.leaderboards_dir.mkdir(exist_ok=True)

    def create_scenario(self, title: str, description: str, category: str) -> Dict:
        """
        创建评比场景

        Args:
            title: 场景标题
            description: 场景描述
            category: 场景分类

        Returns:
            场景数据
        """
        scenario_id = f"scenario-{uuid.uuid4().hex[:12]}"

        scenario = {
            "scenario_id": scenario_id,
            "title": title,
            "description": description,
            "category": category,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "status": "active",
            "registered_skills": [],  # 注册的 Skills 列表
            "metrics": {
                "total_reviews": 0,
                "total_skills": 0,
                "avg_rating": 0.0
            }
        }

        self._save_scenario(scenario_id, scenario)

        print(f"✓ Created scenario: {scenario_id}")
        print(f"  Title: {title}")
        print(f"  Category: {category}")

        return scenario

    def register_skill(self, skill_name: str, description: str, author: str = "anonymous") -> Dict:
        """
        注册 Skill

        Args:
            skill_name: Skill 名称
            description: Skill 描述
            author: 作者

        Returns:
            Skill 数据
        """
        skill_id = f"skill-{uuid.uuid4().hex[:12]}"

        skill = {
            "skill_id": skill_id,
            "skill_name": skill_name,
            "description": description,
            "author": author,
            "registered_at": datetime.now().isoformat(),
            "metrics": {
                "total_reviews": 0,
                "avg_rating": 0.0,
                "avg_accuracy": 0.0,
                "avg_efficiency": 0.0,
                "avg_creativity": 0.0
            },
            "categories": []  # 参与的场景分类
        }

        self._save_skill(skill_id, skill)

        print(f"✓ Registered skill: {skill_id}")
        print(f"  Name: {skill_name}")
        print(f"  Author: {author}")

        return skill

    def add_skill_to_scenario(self, scenario_id: str, skill_id: str) -> Dict:
        """
        将 Skill 添加到场景

        Args:
            scenario_id: 场景 ID
            skill_id: Skill ID

        Returns:
            更新后的场景数据
        """
        scenario = self.load_scenario(scenario_id)
        if not scenario:
            raise ValueError(f"Scenario {scenario_id} not found")

        skill = self.load_skill(skill_id)
        if not skill:
            raise ValueError(f"Skill {skill_id} not found")

        # 检查是否已注册
        if skill_id in scenario["registered_skills"]:
            print(f"⚠ Skill {skill_id} already in scenario {scenario_id}")
            return scenario

        # 添加到场景
        scenario["registered_skills"].append(skill_id)
        scenario["updated_at"] = datetime.now().isoformat()
        scenario["metrics"]["total_skills"] = len(scenario["registered_skills"])

        # 更新 Skill 的分类列表
        skill["categories"].append(scenario["category"])
        skill["registered_at"] = datetime.now().isoformat()

        # 保存
        self._save_scenario(scenario_id, scenario)
        self._save_skill(skill_id, skill)

        print(f"✓ Added skill {skill_id} to scenario {scenario_id}")

        return scenario

    def submit_review(
        self,
        scenario_id: str,
        skill_id: str,
        user_id: str,
        rating: float,
        metrics: Dict[str, float],
        comment: str = ""
    ) -> Dict:
        """
        提交用户评价

        Args:
            scenario_id: 场景 ID
            skill_id: Skill ID
            user_id: 用户 ID
            rating: 总体评分 (1-5)
            metrics: 细分指标评分
            comment: 用户评论

        Returns:
            评价数据
        """
        # 验证
        scenario = self.load_scenario(scenario_id)
        if not scenario:
            raise ValueError(f"Scenario {scenario_id} not found")

        skill = self.load_skill(skill_id)
        if not skill:
            raise ValueError(f"Skill {skill_id} not found")

        if skill_id not in scenario["registered_skills"]:
            raise ValueError(f"Skill {skill_id} not registered in scenario {scenario_id}")

        if not (1 <= rating <= 5):
            raise ValueError("Rating must be between 1 and 5")

        # 创建评价
        review_id = f"review-{uuid.uuid4().hex[:12]}"

        review = {
            "review_id": review_id,
            "scenario_id": scenario_id,
            "skill_id": skill_id,
            "user_id": user_id,
            "rating": rating,
            "metrics": {
                "accuracy": metrics.get("accuracy", 0.0),
                "efficiency": metrics.get("efficiency", 0.0),
                "creativity": metrics.get("creativity", 0.0)
            },
            "comment": comment,
            "created_at": datetime.now().isoformat(),
            "helpful_count": 0,  # 有用投票
            "flagged": False  # 是否被标记
        }

        # 保存评价
        self._save_review(review_id, review)

        # 更新场景指标
        scenario["metrics"]["total_reviews"] += 1
        scenario["updated_at"] = datetime.now().isoformat()
        self._save_scenario(scenario_id, scenario)

        # 更新 Skill 指标
        self._update_skill_metrics(skill_id)

        print(f"✓ Submitted review: {review_id}")
        print(f"  Skill: {skill['skill_name']}")
        print(f"  Rating: {rating}/5")

        return review

    def _update_skill_metrics(self, skill_id: str):
        """
        更新 Skill 的评分指标

        Args:
            skill_id: Skill ID
        """
        skill = self.load_skill(skill_id)
        if not skill:
            return

        # 获取该 Skill 的所有评价
        reviews = self.get_reviews_for_skill(skill_id)

        if not reviews:
            return

        # 计算平均值
        total_reviews = len(reviews)
        total_rating = sum(r["rating"] for r in reviews)
        total_accuracy = sum(r["metrics"]["accuracy"] for r in reviews)
        total_efficiency = sum(r["metrics"]["efficiency"] for r in reviews)
        total_creativity = sum(r["metrics"]["creativity"] for r in reviews)

        skill["metrics"] = {
            "total_reviews": total_reviews,
            "avg_rating": round(total_rating / total_reviews, 2),
            "avg_accuracy": round(total_accuracy / total_reviews, 2),
            "avg_efficiency": round(total_efficiency / total_reviews, 2),
            "avg_creativity": round(total_creativity / total_reviews, 2)
        }
        skill["updated_at"] = datetime.now().isoformat()

        self._save_skill(skill_id, skill)

    def get_reviews_for_skill(self, skill_id: str) -> List[Dict]:
        """
        获取某个 Skill 的所有评价

        Args:
            skill_id: Skill ID

        Returns:
            评价列表
        """
        reviews = []
        for review_file in self.reviews_dir.glob("review-*.json"):
            with open(review_file, 'r', encoding='utf-8') as f:
                review = json.load(f)
                if review["skill_id"] == skill_id:
                    reviews.append(review)
        return reviews

    def generate_leaderboard(self, scenario_id: str) -> Dict:
        """
        生成排行榜

        Args:
            scenario_id: 场景 ID

        Returns:
            排行榜数据
        """
        scenario = self.load_scenario(scenario_id)
        if not scenario:
            raise ValueError(f"Scenario {scenario_id} not found")

        skill_ids = scenario["registered_skills"]
        leaderboard_data = []

        for skill_id in skill_ids:
            skill = self.load_skill(skill_id)
            if skill and skill["metrics"]["total_reviews"] > 0:
                leaderboard_data.append({
                    "skill_id": skill_id,
                    "skill_name": skill["skill_name"],
                    "author": skill["author"],
                    "metrics": skill["metrics"].copy()
                })

        # 排序：按综合评分降序
        leaderboard_data.sort(
            key=lambda x: x["metrics"]["avg_rating"],
            reverse=True
        )

        # 添加排名
        for idx, item in enumerate(leaderboard_data, 1):
            item["rank"] = idx

        leaderboard = {
            "scenario_id": scenario_id,
            "scenario_title": scenario["title"],
            "category": scenario["category"],
            "generated_at": datetime.now().isoformat(),
            "total_skills": len(leaderboard_data),
            "leaderboard": leaderboard_data
        }

        # 保存排行榜
        leaderboard_id = f"leaderboard-{uuid.uuid4().hex[:12]}"
        leaderboard_path = self.leaderboards_dir / f"{leaderboard_id}.json"
        with open(leaderboard_path, 'w', encoding='utf-8') as f:
            json.dump(leaderboard, f, indent=2, ensure_ascii=False)

        print(f"✓ Generated leaderboard: {leaderboard_id}")
        print(f"  Total skills: {len(leaderboard_data)}")

        return leaderboard

    def load_scenario(self, scenario_id: str) -> Optional[Dict]:
        """加载场景"""
        scenario_path = self.scenarios_dir / f"{scenario_id}.json"
        if not scenario_path.exists():
            return None
        with open(scenario_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def load_skill(self, skill_id: str) -> Optional[Dict]:
        """加载 Skill"""
        skill_path = self.skills_dir / f"{skill_id}.json"
        if not skill_path.exists():
            return None
        with open(skill_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _save_scenario(self, scenario_id: str, scenario: Dict):
        """保存场景"""
        scenario_path = self.scenarios_dir / f"{scenario_id}.json"
        with open(scenario_path, 'w', encoding='utf-8') as f:
            json.dump(scenario, f, indent=2, ensure_ascii=False)

    def _save_skill(self, skill_id: str, skill: Dict):
        """保存 Skill"""
        skill_path = self.skills_dir / f"{skill_id}.json"
        with open(skill_path, 'w', encoding='utf-8') as f:
            json.dump(skill, f, indent=2, ensure_ascii=False)

    def _save_review(self, review_id: str, review: Dict):
        """保存评价"""
        review_path = self.reviews_dir / f"{review_id}.json"
        with open(review_path, 'w', encoding='utf-8') as f:
            json.dump(review, f, indent=2, ensure_ascii=False)

    def list_scenarios(self) -> List[Dict]:
        """列出所有场景"""
        scenarios = []
        for scenario_file in self.scenarios_dir.glob("scenario-*.json"):
            with open(scenario_file, 'r', encoding='utf-8') as f:
                scenarios.append(json.load(f))
        return scenarios

    def list_skills(self) -> List[Dict]:
        """列出所有 Skills"""
        skills = []
        for skill_file in self.skills_dir.glob("skill-*.json"):
            with open(skill_file, 'r', encoding='utf-8') as f:
                skills.append(json.load(f))
        return skills

    def get_scenario_reviews(self, scenario_id: str, skill_id: str = None) -> List[Dict]:
        """
        获取场景的评价

        Args:
            scenario_id: 场景 ID
            skill_id: 可选，筛选特定 Skill

        Returns:
            评价列表
        """
        reviews = []
        for review_file in self.reviews_dir.glob("review-*.json"):
            with open(review_file, 'r', encoding='utf-8') as f:
                review = json.load(f)
                if review["scenario_id"] == scenario_id:
                    if skill_id is None or review["skill_id"] == skill_id:
                        reviews.append(review)
        # 按时间倒序
        reviews.sort(key=lambda x: x["created_at"], reverse=True)
        return reviews


def main():
    """测试管理器"""
    import tempfile
    import shutil

    # 创建临时目录
    temp_dir = tempfile.mkdtemp()
    print(f"Using temp directory: {temp_dir}")

    # 初始化
    manager = ArenaManager(data_dir=temp_dir)

    # 创建场景
    print("\n=== 创建场景 ===")
    scenario = manager.create_scenario(
        title="代码生成",
        description="测试 Skills 在生成 Python 代码方面的能力",
        category="code-generation"
    )
    scenario_id = scenario["scenario_id"]

    # 注册 Skills
    print("\n=== 注册 Skills ===")
    skill1 = manager.register_skill(
        skill_name="gpt-4-coder",
        description="基于 GPT-4 的代码生成助手",
        author="OpenAI"
    )

    skill2 = manager.register_skill(
        skill_name="claude-coder",
        description="基于 Claude 的代码生成助手",
        author="Anthropic"
    )

    skill3 = manager.register_skill(
        skill_name="local-llm-coder",
        description="基于本地 LLaMA 的代码生成助手",
        author="Community"
    )

    # 将 Skills 添加到场景
    print("\n=== 添加 Skills 到场景 ===")
    manager.add_skill_to_scenario(scenario_id, skill1["skill_id"])
    manager.add_skill_to_scenario(scenario_id, skill2["skill_id"])
    manager.add_skill_to_scenario(scenario_id, skill3["skill_id"])

    # 提交评价
    print("\n=== 提交用户评价 ===")
    manager.submit_review(
        scenario_id=scenario_id,
        skill_id=skill1["skill_id"],
        user_id="user-001",
        rating=4.5,
        metrics={"accuracy": 4.0, "efficiency": 4.5, "creativity": 5.0},
        comment="代码质量很好，但有时候会产生幻觉"
    )

    manager.submit_review(
        scenario_id=scenario_id,
        skill_id=skill1["skill_id"],
        user_id="user-002",
        rating=4.8,
        metrics={"accuracy": 4.5, "efficiency": 5.0, "creativity": 5.0},
        comment="非常稳定，推荐使用"
    )

    manager.submit_review(
        scenario_id=scenario_id,
        skill_id=skill2["skill_id"],
        user_id="user-001",
        rating=4.2,
        metrics={"accuracy": 4.5, "efficiency": 3.5, "creativity": 4.5},
        comment="准确率高，但响应速度稍慢"
    )

    manager.submit_review(
        scenario_id=scenario_id,
        skill_id=skill3["skill_id"],
        user_id="user-003",
        rating=3.5,
        metrics={"accuracy": 3.0, "efficiency": 4.0, "creativity": 3.5},
        comment="免费且可本地运行，适合离线场景"
    )

    # 生成排行榜
    print("\n=== 生成排行榜 ===")
    leaderboard = manager.generate_leaderboard(scenario_id)

    print(f"\n排行榜 - {leaderboard['scenario_title']}")
    print("=" * 80)
    print(f"{'排名':<6} {'Skill 名称':<25} {'评分':<8} {'准确性':<8} {'效率':<8} {'创意':<8}")
    print("-" * 80)
    for item in leaderboard["leaderboard"]:
        print(
            f"#{item['rank']:<5} {item['skill_name']:<25} "
            f"{item['metrics']['avg_rating']:<8.2f} "
            f"{item['metrics']['avg_accuracy']:<8.2f} "
            f"{item['metrics']['avg_efficiency']:<8.2f} "
            f"{item['metrics']['avg_creativity']:<8.2f}"
        )

    # 清理
    shutil.rmtree(temp_dir)
    print(f"\n✓ Cleaned up temp directory")


if __name__ == "__main__":
    main()
