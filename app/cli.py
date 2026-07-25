"""
CLI entry point for agent-platform.

Usage:
    agent-platform            Start the web server (default)
    agent-platform start      Start the web server
    agent-platform skill-sync Scan skills/ directory and sync to database
"""

import sys
import asyncio


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in ("start", "server"):
        # Default: start the web server
        from app.main import start
        start()
    elif sys.argv[1] == "skill-sync":
        asyncio.run(_run_sync())
    elif sys.argv[1] in ("-h", "--help"):
        print(__doc__)
    else:
        print(f"Unknown command: {sys.argv[1]}")
        print(__doc__)
        sys.exit(1)


async def _run_sync() -> None:
    from app.infrastructure import database as db_module
    from app.core.skill.sync import sync_skills

    # Initialize database
    try:
        await db_module.init_db()
    except Exception as e:
        print(f"[skill-sync] Database init failed: {e}")
        sys.exit(1)

    # Set up global session so sync_skills() can use get_db_session()
    from app.main import _set_db_session
    _set_db_session(db_module.async_session_maker())

    print("Scanning skills/ directory ...")
    result = await sync_skills()
    print(f"  Added:   {result.get('added', 0)}")
    print(f"  Updated: {result.get('updated', 0)}")
    print(f"  Archived: {result.get('archived', 0)}")
    errors = result.get("errors", [])
    if errors:
        print(f"  Errors:  {len(errors)}")
        for e in errors:
            print(f"    - {e}")
    print("Done.")

    # Clean up
    await db_module.close_db()
