"""
Sync skills from the filesystem (skills/*/) into the database.

Scans the skills/ directory, parses each skill's skill.yaml,
and syncs metadata into the skill_definitions table.
Designed to be called both from CLI (agent-platform skill-sync)
and from the web API (POST /admin/skills/sync).
"""

import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

_PROJECT_ROOT: Path | None = None


def _get_project_root() -> Path:
    """Find the project root directory (where skills/ lives)."""
    global _PROJECT_ROOT
    if _PROJECT_ROOT is not None:
        return _PROJECT_ROOT
    # Derive from this file's location: app/core/skill/sync.py → ../../../
    _PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
    return _PROJECT_ROOT


def _git_commit_for(path: Path) -> str | None:
    """Get the latest commit hash for a path within the git repo."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%H", "--", str(path)],
            capture_output=True,
            text=True,
            cwd=_get_project_root(),
            timeout=10,
        )
        commit = result.stdout.strip()
        return commit if commit and len(commit) == 40 else None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def _read_yaml(path: Path) -> dict[str, Any] | None:
    """Read and parse a YAML file, returning None on failure."""
    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
            return data if isinstance(data, dict) else None
    except Exception:
        return None


async def sync_skills() -> dict[str, Any]:
    """
    Scan skills/ directory and sync all skills into the database.

    Returns a summary dict with added/updated/skipped/archived counts.
    """
    from app.main import get_db_session
    from sqlalchemy import select
    from app.infrastructure.models.skill_definition import SkillDefinition

    session = get_db_session()
    if session is None:
        return {"status": "error", "message": "Database not configured"}

    root = _get_project_root()
    skills_dir = root / "skills"

    if not skills_dir.is_dir():
        return {"status": "error", "message": f"skills/ directory not found at {skills_dir}"}

    # Collect all skill directories from filesystem
    fs_names: set[str] = set()
    results: dict[str, Any] = {"added": 0, "updated": 0, "archived": 0, "errors": []}

    for entry in sorted(skills_dir.iterdir()):
        if not entry.is_dir():
            continue

        yaml_path = entry / "skill.yaml"
        if not yaml_path.is_file():
            results["errors"].append(f"{entry.name}: missing skill.yaml, skipped")
            continue

        yaml_data = _read_yaml(yaml_path)
        if yaml_data is None:
            results["errors"].append(f"{entry.name}: invalid skill.yaml, skipped")
            continue

        name = yaml_data.get("name", entry.name)
        description = yaml_data.get("description", "")
        tags = yaml_data.get("tags", [])
        version = str(yaml_data.get("version", "1.0.0"))
        rel_path = f"skills/{entry.name}"

        # Get git commit for this skill directory
        git_hash = _git_commit_for(entry)

        fs_names.add(entry.name)

        # Upsert into database
        try:
            from sqlalchemy import text as _t
            # Check if exists
            existing = await session.execute(
                select(SkillDefinition).where(SkillDefinition.name == name)
            )
            skill = existing.scalar_one_or_none()

            if skill:
                skill.description = description
                skill.tags = tags
                skill.path = rel_path
                skill.version = version
                if git_hash:
                    skill.git_commit_hash = git_hash
                skill.updated_at = datetime.now()
                results["updated"] += 1
            else:
                skill = SkillDefinition(
                    name=name,
                    description=description,
                    tags=tags,
                    path=rel_path,
                    version=version,
                    git_commit_hash=git_hash or "",
                    status="active",
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
                session.add(skill)
                results["added"] += 1

            await session.commit()
        except Exception as e:
            await session.rollback()
            results["errors"].append(f"{entry.name}: DB error - {e}")

    # Mark as archived any skills in DB that no longer exist on filesystem
    try:
        all_db = await session.execute(
            select(SkillDefinition).where(SkillDefinition.status == "active")
        )
        for db_skill in all_db.scalars().all():
            if db_skill.name not in fs_names:
                db_skill.status = "archived"
                db_skill.updated_at = datetime.now()
                results["archived"] += 1
        await session.commit()
    except Exception as e:
        await session.rollback()
        results["errors"].append(f"Archive step: {e}")

    return {
        "status": "ok",
        "added": results["added"],
        "updated": results["updated"],
        "archived": results["archived"],
        "errors": results["errors"],
    }
