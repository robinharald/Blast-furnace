"""
Tkinter GUI for the Blast Furnace bot.

Replaces the command-line interface with a standalone window.
Handles settings, calibration, start/stop, and live log output.
"""

import sys
import io
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

from config import ScreenRegions, BotSettings, load_calibration, save_calibration
from data.bars import BarType
from ui.setup_wizard import run_calibration
from bot.state_machine import BlastFurnaceStateMachine


class LogRedirector(io.TextIOBase):
    """Redirect print() output to a tkinter text widget."""

    def __init__(self, text_widget, original_stdout):
        self.text_widget = text_widget
        self.original = original_stdout

    def write(self, msg):
        if msg:
            self.text_widget.after(0, self._append, msg)
            self.original.write(msg)
        return len(msg) if msg else 0

    def _append(self, msg):
        self.text_widget.configure(state="normal")
        self.text_widget.insert(tk.END, msg)
        self.text_widget.see(tk.END)
        self.text_widget.configure(state="disabled")

    def flush(self):
        self.original.flush()


class BlastFurnaceGUI:
    """Main application window."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Blast Furnace Bot")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e1e")

        self.regions = ScreenRegions()
        self.calibrated = load_calibration(self.regions)
        self.bot_thread = None
        self.machine = None

        self._build_ui()
        self._redirect_stdout()

    # ── UI construction ──

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")

        # Dark theme colors
        bg = "#1e1e1e"
        fg = "#d4d4d4"
        accent = "#4ec9b0"
        field_bg = "#2d2d2d"
        btn_bg = "#3c3c3c"

        style.configure("TFrame", background=bg)
        style.configure("TLabel", background=bg, foreground=fg, font=("Segoe UI", 10))
        style.configure("Header.TLabel", background=bg, foreground=accent,
                        font=("Segoe UI", 14, "bold"))
        style.configure("TCheckbutton", background=bg, foreground=fg,
                        font=("Segoe UI", 10))
        style.configure("TButton", background=btn_bg, foreground=fg,
                        font=("Segoe UI", 10, "bold"), padding=6)
        style.configure("Start.TButton", background="#2d7d46", foreground="#ffffff",
                        font=("Segoe UI", 11, "bold"), padding=8)
        style.configure("Stop.TButton", background="#a63d40", foreground="#ffffff",
                        font=("Segoe UI", 11, "bold"), padding=8)
        style.configure("TCombobox", fieldbackground=field_bg, background=btn_bg,
                        foreground=fg, font=("Segoe UI", 10))
        style.configure("TSpinbox", fieldbackground=field_bg, foreground=fg)
        style.configure("TLabelframe", background=bg, foreground=accent,
                        font=("Segoe UI", 10, "bold"))
        style.configure("TLabelframe.Label", background=bg, foreground=accent)
        style.map("TCheckbutton", background=[("active", bg)])
        style.map("TButton", background=[("active", "#505050")])

        main = ttk.Frame(self.root, padding=12)
        main.pack(fill="both", expand=True)

        # ── Title ──
        ttk.Label(main, text="Blast Furnace Bot", style="Header.TLabel").pack(pady=(0, 8))

        # ── Settings frame ──
        settings = ttk.LabelFrame(main, text="Settings", padding=8)
        settings.pack(fill="x", pady=(0, 8))

        # Bar type
        row0 = ttk.Frame(settings)
        row0.pack(fill="x", pady=2)
        ttk.Label(row0, text="Bar type:").pack(side="left")
        self.bar_var = tk.StringVar()
        bar_names = [bt.data.name for bt in BarType]
        self.bar_combo = ttk.Combobox(row0, textvariable=self.bar_var,
                                      values=bar_names, state="readonly", width=18)
        self.bar_combo.set(bar_names[4])  # Default: Gold
        self.bar_combo.pack(side="right")
        self.bar_combo.bind("<<ComboboxSelected>>", self._on_bar_change)

        # Toggles
        self.coal_bag_var = tk.BooleanVar(value=True)
        self.stamina_var = tk.BooleanVar(value=True)
        self.goldsmith_var = tk.BooleanVar(value=True)
        self.ice_gloves_var = tk.BooleanVar(value=True)

        toggles = ttk.Frame(settings)
        toggles.pack(fill="x", pady=4)

        left_col = ttk.Frame(toggles)
        left_col.pack(side="left", fill="x", expand=True)
        right_col = ttk.Frame(toggles)
        right_col.pack(side="right", fill="x", expand=True)

        self.cb_coal = ttk.Checkbutton(left_col, text="Coal bag",
                                       variable=self.coal_bag_var)
        self.cb_coal.pack(anchor="w")
        self.cb_stam = ttk.Checkbutton(left_col, text="Stamina potions",
                                       variable=self.stamina_var)
        self.cb_stam.pack(anchor="w")
        self.cb_gold = ttk.Checkbutton(right_col, text="Goldsmith gauntlets",
                                       variable=self.goldsmith_var)
        self.cb_gold.pack(anchor="w")
        self.cb_ice = ttk.Checkbutton(right_col, text="Ice gloves",
                                      variable=self.ice_gloves_var)
        self.cb_ice.pack(anchor="w")

        # Coal bag slot
        slot_row = ttk.Frame(settings)
        slot_row.pack(fill="x", pady=2)
        ttk.Label(slot_row, text="Coal bag slot (0-27):").pack(side="left")
        self.slot_var = tk.IntVar(value=0)
        self.slot_spin = ttk.Spinbox(slot_row, from_=0, to=27,
                                     textvariable=self.slot_var, width=5)
        self.slot_spin.pack(side="right")

        # Stop key
        key_row = ttk.Frame(settings)
        key_row.pack(fill="x", pady=2)
        ttk.Label(key_row, text="Stop key:").pack(side="left")
        self.stop_key_var = tk.StringVar(value="F6")
        ttk.Entry(key_row, textvariable=self.stop_key_var, width=6,
                  font=("Segoe UI", 10)).pack(side="right")

        self._on_bar_change()  # Set initial toggle states

        # ── Buttons ──
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill="x", pady=(0, 8))

        self.calibrate_btn = ttk.Button(btn_frame, text="Calibrate",
                                        command=self._on_calibrate)
        self.calibrate_btn.pack(side="left", padx=(0, 4))

        cal_label = "Ready" if self.calibrated else "Not calibrated"
        self.cal_status = ttk.Label(btn_frame, text=cal_label,
                                    foreground=accent if self.calibrated else "#e06c75")
        self.cal_status.pack(side="left", padx=4)

        self.stop_btn = ttk.Button(btn_frame, text="Stop", style="Stop.TButton",
                                   command=self._on_stop, state="disabled")
        self.stop_btn.pack(side="right", padx=(4, 0))

        self.start_btn = ttk.Button(btn_frame, text="Start", style="Start.TButton",
                                    command=self._on_start)
        self.start_btn.pack(side="right")

        # ── Log output ──
        log_frame = ttk.LabelFrame(main, text="Log", padding=4)
        log_frame.pack(fill="both", expand=True)

        self.log_text = scrolledtext.ScrolledText(
            log_frame, height=14, width=55, wrap="word",
            bg="#1a1a1a", fg="#cccccc", font=("Consolas", 9),
            insertbackground="#cccccc", state="disabled",
            relief="flat", borderwidth=0
        )
        self.log_text.pack(fill="both", expand=True)

    def _redirect_stdout(self):
        self._original_stdout = sys.stdout
        sys.stdout = LogRedirector(self.log_text, self._original_stdout)

    # ── Event handlers ──

    def _on_bar_change(self, event=None):
        """Update toggle visibility based on selected bar type."""
        bar = self._get_selected_bar()
        if bar is None:
            return

        # Coal bag: only for coal-requiring bars
        if bar.data.requires_coal:
            self.cb_coal.configure(state="normal")
            self.slot_spin.configure(state="normal")
        else:
            self.coal_bag_var.set(False)
            self.cb_coal.configure(state="disabled")
            self.slot_spin.configure(state="disabled")

        # Goldsmith: only for gold
        if bar == BarType.GOLD:
            self.cb_gold.configure(state="normal")
        else:
            self.goldsmith_var.set(False)
            self.cb_gold.configure(state="disabled")

    def _get_selected_bar(self):
        """Map combo selection to BarType enum."""
        name = self.bar_var.get()
        for bt in BarType:
            if bt.data.name == name:
                return bt
        return None

    def _build_settings(self):
        """Build a BotSettings from current GUI state."""
        settings = BotSettings()
        settings.bar_type = self._get_selected_bar()
        settings.use_coal_bag = self.coal_bag_var.get()
        settings.coal_bag_slot = self.slot_var.get()
        settings.use_stamina = self.stamina_var.get()
        settings.use_goldsmith_gauntlets = self.goldsmith_var.get()
        settings.use_ice_gloves = self.ice_gloves_var.get()
        settings.stop_key = self.stop_key_var.get().strip().lower()
        return settings

    def _on_calibrate(self):
        """Run calibration wizard (minimizes GUI, runs in console)."""
        self.root.iconify()
        try:
            self.regions = ScreenRegions()
            run_calibration(self.regions)
            self.calibrated = True
            self.cal_status.configure(text="Ready", foreground="#4ec9b0")
            print("Calibration saved.\n")
        except Exception as e:
            print(f"Calibration failed: {e}\n")
            self.calibrated = False
            self.cal_status.configure(text="Failed", foreground="#e06c75")
        finally:
            self.root.deiconify()

    def _on_start(self):
        """Start the bot in a background thread."""
        if not self.calibrated:
            messagebox.showwarning("Not Calibrated",
                                   "Run calibration first (click Calibrate).")
            return

        bar = self._get_selected_bar()
        if bar is None:
            messagebox.showwarning("No Bar", "Select a bar type first.")
            return

        settings = self._build_settings()

        # Disable controls
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.calibrate_btn.configure(state="disabled")
        self.bar_combo.configure(state="disabled")

        self.machine = BlastFurnaceStateMachine(self.regions, settings)

        def run_bot():
            try:
                self.machine.run()
            except Exception as e:
                print(f"\n  [FATAL] {e}")
            finally:
                self.root.after(0, self._on_bot_stopped)

        self.bot_thread = threading.Thread(target=run_bot, daemon=True)
        self.bot_thread.start()

        print(f"Bot started — {bar.data.name} | Stop key: {settings.stop_key.upper()}\n")

    def _on_stop(self):
        """Signal the bot to stop."""
        if self.machine:
            self.machine.stop()
            print("Stop signal sent. Finishing current action...\n")

    def _on_bot_stopped(self):
        """Re-enable controls after bot stops."""
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.calibrate_btn.configure(state="normal")
        self.bar_combo.configure(state="readonly")
        self.machine = None

    # ── Run ──

    def run(self):
        """Start the tkinter main loop."""
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def _on_close(self):
        """Clean shutdown."""
        if self.machine:
            self.machine.stop()
        sys.stdout = self._original_stdout
        self.root.destroy()
