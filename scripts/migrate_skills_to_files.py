"""
One-time migration: dump existing skill content from DB to filesystem.

Run BEFORE executing the ALTER TABLE that drops the `content` column.

Usage:
    python scripts/migrate_skills_to_files.py
"""

import asyncio
import sys
from pathlib import Path


async def migrate():
    # Find project root
    root = Path(__file__).resolve().parent.parent

    from app.infrastructure import database as db_module
    from app.infrastructure.models.skill_definition import SkillDefinition
    from sqlalchemy import select

    await db_module.init_db()

    async with db_module.async_session_maker() as session:
        result = await session.execute(select(SkillDefinition))
        skills = result.scalars().all()

        if not skills:
            print("No existing skills found in DB. Nothing to migrate.")
            return

        skills_dir = root / "skills"
        skills_dir.mkdir(exist_ok=True)

        for s in skills:
            skill_dir = skills_dir / s.name
            skill_dir.mkdir(exist_ok=True)

            prompt_path = skill_dir / "prompt.md"
            yaml_path = skill_dir / "skill.yaml"

            # Write prompt.md
            prompt_path.write_text(s.content or "", encoding="utf-8")
            print(f"  Created: {prompt_path.relative_to(root)}")

            # Write skill.yaml if not exists
            if not yaml_path.exists():
                import yaml
                yaml_data = {
                    "name": s.name,
                    "description": s.description or "",
                    "tags": [],
                    "version": "1.0.0",
                }
                with open(yaml_path, "w", encoding="utf-8") as f:
                    yaml.dump(yaml_data, f, allow_unicode=True, default_flow_style=False)
                print(f"  Created: {yaml_path.relative_to(root)}")

        print(f"\nMigrated {len(skills)} skills. Now run the ALTER TABLE, then:")
        print("  agent-platform skill-sync")


if __name__ == "__main__":
    asyncio.run(migrate())
