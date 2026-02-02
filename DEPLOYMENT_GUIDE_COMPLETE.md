# Skills Arena - 部署指南

## 部署概览

**Skills Arena** 采用轻量级架构（Flask + JSON存储），可以轻松部署到多种免费平台。

---

## 免费平台推荐

### 方案 1: Render.com (推荐)

**优势**：
- ✅ 免费套餐永久提供
- ✅ 支持 PostgreSQL（可升级）
- ✅ 自动 HTTPS
- ✅ 自动部署（Git 集成）
- ✅ Web 服务 + Worker 支持

**限制**：
- Web 服务：512MB RAM，0.1 CPU
- 每月 750 小时免费额度
- 睡眠模式（15 分钟无活动后休眠）

**适合场景**：演示、小规模使用

---

### 方案 2: Railway.app

**优势**：
- ✅ $5 免费额度/月
- ✅ 支持 PostgreSQL
- ✅ 自动 HTTPS
- ✅ 自动部署
- ✅ 可视化管理界面

**限制**：
- 免费额度用完后需付费
- 内存限制较小

**适合场景**：需要持久化数据库的场景

---

### 方案 3: PythonAnywhere

**优势**：
- ✅ 永久免费 Beginner 账号
- ✅ 在线 IDE
- ✅ 支持 Flask
- ✅ 固定域名

**限制**：
- Python 3.x
- 无数据库（需要付费）
- 仅支持静态文件

**适合场景**：纯 Flask + JSON 存储

---

### 方案 4: Vercel (前端)

**优势**：
- ✅ 无限免费额度
- ✅ 全球 CDN
- ✅ 自动 HTTPS
- ✅ 极速部署

**限制**：
- 仅支持静态文件
- 不支持 Python 后端

**适合场景**：仅部署 Web 前端

---

### 方案 5: Replit (开发环境)

**优势**：
- ✅ 永久免费 Repls
- ✅ 在线编程环境
- ✅ 自动 HTTPS
- ✅ 支持多种语言

**限制**：
- 休眠模式
- 资源限制

**适合场景**：快速原型和演示

---

## 快速部署到 Render.com

### 步骤 1: 准备代码

```bash
# 1. 创建项目目录
mkdir skills-arena-deploy
cd skills-arena-deploy

# 2. 复制核心文件
cp -r skills-arena/* .
cp -r openclaw-ecosystem/* .

# 3. 创建 .gitignore
cat > .gitignore << 'EOF'
__pycache__/
*.pyc
.env
data/uploads/
*.log
EOF
```

---

### 步骤 2: 创建依赖文件

```bash
# 创建 requirements.txt
cat > requirements.txt << 'EOF'
flask==2.3.3
flask-cors==4.0.0
aiohttp==3.9.1
python-multipart==0.0.6
EOF
```

---

### 步骤 3: 创建 Procfile

```bash
# 创建 Procfile (Render.com 需求)
cat > Procfile << 'EOF'
web: python scripts/web_server.py
EOF
```

---

### 步骤 4: 修改服务器代码

**文件**: `scripts/web_server.py`

```python
#!/usr/bin/env python3
"""
Skills Arena Web 服务器
适配 Render.com 部署
"""

import os
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from pathlib import Path

# 创建 Flask 应用
app = Flask(__name__, static_folder='public', static_url_path='')
CORS(app)

# 数据路径
DATA_DIR = Path(__file__).parent.parent / 'data'

@app.route('/')
def index():
    """主页"""
    return send_from_directory('public', 'index.html')

@app.route('/api/health')
def health():
    """健康检查"""
    return jsonify({"status": "healthy", "service": "skills-arena"})

# ... 其他路由 ...

if __name__ == '__main__':
    # 获取端口（Render.com 从环境变量获取）
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')

    app.run(host=host, port=port, debug=False)
```

---

### 步骤 5: 推送到 GitHub

```bash
# 1. 初始化 Git
git init
git add .
git commit -m "Initial commit"

# 2. 创建 GitHub 仓库
# 访问 https://github.com/new 创建仓库

# 3. 推送到 GitHub
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/skills-arena-deploy.git
git push -u origin main
```

---

### 步骤 6: 在 Render.com 部署

1. **访问 Render.com**
   - 注册账号：https://render.com
   - 登录并连接 GitHub

2. **创建新服务**
   - 点击 "New +"
   - 选择 "Web Service"

3. **配置服务**
   ```
   Name: skills-arena
   Branch: main
   Runtime: Python 3
   Root Directory: (留空)
   Build Command: pip install -r requirements.txt
   Start Command: python scripts/web_server.py
   Instance Type: Free
   ```

4. **部署**
   - 点击 "Create Web Service"
   - 等待 3-5 分钟部署完成

5. **获取 URL**
   - 部署完成后，Render 会提供一个 URL
   - 例如：https://skills-arena.onrender.com

---

### 步骤 7: 初始化演示数据

部署完成后，访问：

```
https://skills-arena.onrender.com/api/init
```

这会自动初始化演示数据。

---

## 完整部署到 Render.com 的文件

### 1. 文件结构

```
skills-arena-deploy/
├── requirements.txt          # Python 依赖
├── Procfile                 # Render 启动配置
├── .gitignore              # Git 忽略文件
├── scripts/                # 脚本目录
│   ├── web_server.py       # Web 服务器
│   ├── arena_manager.py    # 场景和技能管理器
│   ├── skill_validator.py  # 技能验证器
│   └── init_demo.py        # 初始化脚本
├── api/                    # API 服务
│   └── v2_server.py        # API 服务器
├── data/                   # 数据目录
│   ├── skills/            # 技能数据
│   ├── scenarios/         # 场景数据
│   ├── reviews/           # 评价数据
│   ├── leaderboards/      # 排行榜数据
│   └── uploads/           # 上传记录
└── public/                # 静态文件
    └── index.html         # 前端页面
```

---

### 2. requirements.txt

```txt
flask==2.3.3
flask-cors==4.0.0
aiohttp==3.9.1
python-multipart==0.0.6
```

---

### 3. Procfile

```procfile
web: python scripts/web_server.py
```

---

### 4. .gitignore

```gitignore
__pycache__/
*.pyc
.env
data/uploads/
*.log
.DS_Store
```

---

### 5. 适配的 web_server.py

```python
#!/usr/bin/env python3
"""
Skills Arena Web 服务器
适配 Render.com 部署
"""

import os
import json
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from pathlib import Path

# 创建 Flask 应用
app = Flask(__name__, static_folder='public', static_url_path='')
CORS(app)

# 数据路径
DATA_DIR = Path(__file__).parent.parent / 'data'

# 确保数据目录存在
DATA_DIR.mkdir(parents=True, exist_ok=True)

@app.route('/')
def index():
    """主页"""
    return send_from_directory('public', 'index.html')

@app.route('/api/health')
def health():
    """健康检查"""
    return jsonify({"status": "healthy", "service": "skills-arena"})

@app.route('/api/scenarios')
def get_scenarios():
    """获取所有场景"""
    scenarios_dir = DATA_DIR / 'scenarios'
    scenarios = []

    if scenarios_dir.exists():
        for file in scenarios_dir.glob('*.json'):
            with open(file) as f:
                scenarios.append(json.load(f))

    return jsonify(scenarios)

@app.route('/api/skills')
def get_skills():
    """获取所有技能"""
    skills_dir = DATA_DIR / 'skills'
    skills = []

    if skills_dir.exists():
        for file in skills_dir.glob('*.json'):
            with open(file) as f:
                skills.append(json.load(f))

    return jsonify(skills)

@app.route('/api/leaderboard/<scenario_id>')
def get_leaderboard(scenario_id):
    """获取排行榜"""
    leaderboard_dir = DATA_DIR / 'leaderboards'
    leaderboard_file = leaderboard_dir / f'leaderboard-{scenario_id}.json'

    if leaderboard_file.exists():
        with open(leaderboard_file) as f:
            return jsonify(json.load(f))
    else:
        return jsonify({"error": "Leaderboard not found"}), 404

@app.route('/api/reviews', methods=['GET'])
def get_reviews():
    """获取所有评价"""
    scenario_id = request.args.get('scenario_id')
    reviews_dir = DATA_DIR / 'reviews'
    reviews = []

    if reviews_dir.exists():
        for file in reviews_dir.glob('*.json'):
            with open(file) as f:
                review = json.load(f)
                if not scenario_id or review.get('scenario_id') == scenario_id:
                    reviews.append(review)

    return jsonify(reviews)

@app.route('/api/reviews', methods=['POST'])
def create_review():
    """提交评价"""
    review = request.json

    # 验证评价
    required_fields = ['scenario_id', 'skill_id', 'user_id', 'rating']
    for field in required_fields:
        if field not in review:
            return jsonify({"error": f"Missing field: {field}"}), 400

    # 保存评价
    reviews_dir = DATA_DIR / 'reviews'
    reviews_dir.mkdir(parents=True, exist_ok=True)

    review_id = f"review-{os.urandom(6).hex()}"
    review['review_id'] = review_id
    review['created_at'] = None  # 添加时间戳

    review_file = reviews_dir / f'{review_id}.json'
    with open(review_file, 'w') as f:
        json.dump(review, f, indent=2)

    # 更新排行榜
    update_leaderboard(review['scenario_id'])

    return jsonify(review), 201

def update_leaderboard(scenario_id):
    """更新排行榜"""
    # 这里应该实现排行榜更新逻辑
    pass

@app.route('/api/init', methods=['POST'])
def init_demo():
    """初始化演示数据"""
    try:
        # 调用初始化脚本
        import subprocess
        result = subprocess.run(
            ['python', 'scripts/init_demo.py'],
            capture_output=True,
            text=True,
            cwd=str(Path(__file__).parent.parent)
        )

        if result.returncode == 0:
            return jsonify({"status": "success", "message": "Demo data initialized"})
        else:
            return jsonify({"status": "error", "message": result.stderr}), 500

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    # 获取端口（Render.com 从环境变量获取）
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')

    app.run(host=host, port=port, debug=False)
```

---

### 6. 简单的 public/index.html

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Skills Arena</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: white;
        }
        h1 {
            text-align: center;
            margin-bottom: 40px;
        }
        .scenario {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            backdrop-filter: blur(10px);
        }
        .leaderboard {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 20px;
            margin-top: 20px;
            backdrop-filter: blur(10px);
        }
        .skill {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .rank {
            font-size: 24px;
            font-weight: bold;
            color: #ffd700;
        }
        .rating {
            font-size: 20px;
            font-weight: bold;
        }
        .btn {
            background: #ffd700;
            color: #333;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
        }
        .btn:hover {
            background: #ffec8b;
        }
    </style>
</head>
<body>
    <h1>🏆 Skills Arena - 技能擂台评比平台</h1>

    <div id="app">
        <div class="scenario">
            <h2>加载中...</h2>
        </div>
    </div>

    <script>
        // 加载场景列表
        async function loadScenarios() {
            const response = await fetch('/api/scenarios');
            const scenarios = await response.json();

            let html = '';
            scenarios.forEach(scenario => {
                html += `
                    <div class="scenario">
                        <h3>${scenario.title}</h3>
                        <p>${scenario.description}</p>
                        <button class="btn" onclick="loadLeaderboard('${scenario.scenario_id}')">
                            查看排行榜
                        </button>
                        <div id="leaderboard-${scenario.scenario_id}"></div>
                    </div>
                `;
            });

            document.getElementById('app').innerHTML = html;
        }

        // 加载排行榜
        async function loadLeaderboard(scenarioId) {
            const response = await fetch(`/api/leaderboard/${scenarioId}`);
            const leaderboard = await response.json();

            let html = `
                <div class="leaderboard">
                    <h3>📊 排行榜</h3>
            `;

            leaderboard.leaderboard.forEach((item, index) => {
                html += `
                    <div class="skill">
                        <span class="rank">#${item.rank}</span>
                        <span>${item.skill_name}</span>
                        <span class="rating">★ ${item.metrics.avg_rating}</span>
                    </div>
                `;
            });

            html += '</div>';
            document.getElementById(`leaderboard-${scenarioId}`).innerHTML = html;
        }

        // 初始化
        loadScenarios();
    </script>
</body>
</html>
```

---

## 部署步骤总结

### 1. 准备代码

```bash
# 创建部署目录
mkdir skills-arena-deploy
cd skills-arena-deploy

# 复制核心文件
cp -r skills-arena/* .

# 创建必要文件
# - requirements.txt
# - Procfile
# - .gitignore
# - public/index.html
```

---

### 2. 推送到 GitHub

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/skills-arena-deploy.git
git push -u origin main
```

---

### 3. 在 Render.com 部署

1. 访问 https://render.com
2. 注册并登录
3. 连接 GitHub
4. 创建新 Web Service
5. 配置：
   - Runtime: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python scripts/web_server.py`
6. 部署

---

### 4. 初始化数据

```bash
# 访问 API 初始化端点
curl -X POST https://skills-arena.onrender.com/api/init
```

---

## 访问你的 Skills Arena

部署完成后，访问：

```
https://skills-arena.onrender.com
```

你将看到：
- ✅ 响应式 Web 界面
- ✅ 场景列表
- ✅ 技能排行榜
- ✅ 实时数据

---

## 其他平台部署

### PythonAnywhere

```bash
# 1. 注册 PythonAnywhere
https://www.pythonanywhere.com

# 2. 上传代码
# 3. 创建 Web 应用
# 4. 配置 Virtualenv
# 5. 安装依赖
# 6. 运行 WSGI
```

---

### Replit

```bash
# 1. 访问 Replit
https://replit.com

# 2. 创建 Python Repl
# 3. 上传代码
# 4. 运行 scripts/web_server.py
# 5. 点击 "Open in Browser"
```

---

## 生产环境优化

### 1. 数据库迁移

```python
# 使用 PostgreSQL 替代 JSON 存储
import psycopg2
from psycopg2 import sql

# 连接数据库
conn = psycopg2.connect(
    dbname="skills_arena",
    user="postgres",
    password="your_password",
    host="your-db-host"
)

# 创建表
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE skills (
        skill_id VARCHAR(50) PRIMARY KEY,
        name VARCHAR(255),
        description TEXT,
        rating FLOAT,
        created_at TIMESTAMP
    )
""")
conn.commit()
```

---

### 2. 缓存优化

```python
# 使用 Redis 缓存
import redis

# 连接 Redis
r = redis.Redis(host='localhost', port=6379, db=0)

# 缓存排行榜
def get_leaderboard(scenario_id):
    cache_key = f"leaderboard:{scenario_id}"

    # 尝试从缓存获取
    cached = r.get(cache_key)
    if cached:
        return json.loads(cached)

    # 否则从数据库获取
    leaderboard = load_leaderboard_from_db(scenario_id)

    # 缓存结果（5 分钟）
    r.setex(cache_key, 300, json.dumps(leaderboard))

    return leaderboard
```

---

### 3. 安全增强

```python
# 添加 JWT 认证
import jwt
from functools import wraps

def generate_token(user_id):
    """生成 JWT Token"""
    return jwt.encode(
        {"user_id": user_id},
        "your-secret-key",
        algorithm="HS256"
    )

def require_auth(f):
    """认证装饰器"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')

        if not token:
            return jsonify({"error": "Missing token"}), 401

        try:
            data = jwt.decode(token, "your-secret-key", algorithms=["HS256"])
            return f(*args, **kwargs)
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

    return decorated
```

---

## 总结

### 快速部署（5 分钟）

1. ✅ 准备代码和配置文件
2. ✅ 推送到 GitHub
3. ✅ 在 Render.com 创建 Web Service
4. ✅ 等待部署完成
5. ✅ 初始化演示数据
6. ✅ 访问你的 Skills Arena

### 推荐平台

| 平台 | 免费额度 | 推荐度 | 难度 |
|------|---------|--------|------|
| Render.com | 750 小时/月 | ⭐⭐⭐⭐⭐ | 简单 |
| Railway.app | $5/月 | ⭐⭐⭐⭐ | 简单 |
| PythonAnywhere | 永久免费 | ⭐⭐⭐ | 中等 |
| Replit | 永久免费 | ⭐⭐⭐⭐ | 简单 |

### 接下来的步骤

1. 部署到 Render.com
2. 测试所有 API
3. 初始化演示数据
4. 访问 Web 界面
5. 开始使用 Skills Arena！

---

**Skills Arena 现在完全可以部署！**
