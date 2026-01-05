#!/usr/bin/env python3
"""
Create desktop shortcut for ReadAnything on Linux
"""

import os
import sys
import platform
from pathlib import Path

def create_desktop_shortcut():
    """Create a desktop shortcut for ReadAnything"""
    
    if platform.system() != 'Linux':
        print("This script is for Linux only. On macOS, use ReadAnything.app")
        return False
    
    # Get the project directory (where this script is located)
    script_dir = Path(__file__).parent.absolute()
    project_dir = script_dir
    
    # Find paths
    venv_python = project_dir / 'venv' / 'bin' / 'python3'
    main_script = project_dir / 'main.py'
    icon_path = project_dir / 'logo_128.png'
    
    # Check if venv exists
    if not venv_python.exists():
        print("Error: Virtual environment not found!")
        print(f"Expected: {venv_python}")
        print("\nPlease create a virtual environment first:")
        print("  python3 -m venv venv")
        print("  source venv/bin/activate")
        print("  pip install -r requirements.txt")
        return False
    
    # Check if main.py exists
    if not main_script.exists():
        print(f"Error: main.py not found at {main_script}")
        return False
    
    # Desktop file content
    desktop_content = f"""[Desktop Entry]
Version=1.0
Type=Application
Name=ReadAnything
Comment=Text-to-Speech Application
Exec={venv_python} {main_script}
Icon={icon_path}
Terminal=false
Categories=AudioVideo;Audio;Utility;
StartupNotify=true
"""
    
    # Create .local/share/applications directory if it doesn't exist
    applications_dir = Path.home() / '.local' / 'share' / 'applications'
    applications_dir.mkdir(parents=True, exist_ok=True)
    
    # Write desktop file
    desktop_file = applications_dir / 'readanything.desktop'
    try:
        with open(desktop_file, 'w') as f:
            f.write(desktop_content)
        
        # Make it executable
        os.chmod(desktop_file, 0o755)
        
        print("✓ Desktop shortcut created successfully!")
        print(f"  Location: {desktop_file}")
        print("\nThe application should now appear in your applications menu.")
        print("You can also launch it by double-clicking the shortcut.")
        
        # Try to update desktop database
        try:
            import subprocess
            subprocess.run(['update-desktop-database', str(applications_dir)], 
                         check=False, timeout=5)
            print("✓ Desktop database updated")
        except Exception:
            pass  # Not critical if this fails
        
        return True
        
    except Exception as e:
        print(f"Error creating desktop shortcut: {e}")
        return False

if __name__ == "__main__":
    success = create_desktop_shortcut()
    sys.exit(0 if success else 1)

