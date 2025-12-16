# Linux Compatibility Guide for ReadAnything

## Current Status

The app **will work on Kali Linux** with some limitations and required setup.

### ✅ What Works Out of the Box

- **Text-to-Speech**: Uses `pyttsx3` which works on Linux
- **GUI Interface**: PyQt6 is fully cross-platform
- **Word Highlighting**: Platform-independent feature
- **Voice Selection**: Will use available `pyttsx3` voices
- **Speed Control**: Works on all platforms

### ⚠️ What Needs Setup

1. **TTS Backend**: Linux needs a TTS engine installed
2. **Global Hotkey**: Currently hardcoded for macOS (`Cmd+Shift+R`)
3. **Selected Text Capture**: Uses macOS AppleScript (won't work on Linux)

## Installation on Kali Linux

### 1. Install System Dependencies

```bash
# Install TTS backend (espeak is recommended)
sudo apt-get update
sudo apt-get install espeak espeak-data libespeak1 libespeak-dev

# Install PyQt6 system dependencies
sudo apt-get install python3-pyqt6 python3-pyqt6.qtmultimedia

# Install clipboard utilities (for future hotkey feature)
sudo apt-get install xclip xsel

# Install audio system
sudo apt-get install alsa-utils pulseaudio
```

### 2. Install Python Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 3. Run the Application

```bash
source venv/bin/activate
python3 main.py
```

## Known Limitations on Linux

### 1. Global Hotkey Feature

**Current Issue**: The hotkey is hardcoded to `Cmd+Shift+R` (macOS)

**Workaround**: The hotkey feature will not work on Linux until code is updated to:
- Detect Linux platform
- Use `Ctrl+Shift+R` instead of `Cmd+Shift+R`
- Use `xclip`/`xsel` instead of AppleScript for getting selected text

**Temporary Solution**: Use the app manually - paste text and click Play

### 2. Voice Selection

**Current Issue**: Voice detection uses macOS `say` command

**Workaround**: The app falls back to `pyttsx3` voice detection, which should work but may show fewer voices than macOS

**Available Voices**: Depends on installed TTS backends:
- `espeak`: Multiple language voices
- `festival`: Additional voices (if installed)

### 3. Selected Text Capture

**Current Issue**: Uses macOS AppleScript

**Workaround**: Not functional on Linux. Would need to implement:
- `xclip -o -selection primary` for X11
- `wl-paste` for Wayland
- Or use `pynput` to simulate Ctrl+C

## Recommended Code Changes for Full Linux Support

### 1. Update Hotkey for Linux

In `main.py`, line 47, change:
```python
# Current (macOS only):
hotkey = keyboard.HotKey(
    keyboard.HotKey.parse('<cmd>+<shift>+r'),
    self._on_hotkey_pressed
)

# Should be:
if platform.system() == 'Darwin':
    hotkey_str = '<cmd>+<shift>+r'
else:
    hotkey_str = '<ctrl>+<shift>+r'
hotkey = keyboard.HotKey(
    keyboard.HotKey.parse(hotkey_str),
    self._on_hotkey_pressed
)
```

### 2. Add Linux Selected Text Function

Add a new method:
```python
def get_selected_text_linux(self):
    """Get selected text from Linux using xclip"""
    try:
        # Try xclip first (X11)
        result = subprocess.run(
            ['xclip', '-o', '-selection', 'primary'],
            capture_output=True,
            text=True,
            timeout=1
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        
        # Fallback to clipboard
        result = subprocess.run(
            ['xclip', '-o'],
            capture_output=True,
            text=True,
            timeout=1
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except FileNotFoundError:
        # Try xsel as fallback
        try:
            result = subprocess.run(
                ['xsel', '-p'],  # primary selection
                capture_output=True,
                text=True,
                timeout=1
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
    except Exception as e:
        print(f"Error getting selected text: {e}", file=sys.stderr)
    return None
```

### 3. Update `on_hotkey_pressed` Method

Change line 958:
```python
# Current:
selected_text = self.get_selected_text_macos()

# Should be:
if platform.system() == 'Darwin':
    selected_text = self.get_selected_text_macos()
else:
    selected_text = self.get_selected_text_linux()
```

## Testing on Kali Linux

1. **Basic Functionality Test**:
   ```bash
   python3 main.py
   # Enter some text and click Play
   # Should hear speech if espeak is installed
   ```

2. **Voice Selection Test**:
   - Open the voice dropdown
   - Should see available espeak voices
   - Try different voices

3. **Speed Control Test**:
   - Adjust the speed slider
   - Playback speed should change

## Troubleshooting

### No Sound Output

```bash
# Check if espeak is installed
espeak "test"

# Check audio system
aplay /usr/share/sounds/alsa/Front_Left.wav

# Install missing packages
sudo apt-get install alsa-utils pulseaudio
```

### PyQt6 Import Errors

```bash
# Install system packages
sudo apt-get install python3-pyqt6 python3-pyqt6.qtmultimedia

# Reinstall PyQt6
pip install --upgrade --force-reinstall PyQt6
```

### No Voices Available

```bash
# Check espeak voices
espeak --voices

# Install additional voices
sudo apt-get install festival festvox-kallpc16k
```

## Summary

**The app will work on Kali Linux** for basic text-to-speech functionality, but the global hotkey feature needs code updates to work properly. The core TTS, GUI, and playback features should work after installing `espeak` and Python dependencies.

