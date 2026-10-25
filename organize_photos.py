"""照片整理與歸檔工具

依照片拍攝日期（EXIF，若沒有則用檔案修改時間）建立「年-月」子資料夾，
並將照片複製（預設）或搬移過去。

用法：
    python organize_photos.py 來源資料夾 目標資料夾 [--move] [--exif-only] [--dry-run]
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

from PIL import Image

PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".tif", ".tiff", ".bmp", ".gif", ".webp"}
UNCLASSIFIED = "unclassified"

EXIF_IFD = 0x8769
TAG_DATETIME_ORIGINAL = 36867  # 拍攝時間
TAG_DATETIME_DIGITIZED = 36868
TAG_DATETIME = 0x0132          # 檔案最後修改時間（相機寫入）


def parse_exif_date(value):
    try:
        dt = datetime.strptime(str(value).strip()[:19], "%Y:%m:%d %H:%M:%S")
    except ValueError:
        return None
    return dt if dt.year > 1900 else None


def read_exif_date(path):
    try:
        with Image.open(path) as img:
            exif = img.getexif()
            sub = exif.get_ifd(EXIF_IFD)
            for value in (sub.get(TAG_DATETIME_ORIGINAL),
                          sub.get(TAG_DATETIME_DIGITIZED),
                          exif.get(TAG_DATETIME)):
                if value:
                    dt = parse_exif_date(value)
                    if dt:
                        return dt
    except Exception:
        pass
    return None


def get_photo_date(path, exif_only):
    """回傳 (日期, 來源)；找不到日期時回傳 (None, None)。"""
    dt = read_exif_date(path)
    if dt:
        return dt, "EXIF"
    if exif_only:
        return None, None
    return datetime.fromtimestamp(path.stat().st_mtime), "修改時間"


def unique_path(dest):
    """目標已有同名檔案時，自動加上 _1、_2 ..."""
    if not dest.exists():
        return dest
    i = 1
    while True:
        candidate = dest.with_name(f"{dest.stem}_{i}{dest.suffix}")
        if not candidate.exists():
            return candidate
        i += 1


def main():
    parser = argparse.ArgumentParser(description="依拍攝年月整理照片")
    parser.add_argument("source", help="來源資料夾（會包含所有子資料夾）")
    parser.add_argument("target", help="整理後的輸出資料夾")
    parser.add_argument("--move", action="store_true", help="搬移檔案（預設為複製，原檔保留）")
    parser.add_argument("--exif-only", action="store_true",
                        help="只採用 EXIF 拍攝日期；沒有 EXIF 的照片放到 unclassified")
    parser.add_argument("--dry-run", action="store_true", help="只預覽結果，不實際複製或搬移")
    args = parser.parse_args()

    source = Path(args.source).resolve()
    target = Path(args.target).resolve()
    if not source.is_dir():
        sys.exit(f"錯誤：找不到來源資料夾 {source}")
    if target == source or source in target.parents:
        print("注意：目標資料夾位於來源資料夾內，會略過目標資料夾中的檔案。")

    photos = sorted(p for p in source.rglob("*")
                    if p.is_file() and p.suffix.lower() in PHOTO_EXTS
                    and target not in p.parents)
    total = len(photos)
    if total == 0:
        print(f"在 {source} 中沒有找到照片。")
        return

    action = "搬移" if args.move else "複製"
    mode = "（預覽模式，不會變更任何檔案）" if args.dry_run else ""
    print(f"找到 {total} 張照片，開始{action}到 {target} {mode}\n")

    stats = {"EXIF": 0, "修改時間": 0}
    unclassified, failed = [], []
    per_folder = {}

    for i, photo in enumerate(photos, 1):
        rel = photo.relative_to(source)
        try:
            dt, src_kind = get_photo_date(photo, args.exif_only)
            folder = dt.strftime("%Y-%m") if dt else UNCLASSIFIED
            dest = unique_path(target / folder / photo.name)

            if not args.dry_run:
                dest.parent.mkdir(parents=True, exist_ok=True)
                if args.move:
                    shutil.move(str(photo), str(dest))
                else:
                    shutil.copy2(photo, dest)

            per_folder[folder] = per_folder.get(folder, 0) + 1
            if dt:
                stats[src_kind] += 1
                note = f"{folder}（{src_kind}）"
            else:
                unclassified.append(rel)
                note = f"{UNCLASSIFIED}（無日期）"
            print(f"[{i}/{total}] {rel} -> {note}")
        except Exception as e:
            failed.append((rel, e))
            print(f"[{i}/{total}] {rel} -> 失敗：{e}")

    archived = stats["EXIF"] + stats["修改時間"]
    print("\n========== 整理結果 ==========")
    print(f"總共處理：{total} 張")
    print(f"成功歸檔：{archived} 張（EXIF 日期 {stats['EXIF']} 張，檔案修改時間 {stats['修改時間']} 張）")
    print(f"無日期（{UNCLASSIFIED}）：{len(unclassified)} 張")
    print(f"失敗：{len(failed)} 張")

    print("\n各資料夾張數：")
    for folder in sorted(per_folder):
        print(f"  {folder}: {per_folder[folder]}")

    if unclassified:
        print(f"\n以下照片沒有日期，已放到 {UNCLASSIFIED}：")
        for rel in unclassified:
            print(f"  {rel}")
    if failed:
        print("\n以下照片處理失敗：")
        for rel, e in failed:
            print(f"  {rel}：{e}")


if __name__ == "__main__":
    main()
