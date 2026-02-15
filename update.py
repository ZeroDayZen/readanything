#!/usr/bin/env python3
"""
ReadAnything Updater - Update to the latest version from GitHub
Works on Linux and macOS
"""

import sys
import os
import platform
import subprocess
import shutil
from pathlib import Path

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QTextEdit, QMessageBox, QCheckBox
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
    from PyQt6.QtGui import QFont, QIcon
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False

if PYQT6_AVAILABLE:
    def _define_gui():
        def _get_current_branch(project_dir: Path) -> str:
            try:
                result = subprocess.run(
                    ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                    cwd=project_dir,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                branch = result.stdout.strip() if result.returncode == 0 else ''
                return branch or 'main'
            except Exception:
                return 'main'

        class UpdateCheckThread(QThread):
            """Check for updates and gather patch notes (no UI calls)."""
            progress = pyqtSignal(str)
            finished = pyqtSignal(bool, str, int, str, str)  # success, message, commits_behind, patch_notes, branch

            def __init__(self):
                super().__init__()
                self.project_dir = Path(__file__).parent.absolute()

            def run(self):
                try:
                    git_dir = self.project_dir / '.git'
                    if not git_dir.exists():
                        self.finished.emit(
                            False,
                            "This directory is not a git repository.\n\n"
                            "To enable updates, clone the repository using:\n"
                            "git clone https://github.com/ZeroDayZen/readanything.git",
                            0,
                            "",
                            "main",
                        )
                        return

                    branch = _get_current_branch(self.project_dir)

                    self.progress.emit("Fetching latest changes from GitHub...")
                    try:
                        result = subprocess.run(
                            ['git', 'fetch', 'origin'],
                            cwd=self.project_dir,
                            capture_output=True,
                            text=True,
                            timeout=30
                        )
                        if result.returncode != 0:
                            self.finished.emit(False, f"Failed to fetch updates: {result.stderr}", 0, "", branch)
                            return
                    except subprocess.TimeoutExpired:
                        self.finished.emit(
                            False,
                            "Network timeout while fetching updates. Please check your internet connection.",
                            0,
                            "",
                            branch
                        )
                        return

                    self.progress.emit("Checking for updates...")
                    commits_behind = 0
                    try:
                        result = subprocess.run(
                            ['git', 'rev-list', '--count', f'HEAD..origin/{branch}'],
                            cwd=self.project_dir,
                            capture_output=True,
                            text=True,
                            timeout=10
                        )
                        commits_behind = int(result.stdout.strip()) if result.returncode == 0 and result.stdout.strip() else 0
                    except Exception:
                        commits_behind = 0

                    patch_notes = ""
                    if commits_behind > 0:
                        self.progress.emit("Building patch notes...")
                        try:
                            log_result = subprocess.run(
                                ['git', 'log', '--no-merges', '--pretty=format:%s', f'HEAD..origin/{branch}'],
                                cwd=self.project_dir,
                                capture_output=True,
                                text=True,
                                timeout=10
                            )
                            if log_result.returncode == 0 and log_result.stdout.strip():
                                entries = [line.strip() for line in log_result.stdout.splitlines() if line.strip()]
                                entries = entries[:50]
                                patch_notes = "\n".join(f"• {e}" for e in entries)
                        except Exception:
                            patch_notes = ""

                    if commits_behind == 0:
                        self.finished.emit(True, "You are already up to date! No updates available.", 0, "", branch)
                    else:
                        self.finished.emit(True, f"Found {commits_behind} update(s) available.", commits_behind, patch_notes, branch)
                except Exception as e:
                    self.finished.emit(False, f"Update check error: {str(e)}", 0, "", "main")

        class ApplyUpdateThread(QThread):
            """Apply updates (pull + optional dependency update). No UI calls."""
            progress = pyqtSignal(str)
            finished = pyqtSignal(bool, str)

            def __init__(self, branch: str, update_dependencies: bool):
                super().__init__()
                self.project_dir = Path(__file__).parent.absolute()
                self.branch = branch or 'main'
                self.update_dependencies = update_dependencies

            def run(self):
                try:
                    messages = []

                    try:
                        result = subprocess.run(
                            ['git', 'rev-parse', 'HEAD'],
                            cwd=self.project_dir,
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        old_commit = result.stdout.strip()[:7] if result.returncode == 0 else "unknown"
                    except Exception:
                        old_commit = "unknown"

                    self.progress.emit("Checking for uncommitted changes...")
                    has_changes = False
                    try:
                        result = subprocess.run(
                            ['git', 'status', '--porcelain'],
                            cwd=self.project_dir,
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        has_changes = bool(result.stdout.strip()) if result.returncode == 0 else False
                    except Exception:
                        has_changes = False

                    if has_changes:
                        self.progress.emit("Stashing local changes...")
                        try:
                            result = subprocess.run(
                                ['git', 'stash'],
                                cwd=self.project_dir,
                                capture_output=True,
                                text=True,
                                timeout=10
                            )
                            if result.returncode == 0:
                                messages.append("✓ Stashed local changes")
                            else:
                                self.finished.emit(
                                    False,
                                    "You have uncommitted changes that cannot be stashed.\n\n"
                                    "Please commit or discard your changes before updating."
                                )
                                return
                        except Exception as e:
                            self.finished.emit(False, f"Failed to stash changes: {str(e)}")
                            return

                    self.progress.emit("Installing updates (git pull)...")
                    try:
                        result = subprocess.run(
                            ['git', 'pull', 'origin', self.branch],
                            cwd=self.project_dir,
                            capture_output=True,
                            text=True,
                            timeout=60
                        )
                        if result.returncode != 0:
                            self.finished.emit(False, f"Failed to pull updates: {result.stderr}")
                            return
                        messages.append("✓ Updated to latest version")
                    except subprocess.TimeoutExpired:
                        self.finished.emit(False, "Network timeout while pulling updates. Please check your internet connection.")
                        return
                    except Exception as e:
                        self.finished.emit(False, f"Error pulling updates: {str(e)}")
                        return

                    try:
                        result = subprocess.run(
                            ['git', 'rev-parse', 'HEAD'],
                            cwd=self.project_dir,
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        new_commit = result.stdout.strip()[:7] if result.returncode == 0 else "unknown"
                    except Exception:
                        new_commit = "unknown"

                    if self.update_dependencies:
                        requirements_file = self.project_dir / 'requirements.txt'
                        if requirements_file.exists():
                            self.progress.emit("Updating Python dependencies...")
                            venv_path = self.project_dir / 'venv'

                            if venv_path.exists():
                                if platform.system() == 'Windows':
                                    pip_exe = venv_path / 'Scripts' / 'pip'
                                else:
                                    pip_exe = venv_path / 'bin' / 'pip'

                                if pip_exe.exists():
                                    try:
                                        result = subprocess.run(
                                            [str(pip_exe), 'install', '--upgrade', '-r', 'requirements.txt'],
                                            cwd=self.project_dir,
                                            capture_output=True,
                                            text=True,
                                            timeout=300
                                        )
                                        if result.returncode == 0:
                                            messages.append("✓ Updated Python dependencies")
                                        else:
                                            messages.append("⚠ Python dependency update had some issues (check manually)")
                                    except subprocess.TimeoutExpired:
                                        messages.append("⚠ Python dependency update timed out")
                                    except Exception as e:
                                        messages.append(f"⚠ Python dependency update failed: {str(e)}")
                                else:
                                    messages.append("⚠ Virtual environment found but pip not available")
                            else:
                                try:
                                    result = subprocess.run(
                                        [sys.executable, '-m', 'pip', 'install', '--upgrade', '-r', 'requirements.txt'],
                                        cwd=self.project_dir,
                                        capture_output=True,
                                        text=True,
                                        timeout=300
                                    )
                                    if result.returncode == 0:
                                        messages.append("✓ Updated Python dependencies (system-wide)")
                                    else:
                                        messages.append("⚠ Python dependency update had some issues")
                                except Exception as e:
                                    messages.append(f"⚠ Python dependency update failed: {str(e)}")

                    success_message = "\n".join(messages) if messages else "Update complete."
                    if old_commit != "unknown" and new_commit != "unknown":
                        success_message += f"\n\nUpdated from commit {old_commit} to {new_commit}"
                    success_message += "\n\nUpdate complete! You may need to restart the application."
                    self.finished.emit(True, success_message)
                except Exception as e:
                    self.finished.emit(False, f"Update error: {str(e)}")

        class UpdaterWindow(QMainWindow):
            """Main updater window"""

            def __init__(self, auto_check: bool = False):
                super().__init__()
                self.project_dir = Path(__file__).parent.absolute()
                self.check_thread = None
                self.apply_thread = None
                self._auto_check = auto_check
                self.init_ui()

            def init_ui(self):
                self.setWindowTitle("ReadAnything Updater")
                self.setGeometry(100, 100, 600, 500)

                logo_path = self.project_dir / 'logo_128.png'
                if logo_path.exists():
                    self.setWindowIcon(QIcon(str(logo_path)))

                central_widget = QWidget()
                self.setCentralWidget(central_widget)
                layout = QVBoxLayout(central_widget)
                layout.setSpacing(20)
                layout.setContentsMargins(30, 30, 30, 30)

                title = QLabel("ReadAnything Updater")
                title_font = QFont()
                title_font.setPointSize(20)
                title_font.setBold(True)
                title.setFont(title_font)
                title.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(title)

                desc = QLabel("Update ReadAnything to the latest version from GitHub.")
                desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
                layout.addWidget(desc)

                options_layout = QVBoxLayout()
                options_layout.setSpacing(15)

                self.update_deps_checkbox = QCheckBox("Update Python dependencies")
                self.update_deps_checkbox.setChecked(True)
                self.update_deps_checkbox.setToolTip(
                    "If checked, will update Python packages in requirements.txt\n"
                    "Recommended if you're updating to a new version."
                )
                options_layout.addWidget(self.update_deps_checkbox)
                layout.addLayout(options_layout)

                self.status_area = QTextEdit()
                self.status_area.setReadOnly(True)
                self.status_area.setMaximumHeight(200)
                layout.addWidget(self.status_area)

                button_layout = QHBoxLayout()
                button_layout.setSpacing(10)

                self.update_btn = QPushButton("Check for Updates")
                self.update_btn.setMinimumHeight(45)
                self.update_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #4CAF50;
                        color: white;
                        border: none;
                        border-radius: 5px;
                        font-size: 14px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #45a049;
                    }
                    QPushButton:disabled {
                        background-color: #cccccc;
                    }
                """)
                self.update_btn.clicked.connect(self.start_update)
                button_layout.addWidget(self.update_btn)

                self.close_btn = QPushButton("Close")
                self.close_btn.setMinimumHeight(45)
                self.close_btn.clicked.connect(self.close)
                button_layout.addWidget(self.close_btn)

                layout.addLayout(button_layout)

                self.status_area.append("Ready to check for updates. Click 'Check for Updates' to begin.")

                try:
                    result = subprocess.run(
                        ['git', 'rev-parse', '--short', 'HEAD'],
                        cwd=self.project_dir,
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        current_commit = result.stdout.strip()
                        self.status_area.append(f"\nCurrent version: {current_commit}")
                except Exception:
                    pass

                if self._auto_check:
                    QTimer.singleShot(0, self.start_update)

            def start_update(self):
                self.update_btn.setEnabled(False)
                self.status_area.clear()
                self.status_area.append("Checking for updates...")

                self.check_thread = UpdateCheckThread()
                self.check_thread.progress.connect(self.on_progress)
                self.check_thread.finished.connect(self.on_check_finished)
                self.check_thread.start()

            def on_progress(self, message):
                self.status_area.append(message)

            def on_check_finished(self, success: bool, message: str, commits_behind: int, patch_notes: str, branch: str):
                self.update_btn.setEnabled(True)
                self.status_area.append("\n" + message)

                if not success:
                    QMessageBox.warning(self, "Update Check Failed", message)
                    return

                if commits_behind <= 0:
                    QMessageBox.information(self, "No Updates", message)
                    return

                if patch_notes:
                    self.status_area.append("\nPatch notes:\n" + patch_notes)
                else:
                    self.status_area.append("\nPatch notes:\n(No patch notes available.)")

                prompt = QMessageBox(self)
                prompt.setWindowTitle("Update Available")
                prompt.setIcon(QMessageBox.Icon.Information)
                prompt.setText(f"An update is available ({commits_behind} commit(s)).")
                if patch_notes:
                    preview_lines = patch_notes.splitlines()[:10]
                    preview = "\n".join(preview_lines)
                    if len(patch_notes.splitlines()) > 10:
                        preview += "\n…"
                    prompt.setInformativeText("Do you want to install it now?\n\nPatch notes (preview):\n" + preview)
                    prompt.setDetailedText(patch_notes)
                else:
                    prompt.setInformativeText("Do you want to install it now?\n\nPatch notes:\n(No patch notes available.)")
                prompt.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                prompt.setDefaultButton(QMessageBox.StandardButton.Yes)
                resp = prompt.exec()

                if resp != QMessageBox.StandardButton.Yes:
                    self.status_area.append("\nUpdate cancelled.")
                    return

                self._start_apply_updates(branch)

            def _start_apply_updates(self, branch: str):
                self.update_btn.setEnabled(False)
                self.status_area.append("\nInstalling updates...")

                update_deps = self.update_deps_checkbox.isChecked()
                self.apply_thread = ApplyUpdateThread(branch=branch, update_dependencies=update_deps)
                self.apply_thread.progress.connect(self.on_progress)
                self.apply_thread.finished.connect(self.on_apply_finished)
                self.apply_thread.start()

            def on_apply_finished(self, success: bool, message: str):
                self.update_btn.setEnabled(True)
                self.status_area.append("\n" + message)

                if success:
                    QMessageBox.information(self, "Update Complete", message)
                else:
                    QMessageBox.warning(self, "Update Failed", message)

        globals()['_get_current_branch'] = _get_current_branch
        globals()['UpdateCheckThread'] = UpdateCheckThread
        globals()['ApplyUpdateThread'] = ApplyUpdateThread
        globals()['UpdaterWindow'] = UpdaterWindow

    _define_gui()


def main():
    """Main entry point"""
    if not PYQT6_AVAILABLE:
        print("PyQt6 is required for the updater GUI.")
        print("Please install it first: pip install PyQt6")
        print("\nAlternatively, you can manually update using:")
        print("  git pull origin main")
        print("  pip install -r requirements.txt --upgrade")
        sys.exit(1)
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = UpdaterWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

