"""
Humanized keyboard input with natural timing.

All key presses go through pyautogui with variable inter-key delays.
"""
import random
import time

import pyautogui


def press_key(key: str, hold_min: float = 0.03, hold_max: float = 0.08) -> None:
    """Press and release a single key with human-like hold duration."""
    pyautogui.keyDown(key, _pause=False)
    time.sleep(random.uniform(hold_min, hold_max))
    pyautogui.keyUp(key, _pause=False)


def hold_key(key: str, duration: float) -> None:
    """Hold a key for a specific duration (e.g., camera rotation)."""
    variance = duration * 0.1
    actual = duration + random.uniform(-variance, variance)
    pyautogui.keyDown(key, _pause=False)
    time.sleep(max(0.05, actual))
    pyautogui.keyUp(key, _pause=False)


def type_text(text: str, min_delay: float = 0.04, max_delay: float = 0.12) -> None:
    """Type a string with variable inter-key delays."""
    for char in text:
        pyautogui.press(char, _pause=False)
        time.sleep(random.uniform(min_delay, max_delay))


def press_space() -> None:
    """Press SPACE (common for dialogue advancement)."""
    press_key("space")


def press_escape() -> None:
    """Press ESC (dismiss menus/dialogues)."""
    press_key("escape")


def press_number(n: int) -> None:
    """Press a number key 1-5 (dialogue option selection)."""
    if 1 <= n <= 5:
        press_key(str(n))


def press_f_key(n: int) -> None:
    """Press an F-key (F1-F12) for tab switching."""
    if 1 <= n <= 12:
        press_key(f"f{n}")
