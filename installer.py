#!/usr/bin/env python3
"""
ReadAnything Installer - GUI installer for Kali Linux and other Linux distributions
"""

import sys
import os
import subprocess
import platform
from pathlib import Path

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QTextEdit, QProgressBar, QMessageBox
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal
    from PyQt6.QtGui import QFont, QIcon, QPixmap
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    print("PyQt6 is required for the installer GUI.")
    print("Please install it first: pip install PyQt6")
    sys.exit(1)


class InstallThread(QThread):
    """Thread for running installation tasks"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, install_type):
        super().__init__()
        self.install_type = install_type  # 'system', 'python', 'verify', 'run'
        self.project_dir = Path(__file__).parent.absolute()
        
    def run(self):
        try:
            if self.install_type == 'system':
                self.install_system_dependencies()
            elif self.install_type == 'python':
                self.install_python_dependencies()
            elif self.install_type == 'verify':
                self.verify_installation()
            elif self.install_type == 'run':
                self.run_application()
            else:
                self.finished.emit(False, "Unknown installation type")
        except Exception as e:
            self.finished.emit(False, str(e))
    
    def install_system_dependencies(self):
        """Install system dependencies using apt-get"""
        self.progress.emit("Updating package list...")
        result = subprocess.run(
            ['sudo', 'apt-get', 'update'],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            self.finished.emit(False, f"Failed to update package list: {result.stderr}")
            return
        
        packages = [
            'espeak', 'espeak-data', 'libespeak1', 'libespeak-dev',
            'python3-pyqt6', 'python3-pyqt6.qtmultimedia',
            'xclip', 'xsel',
            'alsa-utils', 'pulseaudio'
        ]
        
        self.progress.emit(f"Installing {len(packages)} packages...")
        result = subprocess.run(
            ['sudo', 'apt-get', 'install', '-y'] + packages,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            self.finished.emit(True, "System dependencies installed successfully!")
        else:
            self.finished.emit(False, f"Installation failed: {result.stderr}")
    
    def install_python_dependencies(self):
        """Install Python dependencies"""
        venv_path = self.project_dir / 'venv'
        
        # Create virtual environment if it doesn't exist
        if not venv_path.exists():
            self.progress.emit("Creating virtual environment...")
            result = subprocess.run(
                [sys.executable, '-m', 'venv', 'venv'],
                cwd=self.project_dir,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                self.finished.emit(False, f"Failed to create venv: {result.stderr}")
                return
        
        # Determine Python executable
        if platform.system() == 'Windows':
            python_exe = venv_path / 'Scripts' / 'python.exe'
            pip_exe = venv_path / 'Scripts' / 'pip.exe'
        else:
            python_exe = venv_path / 'bin' / 'python3'
            pip_exe = venv_path / 'bin' / 'pip'
        
        # Upgrade pip
        self.progress.emit("Upgrading pip...")
        result = subprocess.run(
            [str(pip_exe), 'install', '--upgrade', 'pip'],
            cwd=self.project_dir,
            capture_output=True,
            text=True
        )
        
        # Install requirements
        self.progress.emit("Installing Python packages...")
        requirements_file = self.project_dir / 'requirements.txt'
        if requirements_file.exists():
            result = subprocess.run(
                [str(pip_exe), 'install', '-r', 'requirements.txt'],
                cwd=self.project_dir,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                self.finished.emit(True, "Python dependencies installed successfully!")
            else:
                self.finished.emit(False, f"Installation failed: {result.stderr}")
        else:
            self.finished.emit(False, "requirements.txt not found!")
    
    def verify_installation(self):
        """Verify that installation is complete"""
        checks = []
        
        # Check espeak
        self.progress.emit("Checking espeak...")
        result = subprocess.run(['which', 'espeak'], capture_output=True, text=True)
        if result.returncode == 0:
            checks.append("✓ espeak installed")
        else:
            checks.append("✗ espeak not found")
        
        # Check xclip
        self.progress.emit("Checking xclip...")
        result = subprocess.run(['which', 'xclip'], capture_output=True, text=True)
        if result.returncode == 0:
            checks.append("✓ xclip installed")
        else:
            checks.append("✗ xclip not found")
        
        # Check Python packages
        self.progress.emit("Checking Python packages...")
        venv_path = self.project_dir / 'venv'
        if venv_path.exists():
            if platform.system() == 'Windows':
                python_exe = venv_path / 'Scripts' / 'python.exe'
            else:
                python_exe = venv_path / 'bin' / 'python3'
            
            try:
                result = subprocess.run(
                    [str(python_exe), '-c', 'import PyQt6; import pyttsx3; import pynput'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    checks.append("✓ Python packages installed")
                else:
                    checks.append("✗ Python packages missing")
            except:
                checks.append("✗ Python packages check failed")
        else:
            checks.append("✗ Virtual environment not found")
        
        message = "\n".join(checks)
        all_ok = all("✓" in check for check in checks)
        
        if all_ok:
            self.finished.emit(True, f"Installation verified!\n\n{message}")
        else:
            self.finished.emit(False, f"Some components are missing:\n\n{message}")
    
    def run_application(self):
        """Run the ReadAnything application"""
        venv_path = self.project_dir / 'venv'
        main_file = self.project_dir / 'main.py'
        
        if not main_file.exists():
            self.finished.emit(False, "main.py not found!")
            return
        
        if platform.system() == 'Windows':
            python_exe = venv_path / 'Scripts' / 'python.exe'
        else:
            python_exe = venv_path / 'bin' / 'python3'
        
        # If venv exists, use it; otherwise use system Python
        if venv_path.exists():
            python_cmd = str(python_exe)
        else:
            python_cmd = sys.executable
        
        self.progress.emit("Launching ReadAnything...")
        
        # Run the application in background
        try:
            subprocess.Popen(
                [python_cmd, str(main_file)],
                cwd=self.project_dir
            )
            self.finished.emit(True, "Application launched successfully!")
        except Exception as e:
            self.finished.emit(False, f"Failed to launch: {str(e)}")


class InstallerWindow(QMainWindow):
    """Main installer window"""
    
    def __init__(self):
        super().__init__()
        self.project_dir = Path(__file__).parent.absolute()
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("ReadAnything Installer")
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
        title = QLabel("ReadAnything Installer")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Logo
        if logo_path.exists():
            logo_label = QLabel()
            pixmap = QPixmap(str(logo_path))
            logo_label.setPixmap(pixmap)
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(logo_label)
        
        # Description
        desc = QLabel(
            "Welcome to the ReadAnything installer!\n\n"
            "This installer will help you set up ReadAnything on your system.\n"
            "Follow the steps below to install dependencies and run the application."
        )
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)
        
        # Progress area
        self.progress_text = QTextEdit()
        self.progress_text.setReadOnly(True)
        self.progress_text.setMaximumHeight(150)
        self.progress_text.setPlaceholderText("Installation progress will appear here...")
        layout.addWidget(self.progress_text)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Buttons
        button_layout = QVBoxLayout()
        button_layout.setSpacing(10)
        
        # Install system dependencies button
        self.install_system_btn = QPushButton("1. Install System Dependencies")
        self.install_system_btn.setMinimumHeight(40)
        self.install_system_btn.clicked.connect(lambda: self.start_installation('system'))
        button_layout.addWidget(self.install_system_btn)
        
        # Install Python dependencies button
        self.install_python_btn = QPushButton("2. Install Python Dependencies")
        self.install_python_btn.setMinimumHeight(40)
        self.install_python_btn.clicked.connect(lambda: self.start_installation('python'))
        button_layout.addWidget(self.install_python_btn)
        
        # Verify installation button
        self.verify_btn = QPushButton("3. Verify Installation")
        self.verify_btn.setMinimumHeight(40)
        self.verify_btn.clicked.connect(lambda: self.start_installation('verify'))
        button_layout.addWidget(self.verify_btn)
        
        # Run application button
        self.run_btn = QPushButton("▶ Run ReadAnything")
        self.run_btn.setMinimumHeight(50)
        self.run_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """)
        self.run_btn.clicked.connect(lambda: self.start_installation('run'))
        button_layout.addWidget(self.run_btn)
        
        layout.addLayout(button_layout)
        
        # Status label
        self.status_label = QLabel("Ready to install")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Check if we're on Linux
        if platform.system() != 'Linux':
            self.install_system_btn.setEnabled(False)
            self.install_system_btn.setText("1. Install System Dependencies (Linux only)")
            self.status_label.setText("Note: System dependencies installation is for Linux only")
    
    def start_installation(self, install_type):
        """Start installation process"""
        # Disable buttons during installation
        self.install_system_btn.setEnabled(False)
        self.install_python_btn.setEnabled(False)
        self.verify_btn.setEnabled(False)
        self.run_btn.setEnabled(False)
        
        # Show progress bar
        self.progress_bar.setVisible(True)
        self.progress_text.clear()
        
        # Create and start thread
        self.install_thread = InstallThread(install_type)
        self.install_thread.progress.connect(self.update_progress)
        self.install_thread.finished.connect(lambda success, msg: self.installation_finished(success, msg))
        self.install_thread.start()
    
    def update_progress(self, message):
        """Update progress text"""
        self.progress_text.append(message)
        self.status_label.setText(message)
    
    def installation_finished(self, success, message):
        """Handle installation completion"""
        # Hide progress bar
        self.progress_bar.setVisible(False)
        
        # Re-enable buttons
        self.install_system_btn.setEnabled(True)
        self.install_python_btn.setEnabled(True)
        self.verify_btn.setEnabled(True)
        self.run_btn.setEnabled(True)
        
        # Show message
        if success:
            QMessageBox.information(self, "Success", message)
            self.status_label.setText("Ready")
            if "launched" in message.lower():
                # Close installer after launching app
                self.close()
        else:
            QMessageBox.warning(self, "Error", message)
            self.status_label.setText("Error occurred")


def main():
    """Main entry point"""
    if not PYQT6_AVAILABLE:
        print("PyQt6 is required for the installer.")
        print("Please install it first: pip install PyQt6")
        sys.exit(1)
    
    app = QApplication(sys.argv)
    app.setApplicationName("ReadAnything Installer")
    
    window = InstallerWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

