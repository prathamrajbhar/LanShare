import os
import shutil
import subprocess
from pathlib import Path

def create_deb():
    app_name = "lanshare"
    version = "1.0.0"
    pkg_dir = Path(f"build/{app_name}_{version}")
    
    # 1. Clean previous build
    if pkg_dir.exists():
        shutil.rmtree(pkg_dir)
    
    # 2. Create directory structure
    (pkg_dir / "DEBIAN").mkdir(parents=True)
    (pkg_dir / "usr/bin").mkdir(parents=True)
    (pkg_dir / "usr/share/applications").mkdir(parents=True)
    (pkg_dir / "usr/share/pixmaps").mkdir(parents=True)
    
    # 3. Create control file
    control_content = f"""Package: {app_name}
Version: {version}
Section: utils
Priority: optional
Architecture: amd64
Maintainer: Pratham <pratham@example.com>
Description: LanShare file sharing application
 A simple, cross-platform LAN file sharing application built with Python.
"""
    with open(pkg_dir / "DEBIAN/control", "w") as f:
        f.write(control_content)
    
    # 4. Copy executable (Assuming dist/LanShare exists from build.py)
    executable_src = Path("dist/LanShare")
    if not executable_src.exists():
        print("Error: Standalone executable not found in dist/. Please run scripts/build.py first.")
        return
        
    shutil.copy2(executable_src, pkg_dir / "usr/bin/lanshare")
    os.chmod(pkg_dir / "usr/bin/lanshare", 0o755)
    
    # 5. Create .desktop file
    desktop_content = f"""[Desktop Entry]
Name=LanShare
Exec=lanshare
Icon=lanshare
Type=Application
Categories=Network;Utility;
Terminal=false
Comment=Peer-to-peer LAN file sharing
"""
    with open(pkg_dir / f"usr/share/applications/{app_name}.desktop", "w") as f:
        f.write(desktop_content)
        
    # 6. Copy icon
    icon_src = Path("assets/icon.png")
    if icon_src.exists():
        shutil.copy2(icon_src, pkg_dir / f"usr/share/pixmaps/{app_name}.png")
        
    # 7. Build .deb
    print(f"Building debian package: {app_name}_{version}.deb")
    subprocess.check_call(["dpkg-deb", "--build", str(pkg_dir)])
    
    # 8. Move .deb to dist
    (Path("dist")).mkdir(exist_ok=True)
    shutil.move(f"build/{app_name}_{version}.deb", f"dist/{app_name}_{version}.deb")
    print(f"SUCCESS: dist/{app_name}_{version}.deb created.")

if __name__ == "__main__":
    # Ensure in root
    os.chdir(Path(__file__).parent.parent)
    create_deb()
