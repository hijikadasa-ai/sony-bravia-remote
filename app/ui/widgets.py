"""自绘基础控件：支持长按连发的按键、方向盘、音量摇杆、电平条、状态点、浮层提示。"""
from __future__ import annotations

import math
from typing import Callable, Optional

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from . import theme


def restyle(widget: QWidget) -> None:
    """动态属性变更后强制重算样式。"""
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def set_variant(widget: QWidget, variant: str) -> None:
    widget.setProperty("variant", variant)
    restyle(widget)


class HoldButton(QPushButton):
    """可长按连发的按键。按下即触发，长按后按固定间隔重复（贴近实体遥控器手感）。"""

    fired = Signal()

    def __init__(
        self,
        text: str = "",
        parent: Optional[QWidget] = None,
        *,
        repeat: bool = False,
        delay_ms: int = 380,
        interval_ms: int = 120,
    ) -> None:
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.NoFocus)
        self._repeat_enabled = repeat
        # 定时器始终创建：hideEvent / 析构路径下也能安全停止，避免事件回调里抛异常
        self._delay = QTimer(self)
        self._delay.setSingleShot(True)
        self._delay.setInterval(delay_ms)
        self._delay.timeout.connect(self._begin_repeat)
        self._interval = QTimer(self)
        self._interval.setInterval(interval_ms)
        self._interval.timeout.connect(self._tick)
        if repeat:
            self.pressed.connect(self._on_press)
            self.released.connect(self._stop)
        else:
            self.clicked.connect(self.fired.emit)

    # -- 连发逻辑 -------------------------------------------------------
    def _on_press(self) -> None:
        self.fired.emit()
        self._delay.start()

    def _begin_repeat(self) -> None:
        self._interval.start()

    def _tick(self) -> None:
        self.fired.emit()

    def _stop(self) -> None:
        self._delay.stop()
        self._interval.stop()

    def hideEvent(self, event) -> None:  # 避免隐藏后仍在连发
        self._stop()
        super().hideEvent(event)


class DPad(QWidget):
    """圆形方向盘：上/下/左/右 + 中央 OK，支持悬停高亮与长按连发。"""

    keyPressed = Signal(str)

    CENTER_R = 46.0

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(218, 218)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)
        self._hover: Optional[str] = None
        self._active: Optional[str] = None
        self._delay = QTimer(self)
        self._delay.setSingleShot(True)
        self._delay.setInterval(400)
        self._delay.timeout.connect(self._begin_repeat)
        self._interval = QTimer(self)
        self._interval.setInterval(120)
        self._interval.timeout.connect(self._tick)

    # -- 几何 -----------------------------------------------------------
    def _radius(self) -> float:
        return min(self.width(), self.height()) / 2.0 - 3.0

    def region_at(self, pos: QPointF) -> Optional[str]:
        cx, cy = self.width() / 2.0, self.height() / 2.0
        dx, dy = pos.x() - cx, pos.y() - cy
        dist = math.hypot(dx, dy)
        if dist > self._radius():
            return None
        if dist <= self.CENTER_R:
            return "Confirm"
        angle = (-math.degrees(math.atan2(dy, dx))) % 360.0  # 屏幕角 -> 数学角
        if 45 <= angle < 135:
            return "Up"
        if 135 <= angle < 225:
            return "Left"
        if 225 <= angle < 315:
            return "Down"
        return "Right"

    # -- 事件 -----------------------------------------------------------
    def mouseMoveEvent(self, event) -> None:
        region = self.region_at(event.position())
        if region != self._hover:
            self._hover = region
            self.update()

    def leaveEvent(self, event) -> None:
        self._hover = None
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.LeftButton:
            return
        region = self.region_at(event.position())
        if not region:
            return
        self._active = region
        self.update()
        self.keyPressed.emit(region)
        self._delay.start()

    def mouseReleaseEvent(self, event) -> None:
        self._active = None
        self._delay.stop()
        self._interval.stop()
        self.update()

    def _begin_repeat(self) -> None:
        if self._active:
            self._interval.start()

    def _tick(self) -> None:
        if self._active:
            self.keyPressed.emit(self._active)

    def hideEvent(self, event) -> None:
        self._delay.stop()
        self._interval.stop()
        super().hideEvent(event)

    # -- 绘制 -----------------------------------------------------------
    def _sector(self, start_deg: float, span_deg: float, radius: float) -> QPainterPath:
        cx, cy = self.width() / 2.0, self.height() / 2.0
        rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
        path = QPainterPath()
        path.moveTo(cx, cy)
        path.arcTo(rect, start_deg, span_deg)
        path.closeSubpath()
        return path

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cx, cy = self.width() / 2.0, self.height() / 2.0
        r = self._radius()

        # 底盘
        base = QRadialGradient(QPointF(cx, cy - r * 0.35), r * 1.6)
        base.setColorAt(0.0, QColor("#242a33"))
        base.setColorAt(1.0, QColor("#171a20"))
        p.setBrush(base)
        p.setPen(QPen(QColor(theme.BORDER), 1.2))
        p.drawEllipse(QPointF(cx, cy), r, r)

        # 扇区高亮（悬停 / 按下）
        for region, (start, span) in {
            "Up": (45, 90),
            "Left": (135, 90),
            "Down": (225, 90),
            "Right": (315, 90),
        }.items():
            if region not in (self._hover, self._active):
                continue
            hovered = region == self._hover
            active = region == self._active
            color = QColor(theme.ACCENT)
            color.setAlpha(64 if active else (40 if hovered else 0))
            p.save()
            clip = QPainterPath()
            clip.addEllipse(QPointF(cx, cy), r - 1, r - 1)
            p.setClipPath(clip)
            p.setPen(Qt.NoPen)
            p.setBrush(color)
            p.drawPath(self._sector(start, span, r))
            p.restore()

        # 箭头
        arrow_len, arrow_half = r * 0.86, 15.0
        highlight = (self._active or self._hover)
        arrows = {
            "Up": [(cx, cy - arrow_len), (cx - arrow_half, cy - arrow_len + 26), (cx + arrow_half, cy - arrow_len + 26)],
            "Down": [(cx, cy + arrow_len), (cx - arrow_half, cy + arrow_len - 26), (cx + arrow_half, cy + arrow_len - 26)],
            "Left": [(cx - arrow_len, cy), (cx - arrow_len + 26, cy - arrow_half), (cx - arrow_len + 26, cy + arrow_half)],
            "Right": [(cx + arrow_len, cy), (cx + arrow_len - 26, cy - arrow_half), (cx + arrow_len - 26, cy + arrow_half)],
        }
        for region, points in arrows.items():
            path = QPainterPath()
            path.moveTo(points[0][0], points[0][1])
            path.lineTo(points[1][0], points[1][1])
            path.lineTo(points[2][0], points[2][1])
            path.closeSubpath()
            if region == highlight:
                p.setBrush(QColor("#ffffff"))
            else:
                p.setBrush(QColor(theme.TEXT_DIM))
            p.setPen(Qt.NoPen)
            p.drawPath(path)

        # 中央 OK
        center_hover = highlight == "Confirm"
        grad = QLinearGradient(cx, cy - self.CENTER_R, cx, cy + self.CENTER_R)
        if center_hover:
            grad.setColorAt(0.0, QColor("#5a9bfb"))
            grad.setColorAt(1.0, QColor(theme.ACCENT_DIM))
        else:
            grad.setColorAt(0.0, QColor("#333a46"))
            grad.setColorAt(1.0, QColor("#222831"))
        p.setBrush(grad)
        p.setPen(QPen(QColor(theme.ACCENT if center_hover else theme.BORDER_HI), 1.4))
        p.drawEllipse(QPointF(cx, cy), self.CENTER_R, self.CENTER_R)

        font = QFont(self.font())
        font.setPointSize(13)
        font.setWeight(QFont.DemiBold)
        p.setFont(font)
        p.setPen(QColor("#ffffff" if center_hover else theme.TEXT))
        p.drawText(QRectF(cx - self.CENTER_R, cy - self.CENTER_R, self.CENTER_R * 2, self.CENTER_R * 2),
                   Qt.AlignCenter, "OK")
        p.end()


class Rocker(QWidget):
    """竖排摇杆：标题 + 加 + 数值 + 减，用于音量与频道。"""

    def __init__(self, title: str, parent: Optional[QWidget] = None, *, show_value: bool = False) -> None:
        super().__init__(parent)
        self.setFixedWidth(66)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.title = QLabel(title)
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setStyleSheet(f"color:{theme.TEXT_DIM}; font-size:11px;")
        layout.addWidget(self.title)

        self.plus = HoldButton("＋", repeat=True)
        self.plus.setFixedHeight(72)
        self.plus.setStyleSheet("font-size:20px; border-radius:16px;")
        layout.addWidget(self.plus)

        self.value_label = QLabel("")
        self.value_label.setAlignment(Qt.AlignCenter)
        self.value_label.setFixedHeight(22)
        self.value_label.setStyleSheet(f"color:{theme.TEXT}; font-size:13px; font-weight:600;")
        # 始终占位：无论是否显示数值，左右两个摇杆的总高度保持一致
        layout.addWidget(self.value_label)
        self._shows_value = show_value

        self.minus = HoldButton("−", repeat=True)
        self.minus.setFixedHeight(72)
        self.minus.setStyleSheet("font-size:20px; border-radius:16px;")
        layout.addWidget(self.minus)
        layout.addStretch(1)

    def set_value(self, text: str) -> None:
        self.value_label.setText(text)


class LevelBar(QWidget):
    """细音量条。"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(6)
        self.setMinimumWidth(70)
        self._value = 0
        self._max = 100
        self._muted = False

    def set_value(self, value: int, max_value: int = 100, muted: bool = False) -> None:
        self._value = max(0, int(value))
        self._max = max(1, int(max_value))
        self._muted = muted
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#232833"))
        p.drawRoundedRect(QRectF(0, 0, w, h), h / 2, h / 2)
        ratio = min(1.0, self._value / self._max)
        if ratio > 0:
            color = QColor("#4a5260" if self._muted else theme.ACCENT)
            p.setBrush(color)
            p.drawRoundedRect(QRectF(0, 0, max(h, w * ratio), h), h / 2, h / 2)
        p.end()


class StatusDot(QWidget):
    """连接状态指示点（带柔光）。"""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(12, 12)
        self._color = QColor(theme.TEXT_DIM)

    def set_color(self, color: str) -> None:
        self._color = QColor(color)
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        glow = QColor(self._color)
        glow.setAlpha(55)
        p.setPen(Qt.NoPen)
        p.setBrush(glow)
        p.drawEllipse(QRectF(0, 0, 12, 12))
        p.setBrush(self._color)
        p.drawEllipse(QRectF(3, 3, 6, 6))
        p.end()


class Toast(QLabel):
    """窗口内浮层提示，2.6 秒后淡出。"""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setObjectName("Toast")
        self.setAlignment(Qt.AlignCenter)
        self.setWordWrap(True)
        self.hide()
        self._effect = QGraphicsOpacityEffect(self)
        self._effect.setOpacity(0.0)
        self.setGraphicsEffect(self._effect)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fade_out)

    def show_message(self, text: str, kind: str = "info", msec: int = 2600) -> None:
        self.setProperty("kind", kind)
        restyle(self)
        self.setText(text)
        self.adjustSize()
        self._reposition()
        self._effect.setOpacity(1.0)
        self.show()
        self.raise_()
        self._timer.start(msec)

    def _reposition(self) -> None:
        parent = self.parentWidget()
        if not parent:
            return
        width = min(max(self.sizeHint().width(), 160), parent.width() - 40)
        height = max(self.sizeHint().height(), 34)
        self.setFixedWidth(width)
        self.setFixedHeight(height)
        self.move((parent.width() - width) // 2, parent.height() - height - 54)

    def _fade_out(self) -> None:
        self._effect.setOpacity(0.0)
        self.hide()


class Card(QWidget):
    """带标题的分区容器。"""

    def __init__(self, title: str = "", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.outer = QVBoxLayout(self)
        self.outer.setContentsMargins(0, 0, 0, 0)
        self.outer.setSpacing(6)
        self.header = None
        if title:
            self.header = QLabel(title)
            self.header.setObjectName("SectionTitle")
            self.outer.addWidget(self.header)
        self.body = QWidget(self)
        self.outer.addWidget(self.body)

    def set_body_layout(self, layout) -> None:
        self.body.setLayout(layout)
