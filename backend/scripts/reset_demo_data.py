import os
import sys
import asyncio
from pathlib import Path

# Add backend to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text
from app.core.config import settings

async def reset_demo_database():
    print("\n" + "=" * 80)
    print(" METRIXA SAFE DEMO DATA RESET")
    print("=" * 80 + "\n")

    # Safety Guard: Never allow reset in production
    if settings.ENVIRONMENT.lower() in ("production", "prod"):
        print("[CRITICAL ERROR] Cannot execute demo reset in PRODUCTION environment.")
        print("This operation is strictly prohibited outside of development.")
        sys.exit(1)

    print(f"[*] Environment verified: {settings.ENVIRONMENT} (Safe to proceed)")
    print(f"[*] Connecting to database: {settings.DATABASE_URL.split('@')[-1]}")

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    tables_to_clean = [
        "inspection_reports",
        "evidence_items",
        "rule_evaluations",
        "observations",
        "entity_parsing_runs",
        "pdp_geometries",
        "ocr_regions",
        "ocr_runs",
        "inspection_surfaces",
        "inspections",
        "label_versions",
        "products",
        "audit_logs",
    ]

    async with async_session() as session:
        print("[*] Truncating demonstration tables...")
        truncate_query = f"TRUNCATE TABLE {', '.join(tables_to_clean)} CASCADE;"
        try:
            await session.execute(text(truncate_query))
            await session.commit()
            print("  [+] Successfully truncated demonstration tables.")
        except Exception as e:
            print(f"  [!] Truncate note: {e}")
            await session.rollback()

    await engine.dispose()
    print("[SUCCESS] Database tables truncated cleanly.")

    # Call seed_phase10_demo to regenerate pristine demo data
    print("\n[*] Re-seeding pristine SIH 2026 demonstration packages...")
    from scripts.seed_phase10_demo import seed_phase10_demo
    seed_phase10_demo()

if __name__ == "__main__":
    asyncio.run(reset_demo_database())
