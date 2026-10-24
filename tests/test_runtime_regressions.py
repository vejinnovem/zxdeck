from __future__ import annotations

import unittest

from zxdeck.frontends.touch.device_controller import DeviceTouchUIController
from zxdeck.core.state import TransportState


class RuntimeRegressionTests(unittest.TestCase):
    def test_device_controller_can_dispatch_base_home_action(self) -> None:
        controller = DeviceTouchUIController(("GAME.TZX",))
        controller.handle_action("files")
        self.assertNotEqual("home", controller.screen)

    def test_rec_does_not_claim_recording_before_capture_exists(self) -> None:
        controller = DeviceTouchUIController(("GAME.TZX",))
        controller.state = controller.state.next_revision(tape_name="GAME.TZX")

        controller.handle_action("record")

        self.assertEqual(TransportState.STOPPED, controller.state.transport)
        self.assertEqual("REC NOT IMPLEMENTED", controller.state.error)


if __name__ == "__main__":
    unittest.main()
