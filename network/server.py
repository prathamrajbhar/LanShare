import http.server
import socketserver
import threading
import functools
import os
import zipfile
import io
import urllib.parse
import json
import gzip
import time
import hashlib
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import mmap
from typing import Dict, List, Optional, Tuple
import tempfile
import shutil


class LANShareRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler with JSON API for recursive file listing and zip download."""

    # Class-level cache for directory structures with enhanced features
    _dir_cache = {}
    _cache_lock = threading.Lock()
    _cache_ttl = 120  # Cache for 2 minutes (increased from 60)
    _etag_cache = {}  # ETags for integrity checking

    def log_message(self, format, *args):
        pass

    def _get_cached_file_list(self, base_dir: str) -> List[Dict]:
        """Get cached file list or rebuild if expired with better cache management."""
        with self._cache_lock:
            cache_key = base_dir
            current_time = time.time()
            
            # Check if cache exists and is not expired
            if (cache_key in self._dir_cache and 
                current_time - self._dir_cache[cache_key]['timestamp'] < self._cache_ttl):
                self._dir_cache[cache_key]['hits'] += 1
                return self._dir_cache[cache_key]['data']
            
            # Check if directory modification time hasn't changed (avoid unnecessary rebuilds)
            try:
                dir_mtime = os.path.getmtime(base_dir)
                if (cache_key in self._dir_cache and 
                    self._dir_cache[cache_key].get('dir_mtime') == dir_mtime):
                    # Directory hasn't changed, just update timestamp
                    self._dir_cache[cache_key]['timestamp'] = current_time
                    return self._dir_cache[cache_key]['data']
            except OSError:
                pass
            
            # Rebuild cache
            file_list = self._build_file_list(base_dir)
            self._dir_cache[cache_key] = {
                'data': file_list,
                'timestamp': current_time,
                'dir_mtime': dir_mtime if 'dir_mtime' in locals() else current_time,
                'hits': 0,
                'size': len(file_list)
            }
            
            # Clean old cache entries (keep only last 5)
            if len(self._dir_cache) > 5:
                oldest_key = min(self._dir_cache.keys(), 
                               key=lambda k: self._dir_cache[k]['timestamp'])
                del self._dir_cache[oldest_key]
            
            return file_list

    def _build_file_list(self, base_dir: str) -> List[Dict]:
        """Build optimized file list using pathlib with enhanced metadata."""
        file_list = []
        base_path = Path(base_dir)
        
        try:
            # Use pathlib for better performance and error handling
            for file_path in base_path.rglob('*'):
                try:
                    rel_path = file_path.relative_to(base_path)
                    
                    if file_path.is_file():
                        stat = file_path.stat()
                        file_list.append({
                            "name": file_path.name,
                            "path": str(rel_path).replace("\\", "/"),
                            "type": "file",
                            "size": stat.st_size,
                            "modified": stat.st_mtime,
                            "extension": file_path.suffix.lower()
                        })
                    elif file_path.is_dir():
                        file_list.append({
                            "name": file_path.name,
                            "path": str(rel_path).replace("\\", "/"),
                            "type": "folder",
                            "size": 0,
                            "modified": file_path.stat().st_mtime
                        })
                except (OSError, PermissionError):
                    # Skip files we can't access
                    continue
                    
        except Exception:
            # Fallback to old method if pathlib fails
            return self._build_file_list_fallback(base_dir)
            
        # Sort for consistent ordering
        file_list.sort(key=lambda x: (x['type'] == 'file', x['path'].lower()))
        return file_list

    def _build_file_list_fallback(self, base_dir: str) -> List[Dict]:
        """Fallback method using os.walk."""
        file_list = []
        
        for root, dirs, files in os.walk(base_dir):
            rel_dir = os.path.relpath(root, base_dir)
            if rel_dir != '.':
                file_list.append({
                    "name": os.path.basename(root),
                    "path": rel_dir.replace("\\", "/"),
                    "type": "folder",
                    "size": 0,
                })

            for fname in files:
                full_path = os.path.join(root, fname)
                rel_path = os.path.relpath(full_path, base_dir).replace("\\", "/")
                try:
                    size = os.path.getsize(full_path)
                except OSError:
                    size = 0

                file_list.append({
                    "name": fname,
                    "path": rel_path,
                    "type": "file",
                    "size": size,
                })
        
        return file_list

    def do_GET(self):
        path = urllib.parse.unquote(self.path)

        if path == '/api/files':
            self._handle_file_list()
        elif path == '/download_all':
            self._handle_download_all()
        elif path.startswith('/download?') or '?file=' in self.path:
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            filepath = params.get('file', [''])[0]
            self._handle_download_file(filepath)
        else:
            super().do_GET()

    def _handle_file_list(self):
        """Return JSON list of all files recursively with enhanced caching and compression."""
        base_dir = self.directory
        file_list = self._get_cached_file_list(base_dir)

        response_data = json.dumps(file_list, separators=(',', ':')).encode('utf-8')
        
        # Generate ETag for file list caching
        etag = hashlib.md5(response_data).hexdigest()
        client_etag = self.headers.get('If-None-Match')
        
        # Check if client has current version
        if client_etag == etag:
            self.send_response(304)  # Not Modified
            self.send_header('ETag', etag)
            self.send_header('Cache-Control', 'max-age=60')
            self.end_headers()
            return
        
        # Add gzip compression with better error handling
        should_compress = len(response_data) > 1024
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('ETag', etag)
        
        if should_compress:
            try:
                compressed_data = gzip.compress(response_data, compresslevel=6)
                # Only use compression if it actually reduces size significantly
                if len(compressed_data) < len(response_data) * 0.9:
                    response_data = compressed_data
                    self.send_header('Content-Encoding', 'gzip')
            except Exception:
                # If compression fails, send uncompressed data
                pass
            
        self.send_header('Content-Length', str(len(response_data)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'max-age=60')
        self.end_headers()
        self.wfile.write(response_data)

    def _handle_download_file(self, filepath: str):
        """Download a specific file with enhanced support for resume, ETag, and optimized streaming."""
        base_dir = self.directory
        safe_path = os.path.normpath(filepath)
        if safe_path.startswith('..') or os.path.isabs(safe_path):
            self.send_error(403, "Forbidden")
            return

        full_path = os.path.join(base_dir, safe_path)
        if not os.path.isfile(full_path):
            self.send_error(404, "File not found")
            return

        try:
            file_stat = os.stat(full_path)
            file_size = file_stat.st_size
            file_mtime = file_stat.st_mtime
            filename = os.path.basename(full_path)
            
            # Generate ETag based on file size and modification time
            etag = f'"{file_size}-{int(file_mtime)}"'
            client_etag = self.headers.get('If-None-Match')
            
            # Check if client has current version
            if client_etag == etag:
                self.send_response(304)  # Not Modified
                self.send_header('ETag', etag)
                self.send_header('Cache-Control', 'max-age=3600')
                self.end_headers()
                return
            
            # Handle Range requests for resume support
            range_header = self.headers.get('Range')
            start_byte = 0
            end_byte = file_size - 1
            
            if range_header:
                range_match = re.match(r'bytes=(\d+)-(\d*)', range_header)
                if range_match:
                    start_byte = int(range_match.group(1))
                    if range_match.group(2):
                        end_byte = int(range_match.group(2))
                    
                    self.send_response(206)  # Partial Content
                    self.send_header('Content-Range', f'bytes {start_byte}-{end_byte}/{file_size}')
                else:
                    self.send_response(200)
            else:
                self.send_response(200)
            
            content_length = end_byte - start_byte + 1
            
            self.send_header('Content-Type', 'application/octet-stream')
            self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
            self.send_header('Content-Length', str(content_length))
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('ETag', etag)
            self.send_header('Cache-Control', 'max-age=3600')
            self.end_headers()

            # Use memory mapping for large files (>50MB) to reduce memory usage
            if file_size > 50 * 1024 * 1024:
                self._stream_large_file_range(full_path, start_byte, end_byte)
            else:
                self._stream_file_range(full_path, start_byte, end_byte)
                
        except Exception as e:
            self.send_error(500, str(e))

    def _stream_file_range(self, file_path: str, start_byte: int, end_byte: int):
        """Stream file range with optimized chunk size."""
        chunk_size = min(1024 * 1024, end_byte - start_byte + 1)  # 1MB chunks or file size
        with open(file_path, 'rb') as f:
            f.seek(start_byte)
            remaining = end_byte - start_byte + 1
            while remaining > 0:
                chunk_size = min(chunk_size, remaining)
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def _stream_large_file_range(self, file_path: str, start_byte: int, end_byte: int):
        """Stream large file range using memory mapping for better memory efficiency."""
        try:
            with open(file_path, 'rb') as f:
                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mmapped_file:
                    chunk_size = 2 * 1024 * 1024  # 2MB chunks for large files
                    remaining = end_byte - start_byte + 1
                    offset = start_byte
                    while remaining > 0:
                        chunk_size = min(chunk_size, remaining)
                        chunk = mmapped_file[offset:offset + chunk_size]
                        self.wfile.write(chunk)
                        offset += chunk_size
                        remaining -= chunk_size
        except (ValueError, MemoryError):
            # Fallback to regular streaming if mmap fails
            self._stream_file_range(file_path, start_byte, end_byte)

    def _handle_download_all(self):
        """Download entire directory as zip with optimized streaming and better memory management."""
        base_dir = self.directory
        root_name = os.path.basename(base_dir.rstrip(os.sep))
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/zip')
        self.send_header('Content-Disposition', f'attachment; filename="{root_name}.zip"')
        
        # Use temporary file for zip creation
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name
            
            try:
                with zipfile.ZipFile(temp_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
                    base_path = Path(base_dir)
                    
                    for file_path in base_path.rglob('*'):
                        try:
                            if file_path.is_file():
                                rel_path = file_path.relative_to(base_path)
                                arcname = str(Path(root_name) / rel_path)
                                zf.write(str(file_path), arcname)
                            elif file_path.is_dir() and not any(file_path.iterdir()):
                                rel_path = file_path.relative_to(base_path)
                                arcname = str(Path(root_name) / rel_path) + '/'
                                zf.writestr(arcname, '')
                        except (OSError, PermissionError):
                            continue
                
                # Send the zip file
                zip_size = os.path.getsize(temp_path)
                self.send_header('Content-Length', str(zip_size))
                self.end_headers()
                
                chunk_size = 2 * 1024 * 1024  # 2MB chunks
                with open(temp_path, 'rb') as zf:
                    while True:
                        chunk = zf.read(chunk_size)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                    
            finally:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass


class OptimizedThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """Optimized threaded server with better performance characteristics."""
    allow_reuse_address = True
    daemon_threads = True
    request_queue_size = 100
    
    def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True):
        super().__init__(server_address, RequestHandlerClass, bind_and_activate)
        # Use thread pool executor for better thread management
        self.executor = ThreadPoolExecutor(max_workers=min(32, (os.cpu_count() or 1) + 4))
    
    def process_request_thread(self, request, client_address):
        """Process request in thread pool."""
        try:
            self.finish_request(request, client_address)
            self.shutdown_request(request)
        except Exception:
            self.handle_error(request, client_address)
            self.shutdown_request(request)
    
    def process_request(self, request, client_address):
        """Submit request to thread pool."""
        self.executor.submit(self.process_request_thread, request, client_address)


class HTTPServerManager:
    def __init__(self, directory, port=8000):
        self.directory = directory
        self.port = port
        self.httpd = None
        self.server_thread = None
        self.is_running = False

    def start_server(self, ip='0.0.0.0'):
        try:
            handler = functools.partial(LANShareRequestHandler, directory=self.directory)
            self.httpd = OptimizedThreadedHTTPServer((ip, self.port), handler)
            self.is_running = True

            self.server_thread = threading.Thread(target=self.httpd.serve_forever)
            self.server_thread.daemon = True
            self.server_thread.start()
            return True, f"Server started at {ip}:{self.port}"
        except OSError as e:
            if e.errno == 98:
                return False, f"Port {self.port} is already in use."
            return False, f"Error starting server: {e}"
        except Exception as e:
            return False, f"Unexpected error: {e}"

    def stop_server(self):
        if self.httpd and self.is_running:
            self.httpd.shutdown()
            self.httpd.server_close()
            # Shutdown thread pool
            if hasattr(self.httpd, 'executor'):
                self.httpd.executor.shutdown(wait=True)
            self.is_running = False
            self.httpd = None
            if self.server_thread:
                self.server_thread.join(timeout=5)
                self.server_thread = None
            return True
        return False

    def clear_cache(self):
        """Clear directory cache to force refresh."""
        with LANShareRequestHandler._cache_lock:
            LANShareRequestHandler._dir_cache.clear()
