# Skills Arena 生产级系统

> 基于 agentskills.io 规范的 Skills 擂台评比平台 - 生产就绪版本

## 🚀 核心特性

### 1. 用户便捷上传
- **Web 界面上传**：支持通过浏览器上传 ZIP 格式 Skill 包
- **命令行上传**：提供 CLI 工具支持批量上传
- **自动化验证**：上传即验证，实时反馈问题
- **智能处理**：自动解压、验证、归档

### 2. 自动化规范检测
- **agentskills.io 规范验证**：确保符合官方标准
- **硬编码依赖检测**：识别本地地址、固定网址、硬编码密钥
- **安全风险扫描**：检测 eval()、exec() 等危险函数
- **分级评分系统**：EXCELLENT / GOOD / ACCEPTABLE 三级评级
- **详细问题报告**：定位到具体代码行，提供修复建议

### 3. 生产级架构
- **模块化设计**：验证器、上传器、服务器独立解耦
- **错误恢复机制**：上传失败自动清理临时文件
- **并发处理支持**：支持多个 Skill 同时上传验证
- **日志完整记录**：所有操作可追溯

## 📁 系统架构

```
skills-arena/
├── SKILL.md                          # Skills Arena 文档
├── README.md                         # 本文件
├── scripts/                          # 核心脚本目录
│   ├── arena_manager.py             # 擂台管理器
│   ├── web_server.py                # 原 Web 服务器（演示版）
│   ├── production_web_server.py     # ⭐ 生产级 Web 服务器
│   ├── init_demo.py                 # 演示数据初始化
│   ├── skill_validator.py           # ⭐ 技能规范验证器
│   └── skill_uploader.py            # ⭐ 技能上传处理器
└── data/                             # 数据持久化目录
    ├── scenarios/                    # 评测场景
    ├── skills/                       # Skills 元数据和代码
    ├── reviews/                      # 用户评价
    ├── leaderboards/                 # 排行榜
    └── uploads/                      # 上传记录
```

## 🔧 快速开始

### 1. 环境要求

- Python 3.7+
- Flask（生产服务器）
- requests（网络请求）

### 2. 安装依赖

```bash
cd skills-arena
pip install flask requests
```

### 3. 初始化演示数据（可选）

```bash
cd scripts
python3 init_demo.py
```

### 4. 启动生产服务器

```bash
cd scripts
python3 production_web_server.py
```

服务器将在 `http://localhost:5000` 启动

## 📤 上传 Skills

### 方式一：Web 界面上传

1. 访问 `http://localhost:5000`
2. 点击"上传 Skill"按钮
3. 选择 ZIP 格式的 Skill 包
4. 系统自动验证并显示报告
5. 验证通过后自动上架

### 方式二：命令行上传

```bash
# 上传 Skill 目录
cd scripts
python3 skill_uploader.py ../path/to/your-skill --name "your-skill-name"

# 上传 ZIP 包
python3 skill_uploader.py ../path/to/your-skill.zip --name "your-skill-name"
```

## 🔍 验证规范

### 验证维度

| 检查项 | 说明 | 失败影响 |
|--------|------|----------|
| 文件结构 | SKILL.md、scripts/、references/ | ❌ 阻止上传 |
| SKILL.md | name、description 等字段 | ❌ 阻止上传 |
| 硬编码依赖 | 本地地址、固定网址、硬编码密钥 | ⚠️ 降低评分 |
| 安全风险 | eval()、exec() 等危险函数 | ⚠️ 降低评分 |
| 脚本可执行性 | Python 代码语法检查 | ❌ 阻止上传 |

### 评分标准

- **🌟 EXCELLENT**（100分）：完全符合规范，无任何问题
- **✅ GOOD**（75-99分）：轻微问题，符合上架标准
- **⚠️ ACCEPTABLE**（50-74分）：存在严重问题，需修复

### 独立使用验证工具

```bash
# 验证 Skill 目录
python3 skill_validator.py ../path/to/skill

# 验证 ZIP 包
python3 skill_validator.py --zip ../path/to/skill.zip

# 生成详细报告
python3 skill_validator.py ../path/to/skill --report validation_report.md
```

## ⚠️ 硬编码依赖检测

### 检测内容

1. **本地地址**
   - `localhost:8080`
   - `127.0.0.1:5000`
   - `0.0.0.0:3000`

2. **内网地址**
   - `192.168.x.x`
   - `10.x.x.x`
   - `172.16-31.x.x`

3. **硬编码密钥**
   - `API_KEY = "sk-12345678"`
   - `PASSWORD = "secret123"`
   - `TOKEN = "token_xxx"`

4. **固定网址**
   - `http://10.0.1.50`
   - `https://internal.company.com`

### 修复建议

```python
# ❌ 错误做法
API_HOST = "http://localhost:8080"
API_KEY = "sk-1234567890abcdef1234567890abcdef"

# ✅ 正确做法
import os
API_HOST = os.getenv("API_HOST", "https://api.example.com")
API_KEY = os.getenv("API_KEY", "")
```

## 🔒 安全风险检测

### 高风险模式

1. **危险函数**
   - `eval()`: 动态执行代码
   - `exec()`: 执行任意代码
   - `subprocess.Popen`: 命令注入风险
   - `__import__()`: 动态导入风险

2. **文件操作**
   - 无限制的文件读写
   - 非法路径遍历

3. **网络请求**
   - 未验证的外部请求
   - 不安全的 HTTP 连接

### 修复建议

```python
# ❌ 危险做法
result = eval(user_input)
exec(user_code)

# ✅ 安全做法
import json
result = json.loads(user_input)  # 使用 JSON 解析

# 或使用安全的配置管理
from configparser import ConfigParser
config = ConfigParser()
config.read('config.ini')
result = config.get('section', 'option')
```

## 📊 API 端点

### Web 界面

- `GET /` - 主页
- `GET /skills` - Skills 列表
- `GET /leaderboards` - 排行榜

### 上传 API

- `POST /api/upload` - 上传 Skill 包
  - 参数：`skill_file` (ZIP 文件)
  - 返回：上传结果和验证报告

### 验证 API

- `POST /api/validate` - 验证 Skill
  - 参数：`skill_path` 或 `skill_zip`
  - 返回：验证报告

## 🧪 测试 Skill 包

系统包含三个测试 Skill 包用于演示：

### 1. test-skill-package（问题版本）
- **状态**：⚠️ ACCEPTABLE（50/100）
- **问题**：5 个硬编码依赖，2 个安全风险
- **用途**：演示问题检测和错误报告

### 2. test-skill-compliant（合规版本）
- **状态**：✅ GOOD（75/100）
- **问题**：1 个安全风险，1 个警告
- **用途**：演示分级评分

### 3. test-skill-final（完全合规）
- **状态**：🌟 EXCELLENT（100/100）
- **问题**：无
- **用途**：演示完美合规标准

### 运行测试

```bash
# 测试问题版本
python3 skill_validator.py ../data/test-skill-package

# 测试合规版本
python3 skill_validator.py ../data/test-skill-compliant

# 测试完全合规版本
python3 skill_validator.py ../data/test-skill-final
```

## 📝 创建符合规范的 Skill

### 最小结构

```
my-skill/
├── SKILL.md          # 必需：技能文档
├── scripts/          # 必需：脚本目录
│   └── main.py     # 必需：至少一个 Python 脚本
└── references/      # 可选：参考资源目录
    └── template.md # 可选：模板文件
```

### SKILL.md 模板

```markdown
# My Skill

技能描述

---

## Dependencies

依赖列表

## Usage

使用说明
```

### 代码规范

```python
#!/usr/bin/env python3
"""
My Skill - 完全合规版本
"""

import os
import json

# ✅ 使用环境变量
API_HOST = os.getenv("MY_SKILL_API_HOST", "https://api.example.com")

def main():
    """主函数"""
    # ✅ 使用 json.loads 替代 eval
    config = json.loads('{"key": "value"}')
    
    # 业务逻辑
    pass

if __name__ == "__main__":
    main()
```

## 🛠️ 故障排查

### 上传失败

**问题**：上传 ZIP 文件时解压失败

**解决方案**：
- 确保文件格式为 ZIP
- 检查文件是否损坏
- 确认文件大小在限制范围内

### 验证不通过

**问题**：验证报告显示硬编码依赖

**解决方案**：
- 检查代码中的固定地址、密钥
- 使用环境变量替换硬编码值
- 参考测试包中的最佳实践

### 服务器启动失败

**问题**：Flask 服务器无法启动

**解决方案**：
- 确认已安装 Flask：`pip install flask`
- 检查端口 5000 是否被占用
- 查看错误日志获取详细信息

## 📈 性能优化

1. **并发验证**：支持多个 Skill 同时验证
2. **缓存机制**：缓存已验证的 Skill 信息
3. **增量验证**：仅重新验证修改的部分
4. **异步处理**：使用 Celery 实现后台任务

## 🔐 安全建议

1. **输入验证**：严格验证上传的 ZIP 文件
2. **沙箱执行**：在隔离环境中测试 Skill
3. **限流保护**：防止恶意大量上传
4. **日志审计**：记录所有操作用于审计

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

---

**Skills Arena Team** - 让 Skills 开发更规范、更安全、更高效

如有问题，请访问 [agentskills.io](https://agentskills.io) 或提交 Issue。
