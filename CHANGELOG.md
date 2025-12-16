# Changelog

All notable changes to ReadAnything will be documented in this file.

## [1.0-beta] - 2024-12-12

### Added
- **Linux Compatibility**: Full support for Kali Linux and other Linux distributions
  - Platform-aware global hotkey (Ctrl+Shift+R on Linux, Cmd+Shift+R on macOS)
  - Linux text selection support using `xclip` and `xsel`
  - Automatic platform detection for TTS engine selection
- **App Icon**: Added speech bubble logo as window icon
  - Icon appears in window title bar on all platforms
  - macOS app bundle includes proper `.icns` icon file
- **About Menu**: Added Help > About menu with usage instructions
  - Comprehensive usage guide
  - Platform-specific setup instructions
  - Troubleshooting tips

### Changed
- **Global Hotkey**: Now works on both macOS and Linux
  - macOS: Cmd+Shift+R (requires Accessibility permissions)
  - Linux: Ctrl+Shift+R (requires xclip/xsel)
- **Text Selection**: Platform-specific implementation
  - macOS: Uses AppleScript for selected text
  - Linux: Uses xclip/xsel for primary selection and clipboard
- **Voice Detection**: Improved cross-platform voice handling
  - macOS: Uses native `say` command for voice list
  - Linux: Falls back to pyttsx3 voice detection

### Fixed
- Window icon now properly displays on all platforms
- Status bar messages now show correct hotkey for each platform
- About dialog updated with Linux-specific instructions

### Documentation
- Added `LINUX_COMPATIBILITY.md` with detailed Linux setup guide
- Updated README with cross-platform information
- Added version number to About dialog

## [1.0] - Initial Release

### Features
- Text-to-speech with pyttsx3 and macOS native `say` command
- Word highlighting during playback
- Voice selection (US English voices on macOS)
- Adjustable speech speed (50-300 WPM)
- Global hotkey for reading selected text (macOS only)
- Clean, minimalistic PyQt6 GUI
- macOS app bundle for easy launching

