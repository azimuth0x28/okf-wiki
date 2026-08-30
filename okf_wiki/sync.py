"""sync / sync-setup: commit bundle changes as exactly one conventional commit."""

import os
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple


class SyncError(RuntimeError):
    pass


def _git(args: List[str], cwd: Path, env: Optional[dict] = None) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        env=env,
    )


def sync(bundle: Path, message: Optional[str] = None, push: bool = False) -> Tuple[bool, str]:
    """Stage bundle changes and create exactly one commit; no-op when clean.

    Returns ``(committed, message)``. With ``push=True`` a single push to the
    first configured remote follows the commit (when a remote exists).
    """
    bundle = Path(bundle)
    toplevel = _git(["rev-parse", "--show-toplevel"], bundle)
    if toplevel.returncode != 0:
        raise SyncError("not a git repository: run inside a bundle under git")

    status = _git(["status", "--porcelain", "--", "."], bundle)
    if status.returncode != 0:
        raise SyncError("git status failed inside the bundle")
    changed = [line for line in status.stdout.splitlines() if line.strip()]
    if not changed:
        return False, "Nothing to sync — working tree clean."

    add = _git(["add", "-A", "."], bundle)
    if add.returncode != 0:
        raise SyncError(add.stderr.strip() or "git add failed")

    staged = _git(["diff", "--cached", "--numstat"], bundle)
    count = len([line for line in staged.stdout.splitlines() if line.strip()])
    if count == 0:
        return False, "Nothing staged — bundle unchanged."

    commit_message = message or f"wiki: sync {count} file(s)"
    commit = _git(
        ["commit", "-m", commit_message],
        bundle,
        env={**os.environ, "OKF_WIKI_SYNCING": "1"},
    )
    if commit.returncode != 0:
        raise SyncError(commit.stderr.strip() or "git commit failed")

    note = ""
    if push:
        remotes = _git(["remote"], bundle)
        if remotes.stdout.strip():
            push_result = _git(["push"], bundle)
            note = " (pushed)" if push_result.returncode == 0 else " (push failed)"
        else:
            note = " (no remote configured — push skipped)"
    return True, f"Committed {count} file(s): {commit_message}{note}"


def sync_setup(bundle: Path) -> Path:
    """Install a post-commit hook that runs ``okf-wiki sync`` (recursion-guarded)."""
    bundle = Path(bundle)
    proc = _git(["rev-parse", "--show-toplevel"], bundle)
    if proc.returncode != 0:
        raise SyncError("not a git repository")
    hooks_dir = Path(proc.stdout.strip()) / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_path = hooks_dir / "post-commit"
    if hook_path.exists():
        raise SyncError(f"post-commit hook already exists: {hook_path}")
    hook_path.write_text(
        "#!/bin/sh\n"
        "# okf-wiki: commit pending bundle changes right after a commit lands.\n"
        'if [ "$OKF_WIKI_SYNCING" = "1" ]; then\n'
        "  exit 0\n"
        "fi\n"
        "command -v okf-wiki >/dev/null 2>&1 || exit 0\n"
        "okf-wiki sync || exit 0\n",
        encoding="utf-8",
    )
    hook_path.chmod(0o755)
    return hook_path
