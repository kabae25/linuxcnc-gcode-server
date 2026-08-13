#!/usr/bin/env python3
"""
Tkinter GUI Application for LinuxCNC Rotary Table Controller.
Provides real-time angle readout, preset buttons, step jogging, and absolute position move commands.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
import urllib.request
import urllib.error
import json

DEFAULT_API_URL = "http://localhost:8000"

class RotaryTableApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("LinuxCNC Rotary Table Controller (A-Axis)")
        self.geometry("520x640")
        self.resizable(False, False)

        # Style configuration
        self.configure(bg="#0f172a")
        self.style = ttk.Style(self)
        self.style.theme_use("clam")

        self.api_url = DEFAULT_API_URL
        self.running = True
        self.current_step = 1.0

        self._create_widgets()
        
        # Start background polling thread
        self.poll_thread = threading.Thread(target=self._poll_position_loop, daemon=True)
        self.poll_thread.start()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_widgets(self):
        # Header / Status Frame
        header_frame = tk.Frame(self, bg="#1e293b", padx=15, pady=10)
        header_frame.pack(fill="x", padx=15, pady=(15, 10))

        title_lbl = tk.Label(
            header_frame, text="Rotary Table Controller",
            font=("Inter", 16, "bold"), fg="#38bdf8", bg="#1e293b"
        )
        title_lbl.pack(side="left")

        self.status_lbl = tk.Label(
            header_frame, text="• Connecting",
            font=("Inter", 10, "bold"), fg="#fb7185", bg="#1e293b"
        )
        self.status_lbl.pack(side="right")

        # Position Readout Card
        readout_card = tk.Frame(self, bg="#1e293b", padx=20, pady=20, highlightthickness=1, highlightbackground="#334155")
        readout_card.pack(fill="x", padx=15, pady=5)

        card_title = tk.Label(
            readout_card, text="CURRENT POSITION",
            font=("Inter", 10, "bold"), fg="#94a3b8", bg="#1e293b"
        )
        card_title.pack(anchor="w")

        self.pos_var = tk.StringVar(value="0.00°")
        pos_display = tk.Label(
            readout_card, textvariable=self.pos_var,
            font=("JetBrains Mono", 36, "bold"), fg="#f8fafc", bg="#1e293b"
        )
        pos_display.pack(pady=10)

        # Quick Presets Frame
        presets_card = tk.LabelFrame(
            self, text=" Quick Presets ", font=("Inter", 10, "bold"),
            fg="#94a3b8", bg="#1e293b", padx=15, pady=15, highlightthickness=1, highlightbackground="#334155"
        )
        presets_card.pack(fill="x", padx=15, pady=10)

        presets = [-720, -360, -180, -90, 0, 90, 180, 360, 720]
        grid_frame = tk.Frame(presets_card, bg="#1e293b")
        grid_frame.pack(fill="x")

        for idx, angle in enumerate(presets):
            row = idx // 3
            col = idx % 3
            btn = tk.Button(
                grid_frame, text=f"{angle}°", font=("Inter", 11, "bold"),
                fg="#f8fafc", bg="#334155", activebackground="#38bdf8", activeforeground="#0f172a",
                relief="flat", bd=0, padx=10, pady=8,
                command=lambda a=angle: self._send_preset(a)
            )
            btn.grid(row=row, column=col, sticky="ew", padx=4, pady=4)
            grid_frame.grid_columnconfigure(col, weight=1)

        # Jog Control Frame
        jog_card = tk.LabelFrame(
            self, text=" Step Jog Controls ", font=("Inter", 10, "bold"),
            fg="#94a3b8", bg="#1e293b", padx=15, pady=15, highlightthickness=1, highlightbackground="#334155"
        )
        jog_card.pack(fill="x", padx=15, pady=10)

        # Step Radio selector
        step_frame = tk.Frame(jog_card, bg="#1e293b")
        step_frame.pack(fill="x", pady=(0, 10))

        step_lbl = tk.Label(step_frame, text="Step:", font=("Inter", 10), fg="#94a3b8", bg="#1e293b")
        step_lbl.pack(side="left", padx=(0, 10))

        self.step_var = tk.DoubleVar(value=1.0)
        steps = [0.1, 1.0, 10.0, 45.0]
        for s in steps:
            rb = tk.Radiobutton(
                step_frame, text=f"{s}°", value=s, variable=self.step_var,
                font=("Inter", 10, "bold"), fg="#f8fafc", bg="#1e293b",
                activebackground="#1e293b", activeforeground="#38bdf8",
                selectcolor="#0f172a", command=self._on_step_change
            )
            rb.pack(side="left", padx=5)

        jog_btns_frame = tk.Frame(jog_card, bg="#1e293b")
        jog_btns_frame.pack(fill="x")

        ccw_btn = tk.Button(
            jog_btns_frame, text="⟲ JOG - (CCW)", font=("Inter", 12, "bold"),
            fg="#f8fafc", bg="#334155", activebackground="#fb7185", activeforeground="#ffffff",
            relief="flat", pady=10, command=lambda: self._send_jog(-1)
        )
        ccw_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))

        cw_btn = tk.Button(
            jog_btns_frame, text="⟳ JOG + (CW)", font=("Inter", 12, "bold"),
            fg="#f8fafc", bg="#38bdf8", activebackground="#0284c7", activeforeground="#0f172a",
            relief="flat", pady=10, command=lambda: self._send_jog(1)
        )
        cw_btn.pack(side="right", fill="x", expand=True, padx=(5, 0))

        # Absolute Target Entry Frame
        target_card = tk.Frame(self, bg="#1e293b", padx=15, pady=12, highlightthickness=1, highlightbackground="#334155")
        target_card.pack(fill="x", padx=15, pady=5)

        tk.Label(target_card, text="Target Move (G0 A):", font=("Inter", 10, "bold"), fg="#94a3b8", bg="#1e293b").pack(side="left", padx=(0, 10))

        self.target_entry = tk.Entry(target_card, font=("JetBrains Mono", 12), bg="#0f172a", fg="#f8fafc", insertbackground="#f8fafc", width=10)
        self.target_entry.pack(side="left", padx=(0, 10))

        go_btn = tk.Button(
            target_card, text="GO", font=("Inter", 10, "bold"),
            fg="#0f172a", bg="#34d399", activebackground="#059669",
            relief="flat", padx=15, pady=4, command=self._send_target_move
        )
        go_btn.pack(side="left")

        # Machine Action Buttons Frame
        action_frame = tk.Frame(self, bg="#0f172a")
        action_frame.pack(fill="x", padx=15, pady=15)

        enable_btn = tk.Button(
            action_frame, text="ENABLE", font=("Inter", 10, "bold"),
            fg="#34d399", bg="#1e293b", relief="flat", pady=8,
            command=lambda: self._send_action("/api/v1/enable")
        )
        enable_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))

        home_btn = tk.Button(
            action_frame, text="HOME A", font=("Inter", 10, "bold"),
            fg="#f8fafc", bg="#1e293b", relief="flat", pady=8,
            command=lambda: self._send_action("/api/v1/home")
        )
        home_btn.pack(side="left", fill="x", expand=True, padx=2)

        abort_btn = tk.Button(
            action_frame, text="ABORT", font=("Inter", 10, "bold"),
            fg="#fb7185", bg="#1e293b", relief="flat", pady=8,
            command=lambda: self._send_action("/api/v1/abort")
        )
        abort_btn.pack(side="right", fill="x", expand=True, padx=(4, 0))

    def _on_step_change(self):
        self.current_step = self.step_var.get()

    def _send_action(self, endpoint: str, payload: dict = None):
        def _req():
            try:
                url = f"{self.api_url}{endpoint}"
                data = json.dumps(payload or {}).encode('utf-8')
                req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    pass
            except Exception as e:
                print("API action error:", e)
        threading.Thread(target=_req, daemon=True).start()

    def _send_preset(self, angle: float):
        self._send_action("/api/v1/preset", {"preset_deg": angle})

    def _send_jog(self, direction: int):
        self._send_action("/api/v1/jog", {"direction": direction, "step": self.current_step})

    def _send_target_move(self):
        try:
            val = float(self.target_entry.get())
            self._send_action("/api/v1/move", {"position": val, "mode": "absolute"})
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid numeric angle.")

    def _poll_position_loop(self):
        while self.running:
            try:
                url = f"{self.api_url}/api/v1/position"
                req = urllib.request.Request(url, headers={"Accept": "application/json"})
                with urllib.request.urlopen(req, timeout=1.5) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode('utf-8'))
                        pos = data.get("position_deg", 0.0)
                        self.pos_var.set(f"{pos:.2f}°")
                        self.status_lbl.config(text="• Online", fg="#34d399")
                    else:
                        self.status_lbl.config(text="• API Error", fg="#fb7185")
            except Exception:
                self.status_lbl.config(text="• Offline", fg="#fb7185")
            time.sleep(0.2)

    def _on_close(self):
        self.running = False
        self.destroy()

if __name__ == "__main__":
    app = RotaryTableApp()
    app.mainloop()
