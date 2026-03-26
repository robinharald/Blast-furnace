"""
Main GUI application — Tkinter interface for the Mahogany Homes bot.

4-panel layout: Settings, Status, Log, Controls.
All settings persist to settings.json.
"""
import threading
import time
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import logging
from typing import Optional

from config.settings import (
    BotSettings, ScreenRegions, load_settings, save_settings, load_calibration,
)
from ui.setup_wizard import CalibrationWizard

logger = logging.getLogger(__name__)

APP_TITLE = "Mahogany Homes Bot v1.0"
WINDOW_WIDTH = 520
WINDOW_HEIGHT = 780


class MahoganyHomesGUI:
    """Main application window."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title(APP_TITLE)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.resizable(False, False)
        self.root.configure(bg="#1a1a2e")

        self.settings = load_settings()
        self.regions: Optional[ScreenRegions] = load_calibration()
        self.bot = None
        self.bot_thread = None

        self._build_ui()
        self._load_settings_to_ui()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#1a1a2e")
        style.configure("TLabel", background="#1a1a2e", foreground="#e0e0e0", font=("Segoe UI", 10))
        style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"), foreground="#00d4ff")
        style.configure("TButton", font=("Segoe UI", 10, "bold"))
        style.configure("TCheckbutton", background="#1a1a2e", foreground="#e0e0e0")

        main = ttk.Frame(self.root, padding=10)
        main.pack(fill="both", expand=True)

        # Header
        ttk.Label(main, text=APP_TITLE, style="Header.TLabel").pack(pady=(0, 10))

        # Settings Panel
        self._build_settings_panel(main)

        # Status Panel
        self._build_status_panel(main)

        # Log Panel
        self._build_log_panel(main)

        # Control Buttons
        self._build_controls(main)

    def _build_settings_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text=" Settings ", padding=8)
        frame.pack(fill="x", pady=(0, 8))

        # Row 1: Tier + Mode
        row1 = ttk.Frame(frame)
        row1.pack(fill="x", pady=2)

        ttk.Label(row1, text="Tier:").pack(side="left")
        self.tier_var = tk.StringVar(value=self.settings.tier)
        tier_combo = ttk.Combobox(row1, textvariable=self.tier_var, width=10,
                                   values=["beginner", "novice", "adept", "expert"],
                                   state="readonly")
        tier_combo.pack(side="left", padx=(5, 20))

        ttk.Label(row1, text="Mode:").pack(side="left")
        self.mode_var = tk.StringVar(value=self.settings.mode)
        ttk.Radiobutton(row1, text="NPC Contact", variable=self.mode_var,
                         value="npc_contact").pack(side="left", padx=3)
        ttk.Radiobutton(row1, text="Contractor", variable=self.mode_var,
                         value="walk_to_contractor").pack(side="left", padx=3)

        # Row 2: Equipment checkboxes
        row2 = ttk.Frame(frame)
        row2.pack(fill="x", pady=4)

        self.plank_sack_var = tk.BooleanVar(value=self.settings.has_plank_sack)
        self.imcando_var = tk.BooleanVar(value=self.settings.has_imcando_hammer)
        self.amys_saw_var = tk.BooleanVar(value=self.settings.has_amys_saw)

        ttk.Checkbutton(row2, text="Plank Sack", variable=self.plank_sack_var).pack(side="left", padx=3)
        ttk.Checkbutton(row2, text="Imcando Hammer", variable=self.imcando_var).pack(side="left", padx=3)
        ttk.Checkbutton(row2, text="Amy's Saw", variable=self.amys_saw_var).pack(side="left", padx=3)

        # Row 3: Teleport equipment
        row3 = ttk.Frame(frame)
        row3.pack(fill="x", pady=2)

        self.xerics_var = tk.BooleanVar(value=self.settings.has_xerics_talisman)
        self.row_var = tk.BooleanVar(value=self.settings.has_ring_of_wealth)
        self.cloak_var = tk.BooleanVar(value=self.settings.has_ardougne_cloak)

        ttk.Checkbutton(row3, text="Xeric's Talisman", variable=self.xerics_var).pack(side="left", padx=3)
        ttk.Checkbutton(row3, text="Ring of Wealth", variable=self.row_var).pack(side="left", padx=3)
        ttk.Checkbutton(row3, text="Ardougne Cloak", variable=self.cloak_var).pack(side="left", padx=3)

        # Row 4: Teleport method + Anti-detection
        row4 = ttk.Frame(frame)
        row4.pack(fill="x", pady=2)

        ttk.Label(row4, text="Teleports:").pack(side="left")
        self.tp_var = tk.StringVar(value="auto")
        ttk.Combobox(row4, textvariable=self.tp_var, width=10,
                      values=["auto", "tab", "equipment", "spell"],
                      state="readonly").pack(side="left", padx=(5, 20))

        ttk.Label(row4, text="Anti-Detect:").pack(side="left")
        self.anti_var = tk.StringVar(value=self.settings.anti_detection_level)
        ttk.Combobox(row4, textvariable=self.anti_var, width=8,
                      values=["low", "medium", "high"],
                      state="readonly").pack(side="left", padx=5)

        # Row 5: Session length + Stop key
        row5 = ttk.Frame(frame)
        row5.pack(fill="x", pady=2)

        ttk.Label(row5, text="Session:").pack(side="left")
        self.session_var = tk.IntVar(value=self.settings.session_length_minutes)
        tk.Scale(row5, from_=30, to=180, orient="horizontal", variable=self.session_var,
                 length=120, bg="#1a1a2e", fg="#e0e0e0", highlightthickness=0,
                 troughcolor="#333355").pack(side="left", padx=5)
        ttk.Label(row5, text="min").pack(side="left")

        ttk.Label(row5, text="  Stop Key:").pack(side="left", padx=(15, 0))
        self.stop_key_var = tk.StringVar(value=self.settings.stop_key)
        ttk.Entry(row5, textvariable=self.stop_key_var, width=5).pack(side="left", padx=5)

    def _build_status_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text=" Status ", padding=8)
        frame.pack(fill="x", pady=(0, 8))

        self.status_var = tk.StringVar(value="IDLE")
        self.current_var = tk.StringVar(value="—")
        self.stats_var = tk.StringVar(value="Contracts: 0 | Points: 0 | XP: 0")
        self.rate_var = tk.StringVar(value="Session: 00:00 | Rate: 0/hr")
        self.error_var = tk.StringVar(value="Errors: 0")

        ttk.Label(frame, textvariable=self.status_var,
                   font=("Segoe UI", 12, "bold"), foreground="#00ff88").pack(anchor="w")
        ttk.Label(frame, textvariable=self.current_var).pack(anchor="w")
        ttk.Label(frame, textvariable=self.stats_var).pack(anchor="w")
        ttk.Label(frame, textvariable=self.rate_var).pack(anchor="w")
        ttk.Label(frame, textvariable=self.error_var).pack(anchor="w")

    def _build_log_panel(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text=" Log ", padding=4)
        frame.pack(fill="both", expand=True, pady=(0, 8))

        self.log_text = scrolledtext.ScrolledText(
            frame, height=10, bg="#0d0d1a", fg="#cccccc",
            font=("Consolas", 9), state="disabled",
            insertbackground="#ffffff", wrap="word",
        )
        self.log_text.pack(fill="both", expand=True)

    def _build_controls(self, parent: ttk.Frame) -> None:
        frame = ttk.Frame(parent)
        frame.pack(fill="x")

        self.calibrate_btn = tk.Button(
            frame, text="CALIBRATE", command=self._on_calibrate,
            font=("Segoe UI", 11, "bold"), bg="#335599", fg="white",
            width=12, relief="flat",
        )
        self.calibrate_btn.pack(side="left", padx=3)

        self.start_btn = tk.Button(
            frame, text="START", command=self._on_start,
            font=("Segoe UI", 11, "bold"), bg="#22aa44", fg="white",
            width=12, relief="flat",
        )
        self.start_btn.pack(side="left", padx=3)

        self.stop_btn = tk.Button(
            frame, text="STOP", command=self._on_stop,
            font=("Segoe UI", 11, "bold"), bg="#cc3333", fg="white",
            width=12, relief="flat", state="disabled",
        )
        self.stop_btn.pack(side="left", padx=3)

    # ------------------------------------------------------------------
    # Settings Persistence
    # ------------------------------------------------------------------

    def _load_settings_to_ui(self) -> None:
        """Load saved settings into UI widgets."""
        pass  # Already done via default values in constructors

    def _save_settings_from_ui(self) -> BotSettings:
        """Read current UI values and save to settings."""
        self.settings.tier = self.tier_var.get()
        self.settings.mode = self.mode_var.get()
        self.settings.has_plank_sack = self.plank_sack_var.get()
        self.settings.has_imcando_hammer = self.imcando_var.get()
        self.settings.has_amys_saw = self.amys_saw_var.get()
        self.settings.has_xerics_talisman = self.xerics_var.get()
        self.settings.has_ring_of_wealth = self.row_var.get()
        self.settings.has_ardougne_cloak = self.cloak_var.get()
        self.settings.anti_detection_level = self.anti_var.get()
        self.settings.session_length_minutes = self.session_var.get()
        self.settings.stop_key = self.stop_key_var.get()

        # Set all teleport methods to the global preference
        tp = self.tp_var.get()
        self.settings.teleport_varrock = tp
        self.settings.teleport_falador = tp
        self.settings.teleport_ardougne = tp
        self.settings.teleport_hosidius = tp

        save_settings(self.settings)
        return self.settings

    # ------------------------------------------------------------------
    # Button Handlers
    # ------------------------------------------------------------------

    def _on_calibrate(self) -> None:
        wizard = CalibrationWizard(self.root, self._on_calibration_done)
        wizard.start()

    def _on_calibration_done(self, regions: ScreenRegions) -> None:
        self.regions = regions
        self._log_message("Calibration complete")

    def _on_start(self) -> None:
        if self.regions is None:
            messagebox.showwarning("Calibration Required",
                                    "Please run calibration first.")
            return

        settings = self._save_settings_from_ui()

        # Validate spellbook compatibility
        if settings.mode == "npc_contact":
            for city in ["varrock", "falador", "ardougne", "hosidius"]:
                tp_pref = getattr(settings, f"teleport_{city}")
                if tp_pref == "spell":
                    messagebox.showwarning(
                        "Incompatible Settings",
                        "NPC Contact requires Lunar spellbook.\n"
                        "Spell teleports require Standard spellbook.\n"
                        "Please use Tabs or Equipment teleports with NPC Contact mode."
                    )
                    return

        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.status_var.set("RUNNING")

        from bot.state_machine import MahoganyHomesBot
        self.bot = MahoganyHomesBot(settings, self.regions, self._log_message)

        self.bot_thread = threading.Thread(target=self.bot.start, daemon=True)
        self.bot_thread.start()

        self._update_status_loop()

    def _on_stop(self) -> None:
        if self.bot:
            self.bot.stop()
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.status_var.set("STOPPED")

    # ------------------------------------------------------------------
    # Status Updates
    # ------------------------------------------------------------------

    def _update_status_loop(self) -> None:
        """Periodically update the status panel from bot stats."""
        if self.bot and self.bot.is_running:
            stats = self.bot.stats
            state = self.bot.state

            self.current_var.set(f"State: {state.name}")
            self.stats_var.set(
                f"Contracts: {stats.contracts_completed} | "
                f"Points: {stats.total_points} | "
                f"XP: {stats.total_xp:,}"
            )
            self.rate_var.set(
                f"Session: {stats.elapsed_formatted} | "
                f"Rate: {stats.contracts_per_hour:.1f}/hr | "
                f"XP/hr: {stats.xp_per_hour:,.0f}"
            )
            self.error_var.set(f"Errors: {stats.errors}")

            self.root.after(1000, self._update_status_loop)
        else:
            self.status_var.set("STOPPED")
            self.start_btn.config(state="normal")
            self.stop_btn.config(state="disabled")

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log_message(self, msg: str) -> None:
        """Thread-safe log message to the GUI."""
        timestamp = time.strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {msg}\n"

        def _append():
            self.log_text.config(state="normal")
            self.log_text.insert("end", formatted)
            # Trim to 500 lines
            lines = int(self.log_text.index("end-1c").split(".")[0])
            if lines > 500:
                self.log_text.delete("1.0", f"{lines - 500}.0")
            self.log_text.see("end")
            self.log_text.config(state="disabled")

        self.root.after(0, _append)

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Start the Tkinter event loop."""
        self.root.mainloop()
