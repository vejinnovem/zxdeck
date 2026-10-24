from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from zxdeck.config import StorageConfig
from zxdeck.storage import (
    DirectoryBrowser,
    DirectoryUnavailable,
    StorageUnavailable,
    TapeLibrary,
    load_selected_path,
    save_selected_path,
    write_tape_index,
)


class TapeLibraryTests(unittest.TestCase):
    def test_generated_index_avoids_recursive_filesystem_scan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / "collection"
            nested.mkdir()
            tape = nested / "Alpha.tap"
            tape.touch()
            write_tape_index(root, (Path("collection/Alpha.tap"),))

            with patch(
                "zxdeck.storage.library.os.walk",
                side_effect=AssertionError("scan used"),
            ):
                entries = TapeLibrary(StorageConfig(path=root)).refresh()

            self.assertEqual((tape,), tuple(entry.path for entry in entries))

    def test_catalog_keeps_indexed_paths_lazy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / "collection"
            nested.mkdir()
            tape = nested / "Alpha.tap"
            tape.touch()
            write_tape_index(root, (Path("collection/Alpha.tap"),))

            catalog = TapeLibrary(StorageConfig(path=root)).catalog()

            self.assertEqual(("Alpha.tap",), tuple(catalog.names))
            self.assertEqual(tape, catalog.paths[0])

    def test_invalid_index_falls_back_to_scan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".zxdeck-index.json").write_text(
                '{"version":2,"entries":[["outside.tap","../outside.tap"]]}',
                encoding="utf-8",
            )
            tape = root / "Safe.tap"
            tape.touch()

            entries = TapeLibrary(StorageConfig(path=root)).refresh()

            self.assertEqual((tape,), tuple(entry.path for entry in entries))

    def test_force_refresh_ignores_valid_but_stale_index(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stale = root / "Old.tap"
            fresh = root / "New.tap"
            fresh.touch()
            write_tape_index(root, (Path(stale.name),))

            catalog = TapeLibrary(StorageConfig(path=root)).catalog(
                force_refresh=True
            )

            self.assertEqual(("New.tap",), tuple(catalog.names))
            self.assertEqual(fresh, catalog.paths[0])

            # The rebuilt index must also be the fast path on the next start.
            with patch(
                "zxdeck.storage.library.os.walk",
                side_effect=AssertionError("scan used"),
            ):
                cached = TapeLibrary(StorageConfig(path=root)).catalog()
            self.assertEqual(("New.tap",), tuple(cached.names))

    def test_scan_reports_progress_and_persists_index(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Alpha.tap").touch()
            progress: list[tuple[str, int]] = []

            entries = TapeLibrary(StorageConfig(path=root)).refresh(
                lambda status, count: progress.append((status, count))
            )

            self.assertEqual(("Alpha.tap",), tuple(entry.name for entry in entries))
            self.assertEqual(("LOADING INDEX", 0), progress[0])
            self.assertEqual(("INDEX READY", 1), progress[-1])
            self.assertTrue((root / ".zxdeck-index.json").is_file())

    def test_scan_search_and_virtual_initial_groups(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Zorro.tzx").touch()
            (root / "alpha.TAP").touch()
            (root / "snapshot.z80").touch()
            (root / "ignored.txt").touch()
            nested = root / "collection"
            nested.mkdir()
            (nested / "1942.pzx").touch()

            library = TapeLibrary(StorageConfig(path=root))
            entries = library.refresh()

            self.assertEqual(
                ("1942.pzx", "alpha.TAP", "Zorro.tzx"),
                tuple(entry.name for entry in entries),
            )
            self.assertEqual(("alpha.TAP",), tuple(e.name for e in library.search("LPH")))
            self.assertEqual(("#", "A", "Z"), tuple(library.by_initial()))

    def test_required_mount_is_rejected_before_scanning(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            library = TapeLibrary(
                StorageConfig(path=Path(directory), require_mount=True),
                mount_check=lambda _path: False,
            )
            with self.assertRaises(StorageUnavailable):
                library.refresh()

    def test_mount_check_uses_mount_path_not_selected_subdirectory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tapes = root / "tapes"
            tapes.mkdir()
            seen: list[Path] = []
            library = TapeLibrary(
                StorageConfig(
                    path=tapes,
                    require_mount=True,
                    mount_path=root,
                ),
                mount_check=lambda path: seen.append(path) or True,
            )
            library.refresh()
            self.assertEqual([root], seen)


class DirectoryBrowserTests(unittest.TestCase):
    def test_navigation_cannot_escape_configured_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Games").mkdir()
            (root / "games-two").mkdir()
            (root / ".hidden").mkdir()
            browser = DirectoryBrowser(root)

            self.assertEqual(("Games", "games-two"), browser.directories())
            self.assertEqual(root / "Games", browser.enter("Games"))
            self.assertEqual(root, browser.parent())
            self.assertEqual(root, browser.parent())
            with self.assertRaises(DirectoryUnavailable):
                browser.enter("..")


class StorageSelectionTests(unittest.TestCase):
    def test_selection_round_trip_and_outside_path_rejection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            selected = root / "games"
            selected.mkdir()
            state = root / "state" / "storage-path"

            save_selected_path(state, selected)
            self.assertEqual(selected, load_selected_path(state, root, root))

            state.write_text("/\n", encoding="utf-8")
            self.assertEqual(root, load_selected_path(state, root, root))


if __name__ == "__main__":
    unittest.main()
