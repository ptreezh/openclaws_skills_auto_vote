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
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB 最大上传

# 初始化管理器
data_dir = Path(__file__).parent.parent / "data"
manager = ArenaManager(data_dir=str(data_dir))
uploader = SkillUploader(upload_dir=str(data_dir / "uploads"), 
                         skills_dir=str(data_dir / "skills"))

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
        <nav class="navbar">
            <div class="navbar-content">
                <div class="logo">Skills Arena</div>
                <div class="nav-tabs">
                    <button class="nav-tab active" onclick="switchTab('upload')">上传 Skill</button>
                    <button class="nav-tab" onclick="switchTab('validate')">规范验证</button>
                    <button class="nav-tab" onclick="switchTab('skills')">Skills 列表</button>
                    <button class="nav-tab" onclick="switchTab('arena')">擂台评比</button>
                </div>
            </div>
        </nav>

        <!-- 上传页面 -->
        <div id="tab-upload" class="tab-content active">
            <div class="card">
                <div class="card-header">
                    <h2 class="card-title">上传 Skill</h2>
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
                    <h3 class="card-title">规范要求</h3>
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
                    <h2 class="card-title">规范验证</h2>
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
                    <h2 class="card-title">Skills 擂台</h2>
                    <p class="card-subtitle">查看各场景下 Skills 的评比结果</p>
                </div>
                <div id="arenaContent">
                    <div class="loading">
                        <div class="spinner"></div>
                    </div>
                </div>
            </div>
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
            event.target.classList.add('active');
            
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

@app.route('/')
def index():
    """主页"""
    return render_template_string(PRODUCTION_TEMPLATE)


@app.route('/api/upload', methods=['POST'])
def upload_skill():
    """上传 Skill 包"""
    try:
        # 检查文件
        if 'files' not in request.files:
            return jsonify({
                'success': False,
                'error': '没有上传文件'
            })

        files = request.files.getlist('files')
        if not files or files[0].filename == '':
            return jsonify({
                'success': False,
                'error': '文件为空'
            })

        # 保存到临时目录
        temp_dir = Path(data_dir / "uploads" / f"upload_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        temp_dir.mkdir(parents=True, exist_ok=True)

        # 处理上传文件
        for file in files:
            file_path = temp_dir / file.filename
            
            # 如果是目录，创建子目录
            if '/' in file.filename:
                file_path.parent.mkdir(parents=True, exist_ok=True)
            
            file.save(str(file_path))

        # 检查是否是 ZIP 文件
        zip_files = list(temp_dir.glob("*.zip"))
        if zip_files:
            # 解压 ZIP 文件
            import zipfile
            with zipfile.ZipFile(zip_files[0], 'r') as zip_ref:
                zip_ref.extractall(temp_dir / "extracted")
            
            # 使用解压后的内容
            upload_path = str(temp_dir / "extracted")
        else:
            upload_path = str(temp_dir)

        # 上传 Skill
        result = uploader.upload_skill(upload_path, auto_validate=True)

        return jsonify(result)

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/validate', methods=['GET'])
def validate_skill():
    """验证 Skill"""
    path = request.args.get('path')
    if not path:
        return jsonify({'success': False, 'error': '缺少路径参数'})

    try:
        validator = SkillValidator()
        result = validator.validate_skill(path)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/skills/uploaded', methods=['GET'])
def get_uploaded_skills():
    """获取已上传的 Skills"""
    try:
        skills = uploader.list_uploaded_skills()
        return jsonify(skills)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/scenarios', methods=['GET'])
def get_scenarios():
    """获取所有场景"""
    try:
        scenarios = manager.list_scenarios()
        return jsonify(scenarios)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/skills', methods=['GET'])
def get_skills():
    """获取所有 Skills"""
    try:
        skills = manager.list_skills()
        return jsonify(skills)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/leaderboard/<scenario_id>', methods=['GET'])
def get_leaderboard(scenario_id):
    """获取排行榜"""
    try:
        leaderboard = manager.generate_leaderboard(scenario_id)
        return jsonify(leaderboard)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/reviews', methods=['POST'])
def submit_review():
    """提交评价"""
    try:
        data = request.get_json()
        review = manager.submit_review(
            scenario_id=data.get('scenario_id'),
            skill_id=data.get('skill_id'),
            user_id=data.get('user_id'),
            rating=data.get('rating'),
            metrics=data.get('metrics', {}),
            comment=data.get('comment', '')
        )
        return jsonify(review)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
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
    
    app.run(host='0.0.0.0', port=5000, debug=True)
