import unittest
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QUrl
from review import ReviewPane,matched_indices
from rubric import DIMENSIONS
from engine import request_body

def fixtures():
    segments=[{'id':'a','t':8,'text':'过去，整理客户访谈需要反复翻找记录。'},
              {'id':'b','t':24,'text':'我们的 AI 很先进，有很多很强大的功能。'},
              {'id':'c','t':44,'text':'每条结论都附上来源。先查证据，再用结论。'},
              {'id':'d','t':70,'text':'这是最后一句，尚未评分。'}]
    values=[[70,45,35,65,80],[40,20,30,35,65],[80,70,92,86,90]]
    scores=[]
    for i,t in enumerate([12,30,50]):
        window=[dict(s) for s in segments if t-30<s['t']<=t]
        scores.append({'t':t,'raw':sum(values[i])/5,'display':sum(values[i])/5,
                       'dimensions':{k:{'label':DIMENSIONS[k][0],'score':v} for k,v in zip(DIMENSIONS,values[i])},
                       'window':window,'model':'VISUAL-FIXTURE-NOT-JEV','improvement_targets':{}})
    return scores,segments

class ReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_ids_survive_corrected_text(self):
        scores,segments=fixtures(); segments[0]['text']='修正后的文字'
        self.assertEqual(matched_indices(scores[0],segments),[0])
        self.assertIn('id',request_body(segments,12)['state']['current_window'][0])
    def test_legacy_timestamp_match_not_nearest(self):
        self.assertEqual(matched_indices({'window':[{'t':8,'text':'old'}]},[{'t':9,'text':'nearby'}]),[])
    def test_bidirectional_link_and_unscored_gap(self):
        scores,segments=fixtures(); pane=ReviewPane(scores,segments)
        pane.from_transcript(QUrl('segment:2'))
        self.assertEqual(pane.selected,2)
        self.assertEqual(pane.radar.values,[80,70,92,86,90])
        pane.from_transcript(QUrl('segment:3'))
        self.assertIsNone(pane.radar.values)
        self.assertEqual(pane.selector.currentIndex(),-1)
        self.assertIn('没有对应评分',pane.window_label.text()); pane.deleteLater()
    def test_original_snapshot_retained(self):
        scores,segments=fixtures(); segments[0]['text']='已修改'
        pane=ReviewPane(scores,segments)
        self.assertIn('后来有修正',pane.advice.toPlainText())
        self.assertIn('反复翻找',pane.advice.toPlainText())
        self.assertIn('已修改',pane.transcript.toPlainText()); pane.deleteLater()
    def test_no_scores_no_suggestions(self):
        _,segments=fixtures(); pane=ReviewPane([],segments)
        self.assertIsNone(pane.radar.values); self.assertIsNone(pane.radar.average)
        self.assertNotIn('优先练习',pane.advice.toPlainText()); pane.deleteLater()
    def test_improvement_target_uses_original_passage(self):
        from io import BytesIO
        from unittest.mock import patch
        import json
        from engine import evaluate
        from test_floaty import response
        mock=response(); mock['answers']['improve_memory']={'choice':'0'}
        with patch('urllib.request.urlopen',return_value=BytesIO(json.dumps(mock).encode())):
            result=evaluate([{'id':'test-id','t':8,'text':'Exactly this original sentence'}],8,key='test-only')
        self.assertEqual(result['improvement_targets']['memory']['id'],'test-id')
        self.assertEqual(result['improvement_targets']['memory']['text'],'Exactly this original sentence')

if __name__=='__main__':unittest.main()
