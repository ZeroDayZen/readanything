#!/usr/bin/env python3
"""
ReadAnything Uninstaller - Remove ReadAnything application
Works on Linux and macOS
"""

import sys
import os
import platform
import subprocess
import shutil
import json
from pathlib import Path

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QTextEdit, QMessageBox, QCheckBox
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal
    from PyQt6.QtGui import QFont, QIcon
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False


class UninstallThread(QThread):
    """Thread for running uninstallation tasks"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, remove_system_deps, remove_project_dir):
        super().__init__()
        self.remove_system_deps = remove_system_deps
        self.remove_project_dir = remove_project_dir
        self.project_dir = Path(__file__).parent.absolute()
        self.home_dir = Path.home()

    def _xdg_data_home(self) -> Path:
        xdg = os.environ.get("XDG_DATA_HOME")
        if xdg:
            return Path(xdg).expanduser()
        return self.home_dir / ".local" / "share"

    def _xdg_config_home(self) -> Path:
        xdg = os.environ.get("XDG_CONFIG_HOME")
        if xdg:
            return Path(xdg).expanduser()
        return self.home_dir / ".config"
        
    def run(self):
        try:
            removed_items = []
            errors = []
            
            # 1. Remove virtual environment
            self.progress.emit("Removing virtual environment...")
            venv_path = self.project_dir / 'venv'
            if venv_path.exists():
                try:
                    shutil.rmtree(venv_path)
                    removed_items.append("✓ Virtual environment removed")
                except Exception as e:
                    errors.append(f"✗ Failed to remove venv: {e}")
            
            # 2. Remove desktop shortcut (Linux)
            if platform.system() != 'Darwin':
                self.progress.emit("Removing desktop shortcut...")
                desktop_file = self.home_dir / '.local' / 'share' / 'applications' / 'readanything.desktop'
                if desktop_file.exists():
                    try:
                        desktop_file.unlink()
                        removed_items.append("✓ Desktop shortcut removed")
                    except Exception as e:
                        errors.append(f"✗ Failed to remove desktop shortcut: {e}")

                # Remove bundled Piper binary if installed
                self.progress.emit("Removing bundled Piper (if installed)...")
                piper_runtime_dir = self._xdg_data_home() / "readanything" / "piper"
                if piper_runtime_dir.exists():
                    try:
                        shutil.rmtree(piper_runtime_dir)
                        removed_items.append("✓ Bundled Piper removed")
                    except Exception as e:
                        errors.append(f"✗ Failed to remove bundled Piper: {e}")

                # Remove settings file (contains piper path)
                settings_path = self._xdg_config_home() / "readanything" / "settings.json"
                if settings_path.exists():
                    try:
                        settings_path.unlink()
                        removed_items.append("✓ Settings removed")
                    except Exception as e:
                        errors.append(f"✗ Failed to remove settings: {e}")
            else:
                # macOS: Remove .app bundle
                self.progress.emit("Removing application bundle...")
                app_bundle = self.project_dir / 'ReadAnything.app'
                if app_bundle.exists():
                    try:
                        shutil.rmtree(app_bundle)
                        removed_items.append("✓ Application bundle removed")
                    except Exception as e:
                        errors.append(f"✗ Failed to remove app bundle: {e}")
                
                # Also check /Applications if user copied it there
                applications_app = Path('/Applications/ReadAnything.app')
                if applications_app.exists():
                    try:
                        shutil.rmtree(applications_app)
                        removed_items.append("✓ Application bundle removed from /Applications")
                    except PermissionError:
                        errors.append("✗ Permission denied removing /Applications/ReadAnything.app (run with sudo)")
                    except Exception as e:
                        errors.append(f"✗ Failed to remove /Applications bundle: {e}")
            
            # 3. Remove system dependencies (Linux only, optional)
            if self.remove_system_deps and platform.system() != 'Darwin':
                self.progress.emit("Removing system dependencies...")
                packages = [
                    'espeak', 'espeak-data', 'libespeak1', 'libespeak-dev',
                    'python3-pyqt6', 'python3-pyqt6.qtmultimedia',
                    'xclip', 'xsel'
                ]
                # Note: We don't remove alsa-utils and pulseaudio as they're system-critical
                
                try:
                    result = subprocess.run(
                        ['sudo', 'apt-get', 'remove', '-y'] + packages,
                        capture_output=True,
                        text=True,
                        timeout=120
                    )
                    if result.returncode == 0:
                        removed_items.append("✓ System dependencies removed")
                    else:
                        errors.append(f"✗ Failed to remove system dependencies: {result.stderr}")
                except subprocess.TimeoutExpired:
                    errors.append("✗ System dependency removal timed out")
                except Exception as e:
                    errors.append(f"✗ Error removing system dependencies: {e}")
            
            # 4. Remove project directory (optional)
            if self.remove_project_dir:
                self.progress.emit("Removing project directory...")
                parent_dir = self.project_dir.parent
                try:
                    # Don't remove if we're still in it - that would be dangerous
                    # Only remove if explicitly requested and we can safely do so
                    if self.project_dir.exists() and self.project_dir != Path.cwd():
                        shutil.rmtree(self.project_dir)
                        removed_items.append(f"✓ Project directory removed: {self.project_dir}")
                except Exception as e:
                    errors.append(f"✗ Failed to remove project directory: {e}")
            
            # Compile results
            message_parts = []
            if removed_items:
                message_parts.append("Successfully removed:")
                message_parts.extend(removed_items)
            
            if errors:
                message_parts.append("\nErrors encountered:")
                message_parts.extend(errors)
            
            if not removed_items and not errors:
                message = "Nothing to remove - ReadAnything doesn't appear to be installed."
            else:
                message = "\n".join(message_parts)
            
            success = len(errors) == 0
            self.finished.emit(success, message)
            
        except Exception as e:
            self.finished.emit(False, f"Uninstallation error: {str(e)}")


class UninstallerWindow(QMainWindow):
    """Main uninstaller window"""
    
    def __init__(self):
        super().__init__()
        self.project_dir = Path(__file__).parent.absolute()
        self.uninstall_thread = None
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("ReadAnything Uninstaller")
        self.setGeometry(100, 100, 600, 500)
        
        # Set window icon
        logo_path = self.project_dir / 'logo_128.png'
        if logo_path.exists():
            self.setWindowIcon(QIcon(str(logo_path)))
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Title
        title = QLabel("ReadAnything Uninstaller")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Description
        desc = QLabel("This will remove ReadAnything from your system.")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)
        
        # Options
        options_layout = QVBoxLayout()
        options_layout.setSpacing(15)
        
        # Always remove these (no checkbox)
        always_label = QLabel("Will be removed:")
        always_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        options_layout.addWidget(always_label)
        
        always_list = QLabel(
            "• Virtual environment (venv/)\n"
            + ("• Desktop shortcut" if platform.system() != 'Darwin' else "• Application bundle (.app)")
        )
        always_list.setStyleSheet("margin-left: 20px;")
        options_layout.addWidget(always_list)
        
        # Optional removals
        optional_label = QLabel("Optional removals:")
        optional_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        options_layout.addWidget(optional_label)
        
        # System dependencies checkbox (Linux only)
        self.remove_system_deps_checkbox = None
        if platform.system() != 'Darwin':
            self.remove_system_deps_checkbox = QCheckBox("Remove system dependencies (espeak, PyQt6, xclip, etc.)")
            self.remove_system_deps_checkbox.setToolTip(
                "Warning: This will remove system packages that may be used by other applications."
            )
            options_layout.addWidget(self.remove_system_deps_checkbox)
        
        # Project directory checkbox
        self.remove_project_checkbox = QCheckBox("Remove entire project directory")
        self.remove_project_checkbox.setToolTip(
            f"This will delete: {self.project_dir}\n"
            "Warning: This will permanently delete all project files."
        )
        options_layout.addWidget(self.remove_project_checkbox)
        
        layout.addLayout(options_layout)
        
        # Status/output area
        self.status_area = QTextEdit()
        self.status_area.setReadOnly(True)
        self.status_area.setMaximumHeight(150)
        layout.addWidget(self.status_area)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.uninstall_btn = QPushButton("Uninstall")
        self.uninstall_btn.setMinimumHeight(45)
        self.uninstall_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.uninstall_btn.clicked.connect(self.start_uninstall)
        button_layout.addWidget(self.uninstall_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setMinimumHeight(45)
        self.cancel_btn.clicked.connect(self.close)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        # Initial status
        self.status_area.append("Ready to uninstall. Select options and click 'Uninstall' to proceed.")
    
    def start_uninstall(self):
        """Start the uninstallation process"""
        # Confirm before proceeding
        remove_system_deps = self.remove_system_deps_checkbox.isChecked() if self.remove_system_deps_checkbox else False
        remove_project_dir = self.remove_project_checkbox.isChecked()
        
        confirm_msg = "Are you sure you want to uninstall ReadAnything?"
        if remove_system_deps:
            confirm_msg += "\n\nWarning: System dependencies will be removed."
        if remove_project_dir:
            confirm_msg += f"\n\nWarning: The entire project directory will be deleted:\n{self.project_dir}"
        
        reply = QMessageBox.question(
            self,
            "Confirm Uninstallation",
            confirm_msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Disable button during uninstallation
        self.uninstall_btn.setEnabled(False)
        self.status_area.clear()
        self.status_area.append("Starting uninstallation...")
        
        # Start uninstall thread
        self.uninstall_thread = UninstallThread(remove_system_deps, remove_project_dir)
        self.uninstall_thread.progress.connect(self.on_progress)
        self.uninstall_thread.finished.connect(self.on_finished)
        self.uninstall_thread.start()
    
    def on_progress(self, message):
        """Handle progress updates"""
        self.status_area.append(message)
    
    def on_finished(self, success, message):
        """Handle uninstallation completion"""
        self.uninstall_btn.setEnabled(True)
        self.status_area.append("\n" + message)
        
        if success:
            QMessageBox.information(
                self,
                "Uninstallation Complete",
                "ReadAnything has been successfully uninstalled.\n\n" + message
            )
            if not self.remove_project_checkbox.isChecked():
                # If project directory wasn't removed, user can close manually
                self.cancel_btn.setText("Close")
        else:
            QMessageBox.warning(
                self,
                "Uninstallation Complete",
                "Uninstallation completed with some errors.\n\n" + message
            )


def main():
    """Main entry point"""
    if not PYQT6_AVAILABLE:
        print("PyQt6 is required for the uninstaller GUI.")
        print("Please install it first: pip install PyQt6")
        print("\nAlternatively, you can manually remove:")
        print("  - venv/ directory")
        if platform.system() != 'Darwin':
            print("  - ~/.local/share/applications/readanything.desktop")
        else:
            print("  - ReadAnything.app/ directory")
        print("  - The project directory (if desired)")
        sys.exit(1)
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = UninstallerWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

