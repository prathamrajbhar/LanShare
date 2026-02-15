import customtkinter as ctk
import sys
import os

# Ensure import paths are handled correctly if running directly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ui.main_window import MainWindow

def main():
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.configure(fg_color="#1e1e2e")
    app = MainWindow(root)

    root.protocol("WM_DELETE_WINDOW", root.quit)
    root.mainloop()

if __name__ == "__main__":
    main()
