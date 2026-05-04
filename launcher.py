import sys
import os
import importlib.util
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTabWidget, QTextEdit, QLabel
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import Qt, QSize


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowIcon(QIcon("icon.png"))
        self.setWindowTitle("Guubal App Launcher")
        self.resize(700, 450)

        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Home tab
        self.home = QWidget()
        self.tabs.addTab(self.home, "Home")

        home_layout = QVBoxLayout(self.home)

        # Scan apps folder
        apps_folder = "apps"
        self.apps = []

        for folder in sorted(os.listdir(apps_folder)):
            full_path = os.path.join(apps_folder, folder)
            if os.path.isdir(full_path):
                main_py = os.path.join(full_path, "main.py")
                if os.path.exists(main_py):
                    self.apps.append(folder)

        if not self.apps:
            home_layout.addWidget(QLabel("No apps found in /apps"))
        else:
            for app in self.apps:
                app_path = os.path.join(apps_folder, app)

                icon = QIcon()
                for ext in ["png", "jpg", "jpeg"]:
                    icon_path = os.path.join(app_path, f"icon.{ext}")
                    if os.path.exists(icon_path):
                        icon = QIcon(icon_path)
                        break

                btn = QPushButton(app)
                btn.setIcon(icon)
                btn.setIconSize(QSize(16, 16))
                btn.clicked.connect(lambda _, a=app: self.open_app(a))
                home_layout.addWidget(btn)

    # Module loading
    def _load_app_module(self, folder_name):
        """Dynamically import the app's main.py as a module."""
        main_file = os.path.join("apps", folder_name, "main.py")
        spec = importlib.util.spec_from_file_location(f"apps.{folder_name}.main", main_file)
        module = importlib.util.module_from_spec(spec)

        app_dir = os.path.abspath(os.path.join("apps", folder_name))
        if app_dir not in sys.path:
            sys.path.insert(0, app_dir)

        spec.loader.exec_module(module)
        return module

    def _find_main_widget(self, module):
        """
        Find the app's main widget class. Looks for, in order:
          1. A module-level variable called `main_widget` (an instance)
          2. A class that is a subclass of QWidget (but not QWidget itself)
             and is defined in that module (not imported into it).
        Returns an *instance* of the widget, or None.
        """
        if hasattr(module, "main_widget"):
            return module.main_widget

        for name, obj in vars(module).items():
            if (
                isinstance(obj, type)
                and issubclass(obj, QWidget)
                and obj is not QWidget
                and obj.__module__ == module.__name__
            ):
                try:
                    return obj()
                except TypeError:
                    continue

        return None

    # Top bar: [✕]App Name[↻]
    def _make_top_bar(self, folder_name):
        bar = QWidget()
        bar.setStyleSheet("""
            QWidget {
                background-color: #2a2a3d;
                border-bottom: 1px solid #3a3a52;
            }
        """)
        bar.setFixedHeight(34)

        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(6, 0, 6, 0)
        bar_layout.setSpacing(4)

        # close button (left)
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 26)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                color: #a0a0b8;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e04545;
                border-color: #e04545;
                color: #ffffff;
            }
        """)
        close_btn.setToolTip(f"Close {folder_name}")
        close_btn.clicked.connect(lambda: self._close_current_tab())
        bar_layout.addWidget(close_btn)

        bar_layout.addStretch()

        # app name (center)
        name_label = QLabel(folder_name)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet("""
            QLabel {
                color: #d0d0e8;
                font-size: 13px;
                font-weight: bold;
                background: transparent;
                border: none;
            }
        """)
        bar_layout.addWidget(name_label)

        bar_layout.addStretch()

        # reload button (right)
        reload_btn = QPushButton("↻")
        reload_btn.setFixedSize(28, 26)
        reload_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
                color: #a0a0b8;
                font-size: 15px;
            }
            QPushButton:hover {
                background-color: #3a3a52;
                border-color: #4a4a62;
                color: #ffffff;
            }
        """)
        reload_btn.setToolTip(f"Reload {folder_name}")
        reload_btn.clicked.connect(lambda: self._reload_app(folder_name))
        bar_layout.addWidget(reload_btn)

        return bar
    # Open / close / reload
    def open_app(self, folder_name):
        """Dynamically load the app and embed its main widget into a new tab."""

        # prevent duplicate tabs
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i) == folder_name:
                self.tabs.setCurrentIndex(i)
                return

        # tab shell
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # tab icon
        icon = QIcon()
        app_path = os.path.join("apps", folder_name)
        for ext in ["png", "jpg", "jpeg"]:
            icon_path = os.path.join(app_path, f"icon.{ext}")
            if os.path.exists(icon_path):
                icon = QIcon(icon_path)
                break

        # top bar sits above the app
        layout.addWidget(self._make_top_bar(folder_name))

        # load & embed the app
        try:
            module = self._load_app_module(folder_name)
            widget = self._find_main_widget(module)

            if widget is None:
                err = QTextEdit()
                err.setReadOnly(True)
                err.setText(
                    f"<b>{folder_name}</b> loaded, but no embeddable QWidget was found.<br><br>"
                    f"To fix this, either:<br>"
                    f"&nbsp;&nbsp;• Add a module-level <code>main_widget = YourWidget()</code> in main.py<br>"
                    f"&nbsp;&nbsp;• Or define a single QWidget subclass in main.py<br>"
                )
                layout.addWidget(err)
            else:
                widget.setParent(tab)
                widget.show()
                layout.addWidget(widget)

        except Exception:
            import traceback
            err = QTextEdit()
            err.setReadOnly(True)
            err.setText(f"<b>Error loading {folder_name}:</b><br><pre>{traceback.format_exc()}</pre>")
            layout.addWidget(err)

        self.tabs.addTab(tab, icon, folder_name)
        self.tabs.setCurrentWidget(tab)

    def _close_current_tab(self):
        """Close whichever tab is active, unless it's Home (index 0)."""
        idx = self.tabs.currentIndex()
        if idx > 0:
            self.tabs.removeTab(idx)

    def _reload_app(self, folder_name):
        """Close the tab if it's open, then reopen it fresh."""
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i) == folder_name:
                self.tabs.removeTab(i)
                break
        self.open_app(folder_name)


app = QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec())
