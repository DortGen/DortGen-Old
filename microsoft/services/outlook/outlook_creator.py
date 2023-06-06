import datetime
import itertools
import json
import random
import secrets
import string
import sys
import time
import traceback

import httpx
import names
from colr import colr

from funcaptcha.solver.audio.google_audio_solver import GoogleAudioSolver
from funcaptcha.solver.exploit.instant_solver import InstantSolver
from funcaptcha.solver.image import hash_solver
from microsoft.base_task import BaseTask
# from microsoft.ocr import ocr
from microsoft.services.outlook.proof_data import cipher
from microsoft.services.outlook.smtp import SmtpEnable
from microsoft.services.purchasables.buy import Buyer

proxy_iter: iter = itertools.cycle(open("proxies.txt").read().splitlines())
config: list[dict] = json.load(open("templates/domains.json"))


def fix_text(text) -> str:
    return text.replace('\\u002f', "/").replace('\\u003a', ":").replace('\\u0026', "&").replace('\\u003d', "=") \
        .replace('\\u002b', "+")


def random_alphabetic_string(length):
    return "".join(random.choices(string.ascii_letters, k=length))


class OutlookAccount(BaseTask):
    current_wave: int = 0
    current_type: str = "null"

    def __init__(self, do_buy=True, mkt="en-US", debug=True):
        super().__init__()
        self.ht = None
        self.solution = None
        self.hf_id = secrets.token_hex(16)
        self.debug = debug
        self.config = random.choice(config)
        self.cipher = None
        self.agent = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) " \
                     f"Chrome/{random.randint(77, 108)}.0.{random.randint(1000, 9999)}." \
                     f"{random.randint(0, 144)} Safari/537.36"
        self.captcha_site_key = "B7D8911C-5CC8-A9A3-35B0-554ACEE604DA"
        self.signup_url = f"https://signup.live.com/signup?lic=1&mkt={self.config.get('mkt')}"
        self.create_url = f"https://signup.live.com/API/CreateAccount?lic=1"
        self.password = "".join(random.choices(string.ascii_letters + string.digits, k=16))
        self.password += "$DortGen"
        self.first_name = names.get_first_name()
        self.last_name = names.get_last_name()
        self.email = f"{self.first_name}{self.last_name}{random.randint(9990, 100000)}" \
                     f"@{self.config.get('domain')}".lower()
        self.birthday = self._get_birthday()
        self.key = None
        self.ski = None
        self.random_num = None
        self.canary = None
        self.tcxt = None
        self.uaid = None
        self.encAttemptToken = ""
        self.dfpRequestId = ""
        self.load_register_page()
        self.cipher = cipher.package_pwd(self.password, self.random_num, self.key)
        self.do_buy = do_buy

    @staticmethod
    def _hand_error(code: str):
        errors = {
            "1043": "Invalid Captcha",
            "1040": "Text Captcha",
            "1041": "Enforcement Captcha",
            "1042": "SMS Needed",
            "450": "Daily Limit Reached",
            "1304": "OTP Invalid",
            "1324": "Verification SLT Invalid",
            "1058": "Username Taken",
            "1117": "Domain Blocked",
            "1181": "Reserved Domain",
            "403": "Bad Username",
            "1002": "Incorrect Password",
            "1009": "Password Conflict",
            "1062": "Invalid Email Format",
            "1063": "Invalid Phone Format",
            "1039": "Invalid Birth Date",
            "1243": "Invalid Gender",
            "1240": "Invalid first name",
            "1241": "Invalid last name",
            "1204": "Maximum OTPs reached",
            "1217": "Banned Password",
            "1246": "Proof Already Exists",
            "1184": "Domain Blocked",
            "1185": "Domain Blocked",
            "1052": "Email Taken",
            "1242": "Phone Number Taken",
            "1220": "Signup Blocked",
            "1064": "Invalid Member Name Format",
            "1330": "Password Required",
            "1256": "Invalid Email",
            "1334": "Eviction Warning Required",
            "100": "Bad Register Request"
        }
        return errors[code]

    @staticmethod
    def _get_birthday():
        day = random.randint(1, 27)
        month = random.randint(1, 9)
        year = random.randint(1969, 2000)
        return f"{day}:0{month}:{year}"

    def load_register_page(self):
        body: str = self.get_request(self.signup_url, headers={
            "User-Agent": self.agent
        }).text

        self.uaid = body.split('"clientTelemetry":{"uaid":"')[1].split('"')[0]
        self.tcxt = fix_text(body.split('"clientTelemetry":{"uaid":"')[1].split(',"tcxt":"')[1].split('"},')[0])
        self.canary = fix_text(body.split('"apiCanary":"')[1].split('"')[0])
        self.random_num = body.split('var randomNum="')[1].split('"')[0]
        self.key = body.split('var Key="')[1].split('"')[0]
        self.ski = body.split('var SKI="')[1].split('"')[0]

    def register_account(self, solved=None):
        body = self.register_body(solved)
        resp = self.post_request(self.create_url, json=body, headers=self.register_headers())
        error = resp.json().get("error")
        if error:
            code = error.get("code")
            if '1040' in code:
                error_data = error.get("data")
                self.encAttemptToken = fix_text(error_data.split('encAttemptToken":"')[1].split('"')[0])
                self.dfpRequestId = fix_text(error_data.split('dfpRequestId":"')[1].split('"')[0])
                hf_id = self.hf_id
                url: str = f"https://client.hip.live.com/GetHIP/GetHIPAMFE/HIPAMFE?id=15041&mkt=en-US&fid" \
                           f"={hf_id}&type=visual&rand={random.randint(0, 1000000)}"
                data: str = self.session.get(url, headers={
                    "Accept-Encoding": "identity"
                }).text
                dcid: str = data.split('"dataCenter":"')[1].split('"')[0]
                ht: str = data.split('"hipToken":"')[1].split('"')[0].split(".")[1]
                self.ht = dcid + "." + ht
                image: str = f"https://{dcid}.client.hip.live.com/GetHIPData?hid={dcid}" \
                             f".{ht}&fid={hf_id}" \
                             f"&id=15041&type=visual&cs=HIPAMFE"
                self.image_bytes: bytes = httpx.get(image, proxies=self.proxy).content
                self.solution = ocr.ocr_outlook(self.image_bytes)
                self.register_account("tc")
            elif '1041' in code:
                error_data = error.get("data")
                self.encAttemptToken = fix_text(error_data.split('encAttemptToken":"')[1].split('"')[0])
                self.dfpRequestId = fix_text(error_data.split('dfpRequestId":"')[1].split('"')[0])
                self.register_account("fc")
            elif '1043' in code:
                if self.debug:
                    pass
                    current_time = time.strftime("%H:%M:%S", time.localtime())
                    sys.stdout.write(
                        f"[{colr.Colr().hex('#525052', current_time)}] {colr.Colr().hex('#adaaad', 'Invalid captcha')} "
                        f"{colr.Colr().hex('#fc2723', body.get('HSol').split('|')[0])}\n")
                    sys.stdout.flush()
            else:
                if self.debug:
                    current_time = time.strftime("%H:%M:%S", time.localtime())
                    sys.stdout.write(
                        f"[{colr.Colr().hex('#525052', current_time)}] "
                        f"{colr.Colr().hex('#adaaad', self._hand_error(code))} "
                        f"{colr.Colr().hex('#ff6b61', f'{self.email}')}\n")
                    raise Exception(self._hand_error(code))
        else:
            if self.debug:
                current_time = time.strftime("%H:%M:%S", time.localtime())
                sys.stdout.write(
                    f"[{colr.Colr().hex('#525052', current_time)}] {colr.Colr().hex('#adaaad', 'Created')} "
                    f"{colr.Colr().hex('#4792f5', f'{self.email}')}\n")
                sys.stdout.flush()
            with open("accounts/raw_created.txt", "a+") as fp:
                fp.write(f"{self.email}:{self.password}\n")
            if self.do_buy:
                try:
                    Buyer(self.email, self.password).start()
                except Exception:
                    pass
            else:
                pass
                # try:
                #     SmtpEnable(self.debug, self.email, self.password).start()
                # except Exception:
                #     pass
        return {
            "email": self.email,
            "password": self.password,
        }

    def register_body(self, captcha_type: str) -> dict:
        body = {
            "RequestTimeStamp": str(datetime.datetime.now()).replace(" ", "T")[:-3] + "Z",
            "MemberName": self.email,
            "CheckAvailStateMap": [
                f"{self.email}:undefined"
            ],
            "EvictionWarningShown": [],
            "UpgradeFlowToken": {},
            "FirstName": self.first_name,
            "LastName": self.last_name,
            "MemberNameChangeCount": 1,
            "MemberNameAvailableCount": 1,
            "MemberNameUnavailableCount": 0,
            "CipherValue": self.cipher,
            "SKI": self.ski,
            "BirthDate": self.birthday,
            "Country": self.config.get("country"),
            "AltEmail": None,
            "IsOptOutEmailDefault": True,
            "IsOptOutEmailShown": True,
            "IsOptOutEmail": True,
            "LW": True,
            "SiteId": "68692",
            "IsRDM": 0,
            "WReply": None,
            "ReturnUrl": None,
            "SignupReturnUrl": None,
            "uiflvr": 1001,
            "uaid": self.uaid,
            "SuggestedAccountType": "OUTLOOK",
            "SuggestionType": "Locked",
            "HFId": self.hf_id,
            "encAttemptToken": self.encAttemptToken,
            "dfpRequestId": self.dfpRequestId,
            "scid": 100118,
            "hpgid": 201040,
        }
        if captcha_type == "fc":
            body.update({
                "HType": "enforcement",
                "HSol": self.retry_solve(),
                "HPId": self.captcha_site_key,
            })
        elif captcha_type == "tc":
            body.update({
                "HType": "visual",
                "HSol": self.solution,
                "HId": self.ht,
                "HSId": "15041"
            })
        return body

    def retry_solve(self):
        while True:
            try:
                tokens = GoogleAudioSolver(
                    self.captcha_site_key,
                    "https://iframe.arkoselabs.com", {
                        "blob": "undefined"
                    }, self.proxy)
                OutlookAccount.current_wave = tokens.waves
                OutlookAccount.current_type = tokens.game_variant
                token = tokens.solve()
                if token:
                    return token
            except Exception as ex:
                pass

    def register_headers(self):
        return {
            "accept": "application/json",
            "accept-encoding": "gzip, deflate, br",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "no-cache",
            "canary": self.canary,
            "content-type": "application/json",
            "dnt": "1",
            "hpgid": f"2006{random.randint(10, 99)}",
            "origin": "https://signup.live.com",
            "pragma": "no-cache",
            "scid": "100118",
            "sec-ch-ua": '" Not A;Brand";v="107", "Chromium";v="96", "Google Chrome";v="96"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "tcxt": self.tcxt,
            "uaid": self.uaid,
            "uiflvr": "1001",
            "user-agent": self.agent,
            "x-ms-apitransport": "xhr",
            "x-ms-apiversion": "2",
            "referrer": "https://signup.live.com/?lic=1"
        }
