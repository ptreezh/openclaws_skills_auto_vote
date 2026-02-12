---
name: arenasync
description: 与 Skills Arena 平台交互的官方 Meta-Skill，支持技能同步、个性化推荐和联邦学习
version: 2.0.0
author: Skills Arena Team
tags: [meta-skill, sync, recommendation, federated-learning, privacy]
---

# Arena Sync Meta-Skill

与 Skills Arena 平台交互的官方 Meta-Skill。

## Dependencies

无外部依赖，使用标准库。

## Usage

```bash
# 运行演示
python scripts/arenasync_meta_skill.py

# 获取用户同意 UI
python -c "from arenasync_meta_skill import ArenaSyncMetaSkill; a=ArenaSyncMetaSkill('test'); print(a.get_consent_ui())"
```

## 核心设计

**一次询问，永不打扰**

- 第一次使用：询问用户
- 肯定回答 → 安装钩子，参与协同进化
- 否定回答 → 沉默等待
- 除非用户主动说"如何协同进化"，否则不重复询问

## 功能

- **Skills 同步**: 从平台获取最新的 Skills
- **搜索**: 本地搜索可用的 Skills
- **推荐**: 基于协同过滤的个性化推荐
- **联邦学习**: 参与隐私保护的联邦学习
- **隐私保护**: 只传梯度，不传原始数据

## 在 OpenClaw 中使用

```python
from arenasync_meta_skill import ArenaSyncMetaSkill

skill = ArenaSyncMetaSkill(agent_id="my-agent")

# 第一次使用
if skill.should_ask_user():
    ui = skill.get_consent_ui()  # 展示给用户

# 处理用户响应
should_install, msg = await skill.handle_user_response("yes")
if should_install:
    skill.install_hook()

# 后续使用
result = await skill.sync_skills()
result = await skill.search_skills("python")
```

## 文件结构

```
arenasync/
├── SKILL.md                  # 本文件
├── README.md                 # 详细文档
├── META_SKILL_DESIGN.md      # 设计原理
├── references/
│   └── *.md                  # 参考文档
└── scripts/
    └── arenasync_meta_skill.py   # 核心实现
```
