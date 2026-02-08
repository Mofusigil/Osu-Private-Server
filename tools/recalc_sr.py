#!/usr/bin/env python3.11
"""
Star-Rating-Rebirth 批量更新工具

使用 Star-Rating-Rebirth 算法重新计算所有 mania 谱面的 SR 并更新到数据库。
"""
from __future__ import annotations

import argparse
import asyncio
import math
import os
import sys
from pathlib import Path

import databases

# 获取脚本所在目录，然后定位到项目根目录
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

try:
    import app.settings
    from app.constants.gamemodes import GameMode
except ModuleNotFoundError:
    print("\x1b[;91mFailed to import app module. Check your installation.\x1b[m")
    raise

# 添加 Star-Rating-Rebirth 支持
sys.path.insert(0, str(Path.cwd() / "Star-Rating-Rebirth"))
try:
    from algorithm import calculate as srr_calculate
    SRR_AVAILABLE = True
except ImportError as e:
    print(f"\x1b[;91mFailed to import Star-Rating-Rebirth: {e}\x1b[m")
    SRR_AVAILABLE = False

BEATMAPS_PATH = Path.cwd() / ".data/osu"


async def main() -> int:
    parser = argparse.ArgumentParser(
        description="Recalculate mania beatmap star ratings using Star-Rating-Rebirth",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Enable debug mode to show each map being updated",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="Don't actually update the database, just show what would be done",
    )
    args = parser.parse_args()

    if not SRR_AVAILABLE:
        print("\x1b[;91mStar-Rating-Rebirth is not available!\x1b[m")
        return 1

    database = databases.Database(app.settings.DB_DSN)
    await database.connect()

    try:
        # 获取所有 mania 谱面 (mode == 3)
        mania_maps = await database.fetch_all(
            "SELECT id, md5, diff, artist, title, version FROM maps WHERE mode = :mode",
            {"mode": GameMode.VANILLA_MANIA},
        )

        print(f"Found {len(mania_maps)} mania beatmaps to process")

        updated_count = 0
        skipped_count = 0
        error_count = 0

        for i, bmap in enumerate(mania_maps):
            osu_file_path = BEATMAPS_PATH / f"{bmap['id']}.osu"

            if not osu_file_path.exists():
                skipped_count += 1
                if args.debug:
                    print(f"[{i+1}/{len(mania_maps)}] Skipped (no file): {bmap['artist']} - {bmap['title']} [{bmap['version']}]")
                continue

            try:
                new_sr = srr_calculate(str(osu_file_path), "NM")

                if math.isnan(new_sr) or math.isinf(new_sr) or new_sr <= 0:
                    error_count += 1
                    if args.debug:
                        print(f"[{i+1}/{len(mania_maps)}] Error (invalid SR): {bmap['artist']} - {bmap['title']} [{bmap['version']}]")
                    continue

                old_sr = float(bmap['diff'])

                if args.debug:
                    print(f"[{i+1}/{len(mania_maps)}] {bmap['artist']} - {bmap['title']} [{bmap['version']}]: {old_sr:.2f} -> {new_sr:.2f}")

                if not args.dry_run:
                    await database.execute(
                        "UPDATE maps SET diff = :new_sr WHERE id = :id",
                        {"new_sr": new_sr, "id": bmap['id']},
                    )

                updated_count += 1

            except Exception as e:
                error_count += 1
                if args.debug:
                    print(f"[{i+1}/{len(mania_maps)}] Error: {bmap['artist']} - {bmap['title']} [{bmap['version']}] - {e}")

            # 每处理 100 个显示进度
            if (i + 1) % 100 == 0:
                print(f"Progress: {i+1}/{len(mania_maps)}")

        print("\n=== Summary ===")
        print(f"Total maps: {len(mania_maps)}")
        print(f"Updated: {updated_count}")
        print(f"Skipped (no file): {skipped_count}")
        print(f"Errors: {error_count}")

        if args.dry_run:
            print("\n(Dry run mode - no changes were made to the database)")

    finally:
        await database.disconnect()

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
