"""
Configuration management for LanShare application.
Handles saving/loading user preferences, connection history, and app settings.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import time


@dataclass
class ConnectionEntry:
    """Represents a saved connection entry."""
    ip: str
    port: str
    name: str
    last_used: float
    success_count: int = 0
    total_attempts: int = 0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_attempts == 0:
            return 0.0
        return (self.success_count / self.total_attempts) * 100


@dataclass
class FolderEntry:
    """Represents a recently used folder."""
    path: str
    name: str
    last_used: float
    file_count: int = 0
    total_size: int = 0


@dataclass
class AppSettings:
    """Application settings and preferences."""
    # UI Settings
    window_width: int = 820
    window_height: int = 620
    auto_resize: bool = True
    theme: str = "dark"
    
    # Network Settings
    default_port: str = "8000"
    connection_timeout: int = 10
    download_timeout: int = 120
    max_parallel_downloads: int = 4
    resume_downloads: bool = True
    
    # Performance Settings
    cache_enabled: bool = True
    cache_ttl: int = 300
    chunk_size: int = 1024 * 1024  # 1MB
    use_compression: bool = True
    
    # Recent items limits
    max_recent_connections: int = 10
    max_recent_folders: int = 15
    
    # Default paths
    default_download_path: str = ""
    default_share_path: str = ""


class ConfigManager:
    """Manages application configuration, preferences, and history."""
    
    def __init__(self, app_name: str = "LanShare"):
        self.app_name = app_name
        self.config_dir = self._get_config_dir()
        self.config_file = self.config_dir / "config.json"
        self.connections_file = self.config_dir / "connections.json"
        self.folders_file = self.config_dir / "folders.json"
        
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Load or create default configuration
        self.settings = self._load_settings()
        self.recent_connections: List[ConnectionEntry] = self._load_connections()
        self.recent_folders: List[FolderEntry] = self._load_folders()
    
    def _get_config_dir(self) -> Path:
        """Get platform-specific configuration directory."""
        if os.name == 'nt':  # Windows
            base_dir = Path(os.environ.get('APPDATA', '~'))
        else:  # Linux/macOS
            base_dir = Path(os.environ.get('XDG_CONFIG_HOME', '~/.config'))
        
        return (base_dir / self.app_name).expanduser()
    
    def _load_settings(self) -> AppSettings:
        """Load settings from config file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return AppSettings(**data)
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
        
        # Return default settings if loading fails
        settings = AppSettings()
        
        # Set default download path to user's Downloads folder
        downloads_path = Path.home() / "Downloads"
        if downloads_path.exists():
            settings.default_download_path = str(downloads_path)
        
        return settings
    
    def _load_connections(self) -> List[ConnectionEntry]:
        """Load recent connections from file."""
        if self.connections_file.exists():
            try:
                with open(self.connections_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    connections = [ConnectionEntry(**item) for item in data]
                    # Sort by last used time (most recent first)
                    return sorted(connections, key=lambda x: x.last_used, reverse=True)
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
        return []
    
    def _load_folders(self) -> List[FolderEntry]:
        """Load recent folders from file."""
        if self.folders_file.exists():
            try:
                with open(self.folders_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    folders = [FolderEntry(**item) for item in data]
                    # Sort by last used time (most recent first)
                    return sorted(folders, key=lambda x: x.last_used, reverse=True)
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
        return []
    
    def save_settings(self) -> None:
        """Save current settings to file."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.settings), f, indent=2, ensure_ascii=False)
        except (IOError, OSError) as e:
            print(f"Failed to save settings: {e}")
    
    def save_connections(self) -> None:
        """Save recent connections to file."""
        try:
            # Limit to max recent connections
            connections_to_save = self.recent_connections[:self.settings.max_recent_connections]
            data = [asdict(conn) for conn in connections_to_save]
            
            with open(self.connections_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except (IOError, OSError) as e:
            print(f"Failed to save connections: {e}")
    
    def save_folders(self) -> None:
        """Save recent folders to file."""
        try:
            # Limit to max recent folders
            folders_to_save = self.recent_folders[:self.settings.max_recent_folders]
            data = [asdict(folder) for folder in folders_to_save]
            
            with open(self.folders_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except (IOError, OSError) as e:
            print(f"Failed to save folders: {e}")
    
    def add_connection(self, ip: str, port: str, name: str = "", success: bool = True) -> None:
        """Add or update a connection in history."""
        if not name:
            name = f"{ip}:{port}"
        
        current_time = time.time()
        
        # Check if connection already exists
        for conn in self.recent_connections:
            if conn.ip == ip and conn.port == port:
                conn.last_used = current_time
                conn.total_attempts += 1
                if success:
                    conn.success_count += 1
                # Move to front
                self.recent_connections.remove(conn)
                self.recent_connections.insert(0, conn)
                self.save_connections()
                return
        
        # Add new connection
        new_conn = ConnectionEntry(
            ip=ip,
            port=port,
            name=name,
            last_used=current_time,
            success_count=1 if success else 0,
            total_attempts=1
        )
        
        self.recent_connections.insert(0, new_conn)
        # Limit list size
        if len(self.recent_connections) > self.settings.max_recent_connections:
            self.recent_connections = self.recent_connections[:self.settings.max_recent_connections]
        
        self.save_connections()
    
    def add_folder(self, path: str, file_count: int = 0, total_size: int = 0) -> None:
        """Add or update a folder in history."""
        folder_path = Path(path)
        if not folder_path.exists():
            return
        
        name = folder_path.name
        current_time = time.time()
        
        # Check if folder already exists
        for folder in self.recent_folders:
            if folder.path == path:
                folder.last_used = current_time
                folder.file_count = file_count
                folder.total_size = total_size
                # Move to front
                self.recent_folders.remove(folder)
                self.recent_folders.insert(0, folder)
                self.save_folders()
                return
        
        # Add new folder
        new_folder = FolderEntry(
            path=path,
            name=name,
            last_used=current_time,
            file_count=file_count,
            total_size=total_size
        )
        
        self.recent_folders.insert(0, new_folder)
        # Limit list size
        if len(self.recent_folders) > self.settings.max_recent_folders:
            self.recent_folders = self.recent_folders[:self.settings.max_recent_folders]
        
        self.save_folders()
    
    def get_recent_connections(self, limit: Optional[int] = None) -> List[ConnectionEntry]:
        """Get recent connections, optionally limited."""
        if limit:
            return self.recent_connections[:limit]
        return self.recent_connections.copy()
    
    def get_recent_folders(self, limit: Optional[int] = None) -> List[FolderEntry]:
        """Get recent folders, optionally limited."""
        if limit:
            return self.recent_folders[:limit]
        return self.recent_folders.copy()
    
    def clear_connection_history(self) -> None:
        """Clear all connection history."""
        self.recent_connections.clear()
        self.save_connections()
    
    def clear_folder_history(self) -> None:
        """Clear all folder history."""
        self.recent_folders.clear()
        self.save_folders()
    
    def remove_connection(self, ip: str, port: str) -> None:
        """Remove a specific connection from history."""
        self.recent_connections = [
            conn for conn in self.recent_connections 
            if not (conn.ip == ip and conn.port == port)
        ]
        self.save_connections()
    
    def remove_folder(self, path: str) -> None:
        """Remove a specific folder from history."""
        self.recent_folders = [
            folder for folder in self.recent_folders 
            if folder.path != path
        ]
        self.save_folders()
    
    def update_window_size(self, width: int, height: int) -> None:
        """Update saved window dimensions."""
        self.settings.window_width = width
        self.settings.window_height = height
        self.save_settings()
    
    def get_default_download_path(self) -> str:
        """Get default download path, falling back to Downloads folder."""
        if self.settings.default_download_path and os.path.exists(self.settings.default_download_path):
            return self.settings.default_download_path
        
        # Fallback to Downloads folder
        downloads_path = Path.home() / "Downloads"
        if downloads_path.exists():
            return str(downloads_path)
        
        # Final fallback to home directory
        return str(Path.home())
    
    def cleanup_invalid_entries(self) -> None:
        """Remove invalid folder entries (folders that no longer exist)."""
        valid_folders = []
        for folder in self.recent_folders:
            if os.path.exists(folder.path):
                valid_folders.append(folder)
        
        if len(valid_folders) != len(self.recent_folders):
            self.recent_folders = valid_folders
            self.save_folders()


# Global config instance
config = ConfigManager()