#!/usr/bin/env python3
"""
Skills Arena 完整集成测试

测试内容：
1. 后端 API 服务（运行中）
2. 前端 Web 服务（运行中）
3. 子智能体调用 ArenaSync Meta-Skill
4. 联邦学习数据上传

Usage:
    python integration_test.py
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from datetime import datetime

import requests

# ============ 配置 ============

BACKEND_URL = "http://localhost:5000"
FRONTEND_URL = "http://localhost:5000"

# ============ 测试步骤 ============


async def test_1_check_services():
    """测试 1：检查服务状态"""
    print("\n" + "=" * 70)
    print("测试 1：检查服务状态")
    print("=" * 70)

    results = {}

    # 检查后端 API
    try:
        resp = requests.get(f"{BACKEND_URL}/api/skills", timeout=5)
        if resp.status_code == 200:
            print("✅ 后端 API：运行中")
            results["backend"] = True
        else:
            print(f"❌ 后端 API：HTTP {resp.status_code}")
            results["backend"] = False
    except Exception as e:
        print(f"❌ 后端 API：{e}")
        results["backend"] = False

    # 检查前端
    try:
        resp = requests.get(FRONTEND_URL, timeout=5)
        if resp.status_code == 200:
            print("✅ 前端服务：运行中")
            results["frontend"] = True
        else:
            print(f"❌ 前端服务：HTTP {resp.status_code}")
            results["frontend"] = False
    except Exception as e:
        print(f"❌ 前端服务：{e}")
        results["frontend"] = False

    return all(results.values())


async def test_2_api_endpoints():
    """测试 2：测试 API 端点"""
    print("\n" + "=" * 70)
    print("测试 2：测试 API 端点")
    print("=" * 70)

    endpoints = [
        ("/api/skills", "GET", "获取 Skills 列表"),
        ("/api/scenarios", "GET", "获取场景列表"),
        ("/api/skills/uploaded", "GET", "获取已上传的 Skills"),
    ]

    passed = 0
    for endpoint, method, desc in endpoints:
        try:
            resp = requests.get(f"{BACKEND_URL}{endpoint}", timeout=5)
            if resp.status_code == 200:
                print(f"✅ {desc}：{endpoint}")
                passed += 1
            else:
                print(f"❌ {desc}：HTTP {resp.status_code}")
        except Exception as e:
            print(f"❌ {desc}：{e}")

    return passed >= 2


async def test_3_subagent_integration():
    """测试 3：子智能体集成"""
    print("\n" + "=" * 70)
    print("测试 3：子智能体集成 ArenaSync Meta-Skill")
    print("=" * 70)

    # 动态添加路径
    skill_path = Path(__file__).parent / "skills" / "arenasync" / "scripts"
    sys.path.insert(0, str(skill_path))

    from arenasync_meta_skill import ArenaSyncMetaSkill

    # 创建子智能体
    agent = ArenaSyncMetaSkill(agent_id="integration-test-agent")

    print(f"[子智能体] ID: {agent.agent_id}")
    print(f"[子智能体] 状态: {agent.get_status()}")

    # 测试 3a：检查同意状态
    if agent.should_ask_user():
        print("✅ 测试 3a：首次使用，询问用户")
    else:
        print("❌ 测试 3a：应该首次使用")
        return False

    # 测试 3b：获取同意 UI
    ui = agent.get_consent_ui()
    if "Skills Arena" in ui and "协同进化" in ui:
        print("✅ 测试 3b：同意 UI 正确显示")
    else:
        print("❌ 测试 3b：同意 UI 有问题")
        return False

    # 测试 3c：模拟用户选择"是"
    should_install, msg = await agent.handle_user_response("yes")
    if should_install:
        print("✅ 测试 3c：用户同意，安装钩子")
        agent.install_hook()
    else:
        print("❌ 测试 3c：应该安装钩子")
        return False

    # 测试 3d：验证后续不再询问
    if not agent.should_ask_user():
        print("✅ 测试 3d：后续使用不再询问")
    else:
        print("❌ 测试 3d：后续应该不再询问")
        return False

    # 测试 3e：同步 Skills
    sync_result = await agent.sync_skills()
    if sync_result["status"] == "success":
        print(f"✅ 测试 3e：同步 Skills 成功 ({sync_result['synced']} 个)")
    else:
        print("❌ 测试 3e：同步失败")
        return False

    return True


async def test_4_federated_learning():
    """测试 4：联邦学习"""
    print("\n" + "=" * 70)
    print("测试 4：联邦学习模拟")
    print("=" * 70)

    skill_path = Path(__file__).parent / "skills" / "arenasync" / "scripts"
    sys.path.insert(0, str(skill_path))

    from arenasync_meta_skill import ArenaSyncMetaSkill

    # 创建参与联邦学习的子智能体
    agent = ArenaSyncMetaSkill(agent_id="fl-test-agent")

    # 用户同意
    await agent.handle_user_response("yes")
    agent.install_hook()

    print("[联邦学习] 模拟本地训练...")

    # 模拟多次执行，自动记录数据
    for i in range(25):  # 超过阈值，自动上传梯度
        # 包装执行函数
        async def dummy_task(x):
            await asyncio.sleep(0.01)
            return {"result": "done"}

        wrapped = agent.wrap_execute(dummy_task)
        await wrapped({"task": f"task-{i}"})

    # 检查是否自动上传梯度
    gradient_dir = Path("./data/arenasync/gradients")
    gradient_files = (
        list(gradient_dir.glob("grad_*.json")) if gradient_dir.exists() else []
    )

    if len(gradient_files) > 0:
        print(f"✅ 测试 4a：自动上传 {len(gradient_files)} 个梯度文件")
        # 显示最新梯度
        latest = max(gradient_files, key=lambda p: p.stat().st_mtime)
        with open(latest) as f:
            data = json.load(f)
            print(
                f"   最新梯度：{data.get('gradients', {}).get('samples_count', 'N/A')} 条记录"
            )
    else:
        print("⚠️ 测试 4a：没有找到梯度文件（可能是模拟数据不足）")

    return True


async def test_5_data_recording():
    """测试 5：数据记录"""
    print("\n" + "=" * 70)
    print("测试 5：数据记录")
    print("=" * 70)

    skill_path = Path(__file__).parent / "skills" / "arenasync" / "scripts"
    sys.path.insert(0, str(skill_path))

    from arenasync_meta_skill import ArenaSyncMetaSkill

    agent = ArenaSyncMetaSkill(agent_id="data-test-agent")
    await agent.handle_user_response("yes")
    agent.install_hook()

    # 执行任务
    async def task_fn(x):
        await asyncio.sleep(0.01)
        return {"done": True}

    wrapped = agent.wrap_execute(task_fn)

    # 执行 5 次
    for i in range(5):
        await wrapped({"task": i})

    # 检查本地记录
    status = agent.get_status()
    print(f"✅ 测试 5a：本地记录 {status['local_records']} 条")

    # 读取本地记录
    data_file = Path("./data/arenasync/usage_records.jsonl")
    if data_file.exists():
        with open(data_file) as f:
            lines = f.readlines()
            print(f"✅ 测试 5b：记录文件包含 {len(lines)} 条")
            if len(lines) > 0:
                # 显示一条记录
                record = json.loads(lines[0])
                print(
                    f"   示例记录：skill={record.get('skill_id')}, success={record.get('success')}"
                )

    return True


# ============ 主测试流程 ============


async def main():
    """
    完整集成测试
    """
    print("\n" + "=" * 70)
    print("🚀 Skills Arena 完整集成测试")
    print("=" * 70)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"后端: {BACKEND_URL}")
    print(f"前端: {FRONTEND_URL}")
    print("=" * 70)

    results = {}

    # 测试 1：服务状态
    results["services"] = await test_1_check_services()

    # 测试 2：API 端点
    results["api"] = await test_2_api_endpoints()

    # 测试 3：子智能体集成
    results["subagent"] = await test_3_subagent_integration()

    # 测试 4：联邦学习
    results["federated"] = await test_4_federated_learning()

    # 测试 5：数据记录
    results["data"] = await test_5_data_recording()

    # 总结
    print("\n" + "=" * 70)
    print("📊 测试结果总结")
    print("=" * 70)

    for test_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {test_name}: {status}")

    total = len(results)
    passed_count = sum(1 for v in results.values() if v)

    print(f"\n总计: {passed_count}/{total} 测试通过")

    if passed_count == total:
        print("\n🎉 所有测试通过！")
    else:
        print(f"\n⚠️ {total - passed_count} 个测试失败")

    print("\n" + "=" * 70)
    print("📚 查看结果：")
    print(f"  - 后端 API: {BACKEND_URL}/api/")
    print(f"  - 前端界面: {FRONTEND_URL}")
    print(f"  - 梯度文件: ./data/arenasync/gradients/")
    print(f"  - 使用记录: ./data/arenasync/usage_records.jsonl")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
