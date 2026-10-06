# Universal Application State Lifecycle Contract

## Overview

The Universal Application State Lifecycle standard (`taskand.app-state/v1`) defines canonical checkpointing, rollback, and closed-loop resume contracts for stateful external applications (GUI, TUI, Browser, Daemons) within `taskand` task execution graphs.

## Supported Application Kinds

1. **`gui_x11`**:
   - Manages X11 application state, EWMH window geometry, desktop indexing, class name, frame buffer hash, and baseline OCR text.
2. **`tui_terminal`**:
   - Manages interactive terminal sessions (e.g. AGY CLI sessions), terminal dimensions (columns/rows), PTY scrollback history, current working directory, process command line, and agent resume token.
3. **`browser_cdp`**:
   - Manages Chrome DevTools Protocol browser instances: tab hierarchy, active URL, session storage snapshot, form input cache, and viewport scroll coordinates.
4. **`service_daemon`**:
   - Manages systemd unit services: unit name, enabled state, PID, and environment variables.

## Closed-Loop Verification Assertions

To guarantee accurate resumption before downstream tasks proceed, checkpoints can declare verification assertions:
- `assertRfbDiff`: Compares Remote FrameBuffer visual state against a reference frame hash within an acceptable diff tolerance.
- `assertTuiScrollback`: Asserts expected pattern presence in terminal scrollback buffers.
- `assertWindowOcr`: Asserts recognized text matching in active application windows.
