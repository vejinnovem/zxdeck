from __future__ import annotations

import unittest

from zxdeck.core import Backend, DeckState, UnsupportedCommand
from zxdeck.core.commands import ClearError


class BackendTests(unittest.TestCase):
    def test_subscription_receives_initial_and_updated_state(self) -> None:
        backend = Backend(DeckState(error="test"))
        seen: list[DeckState] = []
        unsubscribe = backend.subscribe(seen.append)

        state = backend.dispatch(ClearError())
        unsubscribe()

        self.assertEqual(["test", None], [item.error for item in seen])
        self.assertEqual(1, state.revision)

    def test_unknown_command_is_rejected(self) -> None:
        class Unknown:
            pass

        with self.assertRaises(UnsupportedCommand):
            Backend().dispatch(Unknown())


if __name__ == "__main__":
    unittest.main()

