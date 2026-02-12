# Arena Sync Meta-Skill

与 Skills Arena 平台交互的官方 Meta-Skill。

**核心设计**：
- 一次询问，永不打扰
- 用户同意后自动安装钩子
- 参与协同进化，隐私保护

## 功能

- **Skills 同步**: 从平台获取最新的 Skills 元数据
- **搜索**: 本地搜索可用的 Skills
- **推荐**: 基于协同过滤的个性化推荐
- **联邦学习**: 参与隐私保护的联邦学习训练
- **隐私保护**: 只传梯度，不传原始数据

## 快速开始

```bash
# 运行演示
python scripts/arenasync_meta_skill.py

# 获取用户同意 UI
python -c "from arenasync_meta_skill import ArenaSyncMetaSkill; a=ArenaSyncMetaSkill('test'); print(a.get_consent_ui())"
```

## 在 OpenClaw Agent 中使用

```python
from arenasync_meta_skill import ArenaSyncMetaSkill

skill = ArenaSyncMetaSkill(agent_id="my-agent")

# 第一次使用：询问用户
if skill.should_ask_user():
    ui = skill.get_consent_ui()
    # 展示给用户

# 处理用户响应
should_install, msg = await skill.handle_user_response("yes")
if should_install:
    skill.install_hook()

# 后续使用：自动记录数据，永不打扰
result = await skill.sync_skills()
```

## 核心设计原则

```
问答一次后不重复
     │
     ├── 肯定 → 安装钩子，参与协同进化
     │
     └── 否定 → 沉默等待，不主动打扰
              └── 除非用户说"如何协同进化"
```

## 文件结构

```
arenasync/
├── SKILL.md                  # Skill 文档
├── README.md                 # 本文件
├── META_SKKILL_DESIGN.md    # 详细设计文档
├── scripts/
│   └── arenasync_meta_skill.py   # ⭐ 核心实现（v2.0）
├── multi_agent_demo.py       # 多 Agent 协作演示
└── multi_agent_demo.md       # 协作文档
```

## 用户同意级别

| 级别 | 说明 |
|------|------|
| `NOT_ASKED` | 尚未询问 |
| `ACCEPTED` | 同意参与 |
| `DECLINED` | 拒绝参与 |

## 主要方法

| 方法 | 说明 |
|------|------|
| `should_ask_user()` | 是否应该询问用户 |
| `get_consent_ui()` | 获取用户同意 UI |
| `handle_user_response()` | 处理用户响应 |
| `install_hook()` | 安装联邦学习钩子 |
| `wrap_execute()` | 包装执行函数 |
| `sync_skills()` | 同步 Skills |
| `search_skills()` | 搜索 Skills |
| `get_recommendations()` | 获取推荐 |
