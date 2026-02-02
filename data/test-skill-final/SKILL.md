---
name: text-analyzer-pro
description: "符合 agentskills.io 规范的文本分析工具，支持多语言文本处理和情感分析"
version: "1.0.0"
author: "NLP Team"
tags: ["text-analysis", "nlp", "sentiment-analysis", "compliant"]
---

# Text Analyzer Pro

## 符合规范的特性

✅ **完全合规**：符合 agentskills.io 规范要求  
✅ **无硬编码依赖**：所有配置通过环境变量或配置文件管理  
✅ **无安全风险**：不使用 eval、exec 等危险函数  
✅ **标准结构**：包含 SKILL.md、scripts/、references/ 目录  
✅ **跨平台兼容**：支持 Windows、Linux、macOS  

## 功能特性

- 多语言文本分析
- 情感分析和情感评分
- 关键词提取
- 文本摘要生成
- 支持批量处理
- RESTful API 接口

## 环境变量配置

使用前需要设置以下环境变量：

```bash
# API 配置
export TEXT_ANALYZER_API_HOST="https://api.example.com"
export TEXT_ANALYZER_API_KEY="your-api-key-here"
export TEXT_ANALYZER_TIMEOUT=30

# 数据库配置（可选）
export TEXT_ANALYZER_DB_URL="postgresql://user:password@host:5432/db"

# 缓存配置（可选）
export TEXT_ANALYZER_CACHE_TTL=3600
export TEXT_ANALYZER_CACHE_SIZE=1000
```

## 安装和部署

### 环境要求

- Python 3.8+
- pip 包管理器

### 安装步骤

```bash
# 1. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入配置

# 4. 运行测试
python -m pytest tests/

# 5. 启动服务
python scripts/server.py
```

## API 使用

### 基本用法

```python
from text_analyzer import TextAnalyzer

# 初始化分析器（自动读取环境变量）
analyzer = TextAnalyzer()

# 分析文本
result = analyzer.analyze("这是一段需要分析的文本")

# 批量分析
texts = ["文本1", "文本2", "文本3"]
results = analyzer.batch_analyze(texts)
```

### 配置覆盖

```python
# 使用自定义配置覆盖环境变量
config = {
    "api_host": "https://custom-api.example.com",
    "api_key": "custom-key",
    "timeout": 60
}
analyzer = TextAnalyzer(config=config)
```

## 最佳实践

### 1. 配置管理

✅ **推荐做法**：使用环境变量
```python
api_key = os.getenv("API_KEY")
```

❌ **避免做法**：硬编码配置
```python
api_key = "sk-1234567890abcdef"  # 不安全
```

### 2. 安全编程

✅ **推荐做法**：使用安全的 JSON 解析
```python
import json
config = json.loads(config_string)
```

❌ **避免做法**：使用危险的 eval
```python
config = eval(config_string)  # 安全风险
```

### 3. 错误处理

✅ **推荐做法**：捕获特定异常
```python
try:
    result = api_call()
except TimeoutError:
    # 处理超时
    pass
except APIError as e:
    # 处理 API 错误
    logger.error(f"API 错误: {e}")
```

### 4. 日志记录

✅ **推荐做法**：使用结构化日志
```python
import logging

logger = logging.getLogger(__name__)
logger.info("分析文本", extra={"text_length": len(text)})
```

## 文件结构

```
text-analyzer-pro/
├── SKILL.md                 # 技能描述文件
├── requirements.txt         # Python 依赖
├── .env.example            # 环境变量示例
├── scripts/
│   ├── __init__.py
│   ├── text_analyzer.py     # 主模块
│   ├── sentiment.py         # 情感分析
│   ├── keywords.py          # 关键词提取
│   └── utils.py             # 工具函数
└── references/
    ├── api-specs.md         # API 规范
    ├── examples/
    │   ├── basic-usage.py   # 基本使用示例
    │   └── advanced-usage.py # 高级用法示例
    └── schemas/
        └── request-schema.json # 请求模式定义
```

## 测试

运行测试套件：

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_analyzer.py

# 生成覆盖率报告
pytest --cov=text_analyzer --cov-report=html
```

## 性能优化

- 使用缓存机制减少重复分析
- 批量处理提升吞吐量
- 异步 API 调用提升响应速度
- 连接池管理数据库连接

## 贡献指南

欢迎贡献代码！请遵循以下流程：

1. Fork 本项目
2. 创建特性分支
3. 提交更改（遵循 conventional commits 规范）
4. 推送到分支
5. 创建 Pull Request

### 代码规范

- 遵循 PEP 8 代码风格
- 使用类型提示
- 编写单元测试
- 添加文档字符串

## 许可证

MIT License

## 联系方式

- 项目主页: https://github.com/example/text-analyzer-pro
- 问题反馈: https://github.com/example/text-analyzer-pro/issues
- 邮箱: nlp-team@example.com

## 更新日志

### v1.0.0 (2024-01-01)

- 初始版本发布
- 基础文本分析功能
- 情感分析支持
- 关键词提取
- API 接口
