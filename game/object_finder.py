"""
Object detection via RuneLite Object Markers plugin.

The player tags game objects with unique, high-saturation colors using
RuneLite's Object Markers. The bot finds these colored overlays in the
viewport to locate objects dynamically — immune to camera rotation,
character position drift, and slight movement.

Required RuneLite Object Marker tags:
  Bank chest:     #FF0000 (Red)
  Conveyor belt:  #FFFF00 (Yellow)
  Bar dispenser:  #FF00FF (Magenta)

These colors never appear naturally in the Blast Furnace environment
(dark browns, greys, orange lava). False positive rate is near zero
with a tight tolerance.

Why this is better than fixed coordinates:
  - Camera-proof: overlay moves with the object
  - Position-proof: works regardless of where the object renders
  - Self-correcting: if a click misses, next scan still finds it
  - No recalibration needed after camera bumps or random events
"""

import numpy as np
from screen.capture import capture_region, find_color_in_region
from config import ScreenRegions


# RuneLite Object Marker colors (RGB)
MARKER_BANK = (255, 0, 0)       # Red — bank chest
MARKER_CONVEYOR = (255, 255, 0) # Yellow — conveyor belt
MARKER_DISPENSER = (255, 0, 255) # Magenta — bar dispenser

# Tight tolerance — these are pure saturated colors, very distinct
# from the BF environment (browns, greys, orange lava)
MARKER_TOLERANCE = 30


class ObjectFinder:
    """
    Locates RuneLite-tagged objects in the game viewport by scanning
    for their marker color and returning the centroid.

    Falls back to calibrated fixed positions if the marker is not found
    (e.g., object is off-screen, plugin disabled, or marker occluded).
    """

    def __init__(self, regions: ScreenRegions):
        self.regions = regions

        # Cache last-known positions to avoid full-viewport scans every time.
        # If the object hasn't moved (camera stable), the cached position
        # is reused. Full scan only triggers when cache misses.
        self._cache = {}

    def find_bank(self):
        """Find the bank chest (red marker). Returns (x, y) or None."""
        return self._find_object("bank", MARKER_BANK, self.regions.bank_pos)

    def find_conveyor(self):
        """Find the conveyor belt (yellow marker). Returns (x, y) or None."""
        return self._find_object("conveyor", MARKER_CONVEYOR, self.regions.conveyor_pos)

    def find_dispenser(self):
        """Find the bar dispenser (magenta marker). Returns (x, y) or None."""
        return self._find_object("dispenser", MARKER_DISPENSER, self.regions.dispenser_pos)

    def _find_object(self, name, marker_color, fallback_pos):
        """
        Find an object by its marker color in the game viewport.

        Strategy:
        1. Quick check: scan a small area around the cached/fallback position.
           If found, update cache and return immediately.
        2. Full scan: scan the entire game viewport.
           If found, update cache and return.
        3. Fallback: return the calibrated fixed position.
           This handles plugin-disabled or object-off-screen cases.

        Returns (x, y) screen coordinates of the object centroid.
        """
        # Use cached position or fallback as the starting search center
        search_center = self._cache.get(name, fallback_pos)

        # Step 1: Quick local scan (~80x80 area around expected position)
        result = self._scan_area(marker_color, search_center, radius=40)
        if result is not None:
            self._cache[name] = result
            return result

        # Step 2: Full viewport scan
        result = self._scan_viewport(marker_color)
        if result is not None:
            self._cache[name] = result
            return result

        # Step 3: Fallback to calibrated position
        return fallback_pos

    def _scan_area(self, color, center, radius=40):
        """Scan a small area around a center point for the marker color."""
        cx, cy = center
        x1 = max(self.regions.game_x, cx - radius)
        y1 = max(self.regions.game_y, cy - radius)
        x2 = min(self.regions.game_x + self.regions.game_w, cx + radius)
        y2 = min(self.regions.game_y + self.regions.game_h, cy + radius)

        w = x2 - x1
        h = y2 - y1
        if w <= 0 or h <= 0:
            return None

        frame = capture_region(x1, y1, w, h)
        offset = (x1, y1)

        return find_color_in_region(
            frame, color, x1, y1, x2, y2,
            tolerance=MARKER_TOLERANCE, region_offset=offset
        )

    def _scan_viewport(self, color):
        """Scan the full game viewport for the marker color."""
        gx = self.regions.game_x
        gy = self.regions.game_y
        gw = self.regions.game_w
        gh = self.regions.game_h

        frame = capture_region(gx, gy, gw, gh)
        offset = (gx, gy)

        return find_color_in_region(
            frame, color, gx, gy, gx + gw, gy + gh,
            tolerance=MARKER_TOLERANCE, region_offset=offset
        )

    def clear_cache(self):
        """Clear the position cache (e.g., after camera change detected)."""
        self._cache.clear()
