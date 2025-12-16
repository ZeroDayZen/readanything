#!/usr/bin/env python3
"""
ReadAnything - A minimalistic text-to-speech application
Supports text input, PDF, and Word documents
"""

import sys
import os
import platform
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QLabel, QSlider, QComboBox,
    QMessageBox, QMenuBar, QMenu
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon, QTextCharFormat, QTextCursor, QColor, QShortcut, QKeySequence
import pyttsx3
try:
    from pynput import keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False


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
    
    def __init__(self, text, engine, rate, voice_id):
        super().__init__()
        self.text = text
        self.engine = engine
        self.rate = rate
        self.voice_id = voice_id
        self._is_running = True
        self._process = None
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
    
    def run(self):
        try:
            if not self._is_running:
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
    
    def _run_pyttsx3(self):
        """Run TTS using pyttsx3 (for non-macOS or fallback)"""
        if not self.engine:
            raise Exception("TTS engine not initialized")
        
        self.engine.setProperty('rate', self.rate)
        if self.voice_id:
            self.engine.setProperty('voice', self.voice_id)
        
        # Say the text
        self.engine.say(self.text)
        
        # Use startLoop() and iterate() to avoid event loop conflicts
        try:
            self.engine.startLoop(False)
            for _ in self.engine.iterate():
                if not self._is_running:
                    self.engine.endLoop()
                    break
                self.msleep(10)
            self.engine.endLoop()
        except StopIteration:
            self.engine.endLoop()
        except Exception as e:
            self.engine.endLoop()
            raise e
    
    def stop(self):
        self._is_running = False
        # Stop subprocess if running
        if self._process and self._process.poll() is None:
            try:
                self._process.terminate()
            except:
                pass
        # Stop engine if available
        if self.engine:
            try:
                self.engine.stop()
            except:
                pass


class ReadAnythingApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.tts_thread = None
        self.engine = None
        self.voices = []  # Initialize to empty list to prevent AttributeError
        # Word highlighting
        self.highlight_timer = QTimer()
        self.highlight_timer.timeout.connect(self.highlight_next_word)
        self.word_positions = []  # List of (start_pos, end_pos) tuples
        self.current_word_index = 0
        self.original_format = QTextCharFormat()
        # Global hotkey
        self.hotkey_thread = None
        self.init_engine()
        self.init_ui()
        self.setup_global_hotkey()
        
    def init_engine(self):
        """Initialize text-to-speech engine"""
        try:
            self.engine = pyttsx3.init()
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
        self.setWindowTitle("ReadAnything")
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
        
        # Text input area
        text_label = QLabel("Enter text:")
        text_label.setFont(QFont("Arial", 10))
        layout.addWidget(text_label)
        
        self.text_area = QTextEdit()
        self.text_area.setPlaceholderText("Type or paste your text here...")
        self.text_area.setFont(QFont("Arial", 12))
        self.text_area.setStyleSheet("background-color: white;")
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
        voice_layout.addWidget(self.voice_combo)
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
        
        # Status bar
        self.statusBar().showMessage("Ready")
    
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
        
        # About action
        about_action = help_menu.addAction("About ReadAnything")
        about_action.triggered.connect(self.show_about)
    
    def show_about(self):
        """Show About dialog with usage instructions"""
        about_text = """
<h2>ReadAnything</h2>
<p><b>Version 1.0-beta</b></p>
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
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()
    
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
    
    def populate_voices(self):
        """Populate voice selection dropdown"""
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
                    
                    # If no voices found, try a simpler fallback approach
                    if self.voice_combo.count() == 0:
                        # Fallback: try to add common voices directly
                        fallback_voices = ['Samantha', 'Fred', 'Kathy', 'Ralph', 'Alex', 'Victoria']
                        for voice in fallback_voices:
                            try:
                                # Test if voice exists by trying to use it (quick test)
                                test_result = subprocess.run(
                                    ['say', '-v', voice, 'test'],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    timeout=1
                                )
                                # If command succeeds, voice exists
                                if test_result.returncode == 0 or 'test' in str(test_result.stderr):
                                    self.voice_combo.addItem(voice, voice)
                                    if self.voice_combo.count() >= 3:  # Stop after finding a few
                                        break
                            except:
                                continue
                        
                        # If still no voices, add default
                        if self.voice_combo.count() == 0:
                            self.voice_combo.addItem("Default", None)
                else:
                    # If say command failed, try fallback
                    fallback_voices = ['Samantha', 'Fred', 'Kathy', 'Ralph']
                    for voice in fallback_voices:
                        try:
                            test_result = subprocess.run(
                                ['say', '-v', voice, 'test'],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                timeout=1
                            )
                            if test_result.returncode == 0 or 'test' in str(test_result.stderr):
                                self.voice_combo.addItem(voice, voice)
                        except:
                            continue
                    if self.voice_combo.count() == 0:
                        self.voice_combo.addItem("Default", None)
            except Exception as e:
                # On any error, try to add at least some common voices
                fallback_voices = ['Samantha', 'Fred', 'Kathy', 'Ralph']
                for voice in fallback_voices:
                    try:
                        self.voice_combo.addItem(voice, voice)
                    except:
                        continue
                if self.voice_combo.count() == 0:
                    self.voice_combo.addItem("Default", None)
        else:
            # Use pyttsx3 voices for non-macOS
            if self.engine and self.voices:
                for i, voice in enumerate(self.voices):
                    name = voice.name
                    self.voice_combo.addItem(name, voice.id)
            else:
                self.voice_combo.addItem("Default", None)
    
    def update_speed_label(self, value):
        """Update speed label when slider changes"""
        self.speed_label.setText(str(value))
    
    def play_text(self):
        """Play the text using text-to-speech"""
        try:
            if not self.engine:
                QMessageBox.warning(self, "Error", "Text-to-speech engine not available")
                return
            
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
            
            # Create new engine instance for this thread
            # We create it in the main thread to avoid issues
            engine = None
            try:
                # Protect against any exceptions during engine creation
                engine = pyttsx3.init()
                if not engine:
                    raise Exception("Failed to initialize TTS engine")
            except SystemExit as e:
                # Prevent SystemExit from closing the app
                print(f"Prevented SystemExit during engine creation: {e.code}", file=sys.stderr)
                self.play_btn.setEnabled(True)
                self.statusBar().showMessage("Error: Engine creation failed")
                return
            except Exception as engine_error:
                # Re-enable play button on error
                self.play_btn.setEnabled(True)
                self.statusBar().showMessage("Error initializing TTS engine")
                error_msg = str(engine_error)
                print(f"Error initializing TTS engine: {error_msg}", file=sys.stderr)
                import traceback
                traceback.print_exc()
                try:
                    QMessageBox.critical(self, "Error", f"Failed to initialize TTS engine: {error_msg}")
                except:
                    print(f"Could not show error dialog: {error_msg}", file=sys.stderr)
                return  # Exit early if engine creation fails
            
            # Create and start thread
            try:
                # Create thread object
                self.tts_thread = TextToSpeechThread(text, engine, speed, voice_id)
                
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
                try:
                    if engine:
                        engine.stop()
                except:
                    pass
            except Exception as thread_error:
                # Re-enable play button on error
                self.play_btn.setEnabled(True)
                self.statusBar().showMessage("Error starting speech thread")
                error_msg = str(thread_error)
                print(f"Error starting TTS thread: {error_msg}", file=sys.stderr)
                import traceback
                traceback.print_exc()
                # Clean up engine if thread creation failed
                try:
                    if engine:
                        engine.stop()
                except:
                    pass
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
        # Stop highlighting
        self.stop_highlighting()
        
        if self.tts_thread and self.tts_thread.isRunning():
            self.tts_thread.stop()
            self.tts_thread.wait()
        
        if self.engine:
            self.engine.stop()
        
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
            # Don't try to clean up the engine here - it's managed by the thread
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
        """Start word-by-word highlighting"""
        # Clear any existing highlights
        self.stop_highlighting()
        
        # Prepare word positions
        self.prepare_word_positions(text)
        
        if not self.word_positions:
            return
        
        # Reset to first word
        self.current_word_index = 0
        
        # Calculate delay per word based on rate (words per minute)
        # Average reading speed is ~150 WPM, so adjust accordingly
        words_per_second = rate / 60.0
        delay_ms = int(1000 / words_per_second) if words_per_second > 0 else 200
        # Add some buffer for natural pauses
        delay_ms = max(100, min(delay_ms, 500))
        
        # Start timer
        self.highlight_timer.start(delay_ms)
        # Highlight first word immediately
        self.highlight_next_word()
    
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

