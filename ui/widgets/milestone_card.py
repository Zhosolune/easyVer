# -*- coding: utf-8 -*-
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QPainterPath
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from qfluentwidgets import CardWidget, StrongBodyLabel, CaptionLabel, BodyLabel, FlowLayout, ElevatedCardWidget
from qfluentwidgets import themeColor

from ui.widgets.tag_badge import TagBadge
from utils.datetime_utils import ts_to_str


class MilestoneCard(ElevatedCardWidget
):
    """单个里程碑卡片（点击选中）。

    设计原则：
    - hover 和选中共用 CardWidget 原生背景动画，不单独定制背景色。
    - 选中状态仅额外绘制左侧主题色竖条，悬停/按下效果和普通卡片完全一致。
    - setSelected 只触发竖条重绘（self.update()），不触发背景色动画，
      避免两次 _updateBackgroundColor 叠加造成视觉闪烁。
    """

    clicked_signal = pyqtSignal(int)    # snap_id
    delete_tag_signal = pyqtSignal(int) # tag_id

    def __init__(self, snap_id: int, version: int, name: str, summary: str,
                 created_at: int, file_count: int, tags: list, hash_id: str,
                 parent: QWidget = None) -> None:
        # _is_selected 必须在 super().__init__() 前赋值，
        # 因父类 BackgroundColorObject.__init__ 会立刻调用 _normalBackgroundColor()
        self._is_selected = False
        super().__init__(parent)
        self._snap_id = snap_id
        self._search_text = f"v{version} {name or ''} {summary or ''}".lower()
        self._created_at = created_at
        self._tags = tags

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._setup_ui(version, name, summary, created_at, file_count, tags, hash_id)

    def match_search(self, text: str) -> bool:
        """
        判断卡片是否匹配搜索文本。

        Args:
            text: 搜索关键词（小写）

        Returns:
            True 表示匹配（无关键词时始终匹配）
        """
        if not text:
            return True
        return text.lower() in self._search_text

    def _setup_ui(self, version: int, name: str, summary: str,
                  created_at: int, file_count: int, tags: list, hash_id: str) -> None:
        """
        初始化卡片内容布局。

        Args:
            version: 里程碑版本号
            name: 里程碑名称
            summary: 摘要描述
            created_at: 创建时间戳
            file_count: 包含文件数
            tags: 标签列表
            hash_id: 快照哈希 ID
        """
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 10, 12, 10)
        layout.setSpacing(6)

        # 第一行：名称（若无名称则显示版本）+ 日期时间
        top = QHBoxLayout()
        title_text = name if name else f"v{version}"
        version_label = StrongBodyLabel(title_text, self)
        version_label.setFixedHeight(20)
        top.addWidget(version_label)

        time_label = CaptionLabel(ts_to_str(created_at), self)
        time_label.setObjectName("milestoneTimeLabel")
        top.addStretch()
        top.addWidget(time_label)
        layout.addLayout(top)

        # 第二行：摘要
        display_summary = summary if summary else "(无摘要)"
        msg_label = BodyLabel(display_summary, self)
        msg_label.setWordWrap(True)
        layout.addWidget(msg_label)

        # 第三行：哈希 + 文件数
        count_label = CaptionLabel(f"#{hash_id}   ·   包含 {file_count} 个文件", self)
        count_label.setObjectName("milestoneCountLabel")
        count_label.setFixedHeight(16)
        layout.addWidget(count_label)

        # 第四行：标签
        if not tags:
            empty_tag = CaptionLabel("标签：无", self)
            empty_tag.setObjectName("milestoneEmptyTagLabel")
            empty_tag.setFixedHeight(20)
            layout.addWidget(empty_tag)
        else:
            tag_flow_widget = QWidget(self)
            tag_layout = FlowLayout(tag_flow_widget, needAni=False)
            tag_layout.setContentsMargins(0, 0, 0, 0)
            tag_layout.setHorizontalSpacing(4)
            tag_layout.setVerticalSpacing(4)
            for tag in tags:
                badge = TagBadge(tag.id, tag.name, tag.color, tag_flow_widget)
                badge.deleteClicked.connect(self.delete_tag_signal)
                tag_layout.addWidget(badge)
            layout.addWidget(tag_flow_widget)

    def mousePressEvent(self, event) -> None:
        """鼠标按下，交由父类处理背景动画，同时发出选中信号。"""
        super().mousePressEvent(event)
        self.clicked_signal.emit(self._snap_id)

    def setSelected(self, is_selected: bool) -> None:
        """
        设置选中状态，仅刷新左侧竖条的显隐，不干预背景色动画。

        选中/取消选中不触发 _updateBackgroundColor()，
        背景色完全由 CardWidget 的 hover/leave 动画机制管理，
        从而避免两次动画叠加导致的视觉闪烁。

        Args:
            is_selected: True 表示选中，False 表示取消选中
        """
        if self._is_selected == is_selected:
            return
        self._is_selected = is_selected
        self.update()   # 仅触发 paintEvent 重绘竖条，不改变背景色动画

    def paintEvent(self, e) -> None:
        """
        重写绘制事件：先调父类绘制卡片背景，再在选中时叠加左侧主题色竖条。

        竖条形状 = 卡片圆角路径 ∩ 竖条矩形，自动贴合卡片左边缘（含圆角）。

        Args:
            e: QPaintEvent
        """
        super().paintEvent(e)

        if not self._is_selected:
            return

        painter = QPainter(self)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing)

        from PyQt6.QtCore import QRectF
        r = float(self.borderRadius)
        bar_width = 4.0
        # 与 CardWidget.paintEvent 保持一致：背景区域是 adjusted(1,1,-1,-1)
        card_rect = QRectF(self.rect().adjusted(1, 1, -1, -1))

        # 卡片完整圆角路径
        card_path = QPainterPath()
        card_path.addRoundedRect(card_rect, r, r)

        # 竖条矩形（只取左侧 bar_width 宽度）
        bar_path = QPainterPath()
        bar_path.addRect(QRectF(card_rect.x(), card_rect.y(), bar_width, card_rect.height()))

        # 交集 = 自动贴合圆角的竖条形状
        path = card_path.intersected(bar_path)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(themeColor())
        painter.drawPath(path)

