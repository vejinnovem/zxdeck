from __future__ import annotations

import unittest

try:
    from PIL import ImageChops
except ImportError:  # Pillow is optional outside the rendered touch frontend.
    ImageChops = None

from zxdeck.frontends.touch import MultiTapEditor, TouchRenderer


@unittest.skipIf(ImageChops is None, "Pillow is not installed")
class TouchRendererTests(unittest.TestCase):
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
