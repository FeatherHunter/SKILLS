"""MainWindow: assembles all UI widgets and wires them to ClickerEngine / hotkeys."""
from __future__ import annotations
import ctypes
import os
import sys
from ctypes import wintypes

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QIcon, QCursor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QSlider,
    QSpinBox, QVBoxLayout, QHBoxLayout, QButtonGroup, QFrame, QSizePolicy,
)

from src.clicker import ClickerEngine
from src.resources import resource_path
from src.config import AppConfig
from src.hotkeys import GlobalHotkeyManager


class SegmentedRow(QFrame):
    """A horizontal row of equal-width toggle buttons styled as a segmented control."""
    changed = Signal(str)

    _UNCHECKED_QSS = (
        "QPushButton { background: #ffffff; color: #444; border: none;"
        " border-right: 1px solid #d0d0d0;"
        " padding: 8px 6px; font-size: 13px; font-weight: 500; }"
        "QPushButton:hover { background: #f5f5f7; color: #0067c0; }"
        "QPushButton:pressed { background: #e8e8ea; }"
    )
    _CHECKED_QSS = (
        "QPushButton { background: #0067c0; color: white; border: none;"
        " border-right: 1px solid #0058a3;"
        " padding: 8px 6px; font-size: 13px; font-weight: 600; }"
        "QPushButton:hover { background: #0078d4; color: white; }"
    )

    def __init__(self, label: str, options: list[tuple[str, str]], parent=None):
        super().__init__(parent)
        self.setObjectName("settingsCard")
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)
        lbl = QLabel(label)
        lbl.setProperty("class", "settingLabel")
        lbl.setContentsMargins(2, 0, 0, 0)
        v.addWidget(lbl)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._options: list[tuple[str, str]] = list(options)
        self._buttons: list[QPushButton] = []
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        for value, text in options:
            b = QPushButton(text)
            b.setCheckable(True)
            b.setMinimumHeight(30)
            b.setCursor(QCursor(Qt.PointingHandCursor))
            b.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            b.setStyleSheet(self._UNCHECKED_QSS)
            self._group.addButton(b)
            b.toggled.connect(lambda checked, v=value: self._on_toggled(v, checked))
            row.addWidget(b)
            self._buttons.append(b)
        # remove right border on last button
        if self._buttons:
            self._buttons[-1].setStyleSheet(self._UNCHECKED_QSS.replace(
                "border-right: 1px solid #d0d0d0;", ""))
        v.addLayout(row)
        self._value = options[0][0]
        self._buttons[0].setChecked(True)
        self._refresh_styles()

    def _on_toggled(self, value: str, checked: bool) -> None:
        if checked:
            self._value = value
            self._refresh_styles()
            self.changed.emit(value)

    def _refresh_styles(self):
        for i, btn in enumerate(self._buttons):
            is_last = (i == len(self._buttons) - 1)
            border_rule = "" if is_last else "border-right: 1px solid #d0d0d0;"
            base = self._CHECKED_QSS if btn.isChecked() else self._UNCHECKED_QSS
            # remove stale border-right then re-add conditionally
            cleaned = base.replace("border-right: 1px solid #d0d0d0;", "").replace(
                "border-right: 1px solid #0058a3;", "")
            btn.setStyleSheet(cleaned + ("border-right: 1px solid #0058a3;" if (btn.isChecked() and not is_last) else border_rule))

    def value(self) -> str:
        return self._value

    def set_value(self, v: str) -> None:
        for btn, (val, _txt) in zip(self._buttons, self._options):
            if val == v:
                btn.setChecked(True)
                self._value = v
                self._refresh_styles()
                return
        self._buttons[0].setChecked(True)
        self._value = self._options[0][0]



class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig, clicker: ClickerEngine,
                 hotkeys: GlobalHotkeyManager):
        super().__init__()
        self._config = config
        self._clicker = clicker
        self._hotkeys = hotkeys

        self.setWindowTitle("鼠标连点器")
        self.resize(380, 660)
        self.setMinimumSize(380, 620)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowIcon(QIcon(resource_path("assets/icon.ico")))

        central = QWidget()
        central.setObjectName("central")
        central.setStyleSheet(
            "QWidget#central { background: rgba(248,249,251,0.92); border-radius: 14px;"
            " border: 1px solid rgba(0,0,0,0.06); }"
        )
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)

        # Title bar
        titlebar = QHBoxLayout()
        titlebar.setContentsMargins(0, 0, 0, 0)
        title = QLabel("鼠标连点器")
        title.setObjectName("title")
        title.setStyleSheet("font-size: 15px; font-weight: 600; color: #1a1a1a;")
        titlebar.addWidget(title)
        titlebar.addStretch()
        self._btn_close = QPushButton("✕")
        self._btn_close.setFixedSize(28, 28)
        self._btn_close.setStyleSheet(
            "QPushButton { background: transparent; color: #777; border: none;"
            " font-size: 14px; border-radius: 14px; }"
            "QPushButton:hover { background: #e0e0e0; color: #333; }"
        )
        self._btn_close.setCursor(QCursor(Qt.PointingHandCursor))
        self._btn_close.clicked.connect(self.hide)
        titlebar.addWidget(self._btn_close)
        layout.addLayout(titlebar)

        # Status row
        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 0, 0, 0)
        status_row.setSpacing(8)
        self._status = QLabel("已停止")
        self._status.setObjectName("statusBadge")
        self._refresh_status_style()
        status_row.addWidget(self._status)
        status_row.addStretch()
        self._params_label = QLabel("")
        self._params_label.setStyleSheet(
            "color:#999; font-size:11px; font-weight: 400;"
        )
        status_row.addWidget(self._params_label)
        layout.addLayout(status_row)

        # CTA
        self._cta = QPushButton("启  动")
        self._cta.setObjectName("cta")
        self._cta.setProperty("class", "")
        self._cta.setMinimumHeight(52)
        self._cta.setCursor(QCursor(Qt.PointingHandCursor))
        self._cta.clicked.connect(self._on_toggle_clicked)
        layout.addWidget(self._cta)

        # Interval
        interval_card = QFrame()
        interval_card.setObjectName("settingsCard")
        iv = QVBoxLayout(interval_card)
        iv.setContentsMargins(12, 8, 12, 12)
        iv.setSpacing(4)
        iv.addWidget(self._make_setting_label("点击间隔"))
        h = QHBoxLayout()
        self._slider = QSlider(Qt.Horizontal)
        self._slider.setMinimum(10)
        self._slider.setMaximum(10000)
        self._slider.setSingleStep(10)
        self._slider.setPageStep(100)
        self._slider.setValue(self._config.interval_ms)
        self._spin = QSpinBox()
        self._spin.setMinimum(10)
        self._spin.setMaximum(10000)
        self._spin.setSuffix(" ms")
        self._spin.setValue(self._config.interval_ms)
        self._slider.valueChanged.connect(self._spin.setValue)
        self._spin.valueChanged.connect(self._slider.setValue)
        self._spin.valueChanged.connect(lambda _v: self._on_param_changed())
        h.addWidget(self._slider, 1)
        h.addWidget(self._spin)
        iv.addLayout(h)
        layout.addWidget(interval_card)

        # Segmented rows
        self._button_row = SegmentedRow(
            "按键", [("left", "左"), ("right", "右"), ("middle", "中")]
        )
        self._click_type_row = SegmentedRow(
            "类型", [("single", "单击"), ("double", "双击")]
        )
        self._pos_mode_row = SegmentedRow(
            "位置",
            [("follow", "跟随鼠标"), ("current", "当前位置")],
        )
        self._button_row.set_value(self._config.button)
        self._click_type_row.set_value(self._config.click_type)
        self._pos_mode_row.set_value(self._config.position_mode)
        self._button_row.changed.connect(lambda _v: self._on_param_changed())
        self._click_type_row.changed.connect(lambda _v: self._on_param_changed())
        self._pos_mode_row.changed.connect(lambda _v: self._on_param_changed())
        layout.addWidget(self._button_row)
        layout.addWidget(self._click_type_row)
        layout.addWidget(self._pos_mode_row)

        # Stats
        stats_row = QHBoxLayout()
        stats_row.setContentsMargins(0, 0, 0, 0)
        stats_row.setSpacing(8)
        count_card = QFrame()
        count_card.setObjectName("settingsCard")
        count_card.setMinimumHeight(48)
        cv = QVBoxLayout(count_card)
        cv.setContentsMargins(6, 6, 6, 6)
        cv.setSpacing(0)
        self._count_label = QLabel("0")
        self._count_label.setObjectName("statValue")
        self._count_label.setAlignment(Qt.AlignCenter)
        k = QLabel("已点击")
        k.setObjectName("statKey")
        k.setAlignment(Qt.AlignCenter)
        cv.addWidget(k)
        cv.addWidget(self._count_label)
        stats_row.addWidget(count_card, 1)

        elapsed_card = QFrame()
        elapsed_card.setObjectName("settingsCard")
        elapsed_card.setMinimumHeight(48)
        ev = QVBoxLayout(elapsed_card)
        ev.setContentsMargins(6, 6, 6, 6)
        ev.setSpacing(0)
        self._elapsed_label = QLabel("00:00")
        self._elapsed_label.setObjectName("statValue")
        self._elapsed_label.setAlignment(Qt.AlignCenter)
        k2 = QLabel("运行时长")
        k2.setObjectName("statKey")
        k2.setAlignment(Qt.AlignCenter)
        ev.addWidget(k2)
        ev.addWidget(self._elapsed_label)
        stats_row.addWidget(elapsed_card, 1)
        layout.addLayout(stats_row)

        # Footer
        footer = QLabel(
            f"{self._config.hotkey_toggle} 启停  ·  Esc 急停  ·  "
            f"{self._config.hotkey_show} 显示"
        )
        footer.setObjectName("footer")
        footer.setAlignment(Qt.AlignCenter)
        layout.addWidget(footer)
        layout.addStretch()

        # Wire engine signals
        self._clicker.started.connect(self._on_clicker_started)
        self._clicker.stopped.connect(self._on_clicker_stopped)
        self._clicker.stats_updated.connect(self._on_stats)
        self._clicker.error.connect(self._on_clicker_error)

        # Save debounce
        self._save_timer = QTimer(self)
        self._save_timer.setInterval(500)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._config.save)

        # CTA-start countdown (give user time to move cursor to target)
        self._start_countdown_timer = QTimer(self)
        self._start_countdown_timer.setSingleShot(True)
        self._start_countdown_timer.setInterval(2000)
        self._start_countdown_timer.timeout.connect(self._commit_start)
        self._start_countdown_remaining = 0

        # Wire hotkey activation into us
        self._hotkeys._on_activate = self._on_hotkey

        # Attach hotkey HWND after window is realized
        self._hwnd = int(self.winId())
        self._hotkeys.attach(self._hwnd)

        # Publish HWND for second-instance discovery (single-instance raise)
        try:
            from pathlib import Path
            hwnd_path = Path(os.environ.get("TEMP", ".")) / "autoclicker.hwnd"
            hwnd_path.write_text(str(self._hwnd), encoding="utf-8")
        except OSError:
            pass

        # Initial clicker configure
        self._apply_clicker_config()

        # Apply initial direct styles
        self._update_cta_style()

    def _make_setting_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setProperty("class", "settingLabel")
        return lbl

    def _refresh_status_style(self):
        running = self._clicker.is_running()
        if running:
            bg, fg = "#2e7d32", "#ffffff"
        else:
            bg, fg = "#d0d0d0", "#555555"
        self._status.setStyleSheet(
            f"QLabel {{ background: {bg}; color: {fg}; padding: 5px 14px;"
            f" border-radius: 12px; font-size: 12px; font-weight: 600; }}"
        )

    def _apply_clicker_config(self) -> None:
        self._clicker.configure(
            interval_ms=self._spin.value(),
            button=self._button_row.value(),
            click_type=self._click_type_row.value(),
            position_mode=self._pos_mode_row.value(),
            locked_xy=(0, 0),
        )
        self._params_label.setText(
            f"{self._spin.value()}ms · {self._button_row.value()} · "
            f"{self._pos_mode_row.value()}"
        )

    def _on_param_changed(self):
        self._config.interval_ms = self._spin.value()
        self._config.button = self._button_row.value()
        self._config.click_type = self._click_type_row.value()
        self._config.position_mode = self._pos_mode_row.value()
        self._save_timer.start()
        self._apply_clicker_config()

    def _on_toggle_clicked(self) -> None:
        if self._clicker.is_running():
            self._clicker.stop()
            return
        if self._capture_active:
            return
        # If countdown is in progress, second click cancels it (treated as toggle)
        if self._start_countdown_timer.isActive():
            self._start_countdown_timer.stop()
            if hasattr(self, "_start_countdown_tick") and self._start_countdown_tick:
                self._start_countdown_tick.stop()
                self._start_countdown_tick = None
            self._cta.setText("启  动")
            self._cta.setEnabled(True)
            self._status.setText("已停止")
            return
        # Start a 2-second countdown so user can move cursor to target.
        self._start_countdown_remaining = 2
        self._refresh_cta_countdown()
        self._start_countdown_timer.start()
        self._start_countdown_tick = QTimer(self)
        self._start_countdown_tick.setInterval(500)
        self._start_countdown_tick.timeout.connect(self._refresh_cta_countdown)
        self._start_countdown_tick.start()

    def _refresh_cta_countdown(self):
        self._start_countdown_remaining -= 0.5
        if self._start_countdown_remaining <= 0:
            if hasattr(self, "_start_countdown_tick") and self._start_countdown_tick:
                self._start_countdown_tick.stop()
                self._start_countdown_tick = None
            return
        self._status.setText("准备中…")
        self._cta.setText(f"{int(self._start_countdown_remaining + 0.5)} 秒后开始")
        self._cta.setEnabled(False)

    def _commit_start(self):
        """Called when the 2-second CTA countdown elapses. Captures cursor pos NOW."""
        self._cta.setEnabled(True)
        if hasattr(self, "_start_countdown_tick") and self._start_countdown_tick:
            self._start_countdown_tick.stop()
            self._start_countdown_tick = None
        self._clicker.reset_captured_position()
        self._clicker.start()

    def _on_clicker_started(self) -> None:
        # Clicker started (possibly via F6 hotkey mid-countdown). Stop the
        # countdown tick so it doesn't overwrite "运行中" with "准备中…".
        self._cancel_start_countdown()
        self._status.setText("运行中")
        self._cta.setText("停止")
        self._refresh_status_style()
        self._update_cta_style()
        # Reset stats display so old run's count doesn't flash for slow intervals.
        self._count_label.setText("0")
        self._elapsed_label.setText("00:00")

    def _on_clicker_stopped(self) -> None:
        self._status.setText("已停止")
        self._cta.setText("启  动")
        self._refresh_status_style()
        self._update_cta_style()

    def _cancel_start_countdown(self):
        """Cancel any in-progress CTA-start countdown (idempotent)."""
        if self._start_countdown_timer.isActive():
            self._start_countdown_timer.stop()
        if hasattr(self, "_start_countdown_tick") and self._start_countdown_tick:
            self._start_countdown_tick.stop()
            self._start_countdown_tick = None
        self._cta.setText("启  动")
        self._cta.setEnabled(True)

    def _update_cta_style(self):
        running = self._clicker.is_running()
        if running:
            grad = "stop:0 #e81123, stop:1 #c00000"
        else:
            grad = "stop:0 #0067c0, stop:1 #4a6ee0"
        self._cta.setStyleSheet(
            f"QPushButton {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:1, {grad});"
            f" color: white; border: none; border-radius: 8px; padding: 16px;"
            f" font-size: 17px; font-weight: 600; letter-spacing: 4px; }}"
            f"QPushButton:hover {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:1, {grad}); }}"
        )

    def _update_styles(self) -> None:
        self._refresh_status_style()
        self._update_cta_style()

    def _on_stats(self, count: int, elapsed_ms: int) -> None:
        self._count_label.setText(f"{count:,}")
        s = elapsed_ms // 1000
        self._elapsed_label.setText(f"{s//60:02d}:{s%60:02d}")

    def _on_clicker_error(self, msg: str) -> None:
        # Non-fatal click failure (e.g. SetCursorPos / SendInput returned false).
        # We don't stop the loop on a single error — just surface to user.
        # Append to tooltip on CTA so it's discoverable without modal dialogs.
        self._cta.setToolTip(f"点击错误（已自动跳过）：{msg}")

    def _on_hotkey(self, name: str):
        import os
        from pathlib import Path
        try:
            log = Path(os.environ.get("TEMP", ".")) / "autoclicker_hotkey.log"
            with open(log, "a", encoding="utf-8") as f:
                f.write(f"[on_hotkey] name={name} running={self._clicker.is_running()}\n")
        except OSError:
            pass
        if name == "toggle":
            # Hotkey path: instant start, cursor already at target
            if self._clicker.is_running():
                self._clicker.stop()
            else:
                self._clicker.reset_captured_position()
                self._clicker.start()
        elif name == "panic":
            if self._clicker.is_running():
                self._clicker.stop()
            elif self._start_countdown_timer.isActive():
                self._start_countdown_timer.stop()
                if hasattr(self, "_start_countdown_tick") and self._start_countdown_tick:
                    self._start_countdown_tick.stop()
                    self._start_countdown_tick = None
                    self._cta.setText("启  动")
                    self._cta.setEnabled(True)
                    self._status.setText("已停止")
        elif name == "show":
            if self.isVisible():
                # Hiding: cancel pending countdown
                if self._start_countdown_timer.isActive():
                    self._start_countdown_timer.stop()
                if hasattr(self, "_start_countdown_tick") and self._start_countdown_tick:
                    self._start_countdown_tick.stop()
                    self._start_countdown_tick = None
                    self._cta.setText("启  动")
                    self._cta.setEnabled(True)
                    self._status.setText("已停止")
                self.hide()
            else:
                self.showNormal()
                self.activateWindow()
                self.raise_()

    def _start_capture_mode(self):
        # Removed: locked-coordinate mode was deleted. Kept as no-op stub
        # in case any leftover signal connection references it.
        pass

    def _cancel_capture_mode(self):
        pass

    def _perform_capture(self):
        pass

    def mousePressEvent(self, event):
        # Allow dragging from anywhere in the title bar (everything above the
        # status row). The first child widget in the layout is the title HBox.
        title_height = self._title_bar_height() if hasattr(self, "_title_bar_height") else 36
        if event.button() == Qt.LeftButton and event.y() < title_height:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if hasattr(self, "_drag_pos") and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def _title_bar_height(self) -> int:
        """Actual height of the drag region (title bar). Includes outer padding."""
        try:
            top_layout = self.centralWidget().layout()
            if top_layout is None:
                return 36
            # First child is the titlebar layout
            first_item = top_layout.itemAt(0)
            if first_item is None:
                return 36
            geom = first_item.geometry()
            return geom.bottom() + top_layout.spacing()
        except Exception:
            return 36

    def closeEvent(self, event):
        # Cancel any pending CTA countdown so clicker doesn't silently start
        # while window is closing.
        if self._start_countdown_timer.isActive():
            self._start_countdown_timer.stop()
        if hasattr(self, "_start_countdown_tick") and self._start_countdown_tick:
            self._start_countdown_tick.stop()
            self._start_countdown_tick = None
            self._cta.setText("启  动")
            self._cta.setEnabled(True)
            self._status.setText("已停止")
        # Closing the window quits the app entirely (same path as tray 退出):
        # hide-only behavior left the indicator dot orphaned on screen.
        # The app-level _quit (app.py) handles clicker.stop(), config.save(),
        # single-instance release, indicator.hide() and app.quit(). We trigger
        # it via QApplication.aboutToQuit -> app.quit, but first run the
        # critical cleanup here in case the app-level _quit isn't wired.
        try:
            if self._clicker.is_running():
                self._clicker.stop()
        except Exception:
            pass
        try:
            self._config.save()
        except Exception:
            pass
        app = QApplication.instance()
        if app is not None:
            app.quit()
        event.accept()
