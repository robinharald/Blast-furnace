"""
Human-like mouse movement and clicking.

Implements multiple movement styles to prevent statistical fingerprinting:
- WindMouse (3 profiles: default, lazy, precise)
- Bezier curves (1-2 random control points)

The active style is selected per-session with occasional variation.
"""
import math
import random
import time
from typing import Optional, Tuple

import pyautogui

# Disable pyautogui's built-in pause (we handle timing ourselves)
pyautogui.PAUSE = 0
pyautogui.FAILSAFE = True  # move to corner = emergency stop


def _get_pos() -> Tuple[int, int]:
    return pyautogui.position()


def _platform_move(x: int, y: int) -> None:
    pyautogui.moveTo(int(x), int(y), _pause=False)


# ---------------------------------------------------------------------------
# WindMouse Algorithm
# ---------------------------------------------------------------------------

def _wind_mouse(
    start_x: float, start_y: float,
    end_x: float, end_y: float,
    gravity: float = 9.0,
    wind: float = 3.0,
    min_wait: float = 2.0,
    max_wait: float = 10.0,
    max_step: float = 12.0,
    target_area: float = 8.0,
) -> list:
    """
    Generate a list of (x, y) points along a WindMouse path.

    Physics-based: wind force deviates the path randomly,
    gravity pulls toward the target. Speed varies naturally.
    """
    points = []
    sqrt2 = math.sqrt(2)
    sqrt3 = math.sqrt(3)
    sqrt5 = math.sqrt(5)

    cx, cy = start_x, start_y
    wind_x = wind_y = 0.0
    v_x = v_y = 0.0

    dist = math.hypot(end_x - cx, end_y - cy)

    while dist >= 1:
        wind_mag = min(wind, dist)

        if dist >= target_area:
            wind_x = wind_x / sqrt3 + (random.random() * 2 - 1) * wind_mag / sqrt5
            wind_y = wind_y / sqrt3 + (random.random() * 2 - 1) * wind_mag / sqrt5
        else:
            wind_x /= sqrt2
            wind_y /= sqrt2
            if max_step < 3:
                max_step = random.random() * 3 + 3.0
            else:
                max_step /= sqrt5

        v_x += wind_x + gravity * (end_x - cx) / dist
        v_y += wind_y + gravity * (end_y - cy) / dist

        v_mag = math.hypot(v_x, v_y)
        if v_mag > max_step:
            rand_scale = max_step / 2 + random.random() * max_step / 2
            v_x = v_x / v_mag * rand_scale
            v_y = v_y / v_mag * rand_scale

        cx += v_x
        cy += v_y

        dist = math.hypot(end_x - cx, end_y - cy)
        points.append((round(cx), round(cy)))

    points.append((round(end_x), round(end_y)))
    return points


def _get_wind_params(distance: float, profile: str = "default") -> dict:
    """Get WindMouse parameters based on distance and profile."""
    profiles = {
        "default": {
            "short":  {"gravity": 12, "wind": 1.5, "min_wait": 3, "max_wait": 12, "max_step": 5},
            "medium": {"gravity": 9,  "wind": 3,   "min_wait": 2, "max_wait": 10, "max_step": 12},
            "long":   {"gravity": 7,  "wind": 5,   "min_wait": 1, "max_wait": 8,  "max_step": 20},
        },
        "lazy": {
            "short":  {"gravity": 8,  "wind": 3,   "min_wait": 4, "max_wait": 15, "max_step": 4},
            "medium": {"gravity": 5,  "wind": 5,   "min_wait": 3, "max_wait": 12, "max_step": 10},
            "long":   {"gravity": 4,  "wind": 7,   "min_wait": 2, "max_wait": 10, "max_step": 18},
        },
        "precise": {
            "short":  {"gravity": 16, "wind": 0.8, "min_wait": 2, "max_wait": 10, "max_step": 4},
            "medium": {"gravity": 14, "wind": 1.5, "min_wait": 1, "max_wait": 8,  "max_step": 10},
            "long":   {"gravity": 11, "wind": 2,   "min_wait": 1, "max_wait": 6,  "max_step": 16},
        },
    }

    p = profiles.get(profile, profiles["default"])
    if distance < 50:
        return p["short"]
    elif distance < 250:
        return p["medium"]
    else:
        return p["long"]


# ---------------------------------------------------------------------------
# Bezier Curve Movement
# ---------------------------------------------------------------------------

def _bezier_point(t: float, points: list) -> Tuple[float, float]:
    """Evaluate a Bezier curve at parameter t (0..1)."""
    n = len(points) - 1
    x = y = 0.0
    for i, (px, py) in enumerate(points):
        coeff = math.comb(n, i) * (t ** i) * ((1 - t) ** (n - i))
        x += coeff * px
        y += coeff * py
    return x, y


def _bezier_move_points(
    start_x: float, start_y: float,
    end_x: float, end_y: float,
    steps: int = 50,
) -> list:
    """Generate Bezier curve points with 1-2 random control points."""
    num_controls = random.choice([1, 2])
    controls = []
    for _ in range(num_controls):
        t = random.uniform(0.2, 0.8)
        mx = start_x + (end_x - start_x) * t + random.gauss(0, 30)
        my = start_y + (end_y - start_y) * t + random.gauss(0, 30)
        controls.append((mx, my))

    all_points = [(start_x, start_y)] + controls + [(end_x, end_y)]

    path = []
    for i in range(steps + 1):
        t = i / steps
        px, py = _bezier_point(t, all_points)
        path.append((round(px), round(py)))
    return path


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def move_to(
    x: int, y: int,
    variance: float = 3.0,
    style: Optional[str] = None,
) -> None:
    """
    Move the mouse to (x, y) with human-like movement.

    Args:
        x, y: Target position
        variance: Gaussian jitter on the target (pixels)
        style: Movement style — "default", "lazy", "precise", "bezier"
               If None, uses the session default with 20% variation.
    """
    # Add positional jitter
    tx = int(x + random.gauss(0, variance))
    ty = int(y + random.gauss(0, variance))

    cur_x, cur_y = _get_pos()
    dist = math.hypot(tx - cur_x, ty - cur_y)

    if dist < 2:
        return

    if style is None:
        style = "default"

    if style == "bezier":
        points = _bezier_move_points(cur_x, cur_y, tx, ty)
        for i, (px, py) in enumerate(points):
            _platform_move(px, py)
            progress = i / max(len(points) - 1, 1)
            speed = 1.0 + 2.0 * math.sin(progress * math.pi)
            wait = random.uniform(2, 8) / max(speed, 0.5)
            time.sleep(wait / 1000.0)
    else:
        profile = style if style in ("default", "lazy", "precise") else "default"
        params = _get_wind_params(dist, profile)
        points = _wind_mouse(cur_x, cur_y, tx, ty, **params)

        for px, py in points:
            _platform_move(px, py)
            wait = random.uniform(params["min_wait"], params["max_wait"])
            time.sleep(wait / 1000.0)


def click(
    x: int, y: int,
    variance: float = 3.0,
    style: Optional[str] = None,
    button: str = "left",
) -> None:
    """Move to position and click."""
    move_to(x, y, variance=variance, style=style)
    time.sleep(random.uniform(0.02, 0.08))
    pyautogui.click(button=button, _pause=False)


def right_click(x: int, y: int, variance: float = 3.0, style: Optional[str] = None) -> None:
    """Move to position and right-click."""
    click(x, y, variance=variance, style=style, button="right")


def double_click(x: int, y: int, variance: float = 3.0, style: Optional[str] = None) -> None:
    """Move to position and double-click."""
    move_to(x, y, variance=variance, style=style)
    time.sleep(random.uniform(0.02, 0.06))
    pyautogui.click(button="left", _pause=False)
    time.sleep(random.uniform(0.04, 0.12))
    pyautogui.click(button="left", _pause=False)


def move_off_target(variance: int = 100) -> None:
    """Move mouse to a random neutral position (away from game objects)."""
    cx, cy = _get_pos()
    dx = cx + random.randint(-variance, variance)
    dy = cy + random.randint(-variance, variance)
    move_to(dx, dy, variance=5, style="lazy")
