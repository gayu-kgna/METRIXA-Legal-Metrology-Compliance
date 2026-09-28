import sys, os
sys.path.insert(0, os.path.abspath("."))
import asyncio
from app.core.database import AsyncSessionLocal
from sqlalchemy import text

async def check():
    async with AsyncSessionLocal() as session:
        res = await session.execute(text("SELECT id, inspection_number, status, created_at FROM inspections WHERE inspection_number LIKE '%881594%'"))
        rows = res.fetchall()
        print(f"Found {len(rows)} matching inspections:")
        for r in rows:
            print(r)
            
        # Also let's check package_surfaces and package_images for these
        for r in rows:
            surfaces = await session.execute(text(f"SELECT id, surface_type, pdp_area_sq_cm FROM package_surfaces WHERE inspection_id = '{r[0]}'"))
            s_rows = surfaces.fetchall()
            print(f"Surfaces for {r[0]}: {s_rows}")
            for s in s_rows:
                imgs = await session.execute(text(f"SELECT id, surface_type, storage_path, file_hash_sha256 FROM package_images WHERE inspection_id = '{r[0]}'"))
                print(f"Images: {imgs.fetchall()}")

if __name__ == "__main__":
    asyncio.run(check())
