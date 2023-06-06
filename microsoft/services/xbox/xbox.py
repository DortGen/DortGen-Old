import json
import random
import sys
import time

from colr import colr

from microsoft.base_task import BaseTask


class Xbox(BaseTask):

    def __init__(self, email, password):
        super().__init__()
        self.purchase_auth_token = None
        self.auth_token = None
        self.email = email
        self.password = password
        self.ua = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) " \
                  f"Chrome/{random.randint(77, 115)}.0.{random.randint(100, 9999)}." \
                  f"{random.randint(10, 172)} Safari/537.36"
        self.default_request_headers = {
            "accept-encoding": "identity",
            "User-Agent": self.ua
        }

    def start(self):
        return self.sign_in()

    def get_options(self, headers: dict = None):
        if headers is None:
            return self.default_request_headers
        headers.update(self.default_request_headers)
        return headers

    def prepare_login(self):
        text = self.get_request('https://account.xbox.com/account/signin?returnUrl=https%3A%2F%2Fwww.xbox.com'
                                '%2Fen-ca%2Fxbox-game-pass%2Fpc-game-pass%2Fdirect',
                                headers=self.get_options({
                                    "accept-encoding": "identity"
                                }),
                                allow_redirects=True).text
        return {
            'ppft': text.split("sFTTag:'<input type=\"hidden\" name=\"PPFT\" id=\"i0327\" value=\"")[1].split('"')[0],
            'preLoginUrl': text.split("urlPost:'")[1].split("'")[0]
        }

    def fetch_needed_tokens(self, ppft, pre_login_url):
        form = {
            'i13': '0',
            'login': self.email,
            'loginfmt': self.email,
            'type': '11',
            'LoginOptions': '3',
            'lrt': '',
            'lrtPartition': '',
            'hisRegion': '',
            'hisScaleUnit': '',
            'passwd': self.password,
            'ps': '2',
            'psRNGCDefaultType': '',
            'psRNGCEntropy': '',
            'psRNGCSLK': '',
            'canary': '',
            'ctx': '',
            'hpgrequestid': '',
            'PPFT': ppft,
            'PPSX': 'Passphrase',
            'NewUser': '1',
            'FoundMSAs': '',
            'fspost': '0',
            'i21': '0',
            'CookieDisclosure': '0',
            'IsFidoSupported': '1',
            'isSignupPost': '0',
            'i19': '20559'
        }
        text = self.post_request(url=pre_login_url, data=form,
                                 headers=self.get_options({"Content-Type": "application/x-www-form-urlencoded"}),
                                 allow_redirects=True).text
        failed = 'urlPost:' not in text
        if not failed:
            return {
                'ppft': text.split("sFT:'")[1].split("'")[0],
                'loginUrl': text.split("urlPost:'")[1].split("'")[0],
                'locked': False
            }
        else:
            return {
                'ppft': None,
                'loginUrl': None,
                'locked': True
            }

    def pre_login(self, ppft, login_url):
        form = {
            'LoginOptions': '3',
            'type': '28',
            'ctx': '',
            'hpgrequestid': '',
            'PPFT': ppft,
            'i19': '2081'
        }
        text = self.post_request(url=login_url, data=form,
                                 headers=self.get_options({"Content-Type": "application/x-www-form-urlencoded"}),
                                 allow_redirects=True).text
        failed = '/abuse?mkt=' in text
        if failed:
            return {'failed': True}
        else:
            return {
                'urlHF': text.split('id="fmHF" action="')[1].split('"')[0],
                'tokenPPRID': text.split('id="pprid" value="')[1].split('"')[0],
                'tokenNAP': text.split('id="NAP" value="')[1].split('"')[0],
                'tokenANON': text.split('id="ANON" value="')[1].split('"')[0],
                'tokenT': text.split('id="t" value="')[1].split('"')[0],
                'failed': False
            }

    def is_login_valid(self, url_hf, token_pprid, token_nap, token_anon, token_t):
        form = {
            'pprid': token_pprid,
            'NAP': token_nap,
            'ANON': token_anon,
            't': token_t
        }
        try:
            self.post_request(url=url_hf, data=form,
                              headers=self.get_options({"Content-Type": "application/x-www-form-urlencoded"}),
                              allow_redirects=True)
            return True
        except Exception:
            return False

    def get_request_verification_token(self, url_hf, token_pprid, token_nap, token_anon,
                                       token_t):
        form = {
            'pprid': token_pprid,
            'NAP': token_nap,
            'ANON': token_anon,
            't': token_t
        }
        response = self.post_request(url=url_hf, data=form, headers=self.get_options(
            {"Content-Type": "application/x-www-form-urlencoded"}), allow_redirects=True).text
        return response.split('name="__RequestVerificationToken" type="hidden" value="')[1].split('"')[
            0] if '__RequestVerificationToken' in response else ""

    def create_xbox_profile(self, request_verification_token):
        form = {
            'partnerOptInChoice': 'false',
            'msftOptInChoice': 'false',
            'isChild': 'true',
            'returnUrl': 'https://www.xbox.com/en-US/?lc=1033'
        }
        try:
            if request_verification_token is not None:
                self.post_request(
                    url='https://account.xbox.com/en-US/xbox/account/api/v1/accountscreation/CreateXboxLiveAccount',
                    data=form,
                    allow_redirects=True,
                    headers=self.get_options({
                        '__RequestVerificationToken': request_verification_token,
                        "Content-Type": "application/x-www-form-urlencoded"
                    })
                )
            for cookie in self.get_request(
                    url='https://account.xbox.com/en-US/xbox/accountsignin?returnUrl=https%3a%2f%2fwww'
                        '.xbox.com%2fen-US%2fgames%2fstore%2fpc-game-pass%2fcfq7ttc0kgq8%2f0007',
                    headers=self.get_options(),
                    allow_redirects=False).cookies.items():
                if 'XBXXtkhttp://mp.microsoft.com/' in cookie[0]:
                    val = cookie[1].replace("%3d", "=")
                    uhs = val.split('%22uhs%22%3a%22')[1].split('%22')[0]
                    token = val.split('%7b%22Token%22%3a%22')[1].split('%22')[0]
                    regular_authentication_token = f'XBL3.0 x={uhs};{token}'
                    purchase_authentication_token = json.dumps({
                        "XToken": f"XBL3.0 x={uhs};{token}"
                    })
                    self.auth_token = regular_authentication_token.replace("%3D", "=")
                    self.purchase_auth_token = purchase_authentication_token
                    current_time = time.strftime("%H:%M:%S", time.localtime())
                    sys.stdout.write(
                        f"[{colr.Colr().hex('#525052', current_time)}] "
                        f"{colr.Colr().hex('#adaaad', 'Created xbox profile')} "
                        f"{colr.Colr().hex('#03fc5e', f'{self.email}')}\n")
                    sys.stdout.flush()
                    return {
                        'regular_authentication_token': regular_authentication_token,
                        'purchase_authentication_token': purchase_authentication_token
                    }
            return None
        except Exception:
            return self.create_xbox_profile(request_verification_token=request_verification_token)

    def sign_in(self):
        ppft_data = self.prepare_login()
        sft_token_data = self.fetch_needed_tokens(ppft=ppft_data['ppft'], pre_login_url=ppft_data['preLoginUrl'])
        if sft_token_data['locked']:
            current_time = time.strftime("%H:%M:%S", time.localtime())
            sys.stdout.write(
                f"[{colr.Colr().hex('#525052', current_time)}] {colr.Colr().hex('#525052', 'Locked')} "
                f"{colr.Colr().hex('#fc3923', f'{self.email}:{self.password}')}\n")
            sys.stdout.flush()
            raise Exception('Account locked or invalid.')
        pre_login_data = self.pre_login(ppft=sft_token_data['ppft'], login_url=sft_token_data['loginUrl'])
        if pre_login_data['failed'] or not self.is_login_valid(url_hf=pre_login_data['urlHF'],
                                                               token_pprid=pre_login_data['tokenPPRID'],
                                                               token_nap=pre_login_data['tokenNAP'],
                                                               token_anon=pre_login_data['tokenANON'],
                                                               token_t=pre_login_data['tokenT']):
            raise Exception('Account locked or invalid.')
        request_verification_token = self.get_request_verification_token(url_hf=pre_login_data['urlHF'],
                                                                         token_pprid=pre_login_data['tokenPPRID'],
                                                                         token_nap=pre_login_data['tokenNAP'],
                                                                         token_anon=pre_login_data['tokenANON'],
                                                                         token_t=pre_login_data['tokenT'])
        return self.create_xbox_profile(request_verification_token=request_verification_token)
