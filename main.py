#!/usr/bin/env python3
"""
ReadAnything - A minimalistic text-to-speech application
Supports text input, PDF, and Word documents
"""

# Application version - update this for each release
VERSION = "1.2.1"
VERSION_NAME = "1.2.1"  # Display name (can include beta, alpha, etc.)

import sys
import os
import platform
import subprocess
import shutil
import threading
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QLabel, QSlider, QComboBox,
    QMessageBox, QMenuBar, QMenu, QDialog, QFileDialog, QLineEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon, QTextCharFormat, QTextCursor, QColor, QShortcut, QKeySequence
import pyttsx3
try:
    from pynput import keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False

try:
    from readanything_settings import load_settings, save_settings
except Exception:
    load_settings = lambda: {"piper_bin_path": ""}  # type: ignore
    save_settings = lambda settings: None  # type: ignore

def find_piper_binary(configured_path: str | None = None) -> str | None:
    """
    Locate the Piper TTS executable.

    Supports:
    - `PIPER_BIN_PATH` env var override
    - common user-local paths
    - PATH lookup
    """
    # 0) Saved configuration
    if configured_path:
        try:
            p = Path(configured_path).expanduser()
            if p.exists() and os.access(str(p), os.X_OK):
                return str(p)
        except Exception:
            pass

    # 1) Explicit override
    env_path = os.environ.get("PIPER_BIN_PATH")
    if env_path:
        p = Path(env_path).expanduser()
        if p.exists() and os.access(str(p), os.X_OK):
            return str(p)

    # 2) Common locations
    candidates = [
        Path.home() / ".local" / "bin" / "piper",
        Path.home() / "bin" / "piper",
        Path.home() / ".local" / "share" / "piper" / "piper",
        Path("/usr/local/bin/piper"),
        Path("/opt/homebrew/bin/piper"),  # Homebrew Apple Silicon default
        Path("/usr/bin/piper"),
    ]
    for c in candidates:
        try:
            if c.exists() and os.access(str(c), os.X_OK):
                return str(c)
        except Exception:
            continue

    # 3) PATH
    try:
        which = shutil.which("piper")
        if which:
            return which
    except Exception:
        pass

    return None


# Piper TTS (fully offline neural TTS)
# Note: app instances may override this using saved settings.
PIPER_BINARY = find_piper_binary()
PIPER_TTS_AVAILABLE = bool(PIPER_BINARY)

# Update checker (optional - UpdaterWindow from update.py)
try:
    from update import UpdaterWindow
    UPDATER_AVAILABLE = True
except ImportError:
    try:
        from readanything.update import UpdaterWindow
        UPDATER_AVAILABLE = True
    except ImportError:
        UPDATER_AVAILABLE = False


def get_version_display() -> str:
    """
    Return a user-facing version string.
    Prefer git describe/commit when available so the UI reflects the actual build.
    """
    try:
        project_dir = Path(__file__).parent.absolute()
        result = subprocess.run(
            ['git', 'describe', '--tags', '--always', '--dirty'],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=2
        )
        git_desc = result.stdout.strip() if result.returncode == 0 else ""
        if git_desc:
            # If repo has no tags, git_desc is just a hash; don't pretend it's VERSION_NAME.
            import re
            if re.fullmatch(r"[0-9a-f]{7,}(-dirty)?", git_desc):
                return f"dev-{git_desc}"
            return git_desc
    except Exception:
        pass
    return VERSION_NAME

# Piper voice manager (optional)
try:
    from piper_voice_manager import PiperVoiceManagerDialog
    PIPER_VOICE_MANAGER_AVAILABLE = True
except Exception:
    PIPER_VOICE_MANAGER_AVAILABLE = False


class GlobalHotkeyThread(QThread):
    """Thread for listening to global hotkeys"""
    hotkey_pressed = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self._is_running = True
        self.listener = None
        
    def run(self):
        """Listen for global hotkey (Cmd+Shift+R on macOS, Ctrl+Shift+R on Linux)"""
        if not PYNPUT_AVAILABLE:
            print("pynput not available, global hotkey disabled", file=sys.stderr)
            return
        
        try:
            print("Starting global hotkey listener...", file=sys.stderr)
            # Define hotkey combination based on platform
            # On macOS: Cmd+Shift+R, On Linux/Windows: Ctrl+Shift+R
            if platform.system() == 'Darwin':
                hotkey_str = '<cmd>+<shift>+r'
                hotkey_msg = "Cmd+Shift+R"
            else:
                hotkey_str = '<ctrl>+<shift>+r'
                hotkey_msg = "Ctrl+Shift+R"
            
            hotkey = keyboard.HotKey(
                keyboard.HotKey.parse(hotkey_str),
                self._on_hotkey_pressed
            )
            
            # Create listener
            self.listener = keyboard.Listener(
                on_press=lambda k: hotkey.press(k),
                on_release=lambda k: hotkey.release(k)
            )
            self.listener.start()
            print(f"Global hotkey listener started. Press {hotkey_msg} to test.", file=sys.stderr)
            self.listener.join()
        except Exception as e:
            print(f"Error in hotkey listener: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
    
    def _on_hotkey_pressed(self):
        """Called when hotkey is pressed"""
        print("Hotkey pressed detected!", file=sys.stderr)
        if self._is_running:
            print("Emitting hotkey_pressed signal", file=sys.stderr)
            self.hotkey_pressed.emit()
        else:
            print("Hotkey thread not running, ignoring", file=sys.stderr)
    
    def stop(self):
        """Stop the hotkey listener"""
        self._is_running = False
        if self.listener:
            try:
                self.listener.stop()
            except:
                pass


class TextToSpeechThread(QThread):
    """Thread for text-to-speech to prevent GUI freezing"""
    finished = pyqtSignal()
    error = pyqtSignal(str)
    
    def __init__(self, text, engine, rate, voice_id, tts_engine_type='default', piper_binary: str | None = None):
        super().__init__()
        self.text = text
        self.engine = engine
        self.rate = rate
        self.voice_id = voice_id
        self.tts_engine_type = tts_engine_type  # 'default' or 'piper'
        self.piper_binary = piper_binary
        self._is_running = True
        self._process = None
        self._piper_process = None
        # Prevent thread from causing app to exit
        self.setTerminationEnabled(False)
    
    def _convert_rate_to_say_speed(self, rate):
        """Convert pyttsx3 rate (words per minute) to say command -r rate"""
        # pyttsx3 rate is typically 50-300, say command -r is typically 0-700
        # Map 50-300 to approximately 50-350 for say command
        if rate < 50:
            rate = 50
        elif rate > 300:
            rate = 300
        # Convert to say command rate (roughly 1:1 mapping)
        return int(rate)
    
    def _convert_rate_to_playback_speed(self, rate):
        """Convert WPM rate to audio playback speed multiplier
        Average speaking rate is ~150 WPM (1.0x speed = normal)
        Formula: speed = wpm / 150
        """
        # Clamp rate to valid range
        if rate < 50:
            rate = 50
        elif rate > 300:
            rate = 300
        
        # Convert WPM to playback speed multiplier
        # 150 WPM = 1.0x (normal speed)
        # 50 WPM = 0.33x (slow)
        # 300 WPM = 2.0x (fast)
        baseline_wpm = 150
        speed_multiplier = rate / baseline_wpm
        
        # Clamp to reasonable playback speed range (0.3x to 2.5x)
        speed_multiplier = max(0.3, min(2.5, speed_multiplier))
        
        return speed_multiplier
    
    def _clean_text_for_tts(self, text):
        """Clean text to prevent Edge TTS from reading URLs or other unwanted content
        Replaces URLs with readable text so only the user's actual content is read
        """
        import re
        
        # Pattern to match URLs more accurately
        # Matches: http://, https://, www., and domain-like patterns
        url_patterns = [
            r'https?://[^\s<>"\'{}|\\^`\[\]]+',  # http:// or https:// URLs
            r'www\.[^\s<>"\'{}|\\^`\[\]]+',      # www. URLs
            r'[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.(?:[a-zA-Z]{2,})(?:/[^\s<>"\'{}|\\^`\[\]]*)?',  # domain.com/path
        ]
        
        cleaned_text = text
        for pattern in url_patterns:
            # Replace URLs with "link" to prevent Edge TTS from reading them
            cleaned_text = re.sub(pattern, 'link', cleaned_text, flags=re.IGNORECASE)
        
        return cleaned_text
    
    def run(self):
        try:
            if not self._is_running:
                return
            
            # Set higher thread priority now that thread is running
            # This must be done in run() method, not __init__()
            try:
                self.setPriority(QThread.Priority.HighPriority)
            except Exception:
                # If priority setting fails, continue anyway
                pass
            
            # Increase CPU priority for this thread to reduce latency
            try:
                # Try to increase process priority (optional - requires psutil or os.nice)
                try:
                    import psutil
                    current_process = psutil.Process(os.getpid())
                    # Set high priority (above normal)
                    if platform.system() == 'Windows':
                        current_process.nice(psutil.HIGH_PRIORITY_CLASS)
                    elif platform.system() in ['Linux', 'Darwin']:
                        # On Linux/macOS, use nice value (lower = higher priority)
                        # Try maximum priority boost first, fallback to lower if denied
                        try:
                            os.nice(-15)  # Maximum priority boost (may require permissions)
                        except (PermissionError, OSError):
                            try:
                                os.nice(-10)  # Try medium-high priority
                            except (PermissionError, OSError):
                                try:
                                    os.nice(-5)  # Try lower priority boost
                                except (PermissionError, OSError):
                                    pass  # Continue without priority boost if denied
                except ImportError:
                    # psutil not available, try os.nice directly on Linux/macOS
                    if platform.system() in ['Linux', 'Darwin']:
                        try:
                            os.nice(-5)  # Higher priority
                        except (PermissionError, OSError):
                            pass  # Continue without priority boost if denied
            except Exception:
                # Any other error - continue without priority boost
                pass
            
            # Fully offline TTS: system or Piper TTS
            
            # Use Piper TTS if specified (fully offline neural TTS)
            if self.tts_engine_type == 'piper' and self.piper_binary:
                self._run_piper_tts()
                return
            
            # On macOS, use native 'say' command to avoid event loop conflicts
            if platform.system() == 'Darwin':
                try:
                    # Build say command
                    cmd = ['say']
                    
                    # Add voice if specified (voice_id is already the voice name from say command)
                    if self.voice_id:
                        cmd.extend(['-v', str(self.voice_id)])
                    
                    # Add rate (speed)
                    say_rate = self._convert_rate_to_say_speed(self.rate)
                    cmd.extend(['-r', str(say_rate)])
                    
                    # Add text
                    cmd.append(self.text)
                    
                    # Run say command
                    self._process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    
                    # Wait for process to complete, checking if we should stop
                    while self._process.poll() is None:
                        if not self._is_running:
                            # Stop the process
                            self._process.terminate()
                            self._process.wait(timeout=1)
                            break
                        self.msleep(100)  # Check every 100ms
                    
                    # Wait for process to finish
                    if self._process.poll() is None:
                        self._process.wait()
                    
                    # Check for errors
                    if self._process.returncode != 0 and self._process.returncode != -15:  # -15 is SIGTERM
                        stderr_output = self._process.stderr.read() if self._process.stderr else ""
                        if stderr_output:
                            raise Exception(f"say command failed: {stderr_output}")
                    
                except Exception as say_error:
                    # Fall back to pyttsx3 if say command fails
                    print(f"say command failed, falling back to pyttsx3: {say_error}", file=sys.stderr)
                    self._run_pyttsx3()
                finally:
                    self._process = None
            else:
                # Use pyttsx3 for non-macOS systems
                self._run_pyttsx3()
            
            # Only emit finished if we're still running
            if self._is_running:
                self.finished.emit()
                
        except Exception as e:
            # Emit error signal to main thread
            error_msg = str(e)
            print(f"TTS Thread Error: {error_msg}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            self.error.emit(error_msg)
        finally:
            # Always clean up the engine when thread finishes
            self._cleanup_engine()
    
    def _run_pyttsx3(self):
        """Run TTS using pyttsx3 (for non-macOS or fallback)"""
        if not self.engine:
            raise Exception("TTS engine not initialized")
        
        # Configure engine properties for better voice quality on Linux
        self.engine.setProperty('rate', self.rate)
        
        # On Linux, optimize voice settings for clearer speech
        if platform.system() != 'Darwin':
            try:
                # Set volume for clarity (if not already set)
                try:
                    current_volume = self.engine.getProperty('volume')
                    if current_volume is None or current_volume < 0.8:
                        self.engine.setProperty('volume', 0.9)
                except:
                    pass
                
                # Set pitch for more natural sound (lower = more natural)
                try:
                    self.engine.setProperty('pitch', 40)  # Lower pitch for clarity
                except:
                    pass
            except:
                pass  # Continue if property setting fails
        
        # Set the voice if specified
        # Note: Voice selection is handled in the main app's populate_voices() method
        # The voice_id passed here should already be the correct English US voice
        if self.voice_id:
            self.engine.setProperty('voice', self.voice_id)
        
        # Say the text
        self.engine.say(self.text)
        
        # Use a simpler approach: run in a separate thread with periodic checks
        # This avoids the choppy iterate() loop while allowing immediate stop
        try:
            # Use startLoop() with iterate() but check _is_running frequently
            # and use longer delays to reduce choppiness
            loop_started = False
            try:
                self.engine.startLoop(False)
                loop_started = True
            except RuntimeError as e:
                # If loop is already started, we can continue
                if 'already started' in str(e).lower():
                    loop_started = True
                else:
                    raise
            
            # Simplified iteration: check less frequently to reduce choppiness
            # Check busy state periodically instead of every 10ms
            max_checks = 1000  # Maximum number of busy checks (prevents infinite loop)
            check_count = 0
            check_interval = 50  # Check every 50ms instead of 10ms for smoother playback
            
            while self._is_running and check_count < max_checks:
                # Check if engine is busy (speech in progress)
                is_busy = True
                try:
                    if hasattr(self.engine, '_proxy') and hasattr(self.engine._proxy, 'isBusy'):
                        is_busy = self.engine._proxy.isBusy()
                    else:
                        # If we can't check busy state, use iterate() as fallback
                        try:
                            iterate_result = self.engine.iterate()
                            if iterate_result is not None:
                                # Consume the iterator
                                list(iterate_result)
                        except:
                            pass
                except:
                    pass
                
                # If not busy, speech is complete
                if not is_busy:
                    if self._is_running:
                        # Add small buffer for final word (only if not stopped)
                        self.msleep(300)
                    break
                
                # Wait before next check (longer interval reduces choppiness)
                check_count += 1
                for _ in range(check_interval // 10):
                    if not self._is_running:
                        break  # Exit immediately if stopped
                    self.msleep(10)
            
            # End the loop if we started it
            if loop_started and self.engine:
                try:
                    self.engine.endLoop()
                except:
                    pass  # Ignore errors when ending loop
            
        except Exception as e:
            # End loop on error
            if loop_started and self.engine:
                try:
                    self.engine.endLoop()
                except:
                    pass
            raise e
    
    def _cleanup_engine(self):
        """Clean up the TTS engine resources"""
        if self.engine:
            try:
                # Stop the engine first
                self.engine.stop()
            except:
                pass
            try:
                # Destroy the engine to free resources
                if hasattr(self.engine, 'destroy'):
                    self.engine.destroy()
            except:
                pass
            # Clear the reference
            self.engine = None
    
    def stop(self):
        self._is_running = False
        # Stop piper process if running (when using raw streaming)
        if self._piper_process and self._piper_process.poll() is None:
            try:
                self._piper_process.terminate()
                try:
                    self._piper_process.wait(timeout=0.05)
                except Exception:
                    try:
                        self._piper_process.kill()
                    except Exception:
                        pass
            except Exception:
                pass
        # Stop subprocess if running (immediate termination)
        if self._process and self._process.poll() is None:
            try:
                # Close stdin first (for streaming players like mpg123)
                if hasattr(self._process, 'stdin') and self._process.stdin:
                    try:
                        self._process.stdin.close()
                    except:
                        pass
                # Terminate the process
                self._process.terminate()
                # Wait briefly for termination, then kill if needed
                try:
                    self._process.wait(timeout=0.05)  # Shorter timeout
                except:
                    try:
                        self._process.kill()
                    except:
                        pass
            except:
                pass
        # Stop engine immediately - this is critical for immediate stop (for default engine only)
        if self.engine and self.tts_engine_type == 'default':
            try:
                # Stop the engine first
                self.engine.stop()
                # Also try to end the loop if it's running
                try:
                    self.engine.endLoop()
                except:
                    pass
            except:
                pass
        # Don't call _cleanup_engine here - it will be called in finally block
        # This allows the thread to exit quickly
    
    def _read_piper_sample_rate(self, model_path: str) -> int:
        """
        Piper voice configs are commonly stored as `<model>.onnx.json`.
        Default to 22050 Hz if config is missing/unparseable.
        """
        try:
            config_path = model_path + ".json"  # model.onnx.json
            if os.path.exists(config_path):
                import json as _json
                cfg = _json.loads(Path(config_path).read_text(encoding="utf-8"))
                # common shape: {"audio":{"sample_rate":22050}}
                sr = ((cfg or {}).get("audio") or {}).get("sample_rate")
                sr = int(sr) if sr else 22050
                return max(8000, min(96000, sr))
        except Exception:
            pass
        return 22050

    def _run_piper_tts_stream_raw_linux(self, model_path: str):
        """
        Lower-latency Piper path: stream raw PCM to aplay via stdout.
        Falls back to WAV generation if unavailable.
        """
        sample_rate = self._read_piper_sample_rate(model_path)

        # Piper raw output is typically 16-bit little-endian mono PCM.
        piper_cmd = [str(self.piper_binary), "--model", model_path, "--output-raw"]
        # Use aplay (alsa-utils) which is commonly installed on Linux.
        player_cmd = ["aplay", "-q", "-t", "raw", "-f", "S16_LE", "-c", "1", "-r", str(sample_rate), "-"]

        # Start Piper and pipe into player.
        # Use binary mode because stdout is raw PCM.
        self._piper_process = subprocess.Popen(
            piper_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if not self._piper_process.stdout:
            raise Exception("Failed to start Piper (no stdout).")

        self._process = subprocess.Popen(
            player_cmd,
            stdin=self._piper_process.stdout,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )

        # Send text to Piper
        try:
            if self._piper_process.stdin:
                self._piper_process.stdin.write(self.text.encode("utf-8"))
                self._piper_process.stdin.close()
        except Exception:
            pass

        # Wait for Piper to finish (player will drain)
        while self._piper_process.poll() is None:
            if not self._is_running:
                break
            self.msleep(50)

        # Collect Piper errors if any
        piper_rc = self._piper_process.poll()
        if piper_rc not in (0, None):
            try:
                stderr = self._piper_process.stderr.read().decode("utf-8", errors="ignore") if self._piper_process.stderr else ""
            except Exception:
                stderr = ""
            # If --output-raw isn't supported or aplay missing, surface a clear error for fallback.
            raise Exception(f"piper command failed: {stderr}".strip())

        # Wait for playback to finish
        if self._process:
            while self._process.poll() is None:
                if not self._is_running:
                    break
                self.msleep(50)

    def _run_piper_tts(self):
        """Run TTS using Piper TTS (fully offline neural TTS)"""
        if not self.piper_binary:
            raise Exception(
                "Piper TTS not available.\n\n"
                "Install the `piper` executable and ensure it's in your PATH, or set:\n"
                "  PIPER_BIN_PATH=/full/path/to/piper\n\n"
                "Install instructions: https://github.com/rhasspy/piper"
            )
        
        import tempfile
        
        # voice_id should be the path to the .onnx model file
        model_path = self.voice_id if self.voice_id else None
        if not model_path or not os.path.exists(model_path):
            raise Exception(f"Piper voice model not found: {model_path}")
        
        try:
            # Linux: prefer lower-latency raw streaming when possible
            if platform.system() == "Linux":
                try:
                    self._run_piper_tts_stream_raw_linux(model_path)
                    return
                except Exception as stream_err:
                    # Fallback to WAV generation if raw streaming fails for any reason
                    print(f"Piper raw streaming unavailable, falling back to WAV: {stream_err}", file=sys.stderr)

            # Create temp file for audio output
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
            temp_path = temp_file.name
            temp_file.close()
            
            # Build piper command
            # piper --model <model_path> --output_file <output>
            cmd = [str(self.piper_binary), '--model', model_path, '--output_file', temp_path]
            
            # Add text via stdin
            self._process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Send text to stdin
            self._process.stdin.write(self.text)
            self._process.stdin.close()
            
            # Wait for process to complete, checking if we should stop
            while self._process.poll() is None:
                if not self._is_running:
                    # Stop the process
                    self._process.terminate()
                    self._process.wait(timeout=1)
                    break
                self.msleep(100)  # Check every 100ms
                    
            # Wait for process to finish
            if self._process.poll() is None:
                self._process.wait()
                        
            # Check for errors
            if self._process.returncode != 0 and self._process.returncode != -15:  # -15 is SIGTERM
                stderr_output = self._process.stderr.read() if self._process.stderr else ""
                if stderr_output:
                    raise Exception(f"piper command failed: {stderr_output}")
            
            # Check if output file exists
            if not os.path.exists(temp_path):
                raise Exception("Piper TTS did not generate audio output")
            
            # Play the generated audio file
            if platform.system() == 'Darwin':
                # macOS: use afplay with speed adjustment
                playback_speed = self._convert_rate_to_playback_speed(self.rate)
                # afplay doesn't support speed directly, so we'd need ffmpeg or sox
                # For now, just play at normal speed
                self._process = subprocess.Popen(
                    ['afplay', temp_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
            elif platform.system() == 'Linux':
                # Linux: try mpv, ffplay, or paplay
                playback_speed = self._convert_rate_to_playback_speed(self.rate)
                players = [
                    ('mpv', ['--no-video', '--no-terminal', '--audio-buffer=0.1', f'--speed={playback_speed:.2f}', temp_path]),
                    ('ffplay', ['-autoexit', '-nodisp', '-i', temp_path, '-af', f'atempo={playback_speed:.2f}']),
                    ('paplay', [temp_path]),
                ]
                
                for player_name, player_args in players:
                    try:
                        self._process = subprocess.Popen(
                            [player_name] + player_args,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE
                        )
                        if self._process and self._process.poll() is None:
                            break
                        else:
                            if self._process:
                                self._process.terminate()
                            self._process = None
                    except FileNotFoundError:
                        continue
                
                if not self._process:
                    raise Exception("No audio player found. Install: mpv, ffplay, or paplay")
            else:
                # Windows: use default player
                os.startfile(temp_path)
                # Create dummy process for compatibility
                self._process = type('DummyProcess', (), {
                    'poll': lambda: None,
                    'terminate': lambda: None,
                    'wait': lambda timeout=None: None,
                })()
            
            # Wait for playback
            if self._process:
                    while self._process.poll() is None:
                        if not self._is_running:
                            self._process.terminate()
                            try:
                                self._process.wait(timeout=0.5)
                            except:
                                try:
                                    self._process.kill()
                                except:
                                    pass
                            break
                        self.msleep(100)
                    
                    if self._process.poll() is None:
                        self._process.wait()
                
        except Exception as e:
            raise
        finally:
            # Clean up temp file
            if 'temp_path' in locals() and os.path.exists(temp_path):
                    try:
                        os.unlink(temp_path)
                    except:
                        pass
            if self._process and hasattr(self._process, 'stdin') and self._process.stdin:
                try:
                        self._process.stdin.close()
                except:
                    pass
            if self._piper_process and hasattr(self._piper_process, "stdin") and self._piper_process.stdin:
                try:
                    self._piper_process.stdin.close()
                except Exception:
                    pass


def _playback_speed_from_rate(rate: int) -> float:
    """Convert WPM rate to playback speed multiplier (0.3–2.5)."""
    rate = max(50, min(300, rate))
    return max(0.3, min(2.5, rate / 150.0))


class PlayWavThread(QThread):
    """Play a pre-rendered WAV file (no TTS). Used when we have pre-rendered audio."""
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, wav_path: str, rate: int):
        super().__init__()
        self.wav_path = wav_path
        self.rate = rate
        self._process = None
        self._is_running = True
        self.setTerminationEnabled(False)

    def run(self):
        try:
            if not os.path.exists(self.wav_path):
                self.error.emit("Pre-rendered audio file not found.")
                return
            speed = _playback_speed_from_rate(self.rate)
            if platform.system() == "Darwin":
                self._process = subprocess.Popen(
                    ["afplay", self.wav_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            elif platform.system() == "Linux":
                players = [
                    ("mpv", ["--no-video", "--no-terminal", "--audio-buffer=0.1", f"--speed={speed:.2f}", self.wav_path]),
                    ("ffplay", ["-autoexit", "-nodisp", "-i", self.wav_path, "-af", f"atempo={speed:.2f}"]),
                    ("paplay", [self.wav_path]),
                ]
                for name, args in players:
                    try:
                        self._process = subprocess.Popen(
                            [name] + args,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                        )
                        if self._process and self._process.poll() is None:
                            break
                        if self._process:
                            self._process.terminate()
                        self._process = None
                    except FileNotFoundError:
                        continue
                if not self._process:
                    self.error.emit("No audio player found. Install: mpv, ffplay, or paplay")
                    return
            else:
                os.startfile(self.wav_path)
                self._process = type("_Dummy", (), {"poll": lambda: None, "terminate": lambda: None, "wait": lambda t=None: None})()

            while self._process and self._process.poll() is None and self._is_running:
                self.msleep(100)
            if self._process and self._process.poll() is None:
                self._process.terminate()
                try:
                    self._process.wait(timeout=0.5)
                except Exception:
                    pass
            if self._is_running:
                self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

    def stop(self):
        self._is_running = False
        if self._process and self._process.poll() is None:
            try:
                self._process.terminate()
                self._process.wait(timeout=0.1)
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass


class ReadAnythingApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.tts_thread = None
        self.engine = None
        self.voices = []  # Initialize to empty list to prevent AttributeError
        self.settings = load_settings()
        self.piper_binary = find_piper_binary(self.settings.get("piper_bin_path") or None)
        self.piper_available = bool(self.piper_binary)
        # Piper warm-up: track which models we've preloaded so Play starts faster
        self._piper_preloaded = set()
        self._piper_preload_lock = threading.Lock()
        # Pre-render: generate Piper audio in background so Play starts without stutter
        self._pre_render_text = None
        self._pre_render_voice_id = None
        self._pre_render_audio_path = None
        self._pre_render_lock = threading.Lock()
        self._pre_render_debounce_timer = QTimer(self)
        self._pre_render_debounce_timer.setSingleShot(True)
        self._pre_render_debounce_timer.timeout.connect(self._do_pre_render)
        # Fully offline: use system TTS only (no network calls)
        # Word highlighting
        self.highlight_timer = QTimer()
        self.highlight_timer.timeout.connect(self.highlight_next_word)
        self.word_positions = []  # List of (start_pos, end_pos) tuples
        self.current_word_index = 0
        self.original_format = QTextCharFormat()
        # Global hotkey
        self.hotkey_thread = None
        self.init_ui()
        self.setup_global_hotkey()

    def refresh_piper_state(self):
        """Reload Piper binary path and availability (after settings change)."""
        self.settings = load_settings()
        self.piper_binary = find_piper_binary(self.settings.get("piper_bin_path") or None)
        self.piper_available = bool(self.piper_binary)
        
    def init_engine(self):
        """Initialize text-to-speech engine"""
        try:
            self.engine = pyttsx3.init()
            
            # On Linux, configure espeak for better voice quality
            if platform.system() != 'Darwin':
                try:
                    # Set better default properties for clearer speech
                    # Pitch: 50 is default, higher values = higher pitch
                    # Volume: 0.0 to 1.0, 0.8-0.9 is good for clarity
                    # Word gap: milliseconds between words (50-100ms for better clarity)
                    
                    # Try to set volume for better clarity (if supported)
                    try:
                        self.engine.setProperty('volume', 0.9)  # 90% volume for clarity
                    except:
                        pass
                    
                    # Try to set pitch for more natural sound (if supported)
                    # Lower pitch (30-40) often sounds more natural than default (50)
                    try:
                        # Get current pitch if available
                        current_pitch = self.engine.getProperty('pitch')
                        if current_pitch is not None:
                            # Set to a more natural pitch (lower = more natural)
                            self.engine.setProperty('pitch', 40)
                    except:
                        pass
                    
                except Exception as e:
                    # If setting properties fails, continue anyway
                    print(f"Note: Could not set all voice properties: {e}", file=sys.stderr)
            
            voices = self.engine.getProperty('voices')
            # Ensure voices is always a list, even if getProperty returns None
            self.voices = voices if voices is not None else []
        except Exception as e:
            QMessageBox.warning(self, "Warning", 
                              f"Could not initialize TTS engine: {str(e)}")
            self.engine = None
            self.voices = []  # Initialize to empty list to prevent AttributeError
    
    def init_ui(self):
        """Initialize the user interface"""
        self.version_display = get_version_display()
        self.setWindowTitle(f"ReadAnything v{self.version_display}")
        self.setGeometry(100, 100, 800, 600)
        
        # Set window icon
        self.set_window_icon()
        
        # Create menu bar
        self.create_menu_bar()
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("ReadAnything")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Version label
        version_label = QLabel(f"Version {self.version_display}")
        version_font = QFont()
        version_font.setPointSize(10)
        version_font.setItalic(True)
        version_label.setFont(version_font)
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet("color: #666666;")
        layout.addWidget(version_label)
        
        # Text input area
        text_label = QLabel("Enter text:")
        text_label.setFont(QFont("Arial", 10))
        layout.addWidget(text_label)
        
        self.text_area = QTextEdit()
        self.text_area.setPlaceholderText("Type or paste your text here...")
        self.text_area.setFont(QFont("Arial", 12))
        self.text_area.setStyleSheet("background-color: white; color: black;")
        self.text_area.textChanged.connect(self._on_text_or_voice_changed)
        layout.addWidget(self.text_area)
        
        # Controls section
        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(10)
        
        # Voice selection
        voice_layout = QHBoxLayout()
        voice_label = QLabel("Voice:")
        voice_label.setMinimumWidth(80)
        voice_layout.addWidget(voice_label)
        
        self.voice_combo = QComboBox()
        self.populate_voices()
        self.voice_combo.currentIndexChanged.connect(self._on_voice_selection_changed)
        self.voice_combo.currentIndexChanged.connect(self._on_text_or_voice_changed)
        voice_layout.addWidget(self.voice_combo)

        # Piper voices manager (download/install models)
        self.piper_voices_btn = QPushButton("Piper Voices…")
        self.piper_voices_btn.setToolTip("Download and manage offline neural Piper voices")
        self.piper_voices_btn.clicked.connect(self.open_piper_voice_manager)
        voice_layout.addWidget(self.piper_voices_btn)
        controls_layout.addLayout(voice_layout)
        
        # Speed control
        speed_layout = QHBoxLayout()
        speed_label = QLabel("Speed:")
        speed_label.setMinimumWidth(80)
        speed_layout.addWidget(speed_label)
        
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setMinimum(50)
        self.speed_slider.setMaximum(300)
        self.speed_slider.setValue(150)
        self.speed_slider.valueChanged.connect(self.update_speed_label)
        speed_layout.addWidget(self.speed_slider)
        
        self.speed_label = QLabel("150")
        self.speed_label.setMinimumWidth(40)
        speed_layout.addWidget(self.speed_label)
        controls_layout.addLayout(speed_layout)
        
        layout.addLayout(controls_layout)
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.play_btn = QPushButton("▶ Play")
        self.play_btn.setMinimumHeight(45)
        self.play_btn.setStyleSheet("""
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
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        self.play_btn.clicked.connect(self.play_text)
        button_layout.addWidget(self.play_btn)
        
        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setMinimumHeight(45)
        self.stop_btn.setStyleSheet("""
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
            QPushButton:pressed {
                background-color: #c41104;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_text)
        button_layout.addWidget(self.stop_btn)
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setMinimumHeight(45)
        self.clear_btn.clicked.connect(self.clear_text)
        button_layout.addWidget(self.clear_btn)
        
        layout.addLayout(button_layout)
        
        # Status bar - show version on startup
        self.statusBar().showMessage(f"Ready - ReadAnything v{self.version_display}")
    
    def set_window_icon(self):
        """Set the window icon"""
        logo_path = os.path.join(os.path.dirname(__file__), 'logo_128.png')
        if os.path.exists(logo_path):
            self.setWindowIcon(QIcon(logo_path))
    
    def create_menu_bar(self):
        """Create the menu bar with About menu"""
        menubar = self.menuBar()
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        # Check for Updates action
        check_updates_action = help_menu.addAction("Check for Updates")
        check_updates_action.triggered.connect(self.show_check_for_updates)

        # Piper voices manager
        piper_voices_action = help_menu.addAction("Piper Voices…")
        piper_voices_action.triggered.connect(self.open_piper_voice_manager)

        # Piper setup (binary path)
        piper_setup_action = help_menu.addAction("Piper Setup…")
        piper_setup_action.triggered.connect(self.open_piper_setup)
        
        # About action
        about_action = help_menu.addAction("About ReadAnything")
        about_action.triggered.connect(self.show_about)
    
    def show_about(self):
        """Show About dialog with usage instructions"""
        about_text = f"""
<h2>ReadAnything</h2>
<p><b>Version {get_version_display()}</b></p>
<p>A minimalistic text-to-speech application for macOS and Linux.</p>

<h3>How to Use</h3>

<h4>Method 1: Manual Entry</h4>
<ol>
<li><b>Enter Text:</b> Type or paste text directly into the text area</li>
<li><b>Select Voice:</b> Choose a voice from the dropdown menu (US English voices only)</li>
<li><b>Adjust Speed:</b> Use the slider to control speech speed (50-300 words per minute)</li>
<li><b>Play:</b> Click the "▶ Play" button to start reading</li>
<li><b>Stop:</b> Click the "⏹ Stop" button to stop reading at any time</li>
<li><b>Clear:</b> Click "Clear" to clear the text area</li>
</ol>

<h4>Method 2: Global Hotkey</h4>
<ol>
<li><b>Select Text:</b> Highlight any text in any application (browser, document, etc.)</li>
<li><b>Press Hotkey:</b> Press <b>Cmd+Shift+R</b> (macOS) or <b>Ctrl+Shift+R</b> (Linux) to instantly read the selected text</li>
<li>The app will automatically:
   <ul>
   <li>Copy the selected text</li>
   <li>Load it into the text area</li>
   <li>Start reading immediately</li>
   <li>Bring the app window to the front</li>
   </ul>
</li>
</ol>

<h4>Features</h4>
<ul>
<li>✨ <b>Word Highlighting:</b> See each word highlighted in yellow as it's being spoken</li>
<li>🎤 <b>Natural Voices:</b> Uses high-quality, human-like voices</li>
<li>⌨️ <b>Global Hotkey:</b> Read text from any application instantly</li>
<li>🎚️ <b>Customizable:</b> Adjustable speech speed and voice selection</li>
</ul>

<h4>Global Hotkey Setup</h4>
<p><b>macOS:</b> If the global hotkey (Cmd+Shift+R) doesn't work:</p>
<ol>
<li>Open <b>System Settings</b> (or <b>System Preferences</b>)</li>
<li>Go to <b>Privacy & Security</b> > <b>Accessibility</b></li>
<li>Enable <b>Terminal</b> (if running from terminal) or <b>Python</b> (if running directly)</li>
<li>If using the .app bundle, enable <b>ReadAnything</b></li>
<li>Restart the application after granting permissions</li>
</ol>
<p><b>Linux:</b> For the hotkey (Ctrl+Shift+R) to work, install clipboard utilities:</p>
<ol>
<li>Install <b>xclip</b> or <b>xsel</b>: <code>sudo apt-get install xclip xsel</code></li>
<li>The hotkey will use your system's primary selection or clipboard</li>
</ol>

<h4>Adding More Voices (macOS)</h4>
<ol>
<li>Open <b>System Settings</b> > <b>Accessibility</b> > <b>Spoken Content</b></li>
<li>Click the <b>System Voice</b> dropdown</li>
<li>Select <b>Customize...</b></li>
<li>Download additional voices (Enhanced/Neural voices recommended)</li>
<li>Restart the application - new voices will appear automatically</li>
</ol>

<p><b>Note:</b> As text is being read, each word will be highlighted in yellow to show which word is currently being spoken.</p>

<p style="margin-top: 20px;"><i>ReadAnything - Making text accessible through speech</i></p>
"""
        
        msg = QMessageBox(self)
        msg.setWindowTitle("About ReadAnything")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(about_text)
        ok_btn = msg.addButton(QMessageBox.StandardButton.Ok)
        check_updates_btn = msg.addButton("Check for Updates", QMessageBox.ButtonRole.ActionRole)
        msg.setDefaultButton(ok_btn)
        msg.exec()

        if msg.clickedButton() == check_updates_btn:
            self.show_check_for_updates(auto_check=True)
    
    def show_check_for_updates(self, auto_check: bool = False):
        """Show the Check for Updates dialog"""
        if UPDATER_AVAILABLE:
            try:
                self.updater_window = UpdaterWindow(auto_check=auto_check)
            except TypeError:
                # Backwards compatibility if updater doesn't accept auto_check
                self.updater_window = UpdaterWindow()
            self.updater_window.show()
        else:
            QMessageBox.information(
                self,
                "Check for Updates",
                "The updater is not available.\n\n"
                "To update manually, run from the project directory:\n"
                "  python update.py\n\n"
                "Or use git:\n"
                "  git pull origin main"
            )

    def open_piper_voice_manager(self):
        """Open the Piper voice download/manager dialog."""
        if not PIPER_VOICE_MANAGER_AVAILABLE:
            QMessageBox.information(
                self,
                "Piper Voices",
                "Piper voice manager is not available.\n\n"
                "Make sure `piper_voice_manager.py` is present and PyQt6 is installed.\n\n"
                "You can still install voices manually by downloading a Piper voice model (.onnx) and config (.onnx.json)\n"
                "into: ~/.local/share/piper/voices"
            )
            return

        dlg = PiperVoiceManagerDialog(self)
        dlg.exec()
        # Refresh list in case the user installed new voices
        try:
            self.populate_voices()
        except Exception:
            pass

    def open_piper_setup(self):
        """Configure Piper binary path for desktop shortcut launches."""
        dlg = QDialog(self)
        dlg.setWindowTitle("Piper Setup")
        dlg.setMinimumWidth(520)

        layout = QVBoxLayout(dlg)
        layout.setSpacing(10)

        info = QLabel(
            "ReadAnything needs the `piper` executable to use Piper voices.\n"
            "Desktop shortcuts often don't inherit your shell PATH, so you can set the full path here."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        row = QHBoxLayout()
        row.addWidget(QLabel("Piper binary path:"))
        path_edit = QLineEdit()
        path_edit.setPlaceholderText("/full/path/to/piper")
        path_edit.setText(self.settings.get("piper_bin_path") or "")
        row.addWidget(path_edit, 1)

        browse_btn = QPushButton("Browse…")
        row.addWidget(browse_btn)
        layout.addLayout(row)

        status = QLabel("")
        status.setWordWrap(True)
        layout.addWidget(status)

        def update_status():
            candidate = path_edit.text().strip()
            found = find_piper_binary(candidate or None)
            if found:
                status.setText(f"Detected: {found}")
            else:
                status.setText("Not found. Install Piper or choose the correct executable.")

        def browse():
            fname, _ = QFileDialog.getOpenFileName(dlg, "Select Piper executable")
            if fname:
                path_edit.setText(fname)
                update_status()

        browse_btn.clicked.connect(browse)
        path_edit.textChanged.connect(lambda _: update_status())
        update_status()

        btns = QHBoxLayout()
        btns.addStretch(1)
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        btns.addWidget(save_btn)
        btns.addWidget(cancel_btn)
        layout.addLayout(btns)

        def on_save():
            self.settings["piper_bin_path"] = path_edit.text().strip()
            save_settings(self.settings)
            self.refresh_piper_state()
            try:
                self.populate_voices()
            except Exception:
                pass
            dlg.accept()

        save_btn.clicked.connect(on_save)
        cancel_btn.clicked.connect(dlg.reject)

        dlg.exec()
    
    def _on_voice_selection_changed(self):
        """When user selects a voice, warm up Piper if it's a Piper voice."""
        voice_id = self.voice_combo.currentData()
        if not voice_id or not isinstance(voice_id, str) or not voice_id.endswith(".onnx"):
            return
        if not os.path.exists(voice_id):
            return
        self._piper_preload_async(voice_id)

    def _piper_preload_async(self, model_path: str):
        """
        Preload a Piper model in the background so the next Play has less delay.
        Runs piper once with minimal input so the OS caches the model and libs.
        """
        if not self.piper_available or not self.piper_binary:
            return
        with self._piper_preload_lock:
            if model_path in self._piper_preloaded:
                return
            self._piper_preloaded.add(model_path)

        def run():
            try:
                subprocess.run(
                    [str(self.piper_binary), "--model", model_path, "--output-raw"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    input=b" ",
                    timeout=45,
                )
            except Exception:
                with self._piper_preload_lock:
                    self._piper_preloaded.discard(model_path)

        t = threading.Thread(target=run, daemon=True)
        t.start()

    PRE_RENDER_DEBOUNCE_MS = 700
    PRE_RENDER_MAX_CHARS = 30_000

    def _on_text_or_voice_changed(self):
        """Invalidate pre-render and restart debounce so we pre-render after user stops typing."""
        with self._pre_render_lock:
            old_path = self._pre_render_audio_path
            self._pre_render_text = None
            self._pre_render_voice_id = None
            self._pre_render_audio_path = None
        if old_path and os.path.exists(old_path):
            try:
                os.unlink(old_path)
            except Exception:
                pass
        self._pre_render_debounce_timer.stop()
        self._pre_render_debounce_timer.start(self.PRE_RENDER_DEBOUNCE_MS)

    def _do_pre_render(self):
        """Start background pre-render of current text with current Piper voice (if any)."""
        text = self.text_area.toPlainText().strip()
        voice_id = self.voice_combo.currentData()
        if not text or len(text) > self.PRE_RENDER_MAX_CHARS or not voice_id or not isinstance(voice_id, str) or not voice_id.endswith(".onnx") or not os.path.exists(voice_id):
            return
        if not self.piper_available or not self.piper_binary:
            return
        # Run Piper in a background thread and set result on main thread when done
        piper_binary = str(self.piper_binary)
        model_path = voice_id

        def worker():
            import tempfile
            tmp = None
            try:
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                temp_path = tmp.name
                tmp.close()
                proc = subprocess.run(
                    [piper_binary, "--model", model_path, "--output_file", temp_path],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    timeout=120,
                    input=text.encode("utf-8"),
                )
                if proc.returncode == 0 and os.path.exists(temp_path):
                    QTimer.singleShot(0, lambda: self._on_pre_render_done(True, temp_path, text, voice_id))
                else:
                    if os.path.exists(temp_path):
                        try:
                            os.unlink(temp_path)
                        except Exception:
                            pass
                    QTimer.singleShot(0, lambda: self._on_pre_render_done(False, None, text, voice_id))
            except Exception:
                if tmp and os.path.exists(tmp.name):
                    try:
                        os.unlink(tmp.name)
                    except Exception:
                        pass
                QTimer.singleShot(0, lambda: self._on_pre_render_done(False, None, text, voice_id))

        threading.Thread(target=worker, daemon=True).start()

    def _on_pre_render_done(self, success: bool, path: str | None, text: str, voice_id):
        """Called on main thread when pre-render worker finishes."""
        # Only apply if text/voice haven't changed since we started (avoid stale pre-render)
        current_text = self.text_area.toPlainText().strip()
        current_voice = self.voice_combo.currentData()
        if success and path and current_text == text and current_voice == voice_id:
            with self._pre_render_lock:
                old_path = self._pre_render_audio_path
                self._pre_render_text = text
                self._pre_render_voice_id = voice_id
                self._pre_render_audio_path = path
            if old_path and old_path != path and os.path.exists(old_path):
                try:
                    os.unlink(old_path)
                except Exception:
                    pass
            self.statusBar().showMessage("Ready to play", 2000)
        else:
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except Exception:
                    pass

    def get_default_system_voice(self):
        """Get the default system voice name"""
        try:
            # Try to get default voice from system preferences
            result = subprocess.run(
                ['defaults', 'read', 'com.apple.speech.voice.prefs', 'SelectedVoiceName'],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().strip('"')
        except:
            pass
        
        # Fallback: try to get from say command without specifying voice
        # The default is usually Alex on macOS
        try:
            # Check if Alex is available (common default)
            result = subprocess.run(
                ['say', '-v', 'Alex', '-v', '?'],
                capture_output=True,
                text=True,
                timeout=2
            )
            if 'Alex' in result.stdout:
                return 'Alex'
        except:
            pass
        
        return None
    
    def discover_piper_voices(self):
        """Discover available Piper TTS voice models."""
        piper_voices = []
        
        # Common Piper voice model locations
        possible_paths = [
            Path.home() / '.local' / 'share' / 'piper' / 'voices',
            Path.home() / '.piper' / 'voices',
            Path.home() / 'piper' / 'voices',
            Path('/usr/local/share/piper/voices'),
            Path('/usr/share/piper/voices'),
        ]
        
        # Also check if PIPER_VOICES_PATH env var is set
        env_path = os.environ.get('PIPER_VOICES_PATH')
        if env_path:
            possible_paths.insert(0, Path(env_path))
        
        for voices_dir in possible_paths:
            if not voices_dir.exists():
                continue
            
            # Look for .onnx files (Piper model files)
            for model_file in voices_dir.rglob('*.onnx'):
                # Get voice name from directory structure or filename
                # Piper models are often in: language/voice/voice.onnx
                parts = model_file.parts
                # Common structure is: <family>/<locale>/<voice>/<quality>/<file>.onnx
                # Example: en/en_US/amy/medium/en_US-amy-medium.onnx
                voice_name = model_file.stem
                quality = ""
                try:
                    if len(parts) >= 4:
                        quality = parts[-2]
                        voice_dir = parts[-3]
                        # Prefer directory names over stem
                        if voice_dir and quality:
                            voice_name = voice_dir
                except Exception:
                    pass

                display_name = f"Piper: {voice_name}" + (f" ({quality})" if quality else "")
                piper_voices.append((display_name, str(model_file)))
        
        return piper_voices
    
    def populate_voices(self):
        """Populate voice selection dropdown with system/offline voices and Piper TTS voices."""
        # Ensure pyttsx3 is initialized for non-macOS so populate_voices_old can use self.engine/self.voices
        if platform.system() != 'Darwin' and self.engine is None:
            self.init_engine()
        
        # Store current selection
        current_selection = self.voice_combo.currentIndex() if self.voice_combo.count() > 0 else -1
        
        # Populate system voices first
        self.populate_voices_old()
        
        # Add Piper voices if models are installed (listing does not require piper binary)
        piper_voices = self.discover_piper_voices()
        if piper_voices:
            try:
                self.voice_combo.insertSeparator(self.voice_combo.count())
            except Exception:
                pass
            for display_name, model_path in piper_voices:
                # If piper binary is missing, still list voices, but make it obvious
                if not self.piper_available:
                    display_name = f"{display_name} (install piper binary to use)"
                self.voice_combo.addItem(display_name, model_path)
        # After list is built, warm up Piper for current selection if it's a Piper voice
        QTimer.singleShot(0, self._on_voice_selection_changed)
    
    def populate_voices_old(self):
        """Old populate_voices method - kept for reference but not used"""
        self.voice_combo.clear()
        
        # On macOS, get voices from 'say' command
        if platform.system() == 'Darwin':
            default_voice = None
            try:
                # Get default system voice
                default_voice = self.get_default_system_voice()
            except:
                pass  # Continue even if we can't get default voice
            
            try:
                result = subprocess.run(
                    ['say', '-v', '?'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    # Known natural-sounding voices (default system voices)
                    # These are the voices that come with macOS by default
                    default_system_voices = {
                        'Alex',      # Default natural male voice (most common)
                        'Samantha',  # Natural female voice
                        'Victoria',  # Natural female voice
                        'Fred',      # Natural male voice
                        'Kathy',     # Natural female voice
                        'Ralph',     # Natural male voice
                        'Tessa',     # Natural female voice
                        'Princess',  # Natural female voice
                        # Enhanced/Premium voices (if downloaded):
                        'Ava',       # Enhanced female voice
                        'Nicky',     # Enhanced male voice
                        'Siri',      # Siri voice (if available)
                        'Daniel',    # Enhanced male voice
                        'Karen',     # Enhanced female voice
                        'Moira',     # Enhanced female voice
                        'Veena',     # Enhanced female voice
                    }
                    
                    # Blacklist of clearly robotic/novelty voices
                    robotic_voices = {
                        'Albert', 'Bad', 'Bad News', 'Bahh', 'Bells', 'Boing', 'Bubbles', 
                        'Cellos', 'Wobble', 'Hysterical', 'Trinoids', 'Zarvox', 
                        'Junior', 'Good', 'Good News', 'Jester', 'Organ', 'Superstar', 'Whisper',
                        'Eddy', 'Flo', 'Reed', 'Rocko', 'Sandy', 'Shelley', 
                        'Grandma', 'Grandpa'  # Character voices, less natural
                    }
                    
                    # Parse say command output (format: "VoiceName    Language    # Description")
                    lines = result.stdout.strip().split('\n')
                    seen_voices = set()  # Avoid duplicates
                    voice_items = []  # Store (display_name, voice_name, is_default) tuples
                    
                    for line in lines:
                        if line.strip() and '#' in line:
                            # Extract voice name and language
                            # Format: "VoiceName    Language    # Description" or "VoiceName (Description) Language    # Description"
                            parts = line.split()
                            if len(parts) >= 2:
                                voice_name = parts[0]
                                
                                # Find the language code (it's usually the second part, but could be later if voice name has spaces)
                                language = None
                                for i, part in enumerate(parts):
                                    if part in ['en_US', 'en_GB', 'en_AU', 'en_CA']:
                                        language = part
                                        # If we found language later, voice name might include previous parts
                                        if i > 1:
                                            # Voice name might be multi-word (e.g., "Bad News")
                                            voice_name = ' '.join(parts[:i])
                                        break
                                
                                # Fallback: if no language code found, use second part
                                if not language and len(parts) >= 2:
                                    language = parts[1]
                                
                                if not language or language != 'en_US':
                                    continue
                                
                                # Only include US English voices (en_US)
                                # Include voices from default list OR any voice not in blacklist
                                # (This allows newly downloaded voices to appear automatically)
                                is_default_voice = voice_name in default_system_voices
                                is_not_robotic = voice_name not in robotic_voices
                                # Also check if voice name looks natural (starts with capital, no numbers, reasonable length)
                                looks_natural = (voice_name and 
                                                len(voice_name) > 1 and
                                                voice_name[0].isupper() and
                                                not any(char.isdigit() for char in voice_name) and
                                                voice_name.replace(' ', '').isalpha())
                                
                                if (voice_name not in seen_voices and
                                    is_not_robotic and
                                    (is_default_voice or looks_natural)):
                                    seen_voices.add(voice_name)
                                    # Get display name (just the voice name, language is implied)
                                    display_name = voice_name
                                    
                                    # Mark if this is the system default
                                    is_system_default = (voice_name == default_voice)
                                    if is_system_default:
                                        display_name = f"{display_name} (System Default)"
                                    
                                    voice_items.append((display_name, voice_name, is_system_default, is_default_voice))
                    
                    # Sort voices: system default first, then default voices, then others
                    voice_items.sort(key=lambda x: (not x[2], not x[3], x[0]))
                    
                    # Add voices to combo box
                    for display_name, voice_name, _, _ in voice_items:
                        try:
                            self.voice_combo.addItem(display_name, voice_name)
                        except Exception as e:
                            # If adding fails, try with just the voice name
                            try:
                                self.voice_combo.addItem(voice_name, voice_name)
                            except:
                                pass  # Skip this voice if it still fails
                    
                    # Set first voice (best English US voice) as default
                    if self.voice_combo.count() > 0:
                        self.voice_combo.setCurrentIndex(0)
                    
                    # If no voices found, try a simpler fallback approach
                    if self.voice_combo.count() == 0:
                        # Fallback: try to add common US English voices directly
                        fallback_voices = ['Alex', 'Samantha', 'Victoria', 'Fred', 'Kathy', 'Ralph']
                        for voice in fallback_voices:
                            try:
                                # Test if voice exists and is en_US by checking say command
                                test_result = subprocess.run(
                                    ['say', '-v', voice, '-v', '?'],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    timeout=1
                                )
                                # Check if voice exists and is en_US
                                if test_result.returncode == 0 and 'en_US' in test_result.stdout:
                                    self.voice_combo.addItem(voice, voice)
                                    if self.voice_combo.count() >= 3:  # Stop after finding a few
                                        break
                            except:
                                continue
                        
                        # Set first voice as default if any were added
                        if self.voice_combo.count() > 0:
                            self.voice_combo.setCurrentIndex(0)
                        
                        # If still no voices, add default
                        if self.voice_combo.count() == 0:
                            self.voice_combo.addItem("Default", None)
                else:
                    # If say command failed, try fallback with en_US check
                    fallback_voices = ['Alex', 'Samantha', 'Victoria', 'Fred', 'Kathy', 'Ralph']
                    for voice in fallback_voices:
                        try:
                            # Check if voice is en_US
                            test_result = subprocess.run(
                                ['say', '-v', voice, '-v', '?'],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                timeout=1
                            )
                            if test_result.returncode == 0 and 'en_US' in test_result.stdout:
                                self.voice_combo.addItem(voice, voice)
                        except:
                            continue
                    
                    # Set first voice as default if any were added
                    if self.voice_combo.count() > 0:
                        self.voice_combo.setCurrentIndex(0)
                    
                    if self.voice_combo.count() == 0:
                        self.voice_combo.addItem("Default", None)
            except Exception as e:
                # On any error, try to add at least some common US English voices
                fallback_voices = ['Alex', 'Samantha', 'Victoria', 'Fred', 'Kathy', 'Ralph']
                for voice in fallback_voices:
                    try:
                        # Verify it's en_US before adding
                        test_result = subprocess.run(
                            ['say', '-v', voice, '-v', '?'],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            timeout=1
                        )
                        if test_result.returncode == 0 and 'en_US' in test_result.stdout:
                            self.voice_combo.addItem(voice, voice)
                    except:
                        continue
                
                # Set first voice as default if any were added
                if self.voice_combo.count() > 0:
                    self.voice_combo.setCurrentIndex(0)
                
                if self.voice_combo.count() == 0:
                    self.voice_combo.addItem("Default", None)
        else:
            # Use pyttsx3 voices for non-macOS (Linux)
            # Filter to only English US voices
            if self.engine and self.voices:
                try:
                    # Ensure voices is iterable (not None)
                    if self.voices is not None:
                        # Sort voices to prioritize better quality ones
                        # mbrola and festival voices are generally better quality
                        voice_items = []
                        for voice in self.voices:
                            try:
                                name = voice.name if hasattr(voice, 'name') else str(voice)
                                voice_id = voice.id if hasattr(voice, 'id') else None
                                
                                if not name or not voice_id:
                                    continue
                                
                                # Filter: Only include English voices
                                # Check language property if available
                                is_english = False
                                name_lower = name.lower()
                                id_lower = str(voice_id).lower()
                                
                                # Check if voice has language property
                                if hasattr(voice, 'languages') and voice.languages:
                                    # Check if any language is English
                                    for lang in voice.languages:
                                        if isinstance(lang, str):
                                            lang_lower = lang.lower()
                                            # Accept en, en-us, en_us, english, etc.
                                            if lang_lower.startswith('en') or 'english' in lang_lower:
                                                # Prefer US English (en-us, en_us, en-us)
                                                if 'us' in lang_lower or lang_lower == 'en' or lang_lower.startswith('en-'):
                                                    is_english = True
                                                    break
                                else:
                                    # If no language property, check name/ID for English indicators
                                    english_indicators = ['en', 'english', 'us', 'american']
                                    if any(indicator in name_lower or indicator in id_lower for indicator in english_indicators):
                                        is_english = True
                                
                                # Skip non-English voices
                                if not is_english:
                                    continue
                                
                                # Score voices: higher score = better quality
                                score = 0
                                
                                # Prefer mbrola voices (best quality)
                                if 'mb' in name_lower or 'mbrola' in name_lower or 'mb' in id_lower:
                                    score += 100
                                # Prefer festival voices (good quality)
                                elif 'f' in name_lower or 'festival' in name_lower or 'f' in id_lower:
                                    score += 50
                                
                                # Prefer US English specifically
                                if 'us' in name_lower or 'us' in id_lower or 'american' in name_lower:
                                    score += 30
                                # Prefer English voices (already checked above)
                                elif 'en' in name_lower or 'english' in name_lower or 'en' in id_lower:
                                    score += 25
                                
                                # Prefer female voices (often clearer)
                                if any(female in name_lower for female in ['female', 'f', 'woman']):
                                    score += 10
                                
                                voice_items.append((score, name, voice_id))
                            except Exception as e:
                                print(f"Error processing voice: {e}", file=sys.stderr)
                                continue
                        
                        # Sort by score (highest first), then by name
                        voice_items.sort(key=lambda x: (-x[0], x[1]))
                        
                        # Add voices to combo box
                        for score, name, voice_id in voice_items:
                            try:
                                self.voice_combo.addItem(name, voice_id)
                            except Exception as e:
                                print(f"Error adding voice: {e}", file=sys.stderr)
                                continue
                        
                        # Set first voice (best English US voice) as default
                        if self.voice_combo.count() > 0:
                            self.voice_combo.setCurrentIndex(0)
                        
                        # If no voices were added, add default
                        if self.voice_combo.count() == 0:
                            self.voice_combo.addItem("Default", None)
                    else:
                        self.voice_combo.addItem("Default", None)
                except Exception as e:
                    print(f"Error populating voices: {e}", file=sys.stderr)
                    self.voice_combo.addItem("Default", None)
            else:
                self.voice_combo.addItem("Default", None)
    
    def update_speed_label(self, value):
        """Update speed label when slider changes"""
        self.speed_label.setText(str(value))
    
    def play_text(self):
        """Play the text using offline system text-to-speech only"""
        try:
            text = self.text_area.toPlainText().strip()
            if not text:
                QMessageBox.warning(self, "Warning", "Please enter some text")
                return
            
            # Stop any currently playing speech
            if self.tts_thread and self.tts_thread.isRunning():
                self.stop_text()
            
            # Get selected voice and speed
            voice_id = self.voice_combo.currentData()
            speed = self.speed_slider.value()
            
            # Detect if Piper voice is selected (voice_id is a path to .onnx file)
            is_piper_voice = voice_id and isinstance(voice_id, str) and voice_id.endswith('.onnx') and os.path.exists(voice_id)

            # Use pre-rendered audio if we have a match (no stutter on start)
            with self._pre_render_lock:
                path = self._pre_render_audio_path
                pr_text = self._pre_render_text
                pr_voice = self._pre_render_voice_id
            if is_piper_voice and path and os.path.exists(path) and pr_text == text and pr_voice == voice_id:
                self.tts_thread = PlayWavThread(path, speed)
                self.tts_thread.finished.connect(self.on_speech_finished)
                self.tts_thread.error.connect(self.on_speech_error)
                self.tts_thread.start()
                self.start_highlighting(text, speed)
                self.play_btn.setEnabled(False)
                self.statusBar().showMessage("Playing...")
                return
            
            if is_piper_voice:
                # Use Piper TTS (fully offline neural TTS)
                if not self.piper_available:
                    msg = QMessageBox(self)
                    msg.setIcon(QMessageBox.Icon.Warning)
                    msg.setWindowTitle("Piper TTS Not Available")
                    msg.setText("Piper voices are installed, but the `piper` executable was not found.")
                    msg.setInformativeText(
                        "Click “Piper Setup…” to select the Piper binary path.\n\n"
                        "Alternatively, install Piper and ensure `piper` is on your PATH."
                    )
                    setup_btn = msg.addButton("Piper Setup…", QMessageBox.ButtonRole.ActionRole)
                    msg.addButton(QMessageBox.StandardButton.Ok)
                    msg.exec()
                    if msg.clickedButton() == setup_btn:
                        self.open_piper_setup()
                    return
                tts_engine_type = 'piper'
                engine = None  # Not used for Piper TTS
            else:
                # System/offline path - no network calls
                if platform.system() != 'Darwin' and self.engine is None:
                    self.init_engine()
                if platform.system() != 'Darwin' and not self.engine:
                    QMessageBox.warning(self, "System TTS Unavailable", "Could not initialize system TTS engine.")
                    return
                engine = self.engine
                tts_engine_type = 'default'
            
            # Create and start thread
            try:
                self.tts_thread = TextToSpeechThread(
                    text, engine, speed, voice_id, tts_engine_type,
                    piper_binary=self.piper_binary
                )
                
                # Connect signals BEFORE starting thread
                self.tts_thread.finished.connect(self.on_speech_finished)
                self.tts_thread.error.connect(self.on_speech_error)
                
                # Start the thread - this should not cause the app to exit
                self.tts_thread.start()
                
                # Start word highlighting
                self.start_highlighting(text, speed)
                
                # Update UI
                self.play_btn.setEnabled(False)
                self.statusBar().showMessage("Playing...")
                
            except SystemExit as e:
                # Prevent SystemExit from closing the app
                print(f"ERROR: Prevented SystemExit in thread creation: {e.code}", file=sys.stderr)
                import traceback
                traceback.print_exc()
                self.play_btn.setEnabled(True)
                self.statusBar().showMessage("Error: Thread creation failed")
                # Clean up engine if thread creation failed
                if engine:
                    try:
                        engine.stop()
                        if hasattr(engine, 'destroy'):
                            engine.destroy()
                    except:
                        pass
                    engine = None
            except Exception as thread_error:
                # Re-enable play button on error
                self.play_btn.setEnabled(True)
                self.statusBar().showMessage("Error starting speech thread")
                error_msg = str(thread_error)
                print(f"Error starting TTS thread: {error_msg}", file=sys.stderr)
                import traceback
                traceback.print_exc()
                # Clean up engine if thread creation failed
                if engine:
                    try:
                        engine.stop()
                        if hasattr(engine, 'destroy'):
                            engine.destroy()
                    except:
                        pass
                    engine = None
                try:
                    QMessageBox.critical(self, "Error", f"Failed to start speech: {error_msg}")
                except:
                    print(f"Could not show error dialog: {error_msg}", file=sys.stderr)
        except Exception as e:
            # Catch any unexpected errors and keep the app running
            print(f"Unexpected error in play_text: {e}", file=sys.stderr)
            self.play_btn.setEnabled(True)
            self.statusBar().showMessage("Error occurred")
            try:
                QMessageBox.warning(self, "Error", f"An error occurred: {str(e)}")
            except:
                pass  # If we can't show dialog, just continue
    
    def stop_text(self):
        """Stop the text-to-speech"""
        # Stop highlighting immediately
        self.stop_highlighting()
        
        # Stop the TTS thread immediately
        if self.tts_thread and self.tts_thread.isRunning():
            self.tts_thread.stop()
            # Wait with timeout to avoid hanging
            self.tts_thread.wait(100)  # Wait max 100ms for thread to stop
        
        # Also stop the main engine if it exists (for redundancy)
        if self.engine:
            try:
                self.engine.stop()
            except:
                pass
        
        self.play_btn.setEnabled(True)
        self.statusBar().showMessage("Stopped")
    
    def clear_text(self):
        """Clear the text area"""
        self.text_area.clear()
        self.statusBar().showMessage("Text cleared")
    
    def on_speech_finished(self):
        """Called when speech finishes"""
        try:
            # Stop highlighting
            self.stop_highlighting()
            # Re-enable play button
            self.play_btn.setEnabled(True)
            self.statusBar().showMessage("Finished")
            # Engine cleanup is handled by the thread's run() method finally block
        except Exception as e:
            # Log error but don't crash the app
            print(f"Error in on_speech_finished: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            try:
                self.stop_highlighting()
                self.play_btn.setEnabled(True)
                self.statusBar().showMessage("Finished (with warning)")
            except:
                pass  # If even this fails, just continue
    
    def prepare_word_positions(self, text):
        """Prepare list of word positions in the text"""
        import re
        self.word_positions = []
        cursor = QTextCursor(self.text_area.document())
        
        # Find all word boundaries
        words = re.finditer(r'\b\w+\b', text)
        for match in words:
            start_pos = match.start()
            end_pos = match.end()
            self.word_positions.append((start_pos, end_pos))
    
    def start_highlighting(self, text, rate):
        """Start word-by-word highlighting synchronized with TTS playback"""
        # Clear any existing highlights
        self.stop_highlighting()
        
        # Prepare word positions
        self.prepare_word_positions(text)
        
        if not self.word_positions:
            return
        
        # Reset to first word
        self.current_word_index = 0
        
        # Calculate delay per word to match actual audio playback speed
        # The rate (WPM) is what the user wants, and audio playback speed is adjusted to achieve it
        # Audio is played at: playback_speed = rate / 150 (e.g., 300 WPM = 2x speed)
        # So words are spoken at the target rate, meaning highlighting should match the rate directly
        words_per_second = rate / 60.0
        delay_ms = int(1000 / words_per_second) if words_per_second > 0 else 200
        
        # Clamp delay to reasonable range
        delay_ms = max(50, min(delay_ms, 1000))
        
        # Account for initial audio playback latency
        # There's a delay before audio actually starts (buffer fill, player startup, network latency)
        # This varies by platform and player, so we use a reasonable estimate
        # For pre-generated audio, latency is lower; for on-demand, it's higher
        if platform.system() == 'Linux':
            initial_latency_ms = 350  # Linux streaming: buffer fill + player startup
        elif platform.system() == 'Darwin':
            initial_latency_ms = 600  # macOS: temp file generation + afplay startup
        else:
            initial_latency_ms = 400  # Windows: temp file + player startup
        
        # Start the repeating timer for word highlighting
        self.highlight_timer.start(delay_ms)
        
        # Don't highlight first word immediately - wait for audio to actually start playing
        # Use a one-shot timer to account for initial latency before starting highlights
        # This ensures highlighting starts when audio actually begins, not when generation starts
        QTimer.singleShot(initial_latency_ms, self.highlight_next_word)
    
    def highlight_next_word(self):
        """Highlight the next word in yellow"""
        if not self.word_positions or self.current_word_index >= len(self.word_positions):
            self.stop_highlighting()
            return
        
        # Clear previous word's highlight (if not first word)
        if self.current_word_index > 0:
            prev_start, prev_end = self.word_positions[self.current_word_index - 1]
            cursor = QTextCursor(self.text_area.document())
            cursor.setPosition(prev_start)
            cursor.setPosition(prev_end, QTextCursor.MoveMode.KeepAnchor)
            # Use transparent background to clear highlight without affecting text
            clear_format = QTextCharFormat()
            clear_format.setBackground(Qt.GlobalColor.transparent)
            cursor.mergeCharFormat(clear_format)
        
        # Highlight current word
        start_pos, end_pos = self.word_positions[self.current_word_index]
        cursor = QTextCursor(self.text_area.document())
        cursor.setPosition(start_pos)
        cursor.setPosition(end_pos, QTextCursor.MoveMode.KeepAnchor)
        
        # Create yellow highlight format
        highlight_format = QTextCharFormat()
        highlight_format.setBackground(QColor("yellow"))
        cursor.mergeCharFormat(highlight_format)
        
        # Scroll to make the word visible
        self.text_area.setTextCursor(cursor)
        self.text_area.ensureCursorVisible()
        
        # Move to next word
        self.current_word_index += 1
    
    def stop_highlighting(self):
        """Stop highlighting and clear all highlights"""
        self.highlight_timer.stop()
        
        # Clear all highlights by setting transparent background
        cursor = QTextCursor(self.text_area.document())
        cursor.select(QTextCursor.SelectionType.Document)
        format = QTextCharFormat()
        format.setBackground(Qt.GlobalColor.transparent)
        cursor.mergeCharFormat(format)
        
        # Reset state
        self.word_positions = []
        self.current_word_index = 0
    
    def on_speech_error(self, error_msg):
        """Called when speech encounters an error"""
        self.stop_highlighting()
        self.play_btn.setEnabled(True)
        QMessageBox.critical(self, "Error", f"Speech error: {error_msg}")
        self.statusBar().showMessage("Error occurred")
    
    def get_selected_text_macos(self):
        """Get selected text from macOS using AppleScript"""
        try:
            # Use AppleScript to get selected text
            script = '''
            tell application "System Events"
                keystroke "c" using command down
            end tell
            delay 0.1
            return the clipboard as string
            '''
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                text = result.stdout.strip()
                # Only return if we got actual text (not empty)
                if text:
                    return text
        except Exception as e:
            print(f"Error getting selected text: {e}", file=sys.stderr)
        return None
    
    def get_selected_text_linux(self):
        """Get selected text from Linux using xclip or xsel"""
        try:
            # Try xclip first (X11 - primary selection)
            try:
                result = subprocess.run(
                    ['xclip', '-o', '-selection', 'primary'],
                    capture_output=True,
                    text=True,
                    timeout=1
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            except FileNotFoundError:
                pass
            
            # Fallback to xclip clipboard
            try:
                result = subprocess.run(
                    ['xclip', '-o'],
                    capture_output=True,
                    text=True,
                    timeout=1
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            except FileNotFoundError:
                pass
            
            # Try xsel as fallback (primary selection)
            try:
                result = subprocess.run(
                    ['xsel', '-p'],  # primary selection
                    capture_output=True,
                    text=True,
                    timeout=1
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            except FileNotFoundError:
                pass
            
            # Try xsel clipboard
            try:
                result = subprocess.run(
                    ['xsel', '-b'],  # clipboard
                    capture_output=True,
                    text=True,
                    timeout=1
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            except FileNotFoundError:
                pass
                
        except Exception as e:
            print(f"Error getting selected text on Linux: {e}", file=sys.stderr)
        return None
    
    def on_hotkey_pressed(self):
        """Called when global hotkey is pressed"""
        print("on_hotkey_pressed called in main thread", file=sys.stderr)
        try:
            # Get selected text based on platform
            print("Getting selected text...", file=sys.stderr)
            if platform.system() == 'Darwin':
                selected_text = self.get_selected_text_macos()
            else:
                selected_text = self.get_selected_text_linux()
            print(f"Got text: {selected_text[:50] if selected_text else 'None'}...", file=sys.stderr)
            
            if selected_text and selected_text.strip():
                # Set text in text area
                self.text_area.setPlainText(selected_text)
                # Start reading immediately
                self.play_text()
                # Bring window to front
                self.raise_()
                self.activateWindow()
                self.statusBar().showMessage("Reading selected text...")
            else:
                # If no text selected, show message
                self.statusBar().showMessage("No text selected. Please select text first.")
                print("No text was selected", file=sys.stderr)
        except Exception as e:
            print(f"Error handling hotkey: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            self.statusBar().showMessage("Error reading selected text")
    
    def check_accessibility_permissions(self):
        """Check if Accessibility permissions are granted on macOS"""
        if platform.system() != 'Darwin' or not PYNPUT_AVAILABLE:
            return True  # Not macOS or pynput not available, skip check
        
        try:
            # Try to create a listener - if it fails, permissions might be missing
            # This is a simple test - actual permission errors will show when starting the listener
            return True  # We'll catch permission errors when starting the actual listener
        except Exception as e:
            print(f"Accessibility permission check: {e}", file=sys.stderr)
            return True  # Don't block, let the actual listener show the error
    
    def setup_global_hotkey(self):
        """Setup global hotkey listener"""
        if not PYNPUT_AVAILABLE:
            print("Global hotkey feature requires 'pynput' library. Install it with: pip install pynput", file=sys.stderr)
            self.statusBar().showMessage("Global hotkey requires pynput library")
            return
        
        # Check permissions on macOS
        if not self.check_accessibility_permissions():
            self.statusBar().showMessage("Global hotkey disabled: Accessibility permissions required")
            return
        
        try:
            print("Setting up global hotkey...", file=sys.stderr)
            # Create and start hotkey thread
            self.hotkey_thread = GlobalHotkeyThread()
            self.hotkey_thread.hotkey_pressed.connect(self.on_hotkey_pressed)
            self.hotkey_thread.start()
            print("Hotkey thread started", file=sys.stderr)
            if platform.system() == 'Darwin':
                hotkey_msg = "Cmd+Shift+R"
            else:
                hotkey_msg = "Ctrl+Shift+R"
            self.statusBar().showMessage(f"Global hotkey enabled: {hotkey_msg} (select text and press to read)")
        except Exception as e:
            print(f"Error setting up global hotkey: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            error_msg = str(e)
            if "accessibility" in error_msg.lower() or "permission" in error_msg.lower():
                QMessageBox.warning(
                    self,
                    "Accessibility Permission Required",
                    "The global hotkey requires Accessibility permissions.\n\n"
                    "Please grant permissions in:\n"
                    "System Settings > Privacy & Security > Accessibility"
                )
            self.statusBar().showMessage(f"Global hotkey error: {error_msg}")
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Stop hotkey thread
        if self.hotkey_thread and self.hotkey_thread.isRunning():
            self.hotkey_thread.stop()
            self.hotkey_thread.wait(1000)
        
        # Stop any playing speech
        if self.tts_thread and self.tts_thread.isRunning():
            self.stop_text()
        
        event.accept()


def exception_handler(exc_type, exc_value, exc_traceback):
    """Global exception handler to prevent app from crashing"""
    # Allow SystemExit and KeyboardInterrupt to work normally
    if issubclass(exc_type, (KeyboardInterrupt, SystemExit)):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    # Log the error but don't crash the app
    error_msg = f"Unhandled exception: {exc_type.__name__}: {exc_value}"
    print(error_msg, file=sys.stderr)
    import traceback
    traceback.print_exception(exc_type, exc_value, exc_traceback, file=sys.stderr)
    
    # Try to show a message box if possible, but don't let it crash the app
    try:
        app = QApplication.instance()
        if app and app.activeWindow():
            # Only show dialog if we have an active window
            QMessageBox.critical(app.activeWindow(), "Unexpected Error", 
                                f"An unexpected error occurred:\n{error_msg}\n\nThe application will continue running.")
    except Exception as e:
        # If showing dialog fails, just log it
        print(f"Could not show error dialog: {e}", file=sys.stderr)
        pass  # Continue running - DO NOT EXIT


def main():
    # Set up global exception handler
    sys.excepthook = exception_handler
    
    # Prevent SystemExit from being raised by pyttsx3 or other libraries
    # We'll handle exits ourselves
    original_exit = sys.exit
    def safe_exit(code=0):
        """Prevent unexpected exits - only allow exit if it's intentional"""
        # Only allow exit if it's from the main thread and code is 0 (normal)
        # Otherwise, log it and continue
        import threading
        if threading.current_thread() is threading.main_thread() and code == 0:
            original_exit(code)
        else:
            print(f"Prevented unexpected exit with code {code} from thread {threading.current_thread().name}", file=sys.stderr)
    
    # Don't override sys.exit - it might cause issues
    # Instead, we'll catch SystemExit in the exception handler
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern, clean style
    
    # App will quit when user explicitly closes the window
    app.setQuitOnLastWindowClosed(True)
    
    try:
        window = ReadAnythingApp()
        window.show()
        
        # Run the application event loop
        # This will keep the app running until the user closes the window
        exit_code = app.exec()
        
        # Clean up any remaining TTS threads before exiting
        if hasattr(window, 'tts_thread') and window.tts_thread:
            if window.tts_thread.isRunning():
                window.tts_thread.stop()
                window.tts_thread.wait(1000)  # Wait up to 1 second for thread to finish
        
        return exit_code
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        return 0
    except SystemExit as e:
        # If SystemExit is raised, check if it's intentional
        # If code is 0, it's probably intentional (user closed window)
        # Otherwise, prevent it and keep app running
        if e.code == 0:
            return 0
        else:
            print(f"Prevented SystemExit with code {e.code}, keeping app running", file=sys.stderr)
            # Try to keep the app running
            return 0
    except Exception as e:
        # Final safety net - show error but try to keep app running
        try:
            QMessageBox.critical(None, "Fatal Error", 
                               f"A fatal error occurred:\n{str(e)}\n\nPlease check the console for details.")
        except:
            # If we can't show dialog, just print
            print(f"Fatal error: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
        # Don't exit - let the app continue if possible
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code if exit_code is not None else 0)

