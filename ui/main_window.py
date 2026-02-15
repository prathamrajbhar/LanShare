import customtkinter as ctk
from ui.sender_ui import SenderUI
from ui.receiver_ui import ReceiverUI
from utils.config import config


# ─── Color Palette (Windows 11 inspired) ────────────────────────────────
COLORS = {
    "bg_dark":       "#1e1e2e",
    "bg_card":       "#2b2b3d",
    "bg_sidebar":    "#252536",
    "bg_hover":      "#35354a",
    "accent":        "#0078d4",
    "accent_hover":  "#1a8cff",
    "accent_light":  "#3399ff",
    "text_primary":  "#e4e4e8",
    "text_secondary":"#9090a0",
    "text_dim":      "#6c6c80",
    "success":       "#2ecc71",
    "danger":        "#e74c3c",
    "danger_hover":  "#c0392b",
    "border":        "#3a3a50",
    "white":         "#ffffff",
}


class MainMenu(ctk.CTkFrame):
    def __init__(self, master, switch_callback):
        super().__init__(master, fg_color=COLORS["bg_dark"], corner_radius=0)
        self.switch_callback = switch_callback
        self.pack(fill="both", expand=True)
        self._build()

    def _build(self):
        # ── Center container ──
        center = ctk.CTkFrame(self, fg_color="transparent")
        center.place(relx=0.5, rely=0.45, anchor="center")

        # App icon area
        icon_frame = ctk.CTkFrame(center, fg_color=COLORS["accent"], corner_radius=20,
                                   width=80, height=80)
        icon_frame.pack(pady=(0, 20))
        icon_frame.pack_propagate(False)
        ctk.CTkLabel(icon_frame, text="📁", font=("Segoe UI", 36),
                     text_color=COLORS["white"]).place(relx=0.5, rely=0.5, anchor="center")

        # Title
        ctk.CTkLabel(center, text="LAN Share", font=("Segoe UI Semibold", 36),
                     text_color=COLORS["white"]).pack(pady=(0, 4))
        ctk.CTkLabel(center, text="Fast & simple local file transfer",
                     font=("Segoe UI", 13), text_color=COLORS["text_secondary"]).pack(pady=(0, 40))

        # ── Cards ──
        cards = ctk.CTkFrame(center, fg_color="transparent")
        cards.pack()

        self._make_card(cards, "📤", "Send Files",
                        "Share a folder over your\nlocal network",
                        lambda: self.switch_callback("sender")).pack(side="left", padx=12)

        self._make_card(cards, "📥", "Receive Files",
                        "Download files from a\nsender on the network",
                        lambda: self.switch_callback("receiver")).pack(side="left", padx=12)

        # Footer
        footer = ctk.CTkFrame(self, fg_color="transparent", height=40)
        footer.pack(side="bottom", fill="x", pady=10)
        ctk.CTkLabel(footer, text="v2.0.0  •  Windows-style UI",
                     font=("Segoe UI", 11), text_color=COLORS["text_dim"]).pack()

    def _make_card(self, parent, icon, title, desc, command):
        card = ctk.CTkFrame(parent, fg_color=COLORS["bg_card"], corner_radius=16,
                            width=220, height=220, border_width=1, border_color=COLORS["border"])
        card.pack_propagate(False)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(inner, text=icon, font=("Segoe UI", 40)).pack(pady=(0, 8))
        ctk.CTkLabel(inner, text=title, font=("Segoe UI Semibold", 17),
                     text_color=COLORS["white"]).pack(pady=(0, 6))
        ctk.CTkLabel(inner, text=desc, font=("Segoe UI", 11),
                     text_color=COLORS["text_secondary"], justify="center").pack(pady=(0, 14))
        ctk.CTkButton(inner, text="Open →", command=command,
                      font=("Segoe UI Semibold", 12), fg_color=COLORS["accent"],
                      hover_color=COLORS["accent_hover"], corner_radius=8,
                      width=120, height=34).pack()
        return card


class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("LAN Share")
        
        # Use saved window size or defaults
        width = config.settings.window_width
        height = config.settings.window_height
        self.root.geometry(f"{width}x{height}")
        self.root.minsize(700, 500)  # More flexible minimum size
        self.root.configure(fg_color=COLORS["bg_dark"])
        
        # Save window size on close
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Track window resize for auto-saving
        self.root.bind("<Configure>", self._on_configure)
        self._last_size_save = 0

        self.current_frame = None
        self.switch_frame("main")

    def switch_frame(self, frame_name):
        if self.current_frame:
            self.current_frame.destroy()
            self.current_frame = None

        if frame_name == "main":
            # Don't force resize for main menu if auto-resize is enabled
            if not config.settings.auto_resize:
                self.root.geometry(f"{config.settings.window_width}x{config.settings.window_height}")
            self.current_frame = MainMenu(self.root, self.switch_frame)
        elif frame_name == "sender":
            # Allow natural sizing for sender UI
            if not config.settings.auto_resize:
                self.root.geometry("820x650")
            self.current_frame = SenderUI(self.root, self.switch_frame)
            self.current_frame.pack(fill="both", expand=True)
        elif frame_name == "receiver":
            # Allow natural sizing for receiver UI
            if not config.settings.auto_resize:
                self.root.geometry("920x720")
            self.current_frame = ReceiverUI(self.root, self.switch_frame)
            self.current_frame.pack(fill="both", expand=True)
    
    def _on_configure(self, event):
        """Handle window resize events to save size."""
        if event.widget == self.root and config.settings.auto_resize:
            # Debounce resize events to avoid too frequent saves
            import time
            current_time = time.time()
            if current_time - self._last_size_save > 0.5:
                self._last_size_save = current_time
                self.root.after(500, self._save_window_size)  # Delay to batch resize events
    
    def _save_window_size(self):
        """Save current window size to config."""
        try:
            width = self.root.winfo_width()
            height = self.root.winfo_height()
            if width > 100 and height > 100:  # Sanity check
                config.update_window_size(width, height)
        except:
            pass
    
    def _on_closing(self):
        """Handle application closing."""
        # Save final window size
        self._save_window_size()
        self.root.quit()
