# ReadAnything

A minimalistic, cross-platform text-to-speech application with a clean GUI. Read text aloud on Linux and macOS.

## Features

- 🎤 **Text-to-Speech**: Convert any text to speech
- ⌨️ **Global Hotkey**: Read selected text from any application with Cmd+Shift+R
- 🎚️ **Customizable**: Adjustable speech speed and voice selection
- 🎨 **Minimalistic Design**: Clean, easy-to-use interface
- 🖥️ **Cross-Platform**: Works on Linux and macOS
- ✨ **Word Highlighting**: See each word highlighted as it's being spoken

## Requirements

- Python 3.8 or higher
- For Linux: `espeak` or `festival` (usually pre-installed)
- For macOS: Built-in speech synthesizer (no additional setup needed)

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/ZeroDayZen/readanything.git
cd readanything
```

### 2. Create a virtual environment (recommended)

```bash
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Linux-specific setup (if needed)

If you encounter issues with text-to-speech on Linux, install the required packages:

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install espeak espeak-data libespeak1 libespeak-dev
```

**Fedora:**
```bash
sudo dnf install espeak espeak-devel
```

**Arch Linux:**
```bash
sudo pacman -S espeak
```

## Usage

### Running the Application

**Option 1: Double-click the macOS App (Recommended for macOS users)**

Simply double-click `ReadAnything.app` in Finder to launch the application. The app will automatically:
- Activate the virtual environment
- Launch the GUI application

**Option 2: Command Line**

```bash
python3 main.py
```

### Using the Application

**Method 1: Manual Entry**
1. **Enter Text**: Type or paste text directly into the text area
2. **Select Voice**: Choose a voice from the dropdown menu
3. **Adjust Speed**: Use the slider to control speech speed (50-300)
4. **Play**: Click the "▶ Play" button to start reading
5. **Stop**: Click the "⏹ Stop" button to stop reading
6. **Clear**: Click "Clear" to clear the text area

**Method 2: Global Hotkey (macOS)**
1. **Select Text**: Highlight any text in any application (browser, document, etc.)
2. **Press Hotkey**: Press **Cmd+Shift+R** to instantly read the selected text
3. The app will automatically:
   - Copy the selected text
   - Load it into the text area
   - Start reading immediately
   - Bring the app window to the front

**Note**: As text is being read, each word will be highlighted in yellow to show which word is currently being spoken.

## Screenshots

The application features a clean, minimalistic interface with:
- Large text input area
- Intuitive playback controls
- Voice and speed customization options
- Real-time word highlighting during playback

## Troubleshooting

### macOS App not launching from Finder

If double-clicking `ReadAnything.app` doesn't work:

1. **Check the log file**: Open `~/Library/Logs/ReadAnything.log` to see error messages
2. **Try from Terminal**: Run `open ReadAnything.app` from Terminal to see if there are any errors
3. **Architecture issues**: If you see "incompatible architecture" errors, try:
   ```bash
   source venv/bin/activate
   pip install --upgrade --force-reinstall PyQt6
   ```
4. **Security settings**: macOS might block the app. Right-click the app and select "Open" to allow it

### Text-to-speech not working on Linux

If you get errors about TTS initialization:
1. Ensure `espeak` is installed (see Linux-specific setup above)
2. Try running: `sudo apt-get install python3-pyaudio` (Ubuntu/Debian)


### Adding More Natural Voices (macOS)

To add more human-like voices to your application:

1. **Open System Settings** (or System Preferences on older macOS)
2. Go to **Accessibility** > **Spoken Content**
3. Click on the **System Voice** dropdown
4. Select **Customize...**
5. Browse and download additional voices (Enhanced/Neural voices are recommended for the most natural sound)
6. Once downloaded, restart the application - new voices will automatically appear in the voice dropdown

**Recommended voices to download:**
- **Enhanced voices** (marked with "Enhanced" or "Neural") provide the most natural, human-like sound
- Popular enhanced voices include: Ava, Nicky, Daniel, Karen, Moira, Veena
- These voices use advanced neural networks for more natural intonation and pronunciation

**Note:** Downloaded voices will automatically appear in the application if they are US English (en_US) voices and not in the blacklist of robotic voices.

## Development

### Project Structure

```
readanything/
├── main.py              # Main application file
├── requirements.txt     # Python dependencies
├── README.md           # This file
├── .gitignore          # Git ignore rules
└── ReadAnything.app    # macOS application bundle (double-click to launch)
```

## License

MIT

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
