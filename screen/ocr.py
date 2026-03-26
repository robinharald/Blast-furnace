"""
Chat text recognition for contract parsing.

Uses pytesseract with aggressive preprocessing for OSRS's pixel font.
Falls back to NPC name template matching for reliability.
"""
import re
import logging
from typing import Optional

import numpy as np

from screen.capture import capture_region
from data.npcs import NPC_NAMES

logger = logging.getLogger(__name__)

# Contract chat patterns (from RuneLite plugin source)
CONTRACT_PATTERN = re.compile(
    r"(?:Please could you g|G)o see (\w+)",
    re.IGNORECASE,
)
REMINDER_PATTERN = re.compile(
    r"You're currently on an? (\w+) Contract\. Go see (\w+)",
    re.IGNORECASE,
)
CONTRACT_ASSIGNED = re.compile(
    r"(\w+) Contract: Go see",
    re.IGNORECASE,
)
CONTRACT_FINISHED = re.compile(
    r"You have completed [\d,]+ contracts",
    re.IGNORECASE,
)
NO_MATERIALS = re.compile(
    r"You do not have the required materials",
    re.IGNORECASE,
)


def _preprocess_chat_image(frame: np.ndarray) -> np.ndarray:
    """
    Preprocess a chat box screenshot for OCR.

    OSRS text is white/yellow on a dark brown background.
    1. Convert to grayscale
    2. Binary threshold (keep bright text)
    3. Scale up 2x for better OCR accuracy
    4. Invert (black text on white for tesseract)
    """
    from PIL import Image

    gray = np.mean(frame, axis=2)
    binary = (gray > 160).astype(np.uint8) * 255
    # Scale up 2x
    img = Image.fromarray(binary)
    img = img.resize((img.width * 2, img.height * 2), Image.NEAREST)
    # Invert for tesseract (expects dark text on light bg)
    return 255 - np.array(img)


def read_chat_text(x: int, y: int, w: int, h: int) -> str:
    """
    OCR the chat box region and return the text.
    Returns empty string if pytesseract is not available.
    """
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        logger.warning("pytesseract not available, OCR disabled")
        return ""

    frame = capture_region(x, y, w, h)
    processed = _preprocess_chat_image(frame)
    img = Image.fromarray(processed)

    try:
        text = pytesseract.image_to_string(img, config="--psm 6")
        return text.strip()
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        return ""


def find_npc_name_in_text(text: str) -> Optional[str]:
    """
    Search for a known NPC name in OCR text.
    Returns the NPC key (lowercase) or None.
    """
    text_lower = text.lower()

    # Try regex patterns first
    for pattern in [CONTRACT_PATTERN, REMINDER_PATTERN]:
        match = pattern.search(text)
        if match:
            name = match.group(match.lastindex).lower()
            if name in NPC_NAMES:
                return name

    # Fallback: direct name search
    for name in NPC_NAMES:
        if name in text_lower:
            return name

    return None


def parse_tier_from_text(text: str) -> Optional[str]:
    """Extract contract tier from chat text."""
    match = CONTRACT_ASSIGNED.search(text)
    if match:
        tier = match.group(1).lower()
        if tier in ("beginner", "novice", "adept", "expert"):
            return tier

    match = REMINDER_PATTERN.search(text)
    if match:
        tier = match.group(1).lower()
        if tier in ("beginner", "novice", "adept", "expert"):
            return tier

    return None


def is_contract_finished(text: str) -> bool:
    """Check if the text indicates a contract was completed."""
    return bool(CONTRACT_FINISHED.search(text))


def is_no_materials(text: str) -> bool:
    """Check if the text indicates insufficient materials."""
    return bool(NO_MATERIALS.search(text))
