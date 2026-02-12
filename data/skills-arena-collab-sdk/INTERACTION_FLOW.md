# SubAgent 与 Skills Arena 平台交互 - 简单流程

## 一句话总结

```
SubAgent 调用 ArenaSync Skill → Skill 与平台通信 → 返回结果给 SubAgent
```

## 三种主要交互方式

### 1️⃣ 发现型交互（SubAgent ← Platform）

```
SubAgent                    ArenaSync Skill                    Platform
    │                            │                                │
    │  search(query="python")    │                                │
    │───────────────────────────▶│  search_skills(query)         │
    │                            │───────────────────────────────▶│
    │                            │                                │
    │                            │  [{"name": "PythonGen",...}]   │
    │◀───────────────────────────│◀───────────────────────────────│
    │                            │                                │
```

**示例**：CodingAgent 搜索 "python code" 相关的 Skills

---

### 2️⃣ 联邦学习型交互（SubAgent → Platform）

```
SubAgent                    ArenaSync Skill                    Platform
    │                            │                                │
    │  生成本地模型梯度           │                                │
    │  [0.1, 0.2, 0.3]          │                                │
    │                            │                                │
    │  federated_train(rounds=5) │                                │
    │───────────────────────────▶│  upload_gradients([0.1,0.2])  │
    │                            │───────────────────────────────▶│
    │                            │                                │
    │                            │           ┌───────────────┐   │
    │                            │           │ 聚合梯度       │   │
    │                            │           │ + 平均 + 更新  │   │
    │                            │           └───────────────┘   │
    │                            │                                │
    │                            │  {"accuracy": 0.91}           │
    │◀───────────────────────────│◀───────────────────────────────│
    │                            │                                │
```

**示例**：ResearchAgent 参与联邦学习，贡献模型更新（**原始数据不离开设备**）

---

### 3️⃣ 推荐型交互（SubAgent ← Platform）

```
SubAgent                    ArenaSync Skill                    Platform
    │                            │                                │
    │  recommend(category="writing")                              │
    │───────────────────────────▶│  collaborative_filter()       │
    │                            │───────────────────────────────▶│
    │                            │                                │
    │                            │  [{name": "ContentWriter"}]   │
    │◀───────────────────────────│◀───────────────────────────────│
    │                            │                                │
```

**示例**：WritingAgent 获取个性化写作推荐

---

## 完整协同示例

### 场景：CodingAgent 完成 "写 Python 函数" 任务

```
┌──────────────────────────────────────────────────────────────────┐
│                        CodingAgent                                │
│  1. 理解任务: "写一个 Python 斐波那契函数"                        │
│                                                                  │
│  2. 搜索相关 Skills                                              │
│     ┌─────────────────────────────────────────────────────────┐  │
│     │  call_skill("search", query="python fibonacci")        │  │
│     └─────────────────────────────────────────────────────────┘  │
│                                  │                                │
│                                  ▼                                │
│  3. Skill 与平台交互                                              │
│     ┌─────────────────────────────────────────────────────────┐  │
│     │  Platform 返回:                                        │  │
│     │  [{"name": "PythonGen", "rating": 4.5},               │  │
│     │   {"name": "CodeReview", "rating": 4.2}]              │  │
│     └─────────────────────────────────────────────────────────┘  │
│                                  │                                │
│                                  ▼                                │
│  4. LLM 使用返回的 Skills 执行任务                                │
│                                                                  │
│  5. 如果参与联邦学习:                                              │
│     ┌─────────────────────────────────────────────────────────┐  │
│     │  call_skill("federated_train", rounds=5)               │  │
│     └─────────────────────────────────────────────────────────┘  │
│                                  │                                │
│                                  ▼                                │
│     ┌─────────────────────────────────────────────────────────┐  │
│     │  Platform 聚合梯度，改进全局模型                        │  │
│     │  返回: {"accuracy": 0.89}                              │  │
│     └─────────────────────────────────────────────────────────┘  │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## 代码对应

```python
# SubAgent 内部
class CodingAgent:
    async def generate_python_function(self, requirement: str):
        # 步骤 2: 搜索 Skills
        result = await self.call_skill(
            action=Action.SEARCH.value,
            query=requirement
        )
        
        # 步骤 4: 使用 Skills 执行任务
        # ... LLM 执行 ...
        
        # 步骤 5: 联邦学习贡献
        fl_result = await self.call_skill(
            action=Action.FEDERATED_TRAIN.value,
            rounds=5
        )
        
        return {"success": True, "fl_accuracy": fl_result["accuracy"]}
```

---

## 交互类型速查表

| 需求 | 调用 | 作用 |
|-----|------|-----|
| 找 Skills | `search(query)` | 搜索 Skills |
| 列表 Skills | `list_skills()` | 列出 Skills |
| 获取推荐 | `recommend(category)` | 协同过滤推荐 |
| 同步数据 | `sync(what)` | 同步元数据 |
| 联邦学习 | `federated_train(rounds)` | 贡献模型 |
| 评分 | `rate(skill_id, rating)` | 评分 Skills |
| 统计 | `stats()` | 查看统计 |

---

## 核心原则

```
1. SubAgent 不直接访问平台
2. 所有交互通过 ArenaSync Skill
3. 联邦学习只传梯度，不传原始数据
4. Skill 负责协议转换和缓存管理
```
