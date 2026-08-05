# linuxcnc-gcode-server
Allows connecting to a LinuxCNC installation and executing commands, similar to linuxcncrsh.

The motivation was to allow easier control by OpenPNP. To this end some non-standard (for LinuxCNC) commands will be intercepted and handled either within this server, or translated into something LinuxCNC can understand:
- M115 - firmware version
- M114 - current position
- M105 - read analog sensor
- M400 - wait for completion
- BEGINSUB - start batch
- ENDSUB - send batch

All other g-code commands will be passed through unchanged, and are relayed to LinuxCNC as MDI commands.

<br>

## Non-standard commands

These commands are to let OpenPNP fetch some information from the LinuxCNC side, and to help the synchronization between the two systems.

#### M115
No interaction with LinuxCNC. Returns a string like:  

`ok FIRMWARE_NAME:linuxcnc-gcode, FIRMWARE_VERSION:0.1`

#### M114
Returns the current position of the machine, eg.  

`ok X:1.200000 Y:3.400000 Z:5.600000 A:7.800000`

#### M105
Returns the values of the first four analog inputs (motion.analog-in-00 etc)  

`ok T0:0.147000 T1:0.7890000 T2:0.000000 T3:0.000000`

#### M400

This command will cause all subsequent commands to be deferred until the machine is idle.

#### BEGINSUB, ENDSUB
See the section below about blending.

<br>

## LinuxCNC operator commands

In addition to plain g-code, you can use the commands below to carry out some common operator actions. Note that some of these will be ignored if LinuxCNC is currently running a program.

#### status
Returns information about estop/machine status, task mode, axis homed, and work position, eg.:

`ESTOP MANUAL (0 0 0 0) -97.146500 -14.642751 2.000000 0.000000`

`ON MDI (1 1 1 1) 100.003510 -0.007745 0.005019 0.000000`

#### enable
Same as clearing estop and then toggling the machine on.
#### home
Same as clicking "home all" in Axis GUI. Already homed axes will be ignored. There is currently a ten second timeout, so if your homing takes longer this will incorrectly report a failure. To home an individual axis, add the axis index, eg. "home 0".
#### abort
Same as hitting ESC or the stop button in Axis GUI.
#### manual
Attempts to enter manual mode, which is necessary for manual jogging of axes.
#### mdi
Attempts to enter MDI mode. (MDI mode will automatically be entered when giving g-code commands.)
#### open &lt;filename&gt;
Attempts to open the given gcode file. You must specify the full path for the file.
#### run
Same as clicking the run button in Axis GUI.
#### pause
Same as clicking the pause button in Axis GUI.
#### resume
Same as resuming after a pause in Axis GUI.
#### file
Displays the currently loaded filename

<br>

## Building

Requires the LinuxCNC headers and libs available. On my system I built LinuxCNC from source which produced the package "linuxcnc-uspace-dev", which I then installed. Not sure how you would get this by other methods...

With the requirements in place, you should be able to just run `make` to build.

This server uses NML to interface with LinuxCNC. It expects to find the NML definition file at /usr/share/linuxcnc/linuxcnc.nml which is probably where it will be unless you have really been messing around with things.

<br>

## Basic usage

First startup LinuxCNC, then run this server. By default it will listen on port 5007, or you can change this with the -p option, eg.

    ./linuxcnc-gcode-server -p 5050

To check connection to the server, you can use a telnet connection like:

    telnet 192.168.1.140 5007

If the machine is enabled and homed, you should be able to move it around with g-code commands.

![alt text](https://www.iforce2d.net/tmp/openpnp/Selection_1180.png)

You can use the -e option to instruct the machine to be enabled and homed when the server starts, eg.

    ./linuxcnc-gcode-server -e

This is the equivalent of clicking the e-stop button off and the machine power button on, and then homing each axis that is not already homed. This is probably not advisable on a real machine, but it's quite convenient during development when using a dummy machine, to save some repetitive clicking. It also allows you to run a headless LinuxCNC without any traditional user interface, and still enable the machine and run g-code.

You can optionally specify the .ini file of your machine with the -i parameter, eg.:

    ./linuxcnc-gcode-server -i /path/to/your/machine.ini

If you want to home the machine via this server then this parameter is not really optional because reading the .ini file is how the server obtains some basic information like how many axes your machine has. But if the machine is already homed, you can still use the server to run g-code and most other actions without giving the .ini file parameter.


<br>

## Video demo

You can see a video demonstrating basic usage here. Note that this video was made before some of the options mentioned above existed. For best results please specify your machine .ini file with the -i option when starting the server to know basic but important info like how many axes there are :)

[![Watch the video](https://img.youtube.com/vi/ib_G0eyn5FM/hqdefault.jpg)](https://www.youtube.com/embed/ib_G0eyn5FM)

See the 'headless' subfolder of this repository for the startup/shutdown scripts used in the video.

<br>

## Usage with OpenPNP

Set up a GCodeDriver like this:

![alt text](https://www.iforce2d.net/tmp/openpnp/Selection_1177.png)

In the `Driver Settings` tab, clicking on `Detect Firmware` should show some output like this:

![alt text](https://www.iforce2d.net/tmp/openpnp/Selection_1179.png)

If the gcode server is stopped and restarted, OpenPNP will lose communication with it. You can let it re-connect by clicking the power button off, then on again.

![alt text](https://www.iforce2d.net/tmp/openpnp/Selection_1181.png)

Note that OpenPNP does not read the current position of the machine when connecting, so if the machine was moved by commands outside OpenPNP, they will not be in sync until OpenPNP issues the next move command.

<br>

Some commonly used settings are listed below (see OpenPNP's [GcodeDriver Command Reference](https://github.com/openpnp/openpnp/wiki/GcodeDriver_Command-Reference) for more details).


### COMMAND_CONFIRM_REGEX

The standard rule as suggested by OpenPNP is fine:

    ^ok.*

<br>

### POSITION_REPORT_REGEX

The standard rule as suggested by OpenPNP is fine:

    ^ok X:(?<x>-?\d+\.\d+) Y:(?<y>-?\d+\.\d+) Z:(?<z>-?\d+\.\d+) A:(?<rotation>-?\d+\.\d+)

<br>

### COMMAND_ERROR_REGEX

The standard rule as suggested by OpenPNP is fine:

    ^error:.*

<br>

### ACTUATE_BOOLEAN_COMMAND

You can use LinuxCNC's standard M64 and M65 to switch digital outputs on and off. The value P0, P1 etc maps to motion.digital-out-00, motion.digital-out-01 etc. There are various formats that will work for defining this in OpenPNP, I have found this style works ok:

    M{True:64}{False:65} P0

<br>

### MOVE_TO_COMMAND

OpenPNP will probably suggest something like this which will work fine:

    G1 {X:X%.3f} {Y:Y%.3f} {Z:Z%.3f} {A:A%.4f} {FeedRate:F%.0f}

<br>

### MOVE_TO_COMPLETE_COMMAND

This should be set to M400:

    M400

<br>

### ACTUATOR_READ_COMMAND
I have not tested this, but I think it would be just:

    M105

This will always return four values, for motion.analog-in-00, motion.analog-in-01 etc.

<br>

### ACTUATOR_READ_REGEX
I have not tested this, but I think it would be like:

    ^ok T0:(?<Value>-?\d+\.\d+)

That would be ok if you wanted to read motion.analog-in-00. But because M105 always returns multiple values, to read T1, T2 etc. you would need a a little extra .* in the regex to skip any preceding values:

    ^ok.* T2:(?<Value>-?\d+\.\d+)

<br>

## Setting acceleration

To have OpenPNP specify acceleration for moves, the `Motion Control Type` option in the `Driver Settings` tab must be set to a type that controls acceleration, eg. EuclideanAxisLimits, ConstantAcceleration. Then in the MOVE_TO_COMMAND definition you can prepend a rule to output an acceleration setting, for example:

![alt text](https://www.iforce2d.net/tmp/openpnp/Selection_1182.png)

This will produce a g-code command like `M171 P125`. The M171 is not a standard g-code, it is a [user defined command](https://linuxcnc.org/docs/devel/html/gcode/m-code.html#mcode:m100-m199) that you must create on the LinuxCNC machine. The exact number 171 is not really important, it just needs to be from 100 to 199.

To create the user defined command, you need to make a bash script with the same name, no extension, upper-case M. For this example the file name would be "M171". This script must be placed in the directory specified by PROGRAM_PREFIX in your LinuxCNC .ini file:

![alt text](https://www.iforce2d.net/tmp/openpnp/Selection_1183.png)

The contents of this bash script should be:

    #!/bin/bash
    acceleration=$1
    halcmd setp ini.x.max_acceleration $acceleration
    halcmd setp ini.y.max_acceleration $acceleration
    halcmd setp ini.z.max_acceleration $acceleration
    exit 0

<br>

## Blending
LinuxCNC is capable of blending consecutive segments together when G64 is in effect, but unfortunately sending commands via the MDI interface does not always allow this to happen. In my experiments, blending typically occurs in only 70-80% of cases where it would normally be expected. This is due to the lack of synchronization between the timing of commands entering the queue, and when those commands are allowed to start execution. For example if you issue two MDI commands and the machine starts executing the first one before the second has been received, blending cannot occur.

To work around this problem, multiple commands can be grouped into a batch for processing as a cohesive set by enclosing them inside `beginsub` and `endsub` keywords. This will cause the commands to be stored in a buffer and only sent to LinuxCNC when all commands of the group are known, and full blending can be achieved reliably. For example with this input:

    beginsub
    g1 x10 y20
    g1 x25 y25
    g1 x40 y20
    endsub

... nothing would happen until the `endsub`, at which point all the commands will be sent.

To ensure that the grouped commands are all processed together, a temporary [o-code subroutine](https://linuxcnc.org/docs/html/gcode/o-code.html) file is created and executed. This file will be created in the location specified by the RS247NGC:SUBROUTINE_PATH property of your .ini file:

![alt text](https://www.iforce2d.net/tmp/openpnp/Selection_1184.png)

Since the subroutine file is only temporary and will be written and read potentially thousands of times during a pick and place job, it might be preferable to place it in RAM instead of on hard disk. You can find some info about which paths to use in [this Stack Overflow discussion](https://stackoverflow.com/questions/10982911/creating-temporary-files-in-bash). In the screenshot above, the /run/user/1000 path is actually a RAM location, and as such all the 'files' it contains will be lost when the computer is shut down. So if you already have your own subroutine files, you might actually want to use a normal hard disk location, or maybe copy them into the RAM location each time you start LinuxCNC.

Because SUBROUTINE_PATH is defined in your .ini file, to use this feature you must provide the .ini file when starting the server, eg.:

    ./linuxcnc-gcode-server -i /path/to/your/machine.ini

You can check if these paths are correct when the server starts up:

![alt text](https://www.iforce2d.net/tmp/openpnp/Selection_1186.png)

Finally, to let OpenPNP manage these batches of commands, you can set up your `MOVE_TO_COMMAND` and `MOVE_TO_COMPLETE_COMMAND` so that a batch will be started before moves are issued, and finalized before the M400 'wait' command :

![alt text](https://www.iforce2d.net/tmp/openpnp/Selection_1189.png)

![alt text](https://www.iforce2d.net/tmp/openpnp/Selection_1190.png)

A `beginsub` while a batch is already in progress has no effect.

When using the OpenPNP user interface to jog the machine, the MOVE_TO_COMPLETE_COMMAND is not used, so there will be no `endsub` to complete the batch. To workaround this, a timeout is used to automatically send the batch to LinuxCNC if no further commands are given within a certain time. The default timeout is 250ms, you can change this with the -t parameter:

    ./linuxcnc-gcode-server -t 750

<b>Note:</b> even when using batches to process commands as a group, there are still other factors that can interrupt blending, like the M64/M65
commands or setting the acceleration via bash script as mentioned above.

<b>Note:</b> the commands within a `beginsub`/`endsub` block are passed to LinuxCNC without any special handling, so you cannot use the 'non-standard' commands (M115, M114, M105, M400). These will be ignored inside a batch.

<br>

## Multiple clients

Although this server is capable of communicating with multiple clients at the same time, that's not really the intended use case. The main issue is that the `beginsub` / `endsub` status is tracked globally on the server, not per client. So one client can start the batch and a different client could end it. If you want to switch between using different clients, just make sure there is no ongoing subroutine batch.

<br>

## Single-Axis Rotary Table Control (REST API, Web UI, Tkinter GUI & IDLE)

This codebase includes a single-axis (A-axis) rotary table controller system with a complete suite of interfaces:

1. **Python REST API Gateway** ([python-api-gateway/app.py](python-api-gateway/app.py)): Standard-library HTTP REST server allowing external systems (e.g. Python test runners) to query and command the rotary table.
2. **Web Dashboard** ([web/index.html](web/index.html)): Modern browser UI featuring a visual circular dial gauge, position readout in degrees, quick preset grid (0° to 360°), step jog controls (+ / -), and safety buttons.
3. **Tkinter Desktop GUI** ([gui/tkinter_app.py](gui/tkinter_app.py)): Standalone desktop application with live position readout, jog controls, preset buttons, and manual G-code entry.
4. **Interactive Python IDLE Module** ([rotary.py](rotary.py)): Interactive shell module for Python IDLE/REPL. All commands route through the REST Gateway to maintain identical behavior across all interfaces.
5. **Zero-Dependency Python SDK** ([python-api-gateway/client.py](python-api-gateway/client.py)): `RotaryTableClient` SDK for programmatic integration into Python test suites.

---

### System Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                   External Python Test System / IDLE                     │
└──────────────────────────────────────────────────────────────────────────┘
                                     │ (REST API / client.py)
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    Python REST Gateway (app.py)                          │
│                                                                          │
│  - GET  /api/v1/position    -> Read table angle in degrees (e.g. 180°) │
│  - POST /api/v1/move        -> Absolute/Relative move (G0 A<angle>)     │
│  - POST /api/v1/jog         -> Step jog + / -                           │
│  - POST /api/v1/preset      -> Move to quick preset angle                 │
│  - POST /api/v1/home        -> Home A-axis                              │
│  - POST /api/v1/enable      -> Clear ESTOP & enable machine             │
│  - POST /api/v1/abort       -> Abort motion                             │
└──────────────────────────────────────────────────────────────────────────┘
           │                                          │
           ▼ (HTTP / Localhost)                       ▼ (TCP Socket / JSON)
┌──────────────────────────────────────┐   ┌──────────────────────────────┐
│  Web Dashboard / Tkinter Desktop App │   │  LinuxCNC NML Core Server    │
│  (index.html / tkinter_app.py)       │   │  (linuxcnc-gcode-server)     │
└──────────────────────────────────────┘   └──────────────────────────────┘
```

---

### Simplified System Setup

#### 1. Set `DISPLAY = dummy` in your Machine `.ini` File
Open your machine configuration `.ini` file (e.g. `rotary_table.ini`) and set `DISPLAY = dummy` under the `[DISPLAY]` section:

```ini
[DISPLAY]
DISPLAY = dummy
```
This instructs LinuxCNC to run natively without attempting to open any graphical window, eliminating the need for complex wrapper scripts or virtual display servers.

#### 2. Manual CLI Launch
If running manually from terminal:

```bash
# 0. Kill any leftover background processes from previous runs
make stop

# 1. Start LinuxCNC background engine (piping 'Y' prevents hanging on 'Restart it? [Y/n]')
echo "Y" | linuxcnc /path/to/your/rotary_table.ini &

# 2. Build and start C++ G-Code Server
make
./linuxcnc-gcode-server -p 5007 -e -i /path/to/your/rotary_table.ini &

# 3. Start Python REST Gateway & Web UI
python3 python-api-gateway/app.py
```

#### 3. Control via Web Dashboard, Tkinter GUI, or IDLE
- **Web Dashboard**: Navigate to [http://localhost:8000](http://localhost:8000)
- **Tkinter Desktop GUI**: `python3 gui/tkinter_app.py`
- **Interactive Python IDLE**:
  ```python
  >>> from rotary import *
  >>> pos()            # Reads position: 0.00°
  >>> move(360)        # Executes G0 A360
  >>> jog_cw(10)       # Step jog +10° CW
  >>> home()           # Home A-axis
  ```
- **Python Automation SDK**:
  ```python
  from client import RotaryTableClient
  client = RotaryTableClient("http://localhost:8000")
  client.move_to(360.0)
  ```

<br>

---

## 🍓 Raspberry Pi Headless & Systemd Auto-Start Setup (Zero-IP Configuration)

To run the system on a Raspberry Pi as background services with **mDNS broadcasting** (`rotary-table.local`), follow these simple steps:

---

### 1. Install & Configure Avahi (mDNS)

```bash
sudo apt update && sudo apt install -y avahi-daemon avahi-utils
sudo hostnamectl set-hostname rotary-table

# Copy mDNS service broadcast config
sudo cp configs/avahi/rotary-table.service /etc/avahi/services/
sudo systemctl restart avahi-daemon
```

---

### 2. Install Systemd Background Services

Three simple systemd service files are provided in `configs/systemd/`:

1. [linuxcnc.service](configs/systemd/linuxcnc.service): Starts LinuxCNC core engine.
2. [linuxcnc-gcode-server.service](configs/systemd/linuxcnc-gcode-server.service): Starts C++ NML socket server.
3. [rotary-api-gateway.service](configs/systemd/rotary-api-gateway.service): Starts Python REST API & Web UI.

Edit the `.ini` file paths in `linuxcnc.service` and `linuxcnc-gcode-server.service` to point to your actual machine `.ini` file, then enable them:

```bash
# Copy systemd service units
sudo cp configs/systemd/*.service /etc/systemd/system/

# Reload and start all services on boot
sudo systemctl daemon-reload
sudo systemctl enable --now linuxcnc.service
sudo systemctl enable --now linuxcnc-gcode-server.service
sudo systemctl enable --now rotary-api-gateway.service
```

---

### 3. Zero-IP Access from Any Device

Once enabled, your system automatically boots into service and is accessible network-wide via **`rotary-table.local`**:

- 🌐 **Web Dashboard**: `http://rotary-table.local:8000`
- 🖥️ **Tkinter Desktop GUI**: Connects to `http://rotary-table.local:8000`
- 🐍 **Python IDLE**: `connect("http://rotary-table.local:8000")`
- 🧪 **Test Automation**: `RotaryTableClient("http://rotary-table.local:8000")`

<br>

---

## 🧪 Integration into Larger Hardware Testing Suites

This system is designed specifically for automated hardware-in-the-loop (HIL) testing suites (such as `pytest`, `unittest`, or custom Python test runners). By using the zero-dependency SDK (`python-api-gateway/client.py`), your test harness can programmatically position sensors, antennas, or DUTs (Devices Under Test) mounted on the rotary table.

### 1. Initializing Connection

Import `RotaryTableClient` and pass the gateway endpoint. Thanks to mDNS, you can use the hostname `http://rotary-table.local:8000` without hardcoding IP addresses:

```python
from client import RotaryTableClient

# Initialize connection (default timeout: 5.0s)
table = RotaryTableClient("http://rotary-table.local:8000")

# Optional: verify machine status before running tests
status_info = table.get_status()
print(f"Machine State: {status_info.get('state')}")
```

### 2. Controlling Table & Sweeping Angles in Test Scripts

```python
import time
from client import RotaryTableClient

def run_antenna_pattern_test():
    # 1. Connect & initialize machine state
    table = RotaryTableClient("http://rotary-table.local:8000")
    table.enable()   # Clear ESTOP & enable motor drivers
    table.home()     # Home A-axis to 0° reference point

    # 2. Perform automated angular sweep test (0° to 360° in 45° steps)
    test_angles = [0, 45, 90, 135, 180, 225, 270, 315, 360]
    results = {}

    for angle in test_angles:
        # Move table to exact target angle
        table.move_to(angle, feedrate=1200) # G1 A<angle> F1200
        
        # Verify arrival
        current_pos = table.get_position()
        print(f"Rotary Table positioned at: {current_pos:.2f}°")

        # 3. Trigger your sensor / RF measurement here
        sensor_value = read_rf_power_meter() # Your test instrumentation
        results[angle] = sensor_value

    # 4. Return to 0° home position after test completion
    table.move_preset(0)
    return results

if __name__ == "__main__":
    data = run_antenna_pattern_test()
    print("Test Sweep Complete:", data)
```

### Key SDK Methods for Test Harnesses

| Method | G-Code Equivalent | Description |
| :--- | :--- | :--- |
| `table.get_position()` | `M114` | Returns current A-axis position in degrees as `float`. |
| `table.move_to(angle, feedrate=None)` | `G0 A<val>` / `G1 A<val> F<rate>` | Synchronously moves to absolute angle in degrees. |
| `table.move_relative(delta, feedrate=None)` | `G0 A<current+delta>` | Incremental relative move offset in degrees. |
| `table.jog(direction, step_deg)` | Step move | Step jog CW (`+1`) or CCW (`-1`). |
| `table.home()` | `HOME` | Homes A-axis. |
| `table.enable()` | `ENABLE` | Clears ESTOP and enables machine power. |
| `table.abort()` | `ABORT` | Immediately stops table motion. |





