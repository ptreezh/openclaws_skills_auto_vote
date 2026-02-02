#!/usr/bin/env python3
"""
Skills Arena Web Server

基于 Flask 的轻量级 Web 服务器，提供 RESTful API 和前端界面
"""

from flask import Flask, jsonify, request, render_template_string
import json
from pathlib import Path
from datetime import datetime
import os

# 导入管理器
import sys
sys.path.insert(0, str(Path(__file__).parent))
from arena_manager import ArenaManager


app = Flask(__name__)

# 初始化管理器
data_dir = Path(__file__).parent.parent / "data"
manager = ArenaManager(data_dir=str(data_dir))


# HTML 模板
INDEX_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Skills 擂台 - AI Skills 评比平台</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        .header {
            text-align: center;
            color: white;
            margin-bottom: 40px;
        }

        .header h1 {
            font-size: 3em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }

        .header p {
            font-size: 1.2em;
            opacity: 0.9;
        }

        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 30px;
            justify-content: center;
        }

        .tab {
            padding: 12px 30px;
            background: white;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            color: #667eea;
            transition: all 0.3s;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        .tab:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        }

        .tab.active {
            background: white;
            color: #764ba2;
            box-shadow: 0 6px 12px rgba(0,0,0,0.2);
        }

        .content {
            background: white;
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }

        .section {
            display: none;
        }

        .section.active {
            display: block;
        }

        .card {
            background: #f8f9fa;
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 20px;
            border-left: 4px solid #667eea;
        }

        .card h3 {
            color: #667eea;
            margin-bottom: 15px;
        }

        .stat-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .stat-item {
            text-align: center;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 12px;
            color: white;
        }

        .stat-item .value {
            font-size: 2.5em;
            font-weight: bold;
        }

        .stat-item .label {
            font-size: 0.9em;
            opacity: 0.9;
            margin-top: 5px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }

        th, td {
            padding: 15px;
            text-align: left;
            border-bottom: 1px solid #dee2e6;
        }

        th {
            background: #667eea;
            color: white;
            font-weight: 600;
        }

        tr:hover {
            background: #f8f9fa;
        }

        .rank-1 {
            background: linear-gradient(135deg, #ffd700 0%, #ffec8b 100%) !important;
            font-weight: bold;
        }

        .rank-2 {
            background: linear-gradient(135deg, #c0c0c0 0%, #e8e8e8 100%) !important;
            font-weight: bold;
        }

        .rank-3 {
            background: linear-gradient(135deg, #cd7f32 0%, #daa06d 100%) !important;
            font-weight: bold;
        }

        .rating {
            display: flex;
            gap: 3px;
        }

        .star {
            color: #ffc107;
        }

        .star.empty {
            color: #dee2e6;
        }

        .form-group {
            margin-bottom: 20px;
        }

        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #333;
        }

        .form-group input,
        .form-group textarea,
        .form-group select {
            width: 100%;
            padding: 12px;
            border: 2px solid #dee2e6;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.3s;
        }

        .form-group input:focus,
        .form-group textarea:focus,
        .form-group select:focus {
            outline: none;
            border-color: #667eea;
        }

        .btn {
            padding: 12px 30px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 25px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.2);
        }

        .review-card {
            background: #f8f9fa;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 15px;
        }

        .review-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }

        .review-user {
            font-weight: 600;
            color: #667eea;
        }

        .review-date {
            color: #6c757d;
            font-size: 0.9em;
        }

        .review-rating {
            margin-bottom: 10px;
        }

        .review-comment {
            color: #333;
            line-height: 1.6;
        }

        .badge {
            display: inline-block;
            padding: 4px 12px;
            background: #667eea;
            color: white;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
        }

        .loading {
            text-align: center;
            padding: 40px;
            color: #6c757d;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚔️ Skills 擂台</h1>
            <p>AI Skills 横向评比平台 - 发现最佳工具</p>
        </div>

        <div class="tabs">
            <button class="tab active" onclick="showSection('scenarios')">🎯 场景列表</button>
            <button class="tab" onclick="showSection('leaderboard')">🏆 排行榜</button>
            <button class="tab" onclick="showSection('review')">⭐ 提交评价</button>
            <button class="tab" onclick="showSection('reviews')">💬 评价浏览</button>
        </div>

        <div class="content">
            <!-- 场景列表 -->
            <div id="scenarios" class="section active">
                <div id="scenarios-content" class="loading">加载中...</div>
            </div>

            <!-- 排行榜 -->
            <div id="leaderboard" class="section">
                <h2>🏆 Skills 排行榜</h2>
                <div class="form-group" style="margin-top: 20px;">
                    <label for="scenario-select">选择场景</label>
                    <select id="scenario-select" onchange="loadLeaderboard()">
                        <option value="">请选择场景...</option>
                    </select>
                </div>
                <div id="leaderboard-content" class="loading">请先选择场景</div>
            </div>

            <!-- 提交评价 -->
            <div id="review" class="section">
                <h2>⭐ 提交您的评价</h2>
                <form id="review-form" onsubmit="submitReview(event)">
                    <div class="form-group">
                        <label for="scenario-select-review">选择场景</label>
                        <select id="scenario-select-review" onchange="loadSkillsForReview()" required>
                            <option value="">请选择场景...</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="skill-select">选择 Skill</label>
                        <select id="skill-select" required disabled>
                            <option value="">请先选择场景...</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="user-id">您的 ID</label>
                        <input type="text" id="user-id" placeholder="例如: user-001" required>
                    </div>
                    <div class="form-group">
                        <label for="rating">总体评分 (1-5)</label>
                        <input type="number" id="rating" min="1" max="5" step="0.1" value="5" required>
                    </div>
                    <div class="form-group">
                        <label>细分指标 (1-5)</label>
                        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px;">
                            <div>
                                <label for="accuracy">准确性</label>
                                <input type="number" id="accuracy" min="0" max="5" step="0.1" value="5">
                            </div>
                            <div>
                                <label for="efficiency">效率</label>
                                <input type="number" id="efficiency" min="0" max="5" step="0.1" value="5">
                            </div>
                            <div>
                                <label for="creativity">创意</label>
                                <input type="number" id="creativity" min="0" max="5" step="0.1" value="5">
                            </div>
                        </div>
                    </div>
                    <div class="form-group">
                        <label for="comment">评论 (可选)</label>
                        <textarea id="comment" rows="4" placeholder="分享您的使用体验..."></textarea>
                    </div>
                    <button type="submit" class="btn">提交评价</button>
                </form>
            </div>

            <!-- 评价浏览 -->
            <div id="reviews" class="section">
                <h2>💬 用户评价</h2>
                <div class="form-group" style="margin-top: 20px;">
                    <label for="scenario-select-reviews">选择场景</label>
                    <select id="scenario-select-reviews" onchange="loadReviews()" required>
                        <option value="">请选择场景...</option>
                    </select>
                </div>
                <div id="reviews-content" class="loading">请先选择场景</div>
            </div>
        </div>
    </div>

    <script>
        // 全局数据
        let scenarios = [];
        let currentScenario = null;

        // 页面加载时初始化
        window.onload = function() {
            loadScenarios();
        };

        // 显示指定区块
        function showSection(sectionId) {
            // 隐藏所有区块
            document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));

            // 显示目标区块
            document.getElementById(sectionId).classList.add('active');
            event.target.classList.add('active');
        }

        // 加载场景列表
        async function loadScenarios() {
            try {
                const response = await fetch('/api/scenarios');
                scenarios = await response.json();

                const container = document.getElementById('scenarios-content');
                const selects = [
                    document.getElementById('scenario-select'),
                    document.getElementById('scenario-select-review'),
                    document.getElementById('scenario-select-reviews')
                ];

                if (scenarios.length === 0) {
                    container.innerHTML = '<p>暂无场景</p>';
                    return;
                }

                let html = '<div class="stat-grid">';
                html += '<div class="stat-item"><div class="value">' + scenarios.length + '</div><div class="label">场景总数</div></div>';

                let totalSkills = 0;
                let totalReviews = 0;
                scenarios.forEach(s => {
                    totalSkills += s.metrics.total_skills;
                    totalReviews += s.metrics.total_reviews;
                });

                html += '<div class="stat-item"><div class="value">' + totalSkills + '</div><div class="label">注册 Skills</div></div>';
                html += '<div class="stat-item"><div class="value">' + totalReviews + '</div><div class="label">评价总数</div></div>';
                html += '</div>';

                html += '<h3>场景列表</h3>';
                scenarios.forEach(s => {
                    html += '<div class="card">';
                    html += '<h3>' + s.title + '</h3>';
                    html += '<p><strong>分类:</strong> <span class="badge">' + s.category + '</span></p>';
                    html += '<p><strong>描述:</strong> ' + s.description + '</p>';
                    html += '<p><strong>Skills:</strong> ' + s.metrics.total_skills + ' | ';
                    html += '<strong>评价:</strong> ' + s.metrics.total_reviews + ' | ';
                    html += '<strong>状态:</strong> ' + (s.status === 'active' ? '✅ 活跃' : '⏸️ 暂停') + '</p>';
                    html += '</div>';
                });

                container.innerHTML = html;

                // 更新下拉菜单
                selects.forEach(select => {
                    select.innerHTML = '<option value="">请选择场景...</option>';
                    scenarios.forEach(s => {
                        select.innerHTML += '<option value="' + s.scenario_id + '">' + s.title + '</option>';
                    });
                });

            } catch (error) {
                console.error('加载场景失败:', error);
                document.getElementById('scenarios-content').innerHTML = '<p>加载失败，请刷新页面</p>';
            }
        }

        // 加载排行榜
        async function loadLeaderboard() {
            const scenarioId = document.getElementById('scenario-select').value;
            const container = document.getElementById('leaderboard-content');

            if (!scenarioId) {
                container.innerHTML = '<p>请先选择场景</p>';
                return;
            }

            try {
                const response = await fetch('/api/leaderboard/' + scenarioId);
                const data = await response.json();

                if (data.leaderboard.length === 0) {
                    container.innerHTML = '<p>该场景暂无排行数据</p>';
                    return;
                }

                let html = '<table>';
                html += '<thead><tr><th>排名</th><th>Skill 名称</th><th>作者</th><th>综合评分</th><th>准确性</th><th>效率</th><th>创意</th><th>评价数</th></tr></thead>';
                html += '<tbody>';

                data.leaderboard.forEach(item => {
                    const rankClass = item.rank <= 3 ? 'rank-' + item.rank : '';
                    html += '<tr class="' + rankClass + '">';
                    html += '<td>#' + item.rank + '</td>';
                    html += '<td><strong>' + item.skill_name + '</strong></td>';
                    html += '<td>' + item.author + '</td>';
                    html += '<td><strong>' + item.metrics.avg_rating.toFixed(2) + '</strong></td>';
                    html += '<td>' + item.metrics.avg_accuracy.toFixed(2) + '</td>';
                    html += '<td>' + item.metrics.avg_efficiency.toFixed(2) + '</td>';
                    html += '<td>' + item.metrics.avg_creativity.toFixed(2) + '</td>';
                    html += '<td>' + item.metrics.total_reviews + '</td>';
                    html += '</tr>';
                });

                html += '</tbody></table>';
                container.innerHTML = html;

            } catch (error) {
                console.error('加载排行榜失败:', error);
                container.innerHTML = '<p>加载失败，请刷新页面</p>';
            }
        }

        // 加载 Skills（用于评价表单）
        async function loadSkillsForReview() {
            const scenarioId = document.getElementById('scenario-select-review').value;
            const skillSelect = document.getElementById('skill-select');

            if (!scenarioId) {
                skillSelect.disabled = true;
                skillSelect.innerHTML = '<option value="">请先选择场景...</option>';
                return;
            }

            try {
                const response = await fetch('/api/scenario/' + scenarioId);
                const scenario = await response.json();

                skillSelect.disabled = false;
                skillSelect.innerHTML = '<option value="">请选择 Skill...</option>';

                scenario.registered_skills.forEach(skillId => {
                    fetch('/api/skill/' + skillId)
                        .then(res => res.json())
                        .then(skill => {
                            skillSelect.innerHTML += '<option value="' + skill.skill_id + '">' + skill.skill_name + '</option>';
                        });
                });

            } catch (error) {
                console.error('加载 Skills 失败:', error);
                skillSelect.disabled = true;
            }
        }

        // 提交评价
        async function submitReview(event) {
            event.preventDefault();

            const scenarioId = document.getElementById('scenario-select-review').value;
            const skillId = document.getElementById('skill-select').value;
            const userId = document.getElementById('user-id').value;
            const rating = parseFloat(document.getElementById('rating').value);
            const accuracy = parseFloat(document.getElementById('accuracy').value);
            const efficiency = parseFloat(document.getElementById('efficiency').value);
            const creativity = parseFloat(document.getElementById('creativity').value);
            const comment = document.getElementById('comment').value;

            try {
                const response = await fetch('/api/reviews', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        scenario_id: scenarioId,
                        skill_id: skillId,
                        user_id: userId,
                        rating: rating,
                        metrics: {
                            accuracy: accuracy,
                            efficiency: efficiency,
                            creativity: creativity
                        },
                        comment: comment
                    })
                });

                const data = await response.json();

                if (response.ok) {
                    alert('✅ 评价提交成功！');
                    document.getElementById('review-form').reset();
                } else {
                    alert('❌ 提交失败: ' + data.error);
                }

            } catch (error) {
                console.error('提交评价失败:', error);
                alert('❌ 提交失败，请稍后重试');
            }
        }

        // 加载评价
        async function loadReviews() {
            const scenarioId = document.getElementById('scenario-select-reviews').value;
            const container = document.getElementById('reviews-content');

            if (!scenarioId) {
                container.innerHTML = '<p>请先选择场景</p>';
                return;
            }

            try {
                const response = await fetch('/api/reviews/' + scenarioId);
                const reviews = await response.json();

                if (reviews.length === 0) {
                    container.innerHTML = '<p>该场景暂无评价</p>';
                    return;
                }

                let html = '';
                reviews.forEach(r => {
                    html += '<div class="review-card">';
                    html += '<div class="review-header">';
                    html += '<span class="review-user">' + r.user_id + '</span>';
                    html += '<span class="review-date">' + new Date(r.created_at).toLocaleString('zh-CN') + '</span>';
                    html += '</div>';
                    html += '<div class="review-rating">';
                    html += '<strong>总体评分:</strong> ' + r.rating + '/5 | ';
                    html += '<strong>准确性:</strong> ' + r.metrics.accuracy + ' | ';
                    html += '<strong>效率:</strong> ' + r.metrics.efficiency + ' | ';
                    html += '<strong>创意:</strong> ' + r.metrics.creativity;
                    html += '</div>';
                    if (r.comment) {
                        html += '<div class="review-comment">' + r.comment + '</div>';
                    }
                    html += '</div>';
                });

                container.innerHTML = html;

            } catch (error) {
                console.error('加载评价失败:', error);
                container.innerHTML = '<p>加载失败，请刷新页面</p>';
            }
        }
    </script>
</body>
</html>
"""


# API 路由

@app.route('/')
def index():
    """主页"""
    return render_template_string(INDEX_TEMPLATE)


@app.route('/api/scenarios', methods=['GET'])
def get_scenarios():
    """获取所有场景"""
    scenarios = manager.list_scenarios()
    return jsonify(scenarios)


@app.route('/api/scenarios/<scenario_id>', methods=['GET'])
def get_scenario(scenario_id):
    """获取特定场景"""
    scenario = manager.load_scenario(scenario_id)
    if not scenario:
        return jsonify({"error": "Scenario not found"}), 404
    return jsonify(scenario)


@app.route('/api/scenarios', methods=['POST'])
def create_scenario():
    """创建新场景"""
    data = request.json
    try:
        scenario = manager.create_scenario(
            title=data.get('title'),
            description=data.get('description'),
            category=data.get('category')
        )
        return jsonify(scenario), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/api/skills', methods=['GET'])
def get_skills():
    """获取所有 Skills"""
    skills = manager.list_skills()
    return jsonify(skills)


@app.route('/api/skills/<skill_id>', methods=['GET'])
def get_skill(skill_id):
    """获取特定 Skill"""
    skill = manager.load_skill(skill_id)
    if not skill:
        return jsonify({"error": "Skill not found"}), 404
    return jsonify(skill)


@app.route('/api/skills', methods=['POST'])
def register_skill():
    """注册新 Skill"""
    data = request.json
    try:
        skill = manager.register_skill(
            skill_name=data.get('skill_name'),
            description=data.get('description'),
            author=data.get('author', 'anonymous')
        )
        return jsonify(skill), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/api/scenarios/<scenario_id>/skills/<skill_id>', methods=['POST'])
def add_skill_to_scenario(scenario_id, skill_id):
    """将 Skill 添加到场景"""
    try:
        scenario = manager.add_skill_to_scenario(scenario_id, skill_id)
        return jsonify(scenario)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/api/leaderboard/<scenario_id>', methods=['GET'])
def get_leaderboard(scenario_id):
    """获取排行榜"""
    try:
        leaderboard = manager.generate_leaderboard(scenario_id)
        return jsonify(leaderboard)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/api/reviews', methods=['POST'])
def submit_review():
    """提交评价"""
    data = request.json
    try:
        review = manager.submit_review(
            scenario_id=data.get('scenario_id'),
            skill_id=data.get('skill_id'),
            user_id=data.get('user_id'),
            rating=data.get('rating'),
            metrics=data.get('metrics'),
            comment=data.get('comment', '')
        )
        return jsonify(review), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/api/reviews/<scenario_id>', methods=['GET'])
def get_reviews(scenario_id):
    """获取场景的所有评价"""
    reviews = manager.get_scenario_reviews(scenario_id)
    return jsonify(reviews)


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })


def main():
    """启动服务器"""
    import argparse

    parser = argparse.ArgumentParser(description="Skills Arena Web Server")
    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=5000,
        help='Port to bind to (default: 5000)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode'
    )

    args = parser.parse_args()

    print("=" * 80)
    print("Skills Arena Web Server")
    print("=" * 80)
    print(f"Server URL: http://{args.host}:{args.port}")
    print(f"Data Directory: {data_dir}")
    print("=" * 80)

    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()
