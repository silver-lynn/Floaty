"""Local practice rewards. Cosmetic only, independent of Jev scores."""
import json
from pathlib import Path

from paths import data_dir
PROFILE=data_dir()/'growth.json'
HATS={
 'none':('不戴帽子',0,1), 'sprout':('小芽帽',10,1), 'cap':('棒球帽',10,1),
 'beret':('画家贝雷帽',15,1), 'straw':('夏日草帽',20,2), 'party':('派对尖帽',20,2),
 'witch':('小巫师帽',30,3), 'santa':('冬日绒帽',30,3), 'crown':('小小皇冠',50,4)
}

def default():return {'version':1,'sessions':0,'coins':0,'owned':['none'],'equipped':'none','rewarded':[]}
def level(profile):return 1+profile['sessions']//3

class Growth:
    def __init__(self,path=None):self.path=Path(path or PROFILE)
    def read(self):
        if not self.path.exists():return default()
        data=json.loads(self.path.read_text(encoding='utf-8'))
        if data.get('version')!=1 or not isinstance(data.get('sessions'),int) or not isinstance(data.get('coins'),int) or min(data['sessions'],data['coins'])<0:
            raise ValueError('成长记录格式无效')
        if not isinstance(data.get('owned'),list) or not all(k in HATS for k in data['owned']) or data.get('equipped') not in data['owned'] or not isinstance(data.get('rewarded'),list):
            raise ValueError('装饰记录格式无效')
        return data
    def write(self,data):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        temp=self.path.with_suffix('.tmp'); temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8'); temp.replace(self.path)
    def reward(self,session_id,duration,segments):
        data=self.read()
        if session_id in data['rewarded']:return data,'本次练习已经结算。'
        text=''.join(s['text'] for s in segments).replace(' ','')
        span=max((s['t'] for s in segments),default=0)-min((s['t'] for s in segments),default=0)
        if duration<60 or len(text)<80 or span<20:return data,'本次未满有效练习条件：至少 60 秒、80 字转写，且发言跨越 20 秒。'
        before=level(data); data['sessions']+=1; earned=10+(5 if level(data)>before else 0)
        data['coins']+=earned; data['rewarded'].append(session_id); self.write(data)
        return data,f"完成第 {data['sessions']} 次练习 · +{earned} 星点"+(' · 升级啦！' if level(data)>before else '')
    def redeem(self,hat):
        if hat not in HATS:raise ValueError('装饰不存在')
        data=self.read(); name,cost,required=HATS[hat]
        if hat not in data['owned']:
            if level(data)<required:raise ValueError(f'需要达到 Lv.{required}')
            if data['coins']<cost:raise ValueError('星点不足，再练习一次吧')
            data['coins']-=cost; data['owned'].append(hat)
        data['equipped']=hat; self.write(data); return data
