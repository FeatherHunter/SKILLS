"""Tray icon with right-click menu (show / toggle / quit)."""
from __future__ import annotations
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from src.resources import resource_path


class TrayController:
    def __init__(self, app, on_show, on_toggle, on_quit):
        self._app = app
        self._icon_idle = QIcon(resource_path("assets/icon.ico"))
        self._icon_running = QIcon(resource_path("assets/icon-running.ico"))
        self._tray = QSystemTrayIcon(self._icon_idle, parent=app)
        self._tray.setToolTip("鼠标连点器")

        menu = QMenu()
        self._action_show = QAction("显示主窗口", menu)
        self._action_show.triggered.connect(on_show)
        self._action_toggle = QAction("启停", menu)
        self._action_toggle.triggered.connect(on_toggle)
        action_quit = QAction("退出", menu)
        action_quit.triggered.connect(on_quit)
        menu.addAction(self._action_show)
        menu.addAction(self._action_toggle)
        menu.addSeparator()
        menu.addAction(action_quit)
        self._tray.setContextMenu(menu)

        self._tray.activated.connect(self._on_activated)
        self._tray.show()

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self._action_show.trigger()

    def set_running(self, running: bool) -> None:
        self._tray.setIcon(self._icon_running if running else self._icon_idle)
        self._action_toggle.setText("停止" if running else "启动")

    def hide(self):
        self._tray.hide()
