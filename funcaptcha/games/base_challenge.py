import base64
import json
import random
import time
from abc import abstractmethod, ABC

import httpx
import tls_client
from funcaptcha.bda import fingerprinting
from funcaptcha.util import crypt


def encode_all(site_key) -> str:
    return "".join("%{0:0>2}".format(format(ord(char), "x")) for char in site_key)


class BaseFunCaptchaChallenge(ABC):
    """
    FunCaptcha Base Challenge class
    """

    def __init__(self, site_key: str, site_url: str, data: dict[str, str], proxy: str,
                 service_url: str = "https://client-api.arkoselabs.com"):
        """
        Prepares a FunCaptcha Challenge
        """
        self.service_url = service_url
        self.site_key = site_key
        self.site_url = site_url
        self.captcha_language = "en-US"
        self.bda = fingerprinting.get_browser_data()
        self.agent_str = self.bda.bda_encrypted
        self.agent_ver = random.randint(74, 118)
        self.client = tls_client.Session(client_identifier="firefox109")
        self.client.proxies = proxy
        self.proxy = proxy
        self.data = self.get_blobs(data)
        self.client.get(f"https://iframe.arkoselabs.com/{self.site_key}/index.html?mkt=EN")
        self.api_version = "1.4.3/enforcement.8c86261625b34875f40282074a3ea330.html"
        self.json_token = self._request_token()
        self.full_token = self.json_token.get("token")
        self.skip_verify = False
        self.split_token = self.full_token.split("|")
        self.session = self.full_token
        self.session = self.split_token[0]
        self.region = self.split_token[1].replace("r=", "")
        self.referrer_token = self.full_token.replace("|", "&")
        self.challenge = self._get_challenge()
        self.game = self.challenge.get('challengeID')
        self.game_data = self.challenge.get('game_data', {"customGUI": {}})
        self.custom_gui = self.game_data.get("customGUI")
        self.game_variant = self.game_data.get("game_variant", self.game_data.get("puzzle_name"))
        self.challenge_imgs = self.custom_gui.get("_challenge_imgs")
        self.api_breaker = self.custom_gui.get("api_breaker")
        self.waves = self.game_data.get("waves", self.challenge.get('audio_challenge_urls', [""]))
        if 'sup=1' in self.full_token:
            self.game_variant = "pass"
            self.waves = 0
            self.skip_verify = True
        self.display_name = self.game_variant
        self.encryption_key = None

    def _request_token(self) -> dict:
        return self.client.post(f"https://funcaptcha.com/fc/gt2/public_key/{self.site_key}", headers={
            'accept': '*/*',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'origin': self.service_url,
            'referer': f'{self.service_url}/v2/{self.site_key}/{self.api_version}',
            'sec-ch-ua': '"Chromium";v="112", "Google Chrome";v="112", "Not:A-Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': self.agent_str
        }, data={
            "bda": self.bda.bda_encrypted,
            "public_key": self.site_key,
            "site": self.site_url,
            "userbrowser": self.agent_str,
            "capi_version": "1.4.3",
            "capi_mode": "inline",
            "style_theme": "default",
            "rnd": random.random(),
            **self.data
        }).json()

    @staticmethod
    def get_blobs(data) -> dict:
        blobs: dict = dict()
        for k in data:
            blobs.update({f"data[{k}]": data.get(k)})
        return blobs

    @abstractmethod
    def _get_challenge(self):
        raise NotImplementedError("Use GoogleAudioSolver instead.")


class AudioChallenge(BaseFunCaptchaChallenge, ABC):
    def _get_challenge(self) -> dict:
        ts = str(int(time.time() / 1000))
        self.client.cookies.update({
            "timestamp": ts
        })
        return self.client.post(f"https://funcaptcha.com/fc/gfct/", headers={
            "accept": '*/*',
            "accept-encoding": 'gzip, deflate, br',
            "accept-language": 'en-US,en;q=0.9',
            "cache-control": 'no-cache',
            "content-type": 'application/x-www-form-urlencoded; charset=UTF-8',
            "origin": self.service_url,
            "referer": f'{self.service_url}/fc/assets/ec-game-core/game-core/1.12.0/standard/index.html'
                       f'?session={self.referrer_token}',
            "sec-ch-ua": f'"Google Chrome";v="{self.agent_ver}", "Not(A:Brand";v="8", "Chromium";v="{self.agent_ver}"',
            "sec-ch-ua-mobile": '?0',
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": 'empty',
            "sec-fetch-mode": 'cors',
            "sec-fetch-site": 'same-origin',
            "user-agent": self.agent_str,
            "x-newrelic-timestamp": ts,
            "x-requested-id": crypt.encrypt("{}", f"REQUESTED{self.session}ID"),
            "x-requested-with": 'XMLHttpRequest',
        }, data={
            'token': self.session,
            'sid': self.region,
            'lang': self.captcha_language,
            'render_type': "liteJS",
            'isAudioGame': 'true',
            'analytics_tier': '40',
            'data[status]': 'get_new'
        }).json()

    def _submit_answers(self, answer) -> dict:
        if self.skip_verify:
            return {
                "solved": True
            }
        ts = str(int(time.time()))
        self.client.cookies.update({
            "timestamp": ts
        })
        return self.client.post(f"https://funcaptcha.com/fc/audio/", data={
            "session_token": self.session,
            "analytics_tier": "40",
            "response": answer,
            "language": self.captcha_language,
            "r": self.region,
            "audio_type": "2",
            "bio": ""
        }, headers={
            "accept": '*/*',
            "accept-encoding": 'gzip, deflate, br',
            "accept-language": 'en-US,en;q=0.9',
            "cache-control": 'no-cache',
            "content-type": 'application/x-www-form-urlencoded; charset=UTF-8',
            "origin": self.service_url,
            "referer": f'{self.service_url}/fc/assets/ec-game-core/game-core/1.7.0/standard/index.html?'
                       f'session={self.referrer_token}',
            "sec-ch-ua": f'"Google Chrome";v="{self.agent_ver}", "Not(A:Brand";v="8", "Chromium";v="{self.agent_ver}"',
            "sec-ch-ua-mobile": '?0',
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": 'empty',
            "sec-fetch-mode": 'cors',
            "sec-fetch-site": 'same-origin',
            "user-agent": self.agent_str,
            "x-newrelic-timestamp": ts,
            "x-requested-with": 'XMLHttpRequest',
        }).json()

    def _get_audio_data(self) -> bytes:
        response = httpx.get(
            f"https://funcaptcha.com/fc/get_audio/?session_token={self.session}&analytics_tier=40&r={self.region}"
            f"&game=0&language={self.captcha_language}",
            headers={
                "accept": '*/*',
                "accept-encoding": 'gzip, deflate, br',
                "accept-language": 'en-US,en;q=0.9',
                "cache-control": 'no-cache',
                "content-type": 'application/x-www-form-urlencoded; charset=UTF-8',
                "origin": self.service_url,
                "referer": f'{self.service_url}/fc/gc/?token={self.referrer_token}',
                "sec-ch-ua": f'"Google Chrome";v="{self.agent_ver}", "Not(A:Brand";v="8", "Chromium";v="{self.agent_ver}"',
                "sec-ch-ua-mobile": '?0',
                "sec-ch-ua-platform": '"Windows"',
                "sec-fetch-dest": 'empty',
                "sec-fetch-mode": 'cors',
                "sec-fetch-site": 'same-origin',
                "user-agent": self.agent_str,
                "x-requested-with": 'XMLHttpRequest',
            }, follow_redirects=True, proxies=self.proxy)
        if b"DENIED ACCESS" in response.content:
            raise Exception("Download failed.")
        return response.content
