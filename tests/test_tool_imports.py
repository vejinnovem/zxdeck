from __future__ import annotations

import importlib
import unittest


class ToolImportTests(unittest.TestCase):
    def test_touchscreen_entrypoint_imports(self) -> None:
        module = importlib.import_module("tools.ui_touch_demo")
        self.assertTrue(callable(module.main))


if __name__ == "__main__":
    unittest.main()
