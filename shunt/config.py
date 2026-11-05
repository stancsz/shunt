"""Environment configuration at the application boundary; policy stays model-independent."""

import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping
from urllib.parse import urlsplit

from dotenv import dotenv_values

DEFAULT_MODELS = {
    "T1": "mimo-v2.6-distill-qwen-9b",
    "T2": "qwen3.8:27b",
    "T3": "deepseek-v4.1-flash:1017",
}


@dataclass(frozen=True)
class Target:
    model: str
    base_url: str
    timeout_seconds: float
    api_key: str = field(default="", repr=False)

    def public(self) -> dict:
        """Connection metadata safe to include in a routing decision."""
        return {"model": self.model, "base_url": self.base_url,
                "timeout_seconds": self.timeout_seconds}


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    targets: dict[str, Target]


def load_settings(
    env_file: str | Path = ".env", *, environ: Mapping[str, str] | None = None
) -> Settings:
    """Read explicit .env then process environment, without changing os.environ.

    Interpolation is disabled: credentials containing dollar signs remain literal.
    """
    values = {k: v for k, v in dotenv_values(env_file, interpolate=False).items() if v is not None}
    values.update(os.environ if environ is None else environ)

    def setting(name: str, default: str) -> str:
        value = values.get(name, default).strip()
        if not value:
            raise ValueError(f"{name} must not be empty")
        return value

    host = setting("SHUNT_HOST", "127.0.0.1")
    try:
        port = int(setting("SHUNT_PORT", "18765"))
        if not 1 <= port <= 65535:
            raise ValueError
    except ValueError:
        raise ValueError("SHUNT_PORT must be an integer from 1 to 65535") from None

    targets = {}
    for tier, default_model in DEFAULT_MODELS.items():
        prefix = f"SHUNT_{tier}"
        model = setting(f"{prefix}_MODEL", default_model)
        base_url = setting(f"{prefix}_BASE_URL", values.get("SHUNT_TARGET_BASE_URL", "http://127.0.0.1:11434/v1")).rstrip("/")
        try:
            parsed = urlsplit(base_url)
            valid = (parsed.scheme in ("http", "https") and parsed.hostname
                     and not parsed.username and not parsed.password
                     and not parsed.query and not parsed.fragment)
            port_value = parsed.port  # Validate malformed/out-of-range URL ports.
            if not valid or port_value == 0:
                raise ValueError
        except ValueError:
            raise ValueError(f"{prefix}_BASE_URL must be an HTTP(S) URL without credentials, query, or fragment") from None
        try:
            timeout = float(setting(f"{prefix}_TIMEOUT_SECONDS", values.get("SHUNT_TARGET_TIMEOUT_SECONDS", "120")))
            if not math.isfinite(timeout) or timeout <= 0:
                raise ValueError
        except ValueError:
            raise ValueError(f"{prefix}_TIMEOUT_SECONDS must be a finite positive number") from None
        api_key = values.get(f"{prefix}_API_KEY", values.get("SHUNT_TARGET_API_KEY", ""))
        targets[tier] = Target(model, base_url, timeout, api_key)
    return Settings(host, port, targets)
