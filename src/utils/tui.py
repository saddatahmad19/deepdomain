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
from rich.text import Text


class StatusPanel(ScrollableContainer):
    """Left panel showing status updates and phase information"""
    
    can_focus = True
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_phase = "Initializing"
        self.phase_progress = 0
        self.total_phases = 3
        
    def compose(self) -> ComposeResult:
        yield Label("DeepDomain Status", id="status-title")
        yield ProgressBar(total=100, show_eta=False, id="phase-progress")
        yield Label("", id="current-phase")
        yield RichLog(id="status-messages", wrap=True, highlight=True, markup=True)
    
    def update_phase(self, phase: str, progress: int = 0):
        """Update the current phase and progress"""
        self.current_phase = phase
        self.phase_progress = progress
        try:
            self.query_one("#current-phase", Label).update(f"Phase: {phase}")
            self.query_one("#phase-progress", ProgressBar).update(progress=progress)
        except:
            pass
    
    def add_status_message(self, message: str, msg_type: str = "info"):
        """Add a status message to the panel"""
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
        
        try:
            log = self.query_one("#status-messages", RichLog)
            log.write(formatted_msg)
        except:
            pass
    
    def clear_messages(self):
        """Clear all status messages"""
        try:
            self.query_one("#status-messages", RichLog).clear()
        except:
            pass


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
    """Main TUI application for DeepDomain"""
    
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
        self.running_processes = {}
        self.process_counter = 0
        self.scanning_callback = scanning_callback
        self.scanning_started = False
        
    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            self.status_panel = StatusPanel(id="status-panel")
            yield self.status_panel
            self.output_panel = LiveOutputPanel(id="output-panel")
            yield self.output_panel
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize the TUI when mounted"""
        self.status_panel.add_status_message(f"DeepDomain initialized for {self.domain}", "info")
        self.status_panel.add_status_message(f"Output directory: {self.output_dir}", "info")
        self.status_panel.update_phase("Ready", 0)
        
        # Start scanning after a brief delay
        if self.scanning_callback and not self.scanning_started:
            self.scanning_started = True
            self.set_timer(1.0, self.start_scanning)
    
    def start_scanning(self):
        """Start the scanning process"""
        if self.scanning_callback:
            try:
                self.scanning_callback(self)
            except Exception as e:
                self.add_status_message(f"Scanning error: {str(e)}", "error")
    
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
        """Update the current phase - thread-safe"""
        if self.status_panel:
            try:
                # Try to update directly first (if on main thread)
                self.status_panel.update_phase(phase, progress)
            except:
                # If that fails, we're on a background thread - use call_from_thread
                try:
                    self.call_from_thread(self.status_panel.update_phase, phase, progress)
                except:
                    pass
    
    def add_status_message(self, message: str, msg_type: str = "info"):
        """Add a status message - thread-safe"""
        if self.status_panel:
            try:
                # Try to update directly first (if on main thread)
                self.status_panel.add_status_message(message, msg_type)
            except:
                # If that fails, we're on a background thread - use call_from_thread
                try:
                    self.call_from_thread(self.status_panel.add_status_message, message, msg_type)
                except:
                    pass
    
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
    
    def run_command_live(self, command: str, workdir: Path) -> tuple[str, str, int]:
        """
        Run a command with live output streaming to the TUI.
        Returns (stdout, stderr, returncode)
        This method should be called from a background thread.
        """
        # Use call_from_thread to safely update UI from background thread
        self.call_from_thread(self.start_command, command)
        
        try:
            # Start the process
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=workdir,
                bufsize=1,
                universal_newlines=True
            )
            
            # Store process reference
            self.process_counter += 1
            process_id = self.process_counter
            self.running_processes[process_id] = process
            
            stdout_lines = []
            stderr_lines = []
            
            # Read output line by line
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    stdout_lines.append(output.strip())
                    # Use call_from_thread for thread-safe UI updates
                    self.call_from_thread(self.add_command_output, output)
                
                # Also read stderr
                error = process.stderr.readline()
                if error:
                    stderr_lines.append(error.strip())
                    # Use call_from_thread for thread-safe UI updates
                    self.call_from_thread(self.add_command_output, error)
            
            # Wait for process to complete
            return_code = process.wait()
            
            # Clean up
            if process_id in self.running_processes:
                del self.running_processes[process_id]
            
            # Use call_from_thread for thread-safe UI updates
            self.call_from_thread(self.finish_command)
            
            return '\n'.join(stdout_lines), '\n'.join(stderr_lines), return_code
            
        except Exception as e:
            error_msg = f"Error running command: {str(e)}"
            self.call_from_thread(self.add_command_output, error_msg)
            self.call_from_thread(self.finish_command)
            return "", str(e), 1
    
    def run_command_async(self, command: str, workdir: Path, callback: Optional[Callable] = None) -> None:
        """
        Run a command asynchronously with live output streaming.
        The callback will be called with (stdout, stderr, returncode) when complete.
        """
        def run_in_thread():
            try:
                result = self.run_command_live(command, workdir)
                if callback:
                    callback(*result)
            except Exception as e:
                if callback:
                    callback("", str(e), 1)
        
        thread = threading.Thread(target=run_in_thread, daemon=True)
        thread.start()
    
    def stop_all_processes(self):
        """Stop all running processes"""
        for process in self.running_processes.values():
            try:
                process.terminate()
            except:
                pass
        self.running_processes.clear()


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
            self.tui_app.stop_all_processes()
            self.tui_app.exit()
            self.tui_running = False
    
    def update_phase(self, phase: str, progress: int = 0):
        """Update the current phase - thread-safe"""
        if self.tui_app and self.tui_running:
            try:
                # Use the TUI app's thread-safe method
                self.tui_app.update_phase(phase, progress)
            except:
                # Queue for later if update fails
                self._phase_queue.append((phase, progress))
        else:
            # Queue for later if TUI not ready
            self._phase_queue.append((phase, progress))
    
    def add_status_message(self, message: str, msg_type: str = "info"):
        """Add a status message - thread-safe"""
        if self.tui_app and self.tui_running:
            try:
                # Use the TUI app's thread-safe method
                self.tui_app.add_status_message(message, msg_type)
            except:
                # Queue for later if update fails
                self._status_queue.append((message, msg_type))
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
            self.tui_app.run_command_async(command, workdir, callback)
        else:
            # Fallback
            def run_fallback():
                result = self.run_command_live(command, workdir)
                if callback:
                    callback(*result)
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
