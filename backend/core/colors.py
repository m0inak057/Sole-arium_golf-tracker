"""Colour constants for overlay rendering — OpenCV BGR order.

**OpenCV uses BGR, not RGB.**  Every constant is stored as a
``(B, G, R)`` tuple and suffixed with ``_BGR`` to prevent confusion.
See rules.md §6.
"""

from __future__ import annotations

# ── Primary skeleton / overlay colours ───────────────────────────────────────

CYAN_BGR: tuple[int, int, int] = (255, 212, 0)      # hex #00D4FF
YELLOW_BGR: tuple[int, int, int] = (0, 215, 255)     # hex #FFD700
GREEN_BGR: tuple[int, int, int] = (0, 200, 0)        # hex #00C800
AMBER_BGR: tuple[int, int, int] = (0, 165, 255)      # hex #FFA500
RED_BGR: tuple[int, int, int] = (0, 0, 255)           # hex #FF0000

# ── Neutral colours ──────────────────────────────────────────────────────────

WHITE_BGR: tuple[int, int, int] = (255, 255, 255)    # hex #FFFFFF
BLACK_BGR: tuple[int, int, int] = (0, 0, 0)          # hex #000000

# ── HUD-specific ─────────────────────────────────────────────────────────────

HUD_BG_BGR: tuple[int, int, int] = BLACK_BGR
PHASE_LABEL_YELLOW_BGR: tuple[int, int, int] = YELLOW_BGR
PHASE_LABEL_GREEN_BGR: tuple[int, int, int] = GREEN_BGR
PHASE_LABEL_WHITE_BGR: tuple[int, int, int] = WHITE_BGR
PROGRESS_BAR_ORANGE_BGR: tuple[int, int, int] = (0, 140, 255)  # hex #FF8C00
