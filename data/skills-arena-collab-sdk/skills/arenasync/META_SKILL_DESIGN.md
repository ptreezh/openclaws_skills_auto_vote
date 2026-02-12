# ArenaSync Meta-Skill 设计文档

## 核心设计原则

```
问答一次后不重复
     │
     ├── 肯定回答 → 安装钩子，参与协同进化
     │
     └── 否定回答 → 沉默等待，不主动打扰
              │
              └── 除非用户专门询问"如何协同进化"，否则不再询问
```

## 用户交互流程

```
用户第一次使用 ArenaSync Skill
            │
            ▼
┌─────────────────────────────────────────┐
│  展示用户同意 UI（仅一次）               │
│                                         │
│  "你想参与协同进化吗？"                  │
│                                         │
│  • 是，参与协同进化                      │
│  • 否，仅同步                           │
└─────────────────────────────────────────┘
            │
            ├── 是 ──→ 安装钩子，参与联邦学习
            │
            └── 否 ──→ 记录选择，永不主动询问
                         （除非用户主动说"如何协同进化"）
```

## 状态机

```
┌──────────────┐
│  NOT_ASKED   │  ←── 初始状态
└──────┬───────┘
       │
       │ 第一次使用
       ▼
┌──────────────┐
│   ASKED     │  ←── 已询问，等待用户响应
└──────┬───────┘
       │
       ├── 回答"是" ───→ ACCEPTED（已同意）
       │
       └── 回答"否" ───→ DECLINED（已拒绝）

ACCEPTED ──→ 安装钩子，参与协同进化
DECLINED ──→ 沉默，不打扰
              （除非用户主动询问）
```

## 代码结构

```
ArenaSyncMetaSkill
    │
    ├── 同意管理
    │   ├── _load_consent()    # 加载同意状态
    │   ├── _save_consent()    # 保存同意状态
    │   ├── should_ask_user() # 是否应该询问
    │   └── need_to_ask_again() # 是否需要再次询问
    │
    ├── 用户交互
    │   ├── get_consent_ui()       # 获取同意 UI
    │   ├── handle_user_response()  # 处理用户响应
    │   └── check_activation_phrase() # 检查激活短语
    │
    ├── 钩子管理
    │   ├── install_hook()    # 安装钩子
    │   ├── uninstall_hook()  # 卸载钩子
    │   └── wrap_execute()   # 包装执行函数
    │
    └── 联邦学习
        ├── _record_usage()   # 记录使用
        └── _upload_gradients() # 上传梯度
```

## 使用方法

### 1. 下载 Skill

用户从 Skills Arena 下载 ArenaSync Meta-Skill

### 2. Agent 集成

```python
from arenasync_meta_skill import ArenaSyncMetaSkill

class MyAgent:
    def __init__(self):
        self.arena_sync = ArenaSyncMetaSkill(agent_id="my-agent")

    async def handle_skill_call(self, skill_id: str, execute_fn, *args, **kwargs):
        # 第一次使用？询问用户
        if self.arena_sync.should_ask_user():
            return {
                "action": "ask_consent",
                "ui": self.arena_sync.get_consent_ui(),
            }

        # 包装执行函数
        wrapped = self.arena_sync.wrap_execute(execute_fn)

        # 执行
        result = await wrapped(*args, **kwargs)
        return {"action": "execute", "result": result}

    async def handle_user_input(self, user_input: str):
        # 用户主动询问协同进化？
        if self.arena_sync.check_activation_phrase(user_input):
            if self.arena_sync.has_declined:
                return {
                    "action": "re_ask_consent",
                    "ui": "重新考虑参与？",
                }
            elif self.arena_sync.has_consent:
                return {
                    "action": "show_status",
                    "status": self.arena_sync.get_status(),
                }

        return {"action": "none"}
```

### 3. 处理用户响应

```python
# 用户回答后
should_install, message = await arena_sync.handle_user_response("yes")

if should_install:
    arena_sync.install_hook()
print(message)
```

## 隐私保护

```
上传到平台的内容：
❌ 原始数据
❌ 用户具体输入
❌ Skill 输出内容
✅ 使用统计（成功/失败）
✅ 执行时间（聚合）
✅ 梯度（脱敏后）
```

## 核心优势

| 优势 | 说明 |
|------|------|
| **零打扰** | 只询问一次，永不重复 |
| **透明可控** | 用户完全知道发生了什么 |
| **隐私保护** | 只传梯度，不传原始数据 |
| **可逆** | 用户可以随时退出 |
| **去中心化** | 不强制任何人参与 |

## 运行演示

```bash
python arenasync_meta_skill.py
```
