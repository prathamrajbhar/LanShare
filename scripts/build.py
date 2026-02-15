import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path

def get_customtkinter_path():
    import customtkinter
    return os.path.dirname(customtkinter.__file__)

def build():
    # 1. Install requirements
    print("Checking dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    ctk_path = get_customtkinter_path()
    sep = os.pathsep
    
    # 2. Prepare PyInstaller command
    entry_point = "main.py"
    app_name = "LanShare"
    
    # CustomTKinter needs its assets included
    # The format is: path_to_src;destination_folder_in_exe
    # On Linux/Unix, use : instead of ; for separator
    add_data = f"{ctk_path}{sep}customtkinter"
    
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        f"--name={app_name}",
        f"--add-data={add_data}",
        entry_point
    ]
    
    # 3. Add icon if exists
    icon_path = Path("assets/icon.ico") if platform.system() == "Windows" else Path("assets/icon.png")
    if icon_path.exists():
        cmd.append(f"--icon={icon_path}")
    
    print(f"Running command: {' '.join(cmd)}")
    
    # 4. Run PyInstaller
    try:
        subprocess.check_call(cmd)
        print("\n" + "="*50)
        print(f"SUCCESS: {app_name} executable has been created in the 'dist' folder.")
        print("="*50)
    except subprocess.CalledProcessError as e:
        print(f"Error during build: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Ensure we are in the project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    build()
