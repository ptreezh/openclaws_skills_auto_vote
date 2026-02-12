# SubAgent 与 Skills Arena 平台协同互动指南

## 核心问题

> **SubAgent 如何通过 Skills 与 Skills Arena 平台协同互动？

## 架构图解

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         SubAgent (如 CodingAgent)                         │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │  • 本地 LLM 执行                                                   │ │
│  │  • 理解任务                                                        │ │
│  │  • 决定何时调用 Skill                                              │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                    │                                    │
│                                    │ 调用                               │
│                                    ▼                                    │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                    ArenaSync Skill                                 │ │
│  │                                                                   │ │
│  │   async def run(action, **kwargs):                               │ │
│  │       if action == "search":                                      │ │
│  │           return await platform.search_skills(...)                │ │
│  │       elif action == "federated_train":                          │ │
│  │           return await platform.upload_update(...)                 │ │
│  │                                                                   │ │
│  └───────────────────────────────────────────────────────────────────┘ │
│                                    │                                    │
│                         Skill 与平台通信                                  │
│                                    ▼                                    │
│  ┌───────────────────────────────────────────────────────────────────┐ │
│  │                   Skills Arena Platform                           │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐  │ │
│  │  │ Skills 元数据 │  │ 评分系统    │  │ 联邦学习聚合器         │  │ │
│  │  │ • 列表       │  │ • 用户评分   │  │ • 收集模型更新        │  │ │
│  │  │ • 搜索       │  │ • 平均评分   │  │ • 聚合全局模型        │  │ │
│  │  │ • 推荐       │  │ • 排行榜     │  │ • 分发改进模型        │  │ │
│  │  └──────────────┘  └──────────────┘  └────────────────────────┘  │ │
│  │                                                                   │ │
│  └───────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

## 互动流程详解

### 场景 1: SubAgent 发现并使用 Skill

```
CodingAgent                                      Skills Arena Platform
    │                                                 │
    │  1. 调用 Skill: search_skills()                 │
    │ ──────────────────────────────────────────────▶│
    │                                                 │  查找 Skills 元数据
    │                                                 │◀─────────────────
    │                                                 │
    │  2. 返回: [PythonGen, CodeReview, ...]          │
    │ ◀───────────────────────────────────────────────│
    │                                                 │
    ▼                                                 ▼
```

**代码示例**:
```python
# CodingAgent 内部
async def find_skills(self):
    # 通过 Skill 调用平台
    result = await self.call_skill(
        action=Action.SEARCH.value,
        query="python code generation"
    )
    # result = {"skills": [...], "count": 3}
    return result
```

---

### 场景 2: 联邦学习 - 贡献模型更新

```
ResearchAgent                                      Skills Arena Platform
    │                                                 │
    │  1. 本地训练模型 (不离开设备)                     │
    │  ┌─────────────────────────────────────────┐   │
    │  │ local_model.train(data)                  │   │
    │  │ → gradients = [0.1, 0.2, ...]           │   │
    │  └─────────────────────────────────────────┘   │
    │                                                 │
    │  2. 调用 Skill: federated_train()              │
    │     发送: gradients (不是原始数据!)             │
    │ ──────────────────────────────────────────────▶│
    │                                                 │
    │                                                 │  3. 聚合多个 Agent 的更新
    │                                                 │  ┌─────────────────────┐
    │                                                 │  │ Agent1: [0.1, 0.2]  │──┐
    │                                                 │  │ Agent2: [0.2, 0.3]  │──┼──▶ 平均 ──▶ 新模型
    │                                                 │  │ Agent3: [0.1, 0.3]  │──┘
    │                                                 │  └─────────────────────┘
    │                                                 │
    │  3. 返回: 确认 + 新模型版本                      │
    │ ◀───────────────────────────────────────────────│
    │                                                 │
    ▼                                                 ▼
```

**代码示例**:
```python
# ResearchAgent 内部
async def participate_fl(self, rounds: int = 5):
    result = await self.call_skill(
        action=Action.FEDERATED_TRAIN.value,
        rounds=rounds
    )
    # result = {"rounds_completed": 5, "accuracy": 0.91}
    return result
```

**关键点**:
- ✅ **原始数据不离开设备**
- ✅ **只传输模型梯度/权重**
- ✅ **差分隐私保护**
- ✅ **用户可控参与**

---

### 场景 3: 协同过滤推荐

```
WritingAgent                                       Skills Arena Platform
    │                                                 │
    │  1. 调用 Skill: get_recommendations()           │
    │     发送: 用户历史 [skill-A, skill-B]           │
    │ ──────────────────────────────────────────────▶│
    │                                                 │
    │                                                 │  2. 协同过滤算法
    │                                                 │  ┌─────────────────────┐
    │                                                 │  │ User-A → [A, B, C]  │──┐
    │                                                 │  │ User-B → [A, B, D]  │──┼──▶ 相似用户
    │                                                 │  │ User-C → [A, C, E]  │──┘
    │                                                 │  │ → 推荐: [B] 给当前用户
    │                                                 │  └─────────────────────┘
    │                                                 │
    │  3. 返回: 个性化推荐列表                         │
    │ ◀───────────────────────────────────────────────│
    │                                                 │
    ▼                                                 ▼
```

**代码示例**:
```python
# WritingAgent 内部
async def get_recommendations(self):
    result = await self.call_skill(
        action=Action.RECOMMEND.value,
        category="writing"
    )
    # result = {"recommendations": [...], "source": "collaborative_filtering"}
    return result
```

---

## 多 Agent 协同工作流

```
                              ┌─────────────────┐
                              │  Coordinator    │
                              │  Agent          │
                              └────────┬────────┘
                                       │
              ┌───────────────────────┬─┴───────────────────────┐
              │                       │                           │
              ▼                       ▼                           ▼
    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
    │ CodingAgent     │    │ ResearchAgent   │    │ WritingAgent    │
    │ ─────────────  │    │ ─────────────  │    │ ─────────────  │
    │ action: search │    │ action: FL     │    │ action: recommend│
    └────────┬────────┘    └────────┬────────┘    └────────┬────────┘
             │                     │                     │
             └─────────────────────┼─────────────────────┘
                                   │
                                   ▼
                      ┌─────────────────────────┐
                      │   ArenaSync Skill       │
                      │                         │
                      │  • 统一接口             │
                      │  • 协议转换             │
                      │  • 缓存管理             │
                      └────────────┬────────────┘
                                   │
                                   ▼
                      ┌─────────────────────────┐
                      │  Skills Arena Platform │
                      │                         │
                      │  • Skills 数据库        │
                      │  • FL 聚合器            │
                      │  • 推荐引擎             │
                      └─────────────────────────┘
```

---

## 完整交互示例

### 场景: AI 技术博客生成

```
步骤 1: ResearchAgent 研究 AI 趋势
─────────────────────────────────
ResearchAgent
    │
    ├── call_skill("sync", what="skills")
    │   Platform → 返回最新 Skills
    │
    ├── call_skill("federated_train", rounds=5)
    │   Platform → 收集梯度，聚合模型，返回新版本
    │
    └── 返回: {topic: "AI Agents", accuracy: 0.91}


步骤 2: CodingAgent 生成代码示例
─────────────────────────────────
CodingAgent
    │
    ├── call_skill("search", query="LLM agent implementation")
    │   Platform → 返回相关 Skills
    │
    └── 返回: {skills_found: 3, tools: [...]}


步骤 3: WritingAgent 撰写博客
─────────────────────────────────
WritingAgent
    │
    ├── call_skill("recommend", category="writing")
    │   Platform → 返回写作推荐
    │
    └── 返回: {recommendations: [...]}


步骤 4: 联邦学习贡献
─────────────────────────────────
所有 Agent
    │
    ├── call_skill("federated_train", rounds=5)
    │   Platform → 聚合更新，改进全局模型
    │
    └── 返回: {rounds: 5, accuracy: 0.93}
```

---

## 关键交互点总结

| 交互类型 | Skill 方法 | 平台功能 | 数据流向 |
|---------|-----------|---------|---------|
| **发现** | `search` | Skills 搜索 | Platform → Agent |
| **推荐** | `recommend` | 协同过滤 | Platform → Agent |
| **同步** | `sync` | 数据同步 | Platform ↔ Agent |
| **联邦学习** | `federated_train` | 梯度聚合 | Agent → Platform |
| **评分** | `rate` | 评分系统 | Agent → Platform |
| **统计** | `stats` | 使用统计 | Platform → Agent |

---

## 隐私保护机制

```
                    不传输                    传输
                    ──────                   ──────
原始数据            ✅ 不离开设备              ❌
用户评分            ❌                       ✅
模型梯度            ❌                       ✅
Skill 元数据        ❌                       ✅
使用统计            ❌                       ✅

✓ 联邦学习 = 隐私保护 + 集体智能
```

---

## 总结

**SubAgent 与 Skills Arena 平台协同的核心**：

1. **Skill 是唯一接口** - 所有交互通过 ArenaSync Skill
2. **本地执行** - Skills 在本地运行
3. **隐私保护** - 联邦学习只传输模型，不传输数据
4. **统一协议** - 不同 Agent 通过相同 Skill 与平台交互
5. **协同过滤** - 基于用户行为提供个性化推荐
