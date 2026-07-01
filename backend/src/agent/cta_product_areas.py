"""Known Covis product areas for hybrid 'where' CTA suggestions."""

from __future__ import annotations

# Fallback when the bot asks where an issue appears and none are mentioned yet.
DEFAULT_PRODUCT_AREAS: tuple[str, ...] = (
    "Patient dashboard",
    "Mobile app",
    "Reports export",
    "Card scanning",
    "Dashboard graphs",
    "Reminders module",
    "Admin settings",
    "Login screen",
)
