import json
import secrets
import sys
import time
import urllib.parse
from typing import Union

import discord_webhook
from colr import colr
from discord_webhook import DiscordWebhook

from microsoft.services.purchasables.linker import Linker


class Buyer(Linker):

    def set_default_address(self, profile_data: dict, address_id: str, profile_id: str) -> bool:
        return self.put_request(
            "https://cart.production.store-web.dynamics.com/cart/v1.0/Cart/setDefaultBillingAddress?appId=BuyNow",
            headers=self.get_options({
                "accept": "*/*",
                "accept-encoding": "gzip, deflate, br",
                "accept-language": "en-US,en;q=0.9",
                "cache-control": "max-age=0",
                "content-type": "application/json",
                "if-match": "-7248738646825302319",
                "origin": "https://www.microsoft.com",
                "referer": "https://www.microsoft.com/",
                "sec-ch-ua": "\"Brave\";v=\"113\", \"Chromium\";v=\"113\", \"Not-A.Brand\";v=\"24\"",
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": "\"Windows\"",
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "cross-site",
                "sec-gpc": "1",
                'authority': 'cart.production.store-web.dynamics.com',
                'ms-cv': secrets.token_hex(21) + "b.46.2",
                'authorization': self.auth_token,
                'x-ms-correlation-id': profile_data.get('correlationId'),
                'x-ms-tracking-id': profile_data.get('trackingId'),
                'x-ms-vector-id': profile_data.get('vectorId'),
                'x-authorization-muid': profile_data.get('muid'),
            }),
            json={
                "billingAddressId": address_id,
                "clientContext": {
                    "client": "XboxCom",
                    "deviceFamily": "Web"
                },
                "profileId": profile_id
            }).text

    def start(self):
        linked = super().start()
        try:
            data = self.begin_purchase()
            card_id = linked[0]
            address_id = linked[1]
            is_set = self.set_default_address(data, data.get("profileId"), address_id)
            print(is_set)
            if is_set:
                if self.update_cart(data):
                    paid = self.try_purchase(card_id, data)
                    if paid:
                        current_time = time.strftime("%H:%M:%S", time.localtime())
                        sku = self.config.get('skuId')
                        pid = self.config.get('productId')
                        sys.stdout.write(
                            f"[{colr.Colr().hex('#525052', current_time)}] {colr.Colr().hex('#adaaad', 'Paid')}"
                            f" {colr.Colr().hex('#f246f2', self.email)} "
                            f"{colr.Colr().hex('#adaaad', f'Sku: {sku}, PID: {pid}')}\n")
                        sys.stdout.flush()
                        with open("accounts/purchased_cc.txt", "a+") as file:
                            file.write(f"{self.card}|{self.expm}|{self.expy}\n")
                            file.flush()
                        paid_webhook = self.config.get("paid-webhook")
                        if paid_webhook:
                            paid_webhook = DiscordWebhook(paid_webhook)
                            current_time = time.strftime("%H:%M:%S", time.localtime())
                            paid_webhook.set_content(f"[{current_time}] Paid {self.email} "
                                                     f"| {self.endpoint.upper()}")
                            try:
                                paid_webhook.execute()
                            except Exception:
                                pass
                            pass
                    else:
                        pass
        except Exception:
            pass

    def begin_purchase(self):
        product_id = "CFQ7TTC0KGQ8"
        sku_id = "0002"
        avail_id = self.get_avail_id()
        buy_request_data = urllib.parse.quote(json.dumps(
            {"products": [{"productId": product_id, "skuId": sku_id, "availabilityId": avail_id}],
             "campaignId": "xboxcomct", "callerApplicationId": "XboxCom",
             "expId": ["EX:sc_xboxgamepad", "EX:sc_xboxspinner", "EX:sc_xboxclosebutton", "EX:sc_xboxuiexp",
                       "EX:sc_disabledefaultstyles", "EX:sc_gamertaggifting"],
             "flights": ["sc_xboxgamepad", "sc_xboxspinner", "sc_xboxclosebutton", "sc_xboxuiexp",
                         "sc_disabledefaultstyles", "sc_gamertaggifting"], "clientType": "XboxCom",
             "data": {"usePurchaseSdk": True}, "layout": "Modal", "cssOverride": "XboxCom2NewUI", "theme": "dark",
             "scenario": "", "suppressGiftThankYouPage": False
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
                 f"auth={urllib.parse.quote_plus(self.purchase_auth_token)}").text
        return {
            'profileId': response.split('"profiles":{"byId":{"')[1].split('"')[0],
            'addressId': self.address.get('id'),
            'muid': response.split('"alternativeMuid":"')[1].split('"')[0],
            'accountId': response.split('"accountId":"')[1].split('"')[0],
            'sessionId': response.split('"sessionId":"')[1].split('"')[0],
            'riskId': response.split('"riskId":"')[1].split('"')[0],
            'cartId': response.split('"cartId":"')[1].split('"')[0],
            'customerId': response.split('"customerId":"')[1].split('"')[0],
            'vectorId': response.split('"vectorId":"')[1].split('"')[0],
            "paymentInstrumentId": response.split('{"paymentInstrumentId":"')[1].split('"')[0],
            'correlationId': response.split('"correlationId":"')[1].split('"')[0],
            'trackingId': response.split('"trackingId":"')[1].split('"')[0],
            'price': response.split('"totalAmount":')[1].split(',')[0]
        }

    def update_cart(self, profile_data):
        h = self.put_request(
            f"https://cart.production.store-web.dynamics.com/cart/v1.0/cart/updateCart?cartId="
            f"{profile_data.get('cartId')}&appId=BuyNow", headers=self.get_options({
                'authority': 'cart.production.store-web.dynamics.com',
                'accept': '*/*',
                'accept-language': 'en-US,en;q=0.9',
                'authorization': self.auth_token,
                'content-type': 'application/json',
                'ms-cv': secrets.token_hex(21) + "b.46.2",
                'origin': 'https://www.microsoft.com',
                'referer': 'https://www.microsoft.com/',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'cross-site',
                'x-ms-correlation-id': profile_data.get('correlationId'),
                'x-ms-tracking-id': profile_data.get('trackingId'),
                'x-ms-vector-id': profile_data.get('vectorId'),
                "X-Authorization-Muid": profile_data.get("muid")
            }), json={
                'locale': "es-PA",
                'market': self.endpoint,
                'catalogClientType': '',
                'clientContext': {
                    'client': 'XboxCom',
                    'deviceFamily': 'Web',
                },
                'flights': [
                    'sc_appendconversiontype',
                    'sc_showvalidpis', 'sc_scdstextdirection', 'sc_optimizecheckoutload',
                    'sc_purchasedblockedby', 'sc_passthroughculture', 'sc_showcanceldisclaimerdefaultv1',
                    'sc_redirecttosignin', 'sc_paymentpickeritem', 'sc_cleanreducercode', 'sc_dimealipaystylingfix',
                    'sc_promocode', 'sc_onedrivedowngrade', 'sc_newooslogiconcart', 'sc_optionalcatalogclienttype',
                    'sc_klarna', 'sc_hidecontactcheckbox', 'sc_preparecheckoutrefactor', 'sc_checkoutklarna',
                    'sc_currencyformattingpkg', 'sc_fullpageredirectionforasyncpi', 'sc_xaaconversionerror',
                    'sc_promocodefeature-web-desktop', 'sc_eligibilityproducts', 'sc_disabledpaymentoption',
                    'sc_enablecartcreationerrorparsing', 'sc_purchaseblock', 'sc_returnoospsatocart',
                    'sc_dynamicseligibility', 'sc_usebuynowonlyinternalendpoint', 'sc_removemoreless',
                    'sc_renewalsubscriptionselector', 'sc_hidexdledd', 'sc_militaryshippingurl', 'sc_xboxdualleaf',
                    'sc_japanlegalterms', 'sc_multiplesubscriptions', 'sc_loweroriginalprice',
                    'sc_xaatovalenciastring', 'sc_cannotbuywarrantyalone', 'sc_showminimalfooteroncheckout',
                    'sc_checkoutdowngrade', 'sc_checkoutcontainsiaps', 'sc_localizedtax', 'sc_officescds',
                    'sc_disableupgradetrycheckout', 'sc_extendPageTagToOverride', 'sc_checkoutscenariotelemetry',
                    'sc_skipselectpi', 'sc_allowmpesapi', 'sc_purchasestatusmessage', 'sc_storetermslink',
                    'sc_postorderinfolineitemmessage', 'sc_addpaymentfingerprinttagging', 'sc_shippingallowlist',
                    'sc_emptyresultcheck', 'sc_dualleaf', 'sc_riskyxtoken', 'sc_abandonedretry',
                    'sc_testflightbuynow', 'sc_addshippingmethodtelemetry', 'sc_leaficons', 'sc_newspinneroverlay',
                    'sc_paymentinstrumenttypeandfamily', 'sc_addsitename', 'sc_disallowalipayforcheckout',
                    'sc_checkoutsignintelemetry', 'sc_prominenteddchange', 'sc_disableshippingaddressinit',
                    'sc_preparecheckoutperf', 'sc_buynowctatext', 'sc_buynowuiprod', 'sc_checkoutsalelegaltermsjp',
                    'sc_showooserrorforoneminute', 'sc_proratedrefunds', 'sc_entitlementcheckallitems',
                    'sc_indiaregsbanner', 'sc_checkoutentitlement', 'sc_rspv2', 'sc_focustrapforgiftthankyoupage',
                    'sc_hideneedhelp', 'sc_defaultshippingref', 'sc_uuid', 'sc_checkoutasyncpurchase',
                    'sc_nativeclientlinkredirect', 'sc_enablelegalrequirements', 'sc_expanded.purchasespinner',
                    'sc_valenciaupgrade', 'sc_enablezipplusfour', 'sc_giftingtelemetryfix',
                    'sc_handleentitlementerror', 'sc_alwayscartmuid', 'sc_sharedupgrade', 'sc_checkoutloadspinner',
                    'sc_xaaconversionexpirationdate', 'sc_helptypescript', 'sc_newdemandsandneedsstatement',
                    'sc_citizensoneallowed', 'sc_riskfatal', 'sc_renewtreatmenta', 'sc_trialtreatmenta',
                    'sc_cartzoomfix', 'sc_useofficeonlyinternalendpoint', 'sc_gotopurchase', 'sc_endallactivities',
                    'sc_headingheader', 'sc_flexsubs', 'sc_useanchorcomponent', 'sc_addbillingaddresstelemetry',
                    'sc_replacestoreappclient', 'sc_scenariotelemetryrefactor', 'sc_checkoutsmd',
                    'sc_scenariosupportupdate', 'sc_bankchallengecheckout', 'sc_addpaymenttelemetry', 'sc_railv2',
                    'sc_checkoutglobalpiadd', 'sc_reactcheckout', 'sc_xboxgotocart', 'sc_hidewarningevents',
                    'sc_xboxcomnosapi', 'sc_routebacktocartforoutofstock', 'sc_clientdebuginfo',
                    'sc_koreanlegalterms', 'sc_refactorprorate', 'sc_paymentoptionnotfound', 'sc_pidlflights',
                    'sc_fixcolorcontrastforrecommendeditems', 'sc_hideeditbuttonwhenediting', 'sc_enablekakaopay',
                    'sc_ordercheckoutfix', 'sc_xboxpmgrouping', 'sc_stickyfooter', 'sc_gotoredmrepl',
                    'sc_partnernametelemetry', 'sc_jpregionconversion', 'sc_checkoutorderedpv',
                    'sc_maxaddresslinelength', 'sc_componentexception', 'sc_buynowuipreload', 'sc_updatebillinginfo',
                    'sc_newshippingmethodtelemetry', 'sc_checkoutbannertelemetry', 'sc_learnmoreclcid',
                    'sc_satisfiedcheckout', 'sc_checkboxarialabel', 'sc_newlegaltextlayout', 'sc_newpagetitle',
                    'sc_prepaidcardsv3', 'sc_gamertaggifting', 'sc_checkoutargentinafee', 'sc_xboxcomasyncpurchase',
                    'sc_sameaddressdefault', 'sc_fixcolorcontrastforcheckout', 'sc_checkboxkg',
                    'sc_usebuynowbusinesslogic', 'sc_skippurchaseconfirm', 'sc_activitymonitorasyncpurchase',
                    'sc_shareddowngrade', 'sc_allowedpisenabled', 'sc_xboxoos', 'sc_eligibilityapi',
                    'sc_koreatransactionfeev1', 'sc_removesetpaymentmethod', 'sc_ordereditforincompletedata',
                    'sc_cppidlerror', 'sc_bankchallenge', 'sc_allowelo', 'sc_delayretry', 'sc_loadtestheadersenabled',
                    'sc_migrationforcitizenspay', 'sc_conversionblockederror', 'sc_allowpaysafecard',
                    'sc_purchasedblocked', 'sc_outofstock', 'sc_selectpmonaddfailure', 'sc_allowcustompifiltering',
                    'sc_errorpageviewfix', 'sc_windowsdevkitname', 'sc_xboxredirection',
                    'sc_usebuynowonlynonprodendpoint', 'sc_getmoreinfourl', 'sc_disablefilterforuserconsent',
                    'sc_suppressrecoitem', 'sc_dcccattwo', 'sc_hipercard', 'sc_resellerdetail',
                    'sc_fixpidladdpisuccess', 'sc_xdlshipbuffer', 'sc_allowverve', 'sc_inlinetempfix',
                    'sc_ineligibletostate', 'sc_greenshipping', 'sc_trackinitialcheckoutload', 'sc_creditcardpurge',
                    'sc_showlegalstringforproducttypepass', 'sc_newduplicatesubserror', 'sc_xboxgamepad',
                    'sc_xboxspinner', 'sc_xboxclosebutton', 'sc_xboxuiexp', 'sc_disabledefaultstyles',
                    'sc_gamertaggifting'
                ],
                'paymentInstrumentId': profile_data.get('paymentInstrumentId'),
                'csvTopOffPaymentInstrumentId': None,
                'billingAddressId': {
                    'accountId': profile_data.get('accountId'),
                    'id': profile_data.get('addressId'),
                },
                'sessionId': profile_data.get('sessionId'),
                'orderState': 'CheckingOut',
            })
        return h

    def pre_threeds2_challenge(self, card_id, profile_data):
        data = json.dumps({
            "piid": card_id,
            "language": "en-US",
            "partner": "webblends",
            "piCid": profile_data.get('customerId'),
            "amount": profile_data.get('price'),
            "currency": self.currency,
            "country": self.endpoint.upper(),
            "hasPreOrder": "false",
            "challengeScenario": "RecurringTransaction",
            "challengeWindowSize": "03",
            "purchaseOrderId": profile_data.get('cartId')
        })
        return self.get_request(
            f'https://paymentinstruments.mp.microsoft.com/v6.0/users/me/PaymentSessionDescriptions'
            f'?paymentSessionData={urllib.parse.quote(data)}&operation=Add',
            headers=self.get_options({
                "authorization": self.auth_token
            })
        ).json()[0].get('clientAction').get('context').get('id')

    def _handle_buy_resp(self, resp: dict) -> Union[bool, None]:
        events: dict = resp.get('events')
        cart: dict = resp.get("cart")
        if cart:
            if not cart.get("readyToPurchase"):
                with open("accounts/purchased.txt", "a") as f:
                    f.write(f"{self.email}:{self.password} | {self.config.get('product')}\n")
                with open("accounts/purchased cc.txt", "a") as f:
                    f.write(f"{self.card}\n")
                return True
        if events:
            current_time: str = time.strftime("%H:%M:%S", time.localtime())
            events_cart: list = events.get('cart')
            for x in events_cart:
                data: dict = x.get('data')
                reason: str = data.get('reason')
                message: str = "Unknown Error"
                if 'RiskRejected-CrossBorderPolicy_Reject' == reason:
                    message = "Currency Mismatch"
                elif 'RiskRejected' == reason:
                    message = "Fraud Decline"
                elif 'ProcessorDeclined' == reason:
                    message = "Processor Declined"
                elif 'TransactionNotAllowed' == reason:
                    message = "Transaction Not Allowed"
                if message != "Currency Mismatch":
                    webhook: str = self.config.get("declined-webhook")
                    discord_webhook.webhook.logger.disabled = True
                    declined_webhook = DiscordWebhook(webhook)
                    current_time = time.strftime("%H:%M:%S", time.localtime())
                    declined_webhook.set_content(f"`[{current_time}] {message} -> {self.email} (CCN: {self.card})`")
                    try:
                        declined_webhook.execute()
                    except Exception:
                        pass
                sys.stdout.write(
                    f"[{colr.Colr().hex('#525052', current_time)}] {colr.Colr().hex('#adaaad', message)} "
                    f"{colr.Colr().hex('#00ffff', self.email)} "
                    f"{colr.Colr().hex('#adaaad', f'BIN: {self.card[0:6]}')}\n")
                sys.stdout.flush()
        return False

    def try_purchase(self, card_id, profile_data):
        tds_chl = self.pre_threeds2_challenge(card_id, profile_data)
        paid_resp = self.post_request(
            "https://cart.production.store-web.dynamics.com/cart/v1.0/Cart/purchase?appId"
            "=BuyNow", headers=self.get_options({
                'authority': 'cart.production.store-web.dynamics.com',
                'accept': '*/*',
                'accept-language': 'en-US,en;q=0.9',
                'content-type': 'application/json',
                'ms-cv': secrets.token_urlsafe(21) + "b.46.2",
                'origin': 'https://www.microsoft.com',
                'referer': 'https://www.microsoft.com/',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'cross-site',
                "authorization": self.auth_token,
                "correlation-context": "v=1,ms.b.tel.scenario=commerce.payments.PaymentInstrumentAdd.1,"
                                       "ms.b.tel.partner=XboxCom,ms.c.cfs.payments.partnerSessionId=" +
                                       secrets.token_urlsafe(6),
                "x-ms-pidlsdk-version": "1.22.9_reactview",
                'x-ms-correlation-id': profile_data.get('correlationId'),
                'x-ms-tracking-id': profile_data.get('trackingId'),
                'x-ms-vector-id': profile_data.get('vectorId'),
                "X-Authorization-Muid": profile_data.get("muid"),
            }), json={
                "billingAddressId": {
                    "accountId": profile_data.get("accountId"),
                    "id": profile_data.get("addressId"),
                },
                "callerApplicationId": "_CONVERGED_XboxCom",
                "cartId": profile_data.get("cartId"),
                "catalogClientType": "",
                "clientContext": {
                    "client": "XboxCom",
                    "deviceFamily": "Web"
                },
                "csvTopOffPaymentInstrumentId": None,
                "currentOrderState": "CheckingOut",
                "email": self.email,
                "flights": [
                    'sc_appendconversiontype', 'sc_showvalidpis', 'sc_scdstextdirection',
                    'sc_optimizecheckoutload', 'sc_purchasedblockedby', 'sc_passthroughculture',
                    'sc_showcanceldisclaimerdefaultv1', 'sc_redirecttosignin', 'sc_paymentpickeritem',
                    'sc_cleanreducercode', 'sc_dimealipaystylingfix', 'sc_promocode', 'sc_onedrivedowngrade',
                    'sc_newooslogiconcart', 'sc_optionalcatalogclienttype', 'sc_klarna',
                    'sc_hidecontactcheckbox', 'sc_preparecheckoutrefactor', 'sc_checkoutklarna',
                    'sc_currencyformattingpkg', 'sc_fullpageredirectionforasyncpi', 'sc_xaaconversionerror',
                    'sc_promocodefeature-web-desktop', 'sc_eligibilityproducts', 'sc_disabledpaymentoption',
                    'sc_enablecartcreationerrorparsing', 'sc_purchaseblock', 'sc_returnoospsatocart',
                    'sc_dynamicseligibility', 'sc_usebuynowonlyinternalendpoint', 'sc_removemoreless',
                    'sc_renewalsubscriptionselector', 'sc_hidexdledd', 'sc_militaryshippingurl',
                    'sc_xboxdualleaf', 'sc_japanlegalterms', 'sc_multiplesubscriptions',
                    'sc_loweroriginalprice', 'sc_xaatovalenciastring', 'sc_cannotbuywarrantyalone',
                    'sc_showminimalfooteroncheckout', 'sc_checkoutdowngrade', 'sc_checkoutcontainsiaps',
                    'sc_localizedtax', 'sc_officescds', 'sc_disableupgradetrycheckout',
                    'sc_extendPageTagToOverride', 'sc_checkoutscenariotelemetry', 'sc_skipselectpi',
                    'sc_allowmpesapi', 'sc_purchasestatusmessage', 'sc_storetermslink',
                    'sc_postorderinfolineitemmessage', 'sc_addpaymentfingerprinttagging',
                    'sc_shippingallowlist', 'sc_emptyresultcheck', 'sc_dualleaf', 'sc_riskyxtoken',
                    'sc_abandonedretry', 'sc_testflightbuynow', 'sc_addshippingmethodtelemetry', 'sc_leaficons',
                    'sc_newspinneroverlay', 'sc_paymentinstrumenttypeandfamily', 'sc_addsitename',
                    'sc_disallowalipayforcheckout', 'sc_checkoutsignintelemetry', 'sc_prominenteddchange',
                    'sc_disableshippingaddressinit', 'sc_preparecheckoutperf',
                    'sc_buynowctatext', 'sc_buynowuiprod', 'sc_checkoutsalelegaltermsjp',
                    'sc_showooserrorforoneminute', 'sc_proratedrefunds', 'sc_entitlementcheckallitems',
                    'sc_indiaregsbanner', 'sc_checkoutentitlement', 'sc_rspv2',
                    'sc_focustrapforgiftthankyoupage', 'sc_hideneedhelp', 'sc_defaultshippingref', 'sc_uuid',
                    'sc_checkoutasyncpurchase', 'sc_nativeclientlinkredirect', 'sc_enablelegalrequirements',
                    'sc_expanded.purchasespinner', 'sc_valenciaupgrade', 'sc_enablezipplusfour',
                    'sc_giftingtelemetryfix', 'sc_handleentitlementerror', 'sc_alwayscartmuid',
                    'sc_sharedupgrade', 'sc_checkoutloadspinner', 'sc_xaaconversionexpirationdate',
                    'sc_helptypescript', 'sc_newdemandsandneedsstatement', 'sc_citizensoneallowed',
                    'sc_riskfatal', 'sc_renewtreatmenta', 'sc_trialtreatmenta', 'sc_cartzoomfix',
                    'sc_useofficeonlyinternalendpoint', 'sc_gotopurchase', 'sc_endallactivities',
                    'sc_headingheader', 'sc_flexsubs', 'sc_useanchorcomponent', 'sc_addbillingaddresstelemetry',
                    'sc_replacestoreappclient', 'sc_scenariotelemetryrefactor', 'sc_checkoutsmd',
                    'sc_scenariosupportupdate', 'sc_bankchallengecheckout', 'sc_addpaymenttelemetry',
                    'sc_railv2', 'sc_checkoutglobalpiadd', 'sc_reactcheckout', 'sc_xboxgotocart',
                    'sc_hidewarningevents', 'sc_xboxcomnosapi', 'sc_routebacktocartforoutofstock',
                    'sc_clientdebuginfo', 'sc_koreanlegalterms', 'sc_refactorprorate',
                    'sc_paymentoptionnotfound', 'sc_pidlflights', 'sc_fixcolorcontrastforrecommendeditems',
                    'sc_hideeditbuttonwhenediting', 'sc_enablekakaopay', 'sc_ordercheckoutfix',
                    'sc_xboxpmgrouping', 'sc_stickyfooter', 'sc_gotoredmrepl', 'sc_partnernametelemetry',
                    'sc_jpregionconversion', 'sc_checkoutorderedpv', 'sc_maxaddresslinelength',
                    'sc_componentexception', 'sc_buynowuipreload', 'sc_updatebillinginfo',
                    'sc_newshippingmethodtelemetry', 'sc_checkoutbannertelemetry', 'sc_learnmoreclcid',
                    'sc_satisfiedcheckout', 'sc_checkboxarialabel', 'sc_newlegaltextlayout', 'sc_newpagetitle',
                    'sc_prepaidcardsv3', 'sc_gamertaggifting', 'sc_checkoutargentinafee',
                    'sc_xboxcomasyncpurchase', 'sc_sameaddressdefault', 'sc_fixcolorcontrastforcheckout',
                    'sc_checkboxkg', 'sc_usebuynowbusinesslogic', 'sc_skippurchaseconfirm',
                    'sc_activitymonitorasyncpurchase', 'sc_shareddowngrade', 'sc_allowedpisenabled',
                    'sc_xboxoos', 'sc_eligibilityapi', 'sc_koreatransactionfeev1', 'sc_removesetpaymentmethod',
                    'sc_ordereditforincompletedata', 'sc_cppidlerror', 'sc_bankchallenge', 'sc_allowelo',
                    'sc_delayretry', 'sc_loadtestheadersenabled', 'sc_migrationforcitizenspay',
                    'sc_conversionblockederror', 'sc_allowpaysafecard', 'sc_purchasedblocked', 'sc_outofstock',
                    'sc_selectpmonaddfailure', 'sc_allowcustompifiltering', 'sc_errorpageviewfix',
                    'sc_windowsdevkitname', 'sc_xboxredirection', 'sc_usebuynowonlynonprodendpoint',
                    'sc_getmoreinfourl', 'sc_disablefilterforuserconsent', 'sc_suppressrecoitem',
                    'sc_dcccattwo', 'sc_hipercard', 'sc_resellerdetail', 'sc_fixpidladdpisuccess',
                    'sc_xdlshipbuffer', 'sc_allowverve', 'sc_inlinetempfix', 'sc_ineligibletostate',
                    'sc_greenshipping', 'sc_trackinitialcheckoutload', 'sc_creditcardpurge',
                    'sc_showlegalstringforproducttypepass', 'sc_newduplicatesubserror', 'sc_xboxgamepad',
                    'sc_xboxspinner', 'sc_xboxclosebutton', 'sc_xboxuiexp', 'sc_disabledefaultstyles',
                    'sc_gamertaggifting'
                ],
                "itemsToAdd": {},
                "locale": "en-US",
                "market": self.endpoint,
                "paymentInstrumentId": card_id,
                "paymentInstrumentType": 'visa' if self.card.startswith('4') else 'mc',
                "paymentSessionId": profile_data.get("sessionId"),
                "riskChallengeData": {
                    "data": tds_chl,
                    "type": "threeds2"
                }
            }
        ).json()
        return self._handle_buy_resp(paid_resp)
