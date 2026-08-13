# linuxcnc-gcode-server

A high-performance C++ TCP socket server and Python REST API Gateway for **LinuxCNC**, providing remote G-code execution, machine control, OpenPNP integration, and a complete suite of single-axis rotary table control interfaces (Web Dashboard, Tkinter Desktop App, Python IDLE Shell, and Python SDK).

---

## 🌟 Features Overview

- **C++ Socket Server (`linuxcnc-gcode-server`)**:
  - Direct LinuxCNC interface via NML socket buffer.
  - Custom G-code extensions: `M114` (position readout), `M114_JSON` (structured JSON position), `M115` (firmware query), `M105` (analog input sensing), `M400` (synchronization lock).
  - Machine Control Commands: `STATUS`, `STATUS_JSON`, `ENABLE`, `DISABLE`, `HOME`, `ABORT`, `MANUAL`, `MDI`, `OPEN`, `RUN`, `PAUSE`, `RESUME`, `FILE`.
  - Motion Blending & Subroutine Buffering (`BEGINSUB` / `ENDSUB`): Solves MDI motion blending issues by compiling command batches into temporary O-code subroutines, with automatic timeout auto-flush (`-t`).
  - Headless startup mode (`-e`) for automatic ESTOP reset and homing on boot.

- **Zero-Dependency Python REST API Gateway (`python-api-gateway/app.py`)**:
  - Built using Python standard library (`http.server`, `socketserver`), requiring **no 3rd-party pip packages**.
  - Comprehensive REST API for position monitoring, machine state query, absolute/relative move execution, step jogging, preset moves, power control, and raw G-code.
  - Persistent TCP socket connection to C++ server with automatic reconnect and thread safety.
  - **Mock Mode** (`MOCK_MODE=true`): Full API & Web UI simulation mode for offline development and testing without LinuxCNC hardware.
  - Integrated static web server serving the Web UI.

- **Modern Web Dashboard UI (`web/index.html`)**:
  - Responsive dark-mode interface built with Vanilla CSS, Inter, and JetBrains Mono typography.
  - Real-time 36px monospace position readout with 200ms polling.
  - Dynamic status badges: Connection state (`Connected` / `Offline`), Homing status (`HOMED` / `NOT HOMED`), and Machine power state (`ENABLED` / `DISABLED` / `ESTOP`).
  - Motion Speed & Feedrate Controls: Quick presets (`300°/min` to `3600°/min` + `RAPID G0`), synchronized range slider, and direct numeric input.
  - Quick Angle Presets (-720° to +720°), step jog selector (`0.1°` to `360°`), and target position move input.

- **Tkinter Desktop GUI (`gui/tkinter_app.py`)**:
  - Standalone desktop application with live angle readout, quick presets, step jogging, target position moves, and machine action controls.

- **Interactive Python Shell / IDLE Module (`rotary.py`)**:
  - REPL-friendly commands for Python IDLE (`pos()`, `move(360)`, `move_rel(45)`, `preset(90)`, `jog_cw(10)`, `jog_ccw(10)`, `home()`, `enable()`, `abort()`, `status()`, `gcode()`).

- **Zero-Dependency Python Client SDK (`python-api-gateway/client.py`)**:
  - `RotaryTableClient` SDK for programmatic integration into hardware-in-the-loop (HIL) test harnesses (`pytest`, `unittest`).

- **Raspberry Pi & Zero-IP Systemd Setup**:
  - Native headless execution with `DISPLAY = dummy`.
  - Avahi mDNS broadcast (`rotary-table.local`).
  - Systemd background services (`linuxcnc.service`, `linuxcnc-gcode-server.service`, `rotary-api-gateway.service`).

- **Automated Test Suite (`tests/test_api.py`)**:
  - `unittest` suite verifying REST API endpoints, Python SDK, and IDLE shell module using Mock Mode.

---

## ⚡ Quick Start & System Setup

### 1. Configure LinuxCNC Machine `.ini` File
Set `DISPLAY = dummy` under the `[DISPLAY]` section in your machine `.ini` file (e.g. `rotary_table.ini`). This allows LinuxCNC to run natively without requiring a graphical display server.

```ini
[DISPLAY]
DISPLAY = dummy
```

### 2. Build & Launch System
```bash
# 0. Kill any stale LinuxCNC processes
make stop

# 1. Start LinuxCNC background engine
echo "Y" | linuxcnc /path/to/your/rotary_table.ini

# 2. Build and start C++ G-Code Server (Port 5007)
make
./linuxcnc-gcode-server -p 5007 -i /path/to/your/rotary_table.ini

# 3. Start Python REST Gateway & Web UI (Port 8000)
python3 python-api-gateway/app.py
```

### 3. Launch in Offline Mock Mode (No Hardware Required)
To run and develop without LinuxCNC hardware connected:
```bash
MOCK_MODE=true python3 python-api-gateway/app.py
```

### 4. Access Interfaces
- 🌐 **Web Dashboard**: Open [http://localhost:8000](http://localhost:8000) in your browser.
- 🖥️ **Tkinter Desktop GUI**: Run `python3 gui/tkinter_app.py`.
- 🐍 **Interactive Python IDLE**:
  ```python
  >>> from rotary import *
  >>> pos()            # Read angle: 0.00°
  >>> move(360)        # Move to 360° (G0 A360)
  >>> jog_cw(10)       # Jog +10° CW
  >>> home()           # Home A-axis
  ```
- 🧪 **Python SDK for Automated Testing**:
  ```python
  from client import RotaryTableClient
  client = RotaryTableClient("http://localhost:8000")
  client.move_to(180.0)
  ```

---

## 🛠️ C++ G-Code Server & Operator Commands

The C++ server listens on TCP port `5007` (default) and executes G-code MDI commands or server management directives.

### Server Command-Line Arguments
| Option | Long Option | Description |
| :--- | :--- | :--- |
| `-p <port>` | `--port` | Sets TCP listen port (default: `5007`). |
| `-e` | `--enable` | Auto-clears ESTOP, turns machine state ON, and homes all axes on startup. |
| `-i <inifile>`| `--inifile` | Specifies machine `.ini` file path (required for axis count and subroutine batching). |
| `-t <ms>` | `--timeout` | Sets auto-send batch timeout in milliseconds (default: `250`). |
| `-h` | `--help` | Displays CLI usage instructions. |

### Non-Standard & Extended Commands
- **`M115`**: Firmware query. Returns `ok FIRMWARE_NAME:linuxcnc-gcode, FIRMWARE_VERSION:0.1`.
- **`M114`**: Position query. Returns `ok X:0.000000 Y:0.000000 Z:0.000000 A:0.000000`.
- **`M114_JSON`**: Structured JSON position query. Returns `{"ok":true,"x":0.0,"y":0.0,"z":0.0,"a":180.0,"homed":true,"state":"ON"}`.
- **`M105`**: Reads first 4 analog inputs (`motion.analog-in-00` through `03`).
- **`M400`**: Defer subsequent execution until machine completes current movement and becomes idle.
- **`BEGINSUB` / `ENDSUB`**: Groups move commands into a buffered O-code subroutine batch for seamless G64 blending.

### LinuxCNC Operator Commands
- **`STATUS`**: Returns plaintext status string (ESTOP/ON, mode, homed joints, workspace position).
- **`STATUS_JSON`**: Returns structured JSON machine status dictionary (`state`, `mode`, `homed` array, `workspace` coordinates).
- **`ENABLE`**: Clears ESTOP and turns machine power ON.
- **`DISABLE`**: Powers machine OFF / triggers ESTOP.
- **`HOME` / `HOME <axis_index>`**: Homes all axes (or a specific axis index, e.g. `HOME 3`).
- **`ABORT`**: Immediately stops active machine movement.
- **`MANUAL`**: Switches LinuxCNC task mode to Manual mode.
- **`MDI`**: Switches LinuxCNC task mode to MDI mode (automatically invoked during G-code execution).
- **`OPEN <filename>`**: Opens specified G-code file.
- **`RUN`**: Starts program execution.
- **`PAUSE` / `RESUME`**: Pauses and resumes program execution.
- **`FILE`**: Displays currently open file path.

---

## 🌐 REST API Gateway (`/api/v1/`)

The REST Gateway runs on port `8000` (default) and translates JSON HTTP requests into C++ server commands.

| Endpoint | Method | Payload Example | Description |
| :--- | :--- | :--- | :--- |
| `/api/v1/position` | `GET` | — | Returns current angle, homing state, and machine status. |
| `/api/v1/status` | `GET` | — | Returns detailed machine status dictionary. |
| `/api/v1/move` | `POST` | `{"position": 360, "mode": "absolute", "feedrate": 1200}` | Executes absolute or relative move (`G90`/`G91`, `G0`/`G1`). Position constrained to [-720°, +720°]. |
| `/api/v1/jog` | `POST` | `{"direction": 1, "step": 10.0, "feedrate": 1200}` | Performs step jog CW (+1) or CCW (-1). |
| `/api/v1/preset` | `POST` | `{"preset_deg": 90, "feedrate": 1200}` | Moves table to preset angle. |
| `/api/v1/home` | `POST` | `{}` | Homes A-axis. |
| `/api/v1/enable` | `POST` | `{}` | Clears ESTOP and enables machine power. |
| `/api/v1/disable` | `POST` | `{}` | Disables machine power. |
| `/api/v1/abort` | `POST` | `{}` | Aborts motion immediately. |
| `/api/v1/gcode` | `POST` | `{"gcode": "G0 A180"}` | Executes raw G-code string. |

---

## 🖥️ User Interfaces

### 1. Web Dashboard (`web/index.html`)
Open `http://localhost:8000` in any web browser to access the control dashboard:
- **Numeric Position Readout**: Large 36px monospace display showing real-time angle.
- **Status Badges**: Live connection status, homing state (`HOMED`/`NOT HOMED`), and power state (`ENABLED`/`DISABLED`/`ESTOP`).
- **Feedrate Control**: Select preset move speeds (`300°/min` to `3600°/min` or `RAPID G0`), sync with range slider or numeric feedrate input.
- **Presets Grid**: One-click move to `-720°`, `-360°`, `-180°`, `-90°`, `0°`, `90°`, `180°`, `360°`, `720°`.
- **Step Jogging**: Select step increment (`0.1°`, `1.0°`, `10.0°`, `45.0°`, `90.0°`, `180°`, `360°`) and jog CW / CCW.

### 2. Tkinter Desktop GUI (`gui/tkinter_app.py`)
Launch with:
```bash
python3 gui/tkinter_app.py
```
Provides a standalone native desktop window with real-time background position polling thread, presets, step jogging, target angle entry, and machine controls.

### 3. Interactive Python IDLE Module (`rotary.py`)
Launch Python IDLE or interactive REPL:
```python
>>> from rotary import *
>>> pos()            # Read position in degrees
>>> move(360)        # Absolute move to 360°
>>> move_rel(-45)    # Relative move -45°
>>> preset(180)      # Move to preset 180°
>>> jog_cw(10)       # Step jog CW by 10°
>>> jog_ccw(5)       # Step jog CCW by 5°
>>> home()           # Home A-axis
>>> enable()         # Enable machine power
>>> abort()          # Abort motion
>>> status()         # Print detailed machine status
>>> gcode("G0 A90")  # Send raw G-code
```

### 4. Zero-Dependency Python SDK (`python-api-gateway/client.py`)
Integrate into test scripts:
```python
from client import RotaryTableClient

table = RotaryTableClient("http://localhost:8000")
table.enable()
table.home()
table.move_to(360.0, feedrate=1200)
print("Current position:", table.get_position())
```

---

## 🧪 Automated Testing

An automated test suite is provided in `tests/test_api.py`. It runs the REST API Gateway in **Mock Mode**, verifying all SDK methods and IDLE module commands without hardware.

Run tests:
```bash
python3 -m unittest tests/test_api.py
```

---

## 🚀 Raspberry Pi Headless & Systemd Deployment

### 1. Avahi (mDNS) Zero-IP Network Access
Install Avahi daemon to allow zero-IP network resolution via **`rotary-table.local`**:

```bash
sudo apt update && sudo apt install -y avahi-daemon avahi-utils
sudo hostnamectl set-hostname rotary-table

# Copy mDNS service broadcast definition
sudo cp configs/avahi/rotarytable.service /etc/avahi/services/
sudo systemctl restart avahi-daemon
```

### 2. Install Systemd Services
Three systemd service files are provided in `configs/systemd/`:
1. `linuxcnc.service`: Manages LinuxCNC core engine.
2. `linuxcnc-gcode-server.service`: Manages C++ NML socket server.
3. `rotary-api-gateway.service`: Manages Python REST API Gateway & Web UI.

Edit the `.ini` file paths in `linuxcnc.service` and `linuxcnc-gcode-server.service` to point to your machine `.ini` file, then enable them:

```bash
sudo cp configs/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now linuxcnc.service
sudo systemctl enable --now linuxcnc-gcode-server.service
sudo systemctl enable --now rotary-api-gateway.service
```

Once active, access your system network-wide:
- 🌐 **Web Dashboard**: `http://rotary-table.local:8000`
- 🖥️ **Tkinter App**: Connects to `http://rotary-table.local:8000`
- 🧪 **Python SDK**: `RotaryTableClient("http://rotary-table.local:8000")`

---

## 🎯 OpenPNP Integration Guide

Set up a `GCodeDriver` in OpenPNP:

![OpenPNP Driver Setup](https://www.iforce2d.net/tmp/openpnp/Selection_1177.png)

Clicking `Detect Firmware` under `Driver Settings` returns:  
`ok FIRMWARE_NAME:linuxcnc-gcode, FIRMWARE_VERSION:0.1`

### Recommended OpenPNP Regexes & Commands
- **COMMAND_CONFIRM_REGEX**: `^ok.*`
- **POSITION_REPORT_REGEX**: `^ok X:(?<x>-?\d+\.\d+) Y:(?<y>-?\d+\.\d+) Z:(?<z>-?\d+\.\d+) A:(?<rotation>-?\d+\.\d+)`
- **COMMAND_ERROR_REGEX**: `^error:.*`
- **ACTUATE_BOOLEAN_COMMAND**: `M{True:64}{False:65} P0` (controls `motion.digital-out-00`)
- **MOVE_TO_COMMAND**: `G1 {X:X%.3f} {Y:Y%.3f} {Z:Z%.3f} {A:A%.4f} {FeedRate:F%.0f}`
- **MOVE_TO_COMPLETE_COMMAND**: `M400`
- **ACTUATOR_READ_COMMAND**: `M105`
- **ACTUATOR_READ_REGEX**: `^ok.* T2:(?<Value>-?\d+\.\d+)`

### Dynamic Acceleration (M171 User M-Code Script)
To allow OpenPNP to dynamically adjust acceleration, configure `MOVE_TO_COMMAND` to send `M171 P[accel]`.

Create an executable file named `M171` (no extension) in the directory defined by `PROGRAM_PREFIX` in your `.ini` file:

```bash
#!/bin/bash
acceleration=$1
halcmd setp ini.x.max_acceleration $acceleration
halcmd setp ini.y.max_acceleration $acceleration
halcmd setp ini.z.max_acceleration $acceleration
exit 0
```

---

## 🔄 Motion Blending & Subroutine Buffering

LinuxCNC blends consecutive line segments when `G64` is active. However, commands sent individually via MDI can suffer timing jitter that breaks blending in 20–30% of cases.

### Using `BEGINSUB` and `ENDSUB`
Grouping moves inside `BEGINSUB` and `ENDSUB` stores commands in a buffer and sends them as a cohesive O-code subroutine:

```gcode
beginsub
g1 x10 y20
g1 x25 y25
g1 x40 y20
endsub
```

Subroutines are created in the path defined by `RS247NGC:SUBROUTINE_PATH` in your `.ini` file. For best disk lifespan, point `SUBROUTINE_PATH` to a RAM filesystem (e.g. `/run/user/1000`).

When jogging in OpenPNP without issuing `MOVE_TO_COMPLETE_COMMAND`, the server's auto-send batch timeout (`-t <ms>`, default 250ms) automatically flushes and executes pending move batches.

---

## 🏗️ Building & Process Management

### Build Requirements
Requires LinuxCNC development headers (`linuxcnc-uspace-dev` or equivalent) and `g++`.

```bash
# Build C++ binary
make

# Clean build artifacts
make clean

# Emergency stop & kill all LinuxCNC/server background processes
make stop
```

---

## 📄 License
Released under standard open-source licensing. See [LICENSE](LICENSE) for details.
