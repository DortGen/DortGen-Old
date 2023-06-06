import math
import random
import re
import sys
import threading
import time

import colr
from bs4 import BeautifulSoup

from microsoft.base_task import BaseTask

__lock__ = threading.Lock()


def create_transfer_dict(resp_text):
    so = BeautifulSoup(resp_text, 'html.parser')
    pp_rid = so.find("input", attrs={"name": "pprid"})['value']
    ipt = so.find("input", attrs={"name": "ipt"})['value']
    uaid = so.find("input", attrs={"name": "uaid"})['value']
    n_url = so.find("form", attrs={"name": "fmHF"})['action']

    return n_url, {
        "pprid": pp_rid,
        "ipt": ipt,
        "uaid": uaid
    }


def gup():
    return format(math.floor(65536 * (1 + random.random())), "x")[1:]


def generate_correlation_id():
    return gup() + gup() + "-" + gup() + "-" + gup() + "-" + gup() + "-" + gup() + gup() + gup()


def generate_session_id():
    s = "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx"
    new_s = ""
    for c in s:
        n = random.randint(1, 16)
        if c in ["x", "y"]:
            if c == "x":
                new_s += format(n, "x")
            else:
                new_s += format(3 & n | 8, "x")
        else:
            new_s += c
    return new_s


def create_transfer_dict_2(resp_text):
    so = BeautifulSoup(resp_text, 'html.parser')
    pp_rid = so.find("input", attrs={"name": "pprid"})['value']
    nap = so.find("input", attrs={"name": "NAP"})['value']
    anon = so.find("input", attrs={"name": "ANON"})['value']
    t = so.find("input", attrs={"name": "t"})['value']
    n_url = so.find("form", attrs={"name": "fmHF"})['action']

    return n_url, {
        "pprid": pp_rid,
        "NAP": nap,
        "ANON": anon,
        "t": t
    }


def get_cookie_dict(co):
    return {c: co[c] for c in co}


def headers_wa(**kwargs):
    """Generates custom headers with addition"""
    base_headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "identity",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:104.0) Gecko/20100101 Firefox/104.0"
    }

    for kw in kwargs:
        k, v = kw, kwargs[kw]
        base_headers.update({k.replace("_", "-"): v})

    return base_headers


class SmtpEnable(BaseTask):
    def __init__(self, debug, username, password):
        super().__init__()
        self.debug = debug
        self.username = username
        self.password = password

    def start(self):
        self.enable_smtp()

    def enable_smtp(self):
        username = self.username
        password = self.password
        first_login_stage = self.get_request("https://outlook.live.com/owa/?nlp=1", allow_redirects=True, headers={
            "Accept-Encoding": "identity"
        })
        ppft_string = re.search("PPFT\".*?value=\"(.*?)\"", first_login_stage.text).group(1)
        next_url = re.search("urlPost:\'(.*?)\'", first_login_stage.text).group(1)
        second_stage = self.post_request(next_url, data={
            "i13": "0",
            "login": username,
            "loginfmt": username,
            "type": "11",
            "LoginOptions": "3",
            "Irt": "",
            "IrtPartition": "",
            "hisRegion": "",
            "hisScaleUnit": "",
            "passwd": password,
            "ps": "2",
            "psRNGCDefaultType": "",
            "psRNGCEntropy": "",
            "psRNGCSLK": "",
            "canary": "",
            "ctx": "",
            "hpgrequestid": "",
            "PPFT": ppft_string,
            "PPSX": "Passpo",
            "NewUser": "1",
            "FoundMSAs": "",
            "fspost": "0",
            "i21": "0",
            "CookieDisclosure": "0",
            "IsFidoSupported": "1",
            "isSignupPost": "0",
            "isRecoveryAttemptPost": "0",
            "i19": str(random.randint(300000, 400000))
        }, headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept-Encoding": "identity"
        })
        url_post = re.search("urlPost:\'(.*?)\'", second_stage.text)
        url_post = url_post.group(1)
        ppft_token_2 = re.search("sFT:\'(.*?)\'", second_stage.text).group(1)
        second_login_stage = self.post_request(url_post, data={
            "LoginOptions": "3",
            "type": "28",
            "ctx": "",
            "hpgrequestid": "",
            "PPFT": ppft_token_2,
            "i19": str(random.randint(1000, 5000))
        }, allow_redirects=True, headers=headers_wa(
            Content_Type="application/x-www-form-urlencoded",
            Accept="text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,"
                   "image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;"
                   "q=0.9",
            Host="login.live.com",
            Origin="https://login.live.com"
        ))
        next_url, transfer_dict = create_transfer_dict_2(second_login_stage.text)
        transfer_dict = dict(**transfer_dict, **{"wbids": "0", "wbid": "MSFT"})
        self.post_request(next_url, data=transfer_dict, allow_redirects=True, headers=headers_wa(
            Referer="https://login.live.com/",
            Origin="https://login.live.com",
            Host="outlook.live.com",
            Accept_Language="en-US,en;q=0.5",
            Content_Type="application/x-www-form-urlencoded",
            Accept="text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
        ))
        x_canary = ""
        for k in self.session.cookies.items():
            if k[0] == "X-OWA-CANARY":
                x_canary = k[1]
                break

        self.post_request("https://outlook.live.com/owa/0/lang.owa", data={
            "localeName": "en-US",
            "tzid": "Europe/Warsaw",
            "saveLanguageAndTimezone": "1"
        }, headers=headers_wa(
            Content_Type="application/x-www-form-urlencoded",
            Accept="*/*",
            Host="outlook.live.com",
            Origin="https://outlook.live.com",
            x_owa_canary=x_canary
        ))

        headers = {
            'Host': 'outlook.live.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:107.0) Gecko/20100101 Firefox/107.0',
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://outlook.live.com/',
            'action': 'SetConsumerMailbox',
            'content-type': 'application/json; charset=utf-8',
            'x-owa-canary': x_canary,
            'x-owa-urlpostdata': '{"__type":"SetConsumerMailboxRequest:#Exchange","Header":{'
                                 '"__type":"JsonRequestHeaders:#Exchange","RequestServerVersion":"V2018_01_08",'
                                 '"TimeZoneContext":{"__type":"TimeZoneContext:#Exchange","TimeZoneDefinition":{'
                                 '"__type":"TimeZoneDefinitionType:#Exchange","Id":"Eastern Standard Time"}}},'
                                 '"Options":{"PopEnabled":true,"PopMessageDeleteEnabled":false}}',
            'x-req-source': 'Mail',
            'Origin': 'https://outlook.live.com',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Connection': 'keep-alive',
            'TE': 'trailers'
        }
        params = {"action": 'SetConsumerMailbox', "app": 'Mail', "n": str(random.randint(50, 99))}
        current_time = time.strftime("%H:%M:%S", time.localtime())
        req = None
        status_code = 200
        try:
            req = self.post_request("https://outlook.live.com/owa/0/service.svc", headers=headers, params=params)
        except Exception as ex:
            if '449' in str(ex):
                status_code = 449
            else:
                status_code = 500
        if status_code == 200 or status_code == 449:
            with open("accounts/enabled.txt", 'a+') as fp:
                fp.write(f"{self.username}:{self.password}\n")
                fp.flush()
            sys.stdout.write(
                f"[{colr.Colr().hex('#525052', current_time)}] {colr.Colr().hex('#7f71e3', 'Enabled IMAP/POP')} "
                f"{colr.Colr().hex('#7f71e3', f'{self.username}:{self.password}')}\n")
            sys.stdout.flush()
