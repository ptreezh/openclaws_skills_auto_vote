# Arena Sync - npx 安装包

## 安装方式

### 方式一：npx 一键安装（推荐）

```bash
npx @skills-arena/arenasync@latest
```

### 方式二：npm 全局安装

```bash
npm install -g @skills-arena/arenasync
```

### 方式三：手动下载 ZIP

访问 [Skills Arena 平台](https://openclaws-skills-auto-vote.up.railway.app/skills/arenasync/download) 下载 ZIP 包。

## 使用方法

### Python 项目

```python
from arenasync_meta_skill import ArenaSyncMetaSkill

# 初始化
skill = ArenaSyncMetaSkill(agent_id="your-agent-id")

# 第一次使用：询问用户
if skill.should_ask_user():
    consent_ui = skill.get_consent_ui()
    # 展示给用户...

# 处理用户响应
should_install, message = await skill.handle_user_response("yes")
if should_install:
    skill.install_hook()

# 后续使用
skills = await skill.sync_skills()
results = await skill.search_skills("python")
```

### 两种参与模式

| 模式 | 选择 | 功能 |
|------|------|------|
| **基础参与** | "否，仅同步" | 上传 Skill、点评、下载推荐 |
| **联邦学习** | "是，参与" | + 记录使用数据、上传脱敏梯度 |

## 文件结构

```
@skills-arena/arenasync/
├── SKILL.md                  # 技能描述（必选）
├── README.md                 # 详细文档（必选）
├── META_SKILL_DESIGN.md     # 设计原理
├── package.json              # npx 配置
├── references/
│   └── *.md                 # 参考文档
└── scripts/
    └── arenasync_meta_skill.py  # 核心实现
```

## 相关链接

- **Skills Arena 平台**: https://openclaws-skills-auto-vote.up.railway.app
- **GitHub 仓库**: https://github.com/ptreezh/openclaws_skills_auto_vote
- **问题反馈**: https://github.com/ptreezh/openclaws_skills_auto_vote/issues
