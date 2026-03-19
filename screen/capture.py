"""
Screen capture and pixel reading utilities.

Uses mss for fast screenshots (much faster than pyautogui).
All color checks are done on captured frames to avoid
excessive screen reads.
"""

import mss
import numpy as np
from PIL import Image


# Global screen capturer (reused for performance)
_sct = None


def _get_sct():
    global _sct
    if _sct is None:
        _sct = mss.mss()
    return _sct


def capture_screen(region=None):
    """
    Capture a screenshot.

    Args:
        region: (x, y, width, height) tuple, or None for full screen.

    Returns:
        numpy array of the screenshot (RGB).
    """
    sct = _get_sct()
    if region:
        x, y, w, h = region
        monitor = {"left": x, "top": y, "width": w, "height": h}
    else:
        monitor = sct.monitors[1]  # Primary monitor

    frame = sct.grab(monitor)
    # mss gives BGRA, convert to RGB
    img = np.array(frame)
    return img[:, :, :3][:, :, ::-1]  # BGRA -> RGB


def capture_region(x, y, width, height):
    """Capture a specific screen region as RGB numpy array."""
    return capture_screen(region=(x, y, width, height))


def get_pixel_color(x, y):
    """
    Get the RGB color of a single pixel on screen.
    Returns (r, g, b) tuple.
    """
    img = capture_region(x, y, 1, 1)
    return tuple(img[0, 0])


def get_pixel_color_from_frame(frame, x, y, region_offset=(0, 0)):
    """
    Get pixel color from an already-captured frame.

    Args:
        frame: numpy RGB array
        x, y: screen coordinates
        region_offset: (ox, oy) if frame was captured from a sub-region
    """
    rx = x - region_offset[0]
    ry = y - region_offset[1]
    if 0 <= ry < frame.shape[0] and 0 <= rx < frame.shape[1]:
        return tuple(frame[ry, rx])
    return (0, 0, 0)


def color_distance(c1, c2):
    """Euclidean distance between two RGB colors."""
    return ((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2 + (c1[2] - c2[2]) ** 2) ** 0.5


def color_matches(c1, c2, tolerance=15):
    """Check if two colors are close enough to match."""
    return color_distance(c1, c2) <= tolerance


def find_color_in_region(frame, target_color, x1, y1, x2, y2,
                         tolerance=15, region_offset=(0, 0)):
    """
    Find the centroid of pixels matching target_color within a region of a frame.

    Returns (x, y) in screen coordinates, or None if not found.
    """
    ox, oy = region_offset
    rx1 = max(0, x1 - ox)
    ry1 = max(0, y1 - oy)
    rx2 = min(frame.shape[1], x2 - ox)
    ry2 = min(frame.shape[0], y2 - oy)

    sub = frame[ry1:ry2, rx1:rx2]
    if sub.size == 0:
        return None

    # Find matching pixels
    diff = np.sqrt(np.sum((sub.astype(float) - np.array(target_color, dtype=float)) ** 2, axis=2))
    matches = np.where(diff <= tolerance)

    if len(matches[0]) == 0:
        return None

    # Return centroid of matching pixels (in screen coordinates)
    cy = int(np.mean(matches[0])) + ry1 + oy
    cx = int(np.mean(matches[1])) + rx1 + ox
    return (cx, cy)


def count_color_in_region(frame, target_color, x1, y1, x2, y2,
                          tolerance=15, region_offset=(0, 0)):
    """
    Count pixels matching target_color in a region.
    """
    ox, oy = region_offset
    rx1 = max(0, x1 - ox)
    ry1 = max(0, y1 - oy)
    rx2 = min(frame.shape[1], x2 - ox)
    ry2 = min(frame.shape[0], y2 - oy)

    sub = frame[ry1:ry2, rx1:rx2]
    if sub.size == 0:
        return 0

    diff = np.sqrt(np.sum((sub.astype(float) - np.array(target_color, dtype=float)) ** 2, axis=2))
    return int(np.sum(diff <= tolerance))


def region_has_color(frame, target_color, x1, y1, x2, y2,
                     tolerance=15, min_pixels=5, region_offset=(0, 0)):
    """
    Check if a region contains at least min_pixels of the target color.
    """
    count = count_color_in_region(frame, target_color, x1, y1, x2, y2,
                                  tolerance, region_offset)
    return count >= min_pixels


def frame_to_image(frame):
    """Convert numpy RGB array to PIL Image."""
    return Image.fromarray(frame)
