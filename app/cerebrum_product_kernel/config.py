"""Kernel configuration (path and posture only; no secrets)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PlatformConfig:
    storage_path: Path
    network: bool = False
    kernel_version: str = "bakery-kernel/1.0.0"

    @classmethod
    def from_env(cls) -> "PlatformConfig":
        return cls(storage_path=Path(os.getenv("STORAGE_PATH", "./data")).resolve())


def load() -> PlatformConfig:
    return PlatformConfig.from_env()
