"""App-wide settings that don't belong to any single domain or infrastructure module."""

import os
from dataclasses import dataclass, field

DEFAULT_CORS_ALLOWED_ORIGINS = ("http://localhost:5173",)


@dataclass(frozen=True, slots=True)
class CorsSettings:
    allowed_origins: tuple[str, ...] = field(default_factory=lambda: DEFAULT_CORS_ALLOWED_ORIGINS)
    """Origins the frontend is served from (Vite dev server by default) - comma-separated
    in ``CORS_ALLOWED_ORIGINS``."""

    @classmethod
    def from_environment(cls) -> "CorsSettings":
        raw = os.environ.get("CORS_ALLOWED_ORIGINS")
        if not raw:
            return cls()
        origins = tuple(origin.strip() for origin in raw.split(",") if origin.strip())
        return cls(allowed_origins=origins or DEFAULT_CORS_ALLOWED_ORIGINS)
