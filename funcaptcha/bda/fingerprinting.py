import base64
import json
import random
import secrets
import time
import warnings

import numpy as np

from funcaptcha.util import crypt

warnings.filterwarnings("ignore")


class BDA(object):
    bda_encrypted: str
    agent: str

    def __init__(self, bda_encrypted: str, agent: str):
        self.bda_encrypted = bda_encrypted
        self.agent = agent


def cfp_hash(string_in: str) -> int:
    int1 = np.int32(0)
    for int2 in range(len(string_in)):
        int3 = np.int32(ord(string_in[int2]))
        int1 = np.int32((int1 << 5) - int1 + int3)
        int1 = np.bitwise_and(int1, np.int32(-1))
    return int1.item()


def get_browser_data() -> BDA:
    agent: str = secrets.token_urlsafe(16)
    ts: int = round(time.time())
    timeframe: int = round(ts - ts % 21600)
    key: str = f"{agent}{timeframe}"
    bda: list = json.load(open("templates/outlook.json"))
    for i in range(len(bda)):
        if bda[i].get('key') == 'enhanced_fp':
            for i2 in range(len(bda[i]['value'])):
                _key = bda[i]['value'][i2]['key']
                if 'hash' in _key:
                    bda[i]['value'][i2]['value'] = secrets.token_hex(16)
                if _key in 'audio_fingerprint':
                    bda[i]['value'][i2]['value'] = str(random.uniform(32.0432, 124.0435))
        if bda[i].get('key') == 'fe':
            fe = bda[i].get('value')
            for i3 in range(len(fe)):
                b64_cfp = f'canvas winding:yes~canvas fp:{base64.b64encode(secrets.token_bytes(228)).decode()}'
                if 'CFP:' in fe[i3]:
                    fe[i3] = f'CFP:{cfp_hash(b64_cfp)}'
        if 'hash' in bda[i].get('key'):
            bda[i]['value'] = secrets.token_hex(16)
        if bda[i].get('key') == 'f':
            bda[i]['value'] = secrets.token_hex(16)
        if bda[i].get('key') == 'wh':
            bda[i]['value'] = f'{secrets.token_hex(16)}|72627afbfd19a741c7da1732218301ac'
    return BDA(base64.b64encode(crypt.encrypt(json.dumps(bda), key).encode()).decode(), agent)