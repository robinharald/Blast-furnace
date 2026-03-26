"""
Step-by-step calibration wizard.

Guides the user through clicking key screen positions to calibrate
the bot's coordinate system. Results saved to calibration.json.
"""
import tkinter as tk
from tkinter import messagebox
import logging
from typing import Callable, Optional

from config.settings import ScreenRegions, Region, Point, save_calibration

logger = logging.getLogger(__name__)

WIZARD_STEPS = [
    ("Game Viewport — TOP-LEFT corner",
     "Click the TOP-LEFT corner of the game viewport (where the 3D world begins)."),
    ("Game Viewport — BOTTOM-RIGHT corner",
     "Click the BOTTOM-RIGHT corner of the game viewport."),
    ("Inventory — SLOT 1 center",
     "Click the CENTER of the first inventory slot (top-left slot)."),
    ("Minimap — CENTER",
     "Click the exact CENTER of the minimap circle."),
    ("Run Energy ORB",
     "Click the center of the run energy orb (near minimap)."),
    ("Chat Box — TOP-LEFT corner",
     "Click the TOP-LEFT corner of the chat message area."),
    ("Chat Box — BOTTOM-RIGHT corner",
     "Click the BOTTOM-RIGHT corner of the chat message area."),
    ("Spellbook TAB icon",
     "Click the spellbook tab icon in the interface panel. (Skip if Mode B)"),
    ("Equipment TAB icon",
     "Click the equipment tab icon in the interface panel."),
]


class CalibrationWizard:
    """
    Transparent overlay window that captures mouse clicks for calibration.
    """

    def __init__(self, parent: tk.Tk, on_complete: Callable[[ScreenRegions], None]):
        self.parent = parent
        self.on_complete = on_complete
        self.current_step = 0
        self.clicks = []
        self.overlay = None
        self.label = None

    def start(self) -> None:
        """Launch the calibration overlay."""
        self.current_step = 0
        self.clicks = []

        # Create a fullscreen transparent overlay
        self.overlay = tk.Toplevel(self.parent)
        self.overlay.attributes("-fullscreen", True)
        self.overlay.attributes("-alpha", 0.3)
        self.overlay.attributes("-topmost", True)
        self.overlay.configure(bg="black")

        # Instruction label
        self.label = tk.Label(
            self.overlay, text="", font=("Arial", 16, "bold"),
            fg="white", bg="black", wraplength=600,
        )
        self.label.place(relx=0.5, rely=0.1, anchor="center")

        # Step counter
        self.step_label = tk.Label(
            self.overlay, text="", font=("Arial", 12),
            fg="yellow", bg="black",
        )
        self.step_label.place(relx=0.5, rely=0.05, anchor="center")

        # Cancel button
        cancel_btn = tk.Button(
            self.overlay, text="Cancel (ESC)", command=self._cancel,
            font=("Arial", 11), bg="#cc3333", fg="white",
        )
        cancel_btn.place(relx=0.5, rely=0.95, anchor="center")

        self.overlay.bind("<Button-1>", self._on_click)
        self.overlay.bind("<Escape>", lambda e: self._cancel())

        self._show_step()

    def _show_step(self) -> None:
        """Display the current calibration step instruction."""
        if self.current_step >= len(WIZARD_STEPS):
            self._finish()
            return

        title, instruction = WIZARD_STEPS[self.current_step]
        self.step_label.config(text=f"Step {self.current_step + 1} of {len(WIZARD_STEPS)}")
        self.label.config(text=f"{title}\n\n{instruction}")

    def _on_click(self, event: tk.Event) -> None:
        """Handle a calibration click."""
        x, y = event.x_root, event.y_root
        self.clicks.append((x, y))
        logger.info(f"Calibration step {self.current_step + 1}: ({x}, {y})")

        self.current_step += 1
        self._show_step()

    def _finish(self) -> None:
        """Build ScreenRegions from collected clicks and save."""
        if self.overlay:
            self.overlay.destroy()

        if len(self.clicks) < len(WIZARD_STEPS):
            messagebox.showwarning("Calibration", "Not enough clicks captured.")
            return

        vp_tl = self.clicks[0]
        vp_br = self.clicks[1]
        inv_origin = self.clicks[2]
        minimap_center = self.clicks[3]
        run_orb = self.clicks[4]
        chat_tl = self.clicks[5]
        chat_br = self.clicks[6]
        spellbook_tab = self.clicks[7]
        equipment_tab = self.clicks[8]

        regions = ScreenRegions(
            viewport=Region(
                x=vp_tl[0], y=vp_tl[1],
                w=vp_br[0] - vp_tl[0], h=vp_br[1] - vp_tl[1],
            ),
            inventory_origin=Point(x=inv_origin[0], y=inv_origin[1]),
            chat_box=Region(
                x=chat_tl[0], y=chat_tl[1],
                w=chat_br[0] - chat_tl[0], h=chat_br[1] - chat_tl[1],
            ),
            minimap_center=Point(x=minimap_center[0], y=minimap_center[1]),
            run_orb=Point(x=run_orb[0], y=run_orb[1]),
            spellbook_tab=Point(x=spellbook_tab[0], y=spellbook_tab[1]),
            equipment_tab=Point(x=equipment_tab[0], y=equipment_tab[1]),
        )

        save_calibration(regions)
        messagebox.showinfo("Calibration", "Calibration saved successfully!")
        self.on_complete(regions)

    def _cancel(self) -> None:
        """Cancel the calibration wizard."""
        if self.overlay:
            self.overlay.destroy()
