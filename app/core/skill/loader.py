"""
Load skill content from the filesystem.

Called by the ReActAgent at runtime when the model requests a skill.
Reads prompt.md and optionally assembles extension files (examples/*, etc.).
"""

from pathlib import Path


_PROJECT_ROOT: Path | None = None


def _get_project_root() -> Path:
    global _PROJECT_ROOT
    if _PROJECT_ROOT is not None:
        return _PROJECT_ROOT
    _PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
    return _PROJECT_ROOT


async def load_skill_content(name: str) -> str | None:
    """
    Load a skill's content from the filesystem.

    Looks for skills/{name}/prompt.md and optionally appends
    extension files from subdirectories (examples/*, rules/*, etc.).
    Returns None if the skill directory or prompt.md is missing.
    """
    root = _get_project_root()
    skill_dir = root / "skills" / name

    if not skill_dir.is_dir():
        return None

    prompt_path = skill_dir / "prompt.md"
    if not prompt_path.is_file():
        return None

    try:
        with open(prompt_path, encoding="utf-8") as f:
            lines = [f.read()]
    except Exception:
        return None

    # Append extension files (*.md) from subdirectories
    # Order: alphabetically by subdirectory, then by filename
    for sub_dir in sorted(skill_dir.iterdir()):
        if not sub_dir.is_dir() or sub_dir.name.startswith("."):
            continue
        md_files = sorted(sub_dir.glob("*.md"))
        if not md_files:
            continue
        lines.append(f"\n## {sub_dir.name}\n")
        for md_file in md_files:
            try:
                content = md_file.read_text(encoding="utf-8")
                lines.append(content)
            except Exception:
                pass

    return "\n\n---\n\n".join(lines)
