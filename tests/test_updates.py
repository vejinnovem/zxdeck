from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from zxdeck.system import apply_update, check_for_update, render_update_sudoers


def git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(("git", "-C", str(cwd), *args), check=True, capture_output=True, text=True)


@unittest.skipIf(shutil.which("git") is None, "git is not installed")
class GitUpdaterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.remote = root / "remote.git"
        self.seed = root / "seed"
        self.checkout = root / "checkout"
        subprocess.run(("git", "init", "--bare", str(self.remote)), check=True, capture_output=True, text=True)
        subprocess.run(("git", "init", str(self.seed)), check=True, capture_output=True, text=True)
        git(self.seed, "config", "user.name", "ZX Deck Tests")
        git(self.seed, "config", "user.email", "zxdeck@example.invalid")
        (self.seed / "README.md").write_text("one\n", encoding="utf-8")
        git(self.seed, "add", "README.md"); git(self.seed, "commit", "-m", "initial"); git(self.seed, "branch", "-M", "main")
        git(self.seed, "remote", "add", "origin", str(self.remote)); git(self.seed, "push", "-u", "origin", "main")
        subprocess.run(("git", "clone", "--branch", "main", str(self.remote), str(self.checkout)), check=True, capture_output=True, text=True)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def push_update(self) -> None:
        (self.seed / "README.md").write_text("two\n", encoding="utf-8")
        git(self.seed, "add", "README.md"); git(self.seed, "commit", "-m", "update"); git(self.seed, "push", "origin", "main")

    def test_current_available_and_fast_forward_update(self) -> None:
        current = check_for_update(self.checkout)
        self.assertEqual("current", current.state)
        self.push_update()
        available = check_for_update(self.checkout)
        self.assertEqual("available", available.state); self.assertTrue(available.can_install)
        updated = apply_update(self.checkout)
        self.assertEqual("updated", updated.state)
        self.assertEqual("two\n", (self.checkout / "README.md").read_text())
        self.assertEqual(git(self.checkout, "rev-parse", "HEAD").stdout.strip(), git(self.checkout, "rev-parse", "origin/main").stdout.strip())

    def test_local_changes_block_update(self) -> None:
        self.push_update(); (self.checkout / "local.txt").write_text("do not overwrite\n")
        result = check_for_update(self.checkout)
        self.assertEqual("dirty", result.state); self.assertFalse(result.can_install); self.assertIn("BLOCKED", result.message)

    def test_sudoers_rule_allows_only_service_restart(self) -> None:
        rule = render_update_sudoers("deck")
        self.assertEqual("deck ALL=(root) NOPASSWD: /usr/bin/systemctl --no-block restart zxdeck.service\n", rule)
        self.assertNotIn("poweroff", rule)


if __name__ == "__main__":
    unittest.main()
