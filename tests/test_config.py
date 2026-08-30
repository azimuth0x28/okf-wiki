"""Tests for the Config Resolution Protocol (okf_wiki.config)."""

import os
from pathlib import Path

import pytest

from okf_wiki.config import ConfigError, global_config_dir, list_named_bundles, resolve_config


@pytest.fixture()
def isolated_env(tmp_path, monkeypatch):
    """Isolate CWD, HOME and XDG_CONFIG_HOME so resolution never escapes tmp."""
    home = tmp_path / "home"
    cwd = tmp_path / "work" / "sub"
    xdg = tmp_path / "xdg"
    cwd.mkdir(parents=True)
    home.mkdir()
    xdg.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(xdg))
    monkeypatch.delenv("OKF_BUNDLE_PATH", raising=False)
    monkeypatch.chdir(cwd)
    return {"home": home, "cwd": cwd, "xdg": xdg, "tmp": tmp_path}


def test_env_walk_up_finds_okf_bundle_path(isolated_env):
    env = isolated_env
    bundle = env["tmp"] / "bundle"
    bundle.mkdir()
    (env["tmp"] / "work" / ".env").write_text(f'OKF_BUNDLE_PATH="{bundle}"\n', encoding="utf-8")

    cfg = resolve_config(start_dir=env["cwd"])
    assert cfg.source == "env"
    assert cfg.bundle_path == bundle.resolve()
    assert cfg.config_file == (env["tmp"] / "work" / ".env").resolve()


def test_walk_up_skips_env_without_bundle_path(isolated_env):
    env = isolated_env
    bundle = env["tmp"] / "b2"
    bundle.mkdir()
    (env["cwd"] / ".env").write_text("SOMETHING_ELSE=1\n", encoding="utf-8")
    (env["tmp"] / "work" / ".env").write_text(f"OKF_BUNDLE_PATH={bundle}\n", encoding="utf-8")

    cfg = resolve_config(start_dir=env["cwd"])
    assert cfg.bundle_path == bundle.resolve()


def test_env_without_bundle_path_falls_through_to_global(isolated_env):
    env = isolated_env
    bundle = env["tmp"] / "g-bundle"
    bundle.mkdir()
    gdir = env["xdg"] / "okf-wiki"
    gdir.mkdir()
    (gdir / "config").write_text(f"OKF_BUNDLE_PATH={bundle}\n", encoding="utf-8")
    (env["cwd"] / ".env").write_text("# only a comment\n", encoding="utf-8")

    cfg = resolve_config(start_dir=env["cwd"])
    assert cfg.source == "global"
    assert cfg.bundle_path == bundle.resolve()


def test_no_config_resolves_to_unset(isolated_env):
    cfg = resolve_config(start_dir=isolated_env["cwd"])
    assert cfg.source == "none"
    assert cfg.bundle_path is None
    with pytest.raises(ConfigError):
        cfg.require_bundle()


def test_name_override_resolves_directly(isolated_env):
    env = isolated_env
    bundle = env["tmp"] / "named"
    bundle.mkdir()
    gdir = env["xdg"] / "okf-wiki"
    gdir.mkdir(parents=True, exist_ok=True)
    (gdir / "config.work").write_text(f"OKF_BUNDLE_PATH={bundle}\n", encoding="utf-8")

    cfg = resolve_config(name="work", start_dir=env["cwd"])
    assert cfg.source == "name"
    assert cfg.name == "work"
    assert cfg.bundle_path == bundle.resolve()


def test_name_override_missing_is_error_with_candidates(isolated_env):
    env = isolated_env
    gdir = env["xdg"] / "okf-wiki"
    gdir.mkdir(parents=True, exist_ok=True)
    (gdir / "config.alpha").write_text("OKF_BUNDLE_PATH=/tmp/x\n", encoding="utf-8")

    with pytest.raises(ConfigError) as excinfo:
        resolve_config(name="nope", start_dir=env["cwd"])
    assert "alpha" in str(excinfo.value)


def test_list_named_bundles(isolated_env):
    env = isolated_env
    gdir = env["xdg"] / "okf-wiki"
    gdir.mkdir(parents=True, exist_ok=True)
    (gdir / "config.a").write_text("OKF_BUNDLE_PATH=/tmp/a\n", encoding="utf-8")
    (gdir / "config.b").write_text("OKF_BUNDLE_PATH=/tmp/b\n", encoding="utf-8")
    (gdir / "config").write_text("OKF_BUNDLE_PATH=/tmp/main\n", encoding="utf-8")

    profiles = list_named_bundles()
    assert sorted(profiles) == ["a", "b"]


def test_legacy_home_config_dir_honored(isolated_env):
    env = isolated_env
    legacy = env["home"] / ".obsidian-wiki"
    legacy.mkdir()
    (legacy / "config").write_text("OKF_BUNDLE_PATH=/tmp/legacy\n", encoding="utf-8")

    assert global_config_dir() == legacy


def test_quotes_and_comments_stripped(isolated_env):
    env = isolated_env
    bundle = env["tmp"] / "q bundle"
    bundle.mkdir()
    (env["cwd"] / ".env").write_text(
        "# comment\nOKF_BUNDLE_PATH=\"{p}\"\nOKF_WIKI_REPO='{r}'\n".format(
            p=bundle, r=env["tmp"] / "repo"
        ),
        encoding="utf-8",
    )

    cfg = resolve_config(start_dir=env["cwd"])
    assert cfg.bundle_path == bundle.resolve()
    assert cfg.repo_path == (env["tmp"] / "repo").resolve()


def test_expanduser_and_expandvars(isolated_env, monkeypatch):
    env = isolated_env
    monkeypatch.setenv("BUNDLES", str(env["tmp"] / "vars"))
    (env["tmp"] / "vars").mkdir()
    bundle = env["tmp"] / "vars" / "deep"
    bundle.mkdir(parents=True)
    (env["cwd"] / ".env").write_text("OKF_BUNDLE_PATH=$BUNDLES/deep\n", encoding="utf-8")

    cfg = resolve_config(start_dir=env["cwd"])
    assert cfg.bundle_path == bundle.resolve()
