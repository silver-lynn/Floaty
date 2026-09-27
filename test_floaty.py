import json
import math
import unittest
from io import BytesIO
from unittest.mock import patch
from engine import build_state, request_body, parse_result, evaluate, smooth
from rubric import DIMENSIONS, WEIGHTS, EVENTS

def response(level=3):
    answers={k:{'probabilities':{str(i):int(i==level) for i in range(5)},'confidence':1} for k in DIMENSIONS}
    answers.update({k:{'noul':.9} for k in EVENTS})
    answers.update({'evidence_'+k:{'choice':'0'} for k in EVENTS}); answers['phase']={'choice':'opening'}
    return {'model':'jev-fixture-NOT-LIVE','answers':answers}

class EngineTests(unittest.TestCase):
    def test_atomic_types_and_weights(self):
        q=request_body([{'t':8,'text':'A meaningful example'}],8)['questions']
        self.assertEqual(sum(x['type']=='score' for x in q.values()),5)
        self.assertEqual(sum(x['type']=='noul' for x in q.values()),4)
        self.assertEqual(sum(x['type']=='choice' for x in q.values()),10)
        self.assertAlmostEqual(sum(WEIGHTS.values()),1)
    def test_future_cannot_leak_from_transcript_or_memory(self):
        data=request_body([{'t':5,'text':'already spoken'},{'t':20,'text':'SECRET'}],10,
                          memory=[{'t':20,'text':'SECRET','events':[]}])
        self.assertNotIn('SECRET',json.dumps(data))
    def test_weighted_score(self):
        r=response(0); r['answers']['surprise']['probabilities']={str(i):int(i==4) for i in range(5)}
        self.assertEqual(parse_result(r)['raw'],25)
    def test_fractional_distribution_and_confidence(self):
        r=response(0)
        for k in DIMENSIONS:r['answers'][k]={'probabilities':{'0':0,'1':.5,'2':0,'3':.5,'4':0},'confidence':0}
        self.assertEqual(parse_result(r)['raw'],50)
    def test_invalid_responses_do_not_score(self):
        for value in (float('nan'),True,2,-1):
            r=response(); r['answers']['question']['noul']=value
            with self.assertRaises(ValueError):parse_result(r)
        r=response(); r['answers']['clarity']['probabilities']['3']=0
        with self.assertRaises(ValueError):parse_result(r)
    def test_context_is_bounded(self):
        s=build_state([{'t':i,'text':'x'*100} for i in range(4000)],3999)
        self.assertLess(len(json.dumps(s)),15000)
        self.assertTrue(all(x['t']>3969 for x in s['current_window']))
    def test_silence_no_score(self):
        with self.assertRaises(ValueError):build_state([{'t':1,'text':'hello'}],60)
    def test_actual_request_contract_with_mock_transport(self):
        with patch('urllib.request.urlopen',return_value=BytesIO(json.dumps(response()).encode())) as mock:
            r=evaluate([{'t':8,'text':'A meaningful example'}],8,key='fixture-secret')
        self.assertEqual(r['raw'],75)
        self.assertEqual(r['evidence']['text'],'A meaningful example')
        self.assertNotIn('fixture-secret',json.dumps(r))
        self.assertEqual(mock.call_args.args[0].full_url,'https://api.typesafe.ai/v1/systemone')
    def test_smoothing_composition(self):
        self.assertAlmostEqual(smooth(0,smooth(0,100,4),4),smooth(0,100,8))

class DesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app=QApplication.instance() or QApplication([])
    def setUp(self):
        from floaty import Floaty
        self.w=Floaty(); self.w.timer.stop()
    def tearDown(self):
        for d in list(self.w.dialogs):d.close()
        self.w.tray.hide(); self.w.close(); self.w.deleteLater(); self.app.processEvents()
    def test_initial_and_no_fake_scores(self):
        self.assertEqual(self.w.value,100); self.assertEqual(self.w.scores,[])
        self.w.active=True; self.w.started=0; self.w.ticks=14; self.w.state='initial'
        self.w.tick(); self.assertEqual(self.w.state,'waiting')
    def test_late_result_ignored(self):
        self.w.active=True; self.w.generation=2
        self.w.on_result(1,{'raw':99}); self.assertEqual(self.w.scores,[])
    def test_error_never_becomes_zero(self):
        self.w.on_failure(0,'test failure')
        self.assertEqual(self.w.state,'error'); self.assertEqual(self.w.scores,[])
    def test_confirmed_transcript_corrections_keep_identity(self):
        self.w.active=True
        for text in ['hello','hello world']:
            self.w.on_speech(0,{'type':'final','id':'one','text':text})
        self.assertEqual(len(self.w.segments),1); self.assertEqual(self.w.segments[0]['text'],'hello world')
    def test_inactive_result_ignored(self):
        self.w.on_result(0,{'raw':100}); self.assertEqual(self.w.scores,[])
    def test_scores_and_event_memory_use_model_evidence(self):
        self.w.active=True
        with patch('urllib.request.urlopen',return_value=BytesIO(json.dumps(response()).encode())):
            r=evaluate([{'t':8,'text':'Specific spoken evidence'}],8,key='fixture-only')
        self.w.on_result(0,r)
        self.assertEqual(self.w.target,75)
        self.assertEqual(len(self.w.scores),1)
        self.assertEqual(len(self.w.memory),1)
        self.assertEqual(len(self.w.memory[0]['events']),4)
        self.assertEqual(self.w.state,'live')
    def test_visual_endpoints(self):
        from visual import color_at
        self.assertEqual(color_at(100).name(),'#2ba4ff')
        self.assertNotEqual(color_at(100).name(),color_at(0).name())
    def test_native_windows_render(self):
        self.w.settings(); self.w.review(); self.app.processEvents()
        self.assertEqual(len(self.w.dialogs),2)
        self.assertFalse(self.w.grab().isNull())
    def test_partial_caption_does_not_enter_scoring(self):
        self.w.active=True
        self.w.on_speech(0,{'type':'partial','text':'实时字幕草稿'})
        self.assertEqual(self.w.subtitles.text,'实时字幕草稿')
        self.assertEqual(self.w.segments,[])
        self.w.on_speech(0,{'type':'final','id':'a','text':'实时字幕已确认'})
        self.assertEqual(self.w.subtitles.text,'实时字幕已确认')
        self.assertEqual(len(self.w.segments),1)
    def test_subtitle_controls_and_transparency(self):
        from PySide6.QtCore import Qt
        c=self.w.subtitles
        self.assertTrue(c.testAttribute(Qt.WA_TranslucentBackground))
        self.assertEqual(c.font_size,48)
        c.set_caption('测试字幕'*100)
        self.assertLessEqual(len(c.lines()),2)
        c.set_enabled(False); self.assertFalse(c.isVisible())
        c.set_enabled(True); self.assertTrue(c.isVisible())
        c.clear(); self.assertFalse(c.isVisible())
    def test_old_generation_cannot_change_caption(self):
        self.w.active=True; self.w.generation=2
        self.w.on_speech(1,{'type':'partial','text':'旧文字'})
        self.assertEqual(self.w.subtitles.text,'')
    def test_subtitle_switches_stay_in_sync(self):
        self.w.settings(); self.w.subtitles.set_caption('开关测试')
        self.w.caption_checkbox.setChecked(False)
        self.assertFalse(self.w.subtitles.isVisible())
        self.assertFalse(self.w.caption_action.isChecked())
        self.w.toggle_subtitles()
        self.assertTrue(self.w.caption_checkbox.isChecked())
        self.assertTrue(self.w.subtitles.isVisible())
    def test_key_fields_keep_password_values_after_apply(self):
        from PySide6.QtWidgets import QPushButton,QLineEdit
        self.w.key='fake-jev-for-test'; self.w.speech_key='fake-asr-for-test'
        self.w.settings()
        button=next(b for b in self.w.settings_window.findChildren(QPushButton) if b.text()=='应用并验证密钥')
        with patch('floaty.save_keys') as save,patch.object(self.w,'verify_credentials'):
            button.click()
        save.assert_called_once_with('fake-jev-for-test','fake-asr-for-test')
        self.assertEqual(self.w.key_fields['jev'].text(),'fake-jev-for-test')
        self.assertEqual(self.w.key_fields['asr'].echoMode(),QLineEdit.Password)
        self.w.on_credential('jev','fake-jev-for-test','valid','验证通过 · Jev 可用')
        self.assertIn('验证通过',self.w.key_labels['jev'].text())
        self.w.key_fields['jev'].setText('new-key-not-tested')
        self.assertIn('待验证',self.w.key_labels['jev'].text())
    def test_old_key_result_cannot_override_new_validation(self):
        self.w.key='new-key'
        self.w.on_credential('jev','new-key','valid','可用')
        self.w.on_credential('jev','old-key','failed','失败')
        self.assertEqual(self.w.key_status.get('jev','new-key')[0],'valid')

class StorageTests(unittest.TestCase):
    def test_windows_encrypted_roundtrip(self):
        import tempfile
        from pathlib import Path
        import preferences
        with tempfile.TemporaryDirectory() as folder,patch.object(preferences,'STORE',Path(folder)/'keys.dpapi'):
            preferences.save_keys('fake-secret-one','fake-secret-two')
            self.assertNotIn(b'fake-secret',preferences.STORE.read_bytes())
            self.assertEqual(preferences.load_keys(),{'jev':'fake-secret-one','asr':'fake-secret-two'})

if __name__=='__main__':unittest.main(verbosity=2)
