# src/utils/atomic_ops.py
"""
Atomic operations module for DeepDomain TUI.
Implements atomic writes and thread-safe operations to prevent TUI freezing.
Based on optimization documentation patterns.
"""
import os
import tempfile
import threading
import asyncio
from pathlib import Path
from typing import Optional, Callable, Any, Union
from datetime import datetime
import time


class AtomicFileWriter:
    """Thread-safe atomic file writer with streaming support"""
    
    def __init__(self, max_memory_size: int = 1024 * 1024):  # 1MB default
        self.max_memory_size = max_memory_size
        self._locks = {}  # Per-file locks
        self._lock = threading.Lock()
    
    def _get_lock(self, file_path: Path) -> threading.Lock:
        """Get or create a lock for a specific file"""
        with self._lock:
            if file_path not in self._locks:
                self._locks[file_path] = threading.Lock()
            return self._locks[file_path]
    
    def atomic_write(self, file_path: Path, content: str, mode: str = 'w', encoding: str = 'utf-8') -> None:
        """Atomically write content to file using tempfile + rename"""
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with self._get_lock(file_path):
            # Create temporary file in same directory
            with tempfile.NamedTemporaryFile(
                mode=mode, 
                delete=False, 
                encoding=encoding, 
                dir=str(file_path.parent),
                prefix=f".{file_path.name}."
            ) as tmp_file:
                tmp_file.write(content)
                tmp_file.flush()
                os.fsync(tmp_file.fileno())  # Force write to disk
                temp_path = Path(tmp_file.name)
            
            # Atomic rename
            os.replace(temp_path, file_path)
    
    def atomic_append(self, file_path: Path, content: str, encoding: str = 'utf-8') -> None:
        """Atomically append content to file"""
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with self._get_lock(file_path):
            # For append, we need to read existing content first
            existing_content = ""
            if file_path.exists():
                try:
                    existing_content = file_path.read_text(encoding=encoding)
                except (OSError, UnicodeDecodeError):
                    existing_content = ""
            
            # Write combined content atomically
            combined_content = existing_content + content
            if content and not content.endswith('\n'):
                combined_content += '\n'
            
            self.atomic_write(file_path, combined_content, mode='w', encoding=encoding)
    
    def streaming_write(self, file_path: Path, content: str, encoding: str = 'utf-8') -> None:
        """Stream large content in chunks to avoid memory issues"""
        file_path = Path(file_path)
        
        if len(content) <= self.max_memory_size:
            self.atomic_write(file_path, content, encoding=encoding)
            return
        
        # For large content, write in chunks
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with self._get_lock(file_path):
            with file_path.open("a", encoding=encoding) as fh:
                # Write in 64KB chunks
                for i in range(0, len(content), 65536):
                    chunk = content[i:i+65536]
                    fh.write(chunk)
                    fh.flush()


class AsyncCommandRunner:
    """Async command runner with proper TUI integration"""
    
    def __init__(self, max_concurrent: int = 8):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.running_processes = {}
        self.process_counter = 0
        self._lock = threading.Lock()
    
    async def run_command_async(
        self, 
        command: str, 
        workdir: Path,
        output_callback: Optional[Callable[[str], None]] = None,
        error_callback: Optional[Callable[[str], None]] = None,
        timeout: Optional[int] = None
    ) -> tuple[str, str, int]:
        """
        Run command asynchronously with live output streaming.
        Returns (stdout, stderr, returncode)
        """
        async with self.semaphore:
            try:
                # Start the process
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(workdir),
                    text=True
                )
                
                # Store process reference
                with self._lock:
                    self.process_counter += 1
                    process_id = self.process_counter
                    self.running_processes[process_id] = process
                
                stdout_lines = []
                stderr_lines = []
                
                # Read output streams concurrently
                async def read_stream(stream, lines_list, callback):
                    while True:
                        line = await stream.readline()
                        if not line:
                            break
                        line = line.strip()
                        if line:
                            lines_list.append(line)
                            if callback:
                                try:
                                    callback(line)
                                except Exception:
                                    pass
                
                # Read both streams concurrently
                await asyncio.gather(
                    read_stream(process.stdout, stdout_lines, output_callback),
                    read_stream(process.stderr, stderr_lines, error_callback)
                )
                
                # Wait for process to complete
                return_code = await process.wait()
                
                # Clean up
                with self._lock:
                    if process_id in self.running_processes:
                        del self.running_processes[process_id]
                
                return '\n'.join(stdout_lines), '\n'.join(stderr_lines), return_code
                
            except Exception as e:
                return "", str(e), 1
    
    def stop_all_processes(self):
        """Stop all running processes"""
        with self._lock:
            for process in self.running_processes.values():
                try:
                    process.terminate()
                except Exception:
                    pass
            self.running_processes.clear()


class TUIUpdateManager:
    """Manages atomic TUI updates to prevent freezing"""
    
    def __init__(self, tui_app):
        self.tui_app = tui_app
        self.update_queue = asyncio.Queue()
        self.update_task = None
        self._running = False
    
    async def start(self):
        """Start the update manager"""
        if self._running:
            return
        self._running = True
        self.update_task = asyncio.create_task(self._process_updates())
    
    async def stop(self):
        """Stop the update manager"""
        self._running = False
        if self.update_task:
            self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass
    
    async def queue_update(self, update_type: str, data: Any):
        """Queue an update for the TUI"""
        await self.update_queue.put((update_type, data))
    
    async def _process_updates(self):
        """Process queued updates"""
        while self._running:
            try:
                # Wait for updates with timeout
                update_type, data = await asyncio.wait_for(
                    self.update_queue.get(), 
                    timeout=0.1
                )
                
                # Process the update
                await self._apply_update(update_type, data)
                
                # Mark task as done
                self.update_queue.task_done()
                
            except asyncio.TimeoutError:
                # No updates, continue
                continue
            except Exception as e:
                # Log error but continue
                print(f"Update processing error: {e}")
                continue
    
    async def _apply_update(self, update_type: str, data: Any):
        """Apply a specific update type"""
        try:
            if update_type == "status_message":
                message, msg_type = data
                self.tui_app.add_status_message(message, msg_type)
            elif update_type == "phase_update":
                phase, progress = data
                self.tui_app.update_phase(phase, progress)
            elif update_type == "command_output":
                output = data
                self.tui_app.add_command_output(output)
            elif update_type == "command_start":
                command = data
                self.tui_app.start_command(command)
            elif update_type == "command_finish":
                self.tui_app.finish_command()
        except Exception as e:
            print(f"Error applying update {update_type}: {e}")


# Global instances
atomic_writer = AtomicFileWriter()
command_runner = AsyncCommandRunner()
