"""
Fast screenshot capture and color detection utilities.

Uses mss for high-performance screen capture (~1ms per frame).
All operations work on numpy arrays in RGB format.
"""
import math
from typing import Optional, Tuple, List

import mss
import numpy as np
from PIL import Image

_sct = mss.mss()


def capture_region(x: int, y: int, w: int, h: int) -> np.ndarray:
    """
    Capture a screen region and return as numpy RGB array.
    Shape: (h, w, 3) with dtype uint8.
    """
    monitor = {"left": x, "top": y, "width": w, "height": h}
    frame = np.array(_sct.grab(monitor))
    # mss returns BGRA — convert to RGB
    return frame[:, :, 2::-1]


def capture_full_monitor(monitor_index: int = 1) -> np.ndarray:
    """Capture the entire primary monitor."""
    mon = _sct.monitors[monitor_index]
    return capture_region(mon["left"], mon["top"], mon["width"], mon["height"])


def get_pixel_color(x: int, y: int) -> Tuple[int, int, int]:
    """Get the RGB color of a single pixel."""
    frame = capture_region(x, y, 1, 1)
    return int(frame[0, 0, 0]), int(frame[0, 0, 1]), int(frame[0, 0, 2])


def color_distance(c1: tuple, c2: tuple) -> float:
    """Euclidean distance between two RGB colors."""
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(c1, c2)))


def color_matches(c1: tuple, c2: tuple, tolerance: float) -> bool:
    """Check if two colors are within tolerance."""
    return color_distance(c1, c2) <= tolerance


def find_color_in_region(
    x: int, y: int, w: int, h: int,
    target_color: tuple,
    tolerance: float = 25,
    min_pixels: int = 5,
) -> Optional[Tuple[int, int]]:
    """
    Find the centroid of pixels matching target_color in a region.
    Returns absolute (x, y) or None if fewer than min_pixels match.
    """
    frame = capture_region(x, y, w, h)
    diff = np.sqrt(np.sum((frame.astype(float) - np.array(target_color, dtype=float)) ** 2, axis=2))
    mask = diff <= tolerance
    match_coords = np.argwhere(mask)  # (row, col) pairs

    if len(match_coords) < min_pixels:
        return None

    cy = int(np.mean(match_coords[:, 0])) + y
    cx = int(np.mean(match_coords[:, 1])) + x
    return cx, cy


def find_all_color_clusters(
    x: int, y: int, w: int, h: int,
    target_color: tuple,
    tolerance: float = 25,
    min_cluster_pixels: int = 15,
    max_clusters: int = 20,
) -> List[Tuple[int, int]]:
    """
    Find all distinct clusters of a color in a region.

    Uses scipy connected-component labeling to separate clusters.
    Returns list of absolute (x, y) centroids sorted by distance
    from region center.
    """
    from scipy.ndimage import label

    frame = capture_region(x, y, w, h)
    diff = np.sqrt(np.sum((frame.astype(float) - np.array(target_color, dtype=float)) ** 2, axis=2))
    mask = (diff <= tolerance).astype(np.int32)

    labeled, num_features = label(mask)
    if num_features == 0:
        return []

    centroids = []
    for i in range(1, num_features + 1):
        coords = np.argwhere(labeled == i)
        if len(coords) >= min_cluster_pixels:
            cy = int(np.mean(coords[:, 0])) + y
            cx = int(np.mean(coords[:, 1])) + x
            centroids.append((cx, cy))

    # Sort by distance from region center
    center_x = x + w // 2
    center_y = y + h // 2
    centroids.sort(key=lambda p: math.hypot(p[0] - center_x, p[1] - center_y))

    return centroids[:max_clusters]


def region_has_color(
    x: int, y: int, w: int, h: int,
    target_color: tuple,
    tolerance: float = 25,
    min_pixels: int = 10,
) -> bool:
    """Check if a region contains enough pixels of a given color."""
    frame = capture_region(x, y, w, h)
    diff = np.sqrt(np.sum((frame.astype(float) - np.array(target_color, dtype=float)) ** 2, axis=2))
    return int(np.sum(diff <= tolerance)) >= min_pixels


def frames_differ(frame1: np.ndarray, frame2: np.ndarray, threshold: float = 5.0) -> bool:
    """
    Check if two frames differ significantly.
    Used for movement detection — sample center region and compare.
    """
    if frame1.shape != frame2.shape:
        return True
    diff = np.mean(np.abs(frame1.astype(float) - frame2.astype(float)))
    return diff > threshold


def sample_center_region(x: int, y: int, w: int, h: int, size: int = 40) -> np.ndarray:
    """Capture a small region at the center of a larger region (for motion detection)."""
    cx = x + w // 2 - size // 2
    cy = y + h // 2 - size // 2
    return capture_region(cx, cy, size, size)
