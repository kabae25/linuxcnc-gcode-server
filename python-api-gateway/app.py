#!/usr/bin/env python3
"""
Zero-dependency HTTP REST API Gateway & Web Server for LinuxCNC Rotary Table Controller.
Uses Python's standard library http.server, requiring no third-party pip packages.
"""

import http.server
import socketserver
import json
import socket
import os
import re
from urllib.parse import urlparse, parse_qs

PORT = int(os.getenv("PORT", "8000"))
GCODE_SERVER_HOST = os.getenv("GCODE_SERVER_HOST", "127.0.0.1")
GCODE_SERVER_PORT = int(os.getenv("GCODE_SERVER_PORT", "5007"))
MOCK_MODE = os.getenv("MOCK_MODE", "false").lower() in ("true", "1", "yes")

# Internal state for mock mode
mock_state = {
    "a_position": 0.0,
    "homed": True,
    "enabled": True,
    "mode": "MDI",
    "state": "ON"
}

import threading

_socket_lock = threading.Lock()
_global_socket = None

def get_connected_socket(timeout: float = 3.0):
    global _global_socket
    if _global_socket is not None:
        return _global_socket

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    s.connect((GCODE_SERVER_HOST, GCODE_SERVER_PORT))
    _global_socket = s
    return _global_socket

def close_global_socket():
    global _global_socket
    if _global_socket is not None:
        try:
            _global_socket.close()
        except Exception:
            pass
        _global_socket = None

def send_gcode_command(cmd: str, timeout: float = 3.0) -> str:
    """Send a command string to linuxcnc-gcode-server via persistent TCP socket."""
    if MOCK_MODE:
        cmd_upper = cmd.strip().upper()
        if cmd_upper in ("M114_JSON", "M114"):
            return json.dumps({
                "ok": True, "x": 0.0, "y": 0.0, "z": 0.0, "a": mock_state["a_position"]
            })
        elif cmd_upper in ("STATUS_JSON", "STATUS"):
            return json.dumps({
                "state": mock_state["state"],
                "mode": mock_state["mode"],
                "homed": [1, 1, 1, 1 if mock_state["homed"] else 0],
                "workspace": {"x": 0.0, "y": 0.0, "z": 0.0, "a": mock_state["a_position"]}
            })
        elif "G0" in cmd_upper or "G1" in cmd_upper:
            match = re.search(r'A\s*(-?\d+(?:\.\d+)?)', cmd_upper)
            if match:
                val = float(match.group(1))
                if "G91" in cmd_upper:
                    mock_state["a_position"] += val
                else:
                    mock_state["a_position"] = val
            return "ok\n"
        elif "HOME" in cmd_upper:
            mock_state["homed"] = True
            return "ok\n"
        elif "ENABLE" in cmd_upper:
            mock_state["enabled"] = True
            mock_state["state"] = "ON"
            return "ok\n"
        elif "ABORT" in cmd_upper:
            return "ok\n"
        return "ok\n"

    with _socket_lock:
        if not cmd.endswith('\n'):
            cmd += '\n'

        for attempt in range(2):
            try:
                sock = get_connected_socket(timeout)
                sock.sendall(cmd.encode('utf-8'))
                
                response_bytes = bytearray()
                while True:
                    chunk = sock.recv(1024)
                    if not chunk:
                        raise socket.error("Connection closed by server")
                    response_bytes.extend(chunk)
                    if b'\n' in response_bytes:
                        break
                return response_bytes.decode('utf-8')
            except Exception:
                close_global_socket()
                if attempt == 1:
                    raise

def get_current_position_data() -> dict:
    try:
        raw_res = send_gcode_command("M114_JSON")
        if raw_res.strip().startswith("{"):
            data = json.loads(raw_res)
            return {
                "ok": True,
                "axis": "A",
                "position_deg": data.get("a", 0.0),
                "homed": data.get("homed", False),
                "state": data.get("state", "UNKNOWN"),
                "raw": data
            }
        else:
            parts = raw_res.split()
            pos = {}
            for p in parts:
                if ":" in p:
                    k, v = p.split(":", 1)
                    try:
                        pos[k.lower()] = float(v)
                    except ValueError:
                        pass
            return {
                "ok": True,
                "axis": "A",
                "position_deg": pos.get("a", 0.0),
                "homed": False,
                "state": "UNKNOWN",
                "raw": pos
            }
    except Exception as e:
        if MOCK_MODE:
            return {"ok": True, "axis": "A", "position_deg": mock_state["a_position"], "homed": mock_state["homed"], "state": mock_state["state"], "mock": True}
        return {
            "ok": False,
            "connected": False,
            "position_deg": 0.0,
            "homed": False,
            "state": "OFFLINE",
            "error": f"LinuxCNC server disconnected on {GCODE_SERVER_HOST}:{GCODE_SERVER_PORT}"
        }

class RESTApiHandler(http.server.SimpleHTTPRequestHandler):
    def _set_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers(204)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        if not path:
            path = "/"

        if path == "/api/v1/position":
            data = get_current_position_data()
            status_code = 200 if data.get("ok", True) else 503
            self._set_headers(status_code)
            self.wfile.write(json.dumps(data).encode('utf-8'))

        elif path == "/api/v1/status":
            try:
                raw_res = send_gcode_command("STATUS_JSON")
                if raw_res.strip().startswith("{"):
                    data = json.loads(raw_res)
                else:
                    data = {"raw": raw_res}
                self._set_headers(200)
                self.wfile.write(json.dumps(data).encode('utf-8'))
            except Exception as e:
                self._set_headers(503)
                self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode('utf-8'))

        else:
            # Serve web UI static files
            web_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web")
            if path == "/" or path == "/index.html":
                filepath = os.path.join(web_dir, "index.html")
            else:
                rel_path = path.lstrip("/")
                filepath = os.path.join(web_dir, rel_path)

            if os.path.exists(filepath) and not os.path.isdir(filepath):
                content_type = "text/html"
                if filepath.endswith(".css"):
                    content_type = "text/css"
                elif filepath.endswith(".js"):
                    content_type = "application/javascript"
                
                self._set_headers(200, content_type)
                with open(filepath, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self._set_headers(404)
                self.wfile.write(json.dumps({"error": "Not Found"}).encode('utf-8'))

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        content_length = int(self.headers.get('Content-Length', 0))
        body_bytes = self.rfile.read(content_length) if content_length > 0 else b'{}'
        
        try:
            payload = json.loads(body_bytes.decode('utf-8')) if body_bytes else {}
        except Exception:
            payload = {}

        try:
            if path == "/api/v1/move":
                pos = float(payload.get("position", 0.0))
                mode = str(payload.get("mode", "absolute")).lower()
                feedrate_val = float(payload["feedrate"]) if payload.get("feedrate") and float(payload["feedrate"]) > 0 else None

                if mode == "relative":
                    gcode = f"G91 G1 A{pos:.4f} F{feedrate_val:.2f} G90" if feedrate_val else f"G91 G0 A{pos:.4f} G90"
                    target = pos
                else:
                    pos = max(-720.0, min(720.0, pos))
                    gcode = f"G90 G1 A{pos:.4f} F{feedrate_val:.2f}" if feedrate_val else f"G90 G0 A{pos:.4f}"
                    target = pos

                res = send_gcode_command(gcode)
                response_data = {"status": "ok", "command": gcode, "target_position_deg": target, "raw_response": res.strip()}

            elif path == "/api/v1/jog":
                direction = int(payload.get("direction", 1))
                step = float(payload.get("step", 1.0))
                feedrate_val = float(payload["feedrate"]) if payload.get("feedrate") and float(payload["feedrate"]) > 0 else None

                dir_factor = -1.0 if direction < 0 else 1.0
                delta = step * dir_factor
                current = get_current_position_data()["position_deg"]
                target = current + delta

                if feedrate_val:
                    gcode = f"G91 G1 A{delta:.4f} F{feedrate_val:.2f} G90"
                else:
                    gcode = f"G91 G0 A{delta:.4f} G90"

                res = send_gcode_command(gcode)
                response_data = {
                    "status": "ok",
                    "command": gcode,
                    "delta_deg": delta,
                    "target_position_deg": target,
                    "raw_response": res.strip()
                }

            elif path == "/api/v1/preset":
                preset_deg = float(payload.get("preset_deg", 0.0))
                preset_deg = max(-720.0, min(720.0, preset_deg))
                feedrate_val = float(payload["feedrate"]) if payload.get("feedrate") and float(payload["feedrate"]) > 0 else None

                if feedrate_val:
                    gcode = f"G90 G1 A{preset_deg:.4f} F{feedrate_val:.2f}"
                else:
                    gcode = f"G90 G0 A{preset_deg:.4f}"

                res = send_gcode_command(gcode)
                response_data = {"status": "ok", "command": gcode, "target_position_deg": preset_deg, "raw_response": res.strip()}

            elif path == "/api/v1/home":
                res = send_gcode_command("HOME")
                response_data = {"status": "ok", "raw_response": res.strip()}

            elif path == "/api/v1/enable":
                res = send_gcode_command("ENABLE")
                response_data = {"status": "ok", "raw_response": res.strip()}

            elif path == "/api/v1/disable":
                res = send_gcode_command("DISABLE")
                response_data = {"status": "ok", "raw_response": res.strip()}

            elif path == "/api/v1/abort":
                res = send_gcode_command("ABORT")
                response_data = {"status": "ok", "raw_response": res.strip()}

            elif path == "/api/v1/gcode":
                gcode = payload.get("gcode", "")
                res = send_gcode_command(gcode)
                response_data = {"status": "ok", "command": gcode, "raw_response": res.strip()}

            else:
                self._set_headers(404)
                self.wfile.write(json.dumps({"error": "Endpoint Not Found"}).encode('utf-8'))
                return

            self._set_headers(200)
            self.wfile.write(json.dumps(response_data).encode('utf-8'))

        except Exception as e:
            self._set_headers(500)
            self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

def run_server():
    server_address = ('', PORT)
    httpd = socketserver.TCPServer(server_address, RESTApiHandler)
    print(f"Rotary Table REST API Server running on port {PORT}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()

if __name__ == "__main__":
    run_server()
