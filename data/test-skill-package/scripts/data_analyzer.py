#!/usr/bin/env python3
"""
数据分析核心模块

演示包含硬编码依赖和安全风险的示例代码
"""

import os
import json
import pandas as pd
import numpy as np

# ⚠️ 演示：硬编码依赖（会被检测到）
API_HOST = "http://localhost:8080"  # 本地地址硬编码
API_KEY = "sk-1234567890abcdef1234567890abcdef"  # 硬编码密钥
DB_CONNECTION = "postgresql://user:password@192.168.1.100:5432/db"  # 内网地址

class DataAnalyzer:
    """数据分析器"""
    
    def __init__(self):
        self.api_host = API_HOST
        self.api_key = API_KEY
        
    def load_data(self, file_path: str):
        """加载数据"""
        # ⚠️ 演示：危险函数使用（会被检测到）
        user_input = input("请输入配置: ")
        config = eval(user_input)  # 危险函数 eval
        
        # 读取数据
        return pd.read_csv(file_path)
    
    def analyze(self, data):
        """分析数据"""
        # 使用内网 API 服务
        import requests
        response = requests.post(
            f"http://10.0.1.50:5000/analyze",  # 内网地址
            json={"data": data.to_dict()},
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        return response.json()
    
    def execute_code(self, code: str):
        """执行代码 - ⚠️ 危险函数"""
        exec(code)  # 危险函数 exec
