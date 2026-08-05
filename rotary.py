"""
rotary.py - Interactive Python IDLE Interface for LinuxCNC Rotary Table Controller

Designed for seamless interactive use in Python IDLE or REPL shell.
Routes all commands through the REST API Gateway (http://localhost:8000)
to guarantee behavior identical to the Web GUI and Tkinter GUI.

Usage in IDLE:
    >>> from rotary import *
    >>> pos()            # View position in degrees
    >>> move(360)        # Move to 360° (G0 A360)
    >>> jog_cw(10)       # Jog +10° clockwise
    >>> preset(90)       # Go to 90° preset
    >>> home()           # Home table
    >>> status()         # View machine status
"""

import sys
import os
from typing import Optional, Dict, Any

# Ensure python-api-gateway directory is in sys.path
_gateway_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "python-api-gateway")
if _gateway_path not in sys.path:
    sys.path.insert(0, _gateway_path)

from client import RotaryTableClient

class TableController:
    """Interactive Rotary Table Controller wrapper for Python IDLE."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.client = RotaryTableClient(base_url=base_url)
        self.base_url = base_url

    def connect(self, base_url: str):
        """Connect to a different API Gateway URL."""
        self.base_url = base_url
        self.client = RotaryTableClient(base_url=base_url)
        print(f"Connected to Rotary Table Gateway at {base_url}")

    def pos(self) -> float:
        """Get and display current rotary table position in degrees."""
        try:
            position = self.client.get_position()
            print(f"📍 Rotary Position: {position:.2f}°")
            return position
        except Exception as e:
            print(f"❌ Error getting position: {e}")
            return 0.0

    def move(self, angle_deg: float, feedrate: Optional[float] = None) -> Dict[str, Any]:
        """
        Move table to an absolute target angle in degrees (e.g. move(360) -> G0 A360).
        """
        try:
            print(f"🔄 Moving to {angle_deg:.2f}°...")
            res = self.client.move_to(position_deg=angle_deg, feedrate=feedrate)
            print(f"  → Command: {res.get('command')}")
            print(f"  → Status:  {res.get('status')}")
            return res
        except Exception as e:
            print(f"❌ Move failed: {e}")
            return {"status": "error", "message": str(e)}

    def move_rel(self, delta_deg: float, feedrate: Optional[float] = None) -> Dict[str, Any]:
        """Move table by a relative angle offset in degrees."""
        try:
            print(f"🔄 Relative move by {delta_deg:+.2f}°...")
            res = self.client.move_relative(delta_deg=delta_deg, feedrate=feedrate)
            print(f"  → Command: {res.get('command')}")
            return res
        except Exception as e:
            print(f"❌ Relative move failed: {e}")
            return {"status": "error", "message": str(e)}

    def preset(self, angle_deg: float) -> Dict[str, Any]:
        """Move table to a preset angle (e.g., 0, 45, 90, 180, 270, 360)."""
        try:
            print(f"🎯 Moving to Preset {angle_deg}°...")
            res = self.client.move_preset(preset_deg=angle_deg)
            print(f"  → Command: {res.get('command')}")
            return res
        except Exception as e:
            print(f"❌ Preset move failed: {e}")
            return {"status": "error", "message": str(e)}

    def jog_cw(self, step_deg: float = 1.0, feedrate: Optional[float] = None) -> Dict[str, Any]:
        """Jog table clockwise (+) by step_deg degrees."""
        try:
            print(f"⟳ Jog CW (+{step_deg}°)...")
            res = self.client.jog(direction=1, step_deg=step_deg, feedrate=feedrate)
            print(f"  → Target: {res.get('target_position_deg'):.2f}°")
            return res
        except Exception as e:
            print(f"❌ Jog CW failed: {e}")
            return {"status": "error", "message": str(e)}

    def jog_ccw(self, step_deg: float = 1.0, feedrate: Optional[float] = None) -> Dict[str, Any]:
        """Jog table counter-clockwise (-) by step_deg degrees."""
        try:
            print(f"⟲ Jog CCW (-{step_deg}°)...")
            res = self.client.jog(direction=-1, step_deg=step_deg, feedrate=feedrate)
            print(f"  → Target: {res.get('target_position_deg'):.2f}°")
            return res
        except Exception as e:
            print(f"❌ Jog CCW failed: {e}")
            return {"status": "error", "message": str(e)}

    def home(self) -> Dict[str, Any]:
        """Home the rotary table axis."""
        try:
            print("🏠 Homing rotary table...")
            res = self.client.home()
            print(f"  → Status: {res.get('status')}")
            return res
        except Exception as e:
            print(f"❌ Homing failed: {e}")
            return {"status": "error", "message": str(e)}

    def enable(self) -> Dict[str, Any]:
        """Clear ESTOP and enable machine."""
        try:
            print("⚡ Enabling machine...")
            res = self.client.enable()
            print(f"  → Status: {res.get('status')}")
            return res
        except Exception as e:
            print(f"❌ Enable failed: {e}")
            return {"status": "error", "message": str(e)}

    def abort(self) -> Dict[str, Any]:
        """Abort motion immediately."""
        try:
            print("🛑 Aborting motion...")
            res = self.client.abort()
            print(f"  → Status: {res.get('status')}")
            return res
        except Exception as e:
            print(f"❌ Abort failed: {e}")
            return {"status": "error", "message": str(e)}

    def status(self) -> Dict[str, Any]:
        """Query and display machine status."""
        try:
            res = self.client.get_status()
            print("📊 Machine Status Breakdown:")
            for k, v in res.items():
                print(f"   {k}: {v}")
            return res
        except Exception as e:
            print(f"❌ Status query failed: {e}")
            return {"status": "error", "message": str(e)}

    def gcode(self, cmd_string: str) -> Dict[str, Any]:
        """Send a raw G-code string (e.g. gcode('G0 A180'))."""
        try:
            print(f"⚙️ G-Code: '{cmd_string}'")
            res = self.client.send_gcode(cmd_string)
            print(f"  → Response: {res.get('raw_response')}")
            return res
        except Exception as e:
            print(f"❌ Gcode execution failed: {e}")
            return {"status": "error", "message": str(e)}


# Instantiate default global controller instance for interactive IDLE use
default_table = TableController()

# Top-level helper functions for direct `from rotary import *` usage in IDLE
def pos() -> float:
    """Get current rotary table position in degrees."""
    return default_table.pos()

def move(angle_deg: float, feedrate: Optional[float] = None) -> Dict[str, Any]:
    """Move to absolute target angle in degrees (e.g. move(360))."""
    return default_table.move(angle_deg, feedrate)

def move_rel(delta_deg: float, feedrate: Optional[float] = None) -> Dict[str, Any]:
    """Move relative offset angle in degrees (e.g. move_rel(45))."""
    return default_table.move_rel(delta_deg, feedrate)

def preset(angle_deg: float) -> Dict[str, Any]:
    """Move to preset angle (e.g. preset(90))."""
    return default_table.preset(angle_deg)

def jog_cw(step_deg: float = 1.0, feedrate: Optional[float] = None) -> Dict[str, Any]:
    """Jog table clockwise by step_deg degrees."""
    return default_table.jog_cw(step_deg, feedrate)

def jog_ccw(step_deg: float = 1.0, feedrate: Optional[float] = None) -> Dict[str, Any]:
    """Jog table counter-clockwise by step_deg degrees."""
    return default_table.jog_ccw(step_deg, feedrate)

def home() -> Dict[str, Any]:
    """Home the rotary table."""
    return default_table.home()

def enable() -> Dict[str, Any]:
    """Enable machine / clear ESTOP."""
    return default_table.enable()

def abort() -> Dict[str, Any]:
    """Abort motion immediately."""
    return default_table.abort()

def status() -> Dict[str, Any]:
    """Query machine status."""
    return default_table.status()

def gcode(cmd_string: str) -> Dict[str, Any]:
    """Send raw G-code string."""
    return default_table.gcode(cmd_string)

def connect(base_url: str):
    """Set custom API Gateway URL."""
    default_table.connect(base_url)

print("=" * 65)
print("  LinuxCNC Rotary Table Interactive IDLE Module Loaded")
print("  API Gateway: http://localhost:8000")
print("  Commands: pos(), move(360), jog_cw(10), jog_ccw(10), preset(90),")
print("            home(), enable(), abort(), status(), gcode('G0 A180')")
print("=" * 65)
