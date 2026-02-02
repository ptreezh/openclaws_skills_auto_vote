#!/usr/bin/env python3
"""
数据分析核心模块

符合 agentskills.io 规范的最佳实践示例
无硬编码依赖，无安全风险
"""

import os
import json
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any

# ✅ 最佳实践：使用环境变量读取配置
API_HOST = os.getenv("DATA_ANALYZER_API_HOST", "https://api.example.com")
API_KEY = os.getenv("DATA_ANALYZER_API_KEY", "")
DB_CONNECTION = os.getenv("DATA_ANALYZER_DB_URL", "")

class DataAnalyzer:
    """数据分析器 - 安全合规版本"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化分析器
        
        Args:
            config: 配置字典（可选，优先级低于环境变量）
        """
        self.api_host = API_HOST
        self.api_key = API_KEY
        self.db_connection = DB_CONNECTION
        
        # 支持传入配置覆盖
        if config:
            self.api_host = config.get("api_host", self.api_host)
            self.api_key = config.get("api_key", self.api_key)
            self.db_connection = config.get("db_connection", self.db_connection)
        
        # 验证配置
        self._validate_config()
        
    def _validate_config(self):
        """验证配置完整性"""
        if not self.api_host:
            raise ValueError("API_HOST 配置缺失，请设置 DATA_ANALYZER_API_HOST 环境变量")
        
        # ✅ 最佳实践：验证 URL 格式
        if not self.api_host.startswith(('http://', 'https://')):
            raise ValueError("API_HOST 必须以 http:// 或 https:// 开头")
        
        # ✅ 最佳实践：安全检查 - 避免本地地址
        disallowed_hosts = ['localhost', '127.0.0.1', '0.0.0.0']
        if any(host in self.api_host.lower() for host in disallowed_hosts):
            raise ValueError(f"不允许使用本地地址作为 API_HOST: {self.api_host}")
        
    def load_data(self, file_path: str):
        """
        加载数据
        
        Args:
            file_path: 数据文件路径
            
        Returns:
            DataFrame: 加载的数据
        """
        # ✅ 最佳实践：安全文件读取
        # 验证文件路径安全性
        abs_path = os.path.abspath(file_path)
        if not abs_path.startswith(os.getcwd()):
            raise ValueError("不允许读取工作目录外的文件")
        
        # 读取数据
        try:
            if file_path.endswith('.csv'):
                return pd.read_csv(file_path)
            elif file_path.endswith('.json'):
                return pd.read_json(file_path)
            else:
                raise ValueError(f"不支持的文件格式: {file_path}")
        except Exception as e:
            raise ValueError(f"数据加载失败: {str(e)}")
    
    def analyze(self, data: pd.DataFrame, analysis_type: str = "basic"):
        """
        分析数据
        
        Args:
            data: 要分析的数据
            analysis_type: 分析类型
            
        Returns:
            Dict: 分析结果
        """
        # ✅ 最佳实践：安全的 API 调用
        if not self.api_key:
            return self._analyze_locally(data, analysis_type)
        
        # 使用外部 API（仅演示，实际应使用 requests 等 HTTP 客户端）
        return {
            "analysis_type": analysis_type,
            "rows": len(data),
            "columns": len(data.columns),
            "summary": data.describe().to_dict(),
            "api_host": self.api_host  # 仅用于演示，生产环境不应暴露
        }
    
    def _analyze_locally(self, data: pd.DataFrame, analysis_type: str) -> Dict:
        """本地数据分析（无需外部 API）"""
        results = {
            "analysis_type": analysis_type,
            "rows": len(data),
            "columns": len(data.columns),
            "summary": data.describe().to_dict(),
            "source": "local"
        }
        return results
    
    def execute_safe_expression(self, expression: str, context: Dict[str, Any]) -> Any:
        """
        安全执行表达式（替代 eval/exec）
        
        Args:
            expression: 要执行的表达式
            context: 执行上下文
            
        Returns:
            执行结果
        """
        # ✅ 最佳实践：使用 ast.literal_eval 替代 eval
        import ast
        
        try:
            # 仅支持字面量，不支持任意代码执行
            return ast.literal_eval(expression)
        except (ValueError, SyntaxError):
            raise ValueError("仅支持字面量表达式，不支持任意代码执行")
    
    def process_config(self, config_str: str) -> Dict[str, Any]:
        """
        安全处理配置（替代 eval/exec）
        
        Args:
            config_str: 配置字符串
            
        Returns:
            配置字典
        """
        # ✅ 最佳实践：使用 json.load 替代 eval
        try:
            return json.loads(config_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"配置格式错误: {str(e)}")


# ✅ 最佳实践：环境变量使用示例
if __name__ == "__main__":
    print("Data Analyzer - 安全合规版本")
    print(f"API Host: {API_HOST}")
    print(f"API Key: {'已配置' if API_KEY else '未配置'}")
    print(f"Database: {'已配置' if DB_CONNECTION else '未配置'}")
