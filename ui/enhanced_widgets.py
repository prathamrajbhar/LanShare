"""
Enhanced UI widgets for LanShare application.
Provides improved user experience with history, auto-completion, and responsiveness.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import os
from pathlib import Path
from typing import List, Callable, Optional
import time
from utils.config import config, ConnectionEntry, FolderEntry


class RecentConnectionsDropdown(ctk.CTkFrame):
    """Dropdown widget for recent connections with management options."""
    
    def __init__(self, master, on_select_callback: Optional[Callable] = None, **kwargs):
        super().__init__(master, **kwargs)
        self.on_select_callback = on_select_callback
        self.connections = config.get_recent_connections()
        self._build_ui()
    
    def _build_ui(self):
        # Main input row
        input_frame = ctk.CTkFrame(self, fg_color="transparent")
        input_frame.pack(fill="x", padx=4, pady=2)
        
        # IP Entry with label
        ip_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        ip_frame.pack(side="left", fill="x", expand=True)
        
        ctk.CTkLabel(ip_frame, text="IP Address:", font=("Segoe UI", 11), 
                     text_color="#9090a0").pack(anchor="w")
        self.ip_var = ctk.StringVar()
        self.ip_entry = ctk.CTkEntry(ip_frame, textvariable=self.ip_var,
                                     placeholder_text="192.168.x.x",
                                     font=("Segoe UI", 12), height=32)
        self.ip_entry.pack(fill="x", pady=(2, 0))
        
        # Port Entry with label
        port_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        port_frame.pack(side="left", padx=(12, 0))
        
        ctk.CTkLabel(port_frame, text="Port:", font=("Segoe UI", 11), 
                     text_color="#9090a0").pack(anchor="w")
        self.port_var = ctk.StringVar(value=config.settings.default_port)
        self.port_entry = ctk.CTkEntry(port_frame, textvariable=self.port_var,
                                       width=80, font=("Segoe UI", 12), height=32)
        self.port_entry.pack(pady=(2, 0))

        # ── Suggestions Popup (Hidden by default) ──
        self.suggestions_frame = ctk.CTkFrame(self, fg_color="#2b2b3d", corner_radius=8, 
                                             border_width=1, border_color="#3a3a50")
        # Do not pack yet

        self.suggestions_scroll = ctk.CTkScrollableFrame(self.suggestions_frame, height=0, fg_color="transparent")
        self.suggestions_scroll.pack(fill="both", expand=True, padx=4, pady=4)

        # Bindings for search-as-you-type
        self.ip_entry.bind("<KeyRelease>", lambda e: self._update_suggestions())
        self.ip_entry.bind("<FocusIn>", lambda e: self._update_suggestions())
        
        # Global click binding to hide suggestions (handled via master)
        self.master.bind("<Button-1>", self._check_hide_suggestions, add="+")

    def _update_suggestions(self):
        """Filter and show suggestions based on current input."""
        query = self.ip_var.get().strip().lower()
        
        # Filter connections
        filtered = [c for c in self.connections if query in c.ip.lower()]
        
        # Clear old items
        for w in self.suggestions_scroll.winfo_children():
            w.destroy()
            
        if not filtered or (len(filtered) == 1 and filtered[0].ip == query):
            self.suggestions_frame.pack_forget()
            return

        # Limit to 5 results to keep it compact
        for conn in filtered[:5]:
            self._create_suggestion_item(self.suggestions_scroll, conn)
            
        # Update frame size and show
        height = min(160, len(filtered[:5]) * 40)
        self.suggestions_scroll.configure(height=height)
        self.suggestions_frame.pack(fill="x", padx=4, pady=(4, 0))

    def _create_suggestion_item(self, parent, connection: ConnectionEntry):
        """Create a suggestion item that fills values when clicked."""
        item = ctk.CTkFrame(parent, fg_color="#35354a", corner_radius=6, cursor="hand2", height=34)
        item.pack(fill="x", pady=1)
        item.pack_propagate(False)
        
        def on_click(e=None):
            self.ip_var.set(connection.ip)
            self.port_var.set(connection.port)
            self.suggestions_frame.pack_forget()
            if self.on_select_callback:
                self.on_select_callback()
        
        item.bind("<Button-1>", on_click)
        
        lbl = ctk.CTkLabel(item, text=f"🕒 {connection.ip}:{connection.port}", 
                           font=("Segoe UI", 12), text_color="#e4e4e8", anchor="w")
        lbl.pack(side="left", padx=10, fill="x", expand=True)
        lbl.bind("<Button-1>", on_click)

        # Hover
        item.bind("<Enter>", lambda e: item.configure(fg_color="#404050"))
        item.bind("<Leave>", lambda e: item.configure(fg_color="#35354a"))

    def _check_hide_suggestions(self, event):
        """Hide suggestions if clicked outside the entry or frame."""
        if not self.suggestions_frame.winfo_ismapped():
            return
            
        x, y = event.x_root, event.y_root
        
        # Check if click is within entry or suggestions frame
        for w in [self.ip_entry, self.suggestions_frame]:
            if (w.winfo_rootx() <= x <= w.winfo_rootx() + w.winfo_width() and
                w.winfo_rooty() <= y <= w.winfo_rooty() + w.winfo_height()):
                return
                
        self.suggestions_frame.pack_forget()

    def get_ip(self) -> str:
        return self.ip_var.get().strip()
    
    def get_port(self) -> str:
        return self.port_var.get().strip()
    
    def set_values(self, ip: str, port: str):
        self.ip_var.set(ip)
        self.port_var.set(port)


class ImprovedFolderSelector(ctk.CTkFrame):
    """Enhanced folder selector with recent folders and favorites."""
    
    def __init__(self, master, on_select_callback: Optional[Callable] = None, **kwargs):
        super().__init__(master, **kwargs)
        self.on_select_callback = on_select_callback
        self.recent_folders = config.get_recent_folders()
        self.selected_path = ctk.StringVar()
        self.selected_path.trace('w', self._on_path_change)
        self._build_ui()
    
    def _build_ui(self):
        # Path input section
        input_frame = ctk.CTkFrame(self, fg_color="transparent")
        input_frame.pack(fill="x", padx=4, pady=2)
        
        ctk.CTkLabel(input_frame, text="Selected Folder:", font=("Segoe UI", 11),
                     text_color="#9090a0").pack(anchor="w")
        
        path_row = ctk.CTkFrame(input_frame, fg_color="transparent")
        path_row.pack(fill="x", pady=(2, 0))
        
        self.path_entry = ctk.CTkEntry(path_row, textvariable=self.selected_path,
                                       font=("Segoe UI", 12), height=32,
                                       placeholder_text="Click Browse or select from recent folders")
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        
        self.browse_btn = ctk.CTkButton(path_row, text="Browse...", 
                                        command=self._browse_folder,
                                        width=100, height=32, corner_radius=6)
        self.browse_btn.pack(side="right")
        
        # Folder info
        self.info_label = ctk.CTkLabel(input_frame, text="", font=("Segoe UI", 10),
                                       text_color="#6c6c80")
        self.info_label.pack(anchor="w", pady=(4, 0))
        
        # Recent folders section
        if self.recent_folders:
            recent_frame = ctk.CTkFrame(self, fg_color="#2b2b3d", corner_radius=8)
            recent_frame.pack(fill="both", expand=True, padx=4, pady=(8, 4))
            
            header_frame = ctk.CTkFrame(recent_frame, fg_color="transparent")
            header_frame.pack(fill="x", padx=12, pady=(8, 4))
            
            ctk.CTkLabel(header_frame, text="Recent Folders:", 
                         font=("Segoe UI Semibold", 11), text_color="#e4e4e8").pack(side="left")
            
            clear_btn = ctk.CTkButton(header_frame, text="Clear", command=self._clear_history,
                                      width=60, height=24, corner_radius=4,
                                      fg_color="transparent", text_color="#9090a0",
                                      hover_color="#35354a", font=("Segoe UI", 9))
            clear_btn.pack(side="right")
            
            # Scrollable frame for folders
            max_height = min(200, len(self.recent_folders) * 45)
            self.recent_scroll = ctk.CTkScrollableFrame(recent_frame, height=max_height)
            self.recent_scroll.pack(fill="both", expand=True, padx=8, pady=(0, 8))
            
            for folder in self.recent_folders[:10]:  # Show up to 10 recent folders
                if os.path.exists(folder.path):  # Only show existing folders
                    self._create_folder_item(self.recent_scroll, folder)
    
    def _create_folder_item(self, parent, folder: FolderEntry):
        """Create a single folder item widget."""
        item_frame = ctk.CTkFrame(parent, fg_color="transparent", height=40)
        item_frame.pack(fill="x", pady=1)
        item_frame.pack_propagate(False)
        
        # Folder button (clickable area)
        btn_frame = ctk.CTkFrame(item_frame, fg_color="#35354a", corner_radius=6, 
                                 cursor="hand2")
        btn_frame.pack(fill="both", expand=True, padx=2, pady=1)
        
        # Bind click events
        def on_click(event=None):
            self.selected_path.set(folder.path)
        
        btn_frame.bind("<Button-1>", on_click)
        
        # Folder info
        info_frame = ctk.CTkFrame(btn_frame, fg_color="transparent")
        info_frame.pack(fill="both", expand=True, padx=8, pady=4)
        info_frame.bind("<Button-1>", on_click)
        
        # Folder icon and name
        name_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        name_frame.pack(fill="x")
        name_frame.bind("<Button-1>", on_click)
        
        icon_label = ctk.CTkLabel(name_frame, text="📁", font=("Segoe UI", 14))
        icon_label.pack(side="left", padx=(0, 8))
        icon_label.bind("<Button-1>", on_click)
        
        name_label = ctk.CTkLabel(name_frame, text=folder.name,
                                  font=("Segoe UI Semibold", 12), text_color="#e4e4e8",
                                  anchor="w")
        name_label.pack(side="left", fill="x", expand=True)
        name_label.bind("<Button-1>", on_click)
        
        # Time and size info
        time_ago = self._format_time_ago(folder.last_used)
        if folder.file_count > 0:
            size_text = self._format_size(folder.total_size)
            detail_text = f"{folder.file_count} files • {size_text} • {time_ago}"
        else:
            detail_text = f"{time_ago}"
        
        detail_label = ctk.CTkLabel(info_frame, text=detail_text,
                                    font=("Segoe UI", 10), text_color="#9090a0",
                                    anchor="w")
        detail_label.pack(fill="x", pady=(2, 0))
        detail_label.bind("<Button-1>", on_click)
        
        # Path label (truncated)
        path_text = self._truncate_path(folder.path, 60)
        path_label = ctk.CTkLabel(info_frame, text=path_text,
                                  font=("Consolas", 9), text_color="#6c6c80",
                                  anchor="w")
        path_label.pack(fill="x")
        path_label.bind("<Button-1>", on_click)
        
        # Hover effects
        def on_enter(event):
            btn_frame.configure(fg_color="#404050")
        
        def on_leave(event):
            btn_frame.configure(fg_color="#35354a")
        
        for widget in [btn_frame, info_frame, name_frame, icon_label, name_label, 
                       detail_label, path_label]:
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)
    
    def _browse_folder(self):
        """Open folder browser dialog."""
        from tkinter import filedialog
        folder = filedialog.askdirectory(title="Select Folder to Share")
        if folder:
            self.selected_path.set(folder)
    
    def _clear_history(self):
        """Clear folder history after confirmation."""
        if messagebox.askyesno("Clear History", 
                              "Are you sure you want to clear the folder history?"):
            config.clear_folder_history()
            # Rebuild UI
            for widget in self.winfo_children():
                widget.destroy()
            self.recent_folders = []
            self._build_ui()
    
    def _on_path_change(self, *args):
        """Handle path change to update info and call callback."""
        path = self.selected_path.get()
        if path and os.path.exists(path):
            # Update info asynchronously
            import threading
            threading.Thread(target=self._update_folder_info, args=(path,), daemon=True).start()
            
            if self.on_select_callback:
                self.on_select_callback(path)
        else:
            self.info_label.configure(text="")
    
    def _update_folder_info(self, path: str):
        """Update folder information display."""
        try:
            folder_path = Path(path)
            file_count = sum(1 for f in folder_path.rglob('*') if f.is_file())
            total_size = sum(f.stat().st_size for f in folder_path.rglob('*') if f.is_file())
            size_text = self._format_size(total_size)
            
            info_text = f"📂 {folder_path.name} — {file_count} files — {size_text}"
            
            # Update UI in main thread
            self.after(0, lambda: self.info_label.configure(text=info_text))
        except Exception:
            self.after(0, lambda: self.info_label.configure(text="📂 Ready to share"))
    
    def _format_time_ago(self, timestamp: float) -> str:
        """Format timestamp as 'time ago' string."""
        now = time.time()
        diff = now - timestamp
        
        if diff < 60:
            return "Just now"
        elif diff < 3600:
            minutes = int(diff // 60)
            return f"{minutes}m ago"
        elif diff < 86400:
            hours = int(diff // 3600)
            return f"{hours}h ago"
        else:
            days = int(diff // 86400)
            return f"{days}d ago"
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format."""
        if size_bytes == 0:
            return "0 B"
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}" if unit != 'B' else f"{int(size_bytes)} B"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
    
    def _truncate_path(self, path: str, max_length: int) -> str:
        """Truncate path to fit within max_length."""
        if len(path) <= max_length:
            return path
        
        # Try to keep the end of the path visible
        return "..." + path[-(max_length-3):]
    
    def get_path(self) -> str:
        return self.selected_path.get()
    
    def set_path(self, path: str):
        self.selected_path.set(path)


class StatusProgressBar(ctk.CTkFrame):
    """Enhanced status and progress indicator with better information display."""
    
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self._build_ui()
        self._reset()
    
    def _build_ui(self):
        # Status text
        self.status_label = ctk.CTkLabel(self, text="Ready", 
                                         font=("Segoe UI", 12), text_color="#9090a0")
        self.status_label.pack(anchor="w", padx=8, pady=(8, 4))
        
        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(self, height=8, corner_radius=4)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", padx=8, pady=(0, 4))
        
        # Details row
        details_frame = ctk.CTkFrame(self, fg_color="transparent")
        details_frame.pack(fill="x", padx=8, pady=(0, 8))
        
        self.detail_label = ctk.CTkLabel(details_frame, text="", 
                                         font=("Segoe UI", 10), text_color="#6c6c80")
        self.detail_label.pack(side="left")
        
        self.percent_label = ctk.CTkLabel(details_frame, text="", 
                                          font=("Segoe UI", 10), text_color="#0078d4")
        self.percent_label.pack(side="right")
    
    def _reset(self):
        """Reset to default state."""
        self.status_label.configure(text="Ready")
        self.detail_label.configure(text="")
        self.percent_label.configure(text="")
        self.progress_bar.set(0)
    
    def set_status(self, text: str, progress: float = None, details: str = ""):
        """Set status text and optional progress."""
        self.status_label.configure(text=text)
        self.detail_label.configure(text=details)
        
        if progress is not None:
            self.progress_bar.set(progress)
            self.percent_label.configure(text=f"{int(progress * 100)}%")
        else:
            self.percent_label.configure(text="")
    
    def set_progress(self, current: int, total: int, item_name: str = ""):
        """Set progress with current/total values."""
        if total == 0:
            progress = 0
        else:
            progress = current / total
        
        self.progress_bar.set(progress)
        self.percent_label.configure(text=f"{int(progress * 100)}%")
        
        if item_name:
            self.detail_label.configure(text=f"Processing: {item_name}")
        else:
            self.detail_label.configure(text=f"{current} / {total}")
    
    def reset(self):
        """Reset to default state."""
        self._reset()