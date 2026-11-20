"""直接运行入口（也供 PyInstaller 打包使用）。"""
import sys

from app.main import main

if __name__ == "__main__":
    sys.exit(main())
