# Piper TTS Setup Guide

ReadAnything now supports **Piper TTS** - a fully offline, high-quality neural text-to-speech engine!

## What is Piper TTS?

Piper TTS is an open-source, ONNX-based neural text-to-speech engine that runs **completely offline** on your machine. Unlike cloud-based TTS services, **your text never leaves your device** when using Piper.

## Features

- ✅ **100% Offline** - No internet required after setup
- ✅ **Privacy First** - Your text never leaves your machine
- ✅ **High Quality** - Neural AI voices with natural intonation
- ✅ **Free & Open Source** - No API keys or subscriptions
- ✅ **Multiple Voices** - Many voice models available in different languages
- ✅ **Local Processing** - All TTS generation happens on your computer

## Installation

### 1. Install Piper Binary

**macOS:**
```bash
# Using Homebrew
brew install piper

# Or download from GitHub releases
# Visit: https://github.com/rhasspy/piper/releases
```

**Linux:**
```bash
# Download from GitHub releases
# Visit: https://github.com/rhasspy/piper/releases

# Or build from source (see Piper GitHub repo)
```

**Windows:**
- Download the Windows binary from: https://github.com/rhasspy/piper/releases

### 2. Download Voice Models

Piper voice models are `.onnx` files. Download them from:

**Official Voice Models:**
- Visit: https://github.com/rhasspy/piper/releases
- Look for voice model releases (typically named like `voice-en_US-amy-medium`)

**Place models in one of these locations:**
- `~/.local/share/piper/voices/` (recommended for Linux/macOS)
- `~/.piper/voices/`
- Custom location (set `PIPER_VOICES_PATH` environment variable)

**Example:**
```bash
# Create voices directory
mkdir -p ~/.local/share/piper/voices/en_US

# Download and extract a voice model
# (example structure: en_US/amy/amy.onnx)
```

### 3. Verify Installation

Test that `piper` command is available:
```bash
piper --version
```

If the command is found, ReadAnything will automatically detect Piper TTS when you restart the app!

## Usage

1. **Open ReadAnything** - Piper voices will appear automatically in the voice dropdown (prefixed with "Piper:")

2. **Select a Piper Voice:**
   - Look for voices starting with "Piper:" in the dropdown
   - Example: "Piper: en_US-amy-medium"

3. **Enter Text and Play:**
   - Type or paste your text
   - Adjust speed if needed
   - Click Play!

The app will automatically use Piper TTS when you select a Piper voice.

## How It Works

1. **Voice Discovery:** ReadAnything scans common locations for `.onnx` voice model files
2. **Local Generation:** When you play text, Piper runs locally on your machine
3. **No Network:** All processing happens offline - your text never leaves your device
4. **Audio Playback:** Generated audio is played using your system's audio player

## Voice Model Locations

ReadAnything looks for Piper voices in these locations (in order):

1. `PIPER_VOICES_PATH` environment variable (if set)
2. `~/.local/share/piper/voices/` (Linux/macOS)
3. `~/.piper/voices/`
4. `/usr/local/share/piper/voices/` (system-wide)
5. `/usr/share/piper/voices/` (system-wide)

## Troubleshooting

### Piper Voices Not Appearing in Dropdown

**Solution 1:** Check if `piper` binary is installed:
```bash
which piper
# or on Windows:
where piper
```

**Solution 2:** Verify voice models are in the correct location:
```bash
# Check if voice directory exists
ls ~/.local/share/piper/voices/

# Look for .onnx files
find ~/.local/share/piper/voices -name "*.onnx"
```

**Solution 3:** Set custom voice path via environment variable:
```bash
export PIPER_VOICES_PATH=/path/to/your/voices
# Then restart ReadAnything
```

### No Sound Plays

**macOS:**
- Make sure audio output is working
- Check system volume
- Ensure `afplay` or `ffplay` is available

**Linux:**
- Install audio player: `sudo apt-get install mpv` (recommended) or `sudo apt-get install pulseaudio-utils mpg123`
- Test audio: `mpg123 test.wav`

**Windows:**
- Check that default audio player is working
- Install ffmpeg for better audio support: https://ffmpeg.org/

### "Piper TTS Not Available" Error

**Solution:** Make sure the `piper` binary is in your system PATH:

```bash
# Check if piper is accessible
piper --version

# If not found, add piper to your PATH or create a symlink:
# Linux/macOS:
sudo ln -s /path/to/piper /usr/local/bin/piper
```

### Voice Models Not Found

**Solution:** Verify your voice model files:
- Must have `.onnx` extension
- Should be in one of the standard locations listed above
- Directory structure: `language/voice_name/voice.onnx` (recommended)

**Example structure:**
```
~/.local/share/piper/voices/
  └── en_US/
      └── amy/
          └── amy.onnx
```

## Comparison with Other Engines

| Feature | System (Default) | Piper TTS | Edge TTS |
|---------|-----------------|-----------|----------|
| **Offline** | ✅ Always | ✅ Always (after setup) | ❌ Requires internet |
| **Privacy** | ✅ 100% local | ✅ 100% local | ⚠️ Text sent to Microsoft |
| **Quality** | Good | Excellent (Neural AI) | Excellent (Neural AI) |
| **Voice Options** | System voices | Many models available | 7+ Microsoft voices |
| **Setup Complexity** | None | Medium (install binary + models) | Easy (pip install) |
| **Internet Required** | Never | Never (after setup) | Always |

## Recommendations

**Use Piper TTS when:**
- ✅ You want high-quality neural voices
- ✅ You need fully offline operation
- ✅ Privacy is important (text never leaves your device)
- ✅ You're okay with installing the Piper binary and voice models

**Use System (Default) when:**
- ✅ You want zero setup (works immediately)
- ✅ System voices are sufficient for your needs
- ✅ You prefer simplicity

**Use Edge TTS when:**
- ⚠️ You're okay with online processing
- ⚠️ Privacy is less of a concern
- ⚠️ You want easy setup without downloading models

## Technical Details

- **Voice Format:** ONNX neural models
- **Audio Format:** WAV
- **Model Size:** ~40-100MB per voice (varies by model)
- **Processing:** 100% local (your computer)
- **Privacy:** Text never leaves your device
- **Network Usage:** None (after initial download of models)

## Getting Help

- **Piper GitHub:** https://github.com/rhasspy/piper
- **Voice Models:** https://github.com/rhasspy/piper/releases
- **Documentation:** See Piper project documentation

---

Enjoy high-quality, **fully offline** neural voices with Piper TTS! 🎉
