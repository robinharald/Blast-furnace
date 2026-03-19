"""
Human-like mouse movement using the WindMouse algorithm.

This is the gold standard for undetectable mouse movement. It simulates:
- Wind force: random lateral deviations during travel
- Gravity: pull toward the target point
- Variable speed: faster in the middle, slower at start and end
- Natural overshoot and micro-correction
- Gaussian noise on the final click position

No straight lines. No constant speed. No teleporting.
"""

import math
import random
import time
import ctypes
import sys

import pyautogui

# Disable pyautogui's built-in pause and failsafe for our own control
pyautogui.PAUSE = 0
pyautogui.FAILSAFE = True  # Keep failsafe: move mouse to corner to abort


def _get_cursor_pos():
    """Get current mouse position."""
    return pyautogui.position()


def _platform_move(x, y):
    """
    Move the mouse cursor to (x, y) using OS-level calls.
    Falls back to pyautogui if platform calls aren't available.
    """
    try:
        if sys.platform == "win32":
            ctypes.windll.user32.SetCursorPos(int(x), int(y))
        else:
            pyautogui.moveTo(int(x), int(y), _pause=False)
    except Exception:
        pyautogui.moveTo(int(x), int(y), _pause=False)


def wind_mouse(start_x, start_y, end_x, end_y,
               gravity=9.0, wind=3.0, min_wait=2.0, max_wait=10.0,
               max_step=10.0, target_area=8.0):
    """
    WindMouse algorithm — attempt to move the mouse from (start_x, start_y) to
    (end_x, end_y) in a human-like way.

    Parameters:
        gravity: strength of the pull toward the target
        wind: strength of random wind deviations
        min_wait: minimum ms between steps (controls max speed)
        max_wait: max ms between steps (controls min speed)
        max_step: max pixels per step
        target_area: distance at which we slow down and get precise
    """
    sqrt3 = math.sqrt(3)
    sqrt5 = math.sqrt(5)

    current_x = float(start_x)
    current_y = float(start_y)
    wind_x = 0.0
    wind_y = 0.0

    points = []

    while True:
        dist = math.hypot(end_x - current_x, end_y - current_y)
        if dist < 1:
            break

        # Wind is stronger when far from target, weaker when close
        wind_mag = min(wind, dist)

        if dist >= target_area:
            # Far from target: apply wind and gravity
            wind_x = wind_x / sqrt3 + (random.random() * (wind_mag * 2 + 1) - wind_mag) / sqrt5
            wind_y = wind_y / sqrt3 + (random.random() * (wind_mag * 2 + 1) - wind_mag) / sqrt5
        else:
            # Near target: reduce wind, increase precision
            wind_x /= sqrt3
            wind_y /= sqrt3
            if max_step < 3:
                max_step = random.random() * 3 + 3.0
            else:
                max_step /= sqrt5

        # Apply gravity toward target
        grav_x = gravity * (end_x - current_x) / dist
        grav_y = gravity * (end_y - current_y) / dist

        # Calculate velocity
        vel_x = grav_x + wind_x
        vel_y = grav_y + wind_y

        # Limit step size
        vel_mag = math.hypot(vel_x, vel_y)
        if vel_mag > max_step:
            random_dist = max_step / 2.0 + random.random() * (max_step / 2.0)
            vel_x = (vel_x / vel_mag) * random_dist
            vel_y = (vel_y / vel_mag) * random_dist

        current_x += vel_x
        current_y += vel_y

        # Calculate wait time (slower near target, faster in middle)
        step_dist = math.hypot(vel_x, vel_y)
        if step_dist > 0:
            wait = max(min_wait, min(max_wait, round((max_wait - min_wait) * (target_area / max(dist, 1)))))
        else:
            wait = min_wait

        points.append((round(current_x), round(current_y), wait / 1000.0))

    # Execute the movement
    for px, py, wait in points:
        _platform_move(px, py)
        time.sleep(wait)


def move_to(x, y, variance=3):
    """
    Move mouse to target with WindMouse and slight positional variance.

    Args:
        x, y: target position
        variance: max pixel offset from exact target (humanizes click location)
    """
    # Add small random offset to target
    target_x = x + random.randint(-variance, variance)
    target_y = y + random.randint(-variance, variance)

    cur_x, cur_y = _get_cursor_pos()
    dist = math.hypot(target_x - cur_x, target_y - cur_y)

    # Adapt WindMouse parameters based on distance
    if dist < 50:
        # Short distance: gentle, precise
        wind_mouse(cur_x, cur_y, target_x, target_y,
                   gravity=12.0, wind=1.5, min_wait=3, max_wait=12,
                   max_step=5, target_area=5)
    elif dist < 250:
        # Medium distance: balanced
        wind_mouse(cur_x, cur_y, target_x, target_y,
                   gravity=9.0, wind=3.0, min_wait=2, max_wait=10,
                   max_step=12, target_area=8)
    else:
        # Long distance: fast then slow
        wind_mouse(cur_x, cur_y, target_x, target_y,
                   gravity=7.0, wind=5.0, min_wait=1, max_wait=8,
                   max_step=20, target_area=12)


def click(x, y, button="left", variance=3):
    """
    Move to position and click with human-like timing.
    """
    move_to(x, y, variance=variance)
    # Small pre-click delay (finger pressing down)
    time.sleep(random.uniform(0.04, 0.12))
    pyautogui.click(button=button, _pause=False)
    # Small post-click delay (finger releasing)
    time.sleep(random.uniform(0.03, 0.09))


def right_click(x, y, variance=3):
    """Right-click at position."""
    click(x, y, button="right", variance=variance)


def double_click(x, y, variance=3):
    """Double-click at position."""
    move_to(x, y, variance=variance)
    time.sleep(random.uniform(0.04, 0.10))
    pyautogui.click(button="left", _pause=False)
    time.sleep(random.uniform(0.06, 0.15))
    pyautogui.click(button="left", _pause=False)
    time.sleep(random.uniform(0.03, 0.08))


def click_in_region(x1, y1, x2, y2, button="left"):
    """
    Click at a random point within a rectangular region.
    Uses gaussian distribution centered in the region (humans tend to click center).
    """
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2
    w = (x2 - x1) / 2
    h = (y2 - y1) / 2

    # Gaussian with sigma = 1/3 of half-width, clamped to bounds
    tx = int(max(x1, min(x2, random.gauss(cx, w / 3))))
    ty = int(max(y1, min(y2, random.gauss(cy, h / 3))))

    click(tx, ty, button=button, variance=0)


def move_off_target():
    """Move mouse to a neutral area (away from clickable objects)."""
    # Move to a random spot in the game viewport (not on UI elements)
    x = random.randint(200, 450)
    y = random.randint(200, 350)
    move_to(x, y, variance=10)
