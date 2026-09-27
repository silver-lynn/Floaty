"""Native microphone capture. PCM streams to the existing provider, never saved."""
import asyncio
import importlib.util
import queue
import sys
import threading
import uuid
from pathlib import Path

def cloud_key():
    from preferences import load_keys
    return load_keys().get('asr','')

def verify_key(key):
    """Authenticate and send half a second of synthetic silence, without a microphone."""
    async def verify():
        import speech_protocol as bridge
        headers={'X-Api-Key':key,'X-Api-Resource-Id':'volc.seedasr.sauc.duration',
                 'X-Api-Request-Id':str(uuid.uuid4()),'X-Api-Connect-Id':str(uuid.uuid4()),'X-Api-Sequence':'-1'}
        async with bridge.open_upstream(headers) as upstream:
            await upstream.send(bridge.frame(bridge.config([])))
            await upstream.send(bridge.frame(bytes(16000),audio=True,last=True))
            while True:
                _,terminal=bridge.unpack(await asyncio.wait_for(upstream.recv(),15))
                if terminal:return
    asyncio.run(asyncio.wait_for(verify(),30))

class Speech:
    def __init__(self, emit, key, device=None):
        self.emit, self.key, self.device = emit, key, device
        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()

    def run(self):
        try:
            asyncio.run(self.stream())
        except Exception as e:
            if not self.stop_event.is_set():
                import sounddevice as sd
                if isinstance(e, sd.PortAudioError):
                    self.emit({'type':'error', 'message':'无法打开麦克风。请在设置中选择可用设备，并检查 Windows 麦克风权限。'})
                else:
                    self.emit({'type':'error', 'message':'语音连接失败或中断。请检查网络与豆包语音密钥。'})
        finally:
            self.emit({'type':'finished'})

    async def stream(self):
        import sounddevice as sd
        import speech_protocol as bridge
        headers={'X-Api-Key': self.key, 'X-Api-Resource-Id':'volc.seedasr.sauc.duration',
                 'X-Api-Request-Id':str(uuid.uuid4()), 'X-Api-Connect-Id':str(uuid.uuid4()), 'X-Api-Sequence':'-1'}
        packets=queue.Queue(maxsize=30)
        overflow=threading.Event()
        def callback(data, frames, info, status):
            if status: overflow.set()
            try: packets.put_nowait(bytes(data))
            except queue.Full: overflow.set()
        async with bridge.open_upstream(headers) as upstream:
            await upstream.send(bridge.frame(bridge.config(['AI','Floaty','Demo'])))
            if self.stop_event.is_set(): return
            normalizer=bridge.TranscriptNormalizer()
            async def receive():
                while True:
                    payload, terminal=bridge.unpack(await upstream.recv())
                    for event in normalizer.accept(payload): self.emit(event)
                    if terminal: return
            async def send():
                with sd.RawInputStream(samplerate=16000, channels=1, dtype='int16', blocksize=3200,
                                       device=self.device, callback=callback):
                    self.emit({'type':'ready'})
                    while not self.stop_event.is_set():
                        if overflow.is_set(): raise RuntimeError('Audio overflow')
                        try: data=packets.get_nowait()
                        except queue.Empty:
                            await asyncio.sleep(.02)
                            continue
                        await upstream.send(bridge.frame(data,audio=True))
                while not packets.empty():
                    await upstream.send(bridge.frame(packets.get_nowait(),audio=True))
                await upstream.send(bridge.frame(b'',audio=True,last=True))
            sender=asyncio.create_task(send())
            receiver=asyncio.create_task(receive())
            try:
                done,_=await asyncio.wait([sender,receiver],return_when=asyncio.FIRST_COMPLETED)
                for task in done: task.result()
                if sender in done: await asyncio.wait_for(receiver,10)
                elif not self.stop_event.is_set(): raise RuntimeError('ASR closed')
            finally:
                sender.cancel(); receiver.cancel()
                await asyncio.gather(sender,receiver,return_exceptions=True)
