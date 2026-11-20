"""生成多尺寸 ICO（Windows 托盘/资源管理器在各 DPI 下都能取到合适尺寸）。"""
from __future__ import annotations

import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from PySide6.QtCore import QBuffer, QByteArray
from PySide6.QtWidgets import QApplication

SIZES = [16, 24, 32, 48, 64, 128, 256]


def png_bytes(icon, size: int) -> bytes:
    pixmap = icon.pixmap(size, size)
    storage = QByteArray()          # 必须保持引用，QBuffer 只持有指针
    buffer = QBuffer(storage)
    buffer.open(QBuffer.WriteOnly)
    pixmap.save(buffer, "PNG")
    buffer.close()
    return bytes(storage)


def write_ico(path: str, images: list[tuple[int, bytes]]) -> None:
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = len(header) + 16 * len(images)
    entries, blobs = b"", b""
    for size, data in images:
        width = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", width, width, 0, 0, 1, 32, len(data), offset + len(blobs))
        blobs += data
    with open(path, "wb") as fh:
        fh.write(header + entries + blobs)


def main() -> None:
    app = QApplication([])  # noqa: F841  (QPainter 需要 QGuiApplication)
    from app.main import build_icon

    icon = build_icon()
    assets = os.path.join(ROOT, "assets")
    os.makedirs(assets, exist_ok=True)

    images = [(size, png_bytes(icon, size)) for size in SIZES]
    write_ico(os.path.join(assets, "app.ico"), images)
    icon.pixmap(256, 256).save(os.path.join(assets, "app.png"))
    print("icon written:", os.path.join(assets, "app.ico"), f"({len(images)} sizes)")


if __name__ == "__main__":
    main()
