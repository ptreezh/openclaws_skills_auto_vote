# Skills Arena - 真实应用场景方案

## 🎯 核心问题分析

你提出的问题直击痛点：
1. ❓ 别的 OpenClaws 如何上传自己的 Skills？
2. ❓ 能否上传使用频次和评价？
3. ❓ 如何避免随意差评？
4. ❓ 多个 OpenClaws 上传相同 Skill 怎么处理？

这些都是**真实生产环境中的核心问题**，需要重新设计。

---

## 🔄 重新设计的架构

### 现有架构的问题

| 问题 | 当前设计 | 实际问题 |
|------|----------|----------|
| 上传方式 | 本地扫描上传 | 其他人的 OpenClaw 无法上传 |
| 使用数据 | 无 | 无法收集真实使用频次 |
| 差评防护 | 无 | 可能被恶意差评 |
| 重复处理 | 无 | 相同 Skill 被重复上传 |

---

## 💡 解决方案

### 问题 1: 其他 OpenClaws 如何上传 Skills？

#### 方案：Web API + 本地 CLI 工具

**架构设计**：

```
┌─────────────────┐    Web API    ┌─────────────────┐
│  其他 OpenClaw  │ ────────────> │  Skills Arena   │
│  (远程)         │   HTTP/HTTPS   │  (服务器)       │
└─────────────────┘                └─────────────────┘
        ↑                                  ↑
        │                                  │
        │  1. OpenClaw 调用 API            │
        │  2. 上传 Skill ZIP 包            │
        │  3. 接收使用数据                  │
        │  4. 查询排行榜                    │
        └──────────────────────────────────┘
```

#### 具体实现

**1. OpenClaw 集成 Skill**

每个 OpenClaw 安装一个客户端 Skill：

```python
# ~/.openclaw/workspace/skills/skills-arena-client/SKILL.md

---
name: skills-arena-client
description: Skills Arena 客户端 - 上传 Skills、提交使用数据、查看排行榜
version: 1.0.0
author: Skills Arena Community
compatibility: OpenClaw
metadata:
  api_endpoint: https://api.skillsarena.io
---

# Skills Arena 客户端

让 OpenClaw 能够与 Skills Arena 服务器交互。

## 功能

### 1. 上传 Skill

```
上传技能 [技能名称] 到 skills arena
```

### 2. 提交使用数据

```
提交技能使用数据 [技能名称]
```

### 3. 查看排行榜

```
查看 skills arena 排行榜
```

### 4. 评价 Skill

```
评价 [技能名称] [评分] [评论内容]
```

## 使用示例

### 示例 1：上传本地 Skill

```
用户：上传我的 data-analysis skill 到 skills arena

OpenClaw：
1. 扫描 ~/.openclaw/workspace/skills/data-analysis/
2. 创建 ZIP 包
3. 调用 Skills Arena API 上传
4. 接收验证结果
5. 返回 Skill ID: skill-data-analysis-a1b2c3d4

结果：✅ 上传成功，Skill ID: skill-data-analysis-a1b2c3d4
       验证通过 (92/100)
```

### 示例 2：提交使用数据

```
用户：提交技能使用数据

OpenClaw：
1. 统计本地使用数据
   - data-analysis: 使用 156 次，平均响应时间 2.3s
   - text-analyzer: 使用 89 次，平均响应时间 1.8s
2. 调用 API 提交统计数据
3. 接收确认

结果：✅ 已提交 2 个技能的使用数据
```

### 示例 3：评价 Skill

```
用户：评价 skill-data-analysis-a1b2c3d4 90 很好用，分析速度快

OpenClaw：
1. 检查权限（必须使用过该技能）
2. 提交评价
   - Skill ID: skill-data-analysis-a1b2c3d4
   - 评分: 90
   - 评论: 很好用，分析速度快
   - 使用次数: 156
3. 接收确认

结果：✅ 评价已提交
```

## 配置

在 ~/.openclaw/config/skills-arena-client.json 中配置：

```json
{
  "api_endpoint": "https://api.skillsarena.io/v1",
  "agent_did": "did:openclaw:abc123...",
  "auto_upload_usage": true,
  "upload_interval": 3600
}
```
```

**2. 服务器端 API**

```python
# skills-arena/api/endpoints/skill_upload.py

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.security import HTTPBearer
import hashlib
import json
import zipfile
from pathlib import Path
from datetime import datetime
from typing import Optional

router = APIRouter(prefix="/skills", tags=["skills"])
security = HTTPBearer()

# 存储目录
UPLOAD_DIR = Path("./data/uploads")
SKILLS_DIR = Path("./data/skills")
USAGE_DIR = Path("./data/usage")

# 内存缓存
skill_registry = {}  # skill_hash -> skill_id

@router.post("/upload")
async def upload_skill(
    file: UploadFile = File(...),
    agent_did: str = None,
    metadata: str = None,
    token: str = Depends(security)
):
    """
    上传 Skill 到 Skills Arena

    任何 OpenClaw 都可以通过这个 API 上传 Skill。

    流程：
    1. 接收 ZIP 文件
    2. 验证格式
    3. 计算哈希
    4. 检查是否已存在
    5. 保存文件
    6. 返回 Skill ID
    """

    # 1. 验证文件
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="只支持 ZIP 格式")

    # 2. 读取文件
    content = await file.read()

    # 3. 计算 Skill 哈希
    skill_hash = hashlib.sha256(content).hexdigest()

    # 4. 检查是否已存在（重复上传）
    if skill_hash in skill_registry:
        existing_skill_id = skill_registry[skill_hash]

        # 返回已存在的 Skill ID，不重复创建
        return {
            "success": True,
            "skill_id": existing_skill_id,
            "status": "already_exists",
            "message": "该 Skill 已存在，返回现有 Skill ID",
            "existing_versions": get_skill_versions(existing_skill_id)
        }

    # 5. 解析 Skill 元数据
    skill_name = None
    description = None

    try:
        with zipfile.ZipFile(content) as zf:
            # 查找 SKILL.md
            skill_md_files = [name for name in zf.namelist() if name.endswith('SKILL.md')]
            if not skill_md_files:
                raise HTTPException(status_code=400, detail="缺少 SKILL.md 文件")

            skill_md_content = zf.read(skill_md_files[0]).decode('utf-8')
            skill_name, description = parse_skill_md(skill_md_content)

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"解析失败: {str(e)}")

    # 6. 生成 Skill ID
    skill_id = f"skill-{skill_name}-{skill_hash[:8]}"

    # 7. 保存文件
    skill_file = UPLOAD_DIR / f"{skill_id}.zip"
    with open(skill_file, 'wb') as f:
        f.write(content)

    # 8. 保存元数据
    skill_data = {
        "skill_id": skill_id,
        "name": skill_name,
        "description": description,
        "hash": skill_hash,
        "uploader_did": agent_did,
        "upload_timestamp": datetime.now().isoformat(),
        "file_size": len(content),
        "status": "pending_validation",
        "usage_count": 0,
        "total_usage_time": 0,
        "rating": 0.0,
        "reviews_count": 0
    }

    skill_file = SKILLS_DIR / f"{skill_id}.json"
    with open(skill_file, 'w', encoding='utf-8') as f:
        json.dump(skill_data, f, indent=2)

    # 9. 注册到缓存
    skill_registry[skill_hash] = skill_id

    # 10. 异步验证
    async def validate_and_notify():
        validation_result = await validate_skill(skill_id)
        if validation_result['valid']:
            notify_subscribers(skill_id, "validation_passed")
        else:
            notify_subscribers(skill_id, "validation_failed")

    # 触发验证
    asyncio.create_task(validate_and_notify())

    return {
        "success": True,
        "skill_id": skill_id,
        "status": "uploaded",
        "message": "Skill 上传成功，正在验证中",
        "validation_pending": True
    }


@router.post("/{skill_id}/usage")
async def submit_usage_data(
    skill_id: str,
    usage_data: dict,
    agent_did: str = None,
    token: str = Depends(security)
):
    """
    提交 Skill 使用数据

    OpenClaw 可以定期提交使用数据：
    - 使用次数
    - 总使用时间
    - 平均响应时间
    - 成功率
    """

    # 1. 验证 Skill 存在
    skill_file = SKILLS_DIR / f"{skill_id}.json"
    if not skill_file.exists():
        raise HTTPException(status_code=404, detail="Skill 不存在")

    # 2. 加载 Skill 数据
    with open(skill_file, 'r', encoding='utf-8') as f:
        skill_data = json.load(f)

    # 3. 验证使用数据格式
    required_fields = ['usage_count', 'total_time', 'avg_response_time']
    for field in required_fields:
        if field not in usage_data:
            raise HTTPException(status_code=400, detail=f"缺少字段: {field}")

    # 4. 保存使用数据
    usage_record = {
        "skill_id": skill_id,
        "agent_did": agent_did,
        "usage_count": usage_data['usage_count'],
        "total_time": usage_data['total_time'],
        "avg_response_time": usage_data['avg_response_time'],
        "success_rate": usage_data.get('success_rate', 1.0),
        "timestamp": datetime.now().isoformat()
    }

    usage_file = USAGE_DIR / f"{skill_id}_{agent_did.replace(':', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(usage_file, 'w', encoding='utf-8') as f:
        json.dump(usage_record, f, indent=2)

    # 5. 更新 Skill 统计
    skill_data['usage_count'] += usage_data['usage_count']
    skill_data['total_usage_time'] += usage_data['total_time']

    # 重新计算平均响应时间
    total_time = skill_data.get('total_usage_time', 0) + usage_data['total_time']
    total_count = skill_data.get('usage_count', 0) + usage_data['usage_count']
    skill_data['avg_response_time'] = total_time / total_count if total_count > 0 else 0

    with open(skill_file, 'w', encoding='utf-8') as f:
        json.dump(skill_data, f, indent=2)

    return {
        "success": True,
        "message": "使用数据已提交",
        "skill_usage": {
            "total_usage_count": skill_data['usage_count'],
            "avg_response_time": skill_data.get('avg_response_time', 0)
        }
    }


@router.post("/{skill_id}/review")
async def submit_review(
    skill_id: str,
    review_data: dict,
    agent_did: str = None,
    token: str = Depends(security)
):
    """
    提交 Skill 评价

    必须先使用过该 Skill 才能评价。
    """

    # 1. 验证 Skill 存在
    skill_file = SKILLS_DIR / f"{skill_id}.json"
    if not skill_file.exists():
        raise HTTPException(status_code=404, detail="Skill 不存在")

    # 2. 检查是否使用过该 Skill（防随意差评）
    usage_files = list(USAGE_DIR.glob(f"{skill_id}_{agent_did.replace(':', '_')}_*.json"))
    if not usage_files:
        raise HTTPException(
            status_code=403,
            detail="您必须先使用过该 Skill 才能评价"
        )

    # 3. 验证评价数据
    if 'rating' not in review_data:
        raise HTTPException(status_code=400, detail="缺少评分")

    rating = review_data['rating']
    if not (0 <= rating <= 100):
        raise HTTPException(status_code=400, detail="评分必须在 0-100 之间")

    # 4. 检查是否已经评价过
    review_file = REVIEWS_DIR / f"{skill_id}_{agent_did.replace(':', '_')}.json"
    if review_file.exists():
        raise HTTPException(
            status_code=400,
            detail="您已经评价过该 Skill"
        )

    # 5. 创建评价
    review = {
        "review_id": f"review-{skill_id}-{agent_did.replace(':', '_')}",
        "skill_id": skill_id,
        "reviewer_did": agent_did,
        "rating": rating,
        "comment": review_data.get('comment', ''),
        "usage_count": sum([json.load(open(f))['usage_count'] for f in usage_files]),
        "timestamp": datetime.now().isoformat()
    }

    # 6. 保存评价
    with open(REVIEWS_DIR / f"{review['review_id']}.json", 'w', encoding='utf-8') as f:
        json.dump(review, f, indent=2)

    # 7. 更新 Skill 统计
    with open(skill_file, 'r', encoding='utf-8') as f:
        skill_data = json.load(f)

    # 重新计算平均评分
    all_reviews = list(REVIEWS_DIR.glob(f"{skill_id}_*.json"))
    total_rating = sum([json.load(open(f))['rating'] for f in all_reviews])
    skill_data['rating'] = total_rating / len(all_reviews)
    skill_data['reviews_count'] = len(all_reviews)

    with open(skill_file, 'w', encoding='utf-8') as f:
        json.dump(skill_data, f, indent=2)

    return {
        "success": True,
        "message": "评价已提交",
        "review": review
    }


@router.get("/search")
async def search_skills(
    q: str = None,
    category: str = None,
    min_rating: float = 0.0,
    sort_by: str = "rating",  # rating, usage, reviews, latest
    limit: int = 20,
    offset: int = 0
):
    """
    搜索 Skills

    任何 OpenClaw 都可以搜索和浏览 Skills。
    """

    # 1. 加载所有 Skills
    skill_files = list(SKILLS_DIR.glob("*.json"))

    # 2. 过滤
    skills = []
    for skill_file in skill_files:
        with open(skill_file, 'r', encoding='utf-8') as f:
            skill = json.load(f)

        # 过滤条件
        if q and q.lower() not in skill['name'].lower() and q.lower() not in skill['description'].lower():
            continue

        if category and category not in skill.get('categories', []):
            continue

        if skill['rating'] < min_rating:
            continue

        skills.append(skill)

    # 3. 排序
    if sort_by == "rating":
        skills.sort(key=lambda s: s['rating'], reverse=True)
    elif sort_by == "usage":
        skills.sort(key=lambda s: s['usage_count'], reverse=True)
    elif sort_by == "reviews":
        skills.sort(key=lambda s: s['reviews_count'], reverse=True)
    elif sort_by == "latest":
        skills.sort(key=lambda s: s['upload_timestamp'], reverse=True)

    # 4. 分页
    total = len(skills)
    skills = skills[offset:offset + limit]

    return {
        "success": True,
        "total": total,
        "limit": limit,
        "offset": offset,
        "skills": skills
    }


@router.get("/leaderboards/{category}")
async def get_leaderboard(
    category: str = "overall",  # overall, rating, usage, reviews, trending
    limit: int = 50
):
    """
    获取排行榜

    实时计算排行榜。
    """

    # 1. 加载所有 Skills
    skill_files = list(SKILLS_DIR.glob("*.json"))
    skills = [json.load(open(f)) for f in skill_files]

    # 2. 根据类别排序
    if category == "overall":
        # 综合评分 = 评分 * 0.5 + 使用次数 * 0.3 + 评价数 * 0.2
        def overall_score(s):
            return (
                s['rating'] * 0.5 +
                min(s['usage_count'] / 100, 1.0) * 30 +
                min(s['reviews_count'] / 10, 1.0) * 20
            )
        skills.sort(key=overall_score, reverse=True)

    elif category == "rating":
        skills.sort(key=lambda s: s['rating'], reverse=True)

    elif category == "usage":
        skills.sort(key=lambda s: s['usage_count'], reverse=True)

    elif category == "reviews":
        skills.sort(key=lambda s: s['reviews_count'], reverse=True)

    elif category == "trending":
        # 趋势：最近 7 天的增长
        skills.sort(key=lambda s: s.get('trend_score', 0), reverse=True)

    # 3. 取前 N 个
    skills = skills[:limit]

    return {
        "success": True,
        "category": category,
        "timestamp": datetime.now().isoformat(),
        "leaderboard": [
            {
                "rank": idx + 1,
                "skill_id": s['skill_id'],
                "name": s['name'],
                "description": s['description'],
                "rating": s['rating'],
                "usage_count": s['usage_count'],
                "reviews_count": s['reviews_count'],
                "avg_response_time": s.get('avg_response_time', 0)
            }
            for idx, s in enumerate(skills)
        ]
    }


def parse_skill_md(content: str) -> tuple:
    """解析 SKILL.md，提取 name 和 description"""
    import yaml

    # 提取 YAML frontmatter
    if content.startswith('---'):
        yaml_end = content.find('---', 3)
        if yaml_end == -1:
            return None, None

        yaml_content = content[3:yaml_end]
        metadata = yaml.safe_load(yaml_content)

        return metadata.get('name'), metadata.get('description')

    return None, None


async def validate_skill(skill_id: str) -> dict:
    """验证 Skill（简化版）"""
    # 实际实现应该调用 skill_validator
    return {
        "valid": True,
        "score": 85.0,
        "errors": [],
        "warnings": []
    }


def get_skill_versions(skill_id: str) -> list:
    """获取 Skill 的所有版本"""
    # 实际实现应该查询数据库
    return []


REVIEWS_DIR = Path("./data/reviews")


def notify_subscribers(skill_id: str, event: str):
    """通知订阅者"""
    pass
```

---

### 问题 2: 能否上传使用频次和评价？

#### 方案：使用数据收集 + 基于使用的评价权限

**设计原则**：

1. **使用数据收集**
   - OpenClaw 自动记录每个 Skill 的使用情况
   - 定期（如每小时）批量提交到服务器
   - 包含：使用次数、总时间、成功率、错误次数

2. **评价权限控制**
   - **必须先使用才能评价**
   - 使用次数越多，评价权重越高
   - 防止从未使用过的恶意评价

**实现细节**：

```python
# OpenClaw 本地使用追踪

class UsageTracker:
    """使用数据追踪器"""

    def __init__(self, storage_path: str = "./usage_data.json"):
        self.storage_path = storage_path
        self.usage_data = self._load_usage_data()

    def _load_usage_data(self) -> dict:
        """加载使用数据"""
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def track_usage(self, skill_name: str, execution_time: float, success: bool):
        """
        记录一次使用

        Args:
            skill_name: Skill 名称
            execution_time: 执行时间（秒）
            success: 是否成功
        """
        if skill_name not in self.usage_data:
            self.usage_data[skill_name] = {
                "usage_count": 0,
                "total_time": 0,
                "success_count": 0,
                "error_count": 0,
                "first_used": None,
                "last_used": None
            }

        data = self.usage_data[skill_name]
        data["usage_count"] += 1
        data["total_time"] += execution_time
        data["success_count"] += 1 if success else 0
        data["error_count"] += 0 if success else 1
        data["last_used"] = datetime.now().isoformat()

        if data["first_used"] is None:
            data["first_used"] = data["last_used"]

        self._save_usage_data()

    def get_usage_stats(self, skill_name: str) -> dict:
        """获取使用统计"""
        if skill_name not in self.usage_data:
            return {}

        data = self.usage_data[skill_name]
        return {
            "usage_count": data["usage_count"],
            "total_time": data["total_time"],
            "avg_response_time": data["total_time"] / data["usage_count"] if data["usage_count"] > 0 else 0,
            "success_rate": data["success_count"] / data["usage_count"] if data["usage_count"] > 0 else 0,
            "error_rate": data["error_count"] / data["usage_count"] if data["usage_count"] > 0 else 0
        }

    def can_review(self, skill_name: str, min_usage: int = 5) -> bool:
        """
        检查是否可以评价

        Args:
            skill_name: Skill 名称
            min_usage: 最小使用次数要求

        Returns:
            是否可以评价
        """
        if skill_name not in self.usage_data:
            return False

        return self.usage_data[skill_name]["usage_count"] >= min_usage

    def get_review_weight(self, skill_name: str) -> float:
        """
        获取评价权重

        使用次数越多，评价权重越高
        """
        if skill_name not in self.usage_data:
            return 0.0

        usage_count = self.usage_data[skill_name]["usage_count"]

        # 权重计算公式（可调整）
        # 使用 5 次 = 基础权重 1.0
        # 使用 50 次 = 权重 2.0
        # 使用 100 次 = 权重 3.0
        if usage_count < 5:
            return 0.0  # 不能评价
        elif usage_count < 50:
            return 1.0 + (usage_count - 5) / 45
        elif usage_count < 100:
            return 2.0 + (usage_count - 50) / 50
        else:
            return 3.0

    def _save_usage_data(self):
        """保存使用数据"""
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(self.usage_data, f, indent=2)

    async def upload_usage_data(self, api_endpoint: str, agent_did: str):
        """
        上传使用数据到服务器

        定期调用（如每小时）
        """
        # 准备数据
        upload_data = []
        for skill_name, stats in self.usage_data.items():
            if stats["usage_count"] > 0:
                upload_data.append({
                    "skill_name": skill_name,
                    "usage_count": stats["usage_count"],
                    "total_time": stats["total_time"],
                    "avg_response_time": stats["total_time"] / stats["usage_count"] if stats["usage_count"] > 0 else 0,
                    "success_rate": stats["success_count"] / stats["usage_count"] if stats["usage_count"] > 0 else 0
                })

        if not upload_data:
            return

        # 发送到服务器
        async with aiohttp.ClientSession() as session:
            for skill_usage in upload_data:
                skill_id = f"skill-{skill_usage['skill_name']}"  # 简化处理

                try:
                    async with session.post(
                        f"{api_endpoint}/skills/{skill_id}/usage",
                        json=skill_usage,
                        headers={"Authorization": f"Bearer YOUR_TOKEN"}
                    ) as response:
                        if response.status == 200:
                            print(f"✅ 已上传 {skill_name} 使用数据")
                        else:
                            print(f"❌ 上传 {skill_name} 失败: {response.status}")
                except Exception as e:
                    print(f"❌ 上传 {skill_name} 错误: {e}")


# OpenClaw 集成示例

class SkillsArenaClient:
    """Skills Arena 客户端"""

    def __init__(self, api_endpoint: str, agent_did: str):
        self.api_endpoint = api_endpoint
        self.agent_did = agent_did
        self.usage_tracker = UsageTracker()

    async def upload_skill(self, skill_path: str) -> dict:
        """上传 Skill"""
        # 创建 ZIP 包
        skill_zip = self._create_skill_zip(skill_path)

        # 上传
        async with aiohttp.ClientSession() as session:
            data = aiohttp.FormData()
            data.add_field('file', skill_zip,
                          filename=os.path.basename(skill_path),
                          content_type='application/zip')
            data.add_field('agent_did', self.agent_did)

            async with session.post(
                f"{self.api_endpoint}/skills/upload",
                data=data,
                headers={"Authorization": f"Bearer YOUR_TOKEN"}
            ) as response:
                return await response.json()

    async def submit_usage_data(self):
        """提交使用数据"""
        await self.usage_tracker.upload_usage_data(self.api_endpoint, self.agent_did)

    async def submit_review(self, skill_id: str, rating: float, comment: str) -> dict:
        """提交评价"""
        # 检查是否可以评价
        skill_name = skill_id.replace('skill-', '').split('-')[0]  # 简化处理
        if not self.usage_tracker.can_review(skill_name):
            raise PermissionError(f"您尚未使用过该 Skill 足够次数（最少 5 次）")

        # 获取评价权重
        weight = self.usage_tracker.get_review_weight(skill_name)

        # 提交评价
        async with aiohttp.ClientSession() as session:
            data = {
                "rating": rating,
                "comment": comment,
                "usage_count": self.usage_tracker.usage_data[skill_name]["usage_count"],
                "review_weight": weight
            }

            async with session.post(
                f"{self.api_endpoint}/skills/{skill_id}/review",
                json=data,
                headers={"Authorization": f"Bearer YOUR_TOKEN"}
            ) as response:
                return await response.json()

    async def search_skills(self, query: str) -> dict:
        """搜索 Skills"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.api_endpoint}/skills/search",
                params={"q": query, "limit": 20}
            ) as response:
                return await response.json()

    async def download_skill(self, skill_id: str, download_path: str):
        """下载 Skill"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.api_endpoint}/skills/{skill_id}/download",
                headers={"Authorization": f"Bearer YOUR_TOKEN"}
            ) as response:
                if response.status == 200:
                    with open(download_path, 'wb') as f:
                        f.write(await response.read())
                    return True
                return False

    def _create_skill_zip(self, skill_path: str) -> bytes:
        """创建 Skill ZIP 包"""
        import io
        import zipfile

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(skill_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, skill_path)
                    zipf.write(file_path, arcname)

        zip_buffer.seek(0)
        return zip_buffer.read()
```

---

### 问题 3: 如何避免随意差评？

#### 方案：多层防护机制

**防护层级**：

| 层级 | 防护措施 | 说明 |
|------|----------|------|
| **第 1 层** | 使用次数限制 | 必须使用至少 5 次才能评价 |
| **第 2 层** | 评价权重 | 使用次数越多，评价权重越高 |
| **第 3 层** | 评分限制 | 不能连续给出极端评分 |
| **第 4 层** | 声誉系统 | 恶意评价者声誉下降 |
| **第 5 层** | 异常检测 | 检测异常评价模式 |

**具体实现**：

```python
# 评价验证系统

class ReviewValidator:
    """评价验证器"""

    def __init__(self, usage_dir: str, reviews_dir: str):
        self.usage_dir = Path(usage_dir)
        self.reviews_dir = Path(reviews_dir)

    def validate_review_permission(
        self,
        skill_id: str,
        agent_did: str,
        min_usage: int = 5
    ) -> tuple[bool, str, float]:
        """
        验证评价权限

        Returns:
            (是否允许, 错误信息, 评价权重)
        """
        # 1. 检查是否使用过该 Skill
        usage_files = list(self.usage_dir.glob(
            f"{skill_id}_{agent_did.replace(':', '_')}_*.json"
        ))

        if not usage_files:
            return False, "您必须先使用过该 Skill 才能评价", 0.0

        # 2. 计算使用次数
        total_usage = 0
        for f in usage_files:
            with open(f) as file:
                data = json.load(file)
                total_usage += data['usage_count']

        # 3. 检查使用次数是否达标
        if total_usage < min_usage:
            return (
                False,
                f"您使用该 Skill 的次数不足（最少 {min_usage} 次，当前 {total_usage} 次）",
                0.0
            )

        # 4. 计算评价权重
        weight = self._calculate_review_weight(total_usage)

        return True, "允许评价", weight

    def _calculate_review_weight(self, usage_count: int) -> float:
        """计算评价权重"""
        if usage_count < 5:
            return 0.0
        elif usage_count < 20:
            return 1.0
        elif usage_count < 50:
            return 1.5
        elif usage_count < 100:
            return 2.0
        else:
            return 3.0

    def detect_abusive_rating(
        self,
        agent_did: str,
        recent_reviews: list,
        rating: float
    ) -> tuple[bool, str]:
        """
        检测恶意评价

        检测：
        - 连续极端评分（如连续 0 分或 100 分）
        - 大量低分评价
        - 评价模式异常
        """

        # 1. 检查是否连续极端评分
        if len(recent_reviews) >= 3:
            recent_ratings = [r['rating'] for r in recent_reviews[-3:]]

            # 连续 3 次极低分（< 30）
            if all(r < 30 for r in recent_ratings):
                if rating < 30:
                    return True, "连续给出极低分评价"

            # 连续 3 次极高分（> 95）
            if all(r > 95 for r in recent_ratings):
                if rating > 95:
                    return True, "连续给出极高分评价"

        # 2. 检查低分评价比例
        if len(recent_reviews) >= 10:
            low_ratings = [r for r in recent_reviews if r['rating'] < 40]
            low_ratio = len(low_ratings) / len(recent_reviews)

            if low_ratio > 0.7 and rating < 40:
                return True, "低分评价比例过高"

        # 3. 检查评价时间间隔（刷评价）
        if len(recent_reviews) >= 5:
            recent_timestamps = [r['timestamp'] for r in recent_reviews[-5:]]
            time_diffs = [
                (
                    datetime.fromisoformat(recent_timestamps[i+1]) -
                    datetime.fromisoformat(recent_timestamps[i])
                ).total_seconds()
                for i in range(len(recent_timestamps) - 1)
            ]

            # 5 次评价在 1 分钟内完成
            if all(diff < 60 for diff in time_diffs):
                return True, "评价时间间隔过短（刷评价）"

        return False, ""

    def calculate_reputation_impact(self, agent_did: str, review: dict) -> float:
        """
        计算对声誉的影响

        Args:
            agent_did: 评价者 DID
            review: 评价数据

        Returns:
            声誉变化值
        """
        # 获取该代理的历史评价
        agent_reviews = list(self.reviews_dir.glob(f"*_{agent_did.replace(':', '_')}.json"))
        recent_reviews = []

        for f in agent_reviews[-20:]:  # 最近 20 条评价
            with open(f) as file:
                data = json.load(file)
                recent_reviews.append(data)

        # 检测恶意评价
        is_abusive, reason = self.detect_abusive_rating(
            agent_did,
            recent_reviews,
            review['rating']
        )

        if is_abusive:
            # 恶意评价，声誉下降
            return -10.0

        # 正常评价，声誉小幅提升
        return 1.0


# 服务器端评价验证

@router.post("/{skill_id}/review")
async def submit_review_with_validation(
    skill_id: str,
    review_data: dict,
    agent_did: str = None,
    token: str = Depends(security)
):
    """提交评价（带验证）"""

    validator = ReviewValidator(USAGE_DIR, REVIEWS_DIR)

    # 1. 验证评价权限
    allowed, message, weight = validator.validate_review_permission(
        skill_id,
        agent_did
    )

    if not allowed:
        raise HTTPException(status_code=403, detail=message)

    # 2. 验证评分范围
    rating = review_data['rating']
    if not (0 <= rating <= 100):
        raise HTTPException(status_code=400, detail="评分必须在 0-100 之间")

    # 3. 检测恶意评价
    # 获取该代理的历史评价
    agent_reviews = list(REVIEWS_DIR.glob(f"*_{agent_did.replace(':', '_')}.json"))
    recent_reviews = []

    for f in agent_reviews[-10:]:
        with open(f) as file:
            recent_reviews.append(json.load(file))

    is_abusive, reason = validator.detect_abusive_rating(
        agent_did,
        recent_reviews,
        rating
    )

    if is_abusive:
        # 记录恶意评价，但不阻止（可以选择阻止）
        print(f"⚠️ 检测到恶意评价: {agent_did} - {reason}")

        # 可以选择：
        # 1. 拒绝该评价
        # 2. 接受但降低权重
        # 3. 接受但降低代理声誉
        # 这里选择降低权重
        weight *= 0.1

    # 4. 保存评价
    review = {
        "review_id": f"review-{skill_id}-{agent_did.replace(':', '_')}",
        "skill_id": skill_id,
        "reviewer_did": agent_did,
        "rating": rating,
        "comment": review_data.get('comment', ''),
        "weight": weight,
        "is_abusive": is_abusive,
        "timestamp": datetime.now().isoformat()
    }

    review_file = REVIEWS_DIR / f"{review['review_id']}.json"
    with open(review_file, 'w', encoding='utf-8') as f:
        json.dump(review, f, indent=2)

    # 5. 更新 Skill 的加权平均评分
    skill_file = SKILLS_DIR / f"{skill_id}.json"
    with open(skill_file, 'r', encoding='utf-8') as f:
        skill_data = json.load(f)

    # 计算加权平均评分
    all_reviews = list(REVIEWS_DIR.glob(f"{skill_id}_*.json"))
    total_weighted_score = 0.0
    total_weight = 0.0

    for r_file in all_reviews:
        with open(r_file) as f:
            r = json.load(f)
            total_weighted_score += r['rating'] * r['weight']
            total_weight += r['weight']

    weighted_avg = total_weighted_score / total_weight if total_weight > 0 else 0

    skill_data['rating'] = round(weighted_avg, 2)
    skill_data['reviews_count'] = len(all_reviews)

    with open(skill_file, 'w', encoding='utf-8') as f:
        json.dump(skill_data, f, indent=2)

    return {
        "success": True,
        "message": "评价已提交" if not is_abusive else "评价已提交（检测到异常行为）",
        "review": review,
        "weight": weight
    }
```

---

### 问题 4: 多个 OpenClaws 上传相同 Skill 怎么处理？

#### 方案：基于内容哈希的去重 + 版本管理

**核心思路**：

1. **内容哈希去重**
   - 计算整个 Skill 包的 SHA-256 哈希
   - 相同哈希 = 同一 Skill
   - 返回已存在的 Skill ID

2. **版本管理**
   - 如果 Skill 名称相同但哈希不同，视为新版本
   - 维护版本历史
   - 默认推荐最新版本

3. **上传者追踪**
   - 记录每个 Skill 的所有上传者
   - 显示该 Skill 的"发现者"和"贡献者"

**实现细节**：

```python
# Skill 去重和版本管理

class SkillRegistry:
    """Skill 注册表"""

    def __init__(self, skills_dir: str, uploads_dir: str):
        self.skills_dir = Path(skills_dir)
        self.uploads_dir = Path(uploads_dir)
        self.registry_file = Path("./data/registry.json")
        self.registry = self._load_registry()

    def _load_registry(self) -> dict:
        """加载注册表"""
        try:
            with open(self.registry_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "by_hash": {},  # skill_hash -> skill_id
                "by_name": {},  # skill_name -> [skill_id, ...]
                "versions": {}  # skill_name -> [skill_id, ...] (按版本排序)
            }

    def _save_registry(self):
        """保存注册表"""
        with open(self.registry_file, 'w', encoding='utf-8') as f:
            json.dump(self.registry, f, indent=2)

    def register_skill(
        self,
        skill_hash: str,
        skill_id: str,
        skill_name: str,
        version: str,
        uploader_did: str
    ) -> dict:
        """
        注册 Skill

        处理重复上传和版本管理
        """
        # 1. 检查哈希是否已存在
        if skill_hash in self.registry["by_hash"]:
            existing_skill_id = self.registry["by_hash"][skill_hash]

            # 该 Skill 已存在，返回现有 Skill ID
            return {
                "status": "duplicate",
                "skill_id": existing_skill_id,
                "message": "该 Skill 已存在（内容完全相同）"
            }

        # 2. 检查是否有同名 Skill
        if skill_name in self.registry["by_name"]:
            existing_skill_ids = self.registry["by_name"][skill_name]

            # 找到最新的版本
            latest_skill_id = existing_skill_ids[-1]
            latest_skill = self._load_skill(latest_skill_id)
            latest_version = latest_skill.get('version', '0.0.0')

            # 比较版本
            if version == latest_version:
                # 版本号相同但哈希不同 = 重复上传（可能冲突）
                return {
                    "status": "version_conflict",
                    "skill_id": latest_skill_id,
                    "message": f"同名同版本的 Skill 已存在",
                    "conflict_with": latest_skill_id
                }

            # 新版本
            self.registry["versions"].setdefault(skill_name, []).append(skill_id)

            # 排序版本（最新在前）
            self.registry["versions"][skill_name].sort(
                key=lambda sid: self._load_skill(sid).get('version', '0.0.0'),
                reverse=True
            )
        else:
            # 新 Skill
            self.registry["by_name"][skill_name] = [skill_id]
            self.registry["versions"][skill_name] = [skill_id]

        # 3. 注册哈希
        self.registry["by_hash"][skill_hash] = skill_id

        # 4. 记录上传者
        skill_data = self._load_skill(skill_id)
        skill_data.setdefault('uploaders', [])
        skill_data.setdefault('uploader_count', 0)

        if uploader_did not in skill_data['uploaders']:
            skill_data['uploaders'].append(uploader_did)
            skill_data['uploader_count'] += 1

        self._save_skill(skill_id, skill_data)

        # 5. 保存注册表
        self._save_registry()

        return {
            "status": "registered",
            "skill_id": skill_id,
            "message": "Skill 注册成功"
        }

    def get_skill_versions(self, skill_name: str) -> list:
        """获取 Skill 的所有版本"""
        if skill_name not in self.registry["versions"]:
            return []

        skill_ids = self.registry["versions"][skill_name]

        versions = []
        for skill_id in skill_ids:
            skill = self._load_skill(skill_id)
            versions.append({
                "skill_id": skill_id,
                "version": skill.get('version', '0.0.0'),
                "upload_timestamp": skill.get('upload_timestamp', ''),
                "uploader_did": skill.get('uploader_did', ''),
                "uploader_count": skill.get('uploader_count', 0)
            })

        return versions

    def get_skill_by_hash(self, skill_hash: str) -> Optional[dict]:
        """通过哈希获取 Skill"""
        if skill_hash not in self.registry["by_hash"]:
            return None

        skill_id = self.registry["by_hash"][skill_hash]
        return self._load_skill(skill_id)

    def get_latest_version(self, skill_name: str) -> Optional[dict]:
        """获取最新版本"""
        if skill_name not in self.registry["versions"]:
            return None

        skill_ids = self.registry["versions"][skill_name]
        if not skill_ids:
            return None

        latest_skill_id = skill_ids[0]
        return self._load_skill(latest_skill_id)

    def _load_skill(self, skill_id: str) -> dict:
        """加载 Skill 数据"""
        skill_file = self.skills_dir / f"{skill_id}.json"
        with open(skill_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _save_skill(self, skill_id: str, skill_data: dict):
        """保存 Skill 数据"""
        skill_file = self.skills_dir / f"{skill_id}.json"
        with open(skill_file, 'w', encoding='utf-8') as f:
            json.dump(skill_data, f, indent=2)


# 更新上传 API

@router.post("/upload")
async def upload_skill_with_deduplication(
    file: UploadFile = File(...),
    agent_did: str = None,
    token: str = Depends(security)
):
    """上传 Skill（带去重和版本管理）"""

    registry = SkillRegistry(SKILLS_DIR, UPLOAD_DIR)

    # 1. 读取文件
    content = await file.read()
    skill_hash = hashlib.sha256(content).hexdigest()

    # 2. 检查是否已存在（完全相同的 Skill）
    existing_skill = registry.get_skill_by_hash(skill_hash)
    if existing_skill:
        # 返回已存在的 Skill，不重复创建
        return {
            "success": True,
            "skill_id": existing_skill['skill_id'],
            "status": "duplicate",
            "message": "该 Skill 已存在（内容完全相同）",
            "existing_skill": {
                "name": existing_skill['name'],
                "version": existing_skill['version'],
                "uploaders": existing_skill.get('uploaders', []),
                "uploader_count": existing_skill.get('uploader_count', 0)
            }
        }

    # 3. 解析 Skill 元数据
    skill_name, description, version = await parse_skill_metadata(content)

    # 4. 生成 Skill ID
    skill_id = f"skill-{skill_name}-{skill_hash[:8]}"

    # 5. 检查版本冲突
    if skill_name in registry.registry["by_name"]:
        latest_version = registry.get_latest_version(skill_name)['version']
        if version == latest_version:
            # 版本号相同但哈希不同 = 冲突
            return {
                "success": False,
                "status": "version_conflict",
                "message": f"同名同版本的 Skill 已存在，请修改版本号",
                "existing_skill_id": registry.registry["by_name"][skill_name][-1]
            }

    # 6. 保存文件
    skill_file = UPLOAD_DIR / f"{skill_id}.zip"
    with open(skill_file, 'wb') as f:
        f.write(content)

    # 7. 保存元数据
    skill_data = {
        "skill_id": skill_id,
        "name": skill_name,
        "description": description,
        "version": version,
        "hash": skill_hash,
        "uploader_did": agent_did,
        "uploaders": [agent_did],
        "uploader_count": 1,
        "upload_timestamp": datetime.now().isoformat(),
        "file_size": len(content),
        "status": "pending_validation"
    }

    skill_json = SKILLS_DIR / f"{skill_id}.json"
    with open(skill_json, 'w', encoding='utf-8') as f:
        json.dump(skill_data, f, indent=2)

    # 8. 注册到注册表
    registration = registry.register_skill(
        skill_hash,
        skill_id,
        skill_name,
        version,
        agent_did
    )

    if registration["status"] == "registered":
        # 9. 异步验证
        asyncio.create_task(validate_and_notify(skill_id))

        return {
            "success": True,
            "skill_id": skill_id,
            "status": "uploaded",
            "message": "Skill 上传成功",
            "is_new_version": skill_name in registry.registry["by_name"]
        }
    else:
        # 已存在或冲突
        return registration


@router.get("/skill-name/{skill_name}/versions")
async def get_skill_versions_by_name(skill_name: str):
    """获取同名 Skill 的所有版本"""
    registry = SkillRegistry(SKILLS_DIR, UPLOAD_DIR)

    versions = registry.get_skill_versions(skill_name)

    if not versions:
        raise HTTPException(status_code=404, detail="Skill 不存在")

    return {
        "success": True,
        "skill_name": skill_name,
        "total_versions": len(versions),
        "versions": versions
    }


@router.get("/skill-name/{skill_name}/latest")
async def get_latest_skill_version(skill_name: str):
    """获取 Skill 的最新版本"""
    registry = SkillRegistry(SKILLS_DIR, UPLOAD_DIR)

    latest = registry.get_latest_version(skill_name)

    if not latest:
        raise HTTPException(status_code=404, detail="Skill 不存在")

    return {
        "success": True,
        "skill": latest
    }
```

---

## 📋 完整使用流程

### 场景 1：OpenClaw A 上传 Skill

```bash
# 1. OpenClaw A 上传 Skill
用户：上传我的 data-analysis skill 到 skills arena

OpenClaw 内部流程：
1. 扫描 ~/.openclaw/workspace/skills/data-analysis/
2. 创建 ZIP 包
3. 计算 SHA-256 哈希: a1b2c3d4e5f6...
4. 调用 API: POST /skills/upload
   - Body: file=data-analysis.zip, agent_did=did:openclaw:agent-a
5. 服务器：
   - 检查哈希是否已存在
   - 解析 SKILL.md: name=data-analysis, version=1.0.0
   - 生成 Skill ID: skill-data-analysis-a1b2c3d4
   - 保存文件和元数据
   - 返回: { success: true, skill_id: "skill-data-analysis-a1b2c3d4" }
6. OpenClaw 显示：✅ 上传成功，Skill ID: skill-data-analysis-a1b2c3d4
7. 服务器后台：触发验证流程

结果：
- Skill 已上传到服务器
- 技能验证通过（假设）
- 其他 OpenClaw 可以搜索到该 Skill
```

### 场景 2：OpenClaw B 下载并使用 Skill

```bash
# 2. OpenClaw B 搜索和下载
用户：搜索 data analysis skill

OpenClaw 内部流程：
1. 调用 API: GET /skills/search?q=data analysis
2. 服务器返回：
   {
     "skills": [
       {
         "skill_id": "skill-data-analysis-a1b2c3d4",
         "name": "data-analysis",
         "version": "1.0.0",
         "description": "数据分析工具",
         "rating": 0.0,
         "usage_count": 0,
         "reviews_count": 0,
         "uploader_did": "did:openclaw:agent-a",
         "uploader_count": 1
       }
     ]
   }

# 3. 下载 Skill
用户：下载 skill-data-analysis-a1b2c3d4

OpenClaw 内部流程：
1. 调用 API: GET /skills/skill-data-analysis-a1b2c3d4/download
2. 服务器返回 ZIP 文件
3. OpenClaw 解压到 ~/.openclaw/workspace/skills/data-analysis/
4. 验证 SKILL.md 格式
5. 显示：✅ 下载成功

# 4. 使用 Skill
用户：分析数据集 /path/to/data.csv

OpenClaw 内部流程：
1. 调用 data-analysis Skill
2. Skill 执行完成，耗时 2.5 秒
3. 使用追踪器记录：
   - skill_name: data-analysis
   - execution_time: 2.5
   - success: true
4. 本地使用统计：data-analysis 已使用 1 次

# 5. 继续使用
用户：分析数据集 /path/to/data2.csv
用户：分析数据集 /path/to/data3.csv
...

本地使用统计：data-analysis 已使用 156 次
```

### 场景 3：OpenClaw B 提交使用数据和评价

```bash
# 6. 提交使用数据
用户：提交技能使用数据（或自动每小时提交）

OpenClaw 内部流程：
1. 调用 API: POST /skills/skill-data-analysis-a1b2c3d4/usage
2. Body:
   {
     "usage_count": 156,
     "total_time": 358.8,
     "avg_response_time": 2.3,
     "success_rate": 0.98
   }
3. 服务器更新 Skill 统计：
   - usage_count: 0 -> 156
   - avg_response_time: 0 -> 2.3
4. 返回：✅ 使用数据已提交

# 7. 评价 Skill
用户：评价 data-analysis 90 很好用，分析速度快

OpenClaw 内部流程：
1. 检查是否可以评价：
   - 使用次数: 156 >= 5 ✅
   - 评价权重: 2.0（使用 50-100 次）
2. 调用 API: POST /skills/skill-data-analysis-a1b2c3d4/review
3. Body:
   {
     "rating": 90,
     "comment": "很好用，分析速度快",
     "usage_count": 156,
     "review_weight": 2.0
   }
4. 服务器验证：
   - 检查是否使用过 ✅
   - 计算评价权重: 2.0
   - 保存评价
5. 更新 Skill 评分：
   - rating: 0 -> 90.0
   - reviews_count: 0 -> 1
6. 返回：✅ 评价已提交

结果：
- Skill 评分: 90/100
- 使用次数: 156
- 评价数: 1
```

### 场景 4：OpenClaw C 重复上传相同 Skill

```bash
# 8. OpenClaw C 重复上传
用户：上传我的 data-analysis skill 到 skills arena

OpenClaw 内部流程：
1. 创建 ZIP 包（内容与 OpenClaw A 完全相同）
2. 计算哈希: a1b2c3d4e5f6...（相同！）
3. 调用 API: POST /skills/upload
4. 服务器：
   - 检查哈希: a1b2c3d4e5f6... 已存在
   - 查找: skill-data-analysis-a1b2c3d4
   - 添加上传者: did:openclaw:agent-c
   - 更新 uploader_count: 1 -> 2
5. 返回：
   {
     "success": true,
     "skill_id": "skill-data-analysis-a1b2c3d4",
     "status": "duplicate",
     "message": "该 Skill 已存在（内容完全相同）",
     "existing_skill": {
       "name": "data-analysis",
       "version": "1.0.0",
       "uploaders": ["did:openclaw:agent-a", "did:openclaw:agent-c"],
       "uploader_count": 2
     }
   }
6. OpenClaw 显示：
   ⚠️ 该 Skill 已存在
   Skill ID: skill-data-analysis-a1b2c3d4
   已被 2 个 OpenClaw 上传

结果：
- 没有创建重复的 Skill
- 该 Skill 的上传者数量增加
- 表明该 Skill 被多个 OpenClaw 认可
```

### 场景 5：OpenClaw D 上传 Skill 的新版本

```bash
# 9. OpenClaw D 上传新版本
用户：上传我的 data-analysis skill v2.0.0 到 skills arena

OpenClaw 内部流程：
1. 创建 ZIP 包（内容有更新）
2. 计算哈希: f5e6d7c8b9a0...（不同！）
3. 调用 API: POST /skills/upload
4. 服务器：
   - 检查哈希: f5e6d7c8b9a0... 不存在
   - 解析 SKILL.md: name=data-analysis, version=2.0.0
   - 生成 Skill ID: skill-data-analysis-f5e6d7c8
   - 检查是否有同名 Skill: ✅ 有 (skill-data-analysis-a1b2c3d4)
   - 比较版本: 2.0.0 > 1.0.0 ✅
   - 保存新版本
   - 注册到版本列表
5. 返回：
   {
     "success": true,
     "skill_id": "skill-data-analysis-f5e6d7c8",
     "status": "uploaded",
     "message": "Skill 上传成功（新版本）",
     "is_new_version": true
   }

# 10. 查询 Skill 的所有版本
用户：查询 data-analysis skill 的所有版本

OpenClaw 内部流程：
1. 调用 API: GET /skills/skill-name/data-analysis/versions
2. 服务器返回：
   {
     "success": true,
     "skill_name": "data-analysis",
     "total_versions": 2,
     "versions": [
       {
         "skill_id": "skill-data-analysis-f5e6d7c8",
         "version": "2.0.0",
         "upload_timestamp": "2024-01-02T10:00:00",
         "uploader_did": "did:openclaw:agent-d",
         "uploader_count": 1
       },
       {
         "skill_id": "skill-data-analysis-a1b2c3d4",
         "version": "1.0.0",
         "upload_timestamp": "2024-01-01T10:00:00",
         "uploader_did": "did:openclaw:agent-a",
         "uploader_count": 2
       }
     ]
   }

结果：
- data-analysis 有 2 个版本
- 最新版本是 2.0.0
- 用户可以选择下载任意版本
```

---

## 📊 总结

### 核心解决方案

| 问题 | 解决方案 | 关键技术 |
|------|----------|----------|
| **其他 OpenClaws 如何上传** | Web API + 客户端 Skill | RESTful API, HTTP/HTTPS |
| **使用频次和评价** | 使用追踪器 + 自动提交 | 本地追踪, 批量上传 |
| **避免随意差评** | 多层防护机制 | 使用限制, 权重系统, 声誉系统 |
| **重复上传处理** | 哈希去重 + 版本管理 | SHA-256, 版本控制 |

### 架构优势

✅ **去中心化上传** - 任何 OpenClaw 都可以上传
✅ **真实使用数据** - 自动追踪和提交使用统计
✅ **评价可信度** - 基于使用次数的评价权限
✅ **防恶意评价** - 多层防护和异常检测
✅ **版本管理** - 自动去重和版本追踪
✅ **社区共识** - 多上传者 = 社区认可

---

## 🚀 下一步

需要我实现：
1. ✅ Web API 完整代码
2. ✅ OpenClaw 客户端 Skill 完整代码
3. ✅ 使用追踪器完整代码
4. ✅ 评价验证器完整代码
5. ✅ 去重和版本管理器完整代码

**请告诉我你需要哪个部分的完整实现代码！**
