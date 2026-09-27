import unittest
from unittest.mock import Mock
from PySide6.QtCore import Qt, QPoint, QPointF
from floaty import Floaty
from subtitles import Subtitles


class DragTests(unittest.TestCase):
    def event(self, buttons):
        return Mock(buttons=Mock(return_value=buttons),
                    globalPosition=Mock(return_value=QPointF(300, 400)))

    def test_missing_release_does_not_leave_balloon_following_cursor(self):
        state = Mock(drag=QPoint(10, 20), locked=False)
        Floaty.mouseMoveEvent(state, self.event(Qt.NoButton))
        self.assertIsNone(state.drag)
        state.move.assert_not_called()

    def test_left_button_drag_preserves_cursor_offset(self):
        state = Mock(drag=QPoint(10, 20), locked=False)
        Floaty.mouseMoveEvent(state, self.event(Qt.LeftButton))
        state.move.assert_called_once_with(QPoint(290, 380))

    def test_locked_balloon_cannot_continue_old_drag(self):
        state = Mock(drag=QPoint(10, 20), locked=True)
        Floaty.mouseMoveEvent(state, self.event(Qt.LeftButton))
        state.move.assert_not_called()
        self.assertIsNone(state.drag)

    def test_double_click_clears_drag_before_opening_settings(self):
        state = Mock(drag=QPoint(10, 20))
        state.settings.side_effect = lambda: self.assertIsNone(state.drag)
        Floaty.mouseDoubleClickEvent(state, Mock())
        state.settings.assert_called_once()

    def test_subtitles_recover_from_missing_release(self):
        state = Mock(drag=QPoint(10, 20))
        Subtitles.mouseMoveEvent(state, self.event(Qt.NoButton))
        state.move.assert_not_called()
        self.assertIsNone(state.drag)


if __name__ == '__main__':
    unittest.main()
