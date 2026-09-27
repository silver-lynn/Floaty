"""Floaty-only Windows user-bound encrypted credential storage."""
import json
import sys
from pathlib import Path

from paths import data_dir
from secure_storage import crypt
STORE=data_dir()/'settings.dpapi'

def load_keys():
    if not STORE.exists():return {}
    try:
        result=json.loads(crypt(STORE.read_bytes(),decrypt=True))
        return {k:v for k,v in result.items() if k in ('jev','asr') and isinstance(v,str)}
    except Exception:return {}

def save_keys(jev,asr):
    data=json.dumps({'jev':jev,'asr':asr}).encode()
    if len(data)>20000:raise ValueError('Credential size invalid')
    encrypted=crypt(data); STORE.parent.mkdir(parents=True,exist_ok=True)
    temp=STORE.with_suffix('.tmp'); temp.write_bytes(encrypted); temp.replace(STORE)
