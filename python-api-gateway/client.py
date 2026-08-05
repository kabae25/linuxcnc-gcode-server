import urllib.request
import urllib.error
import json
from typing import Optional, Dict, Any

class RotaryTableClient:
    """
    Zero-dependency Python Client SDK for external testing systems to interface with the
    LinuxCNC Rotary Table Controller REST API.
    
    Example usage:
        client = RotaryTableClient("http://localhost:8000")
        client.home()
        client.move_to(360.0) # equivalent to G0 A360
        pos = client.get_position()
        print("Current position:", pos)
    """

    def __init__(self, base_url: str = "http://localhost:8000", timeout: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _http_get(self, endpoint: str) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = resp.read().decode('utf-8')
                return json.loads(data)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"HTTP Error {e.code}: {e.read().decode('utf-8')}") from e
        except Exception as e:
            raise RuntimeError(f"Connection error to {url}: {str(e)}") from e

    def _http_post(self, endpoint: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        json_bytes = json.dumps(payload or {}).encode('utf-8')
        req = urllib.request.Request(
            url,
            data=json_bytes,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = resp.read().decode('utf-8')
                return json.loads(data)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"HTTP Error {e.code}: {e.read().decode('utf-8')}") from e
        except Exception as e:
            raise RuntimeError(f"Connection error to {url}: {str(e)}") from e

    def get_position(self) -> float:
        """Get current rotary table position in degrees."""
        data = self._http_get("/api/v1/position")
        return float(data.get("position_deg", 0.0))

    def get_status(self) -> Dict[str, Any]:
        """Get machine status breakdown."""
        return self._http_get("/api/v1/status")

    def move_to(self, position_deg: float, feedrate: Optional[float] = None) -> Dict[str, Any]:
        """
        Move rotary table to an absolute angle in degrees (e.g. 360.0 for G0 A360).
        """
        payload = {
            "position": position_deg,
            "mode": "absolute"
        }
        if feedrate is not None:
            payload["feedrate"] = feedrate
            
        return self._http_post("/api/v1/move", payload)

    def move_relative(self, delta_deg: float, feedrate: Optional[float] = None) -> Dict[str, Any]:
        """Move rotary table by a relative angle offset in degrees."""
        payload = {
            "position": delta_deg,
            "mode": "relative"
        }
        if feedrate is not None:
            payload["feedrate"] = feedrate
            
        return self._http_post("/api/v1/move", payload)

    def jog(self, direction: int, step_deg: float = 1.0, feedrate: Optional[float] = None) -> Dict[str, Any]:
        """
        Jog rotary table incrementally.
        direction: +1 for positive (CW), -1 for negative (CCW)
        step_deg: angle increment in degrees
        """
        payload = {
            "direction": 1 if direction >= 0 else -1,
            "step": step_deg
        }
        if feedrate is not None:
            payload["feedrate"] = feedrate

        return self._http_post("/api/v1/jog", payload)

    def move_preset(self, preset_deg: float) -> Dict[str, Any]:
        """Move rotary table to a preset angle."""
        return self._http_post("/api/v1/preset", {"preset_deg": preset_deg})

    def home(self) -> Dict[str, Any]:
        """Home the rotary table axis."""
        return self._http_post("/api/v1/home")

    def enable(self) -> Dict[str, Any]:
        """Enable machine / clear ESTOP."""
        return self._http_post("/api/v1/enable")

    def abort(self) -> Dict[str, Any]:
        """Abort motion immediately."""
        return self._http_post("/api/v1/abort")

    def send_gcode(self, gcode: str) -> Dict[str, Any]:
        """Send raw G-code string."""
        return self._http_post("/api/v1/gcode", {"gcode": gcode})
