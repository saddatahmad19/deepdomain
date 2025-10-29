# src/tui.py
import asyncio
import subprocess
import threading
from pathlib import Path
from typing import Optional, Callable, Any
from datetime import datetime
import time

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Static, TextArea, ProgressBar, Label, RichLog
from textual.binding import Binding
from textual.reactive import reactive
from textual.timer import Timer
from textual import events
from textual.scroll_view import ScrollView
from textual.worker import Worker, WorkerState
from rich.text import Text

from .atomic_ops import AsyncCommandRunner, TUIUpdateManager, atomic_writer


class StatusPanel(ScrollableContainer):
    """Left panel showing status updates and phase information"""
    
    can_focus = True
    
    # Reactive properties for atomic updates
    current_phase = reactive("Initializing")
    phase_progress = reactive(0)
    status_messages = reactive([])
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.total_phases = 3
        
    def compose(self) -> ComposeResult:
        yield Label("DeepDomain Status", id="status-title")
        yield ProgressBar(total=100, show_eta=False, id="phase-progress")
        yield Label("", id="current-phase")
        yield RichLog(id="status-messages", wrap=True, highlight=True, markup=True)
    
    def watch_current_phase(self, phase: str) -> None:
        """React to phase changes"""
        try:
            self.query_one("#current-phase", Label).update(f"Phase: {phase}")
        except Exception:
            pass
    
    def watch_phase_progress(self, progress: int) -> None:
        """React to progress changes"""
        try:
            self.query_one("#phase-progress", ProgressBar).update(progress=progress)
        except Exception:
            pass
    
    def watch_status_messages(self, messages: list) -> None:
        """React to status message changes"""
        try:
            log = self.query_one("#status-messages", RichLog)
            # Clear and rewrite all messages to ensure consistency
            if messages:
                log.clear()
                for message in messages:
                    log.write(message)
        except Exception:
            pass
    
    def update_phase(self, phase: str, progress: int = 0):
        """Update the current phase and progress atomically"""
        self.current_phase = phase
        self.phase_progress = progress
    
    def add_status_message(self, message: str, msg_type: str = "info"):
        """Add a status message to the panel atomically"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Color-coded icons and messages
        if msg_type == "success":
            icon = "✓"
            color = "green"
        elif msg_type == "info":
            icon = "ℹ"
            color = "cyan"
        elif msg_type == "warning":
            icon = "⚠"
            color = "yellow"
        else:  # error
            icon = "✗"
            color = "red"
        
        formatted_msg = f"[dim]{timestamp}[/dim] [{color}]{icon}[/{color}] {message}"
        
        # Update reactive property
        self.status_messages = self.status_messages + [formatted_msg]
    
    def clear_messages(self):
        """Clear all status messages"""
        self.status_messages = []


class LiveOutputPanel(ScrollableContainer):
    """Right panel showing live command output"""
    
    can_focus = True
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_command = ""
        self.command_running = False
        
    def compose(self) -> ComposeResult:
        yield Label("Live Command Output", id="output-title")
        yield Label("", id="current-command")
        yield RichLog(id="output-text", wrap=True, highlight=False, markup=False, max_lines=5000)
    
    def start_command(self, command: str):
        """Start tracking a new command"""
        self.current_command = command
        self.command_running = True
        try:
            self.query_one("#current-command", Label).update(f"[yellow]Running:[/yellow] {command}")
            self.query_one("#output-text", RichLog).clear()
        except:
            pass
    
    def add_output(self, text: str):
        """Add output text to the panel - this will be called from background threads"""
        if not text or not text.strip():
            return
            
        try:
            log = self.query_one("#output-text", RichLog)
            # Write each line separately for better streaming effect
            for line in text.split('\n'):
                if line.strip():
                    log.write(line)
        except:
            pass
    
    def finish_command(self):
        """Mark the current command as finished"""
        self.command_running = False
        try:
            self.query_one("#current-command", Label).update("[green]Command completed[/green]")
        except:
            pass
    
    def clear_output(self):
        """Clear all output"""
        try:
            self.query_one("#output-text", RichLog).clear()
            self.query_one("#current-command", Label).update("No command running")
        except:
            pass


class DeepDomainTUI(App):
    """Main TUI application for DeepDomain with atomic updates"""
    
    CSS = """
    Screen {
        layout: horizontal;
    }
    
    #status-panel {
        width: 1fr;
        max-width: 40%;
        border: solid $primary;
        margin: 1;
        padding: 1;
    }
    
    #status-panel:focus {
        border: solid $accent;
        border-title-color: $accent;
    }
    
    #output-panel {
        width: 2fr;
        border: solid $primary;
        margin: 1;
        padding: 1;
    }
    
    #output-panel:focus {
        border: solid $accent;
        border-title-color: $accent;
    }
    
    #status-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    
    #output-title {
        text-style: bold;
        color: $primary;
        margin-bottom: 1;
    }
    
    #current-command {
        margin-bottom: 1;
    }
    
    #current-phase {
        color: $accent;
        margin-bottom: 1;
    }
    
    #status-messages {
        height: 1fr;
        border: solid $secondary;
        padding: 1;
        margin-top: 1;
    }
    
    #output-text {
        height: 1fr;
        border: solid $secondary;
        padding: 1;
    }
    
    #phase-progress {
        margin: 1 0;
    }
    
    RichLog {
        scrollbar-gutter: stable;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("c", "clear_output", "Clear Output"),
        Binding("r", "clear_status", "Clear Status"),
        Binding("s", "toggle_status", "Toggle Status"),
        Binding("ctrl+1", "focus_status", "Focus Status"),
        Binding("ctrl+2", "focus_output", "Focus Output"),
        Binding("j", "scroll_down", "Scroll Down"),
        Binding("k", "scroll_up", "Scroll Up"),
    ]
    
    def __init__(self, domain: str, output_dir: Path, scanning_callback=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.domain = domain
        self.output_dir = output_dir
        self.status_panel: Optional[StatusPanel] = None
        self.output_panel: Optional[LiveOutputPanel] = None
        self.scanning_callback = scanning_callback
        self.scanning_started = False
        
        # Initialize async components
        self.command_runner = AsyncCommandRunner(max_concurrent=8)
        self.update_manager = TUIUpdateManager(self)
        
    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            self.status_panel = StatusPanel(id="status-panel")
            yield self.status_panel
            self.output_panel = LiveOutputPanel(id="output-panel")
            yield self.output_panel
        yield Footer()
    
    async def on_mount(self) -> None:
        """Initialize the TUI when mounted"""
        # Start the update manager
        await self.update_manager.start()
        
        # Initial status updates
        self.status_panel.add_status_message(f"DeepDomain initialized for {self.domain}", "info")
        self.status_panel.add_status_message(f"Output directory: {self.output_dir}", "info")
        self.status_panel.update_phase("Ready", 0)
        
        # Set up periodic refresh to ensure updates are visible
        self.set_interval(0.5, self.refresh_display)
        
        # Start scanning after a brief delay
        if self.scanning_callback and not self.scanning_started:
            self.scanning_started = True
            self.set_timer(1.0, self.start_scanning)
    
    def refresh_display(self):
        """Periodically refresh the display to ensure updates are visible"""
        try:
            # Force refresh of reactive properties
            if self.status_panel:
                # Trigger reactive property updates
                self.status_panel.current_phase = self.status_panel.current_phase
                self.status_panel.phase_progress = self.status_panel.phase_progress
                self.status_panel.status_messages = self.status_panel.status_messages
        except Exception:
            pass
    
    async def on_unmount(self) -> None:
        """Clean up when TUI is unmounted"""
        await self.update_manager.stop()
        self.command_runner.stop_all_processes()
    
    def start_scanning(self):
        """Start the scanning process asynchronously"""
        if self.scanning_callback:
            # Run scanning in background to avoid blocking TUI
            asyncio.create_task(self._run_scanning_async())
    
    async def _run_scanning_async(self):
        """Run scanning callback asynchronously"""
        try:
            # Create a thread-safe wrapper for the scanning callback
            thread_safe_tui = ThreadSafeTUIWrapper(self)
            
            # Run the scanning callback in a thread to avoid blocking
            loop = asyncio.get_event_loop()
            
            # Add a timeout to prevent infinite hanging
            await asyncio.wait_for(
                loop.run_in_executor(None, self.scanning_callback, thread_safe_tui),
                timeout=1800  # 30 minute timeout for entire scanning process
            )
        except asyncio.TimeoutError:
            await self.update_manager.queue_update("status_message", ("Scanning process timed out after 30 minutes", "error"))
            await self.update_manager.queue_update("phase_update", ("Timeout", 0))
        except Exception as e:
            await self.update_manager.queue_update("status_message", (f"Scanning error: {str(e)}", "error"))
            # Also update phase to show error state
            await self.update_manager.queue_update("phase_update", ("Error", 0))
    
    def action_quit(self) -> None:
        """Quit the application"""
        self.exit()
    
    def action_clear_output(self) -> None:
        """Clear the output panel"""
        if self.output_panel:
            self.output_panel.clear_output()
    
    def action_clear_status(self) -> None:
        """Clear the status panel"""
        if self.status_panel:
            self.status_panel.clear_messages()
    
    def action_toggle_status(self) -> None:
        """Toggle status panel visibility"""
        if self.status_panel:
            self.status_panel.display = not self.status_panel.display
    
    def action_focus_status(self) -> None:
        """Focus the status panel"""
        if self.status_panel:
            self.status_panel.focus()
    
    def action_focus_output(self) -> None:
        """Focus the output panel"""
        if self.output_panel:
            self.output_panel.focus()
    
    def action_scroll_down(self) -> None:
        """Scroll down in the focused panel"""
        focused = self.focused
        if isinstance(focused, (StatusPanel, LiveOutputPanel)):
            focused.scroll_down(animate=False)
    
    def action_scroll_up(self) -> None:
        """Scroll up in the focused panel"""
        focused = self.focused
        if isinstance(focused, (StatusPanel, LiveOutputPanel)):
            focused.scroll_up(animate=False)
    
    def update_phase(self, phase: str, progress: int = 0):
        """Update the current phase"""
        if self.status_panel:
            self.status_panel.update_phase(phase, progress)
    
    def add_status_message(self, message: str, msg_type: str = "info"):
        """Add a status message"""
        if self.status_panel:
            self.status_panel.add_status_message(message, msg_type)
    
    async def update_phase_async(self, phase: str, progress: int = 0):
        """Update the current phase asynchronously (thread-safe)"""
        await self.update_manager.queue_update("phase_update", (phase, progress))
    
    async def add_status_message_async(self, message: str, msg_type: str = "info"):
        """Add a status message asynchronously (thread-safe)"""
        await self.update_manager.queue_update("status_message", (message, msg_type))
    
    def start_command(self, command: str):
        """Start tracking a command"""
        if self.output_panel:
            self.output_panel.start_command(command)
    
    def add_command_output(self, text: str):
        """Add command output"""
        if self.output_panel:
            self.output_panel.add_output(text)
    
    def finish_command(self):
        """Mark current command as finished"""
        if self.output_panel:
            self.output_panel.finish_command()
    
    async def add_command_output_async(self, text: str):
        """Add command output asynchronously (thread-safe)"""
        await self.update_manager.queue_update("command_output", text)
    
    async def start_command_async(self, command: str):
        """Start tracking a command asynchronously (thread-safe)"""
        await self.update_manager.queue_update("command_start", command)
    
    async def finish_command_async(self):
        """Mark current command as finished asynchronously (thread-safe)"""
        await self.update_manager.queue_update("command_finish", None)
    
    async def run_command_async(self, command: str, workdir: Path, callback: Optional[Callable] = None) -> None:
        """
        Run a command asynchronously with live output streaming.
        This is the main method that should be used for command execution.
        """
        def output_callback(text: str):
            """Callback for command output"""
            # Schedule async update to avoid blocking
            asyncio.create_task(self.add_command_output_async(text))
        
        def error_callback(text: str):
            """Callback for command errors"""
            # Schedule async update to avoid blocking
            asyncio.create_task(self.add_command_output_async(f"[red]ERROR: {text}[/red]"))
        
        # Start the command tracking
        await self.start_command_async(command)
        
        try:
            # Run command asynchronously
            stdout, stderr, return_code = await self.command_runner.run_command_async(
                command, 
                workdir, 
                output_callback=output_callback,
                error_callback=error_callback
            )
            
            # Mark command as finished
            await self.finish_command_async()
            
            # Handle completion
            if return_code != 0:
                await self.add_status_message_async(f"Command failed with return code {return_code}", "error")
            else:
                await self.add_status_message_async("Command completed successfully", "success")
            
            # Call user callback if provided
            if callback:
                callback(stdout, stderr, return_code)
                
        except Exception as e:
            await self.finish_command_async()
            await self.add_status_message_async(f"Command error: {str(e)}", "error")
            if callback:
                callback("", str(e), 1)
    
    def run_command_live(self, command: str, workdir: Path) -> tuple[str, str, int]:
        """
        Synchronous wrapper for run_command_async.
        This method blocks until completion - use run_command_async when possible.
        """
        # Create a future to wait for completion
        result_future = asyncio.Future()
        
        def callback(stdout: str, stderr: str, return_code: int):
            result_future.set_result((stdout, stderr, return_code))
        
        # Schedule the async command
        asyncio.create_task(self.run_command_async(command, workdir, callback))
        
        # Wait for completion (this will block the calling thread)
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(result_future)


class ThreadSafeTUIWrapper:
    """
    Thread-safe wrapper for TUI that can be used from background threads.
    This bridges the gap between synchronous scanning callbacks and async TUI updates.
    """
    
    def __init__(self, tui_app: DeepDomainTUI):
        self.tui_app = tui_app
        self._loop = None
    
    def _get_event_loop(self):
        """Get the event loop for the TUI"""
        if self._loop is None:
            # Get the TUI's event loop
            try:
                self._loop = self.tui_app._loop
            except AttributeError:
                # Fallback: try to get the current running loop
                try:
                    self._loop = asyncio.get_running_loop()
                except RuntimeError:
                    # No loop running, we'll use direct updates
                    self._loop = None
        return self._loop
    
    def update_phase(self, phase: str, progress: int = 0):
        """Update the current phase (thread-safe)"""
        loop = self._get_event_loop()
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self.tui_app.update_phase_async(phase, progress), 
                loop
            )
        else:
            # Fallback to direct update if no loop available
            self.tui_app.update_phase(phase, progress)
    
    def add_status_message(self, message: str, msg_type: str = "info"):
        """Add a status message (thread-safe)"""
        loop = self._get_event_loop()
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self.tui_app.add_status_message_async(message, msg_type), 
                loop
            )
        else:
            # Fallback to direct update if no loop available
            self.tui_app.add_status_message(message, msg_type)
    
    def run_command_live(self, command: str, workdir: Path) -> tuple[str, str, int]:
        """Run a command with live output (thread-safe) - STREAMING VERSION"""
        import subprocess
        import threading
        import queue
        
        # Create a queue for streaming output
        output_queue = queue.Queue()
        error_queue = queue.Queue()
        
        def stream_output(pipe, output_queue):
            """Stream output from a pipe to a queue"""
            try:
                for line in iter(pipe.readline, ''):
                    if line:
                        output_queue.put(line.strip())
                pipe.close()
            except Exception:
                pass
        
        try:
            # Start command tracking in TUI
            loop = self._get_event_loop()
            if loop and loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self.tui_app.start_command_async(command), 
                    loop
                )
            
            # Run command with streaming output
            proc = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(workdir),
                bufsize=1,  # Line buffered
                universal_newlines=True
            )
            
            # Start streaming threads
            stdout_thread = threading.Thread(target=stream_output, args=(proc.stdout, output_queue))
            stderr_thread = threading.Thread(target=stream_output, args=(proc.stderr, error_queue))
            stdout_thread.daemon = True
            stderr_thread.daemon = True
            stdout_thread.start()
            stderr_thread.start()
            
            # Collect output while streaming to TUI
            stdout_lines = []
            stderr_lines = []
            
            # Stream output for up to 5 minutes
            import time
            start_time = time.time()
            timeout = 300  # 5 minutes
            
            while proc.poll() is None and (time.time() - start_time) < timeout:
                # Process stdout
                try:
                    while True:
                        line = output_queue.get_nowait()
                        stdout_lines.append(line)
                        if loop and loop.is_running():
                            asyncio.run_coroutine_threadsafe(
                                self.tui_app.add_command_output_async(line), 
                                loop
                            )
                except queue.Empty:
                    pass
                
                # Process stderr
                try:
                    while True:
                        line = error_queue.get_nowait()
                        stderr_lines.append(line)
                        if loop and loop.is_running():
                            asyncio.run_coroutine_threadsafe(
                                self.tui_app.add_command_output_async(f"[red]ERROR: {line}[/red]"), 
                                loop
                            )
                except queue.Empty:
                    pass
                
                # Small delay to prevent busy waiting
                time.sleep(0.1)
            
            # Wait for process to complete or timeout
            try:
                proc.wait(timeout=max(0, timeout - (time.time() - start_time)))
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
            
            # Collect any remaining output
            try:
                while True:
                    line = output_queue.get_nowait()
                    stdout_lines.append(line)
            except queue.Empty:
                pass
            
            try:
                while True:
                    line = error_queue.get_nowait()
                    stderr_lines.append(line)
            except queue.Empty:
                pass
            
            # Finish command tracking
            if loop and loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self.tui_app.finish_command_async(), 
                    loop
                )
            
            return '\n'.join(stdout_lines), '\n'.join(stderr_lines), proc.returncode
            
        except Exception as e:
            # Handle errors
            if loop and loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self.tui_app.add_status_message_async(f"Command error: {str(e)}", "error"), 
                    loop
                )
            return "", str(e), 1
    
    async def _run_command_async(self, command: str, workdir: Path) -> tuple[str, str, int]:
        """Internal async method to run command"""
        result_future = asyncio.Future()
        
        def callback(stdout: str, stderr: str, return_code: int):
            result_future.set_result((stdout, stderr, return_code))
        
        await self.tui_app.run_command_async(command, workdir, callback)
        return await result_future


class TUIWrapper:
    """
    Wrapper class to provide a simple interface for integrating with existing code.
    This allows the TUI to be used as a drop-in replacement for console output.
    """
    
    def __init__(self, domain: str, output_dir: Path, scanning_callback=None):
        self.domain = domain
        self.output_dir = output_dir
        self.tui_app: Optional[DeepDomainTUI] = None
        self.tui_running = False
        self.scanning_callback = scanning_callback
        self._command_queue = []
        self._status_queue = []
        self._phase_queue = []
    
    def start(self):
        """Initialize the TUI application (but don't run it yet)"""
        if self.tui_running:
            return
        
        self.tui_app = DeepDomainTUI(self.domain, self.output_dir, self.scanning_callback)
        self.tui_running = True
    
    def stop(self):
        """Stop the TUI application"""
        if self.tui_app and self.tui_running:
            self.tui_app.command_runner.stop_all_processes()
            self.tui_app.exit()
            self.tui_running = False
    
    def update_phase(self, phase: str, progress: int = 0):
        """Update the current phase"""
        if self.tui_app:
            self.tui_app.update_phase(phase, progress)
        else:
            # Queue for later if TUI not ready
            self._phase_queue.append((phase, progress))
    
    def add_status_message(self, message: str, msg_type: str = "info"):
        """Add a status message"""
        if self.tui_app:
            self.tui_app.add_status_message(message, msg_type)
        else:
            # Queue for later if TUI not ready
            self._status_queue.append((message, msg_type))
    
    def run_command_live(self, command: str, workdir: Path) -> tuple[str, str, int]:
        """Run a command with live output"""
        if self.tui_app:
            return self.tui_app.run_command_live(command, workdir)
        else:
            # Fallback to regular subprocess if TUI not available
            import subprocess
            proc = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=workdir)
            return proc.stdout, proc.stderr, proc.returncode
    
    def run_command_async(self, command: str, workdir: Path, callback: Optional[Callable] = None):
        """Run a command asynchronously"""
        if self.tui_app:
            # Schedule the async command
            asyncio.create_task(self.tui_app.run_command_async(command, workdir, callback))
        else:
            # Fallback to regular subprocess if TUI not available
            import subprocess
            def run_fallback():
                proc = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=workdir)
                if callback:
                    callback(proc.stdout, proc.stderr, proc.returncode)
            threading.Thread(target=run_fallback, daemon=True).start()
    
    def run_tui(self):
        """Run the TUI application in the main thread"""
        if not self.tui_app:
            self.start()
        
        # Process any queued updates
        for phase, progress in self._phase_queue:
            self.tui_app.update_phase(phase, progress)
        self._phase_queue.clear()
        
        for message, msg_type in self._status_queue:
            self.tui_app.add_status_message(message, msg_type)
        self._status_queue.clear()
        
        # Run the TUI
        self.tui_app.run()


# Convenience function to create a TUI
def create_tui(domain: str, output_dir: Path, scanning_callback=None) -> TUIWrapper:
    """Create and return a TUI wrapper instance"""
    return TUIWrapper(domain, output_dir, scanning_callback)
