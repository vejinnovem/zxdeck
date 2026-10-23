"""Safe Git-based software update helpers for a ZX Deck checkout."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess


SYSTEMCTL_PATH = "/usr/bin/systemctl"
SERVICE_NAME = "zxdeck.service"


@dataclass(frozen=True, slots=True)
class UpdateResult:
    """Result shown by the touchscreen updater."""

    state: str
    local_commit: str = "--------"
    remote_commit: str = "--------"
    message: str = ""
    detail: str = ""

    @property
    def can_install(self) -> bool:
        return self.state == "available"

    @property
    def updated(self) -> bool:
        return self.state == "updated"


class GitUpdateError(RuntimeError):
    pass


def _short(commit: str | None) -> str:
    return commit[:8] if commit else "--------"


def _git(
    root: Path,
    *args: str,
    timeout: float = 60.0,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            ("git", "-C", str(root), *args),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise GitUpdateError(str(exc)) from exc
    if check and result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise GitUpdateError(detail or f"git {' '.join(args)} failed")
    return result


def _checkout_info(root: Path) -> tuple[str, str]:
    root = root.expanduser().resolve()
    top = _git(root, "rev-parse", "--show-toplevel").stdout.strip()
    if not top or Path(top).resolve() != root:
        raise GitUpdateError("ZX Deck checkout root could not be verified")
    branch = _git(root, "symbolic-ref", "--quiet", "--short", "HEAD", check=False)
    if branch.returncode != 0:
        raise GitUpdateError("detached Git HEAD is not supported")
    return branch.stdout.strip(), _git(root, "rev-parse", "HEAD").stdout.strip()


def _working_tree_clean(root: Path) -> bool:
    status = _git(
        root,
        "status",
        "--porcelain=v1",
        "--untracked-files=normal",
    ).stdout
    return not status.strip()


def check_for_update(root: str | Path, *, timeout: float = 60.0) -> UpdateResult:
    """Fetch origin/main and report whether a safe fast-forward is available."""

    checkout = Path(root).expanduser().resolve()
    local_full = ""
    try:
        branch, local_full = _checkout_info(checkout)
        if branch != "main":
            return UpdateResult(
                "unsupported",
                _short(local_full),
                message="SWITCH TO MAIN BRANCH",
                detail=f"current branch: {branch}",
            )

        fetch = _git(
            checkout,
            "fetch",
            "--quiet",
            "origin",
            "main",
            timeout=timeout,
            check=False,
        )
        if fetch.returncode != 0:
            detail = (fetch.stderr or fetch.stdout).strip()
            return UpdateResult(
                "error",
                _short(local_full),
                message="UPDATE CHECK FAILED",
                detail=detail or "git fetch failed",
            )

        remote_full = _git(checkout, "rev-parse", "origin/main").stdout.strip()

        if not _working_tree_clean(checkout):
            return UpdateResult(
                "dirty",
                _short(local_full),
                _short(remote_full),
                "LOCAL CHANGES - BLOCKED",
                "commit, stash or remove local changes before updating",
            )

        if local_full == remote_full:
            return UpdateResult(
                "current",
                _short(local_full),
                _short(remote_full),
                "UP TO DATE",
            )

        ancestor = _git(
            checkout,
            "merge-base",
            "--is-ancestor",
            local_full,
            remote_full,
            check=False,
        )
        if ancestor.returncode != 0:
            return UpdateResult(
                "diverged",
                _short(local_full),
                _short(remote_full),
                "HISTORY DIVERGED - BLOCKED",
                "local HEAD is not an ancestor of origin/main",
            )

        return UpdateResult(
            "available",
            _short(local_full),
            _short(remote_full),
            "UPDATE AVAILABLE",
        )
    except GitUpdateError as exc:
        return UpdateResult(
            "error",
            _short(local_full),
            message="UPDATE CHECK FAILED",
            detail=str(exc),
        )


def apply_update(root: str | Path, *, timeout: float = 60.0) -> UpdateResult:
    """Apply only a clean fast-forward from origin/main."""

    checkout = Path(root).expanduser().resolve()
    status = check_for_update(checkout, timeout=timeout)
    if not status.can_install:
        return status

    merge = _git(
        checkout,
        "merge",
        "--ff-only",
        "--quiet",
        "origin/main",
        timeout=timeout,
        check=False,
    )
    if merge.returncode != 0:
        detail = (merge.stderr or merge.stdout).strip()
        return UpdateResult(
            "error",
            status.local_commit,
            status.remote_commit,
            "UPDATE FAILED",
            detail or "git merge --ff-only failed",
        )

    try:
        new_head = _git(checkout, "rev-parse", "HEAD").stdout.strip()
    except GitUpdateError as exc:
        return UpdateResult(
            "error",
            status.local_commit,
            status.remote_commit,
            "UPDATE FAILED",
            str(exc),
        )

    return UpdateResult(
        "updated",
        _short(new_head),
        _short(new_head),
        "UPDATE INSTALLED",
    )


def render_update_sudoers(
    user: str,
    *,
    systemctl_path: str = SYSTEMCTL_PATH,
) -> str:
    """Return the one-command sudo rule needed for a self-restart."""

    if (
        not user
        or any(character.isspace() for character in user)
        or any(character in user for character in "\n\r#,=:")
    ):
        raise ValueError("unsafe service user for sudoers rule")
    return (
        f"{user} ALL=(root) NOPASSWD: "
        f"{systemctl_path} --no-block restart {SERVICE_NAME}\n"
    )


def restart_zxdeck_service(
    *,
    timeout: float = 10.0,
) -> tuple[bool, str]:
    """Request a restart through the narrowly scoped sudoers rule."""

    try:
        result = subprocess.run(
            (
                "sudo",
                "-n",
                SYSTEMCTL_PATH,
                "--no-block",
                "restart",
                SERVICE_NAME,
            ),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    if result.returncode == 0:
        return True, ""
    detail = (result.stderr or result.stdout).strip()
    return False, detail or f"systemctl exited with {result.returncode}"
