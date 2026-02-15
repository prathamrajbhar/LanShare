from PIL import Image
import os
import shutil
from pathlib import Path

def prepare_assets(img_path):
    assets_dir = Path("assets")
    assets_dir.mkdir(exist_ok=True)
    
    # Target paths
    png_path = assets_dir / "icon.png"
    ico_path = assets_dir / "icon.ico"
    
    # Copy generated image to assets as icon.png
    shutil.copy(img_path, png_path)
    print(f"Copied {img_path} to {png_path}")
    
    # Convert to .ico for Windows
    try:
        img = Image.open(png_path)
        # Use multiple sizes for better quality icon
        icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
        img.save(ico_path, format='ICO', sizes=icon_sizes)
        print(f"Created {ico_path}")
    except Exception as e:
        print(f"Error creating .ico: {e}")

if __name__ == "__main__":
    # Find the generated image (it's the only png in the artifact dir usually, 
    # but I'll pass the path from the thought process)
    import sys
    if len(sys.argv) > 1:
        prepare_assets(sys.argv[1])
    else:
        print("Please provide the path to the generated image.")
