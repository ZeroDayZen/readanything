# AI TTS Setup Guide

ReadAnything now supports AI-powered text-to-speech engines for higher quality voices!

## Available AI TTS Engines

### 1. Google Text-to-Speech (gTTS) - FREE

**Features:**
- ✅ Free to use
- ✅ High-quality AI voices
- ✅ Requires internet connection
- ✅ Easy to set up

**Installation:**
```bash
pip install gtts
```

**Usage:**
1. Select "Google TTS (AI - Free)" from the TTS Engine dropdown
2. Click Play - that's it!
3. Requires internet connection

**Limitations:**
- Requires internet connection
- No voice selection (uses default English US voice)
- Speed control may be limited

---

### 2. OpenAI TTS - PREMIUM

**Features:**
- ✅ Highest quality AI voices
- ✅ Multiple voice options (Alloy, Echo, Fable, Onyx, Nova, Shimmer)
- ✅ Natural-sounding speech
- ✅ Requires API key (paid service)

**Installation:**
```bash
pip install openai
```

**Setup:**

1. **Get an OpenAI API Key:**
   - Visit https://platform.openai.com/api-keys
   - Sign up or log in
   - Create a new API key
   - Copy the key

2. **Set the API Key:**
   
   **On macOS/Linux:**
   ```bash
   export OPENAI_API_KEY='your-api-key-here'
   ```
   
   **On Windows (Command Prompt):**
   ```cmd
   set OPENAI_API_KEY=your-api-key-here
   ```
   
   **On Windows (PowerShell):**
   ```powershell
   $env:OPENAI_API_KEY='your-api-key-here'
   ```

   **To make it permanent**, add it to your shell profile:
   - **macOS/Linux**: Add to `~/.bashrc` or `~/.zshrc`
   - **Windows**: Add as a system environment variable

3. **Use in the app:**
   - Select "OpenAI TTS (AI - Premium)" from the TTS Engine dropdown
   - Choose a voice (Alloy, Echo, Fable, Onyx, Nova, or Shimmer)
   - Click Play

**Pricing:**
- OpenAI TTS is a paid service
- Check current pricing at: https://openai.com/pricing
- Typically ~$15 per 1 million characters

**Available Voices:**
- **Alloy** - Balanced, versatile voice
- **Echo** - Clear, confident voice
- **Fable** - Warm, expressive voice
- **Onyx** - Deep, authoritative voice
- **Nova** - Bright, energetic voice
- **Shimmer** - Soft, gentle voice

---

## Comparison

| Feature | Default (System) | Google TTS | OpenAI TTS |
|---------|-----------------|------------|------------|
| **Cost** | Free | Free | Paid (per character) |
| **Internet** | Not required | Required | Required |
| **Quality** | Good | Very Good | Excellent |
| **Voice Options** | System voices | 1 (default) | 6 voices |
| **Setup Complexity** | None | Easy | Medium (API key) |
| **Speed Control** | Full | Limited | Yes |

---

## Recommendations

**For best quality (if budget allows):**
- Use **OpenAI TTS** for the highest quality, most natural-sounding voices

**For free high-quality voices:**
- Use **Google TTS** - good quality and completely free

**For offline use:**
- Use **Default (System)** - works without internet, uses system voices

---

## Troubleshooting

### Google TTS Issues

**Error: "gTTS library not available"**
- Install: `pip install gtts`

**No sound plays:**
- Check internet connection
- On Linux, install audio player: `sudo apt-get install pulseaudio-utils mpg123`

### OpenAI TTS Issues

**Error: "OpenAI library not available"**
- Install: `pip install openai`

**Error: "OPENAI_API_KEY environment variable not set"**
- Set the environment variable (see Setup instructions above)
- Make sure to restart the application after setting it

**Error: "Incorrect API key"**
- Verify your API key is correct
- Check that you have credits in your OpenAI account

**No sound plays:**
- Check internet connection
- On Linux, install audio player: `sudo apt-get install pulseaudio-utils mpg123`

---

## Notes

- AI TTS engines require an internet connection
- Audio is temporarily downloaded and played locally
- Temporary files are automatically cleaned up
- For privacy-sensitive content, consider using the default (offline) engine

