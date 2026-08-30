"""Config Resolution Protocol for okf-wiki.

Resolution order (framework spec in .skills/okf-wiki/SKILL.md):
0. Inline bundle override (``@name``) — resolves <global config dir>/config.<name>
   directly, overriding the steps below. Missing name is an error, never a
   silent fallback to the default.
1. Walk up from CWD — first ``.env`` containing ``OKF_BUNDLE_PATH`` wins.
2. Global config — ``$XDG_CONFIG_HOME/okf-wiki/config`` (default
   ``~/.config/okf-wiki``). Legacy installs migrated from obsidian-wiki keep
   using ``~/.obsidian-wiki`` when present and XDG is absent.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


class ConfigError(Exception):
    """Raised when no configuration can be resolved."""


@dataclass(frozen=True)
class Config:
    """Resolved okf-wiki configuration."""

    bundle_path: Optional[Path] = None
    repo_path: Optional[Path] = None
    config_file: Optional[Path] = None  # the .env or config file that resolved
    source: str = "none"  # name | env | global | none
    name: Optional[str] = None  # set when resolved via @name override

    def require_bundle(self) -> Path:
        if self.bundle_path is None:
            raise ConfigError(
                "OKF_BUNDLE_PATH is not set — run `okf-wiki` inside a directory "
                "with a .env, or create the global config (see wiki-setup)."
            )
        return self.bundle_path


def global_config_dir() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    xdg_dir = Path(xdg) if xdg else Path.home() / ".config"
    xdg_dir = xdg_dir / "okf-wiki"
    legacy = Path.home() / ".obsidian-wiki"
    if legacy.is_dir() and not xdg_dir.exists():
        return legacy  # migrated installs keep their pre-XDG layout
    return xdg_dir


def _parse_kv_file(path: Path) -> dict:
    """Parse a simple KEY=VALUE file: strip quotes, skip blanks/comments."""
    values: dict = {}
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return values
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def _expand(value: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(value))).resolve()


def list_named_bundles() -> dict:
    """Available bundle profiles: {name: config_path} from config.<name>."""
    gdir = global_config_dir()
    profiles: dict = {}
    if gdir.is_dir():
        for cfg in sorted(gdir.glob("config.*")):
            profiles[cfg.name[len("config.") :]] = cfg
    return profiles


def resolve_config(name: Optional[str] = None, start_dir: Optional[Path] = None) -> Config:
    """Resolve config per the Config Resolution Protocol.

    ``name`` corresponds to the ``@name`` inline override token.
    """
    if name:
        gdir = global_config_dir()
        named = gdir / f"config.{name}"
        if named.is_file():
            vals = _parse_kv_file(named)
            return Config(
                bundle_path=_expand(vals["OKF_BUNDLE_PATH"]) if vals.get("OKF_BUNDLE_PATH") else None,
                repo_path=_expand(vals["OKF_WIKI_REPO"]) if vals.get("OKF_WIKI_REPO") else None,
                config_file=named.resolve(),
                source="name",
                name=name,
            )
        available = ", ".join(sorted(list_named_bundles())) or "(none)"
        raise ConfigError(
            f"Bundle profile '{name}' does not exist (config.{name} not found in {gdir}). "
            f"Available: {available}"
        )

    # Step 1: walk up from start_dir (default CWD) for a .env with OKF_BUNDLE_PATH.
    current = (start_dir or Path.cwd()).resolve()
    home = Path.home().resolve()
    while True:
        env_file = current / ".env"
        if env_file.is_file():
            vals = _parse_kv_file(env_file)
            if vals.get("OKF_BUNDLE_PATH"):
                return Config(
                    bundle_path=_expand(vals["OKF_BUNDLE_PATH"]),
                    repo_path=_expand(vals["OKF_WIKI_REPO"]) if vals.get("OKF_WIKI_REPO") else None,
                    config_file=env_file.resolve(),
                    source="env",
                )
        if current == home or current.parent == current:
            break
        current = current.parent

    # Step 2: global config.
    gcfg = global_config_dir() / "config"
    if gcfg.is_file() or gcfg.is_symlink():
        vals = _parse_kv_file(gcfg)
        if vals.get("OKF_BUNDLE_PATH"):
            return Config(
                bundle_path=_expand(vals["OKF_BUNDLE_PATH"]),
                repo_path=_expand(vals["OKF_WIKI_REPO"]) if vals.get("OKF_WIKI_REPO") else None,
                config_file=gcfg.resolve(),
                source="global",
            )

    return Config()  # source="none" — callers decide whether that is fatal
