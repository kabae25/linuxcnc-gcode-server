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

def send_gcode_command(cmd: str, timeout: float = 3.0) -> str:
    """Send a command string to linuxcnc-gcode-server via TCP socket."""
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
                mock_state["a_position"] = float(match.group(1))
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

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    sock.connect((GCODE_SERVER_HOST, GCODE_SERVER_PORT))
    if not cmd.endswith('\n'):
        cmd += '\n'
    sock.sendall(cmd.encode('utf-8'))
    response = sock.recv(4096).decode('utf-8')
    sock.close()
    return response

def get_current_position_data() -> dict:
    try:
        raw_res = send_gcode_command("M114_JSON")
        if raw_res.strip().startswith("{"):
            data = json.loads(raw_res)
            return {
                "ok": True,
                "axis": "A",
                "position_deg": data.get("a", 0.0),
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
                "raw": pos
            }
    except Exception as e:
        if MOCK_MODE:
            return {"ok": True, "axis": "A", "position_deg": mock_state["a_position"], "mock": True}
        raise

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
        path = parsed.path

        if path == "/api/v1/position":
            try:
                data = get_current_position_data()
                self._set_headers(200)
                self.wfile.write(json.dumps(data).encode('utf-8'))
            except Exception as e:
                self._set_headers(503)
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

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
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))

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
        path = parsed.path
        content_length = int(self.headers.get('Content-Length', 0))
        body_bytes = self.rfile.read(content_length) if content_length > 0 else b'{}'
        
        try:
            payload = json.loads(body_bytes.decode('utf-8')) if body_bytes else {}
        except Exception:
            payload = {}

        try:
            if path == "/api/v1/move":
                pos = payload.get("position", 0.0)
                mode = payload.get("mode", "absolute")
                feedrate = payload.get("feedrate")

                if mode.lower() == "relative":
                    current = get_current_position_data()["position_deg"]
                    target = current + pos
                else:
                    target = pos

                gcode = f"G1 A{target:.4f} F{feedrate:.2f}" if feedrate else f"G0 A{target:.4f}"
                res = send_gcode_command(gcode)
                response_data = {"status": "ok", "command": gcode, "target_position_deg": target, "raw_response": res.strip()}

            elif path == "/api/v1/jog":
                direction = payload.get("direction", 1)
                step = payload.get("step", 1.0)
                feedrate = payload.get("feedrate")

                dir_factor = 1.0 if direction >= 0 else -1.0
                current = get_current_position_data()["position_deg"]
                target = current + (step * dir_factor)

                gcode = f"G1 A{target:.4f} F{feedrate:.2f}" if feedrate else f"G0 A{target:.4f}"
                res = send_gcode_command(gcode)
                response_data = {"status": "ok", "command": gcode, "target_position_deg": target, "raw_response": res.strip()}

            elif path == "/api/v1/preset":
                preset_deg = payload.get("preset_deg", 0.0)
                gcode = f"G0 A{preset_deg:.4f}"
                res = send_gcode_command(gcode)
                response_data = {"status": "ok", "command": gcode, "target_position_deg": preset_deg, "raw_response": res.strip()}

            elif path == "/api/v1/home":
                res = send_gcode_command("HOME")
                response_data = {"status": "ok", "raw_response": res.strip()}

            elif path == "/api/v1/enable":
                res = send_gcode_command("ENABLE")
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
