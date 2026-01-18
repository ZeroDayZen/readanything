# Linux Compatibility Guide for ReadAnything

## Current Status

The app **will work on Kali Linux** with Edge TTS (AI-powered text-to-speech).

### ✅ What Works Out of the Box

- **Text-to-Speech**: Works on Linux using either:
  - **System (Offline)** engine (via `pyttsx3` + your system’s TTS backend), or
  - **Edge TTS (Online)** for higher-quality neural voices
- **GUI Interface**: PyQt6 is fully cross-platform
- **Word Highlighting**: Platform-independent feature
- **Voice Selection**: All Edge TTS English US voices available in dropdown
- **Speed Control**: Works on all platforms
- **High-Quality Voices**: Neural AI voices with natural sound

### ⚠️ What Needs Setup

1. **Internet Connection**: Required if you choose **Edge TTS (Online)** (System engine works offline)
2. **Audio Player**: Linux needs an audio player (paplay, aplay, mpg123, or mpv)
3. **Global Hotkey**: Platform-aware (Ctrl+Shift+R on Linux)

## Installation on Kali Linux

### 1. Install System Dependencies

```bash
# Update package list
sudo apt-get update

# Install PyQt6 system dependencies
sudo apt-get install python3-pyqt6 python3-pyqt6.qtmultimedia

# Install audio player (for playing Edge TTS audio files)
sudo apt-get install pulseaudio-utils mpg123

# Install clipboard utilities (for hotkey feature)
sudo apt-get install xclip xsel

# Install audio system (if not already installed)
sudo apt-get install alsa-utils pulseaudio
```

**Note**: Edge TTS is a Python package and doesn't require system TTS engines like `espeak` or `festival`. The audio player is only needed to play the generated audio files.

### 2. Install Python Dependencies

**Important**: Kali Linux (and newer Linux distributions) use PEP 668 which prevents installing packages system-wide. You **must** use a virtual environment.

```bash
# Install python3-venv if not already installed
sudo apt-get install python3-venv

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip (recommended)
pip install --upgrade pip

# Install requirements (includes edge-tts)
pip install -r requirements.txt
```

**Note**: If you see an "externally-managed-environment" error, it means you're trying to install packages outside a virtual environment. Always activate the virtual environment first with `source venv/bin/activate` before running `pip install`.

### 3. Run the Application

```bash
source venv/bin/activate
python3 main.py
```

**Note**: Edge TTS is an online TTS option. If you need offline/private behavior, select **System (Offline)** in the app.

## Known Limitations on Linux

### 1. Global Hotkey Feature

**Current Issue**: The hotkey is hardcoded to `Cmd+Shift+R` (macOS)

**Workaround**: The hotkey feature will not work on Linux until code is updated to:
- Detect Linux platform
- Use `Ctrl+Shift+R` instead of `Cmd+Shift+R`
- Use `xclip`/`xsel` instead of AppleScript for getting selected text

**Temporary Solution**: Use the app manually - paste text and click Play

### 2. Edge TTS Voice Selection

**How It Works**: The app uses Edge TTS which provides high-quality neural AI voices from Microsoft Azure.

**Available Voices**: 
- All English US (en-US) voices from Edge TTS
- Voices are automatically fetched and displayed in the dropdown
- Includes voices like: Aria, Jenny, Guy, Jane, Jason, Nancy, Tony, and many more
- Each voice shows gender information (e.g., "Aria (Female)")

**Voice Quality**:
- ✅ **Neural AI voices** - Natural, human-like sound
- ✅ **No robotic sound** - Much better than traditional TTS engines
- ✅ **Multiple options** - Choose from many voices
- ⚠️ **Requires internet** to generate speech

**Privacy/Network**:
- Edge TTS uses Microsoft’s service to generate audio; the text is sent to the service to synthesize speech.
- For sensitive content, use **System (Offline)**.

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
# Check if audio player is installed
which paplay
which mpg123

# Install audio player if missing
sudo apt-get install pulseaudio-utils mpg123

# Test audio system
paplay /usr/share/sounds/alsa/Front_Left.wav

# Check audio system
aplay /usr/share/sounds/alsa/Front_Left.wav

# Install missing packages
sudo apt-get install alsa-utils pulseaudio
```

### Edge TTS Not Working

```bash
# Check if edge-tts is installed
pip show edge-tts

# Reinstall if needed
pip install --upgrade edge-tts

# Test Edge TTS directly
python3 -c "import edge_tts; print('Edge TTS installed successfully')"
```

### No Voices in Dropdown

```bash
# Check internet connection (required for first voice fetch)
ping -c 3 google.com

# Check Edge TTS can fetch voices
python3 -c "import asyncio; import edge_tts; asyncio.run(edge_tts.list_voices())"

# If voices don't load, check firewall/proxy settings
```

### PyQt6 Import Errors

```bash
# Install system packages
sudo apt-get install python3-pyqt6 python3-pyqt6.qtmultimedia

# Reinstall PyQt6
pip install --upgrade --force-reinstall PyQt6
```

### Voice Download Issues

```bash
# Check cache directory
ls -la ~/.cache/edge-tts/

# Clear cache if corrupted (will re-download on next use)
rm -rf ~/.cache/edge-tts/

# Check disk space
df -h ~/.cache/
```

## Summary

**The app will work on Kali Linux** with Edge TTS! 

**Requirements:**
- ✅ Python 3.8+ (usually pre-installed on Kali)
- ✅ Audio player (paplay, mpg123, or similar) for Edge TTS audio playback
- ✅ Internet connection if using Edge TTS

**Benefits of Edge TTS on Linux:**
- 🎯 **High-quality neural voices** - Much better than espeak/festival
- 🚀 **Easy setup** - No system TTS engine installation needed
- 🌐 **Offline capable** - Works offline after first download
- 🎨 **Many voice options** - 20+ English US voices to choose from

