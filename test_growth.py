import tempfile
import unittest
from pathlib import Path
from growth import Growth,level
from sketch import blink_at

class GrowthTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.g=Growth(Path(self.tmp.name)/'growth.json')
        self.segments=[{'t':10,'text':'练习表达'*12},{'t':40,'text':'明确结论'*12}]
    def tearDown(self):self.tmp.cleanup()
    def test_short_practice_no_reward(self):
        p,_=self.g.reward('short',59,self.segments); self.assertEqual(p['sessions'],0)
        p,_=self.g.reward('silent',300,[]); self.assertEqual(p['coins'],0)
    def test_reward_deduplication_and_level(self):
        for n in range(3):self.g.reward(str(n),65,self.segments)
        p=self.g.read(); self.assertEqual(p['coins'],35); self.assertEqual(level(p),2)
        self.g.reward('2',65,self.segments); self.assertEqual(self.g.read(),p)
    def test_redemption_persistence_and_free_reequip(self):
        self.g.reward('one',65,self.segments)
        p=self.g.redeem('sprout'); self.assertEqual(p['coins'],0)
        self.g.redeem('none'); p=self.g.redeem('sprout'); self.assertEqual(p['coins'],0)
        self.assertEqual(Growth(self.g.path).read()['equipped'],'sprout')
    def test_locked_or_unaffordable_no_write(self):
        for hat in ['sprout','crown']:
            with self.assertRaises(ValueError):self.g.redeem(hat)
        self.assertFalse(self.g.path.exists())
    def test_corrupt_file_not_reset(self):
        self.g.path.write_text('broken')
        with self.assertRaises(ValueError):self.g.reward('one',90,self.segments)
        self.assertEqual(self.g.path.read_text(),'broken')
    def test_blink_short_and_reopens(self):
        self.assertEqual(blink_at(1),1); self.assertLess(blink_at(2.7),.1); self.assertEqual(blink_at(3),1)
    def test_end_practice_awards_once_in_app(self):
        from PySide6.QtWidgets import QApplication
        from floaty import Floaty
        app=QApplication.instance() or QApplication([])
        w=Floaty(); w.timer.stop(); w.growth=self.g
        w.session_id='integration'; w.practice_duration=65; w.segments=self.segments
        w.settle_practice(); w.settle_practice()
        self.assertEqual(self.g.read()['sessions'],1)
        self.assertIsNone(w.session_id); w.tray.hide(); w.close(); w.deleteLater(); app.processEvents()
    def test_wardrobe_purchase_and_equipped_renderer(self):
        from PySide6.QtWidgets import QApplication
        from floaty import Floaty
        from wardrobe import Wardrobe
        app=QApplication.instance() or QApplication([])
        self.g.reward('one',65,self.segments)
        w=Floaty(); w.timer.stop(); w.growth=self.g; view=Wardrobe(w)
        view.choose('cap')
        self.assertEqual(w.profile['equipped'],'cap'); self.assertEqual(view.buttons['cap'].text(),'已佩戴')
        self.assertFalse(view.buttons['crown'].isEnabled())
        view.close(); w.tray.hide(); w.close(); w.deleteLater(); app.processEvents()

if __name__=='__main__':unittest.main()
