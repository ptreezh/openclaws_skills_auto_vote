#!/usr/bin/env python3
"""
Skill 规范验证器

自动化检测 Skill 是否符合 agentskills.io 规范
检测硬编码依赖、安全风险和规范合规性
"""

import json
import re
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import hashlib


class SkillValidator:
    """Skill 验证器核心类"""

    # agentskills.io 规范要求
    REQUIRED_FILES = [
        "SKILL.md",
        "scripts/",
        "references/"
    ]

    # 硬编码依赖检测模式
    HARDCODED_PATTERNS = [
        # 本地路径硬编码
        r'https?://localhost:\d+',
        r'https?://127\.0\.0\.1:\d+',
        r'https?://192\.168\.\d+\.\d+:\d+',
        r'file:///.*',
        r'/home/\w+/',
        r'/Users/\w+/',
        r'C:\\Users\\\\w+\\',
        
        # 固定外部 URL（允许的域名白名单）
        r'https?://api\.openai\.com',
        r'https?://api\.anthropic\.com',
        r'https?://generativelanguage\.googleapis\.com',
        r'https?://github\.com',
        r'https?://coze\.cn',
        
        # 内网地址
        r'https?://10\.\d+\.\d+\.\d+',
        r'https?://172\.(1[6-9]|2[0-9]|3[01])\.\d+\.\d+',
        
        # 硬编码密钥提示
        r'api_key\s*=\s*["\'][\w-]{32,}["\']',
        r'secret\s*=\s*["\'][\w-]{32,}["\']',
        r'token\s*=\s*["\'][\w-]{32,}["\']',
        r'password\s*=\s*["\'][\w-]{8,}["\']',
        
        # 硬编码 IP 地址
        r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+\b',
    ]

    # 允许的域名白名单
    ALLOWED_DOMAINS = [
        'api.openai.com',
        'api.anthropic.com',
        'generativelanguage.googleapis.com',
        'github.com',
        'coze.cn',
        'api.coze.cn',
        'openai.com',
        'anthropic.com',
        'googleapis.com',
        'example.com',  # 示例域名
    ]

    # 危险导入检测
    DANGEROUS_IMPORTS = [
        'eval(',
        'exec(',
        '__import__',
        'compile(',
        'subprocess.call',
        'os.system',
        'pickle.loads',
        'yaml.load(',
    ]

    def __init__(self):
        self.validation_results = {
            "overall_status": "pending",
            "compliance_score": 0,
            "total_checks": 0,
            "passed_checks": 0,
            "failed_checks": 0,
            "warnings": [],
            "errors": [],
            "critical_issues": [],
            "hardcoded_dependencies": [],
            "security_risks": [],
            "file_structure_check": {},
            "content_validation": {},
            "validated_at": None
        }

    def validate_skill(self, skill_path: str) -> Dict:
        """
        验证 Skill 包

        Args:
            skill_path: Skill 包路径（可以是文件夹或 zip 文件）

        Returns:
            验证结果字典
        """
        print(f"\n{'='*80}")
        print(f"开始验证 Skill: {skill_path}")
        print(f"{'='*80}")

        skill_dir = Path(skill_path)

        # 检查路径存在
        if not skill_dir.exists():
            self._add_error("路径不存在", f"Skill 路径不存在: {skill_path}")
            self._finalize_validation()
            return self.validation_results

        # 检查是否为目录
        if not skill_dir.is_dir():
            self._add_error("格式错误", f"必须是目录格式: {skill_path}")
            self._finalize_validation()
            return self.validation_results

        # 执行各项验证
        self._check_file_structure(skill_dir)
        self._validate_skill_md(skill_dir)
        self._scan_hardcoded_dependencies(skill_dir)
        self._detect_security_risks(skill_dir)
        self._validate_scripts(skill_dir)
        self._validate_references(skill_dir)

        # 计算合规分数
        self._calculate_compliance_score()

        # 完成验证
        self._finalize_validation()

        return self.validation_results

    def _check_file_structure(self, skill_dir: Path) -> None:
        """检查文件结构是否符合规范"""
        print("\n[1/6] 检查文件结构...")

        results = {}
        self.validation_results["total_checks"] += len(self.REQUIRED_FILES)

        for required in self.REQUIRED_FILES:
            required_path = skill_dir / required
            exists = required_path.exists()

            results[required] = {
                "exists": exists,
                "path": str(required_path),
                "type": "directory" if required.endswith('/') else "file"
            }

            if exists:
                self.validation_results["passed_checks"] += 1
                print(f"  ✓ {required}")
            else:
                self.validation_results["failed_checks"] += 1
                self._add_warning("文件缺失", f"缺少必需文件/目录: {required}")
                print(f"  ✗ {required} (缺失)")

        self.validation_results["file_structure_check"] = results

    def _validate_skill_md(self, skill_dir: Path) -> None:
        """验证 SKILL.md 文件内容"""
        print("\n[2/6] 验证 SKILL.md 文件...")

        skill_md_path = skill_dir / "SKILL.md"
        if not skill_md_path.exists():
            self._add_error("SKILL.md 缺失", "必需的 SKILL.md 文件不存在")
            return

        content = skill_md_path.read_text(encoding='utf-8')

        validation_result = {
            "exists": True,
            "size_bytes": len(content),
            "required_fields": {}
        }

        # 检查必需的字段（基于 agentskills.io 规范）
        required_fields = [
            "name:",
            "description:",
            "---",
            "# "
        ]

        self.validation_results["total_checks"] += len(required_fields)

        for field in required_fields:
            found = field in content
            validation_result["required_fields"][field] = found

            if found:
                self.validation_results["passed_checks"] += 1
                print(f"  ✓ 包含: {field}")
            else:
                self.validation_results["failed_checks"] += 1
                self._add_warning("字段缺失", f"SKILL.md 缺少必需字段: {field}")
                print(f"  ✗ 缺少: {field}")

        # 检查文档完整性
        if len(content) < 100:
            self._add_warning("文档过短", "SKILL.md 内容过少，可能不完整")
            print(f"  ⚠ 文档内容过短 ({len(content)} 字符)")

        validation_result["content_length"] = len(content)
        self.validation_results["content_validation"] = validation_result

    def _scan_hardcoded_dependencies(self, skill_dir: Path) -> None:
        """扫描硬编码依赖"""
        print("\n[3/6] 扫描硬编码依赖...")

        # 需要扫描的文件类型
        file_extensions = ['.py', '.md', '.txt', '.json', '.yaml', '.yml']

        # 扫描所有相关文件
        all_files = []
        for ext in file_extensions:
            all_files.extend(skill_dir.rglob(f"*{ext}"))

        print(f"  扫描 {len(all_files)} 个文件...")

        hardcoded_issues = []

        for file_path in all_files:
            try:
                content = file_path.read_text(encoding='utf-8')
                self._scan_file_for_hardcoded(content, file_path, hardcoded_issues)
            except Exception as e:
                print(f"  ⚠ 无法读取文件: {file_path.name} ({e})")

        self.validation_results["hardcoded_dependencies"] = hardcoded_issues

        if hardcoded_issues:
            self.validation_results["critical_issues"].extend(hardcoded_issues)
            print(f"  ✗ 发现 {len(hardcoded_issues)} 个硬编码依赖问题")
            for issue in hardcoded_issues[:5]:  # 只显示前5个
                print(f"    • {issue['type']}: {issue['pattern']} in {issue['file']}")
            if len(hardcoded_issues) > 5:
                print(f"    • ... 还有 {len(hardcoded_issues) - 5} 个问题")
        else:
            print(f"  ✓ 未发现硬编码依赖")

    def _scan_file_for_hardcoded(self, content: str, file_path: Path, 
                                  issues: List[Dict]) -> None:
        """扫描单个文件的硬编码依赖"""
        lines = content.split('\n')

        for line_num, line in enumerate(lines, 1):
            for pattern in self.HARDCODED_PATTERNS:
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    matched_text = match.group()
                    
                    # 检查是否在允许的域名白名单中
                    if self._is_allowed_domain(matched_text):
                        continue

                    issue = {
                        "type": "硬编码依赖",
                        "severity": self._determine_severity(matched_text),
                        "file": str(file_path.relative_to(file_path.parent.parent)),
                        "line": line_num,
                        "pattern": matched_text,
                        "description": self._describe_issue(matched_text),
                        "suggestion": self._suggest_fix(matched_text)
                    }
                    issues.append(issue)

    def _is_allowed_domain(self, matched_text: str) -> bool:
        """检查是否在允许的域名白名单中"""
        for domain in self.ALLOWED_DOMAINS:
            if domain in matched_text.lower():
                return True
        return False

    def _determine_severity(self, matched_text: str) -> str:
        """确定问题严重程度"""
        matched_lower = matched_text.lower()

        # 高危：本地地址、内网地址
        if any(x in matched_lower for x in ['localhost', '127.0.0.1', '192.168.', '10.', '172.']):
            return "critical"
        
        # 高危：硬编码密钥
        if any(x in matched_lower for x in ['api_key', 'secret', 'token', 'password']):
            if len(matched_text) > 20:  # 看起来像真实的密钥
                return "critical"
        
        # 中危：固定 IP 地址
        if re.match(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+', matched_text):
            return "high"
        
        # 低危：其他硬编码
        return "low"

    def _describe_issue(self, matched_text: str) -> str:
        """描述问题"""
        matched_lower = matched_text.lower()

        if 'localhost' in matched_lower or '127.0.0.1' in matched_lower:
            return "检测到本地地址硬编码，这将导致服务无法在其他环境运行"
        elif '192.168.' in matched_lower or '10.' in matched_lower:
            return "检测到内网地址硬编码，服务将无法公网访问"
        elif 'api_key' in matched_lower or 'secret' in matched_lower:
            return "检测到疑似硬编码的密钥信息，存在严重安全风险"
        elif 'file:///' in matched_lower:
            return "检测到本地文件路径硬编码，跨平台兼容性差"
        else:
            return f"检测到硬编码依赖: {matched_text}"

    def _suggest_fix(self, matched_text: str) -> str:
        """建议修复方案"""
        matched_lower = matched_text.lower()

        if 'localhost' in matched_lower or '127.0.0.1' in matched_lower or '192.168.' in matched_lower:
            return "建议使用环境变量或配置文件，如: os.getenv('API_HOST')"
        elif 'api_key' in matched_lower or 'secret' in matched_lower:
            return "建议从环境变量读取，如: os.getenv('API_KEY')"
        elif 'file:///' in matched_lower or matched_lower.startswith(('/', 'C:\\')):
            return "建议使用相对路径或配置文件"
        else:
            return "建议使用配置项或环境变量"

    def _detect_security_risks(self, skill_dir: Path) -> None:
        """检测安全风险"""
        print("\n[4/6] 检测安全风险...")

        security_issues = []

        # 扫描 Python 文件
        python_files = list(skill_dir.rglob("*.py"))
        print(f"  扫描 {len(python_files)} 个 Python 文件...")

        for file_path in python_files:
            try:
                content = file_path.read_text(encoding='utf-8')
                self._detect_dangerous_code(content, file_path, security_issues)
            except Exception as e:
                print(f"  ⚠ 无法读取文件: {file_path.name} ({e})")

        self.validation_results["security_risks"] = security_issues

        if security_issues:
            self.validation_results["critical_issues"].extend([
                i for i in security_issues if i.get("severity") == "critical"
            ])
            print(f"  ✗ 发现 {len(security_issues)} 个安全问题")
            for issue in security_issues[:5]:
                print(f"    • {issue['type']}: {issue['pattern']} in {issue['file']}")
            if len(security_issues) > 5:
                print(f"    • ... 还有 {len(security_issues) - 5} 个问题")
        else:
            print(f"  ✓ 未发现安全风险")

    def _detect_dangerous_code(self, content: str, file_path: Path, 
                                issues: List[Dict]) -> None:
        """检测危险代码"""
        lines = content.split('\n')

        for line_num, line in enumerate(lines, 1):
            for pattern in self.DANGEROUS_IMPORTS:
                if pattern in line:
                    issue = {
                        "type": "安全风险",
                        "severity": "high" if pattern in ["eval(", "exec(", "subprocess.call", "os.system"] else "medium",
                        "file": str(file_path.relative_to(file_path.parent.parent)),
                        "line": line_num,
                        "pattern": pattern,
                        "description": f"检测到危险函数使用: {pattern}",
                        "suggestion": "请确保使用环境变量配置或经过严格的输入验证"
                    }
                    issues.append(issue)

    def _validate_scripts(self, skill_dir: Path) -> None:
        """验证 scripts 目录"""
        print("\n[5/6] 验证 scripts 目录...")

        scripts_dir = skill_dir / "scripts"
        if not scripts_dir.exists():
            self._add_warning("scripts 缺失", "scripts 目录不存在")
            return

        python_files = list(scripts_dir.glob("*.py"))
        print(f"  发现 {len(python_files)} 个 Python 脚本")

        # 检查每个脚本的基本语法
        syntax_errors = 0
        for py_file in python_files:
            try:
                compile(py_file.read_text(encoding='utf-8'), str(py_file), 'exec')
                print(f"  ✓ {py_file.name}")
            except SyntaxError as e:
                syntax_errors += 1
                self._add_error("语法错误", 
                    f"{py_file.name} 第 {e.lineno} 行: {e.msg}")
                print(f"  ✗ {py_file.name}: 语法错误")

        if syntax_errors > 0:
            self.validation_results["critical_issues"].append({
                "type": "语法错误",
                "count": syntax_errors
            })

    def _validate_references(self, skill_dir: Path) -> None:
        """验证 references 目录"""
        print("\n[6/6] 验证 references 目录...")

        refs_dir = skill_dir / "references"
        if not refs_dir.exists():
            self._add_warning("references 缺失", "references 目录不存在")
            return

        ref_files = list(refs_dir.glob("*"))
        print(f"  发现 {len(ref_files)} 个参考文件")

        for ref_file in ref_files:
            if ref_file.is_file():
                print(f"  ✓ {ref_file.name}")

    def _calculate_compliance_score(self) -> None:
        """计算合规分数"""
        total = self.validation_results["total_checks"]
        passed = self.validation_results["passed_checks"]

        if total == 0:
            score = 0
        else:
            score = int((passed / total) * 100)

        # 扣分：每个严重问题扣 10 分
        critical_count = len(self.validation_results["critical_issues"])
        score = max(0, score - critical_count * 10)

        # 扣分：每个警告扣 5 分
        warning_count = len(self.validation_results["warnings"])
        score = max(0, score - warning_count * 5)

        self.validation_results["compliance_score"] = score

        # 确定总体状态
        if score >= 90 and not self.validation_results["critical_issues"]:
            self.validation_results["overall_status"] = "excellent"
        elif score >= 70:
            self.validation_results["overall_status"] = "good"
        elif score >= 50:
            self.validation_results["overall_status"] = "acceptable"
        else:
            self.validation_results["overall_status"] = "rejected"

    def _add_error(self, error_type: str, message: str) -> None:
        """添加错误"""
        self.validation_results["errors"].append({
            "type": error_type,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })

    def _add_warning(self, warning_type: str, message: str) -> None:
        """添加警告"""
        self.validation_results["warnings"].append({
            "type": warning_type,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })

    def _finalize_validation(self) -> None:
        """完成验证"""
        self.validation_results["validated_at"] = datetime.now().isoformat()

        # 打印总结
        print(f"\n{'='*80}")
        print(f"验证总结")
        print(f"{'='*80}")
        print(f"总体状态: {self._get_status_emoji()} {self.validation_results['overall_status'].upper()}")
        print(f"合规分数: {self.validation_results['compliance_score']}/100")
        print(f"检查项:   {self.validation_results['passed_checks']}/{self.validation_results['total_checks']} 通过")
        print(f"错误:     {len(self.validation_results['errors'])}")
        print(f"警告:     {len(self.validation_results['warnings'])}")
        print(f"严重问题: {len(self.validation_results['critical_issues'])}")
        print(f"{'='*80}\n")

    def _get_status_emoji(self) -> str:
        """获取状态对应的 emoji"""
        status = self.validation_results.get("overall_status", "pending")
        emojis = {
            "excellent": "🌟",
            "good": "✅",
            "acceptable": "⚠️",
            "rejected": "❌",
            "pending": "⏳"
        }
        return emojis.get(status, "❓")

    def generate_report(self, output_file: Optional[str] = None) -> str:
        """
        生成验证报告

        Args:
            output_file: 输出文件路径（可选）

        Returns:
            报告内容
        """
        report = f"""
# Skill 规范验证报告

**验证时间**: {self.validation_results['validated_at']}
**总体状态**: {self.validation_results['overall_status'].upper()}
**合规分数**: {self.validation_results['compliance_score']}/100

---

## 检查概要

| 指标 | 数值 |
|------|------|
| 总检查项 | {self.validation_results['total_checks']} |
| 通过项 | {self.validation_results['passed_checks']} |
| 失败项 | {self.validation_results['failed_checks']} |
| 错误数 | {len(self.validation_results['errors'])} |
| 警告数 | {len(self.validation_results['warnings'])} |
| 严重问题 | {len(self.validation_results['critical_issues'])} |

---

## 文件结构检查

{'✅' if self.validation_results['file_structure_check'].get('SKILL.md', {}).get('exists') else '❌'} SKILL.md
{'✅' if self.validation_results['file_structure_check'].get('scripts/', {}).get('exists') else '❌'} scripts/
{'✅' if self.validation_results['file_structure_check'].get('references/', {}).get('exists') else '❌'} references/

---

## 硬编码依赖问题

{len(self.validation_results['hardcoded_dependencies'])} 个硬编码依赖问题

"""
        # 添加硬编码依赖详情
        if self.validation_results['hardcoded_dependencies']:
            report += "\n### 详情\n\n"
            for idx, issue in enumerate(self.validation_results['hardcoded_dependencies'], 1):
                report += f"""
{idx}. **{issue['type']}** ({issue['severity']})
   - 文件: `{issue['file']}`
   - 行号: {issue['line']}
   - 模式: `{issue['pattern']}`
   - 描述: {issue['description']}
   - 建议: {issue['suggestion']}

"""

        # 添加安全风险
        report += f"""

## 安全风险

{len(self.validation_results['security_risks'])} 个安全问题

"""
        if self.validation_results['security_risks']:
            report += "\n### 详情\n\n"
            for idx, issue in enumerate(self.validation_results['security_risks'], 1):
                report += f"""
{idx}. **{issue['type']}** ({issue['severity']})
   - 文件: `{issue['file']}`
   - 行号: {issue['line']}
   - 模式: `{issue['pattern']}`
   - 描述: {issue['description']}
   - 建议: {issue['suggestion']}

"""

        # 添加错误和警告
        report += "\n## 错误列表\n\n"
        if self.validation_results['errors']:
            for error in self.validation_results['errors']:
                report += f"- {error['type']}: {error['message']}\n"
        else:
            report += "无错误\n"

        report += "\n## 警告列表\n\n"
        if self.validation_results['warnings']:
            for warning in self.validation_results['warnings']:
                report += f"- {warning['type']}: {warning['message']}\n"
        else:
            report += "无警告\n"

        # 保存到文件
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"报告已保存到: {output_file}")

        return report


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="Skill 规范验证器")
    parser.add_argument("skill_path", help="Skill 包路径")
    parser.add_argument("--report", help="保存验证报告到文件")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")

    args = parser.parse_args()

    # 创建验证器
    validator = SkillValidator()

    # 执行验证
    results = validator.validate_skill(args.skill_path)

    # 输出结果
    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        # 生成报告
        report = validator.generate_report(args.report)
        if not args.report:
            print(report)

    # 返回退出码
    if results['overall_status'] in ['rejected', 'acceptable']:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
