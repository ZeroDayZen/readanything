# Edge TTS Setup Guide

ReadAnything now supports **Edge TTS** - a free, local AI-powered text-to-speech engine from Microsoft!

## What is Edge TTS?

Edge TTS uses Microsoft's Azure Neural Text-to-Speech voices, which provide high-quality, natural-sounding speech. The best part? **It works completely offline** after the first voice download!

## Features

- ✅ **100% Free** - No API keys or paid subscriptions
- ✅ **Offline Capable** - Works offline after initial voice download
- ✅ **High Quality** - Neural voices with natural intonation
- ✅ **Multiple Voices** - 7+ English US voices to choose from
- ✅ **Local Processing** - Your text never leaves your computer

## Installation

1. **Install Edge TTS:**
   ```bash
   pip install edge-tts
   ```

2. **That's it!** The app will automatically detect Edge TTS when you restart it.

## Usage

1. **Select Edge TTS Engine:**
   - Open ReadAnything
   - In the "TTS Engine" dropdown, select **"Edge TTS (AI - Free, Local)"**

2. **Choose a Voice:**
   - Select from available voices:
     - **Aria** (Neural) - Balanced, versatile
     - **Jenny** (Neural) - Clear, friendly
     - **Guy** (Neural) - Deep, authoritative
     - **Jane** (Neural) - Warm, expressive
     - **Jason** (Neural) - Professional, clear
     - **Nancy** (Neural) - Gentle, pleasant
     - **Tony** (Neural) - Energetic, engaging

3. **Enter Text and Play:**
   - Type or paste your text
   - Adjust speed if needed
   - Click Play!

## How It Works

1. **First Use:** When you first use Edge TTS, it downloads the voice model (usually small, ~5-10MB per voice)
2. **Subsequent Uses:** The voice is cached locally, so it works completely offline!
3. **Privacy:** All processing happens locally - your text never leaves your computer

## Offline Usage

After the initial download, Edge TTS works completely offline. The voices are cached in:
- **macOS:** `~/Library/Caches/edge-tts/`
- **Linux:** `~/.cache/edge-tts/`
- **Windows:** `%LOCALAPPDATA%\edge-tts\`

You can use the app without an internet connection after the first use!

## Troubleshooting

### Edge TTS Not Appearing in Dropdown

**Solution:** Make sure Edge TTS is installed:
```bash
pip install edge-tts
```
Then restart the application.

### No Sound Plays

**macOS:**
- Make sure audio output is working
- Check system volume

**Linux:**
- Install audio player: `sudo apt-get install pulseaudio-utils mpg123`
- Test audio: `mpg123 test.mp3`

### Voice Download Fails

**Solution:** 
- Check your internet connection (required only for first download)
- Try again - downloads are usually fast (~5-10MB per voice)

### Slow Performance

**Solution:**
- First generation might be slower as voice downloads
- Subsequent uses will be faster (cached locally)
- Close and reopen the app if issues persist

## Comparison with Default Engine

| Feature | Default (System) | Edge TTS |
|---------|-----------------|----------|
| **Cost** | Free | Free |
| **Internet** | Not required | Required for first download only |
| **Quality** | Good | Excellent (Neural AI) |
| **Voice Options** | System voices | 7+ Neural voices |
| **Offline** | Always | After first use |
| **Setup** | None | Install edge-tts |

## Recommendations

**Use Edge TTS when:**
- You want the highest quality, most natural-sounding voices
- You're okay with a one-time internet connection for voice download
- You want more voice variety

**Use Default Engine when:**
- You need to work completely offline from the start
- You prefer system voices
- You want zero dependencies

## Technical Details

- **Voice Format:** Neural Text-to-Speech (Azure TTS)
- **Audio Format:** MP3
- **Cache Size:** ~5-10MB per voice
- **Processing:** Local (your computer)

---

Enjoy high-quality, free AI voices with Edge TTS! 🎉

