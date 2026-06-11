"""
ui/main_window.py
Main application window with security dashboard - SILENT MODE.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QStackedWidget, QScrollArea,
    QLineEdit, QComboBox, QTextEdit, QFrame, QSizePolicy,
    QMessageBox, QGridLayout, QTabWidget, QCheckBox, QSpinBox, QGroupBox
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QObject, QTimer
from PyQt6.QtGui import QFont, QIcon, QColor

import config
from database.db_manager import DBManager
from core.telegram_client import TelegramBotClient
from ui.components import (
    ToggleSwitch, ExclusionRow, SectionCard, SecurityMetricCard,
    SecurityLogWidget, ThreatIndicator, BlockedUsersList
)

logger = logging.getLogger(__name__)
logger.disabled = True


class Bridge(QObject):
    status_changed = pyqtSignal(str)
    log_received = pyqtSignal(dict)
    security_event = pyqtSignal(dict)


class NavButton(QPushButton):
    def __init__(self, label: str, icon: str = ""):
        super().__init__(f"  {icon}  {label}")
        self.setCheckable(True)
        self.setFixedHeight(44)
        self.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #7FA8C8;
                border: none;
                text-align: left;
                padding-left: 16px;
                font-size: 13px;
                border-radius: 0;
            }
            QPushButton:hover { background: #1E2C3A; color: #F5F5F5; }
            QPushButton:checked { background: #1A3A5C; color: #2481CC; border-left: 3px solid #2481CC; }
        """)


class DashboardPage(QWidget):
    def __init__(self, bridge: Bridge, db: DBManager):
        super().__init__()
        self._bridge = bridge
        self._db = db
        self._build()
        bridge.status_changed.connect(self._update_status)
        bridge.log_received.connect(lambda _: self.update_metrics())
        bridge.security_event.connect(lambda _: self.update_metrics())
        
        # Periodic update timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.update_metrics)
        self._timer.start(2000)
        self.update_metrics()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        row = QHBoxLayout()
        self._status_label = QLabel("Status: DISCONNECTED")
        self._status_label.setStyleSheet("color: #E57373; font-size: 14px; font-weight: bold;")
        row.addWidget(self._status_label)
        row.addStretch()
        threat_label = QLabel("Threat Level:")
        threat_label.setStyleSheet("color: #7FA8C8; font-size: 12px;")
        self._threat_indicator = ThreatIndicator()
        row.addWidget(threat_label)
        row.addWidget(self._threat_indicator)
        layout.addLayout(row)

        metrics_layout = QGridLayout()
        metrics_layout.setSpacing(12)
        self._blocked_metric = SecurityMetricCard("Blocked Users", "0", "🚫", "#E57373")
        self._threats_metric = SecurityMetricCard("Threats Today", "0", "⚠️", "#FFB74D")
        self._violations_metric = SecurityMetricCard("Violations", "0", "📊", "#FFB74D")
        metrics_layout.addWidget(self._blocked_metric, 0, 0)
        metrics_layout.addWidget(self._threats_metric, 0, 1)
        metrics_layout.addWidget(self._violations_metric, 1, 0)
        layout.addLayout(metrics_layout)

        stats = QFrame()
        stats.setStyleSheet("background:#17212B; border-radius:8px;")
        sl = QHBoxLayout(stats)
        sl.setContentsMargins(16, 14, 16, 14)
        
        # Total Replies
        col1 = QVBoxLayout()
        self._total_replies_label = QLabel("—")
        self._total_replies_label.setStyleSheet("color:#2481CC; font-size:22px; font-weight:bold;")
        lbl1 = QLabel("Total Replies")
        lbl1.setStyleSheet("color:#7FA8C8; font-size:11px;")
        col1.addWidget(self._total_replies_label)
        col1.addWidget(lbl1)
        sl.addLayout(col1)
        sl.addStretch()

        # Today's Replies
        col2 = QVBoxLayout()
        self._replies_today_label = QLabel("—")
        self._replies_today_label.setStyleSheet("color:#2481CC; font-size:22px; font-weight:bold;")
        lbl2 = QLabel("Today")
        lbl2.setStyleSheet("color:#7FA8C8; font-size:11px;")
        col2.addWidget(self._replies_today_label)
        col2.addWidget(lbl2)
        sl.addLayout(col2)
        sl.addStretch()

        # Provider
        col3 = QVBoxLayout()
        self._provider_label = QLabel("—")
        self._provider_label.setStyleSheet("color:#2481CC; font-size:22px; font-weight:bold;")
        lbl3 = QLabel("Provider")
        lbl3.setStyleSheet("color:#7FA8C8; font-size:11px;")
        col3.addWidget(self._provider_label)
        col3.addWidget(lbl3)
        sl.addLayout(col3)

        layout.addWidget(stats)
        layout.addStretch()

    def _update_status(self, status: str):
        if status.startswith("CONNECTED"):
            if " — @" in status:
                username = status.split(" — @")[1]
                display_text = f"CONNECTED as @{username}"
            else:
                display_text = "CONNECTED"
            self._status_label.setText(f"Status: {display_text}")
            self._status_label.setStyleSheet("color: #4CAF50; font-size: 14px; font-weight: bold;")
        else:
            self._status_label.setText(f"Status: {status}")
            self._status_label.setStyleSheet("color: #E57373; font-size: 14px; font-weight: bold;")

    def update_metrics(self):
        try:
            # 1. Blocked Users
            blocked_count = len(self._db.get_all_blocked_users())
            self._blocked_metric.set_value(str(blocked_count))

            # 2. Threats/Violations count from database
            with self._db._db_conn() as conn:
                violations_today = conn.execute(
                    "SELECT COUNT(*) FROM security_logs WHERE date(created_at) = date('now', 'localtime')"
                ).fetchone()[0]

                threats_today = conn.execute(
                    "SELECT COUNT(*) FROM security_logs WHERE date(created_at) = date('now', 'localtime') AND severity = 'high'"
                ).fetchone()[0]

                # Total Replies
                total_replies = conn.execute("SELECT COUNT(*) FROM response_logs").fetchone()[0]

                # Replies today
                replies_today = conn.execute(
                    "SELECT COUNT(*) FROM response_logs WHERE date(created_at) = date('now', 'localtime')"
                ).fetchone()[0]

            self._threats_metric.set_value(str(threats_today))
            self._violations_metric.set_value(str(violations_today))
            self._total_replies_label.setText(str(total_replies))
            self._replies_today_label.setText(str(replies_today))
            self._provider_label.setText(config.AI_PROVIDER.upper())

            # Threat level indicator: green for 0, yellow for <3, red for >=3 high severity events
            threat_level = min(100, threats_today * 35)
            self._threat_indicator.set_threat_level(threat_level)
        except Exception as e:
            print(f"Error updating metrics: {e}")


class SecurityDashboardPage(QWidget):
    def __init__(self, bridge: Bridge, db: DBManager, bot_client_ref: list):
        super().__init__()
        self._bridge = bridge
        self._db = db
        self._bot_ref = bot_client_ref
        self._build()
        bridge.security_event.connect(self._on_security_event)

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(20)

        title = QLabel("Security Dashboard")
        title.setStyleSheet("color:#F5F5F5; font-size:17px; font-weight:bold;")
        layout.addWidget(title)

        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane { background: #17212B; border: 1px solid #2D3F50; border-radius: 8px; }
            QTabBar::tab { background: #1E2C3A; color: #7FA8C8; padding: 8px 16px; margin-right: 2px; border-top-left-radius: 6px; border-top-right-radius: 6px; }
            QTabBar::tab:selected { background: #2481CC; color: white; }
            QTabBar::tab:hover { background: #2D4052; }
        """)

        logs_tab = QWidget()
        logs_layout = QVBoxLayout(logs_tab)
        self._security_log = SecurityLogWidget()
        logs_layout.addWidget(self._security_log)
        tabs.addTab(logs_tab, "Security Logs")

        blocked_tab = QWidget()
        blocked_layout = QVBoxLayout(blocked_tab)
        self._blocked_list = BlockedUsersList()
        self._blocked_list.unblock_requested.connect(self._unblock_user)
        blocked_layout.addWidget(self._blocked_list)
        block_frame = QFrame()
        block_frame.setStyleSheet("background:#1E2C3A; border-radius:6px;")
        block_frame_layout = QHBoxLayout(block_frame)
        self._block_user_id = QLineEdit()
        self._block_user_id.setPlaceholderText("User ID")
        self._block_reason = QLineEdit()
        self._block_reason.setPlaceholderText("Reason")
        block_btn = QPushButton("Block User")
        block_btn.clicked.connect(self._manual_block)
        for w in [self._block_user_id, self._block_reason]:
            w.setStyleSheet("background:#0E1621; color:#F5F5F5; border:1px solid #2D4052; border-radius:4px; padding:6px;")
        block_frame_layout.addWidget(self._block_user_id)
        block_frame_layout.addWidget(self._block_reason)
        block_frame_layout.addWidget(block_btn)
        blocked_layout.addWidget(block_frame)
        tabs.addTab(blocked_tab, "Blocked Users")

        settings_tab = QWidget()
        settings_layout = QVBoxLayout(settings_tab)
        security_group = QGroupBox("Security Configuration")
        security_group.setStyleSheet("QGroupBox { color: #7FA8C8; font-weight: bold; margin-top: 10px; }")
        sec_layout = QVBoxLayout(security_group)
        self._security_enabled = QCheckBox("Enable Security Monitoring")
        self._security_enabled.setChecked(config.SECURITY_ENABLED)
        self._security_enabled.setStyleSheet("color: #C8D8E8;")
        sec_layout.addWidget(self._security_enabled)
        
        row = QHBoxLayout()
        row.addWidget(QLabel("Auto-block threshold:"))
        self._block_threshold = QSpinBox()
        self._block_threshold.setRange(1, 20)
        self._block_threshold.setValue(config.AUTO_BLOCK_THRESHOLD)
        row.addWidget(self._block_threshold)
        row.addStretch()
        sec_layout.addLayout(row)
        
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Block duration (minutes):"))
        self._block_duration = QSpinBox()
        self._block_duration.setRange(5, 1440)
        self._block_duration.setValue(config.BLOCK_DURATION_MINUTES)
        row2.addWidget(self._block_duration)
        row2.addStretch()
        sec_layout.addLayout(row2)
        
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Max messages per minute:"))
        self._rate_limit = QSpinBox()
        self._rate_limit.setRange(5, 60)
        self._rate_limit.setValue(config.MAX_MESSAGES_PER_MINUTE)
        row3.addWidget(self._rate_limit)
        row3.addStretch()
        sec_layout.addLayout(row3)
        
        save_btn = QPushButton("Save Security Settings")
        save_btn.clicked.connect(self._save_security_settings)
        save_btn.setStyleSheet("background:#2481CC; color:white; border:none; border-radius:6px; padding:8px;")
        sec_layout.addWidget(save_btn)
        settings_layout.addWidget(security_group)
        settings_layout.addStretch()
        tabs.addTab(settings_tab, "Security Settings")

        layout.addWidget(tabs)
        self._refresh_blocked_list()

    def _refresh_blocked_list(self):
        self._blocked_list.clear()
        blocked = self._db.get_all_blocked_users() if hasattr(self._db, 'get_all_blocked_users') else []
        for user in blocked:
            self._blocked_list.add_blocked_user(
                user.get('user_id', 0),
                user.get('username', 'unknown'),
                user.get('reason', 'No reason'),
                user.get('blocked_until', 'Unknown')[:16]
            )

    def _on_security_event(self, event: dict):
        self._security_log.add_log(
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            event.get('username', 'unknown'),
            event.get('description', ''),
            event.get('severity', 'medium')
        )
        self._refresh_blocked_list()

    def _unblock_user(self, user_id: int):
        self._db.unblock_user(user_id)
        self._refresh_blocked_list()

    def _manual_block(self):
        try:
            user_id = int(self._block_user_id.text().strip())
            reason = self._block_reason.text().strip() or "Manually blocked"
            self._db.block_user(user_id, f"user_{user_id}", reason, config.BLOCK_DURATION_MINUTES)
            self._block_user_id.clear()
            self._block_reason.clear()
            self._refresh_blocked_list()
            QMessageBox.information(self, "Blocked", f"User {user_id} has been blocked.")
        except ValueError:
            QMessageBox.warning(self, "Error", "Invalid user ID")

    def _save_security_settings(self):
        sec_enabled = self._security_enabled.isChecked()
        block_threshold = self._block_threshold.value()
        block_duration = self._block_duration.value()
        rate_limit = self._rate_limit.value()

        # Update db settings
        self._db.set_setting("security_enabled", "1" if sec_enabled else "0")
        self._db.set_setting("auto_block_threshold", str(block_threshold))
        self._db.set_setting("block_duration_minutes", str(block_duration))
        self._db.set_setting("max_messages_per_minute", str(rate_limit))

        # Update config module values
        config.SECURITY_ENABLED = sec_enabled
        config.AUTO_BLOCK_THRESHOLD = block_threshold
        config.BLOCK_DURATION_MINUTES = block_duration
        config.MAX_MESSAGES_PER_MINUTE = rate_limit

        QMessageBox.information(self, "Settings Saved", "Security settings have been saved and applied.")


class AutomationPage(QWidget):
    def __init__(self, bot_client_ref: list, db: DBManager):
        super().__init__()
        self._bot_ref = bot_client_ref
        self._db = db
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(20)
        title = QLabel("Automation Control")
        title.setStyleSheet("color:#F5F5F5; font-size:17px; font-weight:bold;")
        layout.addWidget(title)
        card = QFrame()
        card.setStyleSheet("background:#17212B; border:1px solid #2D3F50; border-radius:8px;")
        cl = QHBoxLayout(card)
        cl.setContentsMargins(16, 14, 16, 14)
        lbl = QLabel("Automation Active")
        lbl.setStyleSheet("color:#F5F5F5; font-size:14px;")
        self._toggle = ToggleSwitch()
        saved = self._db.get_setting("automation_active", "0")
        self._toggle.setChecked(saved == "1")
        self._toggle.toggled.connect(self._on_toggle)
        sub = QLabel("When active, all allowed private chats will receive automated AI replies.")
        sub.setStyleSheet("color:#7FA8C8; font-size:12px;")
        sub.setWordWrap(True)
        vb = QVBoxLayout()
        vb.addWidget(lbl)
        vb.addWidget(sub)
        cl.addLayout(vb, stretch=1)
        cl.addWidget(self._toggle)
        layout.addWidget(card)
        layout.addStretch()

    def _on_toggle(self, active: bool):
        client = self._bot_ref[0] if self._bot_ref else None
        if client:
            client.set_active(active)
        self._db.set_setting("automation_active", "1" if active else "0")


class ChatScopesPage(QWidget):
    def __init__(self, bot_client_ref: list, db: DBManager):
        super().__init__()
        self._bot_ref = bot_client_ref
        self._db = db
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        title = QLabel("Chat Scope & Exclusions")
        title.setStyleSheet("color:#F5F5F5; font-size:17px; font-weight:bold;")
        layout.addWidget(title)
        
        # Scope Mode ComboBox
        mode_frame = QFrame()
        mode_frame.setStyleSheet("background:#17212B; border:1px solid #2D3F50; border-radius:8px;")
        mfl = QVBoxLayout(mode_frame)
        mfl.setContentsMargins(16, 12, 16, 12)
        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["All Private Chats Except Listed", "Only Listed Chats"])
        saved = self._db.get_setting("scope_mode", "exclude")
        self._mode_combo.setCurrentIndex(0 if saved == "exclude" else 1)
        self._mode_combo.currentIndexChanged.connect(self._on_scope_change)
        mfl.addWidget(QLabel("Scope Mode:"))
        mfl.addWidget(self._mode_combo)
        layout.addWidget(mode_frame)
        
        # Respond to New Users Toggle
        new_users_frame = QFrame()
        new_users_frame.setStyleSheet("background:#17212B; border:1px solid #2D3F50; border-radius:8px;")
        nufl = QHBoxLayout(new_users_frame)
        nufl.setContentsMargins(16, 12, 16, 12)
        self._respond_to_new = ToggleSwitch()
        saved_new = self._db.get_setting("respond_to_new_users", "1")
        self._respond_to_new.setChecked(saved_new == "1")
        self._respond_to_new.toggled.connect(self._on_respond_to_new)
        nufl.addWidget(QLabel("Respond to New Users (First-time Senders)"))
        nufl.addStretch()
        nufl.addWidget(self._respond_to_new)
        layout.addWidget(new_users_frame)

        # Respond to Existing Dialogs Toggle
        existing_frame = QFrame()
        existing_frame.setStyleSheet("background:#17212B; border:1px solid #2D3F50; border-radius:8px;")
        efl = QHBoxLayout(existing_frame)
        efl.setContentsMargins(16, 12, 16, 12)
        self._respond_to_existing = ToggleSwitch()
        saved_existing = self._db.get_setting("respond_to_existing", "1")
        self._respond_to_existing.setChecked(saved_existing == "1")
        self._respond_to_existing.toggled.connect(self._on_respond_to_existing)
        efl.addWidget(QLabel("Respond to Existing Dialogs (Active Chats)"))
        efl.addStretch()
        efl.addWidget(self._respond_to_existing)
        layout.addWidget(existing_frame)

        # Ignore groups Toggle
        group_frame = QFrame()
        group_frame.setStyleSheet("background:#17212B; border:1px solid #2D3F50; border-radius:8px;")
        gfl = QHBoxLayout(group_frame)
        gfl.setContentsMargins(16, 12, 16, 12)
        self._ignore_groups = ToggleSwitch()
        saved_ignore = self._db.get_setting("ignore_groups", "1")
        self._ignore_groups.setChecked(saved_ignore == "1")
        self._ignore_groups.toggled.connect(self._on_ignore_groups)
        gfl.addWidget(QLabel("Ignore All Group/Channel Messages"))
        gfl.addStretch()
        gfl.addWidget(self._ignore_groups)
        layout.addWidget(group_frame)
        
        # Add Excluded/Allowed chat input
        add_frame = QFrame()
        add_frame.setStyleSheet("background:#17212B; border:1px solid #2D3F50; border-radius:8px;")
        afl = QHBoxLayout(add_frame)
        afl.setContentsMargins(12, 10, 12, 10)
        self._id_input = QLineEdit()
        self._id_input.setPlaceholderText("Chat ID (integer)")
        self._username_input = QLineEdit()
        self._username_input.setPlaceholderText("@username")
        self._name_input = QLineEdit()
        self._name_input.setPlaceholderText("Display name")
        add_btn = QPushButton("+ Add Chat")
        add_btn.clicked.connect(self._add_chat)
        for w in [self._id_input, self._username_input, self._name_input]:
            w.setStyleSheet("background:#1E2C3A; color:#F5F5F5; border:1px solid #2D4052; border-radius:4px; padding:5px 8px;")
            afl.addWidget(w)
        afl.addWidget(add_btn)
        layout.addWidget(add_frame)
        
        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(6)
        self._list_layout.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._list_widget)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        layout.addWidget(scroll, stretch=1)
        self._reload_list()

    def _on_scope_change(self, idx: int):
        mode = "exclude" if idx == 0 else "include"
        self._db.set_setting("scope_mode", mode)
        client = self._bot_ref[0] if self._bot_ref else None
        if client:
            client.set_scope_mode(mode)

    def _on_ignore_groups(self, checked: bool):
        self._db.set_setting("ignore_groups", "1" if checked else "0")
        client = self._bot_ref[0] if self._bot_ref else None
        if client:
            client.reload_filters()

    def _on_respond_to_new(self, checked: bool):
        self._db.set_setting("respond_to_new_users", "1" if checked else "0")
        client = self._bot_ref[0] if self._bot_ref else None
        if client:
            client.reload_filters()

    def _on_respond_to_existing(self, checked: bool):
        self._db.set_setting("respond_to_existing", "1" if checked else "0")
        client = self._bot_ref[0] if self._bot_ref else None
        if client:
            client.reload_filters()

    def _add_chat(self):
        try:
            chat_id = int(self._id_input.text().strip())
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Chat ID must be an integer.")
            return
        username = self._username_input.text().strip().lstrip("@")
        display = self._name_input.text().strip() or username
        self._db.add_excluded_chat(chat_id, username, display)
        self._id_input.clear()
        self._username_input.clear()
        self._name_input.clear()
        self._reload_list()

    def _remove_chat(self, chat_id: int):
        self._db.remove_excluded_chat(chat_id)
        self._reload_list()

    def _reload_list(self):
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for chat in self._db.get_excluded_chats():
            row = ExclusionRow(chat["chat_id"], chat["username"], chat["display_name"])
            row.remove_requested.connect(self._remove_chat)
            self._list_layout.insertWidget(self._list_layout.count() - 1, row)


class LogsPage(QWidget):
    def __init__(self, bridge: Bridge, db: DBManager):
        super().__init__()
        self._db = db
        self._bridge = bridge
        self._build()
        bridge.log_received.connect(self._append_log)

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        title = QLabel("Response Logs")
        title.setStyleSheet("color:#F5F5F5; font-size:17px; font-weight:bold;")
        layout.addWidget(title)
        self._log_view = QTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setStyleSheet("background:#0E1621; color:#C8D8E8; font-family:monospace; font-size:12px; border:1px solid #2D3F50; border-radius:6px;")
        layout.addWidget(self._log_view)
        for entry in reversed(self._db.get_recent_logs(50)):
            self._append_log(entry)

    def _append_log(self, entry: dict):
        ts = entry.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        user_msg = entry.get('user_message', '')
        ai_resp = entry.get('ai_response', '')
        provider = entry.get('provider', 'AI')
        
        # Premium multi-line box format to show full logs without truncation
        line = (
            f"┌─── [{ts}]  @{entry.get('sender','?')} ──────────────────────────────────────\n"
            f"│  ➜ User: {user_msg}\n"
            f"│  ➜ AI ({provider.upper()}): {ai_resp}\n"
            f"└────────────────────────────────────────────────────────────────────────────\n"
        )
        self._log_view.append(line)


class SettingsPage(QWidget):
    def __init__(self, db: DBManager):
        super().__init__()
        self._db = db
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        
        title = QLabel("Settings")
        title.setStyleSheet("color:#F5F5F5; font-size:17px; font-weight:bold;")
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 16, 0)
        scroll_layout.setSpacing(14)

        # AI Provider setting
        row_provider = QHBoxLayout()
        lbl_provider = QLabel("AI Provider:")
        lbl_provider.setFixedWidth(180)
        lbl_provider.setStyleSheet("color:#C8D8E8; font-size:13px;")
        self._provider_combo = QComboBox()
        self._provider_combo.addItems(["deepseek", "gemini"])
        current_provider = self._db.get_setting("AI_PROVIDER", config.AI_PROVIDER)
        self._provider_combo.setCurrentText(current_provider)
        self._provider_combo.setStyleSheet("background:#1E2C3A; color:#F5F5F5; border:1px solid #2D4052; border-radius:4px; padding:5px 8px;")
        row_provider.addWidget(lbl_provider)
        row_provider.addWidget(self._provider_combo)
        scroll_layout.addLayout(row_provider)

        fields = [
            ("Telegram API ID", "TELEGRAM_API_ID", str(config.TELEGRAM_API_ID)),
            ("Telegram API Hash", "TELEGRAM_API_HASH", config.TELEGRAM_API_HASH),
            ("Session Name", "TELEGRAM_SESSION_NAME", config.TELEGRAM_SESSION_NAME),
            ("Owner Username", "OWNER_USERNAME", config.OWNER_USERNAME),
            ("DeepSeek API Key", "DEEPSEEK_API_KEY", config.DEEPSEEK_API_KEY),
            ("DeepSeek Model", "DEEPSEEK_MODEL", config.DEEPSEEK_MODEL),
            ("DeepSeek Base URL", "DEEPSEEK_BASE_URL", config.DEEPSEEK_BASE_URL),
            ("Gemini API Key", "GEMINI_API_KEY", config.GEMINI_API_KEY),
            ("Gemini Model", "GEMINI_MODEL", config.GEMINI_MODEL),
            ("Gemini Base URL", "GEMINI_BASE_URL", config.GEMINI_BASE_URL),
        ]
        self._inputs = {}
        for label, key, default in fields:
            row = QHBoxLayout()
            lbl = QLabel(label + ":")
            lbl.setFixedWidth(180)
            lbl.setStyleSheet("color:#C8D8E8; font-size:13px;")
            inp = QLineEdit(self._db.get_setting(key, default))
            if "KEY" in key or "HASH" in key:
                inp.setEchoMode(QLineEdit.EchoMode.Password)
            inp.setStyleSheet("background:#1E2C3A; color:#F5F5F5; border:1px solid #2D4052; border-radius:4px; padding:5px 8px;")
            self._inputs[key] = inp
            row.addWidget(lbl)
            row.addWidget(inp)
            scroll_layout.addLayout(row)

        # AI System Prompt (multi-line)
        row_prompt = QVBoxLayout()
        lbl_prompt = QLabel("AI System Prompt:")
        lbl_prompt.setStyleSheet("color:#C8D8E8; font-size:13px; font-weight: bold; margin-top: 8px;")
        self._system_prompt_input = QTextEdit()
        self._system_prompt_input.setMinimumHeight(100)
        self._system_prompt_input.setMaximumHeight(150)
        current_prompt = self._db.get_setting("ai_system_prompt", config.AI_SYSTEM_PROMPT)
        self._system_prompt_input.setPlainText(current_prompt)
        self._system_prompt_input.setStyleSheet("background:#1E2C3A; color:#F5F5F5; border:1px solid #2D4052; border-radius:4px; padding:6px; font-size:12px;")
        row_prompt.addWidget(lbl_prompt)
        row_prompt.addWidget(self._system_prompt_input)
        scroll_layout.addLayout(row_prompt)

        # Save Button
        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self._save)
        save_btn.setStyleSheet("background:#2481CC; color:white; border:none; border-radius:6px; padding:8px 20px; font-size:13px; margin-top: 10px;")
        scroll_layout.addWidget(save_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

    def _save(self):
        for key, inp in self._inputs.items():
            self._db.set_setting(key, inp.text().strip())
        provider_val = self._provider_combo.currentText()
        self._db.set_setting("AI_PROVIDER", provider_val)
        prompt_val = self._system_prompt_input.toPlainText().strip()
        self._db.set_setting("ai_system_prompt", prompt_val)

        # Sync config module variables
        config.load_from_db(self._db)
        QMessageBox.information(self, "Saved", "Settings saved and loaded. Reconnect to apply.")


class AppointmentRow(QFrame):
    complete_requested = pyqtSignal(int)

    def __init__(self, appt_id: int, user_id: int, username: str, date_time: str, description: str, parent=None):
        super().__init__(parent)
        self.appt_id = appt_id
        self.setObjectName("AppointmentRow")
        self.setStyleSheet("""
            QFrame#AppointmentRow {
                background: #1E2C3A;
                border: 1px solid #2D4052;
                border-radius: 6px;
                padding: 4px;
            }
            QFrame#AppointmentRow:hover { border-color: #2481CC; }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        
        info_layout = QVBoxLayout()
        user_lbl = QLabel(f"👤 @{username} (ID: {user_id})")
        user_lbl.setStyleSheet("color: #2481CC; font-weight: bold; font-size: 13px;")
        time_lbl = QLabel(f"📅 {date_time}")
        time_lbl.setStyleSheet("color: #FFB74D; font-size: 12px; font-weight: bold;")
        desc_lbl = QLabel(description)
        desc_lbl.setStyleSheet("color: #C8D8E8; font-size: 12px;")
        desc_lbl.setWordWrap(True)
        
        info_layout.addWidget(user_lbl)
        info_layout.addWidget(time_lbl)
        info_layout.addWidget(desc_lbl)
        
        btn = QPushButton("Complete")
        btn.setFixedWidth(90)
        btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #81C784;
                border: 1px solid #81C784;
                border-radius: 4px;
                padding: 5px 10px;
                font-size: 12px;
            }
            QPushButton:hover { background: #81C784; color: white; }
        """)
        btn.clicked.connect(lambda: self.complete_requested.emit(self.appt_id))
        
        layout.addLayout(info_layout, stretch=1)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignVCenter)


class AppointmentsPage(QWidget):
    def __init__(self, db: DBManager):
        super().__init__()
        self._db = db
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        
        title = QLabel("Scheduled Appointments")
        title.setStyleSheet("color:#F5F5F5; font-size:17px; font-weight:bold;")
        layout.addWidget(title)
        
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(10)
        self._list_layout.addStretch()
        
        self._scroll.setWidget(self._list_widget)
        layout.addWidget(self._scroll, stretch=1)
        self.reload_list()

    def reload_list(self):
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        appts = self._db.get_appointments()
        for appt in appts:
            row = AppointmentRow(
                appt["id"],
                appt["user_id"],
                appt["username"] or "unknown",
                appt["date_time"] or "Not specified",
                appt["description"] or ""
            )
            row.complete_requested.connect(self._complete_appt)
            self._list_layout.insertWidget(self._list_layout.count() - 1, row)

    def _complete_appt(self, appt_id: int):
        self._db.delete_appointment(appt_id)
        self.reload_list()


class MainWindow(QMainWindow):
    def __init__(self, async_loop: asyncio.AbstractEventLoop):
        super().__init__()
        self._loop = async_loop
        self._db = DBManager(config.DB_PATH)
        config.load_from_db(self._db)  # Load settings from database at startup
        self._bridge = Bridge()
        self._bot_ref: list = []
        self.setWindowTitle("Vantavail - Secure Bot Control Center")
        self.setMinimumSize(QSize(1000, 700))
        self._apply_global_style()
        self._build_ui()
        self._bot_thread = None

    def _apply_global_style(self):
        self.setStyleSheet("""
            QMainWindow, QWidget { background-color: #0E1621; color: #F5F5F5; }
            QLabel { color: #F5F5F5; }
            QScrollBar:vertical { background: #17212B; width: 6px; border-radius: 3px; }
            QScrollBar::handle:vertical { background: #2D4052; border-radius: 3px; }
        """)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        sidebar = QWidget()
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet("background: #17212B;")
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(0, 0, 0, 0)
        sb_layout.setSpacing(0)
        logo = QLabel("  🛡️  Vantavail")
        logo.setStyleSheet("color:#2481CC; font-size:14px; font-weight:bold; padding: 18px 12px 14px 12px; border-bottom: 1px solid #1E2C3A;")
        sb_layout.addWidget(logo)
        
        nav_items = [
            ("Dashboard", "📊"),
            ("Automation", "⚡"),
            ("Chat Scopes", "☰"),
            ("Security", "🛡️"),
            ("Appointments", "📅"),
            ("Logs & History", "📋"),
            ("Settings", "⚙️")
        ]
        self._nav_buttons = []
        for label, icon in nav_items:
            btn = NavButton(label, icon)
            btn.clicked.connect(lambda _, l=label: self._navigate(l))
            sb_layout.addWidget(btn)
            self._nav_buttons.append((label, btn))
        sb_layout.addStretch()
        self._connect_btn = QPushButton("⟳  Connect")
        self._connect_btn.setStyleSheet("background: #2481CC; color: white; border: none; padding: 12px; font-size: 13px;")
        self._connect_btn.clicked.connect(self._toggle_connection)
        sb_layout.addWidget(self._connect_btn)
        root.addWidget(sidebar)

        self._stack = QStackedWidget()
        bot_client_ref = self._bot_ref
        self._pages = {
            "Dashboard": DashboardPage(self._bridge, self._db),
            "Automation": AutomationPage(bot_client_ref, self._db),
            "Chat Scopes": ChatScopesPage(bot_client_ref, self._db),
            "Security": SecurityDashboardPage(self._bridge, self._db, bot_client_ref),
            "Appointments": AppointmentsPage(self._db),
            "Logs & History": LogsPage(self._bridge, self._db),
            "Settings": SettingsPage(self._db),
        }
        for page in self._pages.values():
            self._stack.addWidget(page)
        root.addWidget(self._stack, stretch=1)
        self._navigate("Dashboard")

    def _navigate(self, label: str):
        page = self._pages.get(label)
        if page:
            self._stack.setCurrentWidget(page)
            if label == "Appointments" and hasattr(page, "reload_list"):
                page.reload_list()
            elif label == "Dashboard" and hasattr(page, "update_metrics"):
                page.update_metrics()
        for lbl, btn in self._nav_buttons:
            btn.setChecked(lbl == label)

    def _toggle_connection(self):
        if self._bot_ref:
            asyncio.run_coroutine_threadsafe(self._disconnect(), self._loop)
        else:
            asyncio.run_coroutine_threadsafe(self._connect(), self._loop)

    async def _connect(self):
        try:
            config.load_from_db(self._db)  # Make sure the config settings are fresh
            client = TelegramBotClient(
                db=self._db,
                on_log=lambda e: self._bridge.log_received.emit(e),
                on_status_change=lambda s: self._bridge.status_changed.emit(s),
                on_security_event=lambda uid, uname, action, reason, dur: self._bridge.security_event.emit({
                    "user_id": uid, "username": uname, "description": f"{action}: {reason}", "severity": "high"
                })
            )
            await client.connect()
            if self._db.get_setting("automation_active", "0") == "1":
                client.set_active(True)
            self._bot_ref.append(client)
            self._connect_btn.setText("⏏  Disconnect")
        except Exception as exc:
            self._bridge.status_changed.emit(f"ERROR: {exc}")

    async def _disconnect(self):
        if self._bot_ref:
            client = self._bot_ref.pop()
            await client.disconnect()
            self._connect_btn.setText("⟳  Connect")
            self._bridge.status_changed.emit("DISCONNECTED")