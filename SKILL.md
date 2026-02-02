# Skills Arena - AI Skills 擂台评比平台

基于 `adaptive-orchestrator-v2` 架构设计的 Skills 擂台评比网站，提供类似电商平台的用户评价机制，让用户对相同场景下不同 Skills 的表现进行横向对比和反馈。

---

## 核心设计理念

### 1. 场景驱动
- 每个评比围绕**具体应用场景**展开（如代码生成、文本创作、数据分析）
- 同一场景下的不同 Skills 同台竞技
- 用户基于真实使用体验提交评价

### 2. 多维评价
- **总体评分**：1-5 星综合评价
- **细分指标**：
  - 准确性（Accuracy）：输出结果的正确程度
  - 效率（Efficiency）：响应速度和资源消耗
  - 创意（Creativity）：创新性和独特性
- **文字评论**：详细的使用体验分享

### 3. 实时排行
- 基于用户评价动态生成排行榜
- 支持按场景、指标筛选
- 展示排名、评分、评价数等多维度信息

---

## 系统架构

### 数据模型

```
Skills Arena
├── scenarios/           # 场景数据
│   ├── scenario-xxx.json
│   └── ...
├── skills/              # Skill 数据
│   ├── skill-xxx.json
│   └── ...
├── reviews/             # 评价数据
│   ├── review-xxx.json
│   └── ...
└── leaderboards/        # 排行榜数据
    ├── leaderboard-xxx.json
    └── ...
```

### 核心组件

#### 1. ArenaManager（核心管理器）
**文件**: `scripts/arena_manager.py`

核心功能：
- 场景管理：创建、查询、更新评比场景
- Skill 管理：注册、查询 Skills
- 评价管理：收集、存储、统计用户评价
- 排行榜生成：基于评分生成 Skills 排名

#### 2. WebServer（Web 服务器）
**文件**: `scripts/web_server.py`

基于 Flask 的轻量级 Web 服务器，提供：
- RESTful API
- 响应式前端界面
- 实时排行榜展示
- 用户评价提交

#### 3. InitDemo（演示数据初始化）
**文件**: `scripts/init_demo.py`

快速初始化演示数据：
- 4 个评比场景
- 6 个参赛 Skills
- 30+ 条演示评价

---

## 使用指南

### 快速启动

#### 1. 初始化演示数据

```bash
cd skills-arena/scripts
python init_demo.py
```

这将创建：
- 4 个评比场景（代码生成、文本创作、数据分析、对话问答）
- 6 个 Skills（GPT-4-Turbo、Claude-3.5-Sonnet、Gemini-Pro、Qwen-Max、Llama-3.1-70B、DeepSeek-Coder-V2）
- 30+ 条演示评价

#### 2. 启动 Web 服务器

```bash
python web_server.py
```

服务器将在 `http://localhost:5000` 启动

#### 3. 访问网站

打开浏览器访问：`http://localhost:5000`

### API 文档

#### 场景相关

**获取所有场景**
```
GET /api/scenarios
```

**获取特定场景**
```
GET /api/scenarios/<scenario_id>
```

**创建新场景**
```
POST /api/scenarios
Content-Type: application/json

{
  "title": "场景标题",
  "description": "场景描述",
  "category": "场景分类"
}
```

#### Skill 相关

**获取所有 Skills**
```
GET /api/skills
```

**获取特定 Skill**
```
GET /api/skills/<skill_id>
```

**注册新 Skill**
```
POST /api/skills
Content-Type: application/json

{
  "skill_name": "Skill 名称",
  "description": "Skill 描述",
  "author": "作者"
}
```

**将 Skill 添加到场景**
```
POST /api/scenarios/<scenario_id>/skills/<skill_id>
```

#### 排行榜相关

**获取排行榜**
```
GET /api/leaderboard/<scenario_id>
```

#### 评价相关

**提交评价**
```
POST /api/reviews
Content-Type: application/json

{
  "scenario_id": "场景 ID",
  "skill_id": "Skill ID",
  "user_id": "用户 ID",
  "rating": 4.5,
  "metrics": {
    "accuracy": 4.0,
    "efficiency": 4.5,
    "creativity": 5.0
  },
  "comment": "评论内容"
}
```

**获取场景的所有评价**
```
GET /api/reviews/<scenario_id>
```

---

## 数据模型详解

### 场景（Scenario）

```json
{
  "scenario_id": "scenario-abc123",
  "title": "代码生成",
  "description": "测试 Skills 在生成 Python 代码方面的能力",
  "category": "code-generation",
  "created_at": "2026-02-02T12:00:00.000000",
  "updated_at": "2026-02-02T12:00:00.000000",
  "status": "active",
  "registered_skills": ["skill-xyz", "skill-abc"],
  "metrics": {
    "total_reviews": 25,
    "total_skills": 5,
    "avg_rating": 4.5
  }
}
```

### Skill

```json
{
  "skill_id": "skill-abc123",
  "skill_name": "GPT-4-Turbo",
  "description": "OpenAI 的先进语言模型",
  "author": "OpenAI",
  "registered_at": "2026-02-02T12:00:00.000000",
  "metrics": {
    "total_reviews": 15,
    "avg_rating": 4.8,
    "avg_accuracy": 4.7,
    "avg_efficiency": 4.9,
    "avg_creativity": 4.8
  },
  "categories": ["code-generation", "content-creation"]
}
```

### 评价（Review）

```json
{
  "review_id": "review-abc123",
  "scenario_id": "scenario-xyz",
  "skill_id": "skill-abc",
  "user_id": "user-001",
  "rating": 4.5,
  "metrics": {
    "accuracy": 4.0,
    "efficiency": 4.5,
    "creativity": 5.0
  },
  "comment": "代码质量很好，但有时候会产生幻觉",
  "created_at": "2026-02-02T12:00:00.000000",
  "helpful_count": 0,
  "flagged": false
}
```

### 排行榜（Leaderboard）

```json
{
  "scenario_id": "scenario-xyz",
  "scenario_title": "代码生成",
  "category": "code-generation",
  "generated_at": "2026-02-02T12:00:00.000000",
  "total_skills": 5,
  "leaderboard": [
    {
      "rank": 1,
      "skill_id": "skill-abc",
      "skill_name": "GPT-4-Turbo",
      "author": "OpenAI",
      "metrics": {
        "total_reviews": 15,
        "avg_rating": 4.8,
        "avg_accuracy": 4.7,
        "avg_efficiency": 4.9,
        "avg_creativity": 4.8
      }
    }
  ]
}
```

---

## 功能特性

### 1. 场景管理
- ✅ 创建评比场景
- ✅ 支持自定义场景分类
- ✅ 场景状态管理（活跃/暂停）
- ✅ 场景统计信息

### 2. Skill 管理
- ✅ 注册新 Skill
- ✅ Skill 元信息管理（作者、描述）
- ✅ 多场景注册
- ✅ 自动指标统计

### 3. 评价系统
- ✅ 多维度评分（总体、准确性、效率、创意）
- ✅ 文字评论支持
- ✅ 用户标识
- ✅ 评价时间戳
- ✅ 有用投票（预留）
- ✅ 评价标记（预留）

### 4. 排行榜
- ✅ 实时动态生成
- ✅ 多维度排序
- ✅ Top 3 高亮显示
- ✅ 详细指标展示

### 5. Web 界面
- ✅ 响应式设计
- ✅ 实时数据加载
- ✅ 场景切换
- ✅ 评价提交表单
- ✅ 排行榜展示
- ✅ 评价浏览

---

## 扩展方向

### 短期
1. **用户系统**
   - 用户注册/登录
   - 用户画像
   - 评价历史

2. **高级筛选**
   - 按指标筛选
   - 按时间范围筛选
   - 按评价数筛选

3. **评价互动**
   - 有用投票
   - 回复评论
   - 点赞/踩

### 中期
1. **Skill 性能测试**
   - 自动化测试集成
   - 性能基准测试
   - 实时监控

2. **数据分析**
   - 趋势分析
   - 对比分析
   - 洞察报告

3. **推荐系统**
   - 个性化推荐
   - 场景匹配
   - Skill 对比

### 长期
1. **社区功能**
   - 讨论区
   - 最佳实践分享
   - 技术博客

2. **企业版**
   - 企业场景
   - 定制化评测
   - 私有部署

3. **插件生态**
   - 第三方集成
   - API 开放
   - SDK 提供

---

## 技术栈

- **后端**: Python 3.8+
- **Web 框架**: Flask
- **数据存储**: JSON 文件（可扩展至数据库）
- **前端**: 原生 JavaScript + HTML5 + CSS3
- **架构参考**: adaptive-orchestrator-v2

---

## 性能考虑

### 当前实现
- 基于文件系统存储
- 适合中小规模数据（< 10,000 条评价）
- 快速原型和演示

### 扩展方案
- 数据库迁移（PostgreSQL / MongoDB）
- 缓存层（Redis）
- 分页和索引优化
- API 限流

---

## 安全考虑

### 当前实现
- 基础输入验证
- 评分范围检查

### 扩展方案
- 用户认证（JWT / OAuth）
- CSRF 保护
- XSS 防护
- 速率限制
- 数据加密

---

## 许可证

本 Skill 基于 adaptive-orchestrator-v2 架构设计，遵循相同的使用规范。

---

## 贡献

欢迎提交 Issue 和 Pull Request 来完善这个 Skills 擂台评比平台！

---

## 联系方式

如有问题或建议，请通过以下方式联系：
- 提交 Issue
- 发送 Pull Request
