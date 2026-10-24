from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from zxdeck.core.state import TransportState
from zxdeck.frontends.touch import Screen, TouchUIController
from zxdeck.tape import inspect_tape_segments, selected_event_index


class SegmentNavigationUITests(unittest.TestCase):
    def test_forward_rewind_and_play_select_tape_blocks(self) -> None:
        header = (
            b"\x00\x00"
            + b"RING      "
            + (2).to_bytes(2, "little")
            + (10).to_bytes(2, "little")
            + (0).to_bytes(2, "little")
            + b"\x00"
        )
        data = b"\xff\x00"
        image = (
            len(header).to_bytes(2, "little")
            + header
            + len(data).to_bytes(2, "little")
            + data
        )

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ring.tap"
            path.write_bytes(image)
            segments = inspect_tape_segments(path)
            controller = TouchUIController(
                (path.name,),
                file_paths=(path,),
            )

            controller.handle_action("files")
            controller.handle_action("open:0")
            self.assertEqual(Screen.HOME, controller.screen)
            self.assertEqual(1, controller.state.segment_index)
            self.assertEqual(2, controller.state.segment_count)
            self.assertEqual("PROGRAM RING", controller.state.segment_label)

            controller.handle_action("forward")
            self.assertEqual(2, controller.state.segment_index)
            self.assertEqual("DATA RING", controller.state.segment_label)
            self.assertAlmostEqual(
                segments[1].start_seconds,
                controller.state.position_seconds,
            )

            controller.handle_action("play")
            self.assertEqual(TransportState.PLAYING, controller.state.transport)
            self.assertEqual(
                segments[1].event_index,
                selected_event_index(path),
            )

            controller.handle_action("rewind")
            self.assertEqual(TransportState.STOPPED, controller.state.transport)
            self.assertEqual(1, controller.state.segment_index)
            self.assertEqual(
                segments[0].event_index,
                selected_event_index(path),
            )


if __name__ == "__main__":
    unittest.main()
