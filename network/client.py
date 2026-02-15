import requests
import os
import urllib.parse
import json
import gzip
import concurrent.futures
import threading
from pathlib import Path
import time
from typing import Tuple, List, Optional, Callable
import hashlib


class HTTPClient:
    def __init__(self, max_connections=10):
        self.session = requests.Session()
        # Optimize session for performance
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=max_connections,
            pool_maxsize=max_connections,
            max_retries=3
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        # Set optimized headers
        self.session.headers.update({
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'User-Agent': 'LANShare/2.0 (Optimized)'
        })
        
        # Connection cache for similar speed optimization
        self._connection_cache = {}
        self._cache_lock = threading.Lock()
        
    def _get_cache_key(self, ip: str, port: str) -> str:
        """Generate cache key for connection."""
        return f"{ip}:{port}"

    def list_files(self, ip, port):
        """Fetch structured file list from server JSON API with compression support and caching."""
        cache_key = self._get_cache_key(ip, port)
        url = f"http://{ip}:{port}/api/files"
        
        try:
            response = self.session.get(url, timeout=15)  # Increased timeout
            response.raise_for_status()
            
            # Handle compressed responses with fallback
            if response.headers.get('content-encoding') == 'gzip':
                try:
                    content = gzip.decompress(response.content)
                    file_list = json.loads(content.decode('utf-8'))
                except (gzip.BadGzipFile, OSError) as e:
                    # Fallback: try to parse as regular JSON if gzip fails
                    try:
                        file_list = response.json()
                    except:
                        return False, f"Failed to decompress server response: {str(e)}"
            else:
                file_list = response.json()
            
            # Cache connection info for speed optimization
            with self._cache_lock:
                self._connection_cache[cache_key] = {
                    'last_seen': time.time(),
                    'file_count': len(file_list),
                    'responsive': True
                }
                
            return True, file_list
        except requests.exceptions.Timeout:
            return False, "Connection timed out. Check IP and Port."
        except requests.exceptions.ConnectionError:
            with self._cache_lock:
                if cache_key in self._connection_cache:
                    self._connection_cache[cache_key]['responsive'] = False
            return False, "Failed to connect. Is the server running?"
        except json.JSONDecodeError:
            return False, "Invalid response format from server."
        except (gzip.BadGzipFile, OSError) as e:
            return False, f"Error processing server response: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"

    def download_file(self, ip, port, file_path, save_path, progress_callback=None, resume=True, 
                     max_retries=3, verify_integrity=True):
        """Download a file with resume support, retry logic, and integrity checking."""
        url = f"http://{ip}:{port}/download?file={urllib.parse.quote(file_path)}"
        
        retry_count = 0
        while retry_count <= max_retries:
            try:
                # Create parent directories if needed
                parent_dir = Path(save_path).parent
                parent_dir.mkdir(parents=True, exist_ok=True)

                # Check if partial file exists for resume
                resume_pos = 0
                if resume and os.path.exists(save_path):
                    resume_pos = os.path.getsize(save_path)
                    headers = {'Range': f'bytes={resume_pos}-'}
                else:
                    headers = {}
                    
                # Add ETag support for integrity checking
                if verify_integrity and os.path.exists(save_path + '.etag'):
                    try:
                        with open(save_path + '.etag', 'r') as f:
                            headers['If-None-Match'] = f.read().strip()
                    except:
                        pass

                response = self.session.get(url, stream=True, timeout=60, headers=headers)
                
                # Handle not modified (304) response
                if response.status_code == 304:
                    if progress_callback:
                        file_size = os.path.getsize(save_path) if os.path.exists(save_path) else 0
                        progress_callback(file_size, file_size)
                    return True, "File already up to date!"
                
                # Handle range requests
                if response.status_code == 206:  # Partial content
                    mode = 'ab'
                elif response.status_code == 200:
                    mode = 'wb'
                    resume_pos = 0
                else:
                    response.raise_for_status()

                total_size = int(response.headers.get('content-length', 0)) + resume_pos
                # Adaptive chunk size based on file size and connection speed
                chunk_size = self._calculate_optimal_chunk_size(total_size)
                downloaded = resume_pos
                
                # Save ETag for integrity checking
                etag = response.headers.get('ETag')
                if etag and verify_integrity:
                    try:
                        with open(save_path + '.etag', 'w') as f:
                            f.write(etag)
                    except:
                        pass

                start_time = time.time()
                with open(save_path, mode) as f:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            # Adaptive chunk size based on speed
                            if downloaded > chunk_size * 10:  # After 10 chunks
                                elapsed = time.time() - start_time
                                if elapsed > 0:
                                    speed = downloaded / elapsed
                                    chunk_size = self._adapt_chunk_size(chunk_size, speed)
                            
                            if progress_callback:
                                progress_callback(downloaded, total_size)
                
                # Clean up ETag file on successful download
                try:
                    etag_file = save_path + '.etag'
                    if os.path.exists(etag_file):
                        os.remove(etag_file)
                except:
                    pass
                    
                return True, "Download complete!"
                
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                retry_count += 1
                if retry_count <= max_retries:
                    # Exponential backoff for retries
                    wait_time = min(2 ** retry_count, 10)
                    time.sleep(wait_time)
                    continue
                else:
                    return False, f"Download failed after {max_retries} retries: {str(e)}"
            except Exception as e:
                # Only remove file if we were starting fresh (not resuming)
                if not resume and os.path.exists(save_path):
                    try:
                        os.remove(save_path)
                    except:
                        pass
                return False, f"Download failed: {str(e)}"
                
        return False, f"Download failed after {max_retries} retries"

    def download_all(self, ip, port, save_path, progress_callback=None, max_retries=3):
        """Download all files as a zip archive with optimized streaming and retry logic."""
        url = f"http://{ip}:{port}/download_all"
        
        retry_count = 0
        while retry_count <= max_retries:
            try:
                response = self.session.get(url, stream=True, timeout=180)  # Longer timeout for large zips
                response.raise_for_status()

                total_size = int(response.headers.get('content-length', 0))
                # Larger chunk size for zip files
                chunk_size = 4 * 1024 * 1024  # 4MB chunks for better zip streaming
                downloaded = 0

                # Ensure parent directory exists
                Path(save_path).parent.mkdir(parents=True, exist_ok=True)

                start_time = time.time()
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            # Adaptive chunk size for zip downloads
                            if downloaded > chunk_size * 5:
                                elapsed = time.time() - start_time
                                if elapsed > 0:
                                    speed = downloaded / elapsed
                                    if speed > 20 * 1024 * 1024:  # > 20MB/s
                                        chunk_size = min(8 * 1024 * 1024, chunk_size * 2)
                                    elif speed < 1024 * 1024:  # < 1MB/s
                                        chunk_size = max(1024 * 1024, chunk_size // 2)
                                        
                            if progress_callback:
                                progress_callback(downloaded, total_size)

                return True, "Bulk download complete!"
                
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                retry_count += 1
                if retry_count <= max_retries:
                    # Clean up partial file
                    if os.path.exists(save_path):
                        try:
                            os.remove(save_path)
                        except:
                            pass
                    # Exponential backoff
                    wait_time = min(2 ** retry_count, 15)
                    time.sleep(wait_time)
                    continue
                else:
                    if os.path.exists(save_path):
                        try:
                            os.remove(save_path)
                        except:
                            pass
                    return False, f"Bulk download failed after {max_retries} retries: {str(e)}"
            except Exception as e:
                if os.path.exists(save_path):
                    try:
                        os.remove(save_path)
                    except:
                        pass
                return False, f"Bulk download failed: {str(e)}"
                
        return False, f"Bulk download failed after {max_retries} retries"
    
    def _calculate_optimal_chunk_size(self, file_size: int) -> int:
        """Calculate optimal chunk size based on file size."""
        if file_size < 1024 * 1024:  # < 1MB
            return 64 * 1024  # 64KB
        elif file_size < 100 * 1024 * 1024:  # < 100MB
            return 1024 * 1024  # 1MB
        else:
            return 4 * 1024 * 1024  # 4MB
    
    def _adapt_chunk_size(self, current_chunk_size: int, speed_bps: float) -> int:
        """Adapt chunk size based on connection speed."""
        # If speed is very low, use smaller chunks
        if speed_bps < 100 * 1024:  # < 100KB/s
            return max(32 * 1024, current_chunk_size // 2)
        # If speed is high, use larger chunks
        elif speed_bps > 10 * 1024 * 1024:  # > 10MB/s
            return min(8 * 1024 * 1024, current_chunk_size * 2)
        return current_chunk_size

    def download_files_parallel(self, ip, port, file_list, base_save_path, progress_callback=None, 
                                max_workers=None, batch_size=50):
        """Download multiple files in parallel with optimized performance and batching."""
        if max_workers is None:
            # Adaptive worker count based on file count and sizes
            max_workers = self._calculate_optimal_workers(file_list)
        
        def download_single(file_info):
            file_path = file_info['path']
            save_path = os.path.join(base_save_path, file_path)
            return self.download_file(ip, port, file_path, save_path, 
                                    resume=True, max_retries=2)

        successful = 0
        failed = 0
        total_files = len(file_list)
        
        # Filter only files (not folders)
        files_to_download = [f for f in file_list if f.get('type') == 'file']
        
        # Process files in batches to avoid overwhelming the server
        for batch_start in range(0, len(files_to_download), batch_size):
            batch_end = min(batch_start + batch_size, len(files_to_download))
            batch_files = files_to_download[batch_start:batch_end]
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_file = {executor.submit(download_single, file_info): file_info 
                                 for file_info in batch_files}
                
                for future in concurrent.futures.as_completed(future_to_file):
                    file_info = future_to_file[future]
                    try:
                        success, message = future.result()
                        if success:
                            successful += 1
                        else:
                            failed += 1
                            print(f"Failed to download {file_info['path']}: {message}")
                    except Exception as e:
                        failed += 1
                        print(f"Exception downloading {file_info['path']}: {e}")
                    
                    if progress_callback:
                        progress_callback(successful + failed, len(files_to_download))
            
            # Small delay between batches to avoid overwhelming the server
            if batch_end < len(files_to_download):
                time.sleep(0.1)

        return successful > 0, f"Downloaded {successful} files, {failed} failed"
    
    def _calculate_optimal_workers(self, file_list: List[dict]) -> int:
        """Calculate optimal number of worker threads based on file characteristics."""
        file_count = len([f for f in file_list if f.get('type') == 'file'])
        total_size = sum(f.get('size', 0) for f in file_list if f.get('type') == 'file')
        avg_size = total_size / max(file_count, 1)
        
        # More workers for small files, fewer for large files
        if avg_size < 1024 * 1024:  # < 1MB average
            return min(8, file_count)
        elif avg_size < 10 * 1024 * 1024:  # < 10MB average
            return min(4, file_count)
        else:
            return min(2, file_count)
    
    def get_connection_health(self, ip: str, port: str) -> dict:
        """Get connection health information from cache."""
        cache_key = self._get_cache_key(ip, port)
        with self._cache_lock:
            if cache_key in self._connection_cache:
                info = self._connection_cache[cache_key].copy()
                info['age'] = time.time() - info['last_seen']
                return info
        return {'responsive': None, 'age': float('inf')}
    
    def clear_connection_cache(self):
        """Clear the connection cache."""
        with self._cache_lock:
            self._connection_cache.clear()

    def close(self):
        """Clean up session and connections."""
        if self.session:
            self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
