"""照片整理 GUI 版打包腳本

- 用 PyInstaller 把 photo_organizer_auto.py 打包成單一 exe（不顯示終端機視窗）。
- 先打包到 build/ 暫存，成功後才覆蓋 dist/照片整理.exe，打包失敗時舊的 exe 不受影響。
- 執行方式：在專案資料夾執行 python build.py
"""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "photo_organizer_auto.py"
APP_NAME = "照片整理"
WORK_DIR = ROOT / "build"
TEMP_DIST = WORK_DIR / "dist"
TARGET = ROOT / "dist" / f"{APP_NAME}.exe"

# 打包前要先裝好的套件：(import 名稱, pip 套件名稱)
REQUIRED = [("PyInstaller", "pyinstaller"), ("PIL", "pillow")]

BUILD_HINTS = """\
錯誤排除建議：
  1. 確認套件已安裝：python -m pip install --upgrade pyinstaller pillow
  2. 先直接執行 python photo_organizer_auto.py，確認程式本身沒有錯誤。
  3. 防毒軟體（如 Windows Defender）可能攔截或刪除新產生的 exe，
     請把 build、dist 資料夾加入排除清單後重試。
  4. 刪除 build 資料夾後重新執行，排除舊快取造成的問題。
  5. 若 Python 版本太新，PyInstaller 可能還不支援，
     請升級 PyInstaller 或改用較舊的 Python 版本打包。"""


def check_dependencies():
    missing = [pip_name for module, pip_name in REQUIRED
               if importlib.util.find_spec(module) is None]
    if missing:
        print(f"缺少套件：{', '.join(missing)}")
        print(f"請先安裝：python -m pip install {' '.join(missing)}")
        return False
    return True


def run_pyinstaller():
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",      # 打包成單一 exe
        "--windowed",     # Tkinter 視窗程式，不顯示終端機視窗
        "--noconfirm",    # 覆蓋舊的暫存輸出不再詢問
        "--clean",        # 清除 PyInstaller 快取，避免舊檔案殘留
        "--name", APP_NAME,
        "--distpath", str(TEMP_DIST),
        "--workpath", str(WORK_DIR),
        "--specpath", str(WORK_DIR),
        str(SCRIPT),
    ]
    print("開始打包，約需一分鐘…")
    return subprocess.run(cmd, cwd=ROOT).returncode == 0


def install_exe():
    built = TEMP_DIST / f"{APP_NAME}.exe"
    if not built.exists():
        print(f"找不到打包結果：{built}")
        print("可能被防毒軟體刪除，請檢查防毒軟體的隔離區。")
        return False
    TARGET.parent.mkdir(exist_ok=True)
    try:
        os.replace(built, TARGET)
    except PermissionError:
        print(f"無法覆蓋 {TARGET}")
        print(f"請先關閉正在執行的「{APP_NAME}.exe」，再重新執行 build.py。")
        return False
    return True


def main():
    if not SCRIPT.exists():
        print(f"找不到主程式：{SCRIPT}")
        return 1
    if not check_dependencies():
        return 1
    if not run_pyinstaller():
        print("\n打包失敗，請查看上方 PyInstaller 的錯誤訊息。")
        print(BUILD_HINTS)
        return 1
    if not install_exe():
        return 1
    size_mb = TARGET.stat().st_size / 1024 / 1024
    print(f"\n打包完成：{TARGET}（{size_mb:.1f} MB）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
