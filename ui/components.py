"""
ui/components.py
Reusable custom widgets for the dark modern UI with security features.
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QFrame,
    QProgressBar, QTextEdit, QListWidget, QListWidgetItem, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QTimer, QRect, pyqtProperty
from PyQt6.QtGui import QColor, QPainter, QBrush, QPen


class ToggleSwitch(QWidget):
    """Animated iOS-style toggle switch - FULLY FIXED."""
    
    toggled = pyqtSignal(bool)
    
    _BG_ON = QColor("#2481CC")
    _BG_OFF = QColor("#3C3C3C")
    _KNOB = QColor("#FFFFFF")

    def __init__(self, parent=None):
        super().__init__(parent)
        self._checked = False
        self._knob_position = 4  # Position of the knob (x coordinate)
        self.setFixedSize(52, 28)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Create animation
        self._animation = QPropertyAnimation(self, b"knobPosition")
        self._animation.setDuration(150)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, state: bool):
        self._checked = state
        self._knob_position = 28 if state else 4
        self.update()

    @pyqtProperty(float)
    def knobPosition(self):
        return self._knob_position

    @knobPosition.setter
    def knobPosition(self, value):
        self._knob_position = value
        self.update()

    def mousePressEvent(self, event):
        self._checked = not self._checked
        target = 28 if self._checked else 4
        self._animation.stop()
        self._animation.setStartValue(self._knob_position)
        self._animation.setEndValue(target)
        self._animation.start()
        self.toggled.emit(self._checked)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw background
        bg = self._BG_ON if self._checked else self._BG_OFF
        p.setBrush(QBrush(bg))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(0, 0, 52, 28, 14, 14)
        
        # Draw knob
        p.setBrush(QBrush(self._KNOB))
        p.drawEllipse(int(self._knob_position), 4, 20, 20)


class ExclusionRow(QFrame):
    remove_requested = pyqtSignal(int)

    def __init__(self, chat_id: int, username: str, display_name: str, parent=None):
        super().__init__(parent)
        self.chat_id = chat_id
        self.setObjectName("ExclusionRow")
        self.setStyleSheet("""
            QFrame#ExclusionRow {
                background: #1E2C3A;
                border: 1px solid #2D4052;
                border-radius: 6px;
                padding: 2px;
            }
            QFrame#ExclusionRow:hover { border-color: #2481CC; }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        label = QLabel(f"@{username}  —  {display_name}")
        label.setStyleSheet("color: #C8D8E8; font-size: 13px;")
        btn = QPushButton("✕ Remove")
        btn.setFixedWidth(80)
        btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #E57373;
                border: 1px solid #E57373;
                border-radius: 4px;
                padding: 3px 8px;
                font-size: 12px;
            }
            QPushButton:hover { background: #E57373; color: white; }
        """)
        btn.clicked.connect(lambda: self.remove_requested.emit(self.chat_id))
        layout.addWidget(label, stretch=1)
        layout.addWidget(btn)


class SectionCard(QFrame):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setObjectName("SectionCard")
        self.setStyleSheet("""
            QFrame#SectionCard {
                background: #17212B;
                border: 1px solid #2D3F50;
                border-radius: 8px;
            }
        """)
        self._title_label = QLabel(title)
        self._title_label.setStyleSheet(
            "color: #7FA8C8; font-size: 11px; font-weight: bold; letter-spacing: 1px;"
            "text-transform: uppercase; padding: 10px 12px 4px 12px;"
        )

    def setContentLayout(self, layout):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        inner = QWidget()
        inner.setLayout(layout)
        vbox = QVBoxLayout()
        vbox.setContentsMargins(0, 0, 0, 8)
        vbox.setSpacing(0)
        vbox.addWidget(self._title_label)
        vbox.addWidget(inner)
        self.setLayout(vbox)


class SecurityLogWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QListWidget {
                background: #0E1621;
                color: #C8D8E8;
                border: 1px solid #2D3F50;
                border-radius: 6px;
                font-family: monospace;
                font-size: 11px;
            }
            QListWidget::item { padding: 6px; border-bottom: 1px solid #1E2C3A; }
            QListWidget::item:hover { background: #1E2C3A; }
        """)

    def add_log(self, timestamp: str, user: str, activity: str, severity: str):
        severity_colors = {"low": "#7FA8C8", "medium": "#FFB74D", "high": "#E57373"}
        color = severity_colors.get(severity, "#C8D8E8")
        item_text = f"[{timestamp}] [{severity.upper()}] {user}: {activity}"
        item = QListWidgetItem(item_text)
        item.setForeground(QColor(color))
        self.insertItem(0, item)
        while self.count() > 200:
            self.takeItem(self.count() - 1)


class ThreatIndicator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(16, 16)
        self._threat_level = 0

    def set_threat_level(self, level: int):
        self._threat_level = min(100, max(0, level))
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._threat_level < 30:
            color = QColor("#4CAF50")
        elif self._threat_level < 70:
            color = QColor("#FFB74D")
        else:
            color = QColor("#E57373")
        p.setBrush(QBrush(color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(0, 0, 16, 16)


class SecurityMetricCard(QFrame):
    def __init__(self, title: str, value: str, icon: str = "🛡️", color: str = "#2481CC", parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: #17212B; border: 1px solid #2D3F50; border-radius: 8px;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        top_row = QHBoxLayout()
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 24px;")
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #7FA8C8; font-size: 11px;")
        top_row.addWidget(icon_label)
        top_row.addWidget(title_label)
        top_row.addStretch()
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: bold;")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addLayout(top_row)
        layout.addWidget(self.value_label)

    def set_value(self, value: str):
        self.value_label.setText(value)


class BlockedUsersList(QWidget):
    unblock_requested = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        header = QLabel("Blocked Users")
        header.setStyleSheet("color: #7FA8C8; font-size: 12px; font-weight: bold; padding: 5px 0;")
        layout.addWidget(header)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self._container = QWidget()
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._container_layout.setSpacing(4)
        self._container_layout.addStretch()
        scroll.setWidget(self._container)
        layout.addWidget(scroll)

    def add_blocked_user(self, user_id: int, username: str, reason: str, blocked_until: str):
        row = QFrame()
        row.setStyleSheet("background: #1E2C3A; border: 1px solid #2D4052; border-radius: 4px;")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(8, 6, 8, 6)
        info = QLabel(f"@{username} (ID: {user_id})\n{reason}\nBlocked until: {blocked_until}")
        info.setStyleSheet("color: #C8D8E8; font-size: 11px;")
        info.setWordWrap(True)
        unblock_btn = QPushButton("Unblock")
        unblock_btn.setFixedWidth(70)
        unblock_btn.setStyleSheet("""
            QPushButton {
                background: #E57373; color: white; border: none;
                border-radius: 4px; padding: 4px 8px; font-size: 11px;
            }
            QPushButton:hover { background: #EF5350; }
        """)
        unblock_btn.clicked.connect(lambda: self.unblock_requested.emit(user_id))
        row_layout.addWidget(info, stretch=1)
        row_layout.addWidget(unblock_btn)
        row.setProperty("user_id", user_id)
        self._container_layout.insertWidget(self._container_layout.count() - 1, row)

    def remove_blocked_user(self, user_id: int):
        for i in range(self._container_layout.count()):
            item = self._container_layout.itemAt(i)
            if item and item.widget() and item.widget().property("user_id") == user_id:
                item.widget().deleteLater()
                break

    def clear(self):
        while self._container_layout.count() > 1:
            item = self._container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()