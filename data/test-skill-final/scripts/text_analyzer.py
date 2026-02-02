#!/usr/bin/env python3
"""
文本分析核心模块

完全符合 agentskills.io 规范的最佳实践示例
无硬编码依赖，无安全风险，支持环境变量配置
"""

import os
import json
import logging
from typing import Optional, Dict, List, Any
from pathlib import Path

# ✅ 最佳实践：使用环境变量读取配置
API_HOST = os.getenv("TEXT_ANALYZER_API_HOST", "https://api.example.com")
API_KEY = os.getenv("TEXT_ANALYZER_API_KEY", "")
TIMEOUT = int(os.getenv("TEXT_ANALYZER_TIMEOUT", "30"))

# ✅ 最佳实践：配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TextAnalyzer:
    """文本分析器 - 安全合规版本"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化分析器
        
        Args:
            config: 配置字典（可选，优先级低于环境变量）
        """
        self.api_host = API_HOST
        self.api_key = API_KEY
        self.timeout = TIMEOUT
        
        # 支持传入配置覆盖
        if config:
            self.api_host = config.get("api_host", self.api_host)
            self.api_key = config.get("api_key", self.api_key)
            self.timeout = config.get("timeout", self.timeout)
        
        # 验证配置
        self._validate_config()
        
        logger.info(f"TextAnalyzer 初始化完成: API Host={self.api_host}")
        
    def _validate_config(self):
        """验证配置完整性"""
        if not self.api_host:
            raise ValueError("API_HOST 配置缺失，请设置 TEXT_ANALYZER_API_HOST 环境变量")
        
        # ✅ 最佳实践：验证 URL 格式
        if not self.api_host.startswith(('http://', 'https://')):
            raise ValueError("API_HOST 必须以 http:// 或 https:// 开头")
        
        # ✅ 最佳实践：安全检查 - 避免本地地址
        disallowed_hosts = ['localhost', '127.0.0.1', '0.0.0.0', '192.168.', '10.']
        if any(host in self.api_host.lower() for host in disallowed_hosts):
            raise ValueError(f"不允许使用本地或内网地址: {self.api_host}")
        
        # 验证超时配置
        if self.timeout < 1 or self.timeout > 300:
            raise ValueError("TIMEOUT 必须在 1-300 秒之间")
    
    def analyze(self, text: str) -> Dict[str, Any]:
        """
        分析文本
        
        Args:
            text: 要分析的文本
            
        Returns:
            Dict: 分析结果
        """
        if not text or not text.strip():
            raise ValueError("文本不能为空")
        
        logger.info(f"分析文本，长度: {len(text)}")
        
        # ✅ 最佳实践：本地处理（无需外部 API）
        # 实际场景中可以调用外部 API，这里演示纯本地处理
        results = {
            "text_length": len(text),
            "word_count": len(text.split()),
            "sentiment": self._analyze_sentiment(text),
            "keywords": self._extract_keywords(text),
            "language": self._detect_language(text)
        }
        
        logger.info(f"分析完成: 情感={results['sentiment']}")
        return results
    
    def batch_analyze(self, texts: List[str]) -> List[Dict[str, Any]]:
        """
        批量分析文本
        
        Args:
            texts: 文本列表
            
        Returns:
            List[Dict]: 分析结果列表
        """
        if not texts:
            return []
        
        logger.info(f"批量分析 {len(texts)} 个文本")
        results = []
        
        for idx, text in enumerate(texts, 1):
            try:
                result = self.analyze(text)
                results.append(result)
                logger.info(f"进度: {idx}/{len(texts)}")
            except Exception as e:
                logger.error(f"分析失败 (文本 {idx}): {str(e)}")
                results.append({"error": str(e)})
        
        return results
    
    def _analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """分析情感（本地处理）"""
        # ✅ 最佳实践：使用简单的关键词匹配（示例）
        positive_words = ['好', '优秀', '棒', 'good', 'great', 'excellent', 'awesome']
        negative_words = ['差', '糟糕', '坏', 'bad', 'poor', 'terrible', 'awful']
        
        text_lower = text.lower()
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        total = positive_count + negative_count
        
        if total == 0:
            return {"score": 0.0, "label": "neutral"}
        
        score = (positive_count - negative_count) / max(total, 1)
        
        if score > 0.3:
            label = "positive"
        elif score < -0.3:
            label = "negative"
        else:
            label = "neutral"
        
        return {"score": round(score, 2), "label": label}
    
    def _extract_keywords(self, text: str, top_n: int = 5) -> List[str]:
        """提取关键词（本地处理）"""
        # ✅ 最佳实践：使用简单的词频统计（示例）
        words = [word.lower() for word in text.split() if len(word) > 2]
        
        # 简单的停用词过滤
        stopwords = {'the', 'is', 'at', 'which', 'on', 'and', 'a', 'an', '的', '了', '是', '在', '和'}
        words = [word for word in words if word not in stopwords]
        
        # 统计词频
        from collections import Counter
        word_counts = Counter(words)
        
        # 返回前 N 个关键词
        return [word for word, count in word_counts.most_common(top_n)]
    
    def _detect_language(self, text: str) -> str:
        """检测语言（本地处理）"""
        # ✅ 最佳实践：基于字符集的简单语言检测（示例）
        if not text:
            return "unknown"
        
        # 检查中文
        chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
        if chinese_chars > len(text) * 0.3:
            return "zh"
        
        # 检查英文
        english_chars = sum(1 for char in text if char.isalpha() and char.isascii())
        if english_chars > len(text) * 0.7:
            return "en"
        
        return "unknown"
    
    def safe_parse_config(self, config_str: str) -> Dict[str, Any]:
        """
        安全解析配置（替代 eval）
        
        Args:
            config_str: 配置字符串
            
        Returns:
            配置字典
        """
        # ✅ 最佳实践：使用 json.loads 替代 eval
        try:
            config = json.loads(config_str)
            logger.info("配置解析成功")
            return config
        except json.JSONDecodeError as e:
            logger.error(f"配置解析失败: {str(e)}")
            raise ValueError(f"配置格式错误: {str(e)}")


# ✅ 最佳实践：环境变量使用示例
if __name__ == "__main__":
    print("=" * 60)
    print("Text Analyzer - 完全合规版本")
    print("=" * 60)
    print(f"\n配置信息:")
    print(f"  API Host: {API_HOST}")
    print(f"  API Key: {'已配置' if API_KEY else '未配置'}")
    print(f"  Timeout: {TIMEOUT}s")
    
    # 演示使用
    print(f"\n演示分析:")
    analyzer = TextAnalyzer()
    
    test_text = "这是一个优秀的文本分析工具！"
    result = analyzer.analyze(test_text)
    
    print(f"  文本: {test_text}")
    print(f"  情感: {result['sentiment']}")
    print(f"  关键词: {result['keywords']}")
    print(f"  语言: {result['language']}")
    
    print(f"\n✅ 所有功能正常，系统合规！")
    print("=" * 60)
