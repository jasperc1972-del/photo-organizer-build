"""全自動照片整理（雙擊執行版）

- 若程式旁邊有「舊照片」資料夾，就整理該資料夾；否則整理程式所在的資料夾。
- 依拍攝日期（EXIF，若無則用檔案修改時間）複製到「整理後照片/年-月」。
- 無法取得日期的照片放到「整理後照片/unclassified」。
- 原始照片不會被移動或修改。
"""

import shutil
import sys
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import ttk

from PIL import Image

PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".tif", ".tiff", ".bmp", ".gif", ".webp"}
SOURCE_NAME = "舊照片"
OUTPUT_NAME = "整理後照片"
UNCLASSIFIED = "unclassified"
LOG_NAME = "整理結果.txt"

EXIF_IFD = 0x8769
TAG_DATETIME_ORIGINAL = 36867
TAG_DATETIME_DIGITIZED = 36868
TAG_DATETIME = 0x0132


def app_dir():
    # 打包成 exe 後要用 exe 本身的位置，而不是暫存解壓目錄
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


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


def get_photo_date(path):
    dt = read_exif_date(path)
    if dt:
        return dt, "EXIF"
    try:
        return datetime.fromtimestamp(path.stat().st_mtime), "修改時間"
    except OSError:
        return None, None


def unique_path(dest):
    if not dest.exists():
        return dest
    i = 1
    while True:
        candidate = dest.with_name(f"{dest.stem}_{i}{dest.suffix}")
        if not candidate.exists():
            return candidate
        i += 1


class OrganizerWindow:
    def __init__(self, root):
        self.root = root
        root.title("照片整理")
        root.geometry("460x220")
        root.resizable(False, False)

        self.label = tk.Label(root, text="準備中…", font=("Microsoft JhengHei", 11),
                              justify="left", anchor="w", wraplength=420)
        self.label.pack(fill="x", padx=20, pady=(20, 10))

        self.progress = ttk.Progressbar(root, length=420, mode="determinate")
        self.progress.pack(padx=20)

        self.button = tk.Button(root, text="關閉", width=10, state="disabled",
                                font=("Microsoft JhengHei", 10), command=root.destroy)
        self.button.pack(side="bottom", pady=15)

        root.after(100, self.run)

    def set_text(self, text):
        self.label.config(text=text)
        self.root.update()

    def run(self):
        base = app_dir()
        source = base / SOURCE_NAME
        if not source.is_dir():
            source = base
        output = base / OUTPUT_NAME

        photos = sorted(p for p in source.rglob("*")
                        if p.is_file() and p.suffix.lower() in PHOTO_EXTS
                        and output not in p.parents)
        total = len(photos)
        if total == 0:
            self.finish(f"在以下資料夾找不到照片：\n{source}")
            return

        self.progress["maximum"] = total
        counts = {"EXIF": 0, "修改時間": 0}
        unclassified, failed, log = [], [], []

        for i, photo in enumerate(photos, 1):
            rel = photo.relative_to(source)
            self.set_text(f"整理中 {i}/{total}\n{rel}")
            try:
                dt, kind = get_photo_date(photo)
                folder = dt.strftime("%Y-%m") if dt else UNCLASSIFIED
                dest = unique_path(output / folder / photo.name)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(photo, dest)
                if dt:
                    counts[kind] += 1
                    log.append(f"{rel} -> {folder}（{kind}）")
                else:
                    unclassified.append(rel)
                    log.append(f"{rel} -> {UNCLASSIFIED}（無日期）")
            except Exception as e:
                failed.append(rel)
                log.append(f"{rel} -> 失敗：{e}")
            self.progress["value"] = i

        archived = counts["EXIF"] + counts["修改時間"]
        summary = (f"完成！共 {total} 張照片\n"
                   f"成功歸檔：{archived} 張（EXIF {counts['EXIF']}，修改時間 {counts['修改時間']}）\n"
                   f"無日期 unclassified：{len(unclassified)} 張　失敗：{len(failed)} 張\n"
                   f"詳細清單：{OUTPUT_NAME}\\{LOG_NAME}")

        output.mkdir(exist_ok=True)
        (output / LOG_NAME).write_text(
            f"來源：{source}\n執行時間：{datetime.now():%Y-%m-%d %H:%M:%S}\n\n"
            + summary + "\n\n" + "\n".join(log) + "\n",
            encoding="utf-8")

        self.finish(summary)

    def finish(self, text):
        self.set_text(text)
        self.button.config(state="normal")


if __name__ == "__main__":
    root = tk.Tk()
    OrganizerWindow(root)
    root.mainloop()
