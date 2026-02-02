#!/usr/bin/env python3
"""
初始化演示数据

为 Skills 擂台创建初始的演示场景、Skills 和评价
"""

import sys
from pathlib import Path

# 导入管理器
sys.path.insert(0, str(Path(__file__).parent))
from arena_manager import ArenaManager


def init_demo_data():
    """初始化演示数据"""

    print("=" * 80)
    print("Skills 擂台 - 初始化演示数据")
    print("=" * 80)

    # 初始化管理器 - 使用相对路径（从 scripts 目录）
    manager = ArenaManager(data_dir="../data")

    # 创建场景
    print("\n📋 创建评比场景...")
    scenarios = [
        {
            "title": "代码生成",
            "description": "测试 Skills 在生成 Python、JavaScript 等编程语言代码方面的能力。评估标准：代码正确性、可读性、最佳实践遵循度。",
            "category": "code-generation"
        },
        {
            "title": "文本创作",
            "description": "测试 Skills 在创作文章、故事、营销文案等文本内容方面的能力。评估标准：创意性、逻辑性、可读性。",
            "category": "content-creation"
        },
        {
            "title": "数据分析",
            "description": "测试 Skills 在分析数据、生成报告、提供洞察方面的能力。评估标准：分析深度、洞察质量、可视化建议。",
            "category": "data-analysis"
        },
        {
            "title": "对话问答",
            "description": "测试 Skills 在多轮对话、知识问答、问题解决方面的能力。评估标准：准确性、相关性、实用性。",
            "category": "conversational-ai"
        }
    ]

    created_scenarios = {}
    for s in scenarios:
        scenario = manager.create_scenario(
            title=s["title"],
            description=s["description"],
            category=s["category"]
        )
        created_scenarios[s["category"]] = scenario

    # 注册 Skills
    print("\n🤖 注册参赛 Skills...")
    skills = [
        {
            "skill_name": "GPT-4-Turbo",
            "description": "OpenAI 的先进语言模型，擅长多任务处理，在编程、创作、分析等方面表现出色。",
            "author": "OpenAI"
        },
        {
            "skill_name": "Claude-3.5-Sonnet",
            "description": "Anthropic 的高性能模型，以出色的推理能力和安全对齐著称，特别适合长文本处理。",
            "author": "Anthropic"
        },
        {
            "skill_name": "Gemini-Pro",
            "description": "Google DeepMind 开发的大语言模型，在多模态处理和长文本理解方面有优势。",
            "author": "Google"
        },
        {
            "skill_name": "Qwen-Max",
            "description": "阿里云通义千问大模型，在中文理解和代码生成方面表现优异，适合国内应用场景。",
            "author": "Alibaba"
        },
        {
            "skill_name": "Llama-3.1-70B",
            "description": "Meta 开源的大型语言模型，可本地部署，性能接近闭源模型，隐私安全性高。",
            "author": "Meta"
        },
        {
            "skill_name": "DeepSeek-Coder-V2",
            "description": "深度求索开发的代码大模型，在代码生成和代码理解方面有专门优化。",
            "author": "DeepSeek"
        }
    ]

    created_skills = {}
    for s in skills:
        skill = manager.register_skill(
            skill_name=s["skill_name"],
            description=s["description"],
            author=s["author"]
        )
        created_skills[s["skill_name"]] = skill

    # 将 Skills 添加到各个场景
    print("\n🔗 注册 Skills 到场景...")

    # 代码生成场景
    code_gen_skills = [
        created_skills["GPT-4-Turbo"],
        created_skills["Claude-3.5-Sonnet"],
        created_skills["Gemini-Pro"],
        created_skills["DeepSeek-Coder-V2"],
        created_skills["Llama-3.1-70B"]
    ]
    for skill in code_gen_skills:
        manager.add_skill_to_scenario(
            created_scenarios["code-generation"]["scenario_id"],
            skill["skill_id"]
        )

    # 文本创作场景
    content_skills = [
        created_skills["GPT-4-Turbo"],
        created_skills["Claude-3.5-Sonnet"],
        created_skills["Gemini-Pro"],
        created_skills["Qwen-Max"]
    ]
    for skill in content_skills:
        manager.add_skill_to_scenario(
            created_scenarios["content-creation"]["scenario_id"],
            skill["skill_id"]
        )

    # 数据分析场景
    data_skills = [
        created_skills["GPT-4-Turbo"],
        created_skills["Claude-3.5-Sonnet"],
        created_skills["Qwen-Max"],
        created_skills["Gemini-Pro"]
    ]
    for skill in data_skills:
        manager.add_skill_to_scenario(
            created_scenarios["data-analysis"]["scenario_id"],
            skill["skill_id"]
        )

    # 对话问答场景
    conv_skills = [
        created_skills["GPT-4-Turbo"],
        created_skills["Claude-3.5-Sonnet"],
        created_skills["Qwen-Max"],
        created_skills["Llama-3.1-70B"]
    ]
    for skill in conv_skills:
        manager.add_skill_to_scenario(
            created_scenarios["conversational-ai"]["scenario_id"],
            skill["skill_id"]
        )

    # 提交演示评价
    print("\n⭐ 提交演示评价...")

    # 代码生成场景评价
    reviews_code_gen = [
        {
            "skill": "GPT-4-Turbo",
            "user_id": "dev-001",
            "rating": 4.8,
            "metrics": {"accuracy": 4.7, "efficiency": 4.9, "creativity": 4.8},
            "comment": "代码生成质量非常高，Bug 率低，但有时候会产生幻觉函数。"
        },
        {
            "skill": "GPT-4-Turbo",
            "user_id": "dev-002",
            "rating": 4.5,
            "metrics": {"accuracy": 4.5, "efficiency": 4.2, "creativity": 4.8},
            "comment": "很好的编程助手，特别是理解复杂需求的能力。"
        },
        {
            "skill": "GPT-4-Turbo",
            "user_id": "dev-003",
            "rating": 4.9,
            "metrics": {"accuracy": 4.9, "efficiency": 4.9, "creativity": 4.9},
            "comment": "目前最好的代码生成模型，推荐！"
        },
        {
            "skill": "Claude-3.5-Sonnet",
            "user_id": "dev-001",
            "rating": 4.6,
            "metrics": {"accuracy": 4.8, "efficiency": 4.0, "creativity": 5.0},
            "comment": "推理能力很强，代码质量高，但响应速度稍慢。"
        },
        {
            "skill": "Claude-3.5-Sonnet",
            "user_id": "dev-004",
            "rating": 4.7,
            "metrics": {"accuracy": 4.7, "efficiency": 4.3, "creativity": 5.0},
            "comment": "在处理复杂架构设计时表现出色。"
        },
        {
            "skill": "Gemini-Pro",
            "user_id": "dev-002",
            "rating": 4.2,
            "metrics": {"accuracy": 4.0, "efficiency": 4.5, "creativity": 4.1},
            "comment": "整体表现不错，但在某些复杂场景下理解不够准确。"
        },
        {
            "skill": "DeepSeek-Coder-V2",
            "user_id": "dev-003",
            "rating": 4.4,
            "metrics": {"accuracy": 4.6, "efficiency": 4.5, "creativity": 4.1},
            "comment": "代码生成专业化程度高，特别是对于 Python 和 C++。"
        },
        {
            "skill": "Llama-3.1-70B",
            "user_id": "dev-005",
            "rating": 4.0,
            "metrics": {"accuracy": 3.8, "efficiency": 3.5, "creativity": 4.5},
            "comment": "本地部署的首选，虽然速度稍慢，但隐私安全性好。"
        }
    ]

    for r in reviews_code_gen:
        skill = created_skills[r["skill"]]
        manager.submit_review(
            scenario_id=created_scenarios["code-generation"]["scenario_id"],
            skill_id=skill["skill_id"],
            user_id=r["user_id"],
            rating=r["rating"],
            metrics=r["metrics"],
            comment=r["comment"]
        )

    # 文本创作场景评价
    reviews_content = [
        {
            "skill": "GPT-4-Turbo",
            "user_id": "writer-001",
            "rating": 4.7,
            "metrics": {"accuracy": 4.5, "efficiency": 4.8, "creativity": 4.8},
            "comment": "创意性强，写作风格多样，但有时过于冗长。"
        },
        {
            "skill": "GPT-4-Turbo",
            "user_id": "writer-002",
            "rating": 4.5,
            "metrics": {"accuracy": 4.3, "efficiency": 4.7, "creativity": 4.5},
            "comment": "适合日常写作，但在特定领域需要更多上下文。"
        },
        {
            "skill": "Claude-3.5-Sonnet",
            "user_id": "writer-001",
            "rating": 4.9,
            "metrics": {"accuracy": 4.8, "efficiency": 4.5, "creativity": 5.0},
            "comment": "文学创作能力超强，长文本处理无与伦比！"
        },
        {
            "skill": "Claude-3.5-Sonnet",
            "user_id": "writer-003",
            "rating": 4.8,
            "metrics": {"accuracy": 4.7, "efficiency": 4.6, "creativity": 5.0},
            "comment": "在深度写作和创意文案方面表现出色。"
        },
        {
            "skill": "Qwen-Max",
            "user_id": "writer-004",
            "rating": 4.3,
            "metrics": {"accuracy": 4.2, "efficiency": 4.5, "creativity": 4.2},
            "comment": "中文写作能力强，特别适合国内应用场景。"
        },
        {
            "skill": "Gemini-Pro",
            "user_id": "writer-002",
            "rating": 4.1,
            "metrics": {"accuracy": 4.0, "efficiency": 4.3, "creativity": 4.0},
            "comment": "整体表现不错，但在创意写作方面稍逊。"
        }
    ]

    for r in reviews_content:
        skill = created_skills[r["skill"]]
        manager.submit_review(
            scenario_id=created_scenarios["content-creation"]["scenario_id"],
            skill_id=skill["skill_id"],
            user_id=r["user_id"],
            rating=r["rating"],
            metrics=r["metrics"],
            comment=r["comment"]
        )

    # 数据分析场景评价
    reviews_data = [
        {
            "skill": "GPT-4-Turbo",
            "user_id": "analyst-001",
            "rating": 4.6,
            "metrics": {"accuracy": 4.7, "efficiency": 4.5, "creativity": 4.6},
            "comment": "分析深度好，能提供有价值的洞察。"
        },
        {
            "skill": "Claude-3.5-Sonnet",
            "user_id": "analyst-001",
            "rating": 4.8,
            "metrics": {"accuracy": 4.9, "efficiency": 4.3, "creativity": 5.0},
            "comment": "在复杂数据分析和模式识别方面表现卓越。"
        },
        {
            "skill": "Qwen-Max",
            "user_id": "analyst-002",
            "rating": 4.4,
            "metrics": {"accuracy": 4.3, "efficiency": 4.5, "creativity": 4.4},
            "comment": "中文数据分析能力强，适合国内数据场景。"
        },
        {
            "skill": "Gemini-Pro",
            "user_id": "analyst-003",
            "rating": 4.2,
            "metrics": {"accuracy": 4.1, "efficiency": 4.4, "creativity": 4.1},
            "comment": "基本分析能力不错，但在深度洞察方面有待提升。"
        }
    ]

    for r in reviews_data:
        skill = created_skills[r["skill"]]
        manager.submit_review(
            scenario_id=created_scenarios["data-analysis"]["scenario_id"],
            skill_id=skill["skill_id"],
            user_id=r["user_id"],
            rating=r["rating"],
            metrics=r["metrics"],
            comment=r["comment"]
        )

    # 对话问答场景评价
    reviews_conv = [
        {
            "skill": "GPT-4-Turbo",
            "user_id": "user-001",
            "rating": 4.7,
            "metrics": {"accuracy": 4.8, "efficiency": 4.7, "creativity": 4.6},
            "comment": "回答准确，上下文理解能力强，是多轮对话的首选。"
        },
        {
            "skill": "Claude-3.5-Sonnet",
            "user_id": "user-001",
            "rating": 4.8,
            "metrics": {"accuracy": 4.9, "efficiency": 4.4, "creativity": 5.0},
            "comment": "推理能力强，能处理复杂问题，回答更有深度。"
        },
        {
            "skill": "Qwen-Max",
            "user_id": "user-002",
            "rating": 4.5,
            "metrics": {"accuracy": 4.5, "efficiency": 4.6, "creativity": 4.4},
            "comment": "中文问答能力强，适合中文用户。"
        },
        {
            "skill": "Llama-3.1-70B",
            "user_id": "user-003",
            "rating": 4.2,
            "metrics": {"accuracy": 4.1, "efficiency": 3.8, "creativity": 4.5},
            "comment": "开源模型中的佼佼者，本地部署安全可靠。"
        }
    ]

    for r in reviews_conv:
        skill = created_skills[r["skill"]]
        manager.submit_review(
            scenario_id=created_scenarios["conversational-ai"]["scenario_id"],
            skill_id=skill["skill_id"],
            user_id=r["user_id"],
            rating=r["rating"],
            metrics=r["metrics"],
            comment=r["comment"]
        )

    # 生成排行榜
    print("\n🏆 生成排行榜...")
    leaderboards = {}
    for category, scenario in created_scenarios.items():
        leaderboard = manager.generate_leaderboard(scenario["scenario_id"])
        leaderboards[category] = leaderboard

    # 打印统计信息
    print("\n📊 初始化完成统计")
    print("=" * 80)

    all_scenarios = manager.list_scenarios()
    all_skills = manager.list_skills()

    total_reviews = 0
    for scenario in all_scenarios:
        total_reviews += scenario["metrics"]["total_reviews"]

    print(f"场景总数: {len(all_scenarios)}")
    print(f"Skills 总数: {len(all_skills)}")
    print(f"评价总数: {total_reviews}")
    print()

    # 打印各场景排行榜摘要
    for category, leaderboard in leaderboards.items():
        print(f"【{leaderboard['scenario_title']}】排行榜 TOP 3")
        print("-" * 80)
        print(f"{'排名':<6} {'Skill 名称':<25} {'综合评分':<10} {'评价数':<8}")
        print("-" * 80)
        for item in leaderboard["leaderboard"][:3]:
            print(
                f"#{item['rank']:<5} {item['skill_name']:<25} "
                f"{item['metrics']['avg_rating']:<10.2f} "
                f"{item['metrics']['total_reviews']:<8}"
            )
        print()

    print("=" * 80)
    print("✅ 演示数据初始化完成！")
    print("=" * 80)
    print("\n启动 Web 服务器：")
    print("  python skills-arena/scripts/web_server.py")
    print("\n访问地址：")
    print("  http://localhost:5000")


if __name__ == "__main__":
    init_demo_data()
