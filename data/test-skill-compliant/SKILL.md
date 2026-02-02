---
name: data-analyzer-compliant
description: "符合 agentskills.io 规范的安全数据分析工具"
version: "1.0.0"
author: "Data Science Team"
tags: ["data-analysis", "compliant", "secure"]
---

# Data Analyzer - Compliant Version

## 符合规范的特性

✅ 无硬编码依赖  
✅ 无安全风险  
✅ 使用环境变量配置  
✅ 完整的 SKILL.md 文档  
✅ 标准文件结构  

## 环境变量配置

```bash
export DATA_ANALYZER_API_HOST="https://api.example.com"
export DATA_ANALYZER_API_KEY="your-api-key-here"
export DATA_ANALYZER_DB_URL="postgresql://user:pass@host:5432/db"
```

## 文件结构

```
data-analyzer-compliant/
├── SKILL.md
├── scripts/
│   └── data_analyzer.py
└── references/
```

## 最佳实践

1. **配置管理**：使用环境变量，避免硬编码
2. **安全编程**：使用 ast.literal_eval 替代 eval
3. **输入验证**：验证文件路径和用户输入
4. **错误处理**：清晰的错误消息和异常处理
