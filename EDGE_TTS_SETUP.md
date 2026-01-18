# Edge TTS Setup Guide

ReadAnything supports **Edge TTS** - a free, high-quality text-to-speech option that uses Microsoft’s neural voices.

## What is Edge TTS?

Edge TTS uses Microsoft’s Azure Neural Text-to-Speech voices, which provide high-quality, natural-sounding speech.

**Important privacy note:** Edge TTS is an **online** TTS option. When you use it, the text you submit is sent to Microsoft’s service to generate audio. If you need fully offline/private behavior, use the app’s **System (Offline)** engine instead.

## Features

- ✅ **100% Free** - No API keys or paid subscriptions
- ✅ **High Quality** - Neural voices with natural intonation
- ✅ **High Quality** - Neural voices with natural intonation
- ✅ **Multiple Voices** - 7+ English US voices to choose from
- ⚠️ **Internet Required** - Requires a network connection to generate speech

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

Edge TTS generates audio using Microsoft’s service. The app downloads/streams the resulting audio and plays it locally.

## Offline Usage

If you need offline usage, select **System (Offline)** in the app’s TTS Engine dropdown. Edge TTS itself requires internet access to generate speech.

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
| **Internet** | Not required | Required |
| **Quality** | Good | Excellent (Neural AI) |
| **Voice Options** | System voices | 7+ Neural voices |
| **Offline** | Always | No (requires internet) |
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
- **Processing:** Online (Microsoft service), audio played locally

---

Enjoy high-quality, free AI voices with Edge TTS! 🎉

