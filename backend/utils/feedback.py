"""
User-facing fallback feedback messages for when pose landmarks
cannot be detected (partial visibility, poor lighting, etc.).

These are shown to the user in the feedback bar.
Technical error details are logged separately on the backend.
"""
import random

_VISIBILITY_HINTS = [
    "Body not fully visible",
    "Move back from camera",
    "Improve lighting",
    "Reposition your body in frame",
]


def visibility_hint():
    """Return a random user-friendly hint when pose detection fails."""
    return random.choice(_VISIBILITY_HINTS)
