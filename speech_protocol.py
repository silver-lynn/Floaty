"""Minimal Doubao streaming PCM protocol; no HTTP server or credential endpoints."""
import asyncio,gzip,json,struct,uuid,zlib
from contextlib import asynccontextmanager
from websockets.asyncio.client import connect
from asr_transcript import TranscriptNormalizer
UPSTREAM = 'wss://openspeech.bytedance.com/api/v3/sauc/bigmodel_async'
LIMIT = 2 * 1024 * 1024


@asynccontextmanager
async def open_upstream(headers):
    # Retry only connection failures before any audio was sent. Never replay audio.
    for attempt in range(3):
        try:
            upstream = await connect(UPSTREAM, additional_headers=headers, open_timeout=8,
                                     ping_interval=10, ping_timeout=20, max_size=LIMIT, max_queue=8)
            break
        except (OSError, TimeoutError):
            if attempt == 2:
                raise
            await asyncio.sleep(0.3 * (attempt + 1))
    try:
        yield upstream
    finally:
        await upstream.close()

class ServiceError(RuntimeError):
    def __init__(self, code):
        self.code = int(code)
        super().__init__('ASR service rejected request')

def frame(payload, audio=False, last=False):
    raw = payload if audio else json.dumps(payload, ensure_ascii=False).encode()
    body = gzip.compress(raw)
    return bytes([0x11, (0x20 if audio else 0x10) | (2 if last else 0), 0x01 if audio else 0x11, 0]) + struct.pack('>I', len(body)) + body

def unpack(data):
    if not isinstance(data, bytes) or len(data) < 8 or data[0] >> 4 != 1:
        raise ValueError('Invalid ASR frame')
    offset = (data[0] & 15) * 4
    kind, flags = data[1] >> 4, data[1] & 15
    if offset < 4 or kind not in (9, 15):
        raise ValueError('Invalid ASR header')
    code = None
    if kind == 15:
        code = struct.unpack_from('>I', data, offset)[0]
        offset += 4
    elif flags & 1:
        offset += 4
    size = struct.unpack_from('>I', data, offset)[0]
    body = data[offset + 4:]
    if size != len(body) or size > LIMIT:
        raise ValueError('Invalid ASR size')
    if data[2] & 15 == 1:
        decoder = zlib.decompressobj(31)
        body = decoder.decompress(body, LIMIT + 1)
        if len(body) > LIMIT or not decoder.eof:
            raise ValueError('ASR payload too large')
    if code is not None:
        raise ServiceError(code)
    payload = json.loads(body)
    if payload.get('code') not in (None, 0, 20000000):
        raise ServiceError(payload['code'])
    return payload, bool(flags & 2)

def config(terms):
    request = {'model_name': 'bigmodel', 'enable_nonstream': True,
               'enable_itn': True, 'enable_punc': True, 'enable_ddc': False,
               'show_utterances': True, 'result_type': 'full', 'end_window_size': 500,
               'force_to_speech_time': 1000,
               'enable_accelerate_text': True, 'accelerate_score': 5}
    if terms:
        request['corpus'] = {'context': json.dumps({'hotwords': [{'word': t} for t in terms]}, ensure_ascii=False)}
    return {'user': {'uid': str(uuid.uuid4())},
            'audio': {'format': 'pcm', 'codec': 'raw', 'rate': 16000, 'bits': 16, 'channel': 1},
            'request': request}
