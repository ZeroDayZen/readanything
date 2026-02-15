import json
import os
import hashlib
import urllib.request
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QMessageBox,
    QProgressDialog,
)


PIPER_VOICES_MANIFEST_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/voices.json"
PIPER_VOICES_BASE_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/"


def _default_piper_voices_dir() -> Path:
    # Match the first user-writable path from main.py discover_piper_voices()
    env_path = os.environ.get("PIPER_VOICES_PATH")
    if env_path:
        return Path(env_path).expanduser()
    return Path.home() / ".local" / "share" / "piper" / "voices"


def _http_get_bytes(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "ReadAnything PiperVoiceManager/1.0",
            "Accept": "*/*",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


class _DownloadThread(QThread):
    progress = pyqtSignal(str, int, int)  # file_rel_path, downloaded, total
    finished = pyqtSignal(bool, str, list)  # success, message, installed_paths

    def __init__(self, files: list[tuple[str, str]], dest_root: Path):
        """
        files: list of (relative_path_in_repo, expected_md5_or_empty)
        dest_root: base install directory (we preserve relative path under this root)
        """
        super().__init__()
        self.files = files
        self.dest_root = dest_root
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        installed = []
        try:
            for rel_path, expected_md5 in self.files:
                if self._cancelled:
                    self.finished.emit(False, "Download cancelled.", installed)
                    return

                url = PIPER_VOICES_BASE_URL + rel_path
                dest_path = self.dest_root / rel_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)

                # Download to temp then move into place (atomic-ish)
                tmp_path = dest_path.with_suffix(dest_path.suffix + ".part")
                if tmp_path.exists():
                    try:
                        tmp_path.unlink()
                    except Exception:
                        pass

                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": "ReadAnything PiperVoiceManager/1.0",
                        "Accept": "*/*",
                    },
                    method="GET",
                )

                with urllib.request.urlopen(req, timeout=60) as resp:
                    total = int(resp.headers.get("Content-Length", "0") or "0")
                    downloaded = 0
                    md5 = hashlib.md5()
                    with open(tmp_path, "wb") as f:
                        while True:
                            if self._cancelled:
                                try:
                                    f.close()
                                except Exception:
                                    pass
                                try:
                                    tmp_path.unlink()
                                except Exception:
                                    pass
                                self.finished.emit(False, "Download cancelled.", installed)
                                return

                            chunk = resp.read(1024 * 256)
                            if not chunk:
                                break
                            f.write(chunk)
                            md5.update(chunk)
                            downloaded += len(chunk)
                            self.progress.emit(rel_path, downloaded, total)

                digest = md5.hexdigest()
                if expected_md5 and expected_md5.lower() != digest.lower():
                    try:
                        tmp_path.unlink()
                    except Exception:
                        pass
                    self.finished.emit(False, f"Checksum mismatch for {rel_path}.", installed)
                    return

                # Replace existing file if any
                if dest_path.exists():
                    try:
                        dest_path.unlink()
                    except Exception:
                        pass
                tmp_path.rename(dest_path)
                installed.append(str(dest_path))

            self.finished.emit(True, "Voice installed successfully.", installed)
        except Exception as e:
            self.finished.emit(False, f"Download failed: {e}", installed)


class PiperVoiceManagerDialog(QDialog):
    def __init__(self, parent=None, install_dir: Path | None = None):
        super().__init__(parent)
        self.setWindowTitle("Piper Voices")
        self.setMinimumSize(720, 520)

        self.install_dir = install_dir or _default_piper_voices_dir()
        self.manifest = None
        self._download_thread: _DownloadThread | None = None

        self._build_ui()
        self._load_manifest()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        header = QLabel(
            "Download offline neural voices for Piper TTS.\n"
            f"Install location: {self.install_dir}"
        )
        header.setWordWrap(True)
        layout.addWidget(header)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        top_row.addWidget(QLabel("Language:"))
        self.lang_combo = QComboBox()
        self.lang_combo.currentIndexChanged.connect(self._refresh_voice_list)
        top_row.addWidget(self.lang_combo, 1)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search voices (e.g., amy, joe, medium)…")
        self.search_box.textChanged.connect(self._refresh_voice_list)
        top_row.addWidget(self.search_box, 2)

        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._load_manifest)
        top_row.addWidget(self.refresh_btn)

        layout.addLayout(top_row)

        self.voice_list = QListWidget()
        layout.addWidget(self.voice_list, 1)

        self.status = QTextEdit()
        self.status.setReadOnly(True)
        self.status.setMaximumHeight(140)
        layout.addWidget(self.status)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)

        self.install_btn = QPushButton("Install Selected")
        self.install_btn.clicked.connect(self._install_selected)
        btn_row.addWidget(self.install_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)

    def _log(self, msg: str):
        self.status.append(msg)

    def _load_manifest(self):
        self.install_btn.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.voice_list.clear()
        self.lang_combo.clear()
        self._log("Loading voice list…")
        try:
            data = _http_get_bytes(PIPER_VOICES_MANIFEST_URL, timeout=30)
            self.manifest = json.loads(data.decode("utf-8"))

            # Build language list
            langs = {}
            for v in self.manifest.values():
                lang = v.get("language", {}) or {}
                code = lang.get("code")
                if not code:
                    continue
                if code not in langs:
                    langs[code] = f"{code} — {lang.get('name_english','')}".strip(" —")

            codes = sorted(langs.keys())
            # Prefer en_US first if available
            if "en_US" in codes:
                codes.remove("en_US")
                codes.insert(0, "en_US")

            for code in codes:
                self.lang_combo.addItem(langs[code], code)

            self._log(f"Loaded {len(self.manifest)} voice entries.")
            self._refresh_voice_list()
            self.install_btn.setEnabled(True)
        except Exception as e:
            self.manifest = None
            self._log(f"Failed to load voice list: {e}")
            QMessageBox.warning(
                self,
                "Could not load voices",
                "Failed to download the Piper voices list.\n\n"
                f"Error: {e}\n\n"
                "Check your internet connection and try again.",
            )
        finally:
            self.refresh_btn.setEnabled(True)

    def _refresh_voice_list(self):
        self.voice_list.clear()
        if not self.manifest or self.lang_combo.count() == 0:
            return

        lang_code = self.lang_combo.currentData()
        query = (self.search_box.text() or "").strip().lower()

        # Filter manifest entries by selected language code
        entries = []
        for v in self.manifest.values():
            lang = (v.get("language") or {}).get("code")
            if lang != lang_code:
                continue

            name = v.get("name", "")
            quality = v.get("quality", "")
            key = v.get("key", "")
            display = f"{name} — {quality} ({key})"

            if query and query not in display.lower():
                continue
            entries.append((display, v))

        entries.sort(key=lambda x: x[0])
        for display, v in entries:
            item = QListWidgetItem(display)
            item.setData(Qt.ItemDataRole.UserRole, v)
            self.voice_list.addItem(item)

        if self.voice_list.count() == 0:
            self._log("No voices match your filter.")

    def _install_selected(self):
        item = self.voice_list.currentItem()
        if not item:
            QMessageBox.information(self, "Select a voice", "Please select a voice to install.")
            return

        voice = item.data(Qt.ItemDataRole.UserRole) or {}
        files = voice.get("files") or {}
        if not files:
            QMessageBox.warning(self, "No files", "This voice entry does not contain downloadable files.")
            return

        # Download .onnx + .onnx.json (required for Piper)
        onnx_rel = None
        json_rel = None
        onnx_md5 = ""
        json_md5 = ""
        for rel_path, meta in files.items():
            if rel_path.endswith(".onnx"):
                onnx_rel = rel_path
                onnx_md5 = (meta or {}).get("md5_digest", "") or ""
            elif rel_path.endswith(".onnx.json"):
                json_rel = rel_path
                json_md5 = (meta or {}).get("md5_digest", "") or ""

        if not onnx_rel or not json_rel:
            QMessageBox.warning(
                self,
                "Missing files",
                "Could not find both the `.onnx` model and `.onnx.json` config for this voice.",
            )
            return

        # Confirm download size (approx)
        size_bytes = 0
        try:
            size_bytes += int((files.get(onnx_rel) or {}).get("size_bytes", 0) or 0)
            size_bytes += int((files.get(json_rel) or {}).get("size_bytes", 0) or 0)
        except Exception:
            size_bytes = 0

        pretty_size = f"{size_bytes/1024/1024:.1f} MB" if size_bytes else "unknown size"
        resp = QMessageBox.question(
            self,
            "Install voice",
            f"Download and install this voice now?\n\n"
            f"Files:\n- {onnx_rel}\n- {json_rel}\n\n"
            f"Total download: {pretty_size}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if resp != QMessageBox.StandardButton.Yes:
            return

        self.install_btn.setEnabled(False)
        self.refresh_btn.setEnabled(False)

        progress = QProgressDialog("Downloading voice…", "Cancel", 0, 100, self)
        progress.setWindowTitle("Downloading")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)

        def on_cancel():
            if self._download_thread:
                self._download_thread.cancel()

        progress.canceled.connect(on_cancel)

        self._download_thread = _DownloadThread(
            files=[(onnx_rel, onnx_md5), (json_rel, json_md5)],
            dest_root=self.install_dir,
        )

        def on_progress(rel_path: str, downloaded: int, total: int):
            if total > 0:
                pct = int((downloaded / total) * 100)
                progress.setValue(max(0, min(100, pct)))
                progress.setLabelText(f"Downloading {os.path.basename(rel_path)}… {pct}%")
            else:
                # Unknown length
                progress.setValue(0)
                progress.setLabelText(f"Downloading {os.path.basename(rel_path)}…")

        def on_finished(success: bool, msg: str, installed_paths: list):
            progress.close()
            self.install_btn.setEnabled(True)
            self.refresh_btn.setEnabled(True)
            self._log(msg)
            if success:
                self._log("Installed:\n" + "\n".join(installed_paths))
                QMessageBox.information(self, "Installed", "Voice installed. It will appear in the voice list after refresh.")
            else:
                QMessageBox.warning(self, "Install failed", msg)

        self._download_thread.progress.connect(on_progress)
        self._download_thread.finished.connect(on_finished)
        self._download_thread.start()

