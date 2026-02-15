import customtkinter as ctk
from tkinter import filedialog, messagebox
import os
import threading
from pathlib import Path
from network.server import HTTPServerManager
from utils.ip_utils import get_local_ip
from utils.performance import fs_optimizer, global_cache
from utils.config import config
from ui.enhanced_widgets import ImprovedFolderSelector


# ─── Color Palette (Windows 11 inspired) ────────────────────────────────
C = {
    "bg":           "#1e1e2e",
    "card":         "#2b2b3d",
    "sidebar":      "#252536",
    "hover":        "#35354a",
    "accent":       "#0078d4",
    "accent_hover": "#1a8cff",
    "text":         "#e4e4e8",
    "text2":        "#9090a0",
    "text_dim":     "#6c6c80",
    "success":      "#2ecc71",
    "danger":       "#e74c3c",
    "danger_hover": "#c0392b",
    "border":       "#3a3a50",
    "white":        "#ffffff",
    "input_bg":     "#333348",
}


class SenderUI(ctk.CTkFrame):
    def __init__(self, master, switch_callback):
        super().__init__(master, fg_color=C["bg"], corner_radius=0)
        self.switch_callback = switch_callback
        self.server_manager = None
        self.is_running = False
        self.folder_path_var = ctk.StringVar()
        self.port_var = ctk.StringVar(value=config.settings.default_port)
        self._build()

    def _build(self):
        # ── Top bar ──
        topbar = ctk.CTkFrame(self, fg_color=C["sidebar"], corner_radius=0, height=56)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)

        ctk.CTkButton(topbar, text="←  Back", command=self._go_back,
                      fg_color="transparent", hover_color=C["hover"],
                      font=("Segoe UI", 13), width=80, anchor="w",
                      text_color=C["text2"]).pack(side="left", padx=16, pady=10)

        ctk.CTkLabel(topbar, text="📤  Sender Mode", font=("Segoe UI Semibold", 18),
                     text_color=C["white"]).pack(side="left", padx=8)

        # ── Main content ──
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=40, pady=24)

        # Folder selection card
        folder_card = ctk.CTkFrame(content, fg_color=C["card"], corner_radius=12,
                                    border_width=1, border_color=C["border"])
        folder_card.pack(fill="both", expand=True, pady=(0, 16))

        fc_inner = ctk.CTkFrame(folder_card, fg_color="transparent")
        fc_inner.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(fc_inner, text="Folder to Share",
                     font=("Segoe UI Semibold", 14), text_color=C["text"]).pack(anchor="w")
        ctk.CTkLabel(fc_inner, text="Select the folder you want to share on the network",
                     font=("Segoe UI", 11), text_color=C["text_dim"]).pack(anchor="w", pady=(2, 8))

        # Use enhanced folder selector
        self.folder_selector = ImprovedFolderSelector(fc_inner, 
                                                      on_select_callback=self._on_folder_selected)
        self.folder_selector.pack(fill="both", expand=True)

        # Settings card
        settings_card = ctk.CTkFrame(content, fg_color=C["card"], corner_radius=12,
                                      border_width=1, border_color=C["border"])
        settings_card.pack(fill="x", pady=(0, 16))

        sc_inner = ctk.CTkFrame(settings_card, fg_color="transparent")
        sc_inner.pack(fill="x", padx=16, pady=12)  # Reduced padding

        ctk.CTkLabel(sc_inner, text="Server Settings",
                     font=("Segoe UI Semibold", 14), text_color=C["text"]).pack(anchor="w")

        settings_row = ctk.CTkFrame(sc_inner, fg_color="transparent")
        settings_row.pack(fill="x", pady=(8, 0))

        # Port setting
        port_frame = ctk.CTkFrame(settings_row, fg_color="transparent")
        port_frame.pack(side="left")
        
        ctk.CTkLabel(port_frame, text="Port:", font=("Segoe UI", 12),
                     text_color=C["text2"]).pack(side="left")
        ctk.CTkEntry(port_frame, textvariable=self.port_var, width=90,
                     font=("Segoe UI", 12), fg_color=C["input_bg"],
                     border_color=C["border"], corner_radius=8,
                     height=32).pack(side="left", padx=(6, 0))
        
        # Add settings button
        settings_btn = ctk.CTkButton(settings_row, text="⚙️", width=32, height=32,
                                     command=self._show_settings,
                                     fg_color="transparent", text_color=C["text2"],
                                     hover_color=C["hover"])
        settings_btn.pack(side="right")

        # Server status card (initially hidden)
        self.status_card = ctk.CTkFrame(content, fg_color=C["card"], corner_radius=12,
                                         border_width=1, border_color=C["border"])

        self.status_inner = ctk.CTkFrame(self.status_card, fg_color="transparent")
        self.status_inner.pack(fill="x", padx=20, pady=16)

        self.status_icon = ctk.CTkLabel(self.status_inner, text="🟢  Server Running",
                                         font=("Segoe UI Semibold", 14),
                                         text_color=C["success"])
        self.status_icon.pack(anchor="w")

        info_box = ctk.CTkFrame(self.status_inner, fg_color=C["input_bg"], corner_radius=8)
        info_box.pack(fill="x", pady=(10, 0))

        self.ip_label = ctk.CTkLabel(info_box, text="", font=("Consolas", 13),
                                      text_color=C["accent"])
        self.ip_label.pack(anchor="w", padx=14, pady=(10, 2))

        self.url_label = ctk.CTkLabel(info_box, text="", font=("Consolas", 13),
                                       text_color=C["success"])
        self.url_label.pack(anchor="w", padx=14, pady=(2, 4))

        self.share_info = ctk.CTkLabel(info_box, text="", font=("Segoe UI", 11),
                                        text_color=C["text_dim"])
        self.share_info.pack(anchor="w", padx=14, pady=(0, 10))

        # ── Bottom action bar ──
        bottom = ctk.CTkFrame(self, fg_color=C["sidebar"], corner_radius=0, height=64)
        bottom.pack(fill="x", side="bottom")
        bottom.pack_propagate(False)

        btn_row = ctk.CTkFrame(bottom, fg_color="transparent")
        btn_row.pack(expand=True)

        self.start_btn = ctk.CTkButton(
            btn_row, text="▶  Start Server", command=self._toggle_server,
            font=("Segoe UI Semibold", 13), fg_color=C["accent"],
            hover_color=C["accent_hover"], corner_radius=8,
            width=180, height=40)
        self.start_btn.pack(side="left", padx=8, pady=12)

    def _on_folder_selected(self, folder_path):
        """Handle folder selection from enhanced selector."""
        self.folder_path_var.set(folder_path)
        # Add to recent folders
        threading.Thread(target=self._add_to_recent_folders, 
                        args=(folder_path,), daemon=True).start()
    
    def _add_to_recent_folders(self, folder_path):
        """Add folder to recent folders with file count and size."""
        try:
            path = Path(folder_path)
            file_count = sum(1 for f in path.rglob('*') if f.is_file())
            total_size = sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
            config.add_folder(folder_path, file_count, total_size)
        except:
            config.add_folder(folder_path)
    
    def _show_settings(self):
        """Show advanced settings dialog."""
        # This could open a settings dialog in the future
        messagebox.showinfo("Settings", "Advanced settings will be available in a future update.")



    def _go_back(self):
        if self.is_running:
            if messagebox.askyesno("Server Running",
                                   "Stop the server and go back?"):
                self._stop_server()
            else:
                return
        self.switch_callback("main")

    def _toggle_server(self):
        if not self.is_running:
            self._start_server()
        else:
            self._stop_server()

    def _start_server(self):
        folder = self.folder_selector.get_path()
        if not folder:
            messagebox.showerror("Error", "Please select a folder to share.")
            return
        if not os.path.isdir(folder):
            messagebox.showerror("Error", "Selected path is not a valid folder.")
            return
        try:
            port = int(self.port_var.get())
        except ValueError:
            messagebox.showerror("Error", "Port must be a valid number.")
            return

        self.server_manager = HTTPServerManager(folder, port)
        ip = get_local_ip()

        success, msg = self.server_manager.start_server(ip)
        if success:
            self.is_running = True
            self.start_btn.configure(text="■  Stop Server",
                                     fg_color=C["danger"],
                                     hover_color=C["danger_hover"])
            self.ip_label.configure(text=f"Local IP:     {ip}")
            self.url_label.configure(text=f"Share URL:    http://{ip}:{port}")
            self.share_info.configure(
                text="Share the IP and port with the receiver to connect")
            self.status_card.pack(fill="x", pady=(0, 16),
                                  after=self.status_card.master.winfo_children()[1])
        else:
            messagebox.showerror("Error", msg)

    def _stop_server(self):
        if self.server_manager:
            self.server_manager.stop_server()
            self.server_manager = None
        
        # Clear performance cache
        global_cache.clear()
        
        self.is_running = False
        self.start_btn.configure(text="▶  Start Server",
                                 fg_color=C["accent"],
                                 hover_color=C["accent_hover"])
        self.status_card.pack_forget()
