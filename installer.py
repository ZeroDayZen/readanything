#!/usr/bin/env python3
"""
ReadAnything Installer - GUI installer for Kali Linux and other Linux distributions
"""

import sys
import os
import subprocess
import platform
import json
import tarfile
import tempfile
import urllib.request
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
            elif self.install_type == 'piper':
                self.install_piper()
            elif self.install_type == 'verify':
                self.verify_installation()
            elif self.install_type == 'run':
                self.run_application()
            else:
                self.finished.emit(False, "Unknown installation type")
        except Exception as e:
            self.finished.emit(False, str(e))

    def _xdg_data_home(self) -> Path:
        xdg = os.environ.get("XDG_DATA_HOME")
        if xdg:
            return Path(xdg).expanduser()
        return Path.home() / ".local" / "share"

    def _xdg_config_home(self) -> Path:
        xdg = os.environ.get("XDG_CONFIG_HOME")
        if xdg:
            return Path(xdg).expanduser()
        return Path.home() / ".config"

    def _readanything_config_path(self) -> Path:
        return self._xdg_config_home() / "readanything" / "settings.json"

    def _save_piper_path_setting(self, piper_path: Path) -> None:
        cfg_path = self._readanything_config_path()
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        try:
            if cfg_path.exists():
                data = json.loads(cfg_path.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    data = {}
        except Exception:
            data = {}
        data["piper_bin_path"] = str(piper_path)
        cfg_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _machine_arch(self) -> str:
        # Normalize common arch names for release assets
        m = (platform.machine() or "").lower()
        if m in ("x86_64", "amd64"):
            return "x86_64"
        if m in ("aarch64", "arm64"):
            return "aarch64"
        if m.startswith("armv7"):
            return "armv7"
        return m or "x86_64"

    def _github_latest_release_asset(self, owner: str, repo: str, name_contains: list[str]) -> tuple[str, str]:
        """
        Returns (asset_name, browser_download_url).
        """
        api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
        req = urllib.request.Request(
            api_url,
            headers={
                "User-Agent": "ReadAnythingInstaller/1.0",
                "Accept": "application/vnd.github+json",
            },
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        assets = data.get("assets") or []
        for a in assets:
            aname = a.get("name") or ""
            url = a.get("browser_download_url") or ""
            if not aname or not url:
                continue
            hay = aname.lower()
            if all(s.lower() in hay for s in name_contains):
                return aname, url
        raise RuntimeError(f"Could not find a matching release asset in {owner}/{repo}.")

    def _download_file(self, url: str, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "ReadAnythingInstaller/1.0", "Accept": "*/*"},
        )
        with urllib.request.urlopen(req, timeout=60) as resp, open(dest, "wb") as f:
            total = int(resp.headers.get("Content-Length", "0") or "0")
            downloaded = 0
            while True:
                chunk = resp.read(1024 * 256)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                if total > 0:
                    pct = int((downloaded / total) * 100)
                    self.progress.emit(f"Downloading Piper… {pct}%")

    def install_piper(self):
        """Download and install Piper binary to a known location (Linux)."""
        if platform.system() != "Linux":
            self.finished.emit(False, "Piper install step is currently supported on Linux only.")
            return

        arch = self._machine_arch()
        self.progress.emit(f"Detecting system architecture… ({arch})")

        # Install location (known, user-writable)
        bin_dir = self._xdg_data_home() / "readanything" / "bin"
        piper_dest = bin_dir / "piper"
        bin_dir.mkdir(parents=True, exist_ok=True)

        # Find an appropriate release asset
        # Primary: rhasspy/piper (archived but still hosts releases)
        # Fallback: OHF-Voice/piper1-gpl (community continuation)
        asset_url = None
        asset_name = None
        errors = []

        # Common asset naming: piper_linux_<arch>.tar.gz
        name_contains = ["piper", "linux", arch, ".tar.gz"]
        for owner, repo in [("rhasspy", "piper"), ("OHF-Voice", "piper1-gpl")]:
            try:
                self.progress.emit(f"Looking up latest Piper release… ({owner}/{repo})")
                asset_name, asset_url = self._github_latest_release_asset(owner, repo, name_contains=name_contains)
                break
            except Exception as e:
                errors.append(f"{owner}/{repo}: {e}")

        # If arch-specific asset wasn't found, try x86_64 as a last resort (common on Kali)
        if not asset_url and arch != "x86_64":
            for owner, repo in [("rhasspy", "piper"), ("OHF-Voice", "piper1-gpl")]:
                try:
                    self.progress.emit(f"Trying x86_64 Piper asset… ({owner}/{repo})")
                    asset_name, asset_url = self._github_latest_release_asset(
                        owner, repo, name_contains=["piper", "linux", "x86_64", ".tar.gz"]
                    )
                    break
                except Exception as e:
                    errors.append(f"{owner}/{repo} (x86_64 fallback): {e}")

        if not asset_url:
            self.finished.emit(
                False,
                "Could not find a Piper Linux release to download.\n\n"
                + "\n".join(errors[-6:])
            )
            return

        self.progress.emit(f"Downloading Piper release asset: {asset_name}")
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            tar_path = td_path / (asset_name or "piper_linux.tar.gz")
            self._download_file(asset_url, tar_path)

            self.progress.emit("Extracting Piper…")
            try:
                with tarfile.open(tar_path, "r:gz") as tf:
                    tf.extractall(path=td_path)
            except Exception as e:
                self.finished.emit(False, f"Failed to extract Piper archive: {e}")
                return

            # Find the piper executable within extracted files
            piper_found = None
            for root, _, files in os.walk(td_path):
                if "piper" in files:
                    candidate = Path(root) / "piper"
                    if candidate.is_file():
                        piper_found = candidate
                        break

            if not piper_found:
                self.finished.emit(False, "Could not locate `piper` executable inside the downloaded archive.")
                return

            # Install to destination
            try:
                if piper_dest.exists():
                    piper_dest.unlink()
            except Exception:
                pass

            try:
                piper_dest.write_bytes(piper_found.read_bytes())
                os.chmod(piper_dest, 0o755)
            except Exception as e:
                self.finished.emit(False, f"Failed to install Piper to {piper_dest}: {e}")
                return

        # Save setting so desktop shortcut launches work without PATH
        try:
            self._save_piper_path_setting(piper_dest)
        except Exception as e:
            # Piper still installed; just warn about settings
            self.finished.emit(
                True,
                f"✓ Piper installed to: {piper_dest}\n"
                f"⚠ Could not save settings.json automatically: {e}\n\n"
                "You can set Piper path in the app via Help → Piper Setup…"
            )
            return

        self.finished.emit(
            True,
            f"✓ Piper installed successfully!\n\n"
            f"Installed to: {piper_dest}\n"
            f"Configured in: {self._readanything_config_path()}\n\n"
            "Restart ReadAnything, then select a Piper voice and press Play."
        )
    
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

        # Install Piper (optional) button
        self.install_piper_btn = QPushButton("2.5 Install Piper (Optional Neural Voices)")
        self.install_piper_btn.setMinimumHeight(40)
        self.install_piper_btn.clicked.connect(lambda: self.start_installation('piper'))
        button_layout.addWidget(self.install_piper_btn)
        
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
        self.install_piper_btn.setEnabled(False)
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
        self.install_piper_btn.setEnabled(True)
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

