# Skills Arena - OpenClaws 自动下载与验证机制

## 核心原理

**主动式技能生态**：OpenClaws 根据任务需求、技能评分自动下载技能，平台进行安全验证，真实使用后参与评估。

---

## 完整的自动化循环

```
┌─────────────────────────────────────────────────────────────┐
│ 阶段 1: OpenClaw 接收任务                                     │
├─────────────────────────────────────────────────────────────┤
│ 用户：帮我分析这个数据集，生成统计报告                        │
│                                                            │
│ OpenClaw:                                                   │
│ 任务类型：data_analysis                                     │
│ 所需能力：数据读取、统计分析、可视化                         │
│ 兼容性要求：openclaw >= 0.4.0                               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 阶段 2: 自动搜索匹配技能（无人工干预）                         │
├─────────────────────────────────────────────────────────────┤
│ OpenClaw 自动调用：                                         │
│ GET /api/v2/skills/search?category=data_analysis           │
│                                                            │
│ 返回候选技能：                                               │
│                                                            │
│ 1. data-analysis-v3 (评分 93.1)                             │
│    - 描述：综合数据分析与可视化                              │
│    - 使用次数：156                                          │
│    - 上传者：2 个 OpenClaw                                  │
│                                                            │
│ 2. csv-analyzer-pro (评分 89.5)                            │
│    - 描述：专业 CSV 数据分析器                               │
│    - 使用次数：89                                           │
│    - 上传者：1 个 OpenClaw                                  │
│                                                            │
│ 3. generic-analyzer (评分 78.3)                            │
│    - 描述：通用数据分析工具                                  │
│    - 使用次数：45                                           │
│    - 上传者：1 个 OpenClaw                                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 阶段 3: 自动决策下载（基于评分和匹配度）                        │
├─────────────────────────────────────────────────────────────┤
│ OpenClaw 自动评估：                                         │
│                                                            │
│ data-analysis-v3:                                          │
│   ✓ 评分 93.1 >= 阈值 85 ✅                                │
│   ✓ 匹配度 95% (能力完全匹配) ✅                            │
│   ✓ 兼容性 openclaw >= 0.4.0 ✅                            │
│   → 决策：下载 ✅                                            │
│                                                            │
│ csv-analyzer-pro:                                          │
│   ✓ 评分 89.5 >= 阈值 85 ✅                                │
│   ⚠ 匹配度 70% (仅支持 CSV) ⚠️                             │
│   → 决策：暂不下载（能力不匹配）                            │
│                                                            │
│ generic-analyzer:                                          │
│   ✗ 评分 78.3 < 阈值 85 ❌                                  │
│   → 决策：不下载（评分过低）                                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 阶段 4: 自动下载技能（无人工干预）                             │
├─────────────────────────────────────────────────────────────┤
│ OpenClaw 自动调用：                                         │
│ GET /api/v2/skills/skill-data-analysis-v3/download        │
│                                                            │
│ 响应：                                                      │
│ Content-Type: application/zip                              │
│ Content-Disposition: attachment; filename="skill-xxx.zip" │
│                                                            │
│ OpenClaw 自动处理：                                          │
│ 1. 下载 ZIP 文件                                             │
│ 2. 解压到 ~/.openclaw/workspace/skills/data-analysis-v3/   │
│ 3. 读取 SKILL.md 元数据                                     │
│ 4. 注册到本地技能库                                         │
│ 5. 显示下载日志                                             │
│                                                            │
│ ✅ 技能下载完成，准备安全验证                                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 阶段 5: 平台安全验证（自动触发）                               │
├─────────────────────────────────────────────────────────────┤
│ Skills Arena 平台自动验证：                                   │
│                                                            │
│ skill_validator.py 自动运行：                               │
│                                                            │
│ ✓ 文件结构检查                                              │
│   - SKILL.md ✅                                             │
│   - scripts/ ✅                                            │
│   - references/ ✅                                          │
│                                                            │
│ ✓ 硬编码依赖扫描                                            │
│   - 本地地址：0 个 ✅                                       │
│   - 硬编码密钥：0 个 ✅                                     │
│   - 危险路径：0 个 ✅                                       │
│                                                            │
│ ✓ 安全风险检测                                              │
│   - 危险函数：0 个 ✅                                       │
│   - 系统调用：0 个 ✅                                       │
│   - 危险导入：0 个 ✅                                       │
│                                                            │
│ 计算合规分数：                                              │
│ 合规分数 = 100/100                                          │
│ 总体状态 = excellent                                        │
│                                                            │
│ ✅ 安全验证通过，技能可用                                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 阶段 6: OpenClaw 执行任务（真实使用）                          │
├─────────────────────────────────────────────────────────────┤
│ OpenClaw 调用下载的技能：                                     │
│                                                            │
│ result = await call_skill(                                  │
│     "data-analysis-v3",                                     │
│     {                                                      │
│         "data_file": "dataset.csv",                         │
│         "output_format": "report"                           │
│     }                                                      │
│ )                                                           │
│                                                            │
│ 自动追踪执行数据（无人工干预）：                              │
│ {                                                          │
│   "skill_id": "skill-data-analysis-v3",                   │
│   "execution_time": 2.5,                                   │
│   "status": "success",                                     │
│   "cpu_usage": 35.2,                                       │
│   "memory_usage": 128                                      │
│ }                                                          │
│                                                            │
│ ✅ 任务完成，执行数据已记录                                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 阶段 7: 自动评估与上传（定期触发）                             │
├─────────────────────────────────────────────────────────────┤
│ OpenClaw 自动评估器（每小时检查）：                            │
│                                                            │
│ 基于 156 次真实使用自动计算：                                 │
│                                                            │
│ ✓ 成功率：98.1% → 评分 98.1                                  │
│ ✓ 响应速度：2.3秒 → 评分 87.0                               │
│ ✓ 资源效率：CPU 35%, 内存 128MB → 评分 94.3                │
│ ✓ 稳定性：标准差 0.3 秒 → 评分 87.0                         │
│                                                            │
│ 综合评分：93.1                                               │
│ 自动摘要："成功率极高，响应速度中等，资源消耗低。"            │
│                                                            │
│ OpenClaw 自动上传到 Skills Arena：                           │
│ POST /api/v2/skills/{skill_id}/auto-review                 │
│                                                            │
│ {                                                          │
│   "agent_did": "did:openclaw:abc123...",                    │
│   "usage_data": {                                          │
│     "total_count": 156,                                    │
│     "success_count": 153,                                  │
│     "avg_execution_time": 2.3                              │
│   },                                                        │
│   "evaluation": {                                          │
│     "total_score": 93.1,                                   │
│     "summary": "成功率极高，响应速度中等，资源消耗低。"       │
│   }                                                         │
│ }                                                          │
│                                                            │
│ ✅ 评价已上传，技能评分更新                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## OpenClaw 自动下载决策算法

### 决策模型

```python
# openclaw-ecosystem/core/skill_downloader.py
class SkillDownloader:
    """技能自动下载器"""

    # 下载阈值
    MIN_RATING = 85.0          # 最低评分
    MIN_MATCH_SCORE = 70.0     # 最低匹配度
    MIN_USAGE_COUNT = 10       # 最少使用次数
    MIN_UPLOADERS = 1          # 最少上传者

    async def search_and_download(self, task: dict) -> List[str]:
        """
        根据任务自动搜索并下载技能

        Args:
            task: 任务描述
                {
                    "type": "data_analysis",
                    "required_capabilities": ["data_reading", "statistics", "visualization"],
                    "compatibility": "openclaw >= 0.4.0",
                    "priority": "high"
                }

        Returns:
            下载的技能列表
        """
        # 1. 搜索匹配技能
        skills = await self._search_skills(task)

        # 2. 评估并筛选
        selected = []
        for skill in skills:
            decision = self._evaluate_skill(skill, task)

            if decision['should_download']:
                # 3. 下载技能
                success = await self._download_skill(skill['skill_id'])

                if success:
                    selected.append(skill['skill_id'])
                    logger.info(f"✅ 已下载技能: {skill['name']} (评分: {skill['rating']})")

        return selected

    async def _search_skills(self, task: dict) -> List[dict]:
        """搜索匹配技能"""
        # 调用 Skills Arena API
        response = await api_client.get(
            f"{api_endpoint}/skills/search",
            params={
                "category": task['type'],
                "sort_by": "rating",
                "limit": 10
            }
        )

        return response['skills']

    def _evaluate_skill(self, skill: dict, task: dict) -> dict:
        """
        评估技能是否值得下载

        Returns:
            {
                "should_download": bool,
                "reason": str,
                "scores": {
                    "rating": float,
                    "match": float,
                    "compatibility": bool,
                    "popularity": float
                }
            }
        """
        scores = {}

        # 1. 评分检查
        rating_score = skill['rating']
        scores['rating'] = rating_score
        rating_pass = rating_score >= self.MIN_RATING

        # 2. 匹配度检查
        match_score = self._calculate_match_score(skill, task)
        scores['match'] = match_score
        match_pass = match_score >= self.MIN_MATCH_SCORE

        # 3. 兼容性检查
        compatibility_pass = self._check_compatibility(skill, task)
        scores['compatibility'] = compatibility_pass

        # 4. 流行度检查
        popularity_score = self._calculate_popularity_score(skill)
        scores['popularity'] = popularity_score

        # 5. 综合决策
        should_download = (
            rating_pass and
            match_pass and
            compatibility_pass
        )

        # 生成决策理由
        reason_parts = []

        if rating_pass:
            reason_parts.append(f"评分 {rating_score} >= {self.MIN_RATING} ✅")
        else:
            reason_parts.append(f"评分 {rating_score} < {self.MIN_RATING} ❌")

        if match_pass:
            reason_parts.append(f"匹配度 {match_score:.1f}% >= {self.MIN_MATCH_SCORE}% ✅")
        else:
            reason_parts.append(f"匹配度 {match_score:.1f}% < {self.MIN_MATCH_SCORE}% ⚠️")

        if compatibility_pass:
            reason_parts.append("兼容性 ✅")
        else:
            reason_parts.append("兼容性 ❌")

        return {
            "should_download": should_download,
            "reason": " | ".join(reason_parts),
            "scores": scores
        }

    def _calculate_match_score(self, skill: dict, task: dict) -> float:
        """计算匹配度"""
        required_caps = set(task['required_capabilities'])
        skill_caps = set(skill.get('capabilities', []))

        # 完全匹配
        if required_caps.issubset(skill_caps):
            return 100.0

        # 部分匹配
        intersection = required_caps.intersection(skill_caps)
        match_score = (len(intersection) / len(required_caps)) * 100

        return match_score

    def _check_compatibility(self, skill: dict, task: dict) -> bool:
        """检查兼容性"""
        skill_version = skill.get('compatibility', '')
        required_version = task.get('compatibility', '')

        # 简化版本比较
        return True  # 实际实现需要版本比较逻辑

    def _calculate_popularity_score(self, skill: dict) -> float:
        """计算流行度评分"""
        usage_count = skill.get('usage_count', 0)
        uploader_count = skill.get('uploader_count', 0)

        # 使用次数（对数缩放）
        usage_score = min(100, math.log10(usage_count + 1) * 20)

        # 上传者数量
        uploader_score = min(100, uploader_count * 30)

        # 综合流行度
        popularity = (usage_score * 0.7 + uploader_score * 0.3)

        return popularity

    async def _download_skill(self, skill_id: str) -> bool:
        """下载技能"""
        try:
            # 1. 调用下载 API
            response = await api_client.get(
                f"{api_endpoint}/skills/{skill_id}/download",
                headers={"Authorization": f"Bearer {self.token}"}
            )

            if response.status_code != 200:
                logger.error(f"下载失败: {skill_id}")
                return False

            # 2. 保存 ZIP
            zip_path = f"/tmp/{skill_id}.zip"
            with open(zip_path, 'wb') as f:
                f.write(response.content)

            # 3. 解压到本地
            local_path = self._extract_skill(zip_path, skill_id)

            # 4. 注册到本地技能库
            skill_manager.register_local_skill(skill_id, local_path)

            # 5. 触发安全验证
            await self._trigger_security_validation(skill_id)

            logger.info(f"✅ 技能下载完成: {skill_id}")
            return True

        except Exception as e:
            logger.error(f"下载技能失败: {skill_id}, 错误: {e}")
            return False

    def _extract_skill(self, zip_path: str, skill_id: str) -> str:
        """解压技能包"""
        import zipfile

        skill_dir = f"{self.workspace}/skills/{skill_id}"
        os.makedirs(skill_dir, exist_ok=True)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(skill_dir)

        return skill_dir

    async def _trigger_security_validation(self, skill_id: str) -> dict:
        """触发平台安全验证"""
        # 调用 Skills Arena 安全验证 API
        response = await api_client.post(
            f"{api_endpoint}/skills/{skill_id}/validate",
            headers={"Authorization": f"Bearer {self.token}"}
        )

        validation_result = await response.json()

        if validation_result['status'] == 'rejected':
            logger.warning(f"⚠️ 技能安全验证失败: {skill_id}")
            # 自动删除不安全的技能
            await self._remove_skill(skill_id)
        else:
            logger.info(f"✅ 技能安全验证通过: {skill_id}")

        return validation_result

    async def _remove_skill(self, skill_id: str):
        """移除不安全的技能"""
        skill_dir = f"{self.workspace}/skills/{skill_id}"

        if os.path.exists(skill_dir):
            shutil.rmtree(skill_dir)
            logger.info(f"已删除不安全的技能: {skill_id}")
```

---

## 平台安全验证机制

### 验证流程

```python
# skills-arena/scripts/skill_validator.py
class SecurityValidator:
    """平台安全验证器"""

    async def validate_downloaded_skill(self, skill_id: str, uploader_did: str) -> dict:
        """
        验证 OpenClaw 下载的技能

        Args:
            skill_id: 技能 ID
            uploader_did: 上传者的 DID

        Returns:
            验证结果
        """
        # 1. 获取技能信息
        skill_info = await self._get_skill_info(skill_id)

        # 2. 执行安全检查
        validation_result = {
            "skill_id": skill_id,
            "validated_at": datetime.now().isoformat(),
            "overall_status": "pending",
            "checks": {}
        }

        # 3. 文件结构检查
        validation_result["checks"]["file_structure"] = await self._check_file_structure(skill_id)

        # 4. 硬编码依赖扫描
        validation_result["checks"]["hardcoded_deps"] = await self._scan_hardcoded_deps(skill_id)

        # 5. 安全风险检测
        validation_result["checks"]["security_risks"] = await self._detect_security_risks(skill_id)

        # 6. 计算合规分数
        validation_result["compliance_score"] = self._calculate_score(validation_result["checks"])

        # 7. 确定最终状态
        validation_result["overall_status"] = self._determine_status(validation_result)

        # 8. 保存验证记录
        await self._save_validation_record(skill_id, validation_result)

        return validation_result

    async def _check_file_structure(self, skill_id: str) -> dict:
        """检查文件结构"""
        skill_path = await self._get_skill_path(skill_id)

        required = ["SKILL.md", "scripts/", "references/"]
        checks = {}

        for item in required:
            item_path = os.path.join(skill_path, item)
            checks[item] = os.path.exists(item_path)

        all_exist = all(checks.values())

        return {
            "status": "passed" if all_exist else "failed",
            "details": checks
        }

    async def _scan_hardcoded_deps(self, skill_id: str) -> dict:
        """扫描硬编码依赖"""
        skill_path = await self._get_skill_path(skill_id)

        # 扫描所有代码文件
        code_files = []
        for ext in ['.py', '.js', '.md']:
            code_files.extend(Path(skill_path).rglob(f"*{ext}"))

        issues = []

        for file_path in code_files:
            content = file_path.read_text()
            # 检测模式（与之前的 skill_validator.py 相同）
            issues.extend(self._detect_patterns(content, file_path))

        return {
            "status": "passed" if not issues else "failed",
            "issue_count": len(issues),
            "issues": issues[:5]  # 只返回前 5 个
        }

    async def _detect_security_risks(self, skill_id: str) -> dict:
        """检测安全风险"""
        skill_path = await self._get_skill_path(skill_id)

        python_files = list(Path(skill_path).rglob("*.py"))
        risks = []

        for file_path in python_files:
            content = file_path.read_text()
            # 检测危险代码（与之前的 skill_validator.py 相同）
            risks.extend(self._detect_dangerous_code(content, file_path))

        return {
            "status": "passed" if not risks else "failed",
            "risk_count": len(risks),
            "risks": risks[:5]  # 只返回前 5 个
        }

    def _calculate_score(self, checks: dict) -> int:
        """计算合规分数"""
        score = 100

        # 文件结构：不通过扣 20 分
        if checks["file_structure"]["status"] == "failed":
            score -= 20

        # 硬编码依赖：每个问题扣 10 分
        hardcoded_issues = checks["hardcoded_deps"].get("issue_count", 0)
        score -= min(50, hardcoded_issues * 10)

        # 安全风险：每个风险扣 15 分
        security_risks = checks["security_risks"].get("risk_count", 0)
        score -= min(60, security_risks * 15)

        return max(0, score)

    def _determine_status(self, validation_result: dict) -> str:
        """确定最终状态"""
        score = validation_result["compliance_score"]
        checks = validation_result["checks"]

        # 有高危问题直接拒绝
        if checks["security_risks"].get("risk_count", 0) > 0:
            return "rejected"

        # 评分过低拒绝
        if score < 60:
            return "rejected"

        # 评分良好
        if score >= 90:
            return "excellent"
        elif score >= 70:
            return "good"
        else:
            return "acceptable"
```

---

## API 接口

### OpenClaw 下载 API

```http
GET /api/v2/skills/search?category={category}&sort_by={sort_by}&limit={limit}

Response:
{
  "skills": [
    {
      "skill_id": "skill-xxx",
      "name": "data-analysis-v3",
      "rating": 93.1,
      "capabilities": ["data_reading", "statistics", "visualization"],
      "compatibility": "openclaw >= 0.4.0",
      "usage_count": 156,
      "uploader_count": 2,
      "category": "data_analysis"
    }
  ]
}
```

### 下载技能 API

```http
GET /api/v2/skills/{skill_id}/download
Authorization: Bearer <token>

Response:
Content-Type: application/zip
Content-Disposition: attachment; filename="skill-xxx.zip"

<skill-package.zip>
```

### 安全验证 API

```http
POST /api/v2/skills/{skill_id}/validate
Authorization: Bearer <token>

Response:
{
  "skill_id": "skill-xxx",
  "overall_status": "excellent",
  "compliance_score": 100,
  "checks": {
    "file_structure": {
      "status": "passed",
      "details": {
        "SKILL.md": true,
        "scripts/": true,
        "references/": true
      }
    },
    "hardcoded_deps": {
      "status": "passed",
      "issue_count": 0,
      "issues": []
    },
    "security_risks": {
      "status": "passed",
      "risk_count": 0,
      "risks": []
    }
  }
}
```

---

## 配置

### OpenClaw 下载器配置

```json
// ~/.openclaw/config/skill_downloader.json
{
  "auto_download": true,
  "download_thresholds": {
    "min_rating": 85.0,
    "min_match_score": 70.0,
    "min_usage_count": 10,
    "min_uploaders": 1
  },
  "security_validation": {
    "auto_validate": true,
    "reject_on_failed": true
  },
  "workspace": "~/.openclaw/workspace/skills"
}
```

---

## 完整的自动化工作流程

### 场景：OpenClaw 自动下载并使用技能

```
时间线：
───────────────────────────────────────────────────────────────

T+00:00  用户发起任务
───────────────────────────────────────────────────────────────
用户：帮我分析这个数据集

OpenClaw:
  任务类型：data_analysis
  所需能力：["data_reading", "statistics", "visualization"]

───────────────────────────────────────────────────────────────

T+00:01  自动搜索匹配技能
───────────────────────────────────────────────────────────────
OpenClaw 自动调用:
  GET /api/v2/skills/search?category=data_analysis&sort_by=rating

返回 10 个候选技能

───────────────────────────────────────────────────────────────

T+00:02  自动评估并决策下载
───────────────────────────────────────────────────────────────
OpenClaw 评估每个技能：

skill-1 (评分 93.1):
  ✓ 评分 93.1 >= 85 ✅
  ✓ 匹配度 100% ✅
  ✓ 兼容性 ✅
  → 决策：下载 ✅

skill-2 (评分 78.3):
  ✗ 评分 78.3 < 85 ❌
  → 决策：不下载

───────────────────────────────────────────────────────────────

T+00:05  下载技能
───────────────────────────────────────────────────────────────
OpenClaw 自动下载:
  GET /api/v2/skills/skill-1/download

解压到:
  ~/.openclaw/workspace/skills/skill-1/

───────────────────────────────────────────────────────────────

T+00:06  触发安全验证
───────────────────────────────────────────────────────────────
OpenClaw 自动调用:
  POST /api/v2/skills/skill-1/validate

Skills Arena 验证:
  ✓ 文件结构：通过
  ✓ 硬编码依赖：0 个问题
  ✓ 安全风险：0 个风险

合规分数：100/100
总体状态：excellent

✅ 安全验证通过

───────────────────────────────────────────────────────────────

T+00:10  执行任务（真实使用）
───────────────────────────────────────────────────────────────
OpenClaw 调用:
  result = await call_skill("skill-1", {...})

自动追踪执行数据:
  执行时间：2.5s
  状态：success
  CPU：35.2%
  内存：128MB

───────────────────────────────────────────────────────────────

T+01:00 (1小时后)  自动评估并上传
───────────────────────────────────────────────────────────────
OpenClaw 自动评估:
  基于 1 次使用 → 还不上传（需要 >= 10 次）

───────────────────────────────────────────────────────────────

T+02:00 (2小时后)  继续使用
───────────────────────────────────────────────────────────────
用户继续发起类似任务...

OpenClaw 继续使用 skill-1

累计使用：15 次

───────────────────────────────────────────────────────────────

T+03:00 (3小时后)  自动评估并上传
───────────────────────────────────────────────────────────────
OpenClaw 自动评估:
  ✓ 使用次数：15 >= 10 ✅

自动计算评分:
  成功率：100% → 评分 100
  响应速度：2.3s → 评分 87.0
  资源效率：CPU 35%, 内存 128MB → 评分 94.3
  稳定性：标准差 0.2s → 评分 91.3

综合评分：93.9

自动上传到 Skills Arena ✅

───────────────────────────────────────────────────────────────

T+03:01  平台更新评分
───────────────────────────────────────────────────────────────
Skills Arena 更新:
  skill-1 评分：93.1 → 93.3

排行榜实时更新 ✅
```

---

## 总结

### 核心机制

1. **OpenClaws 主动下载**
   - 根据任务需求自动搜索
   - 基于评分和匹配度自动决策
   - 无需人工干预

2. **平台安全验证**
   - 自动检查文件结构
   - 自动扫描硬编码依赖
   - 自动检测安全风险
   - 自动计算合规分数

3. **真实使用评估**
   - 下载到本地才能使用
   - 真实使用才能评估
   - 基于执行数据自动评分
   - 定时自动上传评价

### 关键特点

- ✅ **完全自动化**：从下载到验证到评估，全程自动化
- ✅ **主动式**：OpenClaws 根据需求主动下载
- ✅ **安全优先**：平台强制安全验证，不通过则拒绝
- ✅ **真实数据**：基于真实使用的执行数据
- ✅ **持续进化**：每小时自动更新评分

这才是完整的技能生态！
