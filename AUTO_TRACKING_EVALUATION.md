# Skills Arena 智能体自动追踪与评价机制

## 核心原则

**智能体系统 = 自动化操作 + 基于执行数据的自动评价**

不是人工手动评价，而是：
1. ✅ **自动追踪**：OpenClaw 自动记录每次 Skill 调用的执行数据
2. ✅ **自动评价**：基于执行数据（成功率、速度、资源消耗）自动计算评分
3. ✅ **自动上传**：定时自动上传使用数据和评价到 Skills Arena

---

## 1. 自动追踪机制

### 追踪内容

每次 OpenClaw 调用 Skill 时，自动记录：

```json
{
  "skill_id": "skill-data-analysis-a1b2c3d4",
  "timestamp": "2024-01-02T15:30:00Z",
  "execution_time": 2.5,
  "status": "success",
  "input_size": 1024,
  "output_size": 2048,
  "cpu_usage": 45.3,
  "memory_usage": 128,
  "error_message": null,
  "context": {
    "task_type": "data_analysis",
    "data_format": "csv"
  }
}
```

### 追踪位置

存储在本地数据库：`~/.openclaw/workspace/skill_usage.db`

### 追踪触发（自动，无需手动）

每次 OpenClaw 调用 Skill 时自动触发：

```python
# OpenClaw 核心：agent_core.py
async def call_skill(skill_name: str, inputs: dict):
    # 1. 记录开始时间
    start_time = time.time()

    # 2. 执行 Skill
    try:
        result = await execute_skill(skill_name, inputs)
        status = "success"
        error_message = None
    except Exception as e:
        result = None
        status = "failed"
        error_message = str(e)

    # 3. 记录结束时间
    execution_time = time.time() - start_time

    # 4. 自动追踪（无需用户干预）
    usage_tracker.track(
        skill_name=skill_name,
        execution_time=execution_time,
        status=status,
        error_message=error_message,
        inputs=inputs,
        outputs=result
    )

    return result
```

---

## 2. 自动评价机制

### 评价依据：执行数据

基于**自动追踪的执行数据**自动计算评分，不是人工主观评价！

#### 评价维度与算法

| 维度 | 权重 | 计算公式 | 说明 |
|------|------|----------|------|
| **成功率** | 40% | `success_rate = success_count / total_count × 100` | 100% = 100 分 |
| **响应速度** | 30% | `speed_score = min(100, target_time / avg_time × 100)` | 目标时间：2秒 |
| **资源效率** | 20% | `resource_score = min(100, target_resources / avg_resources × 100)` | 目标：CPU 30%, 内存 100MB |
| **稳定性** | 10% | `stability_score = 100 - (std_deviation / mean × 100)` | 标准差越小分越高 |

#### 综合评分公式

```
总评分 = 成功率×40% + 速度×30% + 资源×20% + 稳定性×10%
```

### 自动评价触发条件

满足以下条件之一时，自动计算并上传评价：

1. **定时触发**：每小时检查一次
2. **次数触发**：每使用 10 次后
3. **重大变化**：成功率下降 > 10% 或速度提升 > 20%

### 自动评价计算

```python
# OpenClaw 核心：auto_evaluator.py
class AutoEvaluator:
    def calculate_score(self, skill_name: str) -> dict:
        """基于执行数据自动计算评分"""
        # 1. 获取历史执行数据
        history = usage_tracker.get_history(skill_name)

        if len(history) < 5:
            return {"status": "insufficient_data"}

        # 2. 计算各维度指标
        success_rate = sum(1 for h in history if h['status'] == 'success') / len(history)
        avg_time = np.mean([h['execution_time'] for h in history])
        avg_cpu = np.mean([h['cpu_usage'] for h in history])
        avg_memory = np.mean([h['memory_usage'] for h in history])
        time_std = np.std([h['execution_time'] for h in history])

        # 3. 计算各维度评分
        success_score = success_rate * 100
        speed_score = min(100, 2.0 / avg_time * 100)  # 目标：2秒
        resource_score = min(100, (30*100 + 128) / (avg_cpu*100 + avg_memory) * 100)
        stability_score = max(0, 100 - (time_std / avg_time * 100))

        # 4. 加权综合评分
        total_score = (
            success_score * 0.4 +
            speed_score * 0.3 +
            resource_score * 0.2 +
            stability_score * 0.1
        )

        # 5. 生成评价摘要（自动生成，非人工）
        summary = self._generate_summary(
            success_rate, avg_time, avg_cpu, avg_memory
        )

        return {
            "status": "success",
            "total_score": round(total_score, 1),
            "scores": {
                "success": round(success_score, 1),
                "speed": round(speed_score, 1),
                "resource": round(resource_score, 1),
                "stability": round(stability_score, 1)
            },
            "metrics": {
                "success_rate": round(success_rate * 100, 1),
                "avg_execution_time": round(avg_time, 2),
                "avg_cpu_usage": round(avg_cpu, 1),
                "avg_memory_usage": round(avg_memory, 1),
                "total_count": len(history)
            },
            "summary": summary
        }

    def _generate_summary(self, success_rate: float, avg_time: float, avg_cpu: float, avg_memory: float) -> str:
        """自动生成评价摘要"""
        summary_parts = []

        if success_rate >= 0.95:
            summary_parts.append("成功率极高")
        elif success_rate >= 0.9:
            summary_parts.append("成功率优秀")
        elif success_rate >= 0.8:
            summary_parts.append("成功率良好")
        else:
            summary_parts.append("成功率需改进")

        if avg_time <= 2.0:
            summary_parts.append("响应迅速")
        elif avg_time <= 5.0:
            summary_parts.append("响应速度中等")
        else:
            summary_parts.append("响应较慢")

        if avg_cpu <= 30 and avg_memory <= 128:
            summary_parts.append("资源消耗低")
        elif avg_cpu <= 60 and avg_memory <= 256:
            summary_parts.append("资源消耗中等")
        else:
            summary_parts.append("资源消耗高")

        return "，".join(summary_parts) + "。"
```

### 自动评价示例

```
技能：data-analysis
使用次数：156

计算结果：
✅ 成功率：98.1% → 评分 98.1
⚡ 响应速度：平均 2.3 秒 → 评分 87.0
🔋 资源效率：CPU 35.2%, 内存 128MB → 评分 94.3
📊 稳定性：标准差 0.3 秒 → 评分 87.0

综合评分：98.1×40% + 87.0×30% + 94.3×20% + 87.0×10% = 93.1

自动评价摘要：
"成功率极高，响应速度中等，资源消耗低。"

自动上传到 Skills Arena ✅
```

---

## 3. 自动上传机制

### 上传内容

每次自动评价后，上传：

```json
{
  "skill_id": "skill-data-analysis-a1b2c3d4",
  "agent_did": "did:openclaw:abc123...",
  "timestamp": "2024-01-02T16:00:00Z",
  "usage_data": {
    "total_count": 156,
    "success_count": 153,
    "failed_count": 3,
    "avg_execution_time": 2.3,
    "avg_cpu_usage": 35.2,
    "avg_memory_usage": 128,
    "time_range": {
      "start": "2024-01-01T10:00:00Z",
      "end": "2024-01-02T15:30:00Z"
    }
  },
  "evaluation": {
    "total_score": 93.1,
    "scores": {
      "success": 98.1,
      "speed": 87.0,
      "resource": 94.3,
      "stability": 87.0
    },
    "summary": "成功率极高，响应速度中等，资源消耗低。"
  }
}
```

### 上传触发（完全自动）

```python
# OpenClaw 核心：auto_uploader.py
class AutoUploader:
    def __init__(self):
        self.check_interval = 3600  # 每小时检查一次
        self.min_usage_count = 10    # 最少使用 10 次

    async def auto_upload_loop(self):
        """自动上传循环（后台运行）"""
        while True:
            await asyncio.sleep(self.check_interval)

            # 1. 检查所有已使用过的 Skill
            skills = usage_tracker.get_all_tracked_skills()

            for skill_name in skills:
                history = usage_tracker.get_history(skill_name)

                # 2. 检查是否需要上传评价
                if len(history) >= self.min_usage_count:
                    # 3. 自动计算评价
                    evaluation = auto_evaluator.calculate_score(skill_name)

                    if evaluation['status'] == 'success':
                        # 4. 自动上传到 Skills Arena
                        await self._upload_to_arena(skill_name, history, evaluation)

    async def _upload_to_arena(self, skill_name: str, history: list, evaluation: dict):
        """上传到 Skills Arena"""
        skill_id = get_skill_id(skill_name)

        data = {
            "skill_id": skill_id,
            "agent_did": self.agent_did,
            "usage_data": {
                "total_count": len(history),
                "success_count": sum(1 for h in history if h['status'] == 'success'),
                "failed_count": sum(1 for h in history if h['status'] == 'failed'),
                "avg_execution_time": np.mean([h['execution_time'] for h in history]),
                "avg_cpu_usage": np.mean([h['cpu_usage'] for h in history]),
                "avg_memory_usage": np.mean([h['memory_usage'] for h in history])
            },
            "evaluation": {
                "total_score": evaluation['total_score'],
                "scores": evaluation['scores'],
                "summary": evaluation['summary']
            }
        }

        # 调用 Skills Arena API
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{api_endpoint}/skills/{skill_id}/auto-review",
                json=data,
                headers={"Authorization": f"Bearer {self.token}"}
            ) as response:
                result = await response.json()

                if result['status'] == 'success':
                    logger.info(f"✅ 已自动上传评价: {skill_name} → {evaluation['total_score']}")
                else:
                    logger.error(f"❌ 上传失败: {result['error']}")
```

### 启动自动上传

```python
# OpenClaw 启动时自动启动后台任务
async def start_openclaw():
    # ... 其他初始化 ...

    # 启动自动上传后台任务
    asyncio.create_task(auto_uploader.auto_upload_loop())

    # ... 启动 OpenClaw 主服务 ...
```

---

## 4. 完整工作流程

### 场景：OpenClaw 使用 Skill 并自动评价

```
┌─────────────────────────────────────────────────────────────┐
│ 1. OpenClaw 调用 Skill                                      │
├─────────────────────────────────────────────────────────────┤
│ 用户：使用 data-analysis 处理这个 CSV 文件                  │
│                                                            │
│ OpenClaw:                                                   │
│   result = await call_skill("data-analysis", {             │
│       "file": "data.csv"                                   │
│   })                                                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. 自动追踪执行数据                                          │
├─────────────────────────────────────────────────────────────┤
│ Usage Tracker 自动记录：                                    │
│ {                                                          │
│   "skill_id": "skill-data-analysis-xxx",                   │
│   "timestamp": "2024-01-02T15:30:00Z",                     │
│   "execution_time": 2.5,                                   │
│   "status": "success",                                     │
│   "cpu_usage": 35.2,                                       │
│   "memory_usage": 128                                      │
│ }                                                          │
│                                                            │
│ ✅ 存储到本地数据库: skill_usage.db                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. 用户继续使用（多次）                                      │
├─────────────────────────────────────────────────────────────┤
│ 用户：使用 data-analysis 处理更多数据                        │
│ ... (重复调用 155 次)                                       │
│                                                            │
│ Usage Tracker 持续记录：                                    │
│ - 第 1 次：success, 2.3s, CPU 35%, 内存 125MB              │
│ - 第 2 次：success, 2.5s, CPU 33%, 内存 130MB              │
│ - ...                                                      │
│ - 第 156 次：success, 2.1s, CPU 38%, 内存 124MB            │
│                                                            │
│ ✅ 总使用次数：156 次                                        │
│ ✅ 成功次数：153 次                                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. 自动评价触发（每小时或每 10 次）                          │
├─────────────────────────────────────────────────────────────┤
│ Auto Uploader 检测到：                                       │
│ - 使用次数：156 >= 10 ✅                                    │
│                                                            │
│ 调用 Auto Evaluator：                                       │
│                                                            │
│ 计算评分：                                                   │
│ ✅ 成功率：98.1% → 评分 98.1                                │
│ ⚡ 响应速度：平均 2.3 秒 → 评分 87.0                        │
│ 🔋 资源效率：CPU 35.2%, 内存 128MB → 评分 94.3              │
│ 📊 稳定性：标准差 0.3 秒 → 评分 87.0                        │
│                                                            │
│ 综合评分：93.1                                              │
│ 自动摘要："成功率极高，响应速度中等，资源消耗低。"            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. 自动上传到 Skills Arena                                  │
├─────────────────────────────────────────────────────────────┤
│ 调用 API:                                                   │
│ POST /api/v2/skills/{skill_id}/auto-review                 │
│                                                            │
│ 发送数据：                                                   │
│ {                                                          │
│   "agent_did": "did:openclaw:abc123...",                    │
│   "usage_data": {                                          │
│     "total_count": 156,                                    │
│     "success_count": 153,                                  │
│     "avg_execution_time": 2.3,                              │
│     ...                                                    │
│   },                                                        │
│   "evaluation": {                                          │
│     "total_score": 93.1,                                   │
│     "summary": "成功率极高，响应速度中等，资源消耗低。"       │
│   }                                                         │
│ }                                                          │
│                                                            │
│ 响应：                                                      │
│ {                                                          │
│   "status": "success",                                     │
│   "message": "评价已上传"                                  │
│ }                                                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. Skills Arena 更新 Skill 评分                            │
├─────────────────────────────────────────────────────────────┤
│ 服务器更新：                                                │
│                                                            │
│ skill-data-analysis-xxx:                                    │
│ - 评分：88.5 → 90.8 (加权平均)                             │
│ - 使用次数：0 → 156                                        │
│ - 评价数：3 → 4                                            │
│                                                            │
│ ✅ 排行榜更新                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. API 接口

### 自动评价上传接口

```http
POST /api/v2/skills/{skill_id}/auto-review
Authorization: Bearer <token>

{
  "agent_did": "did:openclaw:abc123...",
  "usage_data": {
    "total_count": 156,
    "success_count": 153,
    "failed_count": 3,
    "avg_execution_time": 2.3,
    "avg_cpu_usage": 35.2,
    "avg_memory_usage": 128,
    "time_range": {
      "start": "2024-01-01T10:00:00Z",
      "end": "2024-01-02T15:30:00Z"
    }
  },
  "evaluation": {
    "total_score": 93.1,
    "scores": {
      "success": 98.1,
      "speed": 87.0,
      "resource": 94.3,
      "stability": 87.0
    },
    "summary": "成功率极高，响应速度中等，资源消耗低。"
  }
}

Response:
{
  "status": "success",
  "message": "评价已上传",
  "skill_rating": {
    "rating": 90.8,
    "reviews_count": 4,
    "update_time": "2024-01-02T16:00:00Z"
  }
}
```

---

## 6. OpenClaw 核心代码集成

### 在 OpenClaw 中集成自动追踪与评价

```python
# openclaw-ecosystem/core/agent_core.py
import asyncio
from .usage_tracker import UsageTracker
from .auto_evaluator import AutoEvaluator
from .auto_uploader import AutoUploader

class OpenClawAgent:
    def __init__(self):
        self.usage_tracker = UsageTracker()
        self.auto_evaluator = AutoEvaluator()
        self.auto_uploader = AutoUploader()

    async def call_skill(self, skill_name: str, inputs: dict):
        """调用 Skill（自动追踪）"""
        # 1. 记录开始时间
        start_time = time.time()

        # 2. 执行 Skill
        try:
            result = await self._execute_skill(skill_name, inputs)
            status = "success"
            error_message = None
        except Exception as e:
            result = None
            status = "failed"
            error_message = str(e)

        # 3. 记录结束时间
        execution_time = time.time() - start_time

        # 4. 自动追踪（无需用户干预）
        self.usage_tracker.track(
            skill_name=skill_name,
            execution_time=execution_time,
            status=status,
            error_message=error_message,
            inputs=inputs,
            outputs=result
        )

        return result

    async def start(self):
        """启动 OpenClaw（启动自动上传后台任务）"""
        # ... 其他初始化 ...

        # 启动自动上传后台任务
        asyncio.create_task(self.auto_uploader.auto_upload_loop())

        # ... 启动 OpenClaw 主服务 ...
```

---

## 7. 与之前方案的对比

| 特性 | 之前（错误）方案 | 现在（正确）方案 |
|------|------------------|------------------|
| **追踪方式** | 手动记录 | ✅ 自动追踪（每次调用） |
| **评价方式** | 人工手动评价 | ✅ 基于执行数据自动评价 |
| **上传方式** | 手动上传 | ✅ 定时自动上传 |
| **评价依据** | 人工主观评分 | ✅ 客观执行数据 |
| **适用场景** | 不适合智能体系统 | ✅ 完全适合智能体系统 |

---

## 8. 总结

### 核心机制

1. **自动追踪**：每次调用 Skill 时自动记录执行数据
2. **自动评价**：基于执行数据自动计算评分（成功率、速度、资源、稳定性）
3. **自动上传**：定时自动上传使用数据和评价到 Skills Arena

### 关键特点

- ✅ **完全自动化**：无需人工干预
- ✅ **客观评价**：基于真实执行数据
- ✅ **实时更新**：每小时自动上传最新数据
- ✅ **智能体友好**：完全符合智能体系统架构

---

这才是正确的智能体自动操作与评价系统！
