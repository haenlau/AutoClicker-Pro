"""Windows registration, dispatch, conflict reporting, and cleanup regression tests."""
import ctypes
import importlib.util
import os
from pathlib import Path
import unittest

os.environ['QT_QPA_PLATFORM'] = 'offscreen'
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('ck', ROOT / 'clicker.py')
ck = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ck)
qapp = ck.QApplication.instance() or ck.QApplication([])

class HotkeyTests(unittest.TestCase):
    def setUp(self):
        self.received = []
        self.hotkeys = ck.WindowsHotkeys([
            (0xAB16, 0x87, 'F24', lambda: self.received.append('F24')),
        ])
        self.assertEqual(self.hotkeys.failed, [])

    def tearDown(self):
        self.hotkeys.stop()

    def dispatch(self, message, key=0xAB16, event=b'windows_dispatcher_MSG'):
        msg = ck.wintypes.MSG()
        msg.message, msg.wParam = message, key
        return self.hotkeys.nativeEventFilter(event, ctypes.addressof(msg))

    def test_windows_hotkey_message_dispatches(self):
        self.assertEqual(self.dispatch(0x0312), (True, 0))
        self.assertEqual(self.received, ['F24'])

    def test_unrelated_native_messages_are_ignored(self):
        self.assertEqual(self.dispatch(0x0100), (False, 0))
        self.assertEqual(self.dispatch(0x0312, key=0xAB17), (False, 0))
        self.assertEqual(self.dispatch(0x0312, event=b'other'), (False, 0))
        self.assertEqual(self.received, [])

    def test_registration_conflict_is_reported(self):
        other = ck.WindowsHotkeys([(0xAB17, 0x87, 'F24', lambda: None)])
        try:
            self.assertEqual(other.failed, ['F24'])
        finally:
            other.stop()

    def test_stop_releases_shortcut_and_is_repeatable(self):
        self.hotkeys.stop()
        self.hotkeys.stop()
        replacement = ck.WindowsHotkeys([(0xAB17, 0x87, 'F24', lambda: None)])
        try:
            self.assertEqual(replacement.failed, [])
        finally:
            replacement.stop()

if __name__ == '__main__':
    unittest.main()
