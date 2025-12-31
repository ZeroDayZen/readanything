# Installation Guide for Kali Linux

This guide will help you install ReadAnything on Kali Linux.

## Quick Install

### Option 1: Using the GUI Installer (Recommended)

1. **Download the repository:**
   ```bash
   git clone https://github.com/ZeroDayZen/readanything.git
   cd readanything
   ```

2. **Run the installer:**
   ```bash
   python3 installer.py
   ```

3. **Follow the GUI prompts** to install dependencies and set up the application.

### Option 2: Manual Installation

#### Step 1: Install System Dependencies

```bash
# Update package list
sudo apt-get update

# Install TTS backend (espeak)
sudo apt-get install -y espeak espeak-data libespeak1 libespeak-dev

# Install PyQt6 system dependencies
sudo apt-get install -y python3-pyqt6 python3-pyqt6.qtmultimedia

# Install clipboard utilities (for global hotkey feature)
sudo apt-get install -y xclip xsel

# Install audio system (if not already installed)
sudo apt-get install -y alsa-utils pulseaudio
```

#### Step 2: Install Python Dependencies

```bash
# Navigate to the project directory
cd readanything

# Create virtual environment (recommended)
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install Python packages
pip install --upgrade pip
pip install -r requirements.txt
```

#### Step 3: Verify Installation

```bash
# Test espeak
espeak "Hello, this is a test"

# Test Python installation
python3 -c "import PyQt6; print('PyQt6 installed successfully')"
python3 -c "import pyttsx3; print('pyttsx3 installed successfully')"
```

#### Step 4: Run the Application

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Run the application
python3 main.py
```

## Creating a Desktop Shortcut (Optional)

1. **Create a desktop entry file:**
   ```bash
   nano ~/.local/share/applications/readanything.desktop
   ```

2. **Add the following content** (adjust paths as needed):
   ```ini
   [Desktop Entry]
   Version=1.0
   Type=Application
   Name=ReadAnything
   Comment=Text-to-Speech Application
   Exec=/path/to/readanything/venv/bin/python3 /path/to/readanything/main.py
   Icon=/path/to/readanything/logo_128.png
   Terminal=false
   Categories=AudioVideo;Audio;
   ```

3. **Make it executable:**
   ```bash
   chmod +x ~/.local/share/applications/readanything.desktop
   ```

4. **The application should now appear in your applications menu.**

## Troubleshooting

### No Sound Output

```bash
# Test audio system
aplay /usr/share/sounds/alsa/Front_Left.wav

# Check if espeak works
espeak "test"

# Check audio devices
aplay -l
```

### PyQt6 Import Errors

```bash
# Reinstall PyQt6
pip install --upgrade --force-reinstall PyQt6

# Or install system package
sudo apt-get install python3-pyqt6
```

### Global Hotkey Not Working

```bash
# Ensure xclip or xsel is installed
which xclip
which xsel

# Install if missing
sudo apt-get install xclip xsel
```

### Permission Issues

If you encounter permission issues:
```bash
# Make scripts executable
chmod +x main.py
chmod +x installer.py
```

## Updating

### Option 1: GUI Updater (Recommended)

Use the GUI updater to easily update to the latest version:

```bash
python3 update.py
```

The updater will:
- ✓ Check for available updates from GitHub
- ✓ Fetch and pull the latest version
- ✓ Optionally update Python dependencies
- ✓ Handle local changes automatically

### Option 2: Manual Update

Update manually using git:

```bash
# Fetch latest changes
git fetch origin

# Pull latest version
git pull origin main

# Update dependencies (if using venv)
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

**Note:** The updater requires the repository to be cloned using `git clone`. If you downloaded a ZIP file, you'll need to clone the repository to enable updates.

For detailed step-by-step manual update instructions, see [MANUAL_UPDATE.md](../MANUAL_UPDATE.md).

## Uninstallation

### Option 1: GUI Uninstaller (Recommended)

Use the GUI uninstaller for an easy removal process:

```bash
python3 uninstall.py
```

The uninstaller provides:
- ✓ Automatic removal of virtual environment
- ✓ Removal of desktop shortcuts
- ✓ Optional removal of system dependencies
- ✓ Optional removal of project directory
- ✓ Clear status messages and error handling

### Option 2: Manual Uninstallation

If you prefer to uninstall manually:

```bash
# Remove virtual environment
rm -rf venv

# Remove desktop shortcut (if created)
rm ~/.local/share/applications/readanything.desktop

# Remove cloned repository (optional)
cd ..
rm -rf readanything
```

**Note:** If you installed system dependencies specifically for ReadAnything and want to remove them:

```bash
sudo apt-get remove espeak espeak-data libespeak1 libespeak-dev python3-pyqt6 python3-pyqt6.qtmultimedia xclip xsel
```

**Warning:** Only remove system dependencies if they're not used by other applications on your system.

## Next Steps

After installation:
- Launch the application using `python3 main.py` or the desktop shortcut
- Use **Ctrl+Shift+R** to read selected text from any application
- See the About menu (Help > About ReadAnything) for usage instructions

