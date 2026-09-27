"""Credential state is bound to the exact in-memory value that was tested."""
import hashlib

class KeyStatus:
    def __init__(self):self.records={}
    @staticmethod
    def fingerprint(key):return hashlib.sha256(key.encode()).hexdigest()
    def set(self,provider,key,state,message):
        self.records[provider]=(self.fingerprint(key),state,message)
    def get(self,provider,key):
        if not key:return ('empty','未填写')
        record=self.records.get(provider)
        if record and record[0]==self.fingerprint(key):return record[1:]
        return ('pending','已填写 · 待验证')
