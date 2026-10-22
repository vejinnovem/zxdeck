from __future__ import annotations

import unittest

from zxdeck.frontends.touch.keypad import InputMode, MultiTapEditor


class MultiTapEditorTests(unittest.TestCase):
    def test_repeated_key_cycles_like_classic_phone(self) -> None:
        editor = MultiTapEditor()
        self.assertEqual(editor.press("2", now=0.0), "A")
        self.assertEqual(editor.press("2", now=0.2), "B")
        self.assertEqual(editor.press("2", now=0.4), "C")
        self.assertEqual(editor.press("2", now=0.6), "2")
        self.assertEqual(editor.press("2", now=0.8), "A")

    def test_timeout_starts_a_new_character(self) -> None:
        editor = MultiTapEditor(timeout_seconds=0.8)
        editor.press("6", now=0.0)
        self.assertEqual(editor.press("6", now=1.0), "MM")

    def test_different_key_commits_previous_character(self) -> None:
        editor = MultiTapEditor()
        editor.press("6", now=0.0)  # M
        editor.press("2", now=0.2)  # A
        editor.press("6", now=0.4)  # M
        self.assertEqual(editor.text, "MAM")

    def test_star_is_backspace(self) -> None:
        editor = MultiTapEditor(text="ELITE")
        self.assertEqual(editor.press("*", now=0.0), "ELIT")

    def test_hash_cycles_input_mode(self) -> None:
        editor = MultiTapEditor()
        self.assertEqual(editor.mode, InputMode.UPPER)
        editor.press("#", now=0.0)
        self.assertEqual(editor.mode, InputMode.NUMERIC)
        editor.press("#", now=0.1)
        self.assertEqual(editor.mode, InputMode.LOWER)
        editor.press("#", now=0.2)
        self.assertEqual(editor.mode, InputMode.UPPER)

    def test_lowercase_and_numeric_modes(self) -> None:
        editor = MultiTapEditor(mode=InputMode.LOWER)
        editor.press("2", now=0.0)
        editor.press("2", now=0.1)
        self.assertEqual(editor.text, "b")

        editor.press("#", now=1.0)  # UPPER
        editor.press("#", now=1.1)  # NUMERIC
        editor.press("7", now=1.2)
        self.assertEqual(editor.text, "b7")

    def test_zero_starts_with_space(self) -> None:
        editor = MultiTapEditor(text="JET")
        self.assertEqual(editor.press("0", now=0.0), "JET ")

    def test_max_length_is_respected(self) -> None:
        editor = MultiTapEditor(text="ABCD", max_length=4)
        self.assertEqual(editor.press("2", now=0.0), "ABCD")


if __name__ == "__main__":
    unittest.main()
