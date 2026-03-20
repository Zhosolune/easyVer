# -*- coding: utf-8 -*-
from PyQt6.QtCore import Qt, pyqtSignal, QPointF
from PyQt6.QtGui import QColor, QPainter, QPen, QIcon, QPixmap, QPolygonF
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLabel, QHBoxLayout
from qfluentwidgets import (
    FlyoutViewBase, ColorDialog, Flyout, FlyoutAnimationType,
    TransparentToolButton, CaptionLabel, BodyLabel
)
from app.style_sheet import StyleSheet

class ColorBlock(QWidget):
    """栅格色块，手绘纯色块"""
    colorClicked = pyqtSignal(QColor)

    def __init__(self, color: str, parent=None):
        super().__init__(parent)
        self.color = QColor(color)
        self.setFixedSize(24, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.isHover = False

    def enterEvent(self, e):
        self.isHover = True
        self.update()

    def leaveEvent(self, e):
        self.isHover = False
        self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.colorClicked.emit(self.color)

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect()
        
        # 内聚一点防止贴边
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.color)
        painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 3, 3)
        
        if self.isHover:
            painter.setPen(QPen(QColor(128, 128, 128), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 4, 4)
        else:
            painter.setPen(QPen(QColor(0, 0, 0, 20), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(2, 2, -2, -2), 3, 3)


class ColorRowItem(QWidget):
    """通用的整行点击项，包含左侧边距和背景色，如图1中的 Automatic 和 More Colors"""
    clicked = pyqtSignal()

    def __init__(self, color_block: QWidget, text: str, parent=None):
        super().__init__(parent)
        # self.setFixedHeight(38)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._isHover = False
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(12)
        
        if color_block:
            layout.addWidget(color_block)
        
        lbl = BodyLabel(text, self)
        layout.addWidget(lbl)
        layout.addStretch()

    def enterEvent(self, e):
        self._isHover = True
        self.update()

    def leaveEvent(self, e):
        self._isHover = False
        self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

    def paintEvent(self, e):
        # 如果是悬浮态，则绘制选中高亮背景
        if self._isHover:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, 12))
            painter.drawRoundedRect(self.rect().adjusted(0, 0, 0, 0), 4, 4)


def create_static_color_block(hex_color: str) -> QWidget:
    w = QWidget()
    w.setFixedSize(20, 20)
    w.setObjectName("colorPickerBlock")
    w.setStyleSheet(f"background-color: {hex_color};")
    return w


def create_icon_block(icon_path: str) -> QWidget:
    from qfluentwidgets import FluentIcon
    w = QWidget()
    w.setFixedSize(20, 20)
    l = QVBoxLayout(w)
    l.setContentsMargins(0, 0, 0, 0)
    lbl = QLabel()
    FluentIcon.PALETTE.render(lbl)
    l.addWidget(lbl)
    return w


class VerticalColorGroup(QWidget):
    """标题和颜色栅格呈上下垂直排列的组块，底部通常可选自带分隔线"""
    def __init__(self, title: str, grid_widget: QWidget, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)
        
        # 顶部标题
        self.titleLabel = BodyLabel(title, self)
        self.titleLabel.setContentsMargins(2, 0, 2, 0)
        layout.addWidget(self.titleLabel)
        
        # 底部网格
        layout.addWidget(grid_widget)


class ColorFlyoutView(FlyoutViewBase):
    colorSelected = pyqtSignal(QColor)
    moreColorsClicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 主布局是一个外层有一圈细弱阴影线边框样式的容器
        self.setMinimumWidth(260)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. Automatic 区域
        self.auto_row = ColorRowItem(create_static_color_block("black"), "Automatic", self)
        self.auto_row.clicked.connect(lambda: self.colorSelected.emit(QColor("black")))
        layout.addWidget(self.auto_row)

        line1 = QWidget(self)
        line1.setFixedHeight(1)
        line1.setObjectName("colorPickerLine")
        line1.setStyleSheet("background-color: rgba(0, 0, 0, 0.1);")
        layout.addWidget(line1)

        # 2. Theme Colors
        theme_widget = QWidget()
        grid_theme = QGridLayout(theme_widget)
        grid_theme.setContentsMargins(0, 0, 0, 0)
        grid_theme.setSpacing(2)
        base_colors = ["#FFFFFF", "#000000", "#E7E6E6", "#44546A", "#4472C4", "#ED7D31", "#A5A5A5", "#FFC000", "#5B9BD5", "#70AD47"]
        for col, c in enumerate(base_colors):
            b = ColorBlock(c, self)
            b.colorClicked.connect(self.colorSelected)
            grid_theme.addWidget(b, 0, col)
            for row in range(1, 6):
                bg = QColor(c)
                if row <= 3:
                    factor = 0.2 * (4 - row)
                    r = int(bg.red() + (255 - bg.red()) * factor)
                    g = int(bg.green() + (255 - bg.green()) * factor)
                    b_val = int(bg.blue() + (255 - bg.blue()) * factor)
                else:
                    factor = 0.2 * (row - 3)
                    r = int(bg.red() * (1 - factor))
                    g = int(bg.green() * (1 - factor))
                    b_val = int(bg.blue() * (1 - factor))
                
                shade = QColor(r, g, b_val).name()
                bd = ColorBlock(shade, self)
                bd.colorClicked.connect(self.colorSelected)
                grid_theme.addWidget(bd, row, col)
        
        # 将它包裹在一个 VerticalColorGroup 里
        vg1 = VerticalColorGroup("Theme Colors", theme_widget, parent=self)
        layout.addWidget(vg1)

        line2 = QWidget(self)
        line2.setFixedHeight(1)
        line2.setObjectName("colorPickerLine")
        line2.setStyleSheet("background-color: rgba(0, 0, 0, 0.1);")
        layout.addWidget(line2)

        # 3. Standard Colors
        std_widget = QWidget()
        grid_std = QGridLayout(std_widget)
        grid_std.setContentsMargins(0, 0, 0, 0)
        grid_std.setSpacing(2)
        std_colors = ["#C00000", "#FF0000", "#FFC000", "#FFFF00", "#92D050", "#00B050", "#00B0F0", "#0070C0", "#002060", "#7030A0"]
        for col, c in enumerate(std_colors):
            b = ColorBlock(c, self)
            b.colorClicked.connect(self.colorSelected)
            grid_std.addWidget(b, 0, col)
            
        vg2 = VerticalColorGroup("Standard Colors", std_widget, parent=self)
        layout.addWidget(vg2)

        line3 = QWidget(self)
        line3.setFixedHeight(1)
        line3.setObjectName("colorPickerLine")
        line3.setStyleSheet("background-color: rgba(0, 0, 0, 0.1);")
        layout.addWidget(line3)

        # 4. More Colors 区域
        from qfluentwidgets import FluentIcon, IconWidget
        icon_widget = IconWidget(FluentIcon.PALETTE)
        icon_widget.setFixedSize(16, 16)
        self.more_row = ColorRowItem(icon_widget, "More Colors...", self)
        self.more_row.clicked.connect(self.moreColorsClicked)
        layout.addWidget(self.more_row)


class TagColorPicker(QWidget):
    """标签颜色选择器入口按钮，右侧带有个下拉小尖头"""
    colorChanged = pyqtSignal(QColor)

    def __init__(self, default_color: QColor, parent=None):
        super().__init__(parent)
        self._color = default_color
        self.setFixedSize(54, 32)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.isHover = False
        self.flyout = None

    @property
    def color(self) -> QColor:
        return self._color
        
    def enterEvent(self, e):
        self.isHover = True
        self.update()

    def leaveEvent(self, e):
        self.isHover = False
        self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.showFlyout()

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        bg_rect = self.rect()
        painter.setPen(QPen(QColor(0, 0, 0, 20), 1))
        if self.isHover:
            painter.setBrush(QColor(0, 0, 0, 10))
        else:
            painter.setBrush(QColor(255, 255, 255, 100)) # 纯白底增加一丁点透明
        painter.drawRoundedRect(bg_rect.adjusted(1, 1, -1, -1), 4, 4)
        
        # Color rect 
        color_rect = bg_rect.adjusted(6, 6, -28, -6)
        painter.setPen(QPen(QColor(0, 0, 0, 30), 1))
        painter.setBrush(self._color)
        painter.drawRoundedRect(color_rect, 2, 2)
        
        # Arrow (V)
        painter.setPen(QPen(QColor(96, 96, 96), 1.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        arrow_x = bg_rect.width() - 18
        arrow_y = bg_rect.height() // 2 - 1
        points = [
            QPointF(arrow_x, arrow_y),
            QPointF(arrow_x + 4, arrow_y + 4),
            QPointF(arrow_x + 8, arrow_y)
        ]
        painter.drawPolyline(QPolygonF(points))

    def showFlyout(self):
        view = ColorFlyoutView(self)
        view.colorSelected.connect(self._onColorSelected)
        view.moreColorsClicked.connect(self._onMoreColors)
        
        # 使用类似系统基础菜单的拉出动画
        self.flyout = Flyout.make(view, self, self, FlyoutAnimationType.PULL_UP)

    def _onColorSelected(self, color: QColor):
        self._color = color
        self.colorChanged.emit(self._color)
        self.update()
        if self.flyout:
            self.flyout.close()

    def _onMoreColors(self):
        if self.flyout:
            self.flyout.close()
        # Top-level window for ColorDialog
        dlg = ColorDialog(self._color, "选择自定义颜色", self.window())
        dlg.colorChanged.connect(self._onColorSelected)
        dlg.exec()
