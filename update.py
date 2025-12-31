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
    from PyQt6.QtCore import Qt, QThread, pyqtSignal
    from PyQt6.QtGui import QFont, QIcon
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False


class UpdateThread(QThread):
    """Thread for running update tasks"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, update_dependencies):
        super().__init__()
        self.update_dependencies = update_dependencies
        self.project_dir = Path(__file__).parent.absolute()
        
    def run(self):
        try:
            messages = []
            
            # Check if this is a git repository
            git_dir = self.project_dir / '.git'
            if not git_dir.exists():
                self.finished.emit(False, 
                    "This directory is not a git repository.\n\n"
                    "To enable updates, clone the repository using:\n"
                    "git clone https://github.com/ZeroDayZen/readanything.git")
                return
            
            # Get current branch
            self.progress.emit("Checking current branch...")
            try:
                result = subprocess.run(
                    ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                    cwd=self.project_dir,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                current_branch = result.stdout.strip() if result.returncode == 0 else 'main'
            except:
                current_branch = 'main'
            
            # Fetch latest changes from GitHub
            self.progress.emit(f"Fetching latest changes from GitHub...")
            try:
                result = subprocess.run(
                    ['git', 'fetch', 'origin'],
                    cwd=self.project_dir,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode != 0:
                    self.finished.emit(False, f"Failed to fetch updates: {result.stderr}")
                    return
                messages.append("✓ Fetched latest changes from GitHub")
            except subprocess.TimeoutExpired:
                self.finished.emit(False, "Network timeout while fetching updates. Please check your internet connection.")
                return
            except Exception as e:
                self.finished.emit(False, f"Error fetching updates: {str(e)}")
                return
            
            # Check if there are updates available
            self.progress.emit("Checking for updates...")
            try:
                # Compare local and remote branches
                result = subprocess.run(
                    ['git', 'rev-list', '--count', f'HEAD..origin/{current_branch}'],
                    cwd=self.project_dir,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                commits_behind = int(result.stdout.strip()) if result.returncode == 0 and result.stdout.strip() else 0
            except:
                commits_behind = 0
            
            if commits_behind == 0:
                self.finished.emit(True, "You are already up to date! No updates available.")
                return
            
            messages.append(f"✓ Found {commits_behind} new commit(s) available")
            
            # Get current commit hash (before update)
            try:
                result = subprocess.run(
                    ['git', 'rev-parse', 'HEAD'],
                    cwd=self.project_dir,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                old_commit = result.stdout.strip()[:7] if result.returncode == 0 else "unknown"
            except:
                old_commit = "unknown"
            
            # Check for uncommitted changes
            self.progress.emit("Checking for uncommitted changes...")
            try:
                result = subprocess.run(
                    ['git', 'status', '--porcelain'],
                    cwd=self.project_dir,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                has_changes = bool(result.stdout.strip()) if result.returncode == 0 else False
            except:
                has_changes = False
            
            if has_changes:
                # Stash changes before pulling
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
                        self.finished.emit(False, 
                            "You have uncommitted changes that cannot be stashed.\n\n"
                            "Please commit or discard your changes before updating.")
                        return
                except Exception as e:
                    self.finished.emit(False, f"Failed to stash changes: {str(e)}")
                    return
            
            # Pull latest changes
            self.progress.emit(f"Updating to latest version...")
            try:
                result = subprocess.run(
                    ['git', 'pull', 'origin', current_branch],
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
            
            # Get new commit hash
            try:
                result = subprocess.run(
                    ['git', 'rev-parse', 'HEAD'],
                    cwd=self.project_dir,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                new_commit = result.stdout.strip()[:7] if result.returncode == 0 else "unknown"
            except:
                new_commit = "unknown"
            
            # Update dependencies if requested and requirements.txt exists
            if self.update_dependencies:
                requirements_file = self.project_dir / 'requirements.txt'
                if requirements_file.exists():
                    self.progress.emit("Updating Python dependencies...")
                    venv_path = self.project_dir / 'venv'
                    
                    if venv_path.exists():
                        # Use venv Python
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
                        # No venv, use system Python (with warning)
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
            
            # Compile success message
            success_message = "\n".join(messages)
            if old_commit != "unknown" and new_commit != "unknown":
                success_message += f"\n\nUpdated from commit {old_commit} to {new_commit}"
            
            success_message += "\n\nUpdate complete! You may need to restart the application."
            
            self.finished.emit(True, success_message)
            
        except Exception as e:
            self.finished.emit(False, f"Update error: {str(e)}")


class UpdaterWindow(QMainWindow):
    """Main updater window"""
    
    def __init__(self):
        super().__init__()
        self.project_dir = Path(__file__).parent.absolute()
        self.update_thread = None
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("ReadAnything Updater")
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
        title = QLabel("ReadAnything Updater")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Description
        desc = QLabel("Update ReadAnything to the latest version from GitHub.")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)
        
        # Options
        options_layout = QVBoxLayout()
        options_layout.setSpacing(15)
        
        # Update dependencies checkbox
        self.update_deps_checkbox = QCheckBox("Update Python dependencies")
        self.update_deps_checkbox.setChecked(True)
        self.update_deps_checkbox.setToolTip(
            "If checked, will update Python packages in requirements.txt\n"
            "Recommended if you're updating to a new version."
        )
        options_layout.addWidget(self.update_deps_checkbox)
        
        layout.addLayout(options_layout)
        
        # Status/output area
        self.status_area = QTextEdit()
        self.status_area.setReadOnly(True)
        self.status_area.setMaximumHeight(200)
        layout.addWidget(self.status_area)
        
        # Buttons
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
        
        # Initial status
        self.status_area.append("Ready to check for updates. Click 'Check for Updates' to begin.")
        
        # Show current version info
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
        except:
            pass
    
    def start_update(self):
        """Start the update process"""
        # Disable button during update
        self.update_btn.setEnabled(False)
        self.status_area.clear()
        self.status_area.append("Checking for updates...")
        
        # Start update thread
        update_deps = self.update_deps_checkbox.isChecked()
        self.update_thread = UpdateThread(update_deps)
        self.update_thread.progress.connect(self.on_progress)
        self.update_thread.finished.connect(self.on_finished)
        self.update_thread.start()
    
    def on_progress(self, message):
        """Handle progress updates"""
        self.status_area.append(message)
    
    def on_finished(self, success, message):
        """Handle update completion"""
        self.update_btn.setEnabled(True)
        self.status_area.append("\n" + message)
        
        if success:
            QMessageBox.information(
                self,
                "Update Complete",
                message
            )
            self.close_btn.setText("Close")
        else:
            QMessageBox.warning(
                self,
                "Update Failed",
                message
            )


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

