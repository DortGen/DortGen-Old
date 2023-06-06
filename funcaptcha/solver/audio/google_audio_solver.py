import httpx

import requests
import json

from funcaptcha.games.base_challenge import AudioChallenge


class AudioRecognizer(object):
    def __init__(self, language="en-US", key="AIzaSyBOti4mM-6x9WDnZIjIeyEU21OpBXqWBgw"):
        self.language = language
        self.key = key
        self.request = None

    def recognize(self, audio_data: bytes):
        url = "http://www.google.com/speech-api/v2/recognize?client=chromium&lang=%s&key=%s" % (self.language, self.key)
        request = httpx.post(url, content=audio_data,
                             headers={"Content-Type": "audio/l16; rate=%s" % 8000})
        actual_result = json.loads(request.text.split('\n')[1]).get("result")[0]
        if "alternative" in actual_result:
            for prediction in actual_result["alternative"]:
                if "transcript" in prediction:
                    return prediction["transcript"]
        raise LookupError("Speech is unintelligible")


class GoogleAudioSolver(AudioChallenge):

    @staticmethod
    def replace_resp(resp: str):
        # most of these were made by me, others belong to "useragents" on GitHub.
        resp = resp.lower()
        replacements = {
            "weinstein": "17",
            "/": "",
            "the": "0",
            "please": "3",
            "brie": "3",
            "river": "0",
            "sex": "6",
            "tube": "2",
            "over": "4",
            "liver": "0",
            "europe": "0",
            "play": "5",
            "text": "6",
            "book": "6",
            "vibe": "5",
            "thor": "4",
            "hai": "5",
            "one": "1",
            "to": "2",
            "two": "2",
            "tree": "3",
            "three": "3",
            "four": "4",
            "jeden": "7",
            "for": "4",
            "or": "4",
            "zero": "0",
            "do": "5",
            "right": "5",
            "hero": "4",
            "five": "5",
            "six": "6",
            "nine": "9",
            "white": "1",
            "whine": "1",
            "dial": "69",
            "wine": "1",
            "guys": "9",
            "sides": "9",
            "store": "44",
            "door": "04",
            "side": "9",
            "buy": "55",
            "rightly": "53",
            "rightfully": "53",
            "lee": "53",
            "now": "9",
            "eight": "8",
            "soon": "2",
            "wireless": "8",
            "find": "5",
            "rise": "1",
            "italy": "34",
            "ice": "0",
            "lights": "9",
            "light": "9",
            "sites": "9",
            "pwell": "9",
            "well": "9",
            "size": "9",
            "by": "1",
            "knights": "9",
            "knight": "9",
            "nights": "9",
            "night": "9",
            "-": "",
            " ": "",
            "r": "9",
            "l": "2",
            "a": "4"
        }
        for key in replacements:
            if key in resp:
                resp = resp.replace(key, replacements[key])
        return resp

    def recognize_audio_captcha(self, audio: bytes) -> str:
        r = AudioRecognizer(self.captcha_language)
        possible_answer = r.recognize(audio)
        return self.replace_resp(possible_answer)

    def solve(self):
        if self.skip_verify:
            return self.full_token
        response = self._submit_answers(self.recognize_audio_captcha(self._get_audio_data()))
        if not response.get('error'):
            with open("agents.txt", "a+") as fp:
                fp.write(f"{self.agent_str}\n")
        if response.get("response") == 'correct':
            return self.full_token
