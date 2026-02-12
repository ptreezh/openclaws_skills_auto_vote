# Skills Arena - SubAgent 协同系统

## 项目概述

完整的 Skills Arena 联邦学习与多 Agent 协作系统。

## 核心架构

```
用户
  │
  ▼
AI CLI (OpenClaw)
  │
  ├── 本地 LLM 执行 Skills
  │
  ▼
SubAgent (通过调用 Skill 与平台交互)
  │
  ├── CodingAgent
  ├── ResearchAgent
  ├── WritingAgent
  ├── DataAgent
  │
  ▼
  Arena Sync Skill (与 Skills Arena 平台交互)
  │
  ├── Skills 同步
  ├── 搜索
  ├── 推荐
  ├── 联邦学习
  │
  ▼
Skills Arena Platform
```

## 文件结构

```
skills-arena-collab-sdk/
├── PROJECT_SUMMARY.md          # 本文件
├── collab_sdk.py              # Phase 2: 协作过滤 SDK
├── cloud_api_client.py        # Phase 6: 云 API 客户端
├── performance_benchmarks.py  # 性能测试
│
├── skills/
│   └── arenasync/
│       ├── SKILL.md           # Skill 文档
│       ├── README.md          # 使用说明
│       ├── multi_agent_demo.py    # 多 Agent 演示
│       ├── multi_agent_demo.md    # 协作文档
│       └── scripts/
│           ├── skill.py           # 核心 Skill 实现
│           ├── skill_test.py      # 单元测试
│           └── advanced_demo.py   # 高级场景演示
│
├── data/
│   ├── skills_cache/          # Skills 缓存
│   └── federated/             # 联邦学习数据
│
└── phaseX/
    ├── phase4/                # 联邦学习
    ├── phase5/                # 高级联邦学习
    └── phase6/                # 跨设备传输
```

## 快速开始

### 1. 测试 Skill

```bash
# 基础演示
cd skills/arenasync/scripts
python skill.py --demo

# 单元测试
python skill_test.py
```

### 2. 多 Agent 协作

```bash
cd skills/arenasync
python multi_agent_demo.py
```

### 3. 高级场景

```bash
cd skills/arenasync/scripts
python advanced_demo.py --scenario all
```

## SubAgent 类型

| Agent | 角色 | 主要功能 |
|-------|------|---------|
| `CodingAgent` | 编码 | 代码生成、代码审查 |
| `ResearchAgent` | 研究 | 信息搜索、论文分析 |
| `WritingAgent` | 写作 | 内容创作、文档编辑 |
| `DataAgent` | 数据 | 统计分析、数据可视化 |

## 使用示例

### 在 OpenClaw Agent 中使用

```python
from arenasync_meta_skill import ArenaSyncMetaSkill

# 创建 Meta-Skill 实例
skill = ArenaSyncMetaSkill(agent_id="my-agent")

# 第一次使用：检查是否需要询问用户
if skill.should_ask_user():
    ui = skill.get_consent_ui()
    # 展示给用户

# 处理用户响应
should_install, msg = await skill.handle_user_response("yes")
if should_install:
    skill.install_hook()

# 后续使用：自动记录数据，永不打扰
result = await skill.sync_skills()
result = await skill.search_skills("python")
```

### 核心设计：一次询问，永不打扰

```
第一次使用：
  → 询问用户（仅一次）
  → 肯定：安装钩子，参与协同进化
  → 否定：沉默，不主动打扰
  → 除非用户主动说"如何协同进化"

后续使用：
  → 绝不主动询问
  → 自动记录使用数据
  → 定期上传梯度（脱敏后）
```

## 主要方法

| 方法 | 说明 |
|------|------|
| `should_ask_user()` | 是否应该询问用户（第一次使用） |
| `get_consent_ui()` | 获取用户同意 UI |
| `handle_user_response()` | 处理用户响应（是/否） |
| `install_hook()` | 安装联邦学习钩子 |
| `wrap_execute()` | 包装执行函数（自动记录） |
| `sync_skills()` | 同步 Skills |
| `search_skills()` | 搜索 Skills |
| `get_recommendations()` | 获取推荐 |

## 核心功能

### 1. Skills 同步

从 Skills Arena 平台同步最新的 Skills 元数据：

```python
await skill.run(action=Action.SYNC.value, what="skills")
```

### 2. 联邦学习

参与隐私保护的联邦学习：

```python
await skill.run(
    action=Action.FEDERATED_TRAIN.value,
    rounds=10  # 训练轮数
)
```

### 3. 协同过滤推荐

基于用户行为的个性化推荐：

```python
await skill.run(
    action=Action.RECOMMEND.value,
    category="coding",
    limit=5
)
```

## 演示输出

### 基础演示

```
[1] Syncing skills from Skills Arena...
    ✓ Synced 5 skills

[2] Listing available skills...
    - Python Code Generator (coding) - ⭐ 4.5
    - Web Searcher (research) - ⭐ 4.2
    ...

[3] Participating in Federated Learning...
    Round 1: Accuracy 71.3%
    Round 2: Accuracy 76.7%
    Round 3: Accuracy 97.0%
```

### 复杂任务演示

```
[1] Task Decomposition
  task-1: [research] 研究 AI 最新趋势
  task-2: [coding] 生成代码示例
  task-3: [writing] 撰写报告

[2] Task Execution
  Research: FL Accuracy 91.0%
  Code: Skills found: 3
  Writing: Tools available: 5

[3] Federated Learning Contributions
  Total FL Rounds: 8
```

## 技术特点

1. **本地优先** - Skills 在本地执行，不依赖网络
2. **隐私保护** - 联邦学习只传输模型梯度
3. **离线可用** - Skills 缓存后可离线使用
4. **可扩展** - 易于添加新的 Agent 类型
5. **可测试** - 完整的单元测试覆盖

## 下一步

1. **真实平台集成** - 替换 Mock 实现为真实 API
2. **gRPC 支持** - 添加高性能 gRPC 通信
3. **安全增强** - 添加加密和认证
4. **生产部署** - Docker 容器化部署
