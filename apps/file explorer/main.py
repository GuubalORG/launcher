import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QTabWidget, QLabel, QTextEdit, QSizePolicy, QPushButton
)
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import Qt

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".ico", ".tiff", ".tif"}
APPS_FOLDER = "apps"


class FileExplorerApp(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.open_tabs = {}  # path -> tab widget, for deduplication

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Tabs — closable is OFF. Each file tab has its own ✕ button instead.
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # --- Explorer tab (index 0, permanent) ---
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(18)
        self.tree.setRootIsDecorated(True)
        self.tree.itemDoubleClicked.connect(self._on_double_click)
        self.tree.setStyleSheet("""
            QTreeWidget {
                font-size: 13px;
                background-color: #1e1e2e;
                color: #cdd6f4;
                border: none;
                padding: 4px;
            }
            QTreeWidget::item { padding: 3px 0; }
            QTreeWidget::item:hover { background-color: #313244; }
            QTreeWidget::item:selected { background-color: #45475a; color: #cdd6f4; }
        """)

        explorer_wrap = QWidget()
        explorer_wrap_layout = QVBoxLayout(explorer_wrap)
        explorer_wrap_layout.setContentsMargins(0, 0, 0, 0)
        explorer_wrap_layout.addWidget(self.tree)

        self.tabs.addTab(explorer_wrap, "Explorer")
        self._build_tree()

    # -----------------------------------------------------------
    # Tree building
    # -----------------------------------------------------------
    def _build_tree(self):
        self.tree.clear()
        if not os.path.isdir(APPS_FOLDER):
            QTreeWidgetItem(self.tree).setText(0, "apps/ folder not found")
            return
        self._add_level(self.tree, APPS_FOLDER)
        self.tree.expandAll()

    def _add_level(self, parent, dir_path):
        try:
            entries = os.listdir(dir_path)
        except PermissionError:
            QTreeWidgetItem(parent).setText(0, "[Permission denied]")
            return

        dirs  = sorted(e for e in entries if os.path.isdir(os.path.join(dir_path, e)))
        files = sorted(e for e in entries if os.path.isfile(os.path.join(dir_path, e)))

        for d in dirs:
            full = os.path.join(dir_path, d)
            item = QTreeWidgetItem(parent)
            item.setText(0, d + "/")
            item.setData(0, Qt.ItemDataRole.UserRole, full)
            item.setData(0, Qt.ItemDataRole.UserRole + 1, "dir")
            self._add_level(item, full)

        for f in files:
            full = os.path.join(dir_path, f)
            item = QTreeWidgetItem(parent)
            item.setText(0, f)
            item.setData(0, Qt.ItemDataRole.UserRole, full)
            item.setData(0, Qt.ItemDataRole.UserRole + 1, "file")

            if os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS:
                px = QPixmap(full)
                if not px.isNull():
                    item.setIcon(0, QIcon(px.scaled(16, 16)))

    # -----------------------------------------------------------
    # Double click handler
    # -----------------------------------------------------------
    def _on_double_click(self, item, _col):
        if item.data(0, Qt.ItemDataRole.UserRole + 1) == "dir":
            item.setExpanded(not item.isExpanded())
            return

        path = item.data(0, Qt.ItemDataRole.UserRole)
        if not path or not os.path.isfile(path):
            return

        # already open → just switch
        if path in self.open_tabs:
            self.tabs.setCurrentWidget(self.open_tabs[path])
            return

        # image or text?
        if os.path.splitext(path)[1].lower() in IMAGE_EXTENSIONS:
            tab = self._make_image_tab(path)
        else:
            tab = self._make_text_tab(path)

        self.open_tabs[path] = tab
        self.tabs.addTab(tab, os.path.basename(path))
        self.tabs.setCurrentWidget(tab)

    # -----------------------------------------------------------
    # Close helper
    # -----------------------------------------------------------
    def _close_button(self, path):
        btn = QPushButton("✕")
        btn.setFixedSize(22, 22)
        btn.setStyleSheet("""
            QPushButton { background:none; border:none; color:#a6adc8; font-size:12px; padding:0; }
            QPushButton:hover { color:#f38ba8; }
        """)
        btn.clicked.connect(lambda: self._remove_tab(path))
        return btn

    def _remove_tab(self, path):
        tab = self.open_tabs.pop(path, None)
        if tab:
            self.tabs.removeTab(self.tabs.indexOf(tab))

    # -----------------------------------------------------------
    # Image tab
    # -----------------------------------------------------------
    def _make_image_tab(self, path):
        root = QWidget()
        root.setStyleSheet("background-color:#1e1e2e;")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(8, 8, 8, 8)

        # close button top-right
        top = QWidget()
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addStretch()
        top_layout.addWidget(self._close_button(path))
        layout.addWidget(top)

        # path label
        lbl = QLabel(path)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("color:#a6adc8; font-size:11px;")
        layout.addWidget(lbl)

        # pixmap
        img = QLabel()
        img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        img.setPixmap(QPixmap(path))
        layout.addWidget(img, stretch=1)

        return root

    # -----------------------------------------------------------
    # Text tab
    # -----------------------------------------------------------
    def _make_text_tab(self, path):
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)

        # top bar with path + close button
        bar = QWidget()
        bar.setStyleSheet("background-color:#181825;")
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(8, 4, 8, 4)
        bar_layout.addWidget(QLabel(path), stretch=1)
        bar_layout.addWidget(self._close_button(path))
        bar.findChild(QLabel).setStyleSheet("color:#a6adc8; font-size:11px;")
        layout.addWidget(bar)

        # editor
        editor = QTextEdit()
        editor.setReadOnly(True)
        editor.setStyleSheet("""
            QTextEdit {
                background-color:#1e1e2e; color:#cdd6f4; border:none;
                font-family:'Consolas','Courier New',monospace;
                font-size:13px; padding:8px;
            }
        """)
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                editor.setPlainText(f.read())
        except Exception as e:
            editor.setPlainText(f"Could not read file:\n{e}")

        layout.addWidget(editor)
        return root


# Guubal hook
main_widget = FileExplorerApp()
