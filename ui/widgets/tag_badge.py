# -*- coding: utf-8 -*-
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QRect, QEasingCurve, QSize
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel
from qfluentwidgets import FluentIcon, TransparentToolButton, isDarkTheme

class TagBadge(QFrame):
    """
    标签徽章组件（胶囊形，三种模式）：

    - **默认模式**：图标 + 文字；hover 时整个标签从右向左滑出有色遮罩，
      遮罩中央显示 × 图标，点击即删除，发出 `deleteClicked(tag_id)`
    - **筛选 chip 模式** (is_filter_mode=True)：图标 + 文字 + 内联 × 按鈕，发出 `closed()`
    - **可选模式** (is_selectable=True)：点击切换选中，发出 `toggled(bool)`
    """
    deleteClicked = pyqtSignal(int)
    closed = pyqtSignal()
    toggled = pyqtSignal(bool)

    def __init__(
        self,
        tag_id: int,
        text: str,
        color_hex: str,
        parent=None,
        is_filter_mode: bool = False,
        is_selectable: bool = False,
        is_deletable: bool = False,
    ):
        super().__init__(parent)
        self.tag_id = tag_id
        self.text = text
        self.color = QColor(color_hex)
        self.is_filter_mode = is_filter_mode
        self.is_selectable = is_selectable
        self.is_deletable = is_deletable or (not is_selectable and not is_filter_mode)
        self._is_selected = False

        self.setObjectName("tagBadge")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(20)

        self._build_ui(text)
        self._apply_color()

    # ------------------------------------------------------------------ #
    # 公共接口
    # ------------------------------------------------------------------ #
    def isSelected(self) -> bool:
        """返回当前选中状态（仅 selectable 模式有意义）。"""
        return self._is_selected

    def setSelected(self, selected: bool) -> None:
        """设置选中状态，刷新样式并发出 toggled 信号。"""
        if self._is_selected == selected:
            return
        self._is_selected = selected
        self._apply_color()
        self.toggled.emit(selected)

    # ------------------------------------------------------------------ #
    # 构建 UI
    # ------------------------------------------------------------------ #
    def _build_ui(self, text: str) -> None:
        """构建内部布局：图标 + 文字（+ 可选的内联 × 按鈕 / 遮罩层）。"""
        h = QHBoxLayout(self)
        h.setContentsMargins(8, 2, 8, 2)   # 对称内边距，减小上下留白降低高度
        h.setSpacing(4)

        # ── 图标 ──
        self._icon_label = QLabel(self)
        self._icon_label.setFixedSize(12, 12)
        self._icon_label.setObjectName("tagBadgeIcon")
        self._refresh_icon()
        h.addWidget(self._icon_label, 0, Qt.AlignmentFlag.AlignVCenter)

        # ── 文字 ──
        self._text_label = QLabel(text, self)
        self._text_label.setObjectName("tagBadgeText")
        f = self._text_label.font()
        f.setPixelSize(11)
        f.setBold(False)
        self._text_label.setFont(f)
        h.addWidget(self._text_label, 0, Qt.AlignmentFlag.AlignVCenter)

        if self.is_filter_mode:
            # ── 筛选 chip：内联 × 按鈕跟随文字排列 ──
            self._close_btn = TransparentToolButton(FluentIcon.CLOSE, self)
            self._close_btn.setObjectName("tagBadgeCloseBtn")
            self._close_btn.setFixedSize(10, 10)
            self._close_btn.setIconSize(QSize(8, 8))
            self._close_btn.clicked.connect(self._on_close_clicked)
            h.setContentsMargins(8, 2, 6, 2)   # 右边距缩小
            h.addWidget(self._close_btn, 0, Qt.AlignmentFlag.AlignVCenter)

        elif self.is_deletable:
            # ── 构建遮罩层（hover 时从右向左滑入）──
            self._overlay = QFrame(self)
            self._overlay.setObjectName("tagBadgeOverlay")
            ov = QHBoxLayout(self._overlay)
            ov.setContentsMargins(0, 0, 0, 0)
            # 遮罩中央的 × 图标（白色）
            self._close_icon = QLabel(self._overlay)
            self._close_icon.setObjectName("tagBadgeCloseIcon")
            self._close_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ov.addWidget(self._close_icon, 0, Qt.AlignmentFlag.AlignCenter)
            self._overlay.hide()
            self._overlay.raise_()  # 最顶层
            self._refresh_close_icon()
            # 滑入动画
            self._anim = QPropertyAnimation(self._overlay, b"geometry")
            self._anim.setDuration(150)
            self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    # ------------------------------------------------------------------ #
    # 样式计算
    # ------------------------------------------------------------------ #
    def _apply_color(self) -> None:
        """根据当前状态设置背景、边框、文字颜色和遮罩颜色。"""
        c = self.color
        # 常态下无背景色，选中时填充色彩
        bg_alpha   = 120 if (self.is_selectable and self._is_selected) else 0
        border_w   = 1 # 恒定 1px 避免加粗导致的 QFrame 布局推挤视觉
        bg         = f"rgba({c.red()},{c.green()},{c.blue()},{bg_alpha})"
        border     = f"rgba({c.red()},{c.green()},{c.blue()},180)"
        tc         = f"rgb({c.red()},{c.green()},{c.blue()})"

        # 遮罩颜色：比原标签深一些的圆形背景（半透明）
        ov_color   = f"rgba({c.red()},{c.green()},{c.blue()},180)"

        self.setStyleSheet(
            f"QFrame#tagBadge {{"
            f"  background-color:{bg};"
            f"  border:{border_w}px solid {border};"
            f"  border-radius:10px;"
            f"}}"
            f"QLabel#tagBadgeText{{color:{tc};background:transparent;border:none;}}"
            f"QFrame#tagBadgeOverlay {{"
            f"  background-color:{ov_color};"
            f"  border-radius:10px;"   # 20px / 2 = 10px
            f"  border:none;"
            f"}}"
            f"QLabel#tagBadgeCloseIcon{{background:transparent;border:none;}}"
        )
        self._refresh_icon()

    def _refresh_icon(self) -> None:
        """刷新左侧标签图标（着色为 self.color）。"""
        try:
            pix = FluentIcon.TAG.icon(color=self.color).pixmap(12, 12)
            self._icon_label.setPixmap(pix)
        except Exception:
            pass

    def _refresh_close_icon(self) -> None:
        """刷新遮罩上的白色 × 图标（仅默认模式）。"""
        try:
            pix = FluentIcon.CLOSE.icon(color=QColor("white")).pixmap(12, 12)
            self._close_icon.setPixmap(pix)
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # 事件处理
    # ------------------------------------------------------------------ #
    def enterEvent(self, e):
        super().enterEvent(e)
        if hasattr(self, '_anim') and self.is_deletable:
            w, ht = self.width(), self.height()
            # 遮罩宽=ht，高=ht（圆形）
            ov_w = ht
            
            self._anim.stop()
            # 初始位置：从标签最右侧的外边缘开始
            self._anim.setStartValue(QRect(w, 0, ov_w, ht))
            # 结束位置：刚好靠在最右面，即覆盖最右的 ht 宽度区域
            self._anim.setEndValue(QRect(w - ov_w, 0, ov_w, ht))
            
            self._overlay.show()
            self._anim.start()

    def leaveEvent(self, e):
        super().leaveEvent(e)
        if hasattr(self, '_anim') and self.is_deletable:
            self._anim.stop()
            self._overlay.hide()

    def mousePressEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(e)
            return

        from PyQt6.QtCore import QPoint
        # 优先判断是否点击了遮罩层的删除区
        if not self.is_filter_mode and self.is_deletable and hasattr(self, '_overlay') and self._overlay.isVisible():
            pos_x = e.pos().x()
            if pos_x >= self.width() - self.height():
                self._on_close_clicked()
                e.accept()
                return

        # 如果没点删除区，且是可选模式，则触发选中切换
        if self.is_selectable:
            self.setSelected(not self._is_selected)

        e.accept()

    def _on_close_clicked(self) -> None:
        """根据模式发出删除信号。"""
        if self.is_filter_mode:
            self.closed.emit()
        else:
            self.deleteClicked.emit(self.tag_id)
