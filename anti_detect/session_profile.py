"""
Per-session behavioral personality.

Each session generates a unique profile that governs reaction speed,
click precision, break patterns, mouse style, and more. No two sessions
should produce identical statistical fingerprints.
"""
import random


class SessionProfile:
    """
    A randomized behavioral profile generated once per bot session.
    All timing and behavior decisions reference this profile.
    """

    def __init__(self):
        # Core speed personality (multiplier on all delays)
        self.reaction_speed = max(0.6, min(1.4, random.gauss(1.0, 0.15)))

        # Click precision — affects jitter radius
        self.click_precision = max(0.7, min(1.3, random.gauss(1.0, 0.1)))

        # Break patterns
        self.micro_break_frequency = random.uniform(0.002, 0.01)
        self.macro_break_interval_min = random.uniform(20, 45)  # minutes
        self.macro_break_duration_range = (
            random.uniform(20, 60),   # min seconds
            random.uniform(90, 240),  # max seconds
        )

        # Session length
        self.session_length_minutes = max(30, random.gauss(90, 30))

        # Attention / distraction
        self.distraction_chance = random.uniform(0.01, 0.05)

        # Mouse movement style preference
        self.mouse_style = random.choice([
            "default", "default", "default",  # weighted toward default
            "lazy",
            "precise",
            "bezier",
        ])

        # How optimally the player plays (1.0 = perfect, lower = more mistakes)
        self.efficiency = random.uniform(0.7, 0.95)

        # Social behavior
        self.types_in_chat = random.random() < 0.12
        self.checks_stats = random.random() < 0.30
        self.checks_equipment = random.random() < 0.15

        # Misclick probability
        self.misclick_chance = random.uniform(0.02, 0.07)
        self.hesitation_chance = random.uniform(0.05, 0.15)
        self.double_click_chance = random.uniform(0.03, 0.10)

        # Hotspot ordering preference
        self.suboptimal_order_chance = random.uniform(0.08, 0.20)

        # Tea acceptance threshold (run energy %)
        self.tea_threshold = random.randint(15, 45)

    def jitter_radius(self) -> float:
        """Click jitter radius in pixels (affected by precision personality)."""
        return max(1.0, 3.0 * self.click_precision)

    def pick_mouse_style(self) -> str:
        """
        Pick a mouse movement style for this action.
        80% session default, 20% random alternative.
        """
        if random.random() < 0.80:
            return self.mouse_style
        return random.choice(["default", "lazy", "precise", "bezier"])

    def should_misclick(self) -> bool:
        return random.random() < self.misclick_chance

    def should_hesitate(self) -> bool:
        return random.random() < self.hesitation_chance

    def should_double_click(self) -> bool:
        return random.random() < self.double_click_chance

    def should_suboptimal_order(self) -> bool:
        return random.random() < self.suboptimal_order_chance

    def should_distract(self) -> bool:
        return random.random() < self.distraction_chance

    def should_micro_break(self) -> bool:
        return random.random() < self.micro_break_frequency

    def __repr__(self) -> str:
        return (
            f"SessionProfile(speed={self.reaction_speed:.2f}, "
            f"precision={self.click_precision:.2f}, "
            f"mouse={self.mouse_style}, "
            f"efficiency={self.efficiency:.2f}, "
            f"session_len={self.session_length_minutes:.0f}min)"
        )
