import unittest
from unittest.mock import Mock,patch
from floaty import Floaty

class RestartTests(unittest.TestCase):
    def state(self,**kwargs):
        values=dict(active=False,finishing=False,busy=False,segments=[],scores=[],exported=False)
        values.update(kwargs); return Mock(**values)
    def test_active_session_is_not_interrupted(self):
        for flag in ('active','finishing','busy'):
            state=self.state(**{flag:True})
            with patch('floaty.QMessageBox.information'):Floaty.restart(state)
            state.quit.assert_not_called()
    def test_cancelled_export_preserves_session(self):
        state=self.state(segments=[{'text':'keep'}]); Floaty.restart(state)
        state.export.assert_called_once(); state.quit.assert_not_called()
    def test_saved_or_empty_session_can_restart(self):
        for state in (self.state(),self.state(segments=[{'text':'keep'}],exported=True)):
            Floaty.restart(state); state.quit.assert_called_once_with(restarting=True)
        state=self.state(segments=[{'text':'keep'}])
        state.export.side_effect=lambda:setattr(state,'exported',True)
        Floaty.restart(state); state.quit.assert_called_once_with(restarting=True)

if __name__=='__main__':unittest.main()
