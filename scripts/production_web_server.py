#!/usr/bin/env python3
"""
生产级 Skills Arena Web 服务器

包含完整的 Skill 上传、验证、展示和管理功能
"""

from flask import Flask, jsonify, request, render_template_string, send_file
import json
import os
import sys
from pathlib import Path
from datetime import datetime
import tempfile
import shutil

# 导入管理器
sys.path.insert(0, str(Path(__file__).parent))
from arena_manager import ArenaManager
from skill_validator import SkillValidator
from skill_uploader import SkillUploader

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB 最大上传

# 初始化管理器
data_dir = Path(__file__).parent.parent / "data"
manager = ArenaManager(data_dir=str(data_dir))
uploader = SkillUploader(
    upload_dir=str(data_dir / "uploads"), skills_dir=str(data_dir / "skills")
)

# 生产级 HTML 模板
PRODUCTION_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Skills Arena - 生产级 Skills 上架平台</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #eee;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }

        /* 导航栏 */
        .navbar {
            background: rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(10px);
            padding: 20px 0;
            margin-bottom: 30px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }

        .navbar-content {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .logo {
            font-size: 24px;
            font-weight: bold;
            background: linear-gradient(90deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .nav-tabs {
            display: flex;
            gap: 10px;
        }

        .nav-tab {
            padding: 10px 20px;
            background: rgba(255, 255, 255, 0.1);
            border: none;
            color: #fff;
            cursor: pointer;
            border-radius: 8px;
            transition: all 0.3s;
        }

        .nav-tab:hover {
            background: rgba(255, 255, 255, 0.2);
        }

        .nav-tab.active {
            background: linear-gradient(90deg, #667eea, #764ba2);
        }

        /* 标签页内容 */
        .tab-content {
            display: none;
        }

        .tab-content.active {
            display: block;
        }

        /* 卡片样式 */
        .card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border-radius: 16px;
            padding: 30px;
            margin-bottom: 20px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .card-header {
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }

        .card-title {
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 10px;
        }

        .card-subtitle {
            color: #aaa;
            font-size: 14px;
        }

        /* 上传区域 */
        .upload-zone {
            border: 2px dashed rgba(255, 255, 255, 0.3);
            border-radius: 12px;
            padding: 60px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
        }

        .upload-zone:hover {
            border-color: #667eea;
            background: rgba(102, 126, 234, 0.1);
        }

        .upload-zone.dragover {
            border-color: #667eea;
            background: rgba(102, 126, 234, 0.2);
        }

        .upload-icon {
            font-size: 48px;
            margin-bottom: 20px;
        }

        .upload-text {
            font-size: 18px;
            margin-bottom: 10px;
        }

        .upload-hint {
            color: #888;
            font-size: 14px;
        }

        /* 表单元素 */
        .form-group {
            margin-bottom: 20px;
        }

        .form-label {
            display: block;
            margin-bottom: 8px;
            font-weight: 500;
        }

        .form-input {
            width: 100%;
            padding: 12px 16px;
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 8px;
            color: #fff;
            font-size: 14px;
        }

        .form-input:focus {
            outline: none;
            border-color: #667eea;
        }

        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.3s;
        }

        .btn-primary {
            background: linear-gradient(90deg, #667eea, #764ba2);
            color: #fff;
        }

        .btn-primary:hover {
            opacity: 0.9;
            transform: translateY(-2px);
        }

        .btn-secondary {
            background: rgba(255, 255, 255, 0.1);
            color: #fff;
        }

        .btn-secondary:hover {
            background: rgba(255, 255, 255, 0.2);
        }

        /* 验证结果 */
        .validation-result {
            margin-top: 20px;
            padding: 20px;
            border-radius: 12px;
            display: none;
        }

        .validation-result.show {
            display: block;
        }

        .validation-result.success {
            background: rgba(76, 175, 80, 0.2);
            border: 1px solid rgba(76, 175, 80, 0.5);
        }

        .validation-result.error {
            background: rgba(244, 67, 54, 0.2);
            border: 1px solid rgba(244, 67, 54, 0.5);
        }

        .validation-result.warning {
            background: rgba(255, 193, 7, 0.2);
            border: 1px solid rgba(255, 193, 7, 0.5);
        }

        .score-display {
            font-size: 48px;
            font-weight: bold;
            margin-bottom: 10px;
        }

        .score-excellent {
            color: #4caf50;
        }

        .score-good {
            color: #2196f3;
        }

        .score-acceptable {
            color: #ff9800;
        }

        .score-rejected {
            color: #f44336;
        }

        /* 问题列表 */
        .issue-list {
            margin-top: 15px;
        }

        .issue-item {
            padding: 12px;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 8px;
            margin-bottom: 10px;
        }

        .issue-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }

        .issue-type {
            font-weight: bold;
        }

        .issue-severity {
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
        }

        .issue-severity.critical {
            background: rgba(244, 67, 54, 0.3);
            color: #f44336;
        }

        .issue-severity.high {
            background: rgba(255, 152, 0, 0.3);
            color: #ff9800;
        }

        .issue-severity.medium {
            background: rgba(255, 193, 7, 0.3);
            color: #ffc107;
        }

        .issue-severity.low {
            background: rgba(76, 175, 80, 0.3);
            color: #4caf50;
        }

        .issue-description {
            color: #aaa;
            font-size: 14px;
        }

        /* 技能列表 */
        .skill-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
        }

        .skill-card {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 20px;
            transition: all 0.3s;
        }

        .skill-card:hover {
            transform: translateY(-5px);
            border-color: #667eea;
        }

        .skill-name {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
        }

        .skill-meta {
            color: #888;
            font-size: 13px;
            margin-bottom: 15px;
        }

        .skill-score {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 15px;
        }

        .score-badge {
            padding: 6px 12px;
            border-radius: 6px;
            font-weight: bold;
            font-size: 14px;
        }

        .score-badge.excellent {
            background: rgba(76, 175, 80, 0.3);
            color: #4caf50;
        }

        .score-badge.good {
            background: rgba(33, 150, 243, 0.3);
            color: #2196f3;
        }

        .score-badge.acceptable {
            background: rgba(255, 152, 0, 0.3);
            color: #ff9800;
        }

        .score-badge.rejected {
            background: rgba(244, 67, 54, 0.3);
            color: #f44336;
        }

        /* 统计数据 */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .stat-card {
            background: rgba(255, 255, 255, 0.05);
            padding: 20px;
            border-radius: 12px;
            text-align: center;
        }

        .stat-value {
            font-size: 36px;
            font-weight: bold;
            background: linear-gradient(90deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .stat-label {
            color: #888;
            font-size: 14px;
            margin-top: 5px;
        }

        /* 加载动画 */
        .loading {
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 40px;
        }

        .spinner {
            border: 3px solid rgba(255, 255, 255, 0.1);
            border-top-color: #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        /* 进度条 */
        .progress-bar {
            width: 100%;
            height: 8px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
            overflow: hidden;
            margin-bottom: 10px;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            transition: width 0.3s;
        }

        .progress-text {
            text-align: center;
            color: #888;
            font-size: 13px;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- 导航栏 -->
        <nav class="navbar" style="position: sticky; top: 0; z-index: 100; background: rgba(26, 26, 46, 0.95); backdrop-filter: blur(10px);">
            <div class="navbar-content">
                <div class="logo" style="display: flex; align-items: center; gap: 10px;">
                    <span style="font-size: 28px;">🦞</span>
                    <span style="font-size: 22px;">Skills Arena</span>
                </div>
                <div class="nav-tabs">
                    <button class="nav-tab active" onclick="switchTab('upload')">📤 上传 Skill</button>
                    <button class="nav-tab" onclick="switchTab('validate')">✅ 规范验证</button>
                    <button class="nav-tab" onclick="switchTab('skills')">📋 Skills 列表</button>
                    <button class="nav-tab" onclick="switchTab('arena')">🏆 擂台评比</button>
                </div>
            </div>
        </nav>

        <!-- 操作区域 -->
        <div id="tab-upload" class="tab-content active">
            <div class="card">
                <div class="card-header">
                    <h2 class="card-title">📤 上传 Skill</h2>
                    <p class="card-subtitle">上传你的 Skill 包到平台，系统将自动验证规范合规性</p>
                </div>

                <div class="upload-zone" id="uploadZone">
                    <div class="upload-icon">📦</div>
                    <div class="upload-text">拖拽文件到此处或点击选择</div>
                    <div class="upload-hint">支持文件夹或 ZIP 文件，最大 50MB</div>
                </div>

                <input type="file" id="fileInput" style="display: none" webkitdirectory directory multiple>

                <div id="uploadProgress" style="display: none; margin-top: 20px;">
                    <div class="progress-bar">
                        <div class="progress-fill" id="progressFill" style="width: 0%"></div>
                    </div>
                    <div class="progress-text" id="progressText">准备上传...</div>
                </div>

                <div id="validationResult" class="validation-result"></div>
            </div>

            <div class="card">
                <div class="card-header">
                    <h3 class="card-title">📝 规范要求</h3>
                </div>
                <div style="color: #aaa;">
                    <p><strong>必需文件：</strong></p>
                    <ul style="margin-left: 20px; margin-bottom: 15px;">
                        <li>SKILL.md - 技能描述文件</li>
                        <li>scripts/ - 脚本目录</li>
                        <li>references/ - 参考资源目录</li>
                    </ul>
                    <p><strong>禁止事项：</strong></p>
                    <ul style="margin-left: 20px;">
                        <li>硬编码本地地址（localhost, 127.0.0.1）</li>
                        <li>硬编码内网 IP 地址</li>
                        <li>硬编码密钥、密码等敏感信息</li>
                        <li>使用 eval、exec 等危险函数</li>
                    </ul>
                </div>
            </div>
        </div>

        <!-- 验证页面 -->
        <div id="tab-validate" class="tab-content">
            <div class="card">
                <div class="card-header">
                    <h2 class="card-title">✅ 规范验证</h2>
                    <p class="card-subtitle">验证 Skill 包是否符合 agentskills.io 规范</p>
                </div>

                <div class="form-group">
                    <label class="form-label">Skill 路径</label>
                    <input type="text" class="form-input" id="validatePath" 
                           placeholder="输入 Skill 的本地路径或已上传的 Skill ID">
                </div>

                <button class="btn btn-primary" onclick="validateSkill()">开始验证</button>

                <div id="validationOutput" class="validation-result"></div>
            </div>
        </div>

        <!-- Skills 列表 -->
        <div id="tab-skills" class="tab-content">
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value" id="totalSkills">0</div>
                    <div class="stat-label">总 Skills 数</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="excellentSkills">0</div>
                    <div class="stat-label">优秀 (≥90分)</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="avgScore">0</div>
                    <div class="stat-label">平均合规分</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="totalIssues">0</div>
                    <div class="stat-label">总问题数</div>
                </div>
            </div>

            <div id="skillsList" class="skill-grid">
                <div class="loading">
                    <div class="spinner"></div>
                </div>
            </div>
        </div>

        <!-- 擂台评比 -->
        <div id="tab-arena" class="tab-content">
            <div class="card">
                <div class="card-header">
                    <h2 class="card-title">🏆 Skills 擂台</h2>
                    <p class="card-subtitle">查看各场景下 Skills 的评比结果</p>
                </div>
                <div id="arenaContent">
                    <div class="loading">
                        <div class="spinner"></div>
                    </div>
                </div>
            </div>
        </div>

        <!-- 首页横幅：平台理念和机制说明（操作区域下方） -->
        <div class="hero-banner" style="
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.12) 0%, rgba(118, 75, 162, 0.12) 100%);
            border-radius: 20px;
            padding: 35px;
            margin-top: 30px;
            border: 1px solid rgba(255, 255, 255, 0.08);
        ">
            <!-- 平台理念 -->
            <div style="text-align: center; margin-bottom: 35px;">
                <h1 style="
                    font-size: 38px;
                    font-weight: bold;
                    background: linear-gradient(90deg, #667eea, #764ba2);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    margin-bottom: 12px;
                ">🦞 Skills Arena</h1>
                <p style="font-size: 17px; color: #aaa; max-width: 600px; margin: 0 auto;">
                    智能体社会化协同过滤 + 联邦学习平台
                </p>
            </div>

            <!-- 三大核心概念 -->
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 35px;">
                <div style="
                    background: linear-gradient(135deg, rgba(102, 126, 234, 0.15), rgba(102, 126, 234, 0.05));
                    border-radius: 14px; padding: 22px 18px; text-align: center;
                    border: 1px solid rgba(102, 126, 234, 0.25);
                ">
                    <div style="font-size: 32px; margin-bottom: 8px;">🧬</div>
                    <h3 style="font-size: 16px; color: #667eea; margin-bottom: 6px; font-weight: 600;">协同进化</h3>
                    <p style="font-size: 12px; color: #888; line-height: 1.5;">
                        Skills 越用越聪明<br>集体智慧驱动持续进化
                    </p>
                </div>
                <div style="
                    background: linear-gradient(135deg, rgba(156, 39, 176, 0.15), rgba(118, 75, 162, 0.05));
                    border-radius: 14px; padding: 22px 18px; text-align: center;
                    border: 1px solid rgba(156, 39, 176, 0.25);
                ">
                    <div style="font-size: 32px; margin-bottom: 8px;">👥</div>
                    <h3 style="font-size: 16px; color: #9c27b0; margin-bottom: 6px; font-weight: 600;">社会化协同过滤</h3>
                    <p style="font-size: 12px; color: #888; line-height: 1.5;">
                        借鉴相似智能体经验<br>精准推荐最适合的 Skill
                    </p>
                </div>
                <div style="
                    background: linear-gradient(135deg, rgba(76, 175, 80, 0.15), rgba(76, 175, 80, 0.05));
                    border-radius: 14px; padding: 22px 18px; text-align: center;
                    border: 1px solid rgba(76, 175, 80, 0.25);
                ">
                    <div style="font-size: 32px; margin-bottom: 8px;">🔒</div>
                    <h3 style="font-size: 16px; color: #4caf50; margin-bottom: 6px; font-weight: 600;">隐私保护联邦学习</h3>
                    <p style="font-size: 12px; color: #888; line-height: 1.5;">
                        只传梯度，不传内容<br>敏感数据永不离开设备
                    </p>
                </div>
            </div>

            <!-- 核心机制流程图 - SVG -->
            <div style="
                background: rgba(0, 0, 0, 0.2);
                border-radius: 16px;
                padding: 25px;
                margin-bottom: 30px;
            ">
                <h3 style="text-align: center; font-size: 16px; color: #fff; margin-bottom: 20px;">
                    🔄 联邦学习核心机制
                </h3>
                
                <!-- SVG Flowchart -->
                <svg viewBox="0 0 800 200" style="width: 100%; max-width: 800px; display: block; margin: 0 auto;">
                    <defs>
                        <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="0%">
                            <stop offset="0%" style="stop-color:#667eea;stop-opacity:1" />
                            <stop offset="100%" style="stop-color:#764ba2;stop-opacity:1" />
                        </linearGradient>
                        <marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto" markerUnits="strokeWidth">
                            <path d="M0,0 L0,6 L9,3 z" fill="#667eea" />
                        </marker>
                    </defs>
                    
                    <rect x="20" y="60" width="160" height="80" rx="12" fill="rgba(102,126,234,0.2)" stroke="#667eea" stroke-width="2"/>
                    <text x="100" y="95" text-anchor="middle" fill="#fff" font-size="14" font-weight="600">🦞 智能体 A</text>
                    <text x="100" y="120" text-anchor="middle" fill="#888" font-size="11">使用 Skill</text>
                    
                    <line x1="180" y1="100" x2="240" y2="100" stroke="#667eea" stroke-width="2" marker-end="url(#arrow)"/>
                    
                    <rect x="250" y="60" width="160" height="80" rx="12" fill="rgba(76,175,80,0.2)" stroke="#4caf50" stroke-width="2"/>
                    <text x="330" y="95" text-anchor="middle" fill="#fff" font-size="14" font-weight="600">🛡️ 本地计算</text>
                    <text x="330" y="120" text-anchor="middle" fill="#888" font-size="11">生成梯度</text>
                    
                    <line x1="410" y1="100" x2="470" y2="100" stroke="#4caf50" stroke-width="2" marker-end="url(#arrow)"/>
                    
                    <rect x="480" y="60" width="160" height="80" rx="12" fill="rgba(255,152,0,0.2)" stroke="#ff9800" stroke-width="2"/>
                    <text x="560" y="95" text-anchor="middle" fill="#fff" font-size="14" font-weight="600">📊 上传梯度</text>
                    <text x="560" y="120" text-anchor="middle" fill="#888" font-size="11">只传统计</text>
                    
                    <line x1="640" y1="100" x2="700" y2="100" stroke="#ff9800" stroke-width="2" marker-end="url(#arrow)"/>
                    
                    <rect x="710" y="60" width="80" height="80" rx="12" fill="url(#grad1)" stroke="none"/>
                    <text x="750" y="95" text-anchor="middle" fill="#fff" font-size="14" font-weight="600">🧬 聚合</text>
                    <text x="750" y="120" text-anchor="middle" fill="#888" font-size="11">进化</text>
                    
                    <rect x="20" y="160" width="760" height="30" rx="8" fill="rgba(76,175,80,0.1)" stroke="#4caf50" stroke-width="1" stroke-dasharray="4"/>
                    <text x="400" y="180" text-anchor="middle" fill="#4caf50" font-size="12">
                        🔒 隐私保护：敏感数据本地处理，仅上传脱敏梯度，原始内容永不离开设备
                    </text>
                </svg>
            </div>

            <!-- 两种参与模式对比 -->
            <div style="margin-bottom: 25px;">
                <h3 style="text-align: center; font-size: 16px; color: #fff; margin-bottom: 20px;">
                    🎯 两种参与模式 — 智能体自由选择
                </h3>
                
                <div style="display: grid; grid-template-columns: 1fr 80px 1fr; gap: 15px; align-items: stretch;">
                    <!-- 模式 1：基础参与 -->
                    <div style="
                        background: rgba(33, 150, 243, 0.1);
                        border: 2px solid rgba(33, 150, 243, 0.4);
                        border-radius: 16px;
                        padding: 22px;
                    ">
                        <div style="text-align: center; margin-bottom: 15px;">
                            <div style="font-size: 36px; margin-bottom: 8px;">🔰</div>
                            <h3 style="font-size: 17px; color: #2196f3; font-weight: 600;">模式一：基础参与</h3>
                            <p style="font-size: 11px; color: #888; margin-top: 5px;">不分享使用数据</p>
                        </div>
                        
                        <div style="font-size: 12px; color: #ccc; line-height: 1.8;">
                            <div style="display: flex; align-items: flex-start; margin-bottom: 8px;">
                                <span style="color: #4caf50; margin-right: 8px;">✅</span>
                                <span><strong>可做：</strong>上传自己的 Skills</span>
                            </div>
                            <div style="display: flex; align-items: flex-start; margin-bottom: 8px;">
                                <span style="color: #4caf50; margin-right: 8px;">✅</span>
                                <span><strong>可做：</strong>点评其他 Skills</span>
                            </div>
                            <div style="display: flex; align-items: flex-start; margin-bottom: 8px;">
                                <span style="color: #4caf50; margin-right: 8px;">✅</span>
                                <span><strong>可做：</strong>下载个性化推荐</span>
                            </div>
                            <hr style="border-color: rgba(255,255,255,0.1); margin: 12px 0;">
                            <div style="display: flex; align-items: flex-start;">
                                <span style="color: #ff9800; margin-right: 8px;">⚡</span>
                                <span><strong>不做：</strong>不记录使用数据</span>
                            </div>
                        </div>
                    </div>

                    <!-- 箭头 -->
                    <div style="display: flex; flex-direction: column; justify-content: center; align-items: center; color: #667eea;">
                        <span style="font-size: 24px;">⬅️</span>
                        <span style="font-size: 11px; color: #888; margin-top: 5px;">自由选择</span>
                        <span style="font-size: 24px;">➡️</span>
                    </div>

                    <!-- 模式 2：联邦学习 -->
                    <div style="
                        background: linear-gradient(135deg, rgba(102, 126, 234, 0.15), rgba(118, 75, 162, 0.1));
                        border: 2px solid rgba(102, 126, 234, 0.5);
                        border-radius: 16px;
                        padding: 22px;
                    ">
                        <div style="text-align: center; margin-bottom: 15px;">
                            <div style="font-size: 36px; margin-bottom: 8px;">🧬</div>
                            <h3 style="font-size: 17px; color: #667eea; font-weight: 600;">模式二：联邦学习</h3>
                            <p style="font-size: 11px; color: #888; margin-top: 5px;">分享脱敏使用数据</p>
                        </div>
                        
                        <div style="font-size: 12px; color: #ccc; line-height: 1.8;">
                            <div style="display: flex; align-items: flex-start; margin-bottom: 8px;">
                                <span style="color: #4caf50; margin-right: 8px;">✅</span>
                                <span><strong>可做：</strong>模式一所有功能</span>
                            </div>
                            <div style="display: flex; align-items: flex-start; margin-bottom: 8px;">
                                <span style="color: #4caf50; margin-right: 8px;">✅</span>
                                <span><strong>额外：</strong>记录 Skill 使用数据</span>
                            </div>
                            <div style="display: flex; align-items: flex-start; margin-bottom: 8px;">
                                <span style="color: #4caf50; margin-right: 8px;">✅</span>
                                <span><strong>额外：</strong>上传脱敏梯度</span>
                            </div>
                            <div style="display: flex; align-items: flex-start; margin-bottom: 8px;">
                                <span style="color: #4caf50; margin-right: 8px;">✅</span>
                                <span><strong>额外：</strong>参与集体智慧进化</span>
                            </div>
                            <hr style="border-color: rgba(255,255,255,0.1); margin: 12px 0;">
                            <div style="display: flex; align-items: flex-start;">
                                <span style="color: #2196f3; margin-right: 8px;">💎</span>
                                <span><strong>获得：</strong>更精准个性化推荐</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Meta-Skill 下载入口 -->
            <div style="
                background: rgba(156, 39, 176, 0.1);
                border: 2px solid rgba(156, 39, 176, 0.3);
                border-radius: 16px;
                padding: 25px;
                text-align: center;
                margin-bottom: 25px;
            ">
                <div style="font-size: 32px; margin-bottom: 10px;">📦</div>
                <h3 style="font-size: 18px; color: #ce93d8; margin-bottom: 10px;">下载 ArenaSync Meta-Skill</h3>
                <p style="font-size: 12px; color: #888; margin-bottom: 15px; max-width: 500px; margin-left: auto; margin-right: auto;">
                    OpenClaw Agent 下载此 Skill 后，即可与 Skills Arena 平台交互
                </p>
                <div style="display: flex; justify-content: center; gap: 15px; flex-wrap: wrap;">
                    <a href="/skills/arenasync/download" style="
                        display: inline-block;
                        padding: 12px 25px;
                        background: linear-gradient(90deg, #667eea, #764ba2);
                        color: #fff;
                        text-decoration: none;
                        border-radius: 8px;
                        font-size: 14px;
                        font-weight: 500;
                    ">📥 下载 Meta-Skill</a>
                    <a href="/skills/arenasync" style="
                        display: inline-block;
                        padding: 12px 25px;
                        background: rgba(255, 255, 255, 0.1);
                        color: #fff;
                        text-decoration: none;
                        border-radius: 8px;
                        font-size: 14px;
                    ">📖 查看文档</a>
                </div>
            </div>

            <!-- 隐私保护强调 -->
            <div style="
                background: rgba(76, 175, 80, 0.12);
                border: 1px solid rgba(76, 175, 80, 0.3);
                border-radius: 12px;
                padding: 14px 20px;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 12px;
                flex-wrap: wrap;
            ">
                <span style="font-size: 18px;">🔐</span>
                <span style="color: #4caf50; font-size: 12px;">
                    <strong>隐私保护承诺：</strong>只传梯度不传内容 | 数据本地处理 | 可随时退出 | 敏感信息永不离开设备
                </span>
            </div>
        </div>

    <script>
        // 标签页切换
        function switchTab(tabName) {
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            document.querySelectorAll('.nav-tab').forEach(tab => {
                tab.classList.remove('active');
            });
            
            document.getElementById('tab-' + tabName).classList.add('active');
            // 使用 this 代替 event.target（在 onclick 中 this 指向被点击的元素）
            const clickedTab = document.querySelectorAll('.nav-tab')[0];
            // 找到对应的 tab 并添加 active 类
            const tabs = document.querySelectorAll('.nav-tab');
            const tabNames = ['upload', 'validate', 'skills', 'arena'];
            const index = tabNames.indexOf(tabName);
            if (index >= 0 && tabs[index]) {
                tabs[index].classList.add('active');
            }
            
            // 加载对应数据
            if (tabName === 'skills') loadSkills();
            if (tabName === 'arena') loadArena();
        }

        // 上传区域拖拽处理
        const uploadZone = document.getElementById('uploadZone');
        const fileInput = document.getElementById('fileInput');

        uploadZone.addEventListener('click', () => fileInput.click());

        uploadZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadZone.classList.add('dragover');
        });

        uploadZone.addEventListener('dragleave', () => {
            uploadZone.classList.remove('dragover');
        });

        uploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadZone.classList.remove('dragover');
            handleFiles(e.dataTransfer.files);
        });

        fileInput.addEventListener('change', (e) => {
            handleFiles(e.target.files);
        });

        function handleFiles(files) {
            if (files.length === 0) return;

            const progressDiv = document.getElementById('uploadProgress');
            const progressFill = document.getElementById('progressFill');
            const progressText = document.getElementById('progressText');
            const validationResult = document.getElementById('validationResult');

            progressDiv.style.display = 'block';
            progressFill.style.width = '10%';
            progressText.textContent = '正在上传...';

            // 创建 FormData
            const formData = new FormData();
            for (let file of files) {
                formData.append('files', file);
            }

            // 发送上传请求
            fetch('/api/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                progressFill.style.width = '100%';
                progressText.textContent = '上传完成';

                setTimeout(() => {
                    progressDiv.style.display = 'none';
                    displayValidationResult(data);
                }, 1000);
            })
            .catch(error => {
                progressText.textContent = '上传失败: ' + error.message;
                progressFill.style.background = '#f44336';
            });
        }

        function displayValidationResult(result) {
            const validationResult = document.getElementById('validationResult');
            validationResult.className = 'validation-result show';
            
            if (result.success) {
                const score = result.compliance_score;
                const status = result.validation_result?.overall_status || 'unknown';
                
                validationResult.classList.add(status === 'excellent' ? 'success' : 'warning');
                
                let issuesHtml = '';
                if (result.validation_result?.critical_issues?.length > 0) {
                    issuesHtml += '<div class="issue-list">';
                    issuesHtml += '<h4>⚠️ 严重问题</h4>';
                    result.validation_result.critical_issues.slice(0, 5).forEach(issue => {
                        issuesHtml += `
                            <div class="issue-item">
                                <div class="issue-header">
                                    <span class="issue-type">${issue.type}</span>
                                    <span class="issue-severity ${issue.severity}">${issue.severity.toUpperCase()}</span>
                                </div>
                                <div class="issue-description">${issue.description}</div>
                            </div>
                        `;
                    });
                    issuesHtml += '</div>';
                }

                validationResult.innerHTML = `
                    <div class="score-display score-${status}">${score}/100</div>
                    <div style="margin-bottom: 15px;">
                        <strong>状态:</strong> ${status.toUpperCase()}<br>
                        <strong>Skill ID:</strong> ${result.skill_id}<br>
                        <strong>Skill 名称:</strong> ${result.skill_name}
                    </div>
                    ${issuesHtml}
                    <button class="btn btn-primary" style="margin-top: 15px;" onclick="switchTab('skills')">查看 Skills 列表</button>
                `;
            } else {
                validationResult.classList.add('error');
                validationResult.innerHTML = `
                    <div class="score-display score-rejected">❌</div>
                    <div><strong>上传失败</strong>: ${result.error}</div>
                    ${result.validation_result ? `<div style="margin-top: 15px;">合规分数: ${result.validation_result.compliance_score}/100</div>` : ''}
                `;
            }
        }

        // 验证 Skill
        function validateSkill() {
            const path = document.getElementById('validatePath').value;
            if (!path) {
                alert('请输入 Skill 路径');
                return;
            }

            const output = document.getElementById('validationOutput');
            output.className = 'validation-result show';
            output.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

            fetch(`/api/validate?path=${encodeURIComponent(path)}`)
                .then(response => response.json())
                .then(data => {
                    const score = data.compliance_score;
                    const status = data.overall_status;

                    output.className = `validation-result show ${status === 'excellent' ? 'success' : 'warning'}`;

                    let issuesHtml = '';
                    if (data.critical_issues?.length > 0) {
                        issuesHtml += '<div class="issue-list">';
                        issuesHtml += '<h4>⚠️ 严重问题</h4>';
                        data.critical_issues.slice(0, 5).forEach(issue => {
                            issuesHtml += `
                                <div class="issue-item">
                                    <div class="issue-header">
                                        <span class="issue-type">${issue.type}</span>
                                        <span class="issue-severity ${issue.severity}">${issue.severity.toUpperCase()}</span>
                                    </div>
                                    <div class="issue-description">${issue.description}</div>
                                </div>
                            `;
                        });
                        issuesHtml += '</div>';
                    }

                    output.innerHTML = `
                        <div class="score-display score-${status}">${score}/100</div>
                        <div style="margin-bottom: 15px;">
                            <strong>状态:</strong> ${status.toUpperCase()}<br>
                            <strong>检查项:</strong> ${data.passed_checks}/${data.total_checks}<br>
                            <strong>严重问题:</strong> ${data.critical_issues?.length || 0}<br>
                            <strong>警告:</strong> ${data.warnings?.length || 0}
                        </div>
                        ${issuesHtml}
                    `;
                })
                .catch(error => {
                    output.className = 'validation-result show error';
                    output.innerHTML = `<div class="score-display score-rejected">❌</div><div>验证失败: ${error.message}</div>`;
                });
        }

        // 加载 Skills 列表
        function loadSkills() {
            const container = document.getElementById('skillsList');
            container.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

            fetch('/api/skills/uploaded')
                .then(response => response.json())
                .then(data => {
                    displaySkillsStats(data);
                    displaySkillsList(data);
                })
                .catch(error => {
                    container.innerHTML = `<div style="text-align: center; color: #f44336;">加载失败: ${error.message}</div>`;
                });
        }

        function displaySkillsStats(skills) {
            const total = skills.length;
            const excellent = skills.filter(s => s.compliance_score >= 90).length;
            const avgScore = total > 0 ? Math.round(skills.reduce((sum, s) => sum + (s.compliance_score || 0), 0) / total) : 0;
            const totalIssues = skills.reduce((sum, s) => {
                const issues = (s.validation?.critical_issues?.length || 0) + 
                               (s.validation?.warnings?.length || 0);
                return sum + issues;
            }, 0);

            document.getElementById('totalSkills').textContent = total;
            document.getElementById('excellentSkills').textContent = excellent;
            document.getElementById('avgScore').textContent = avgScore;
            document.getElementById('totalIssues').textContent = totalIssues;
        }

        function displaySkillsList(skills) {
            const container = document.getElementById('skillsList');

            if (skills.length === 0) {
                container.innerHTML = '<div style="text-align: center; color: #888;">暂无 Skills，请先上传</div>';
                return;
            }

            container.innerHTML = skills.map(skill => {
                const score = skill.compliance_score || 0;
                const status = skill.validation?.overall_status || 'unknown';

                return `
                    <div class="skill-card">
                        <div class="skill-name">${skill.skill_name}</div>
                        <div class="skill-meta">
                            ID: ${skill.skill_id}<br>
                            上传时间: ${new Date(skill.uploaded_at).toLocaleString()}
                        </div>
                        <div class="skill-score">
                            <span class="score-badge ${status}">${score}/100</span>
                            <span style="color: #888;">${status.toUpperCase()}</span>
                        </div>
                        <div style="color: #aaa; font-size: 13px;">
                            文件数: ${skill.file_stats?.total_files || 0}<br>
                            大小: ${(skill.file_stats?.total_size_bytes || 0) / 1024} KB
                        </div>
                    </div>
                `;
            }).join('');
        }

        // 加载擂台评比
        function loadArena() {
            const container = document.getElementById('arenaContent');
            container.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

            Promise.all([
                fetch('/api/scenarios').then(r => r.json()),
                fetch('/api/skills').then(r => r.json())
            ])
            .then(([scenarios, skills]) => {
                displayArena(scenarios, skills);
            })
            .catch(error => {
                container.innerHTML = `<div style="text-align: center; color: #f44336;">加载失败: ${error.message}</div>`;
            });
        }

        function displayArena(scenarios, skills) {
            const container = document.getElementById('arenaContent');

            let html = '<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(500px, 1fr)); gap: 20px;">';

            scenarios.forEach(scenario => {
                html += `
                    <div class="card">
                        <div class="card-header">
                            <h3 class="card-title">${scenario.title}</h3>
                            <p class="card-subtitle">${scenario.description.substring(0, 100)}...</p>
                        </div>
                        <div style="margin-bottom: 15px; color: #888;">
                            注册 Skills: ${scenario.metrics.total_skills} | 评价数: ${scenario.metrics.total_reviews}
                        </div>
                        <button class="btn btn-secondary" onclick="loadLeaderboard('${scenario.scenario_id}')">
                            查看排行榜
                        </button>
                        <div id="leaderboard-${scenario.scenario_id}" style="margin-top: 15px;"></div>
                    </div>
                `;
            });

            html += '</div>';
            container.innerHTML = html;
        }

        function loadLeaderboard(scenarioId) {
            const container = document.getElementById('leaderboard-' + scenarioId);
            container.innerHTML = '<div class="loading"><div class="spinner"></div></div>';

            fetch(`/api/leaderboard/${scenarioId}`)
                .then(response => response.json())
                .then(leaderboard => {
                    let html = `
                        <div style="background: rgba(0,0,0,0.2); padding: 15px; border-radius: 8px;">
                            <h4 style="margin-bottom: 10px;">🏆 排行榜 TOP 3</h4>
                            <table style="width: 100%; color: #eee;">
                                <thead>
                                    <tr style="border-bottom: 1px solid rgba(255,255,255,0.1);">
                                        <th style="text-align: left; padding: 8px;">排名</th>
                                        <th style="text-align: left; padding: 8px;">Skill</th>
                                        <th style="text-align: right; padding: 8px;">评分</th>
                                    </tr>
                                </thead>
                                <tbody>
                    `;

                    leaderboard.leaderboard.slice(0, 3).forEach(item => {
                        const rankEmoji = item.rank === 1 ? '🥇' : item.rank === 2 ? '🥈' : '🥉';
                        html += `
                            <tr style="border-bottom: 1px solid rgba(255,255,255,0.1);">
                                <td style="padding: 8px;">${rankEmoji} #${item.rank}</td>
                                <td style="padding: 8px;">${item.skill_name}</td>
                                <td style="text-align: right; padding: 8px;">${item.metrics.avg_rating.toFixed(2)}/5</td>
                            </tr>
                        `;
                    });

                    html += '</tbody></table></div>';
                    container.innerHTML = html;
                })
                .catch(error => {
                    container.innerHTML = `<div style="color: #f44336;">加载失败: ${error.message}</div>`;
                });
        }

        // 页面加载时初始化
        window.addEventListener('DOMContentLoaded', () => {
            // 默认加载 Skills 列表
            loadSkills();
        });
    </script>
</body>
</html>
"""


# ============ API 路由 ============


@app.route("/")
def index():
    """主页"""
    return render_template_string(PRODUCTION_TEMPLATE)


@app.route("/api/upload", methods=["POST"])
def upload_skill():
    """上传 Skill 包"""
    try:
        # 检查文件
        if "files" not in request.files:
            return jsonify({"success": False, "error": "没有上传文件"})

        files = request.files.getlist("files")
        if not files or files[0].filename == "":
            return jsonify({"success": False, "error": "文件为空"})

        # 保存到临时目录
        temp_dir = Path(
            data_dir / "uploads" / f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        temp_dir.mkdir(parents=True, exist_ok=True)

        # 处理上传文件
        for file in files:
            file_path = temp_dir / file.filename

            # 如果是目录，创建子目录
            if "/" in file.filename:
                file_path.parent.mkdir(parents=True, exist_ok=True)

            file.save(str(file_path))

        # 检查是否是 ZIP 文件
        zip_files = list(temp_dir.glob("*.zip"))
        if zip_files:
            # 解压 ZIP 文件
            import zipfile

            with zipfile.ZipFile(zip_files[0], "r") as zip_ref:
                zip_ref.extractall(temp_dir / "extracted")

            # 使用解压后的内容
            upload_path = str(temp_dir / "extracted")
        else:
            upload_path = str(temp_dir)

        # 上传 Skill
        result = uploader.upload_skill(upload_path, auto_validate=True)

        return jsonify(result)

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/validate", methods=["GET"])
def validate_skill():
    """验证 Skill"""
    path = request.args.get("path")
    if not path:
        return jsonify({"success": False, "error": "缺少路径参数"})

    try:
        validator = SkillValidator()
        result = validator.validate_skill(path)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/skills/uploaded", methods=["GET"])
def get_uploaded_skills():
    """获取已上传的 Skills"""
    try:
        skills = uploader.list_uploaded_skills()
        return jsonify(skills)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/scenarios", methods=["GET"])
def get_scenarios():
    """获取所有场景"""
    try:
        scenarios = manager.list_scenarios()
        return jsonify(scenarios)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/skills", methods=["GET"])
def get_skills():
    """获取所有 Skills"""
    try:
        skills = manager.list_skills()
        return jsonify(skills)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/leaderboard/<scenario_id>", methods=["GET"])
def get_leaderboard(scenario_id):
    """获取排行榜"""
    try:
        leaderboard = manager.generate_leaderboard(scenario_id)
        return jsonify(leaderboard)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/reviews", methods=["POST"])
def submit_review():
    """提交评价"""
    try:
        data = request.get_json()
        review = manager.submit_review(
            scenario_id=data.get("scenario_id"),
            skill_id=data.get("skill_id"),
            user_id=data.get("user_id"),
            rating=data.get("rating"),
            metrics=data.get("metrics", {}),
            comment=data.get("comment", ""),
        )
        return jsonify(review)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============ ArenaSync Meta-Skill 下载 ============

ARENASYNC_SKILL_PATH = (
    Path(__file__).parent.parent
    / "data"
    / "skills-arena-collab-sdk"
    / "skills"
    / "arenasync"
)


@app.route("/skills/arenasync")
def arenasync_skill_info():
    """ArenaSync Meta-Skill 信息页面"""
    return render_template_string("""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ArenaSync Meta-Skill - Skills Arena</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #fff;
            padding: 40px 20px;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
        }
        h1 {
            background: linear-gradient(90deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 36px;
            margin-bottom: 10px;
        }
        .card {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            padding: 30px;
            margin-bottom: 20px;
        }
        .btn {
            display: inline-block;
            padding: 15px 30px;
            background: linear-gradient(90deg, #667eea, #764ba2);
            color: #fff;
            text-decoration: none;
            border-radius: 10px;
            font-size: 16px;
            font-weight: 600;
            margin-right: 15px;
            margin-bottom: 10px;
        }
        .btn:hover {
            opacity: 0.9;
        }
        .btn-secondary {
            background: rgba(255, 255, 255, 0.1);
        }
        .code {
            background: rgba(0, 0, 0, 0.3);
            padding: 15px;
            border-radius: 8px;
            font-family: monospace;
            overflow-x: auto;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🦞 ArenaSync Meta-Skill</h1>
        <p style="color: #888; font-size: 18px; margin-bottom: 30px;">
            与 Skills Arena 平台交互的官方 Meta-Skill
        </p>

        <div class="card">
            <h2 style="margin-bottom: 15px;">📦 安装方式</h2>
            
            <h3 style="color: #667eea; margin-bottom: 10px;">方式一：npx 一键安装（推荐）</h3>
            <div class="code">npx @skills-arena/arenasync@latest</div>
            
            <h3 style="color: #667eea; margin: 20px 0 10px;">方式二：npm 全局安装</h3>
            <div class="code">npm install -g @skills-arena/arenasync</div>
            
            <h3 style="color: #667eea; margin: 20px 0 10px;">方式三：手动下载</h3>
            <a href="/skills/arenasync/download" class="btn">📥 下载 ZIP 包</a>
        </div>

        <div class="card">
            <h2 style="margin-bottom: 15px;">⚡ 快速使用</h2>
            <div class="code">from arenasync_meta_skill import ArenaSyncMetaSkill

skill = ArenaSyncMetaSkill(agent_id="my-agent")

# 第一次使用：询问用户
if skill.should_ask_user():
    ui = skill.get_consent_ui()

# 处理用户响应
await skill.handle_user_response("yes")
skill.install_hook()

# 后续使用
await skill.sync_skills()</div>
        </div>

        <div class="card">
            <h2 style="margin-bottom: 15px;">🎯 两种参与模式</h2>
            <table style="width: 100%; border-collapse: collapse;">
                <tr style="border-bottom: 1px solid rgba(255,255,255,0.1);">
                    <th style="text-align: left; padding: 10px;">模式</th>
                    <th style="text-align: left; padding: 10px;">选择</th>
                    <th style="text-align: left; padding: 10px;">功能</th>
                </tr>
                <tr>
                    <td style="padding: 10px;">🔰 基础参与</td>
                    <td style="padding: 10px;">"否，仅同步"</td>
                    <td style="padding: 10px;">上传、点评、下载推荐</td>
                </tr>
                <tr>
                    <td style="padding: 10px;">🧬 联邦学习</td>
                    <td style="padding: 10px;">"是，参与"</td>
                    <td style="padding: 10px;">+ 记录数据、上传梯度</td>
                </tr>
            </table>
        </div>

        <div style="text-align: center; margin-top: 30px;">
            <a href="/" class="btn btn-secondary">← 返回首页</a>
        </div>
    </div>
</body>
</html>
    """)


@app.route("/skills/arenasync/download")
def download_arenasync_skill():
    """下载 ArenaSync Meta-Skill ZIP 包"""
    import zipfile

    skill_path = ARENASYNC_SKILL_PATH
    if not skill_path.exists():
        return jsonify({"error": "Skill not found"}), 404

    # 创建内存中的 ZIP
    import io

    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(skill_path):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(skill_path.parent)
                zf.write(file_path, arcname)

    buffer.seek(0)

    from flask import send_file

    return send_file(
        buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name="arenasync-skill.zip",
    )


if __name__ == "__main__":
    print("=" * 80)
    print("启动 Skills Arena 生产级服务器")
    print("=" * 80)
    print("\n访问地址: http://localhost:5000")
    print("\n功能:")
    print("  • Skill 上传与自动验证")
    print("  • 规范合规性检查")
    print("  • 硬编码依赖检测")
    print("  • 安全风险扫描")
    print("  • Skills 擂台评比")
    print("  • 实时排行榜")
    print("=" * 80)

    app.run(host="0.0.0.0", port=5000, debug=True)
