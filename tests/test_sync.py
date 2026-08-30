"""Tests for okf_wiki.sync — exactly one conventional commit per sync."""

import subprocess
from pathlib import Path

import pytest

from okf_wiki.capture import capture
from okf_wiki.sync import SyncError, sync, sync_setup


def _init_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "test@example.com"],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "Test"],
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "init", "--allow-empty"],
        check=True,
        capture_output=True,
    )
    return repo


def _commit_count(repo):
    out = subprocess.run(
        ["git", "-C", str(repo), "log", "--oneline"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return len([line for line in out.splitlines() if line.strip()])


class TestSync:
    def test_sync_commits_exactly_once(self, tmp_path):
        repo = _init_repo(tmp_path)
        bundle = repo / "bundle"
        bundle.mkdir()
        (bundle / "index.md").write_text("---\nokf_version: \"0.2\"\n---\n\n# B\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True, capture_output=True)
        subprocess.run(
            ["git", "-C", str(repo), "commit", "-q", "-m", "init bundle"],
            check=True,
            capture_output=True,
        )
        capture(bundle, title="first note")

        committed, message = sync(bundle)
        assert committed is True
        assert message.startswith("Committed 1 file(s): wiki: sync 1 file(s)")
        out = subprocess.run(
            ["git", "-C", str(repo), "log", "--oneline"], capture_output=True, text=True
        ).stdout
        assert out.splitlines()[0].endswith("wiki: sync 1 file(s)")

        committed_again, message_again = sync(bundle)
        assert committed_again is False
        assert "Nothing to sync" in message_again
        count_after = subprocess.run(
            ["git", "-C", str(repo), "log", "--oneline"], capture_output=True, text=True
        ).stdout.count("\n")
        assert count_after == 3  # empty init + init bundle + one sync commit

    def test_custom_message(self, tmp_path):
        repo = _init_repo(tmp_path)
        bundle = repo / "bundle"
        bundle.mkdir()
        capture(bundle, title="another")
        committed, message = sync(bundle, message="wiki: capture actor-reentrancy")
        assert committed is True
        assert "wiki: capture actor-reentrancy" in message

    def test_push_without_remote_notes_skip(self, tmp_path):
        repo = _init_repo(tmp_path)
        bundle = repo / "bundle"
        bundle.mkdir()
        capture(bundle, title="no remote")
        committed, message = sync(bundle, push=True)
        assert committed is True
        assert "no remote" in message


class TestSyncSetup:
    def test_installs_hook_once(self, tmp_path):
        repo = _init_repo(tmp_path)
        bundle = repo / "bundle"
        bundle.mkdir()
        hook = sync_setup(bundle)
        assert hook.name == "post-commit"
        assert hook.exists()
        with pytest.raises(SyncError):
            sync_setup(bundle)
