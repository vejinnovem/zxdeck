from __future__ import annotations

import unittest

try:
    from PIL import ImageChops
except ImportError:  # Pillow is optional outside the rendered touch frontend.
    ImageChops = None

from zxdeck.frontends.touch import MultiTapEditor, TouchRenderer
from zxdeck.frontends.touch.renderer import marquee_offset


@unittest.skipIf(ImageChops is None, "Pillow is not installed")
class TouchRendererTests(unittest.TestCase):
    def test_long_tape_title_can_scroll_while_short_title_stays_centered(self) -> None:
        renderer = TouchRenderer()
        short_at_start = renderer.render_tape_title("DEMO.TAP", offset=0)
        short_scrolled = renderer.render_tape_title("DEMO.TAP", offset=100)
        long_at_start = renderer.render_tape_title("A VERY LONG TAPE FILE NAME.TZX")
        long_scrolled = renderer.render_tape_title(
            "A VERY LONG TAPE FILE NAME.TZX",
            offset=40,
        )

        self.assertIsNone(
            ImageChops.difference(short_at_start, short_scrolled).getbbox()
        )
        self.assertIsNotNone(
            ImageChops.difference(long_at_start, long_scrolled).getbbox()
        )

    def test_marquee_pauses_then_moves_to_both_ends(self) -> None:
        self.assertEqual(0, marquee_offset(1.0, 60))
        self.assertEqual(30, marquee_offset(2.5, 60))
        self.assertEqual(60, marquee_offset(3.5, 60))
        self.assertEqual(60, marquee_offset(4.0, 60))
        self.assertEqual(30, marquee_offset(5.5, 60))
    def test_cursor_is_hidden_while_multitap_character_is_pending(self) -> None:
        renderer = TouchRenderer()
        editor = MultiTapEditor(text="M")
        with_cursor = renderer.render_filename(editor, cursor_visible=True).image

        editor.press("6", now=0.0)
        pending = renderer.render_filename(editor, cursor_visible=True).image
        pending_cursor_off = renderer.render_filename(
            editor,
            cursor_visible=False,
        ).image

        self.assertIsNone(ImageChops.difference(pending, pending_cursor_off).getbbox())
        self.assertIsNotNone(ImageChops.difference(with_cursor, pending).getbbox())

    def test_committed_cursor_has_visible_and_hidden_blink_frames(self) -> None:
        renderer = TouchRenderer()
        editor = MultiTapEditor(text="TEST")

        visible = renderer.render_filename(editor, cursor_visible=True).image
        hidden = renderer.render_filename(editor, cursor_visible=False).image

        self.assertIsNotNone(ImageChops.difference(visible, hidden).getbbox())


if __name__ == "__main__":
    unittest.main()
