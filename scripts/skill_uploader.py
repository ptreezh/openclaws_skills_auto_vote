#!/usr/bin/env python3
"""
Skill 上传管理器

支持便捷上传、自动验证和规范化处理
"""

import os
import sys
import json
import shutil
import zipfile
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List
import hashlib

# 导入自定义异常、日志和验证器
from core.exceptions import UploadError, FileOperationError, ValidationError
from core.logging_config import get_logger
from scripts.skill_validator import SkillValidator


logger = get_logger("arena.uploader")


class SkillUploader:
    """Skill 上传管理器"""

    def __init__(self, upload_dir: str = "../data/uploads",
                 skills_dir: str = "../data/skills"):
        """
        初始化上传管理器

        Args:
            upload_dir: 上传文件存储目录
            skills_dir: 验证通过后的 Skill 存储目录
        """
        self.upload_dir = Path(upload_dir)
        self.skills_dir = Path(skills_dir)
        self.validator = SkillValidator()

        # 创建必要的目录
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.skills_dir.mkdir(parents=True, exist_ok=True)

    def upload_skill(self, source_path: str, skill_name: Optional[str] = None,
                    auto_validate: bool = True) -> Dict:
        """
        上传 Skill

        Args:
            source_path: Skill 源路径（文件夹或 zip 文件）
            skill_name: 自定义 Skill 名称（可选）
            auto_validate: 是否自动验证

        Returns:
            上传结果字典

        Raises:
            UploadError: 上传失败
            ValidationError: 验证失败
        """
        logger.info("Starting skill upload", source_path=source_path)

        source = Path(source_path)

        # 检查源文件
        if not source.exists():
            raise UploadError(
                message="源文件不存在",
                file_name=str(source),
                reason="file_not_found",
            )

        # 解压或复制到临时目录
        temp_dir = self._prepare_upload(source, skill_name)
        if not temp_dir:
            raise UploadError(
                message="上传准备失败",
                file_name=source.name,
                reason="prepare_failed",
            )

        # 生成 Skill ID
        skill_id = self._generate_skill_id(temp_dir.name)
        skill_dir = self.skills_dir / skill_id

        # 自动验证
        validation_result = None
        if auto_validate:
            logger.info("Running automated validation")
            validation_result = self.validator.validate_skill(str(temp_dir))

            # 检查验证结果
            if validation_result['overall_status'] == 'rejected':
                # 清理临时目录
                shutil.rmtree(temp_dir, ignore_errors=True)
                logger.warning(
                    "Skill validation failed, upload rejected",
                    skill_id=skill_id,
                    score=validation_result['compliance_score'],
                    critical=len(validation_result['critical_issues']),
                )

                raise UploadError(
                    message="Skill 验证未通过，上传被拒绝",
                    file_name=source.name,
                    reason="validation_failed",
                    details={
                        "compliance_score": validation_result['compliance_score'],
                        "critical_issues": len(validation_result['critical_issues']),
                    },
                )

        # 移动到目标目录
        logger.info("Moving skill to destination", skill_dir=str(skill_dir))
        shutil.move(str(temp_dir), str(skill_dir))

        # 生成 Skill 元数据
        metadata = self._generate_metadata(skill_dir, skill_id, validation_result)
        metadata_file = self.skills_dir / f"{skill_id}.json"
        metadata_file.write_text(json.dumps(metadata, indent=2, ensure_ascii=False))

        # 生成上传报告
        upload_report = {
            "success": True,
            "skill_id": skill_id,
            "skill_name": metadata['skill_name'],
            "skill_dir": str(skill_dir),
            "uploaded_at": datetime.now().isoformat(),
            "validation_passed": validation_result['overall_status'] != 'rejected' if validation_result else None,
            "compliance_score": validation_result.get('compliance_score') if validation_result else None,
            "validation_result": validation_result
        }

        # 保存上传记录
        upload_record_file = self.upload_dir / f"upload-{skill_id}.json"
        upload_record_file.write_text(json.dumps(upload_report, indent=2, ensure_ascii=False))

        logger.info(
            "Skill uploaded successfully",
            skill_id=skill_id,
            skill_name=metadata['skill_name'],
            score=validation_result.get('compliance_score') if validation_result else None,
        )

        return upload_report

    def _prepare_upload(self, source: Path, skill_name: Optional[str]) -> Optional[Path]:
        """
        准备上传文件

        Args:
            source: 源文件或目录
            skill_name: 自定义名称

        Returns:
            临时目录路径

        Raises:
            UploadError: 准备失败
        """
        logger.info("Preparing upload", file_name=source.name)

        # 创建临时目录
        temp_dir = self.upload_dir / f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        if source.is_file() and source.suffix == '.zip':
            # 处理 zip 文件
            logger.info("Extracting ZIP file")
            try:
                with zipfile.ZipFile(source, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)

                # 检查解压后的内容
                extracted_items = list(temp_dir.iterdir())
                if len(extracted_items) == 1 and extracted_items[0].is_dir():
                    # 如果只包含一个目录，移动内容
                    inner_dir = extracted_items[0]
                    for item in inner_dir.iterdir():
                        shutil.move(str(item), str(temp_dir / item.name))
                    shutil.rmtree(inner_dir)

                logger.info("ZIP extraction completed")
                return temp_dir

            except Exception as e:
                shutil.rmtree(temp_dir, ignore_errors=True)
                raise UploadError(
                    message="解压 ZIP 文件失败",
                    file_name=source.name,
                    reason="zip_extraction_failed",
                ) from e

        elif source.is_dir():
            # 处理目录
            logger.info("Copying directory")
            try:
                # 如果有自定义名称，使用自定义名称
                target_dir = temp_dir / (skill_name if skill_name else source.name)
                shutil.copytree(source, target_dir)

                # 如果创建的是子目录，将内容移到 temp_dir
                if target_dir != temp_dir:
                    for item in target_dir.iterdir():
                        shutil.move(str(item), str(temp_dir / item.name))
                    shutil.rmtree(target_dir)

                logger.info("Directory copy completed")
                return temp_dir

            except Exception as e:
                shutil.rmtree(temp_dir, ignore_errors=True)
                raise UploadError(
                    message="复制目录失败",
                    file_name=source.name,
                    reason="directory_copy_failed",
                ) from e

        else:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise UploadError(
                message="不支持的文件类型",
                file_name=source.name,
                reason="unsupported_file_type",
            )

    def _generate_skill_id(self, skill_name: str) -> str:
        """生成唯一的 Skill ID"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        unique_str = f"{skill_name}_{timestamp}"
        hash_obj = hashlib.md5(unique_str.encode())
        return f"skill-{hash_obj.hexdigest()[:12]}"

    def _generate_metadata(self, skill_dir: Path, skill_id: str,
                           validation_result: Optional[Dict]) -> Dict:
        """生成 Skill 元数据"""
        # 尝试从 SKILL.md 读取基本信息
        skill_md = skill_dir / "SKILL.md"
        skill_name = skill_dir.name
        description = ""
        author = ""
        version = "1.0.0"

        if skill_md.exists():
            try:
                content = skill_md.read_text(encoding='utf-8')

                # 提取名称
                import re
                name_match = re.search(r'name:\s*["\']?([^"\'\n]+)["\']?', content)
                if name_match:
                    skill_name = name_match.group(1).strip()

                # 提取描述
                desc_match = re.search(r'description:\s*["\']([^"\']+)', content)
                if desc_match:
                    description = desc_match.group(1).strip()

            except Exception as e:
                logger.warning("Failed to read SKILL.md", exception=e)

        # 计算文件统计
        file_stats = self._calculate_file_stats(skill_dir)

        metadata = {
            "skill_id": skill_id,
            "skill_name": skill_name,
            "description": description,
            "author": author,
            "version": version,
            "uploaded_at": datetime.now().isoformat(),
            "file_stats": file_stats,
            "validation": validation_result,
            "status": "active"
        }

        return metadata

    def _calculate_file_stats(self, skill_dir: Path) -> Dict:
        """计算文件统计信息"""
        stats = {
            "total_files": 0,
            "total_size_bytes": 0,
            "file_types": {},
            "directories": []
        }

        for item in skill_dir.rglob('*'):
            if item.is_file():
                stats["total_files"] += 1
                stats["total_size_bytes"] += item.stat().st_size

                # 统计文件类型
                ext = item.suffix.lower()
                if ext:
                    stats["file_types"][ext] = stats["file_types"].get(ext, 0) + 1
            elif item.is_dir() and item != skill_dir:
                stats["directories"].append(item.name)

        return stats

    def list_uploaded_skills(self) -> List[Dict]:
        """列出已上传的 Skills"""
        skills = []

        # 遍历 skills 目录
        for skill_id_dir in self.skills_dir.iterdir():
            if skill_id_dir.is_dir():
                metadata_file = self.skills_dir / f"{skill_id_dir.name}.json"
                if metadata_file.exists():
                    try:
                        metadata = json.loads(metadata_file.read_text(encoding='utf-8'))
                        skills.append(metadata)
                    except Exception as e:
                        logger.warning("Failed to read metadata", file=metadata_file.name, exception=e)

        return skills

    def get_upload_status(self, skill_id: str) -> Optional[Dict]:
        """获取上传状态"""
        upload_record = self.upload_dir / f"upload-{skill_id}.json"
        if upload_record.exists():
            return json.loads(upload_record.read_text(encoding='utf-8'))
        return None


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(description="Skill 上传管理器")
    parser.add_argument("source", help="Skill 源路径（文件夹或 zip 文件）")
    parser.add_argument("--name", help="自定义 Skill 名称")
    parser.add_argument("--no-validate", action="store_true",
                        help="跳过自动验证（不推荐）")
    parser.add_argument("--list", action="store_true", help="列出已上传的 Skills")
    parser.add_argument("--status", help="查询指定 Skill 的上传状态")

    args = parser.parse_args()

    # 创建上传管理器
    uploader = SkillUploader()

    # 列出 Skills
    if args.list:
        skills = uploader.list_uploaded_skills()
        print(f"\n已上传 {len(skills)} 个 Skills:\n")
        for skill in skills:
            print(f"  • {skill['skill_name']} ({skill['skill_id']})")
            print(f"    上传时间: {skill['uploaded_at']}")
            print(f"    合规分数: {skill.get('compliance_score', 'N/A')}/100")
            print()
        return

    # 查询状态
    if args.status:
        status = uploader.get_upload_status(args.status)
        if status:
            print(json.dumps(status, indent=2, ensure_ascii=False))
        else:
            print(f"未找到 Skill: {args.status}")
            return

    # 上传 Skill
    try:
        result = uploader.upload_skill(
            args.source,
            skill_name=args.name,
            auto_validate=not args.no_validate
        )

        if result["success"]:
            print(f"\n✅ 上传成功!")
            print(f"Skill ID: {result['skill_id']}")
            sys.exit(0)
    except UploadError as e:
        print(f"\n❌ 上传失败: {e.message}")
        if e.details:
            print(f"详情: {e.details}")
        sys.exit(1)


if __name__ == "__main__":
    main()
