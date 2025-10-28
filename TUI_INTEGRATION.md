# DeepDomain TUI Integration

This document describes the Textual-based TUI (Terminal User Interface) integration for DeepDomain.

## Overview

The TUI provides a modern, interactive interface for DeepDomain that replaces the traditional console output with a split-screen layout:

- **Left Panel (1/3)**: Status updates, phase information, and progress tracking
- **Right Panel (2/3)**: Live command output streaming

## Features

### Status Panel
- Real-time phase updates (Reconnaissance, Scanning, Enumeration)
- Progress bar showing overall completion
- Timestamped status messages with icons
- Scrollable message history (last 20 messages visible)

### Live Output Panel
- Real-time streaming of command output
- Current command display
- Scrollable output history (last 1000 lines)
- Syntax highlighting for better readability

### Controls
- `q` - Quit the application
- `c` - Clear output panel
- `r` - Clear status messages
- `s` - Toggle status panel visibility

## Architecture

### Core Components

1. **DeepDomainTUI**: Main Textual application class
2. **StatusPanel**: Left panel for status updates
3. **LiveOutputPanel**: Right panel for command output
4. **TUIWrapper**: Simple interface for integration with existing code
5. **Execute**: Enhanced with TUI integration for live output

### Integration Points

The TUI integrates seamlessly with the existing DeepDomain workflow:

1. **CLI Integration**: `cli.py` starts the TUI after tool checks
2. **Command Execution**: `execute.py` streams output to TUI
3. **Phase Management**: Each phase updates the TUI with progress and status

## Usage

### Basic Usage

The TUI is automatically started when running DeepDomain:

```bash
deepdomain run -d example.com -o ./output
```

### Programmatic Usage

```python
from src.tui import create_tui
from src.execute import Execute

# Create TUI
tui = create_tui("example.com", Path("./output"))
tui.start()

# Create executor with TUI integration
executor = Execute(workdir=Path("./output"), tui=tui)

# Run commands with live output
stdout, stderr, returncode = executor.run_command("nmap -sS example.com")
```

### Async Command Execution

```python
def callback(stdout, stderr, returncode):
    print(f"Command completed: {returncode}")

# Run command asynchronously
executor.run_command_async("long-running-command", callback)
```

## Implementation Details

### Live Output Streaming

The TUI uses subprocess with real-time output streaming:

```python
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

# Stream output line by line
while True:
    output = process.stdout.readline()
    if output == '' and process.poll() is not None:
        break
    if output:
        self.add_command_output(output)
```

### Status Management

Status updates are managed through the TUI wrapper:

```python
# Update current phase
tui.update_phase("Reconnaissance Phase", 30)

# Add status message
tui.add_status_message("Starting subdomain discovery...", "info")
tui.add_status_message("Subdomain discovery complete", "success")
```

### Thread Safety

The TUI runs in a separate thread to avoid blocking the main execution:

```python
def run_tui():
    self.tui_app.run()

self.tui_thread = threading.Thread(target=run_tui, daemon=True)
self.tui_thread.start()
```

## Dependencies

The TUI requires the following additional dependency:

```
textual>=0.44.0
```

This is automatically included in the updated `pyproject.toml`.

## Error Handling

The TUI includes comprehensive error handling:

1. **Fallback Mode**: If TUI fails to start, falls back to regular console output
2. **Process Management**: Tracks and can terminate running processes
3. **Graceful Shutdown**: Properly cleans up resources on exit

## Future Enhancements

### Planned Features

1. **Concurrent Command Execution**: Support for running multiple commands simultaneously
2. **Output Filtering**: Filter command output by type (stdout/stderr)
3. **Command History**: Save and replay command history
4. **Custom Themes**: Support for different color themes
5. **Export Functionality**: Export TUI output to files

### Concurrent Execution Support

The architecture is designed to support concurrent command execution as mentioned in the requirements:

```python
# Future implementation for concurrent execution
def run_concurrent_commands(self, commands: List[str]):
    """Run multiple commands concurrently with live output"""
    for command in commands:
        self.run_command_async(command, self._command_callback)
```

## Troubleshooting

### Common Issues

1. **TUI Not Starting**: Check if Textual is properly installed
2. **Output Not Streaming**: Verify command is producing output
3. **Performance Issues**: Reduce max_lines in LiveOutputPanel

### Debug Mode

Enable debug mode by setting environment variable:

```bash
export DEEPDOMAIN_DEBUG=1
deepdomain run -d example.com
```

## Testing

Run the test script to verify TUI functionality:

```bash
python test_tui.py
```

This will test:
- TUI initialization
- Status updates
- Command execution
- Live output streaming
- Async command execution

## Contributing

When contributing to the TUI:

1. Follow Textual best practices
2. Maintain thread safety
3. Add proper error handling
4. Update tests for new features
5. Document new functionality

## License

The TUI integration follows the same MIT license as the main DeepDomain project.
