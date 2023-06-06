import secrets

import tls_client
from httpx import Response, RequestError

from microsoft.socket.per_user_proxy import proxy_url

GLOBAL_PROXY = proxy_url()


class BaseTask:
    def __init__(self):
        self.proxy = GLOBAL_PROXY
        self.session = tls_client.Session("chrome_104")
        self.session.proxies = self.proxy
        self.mscv = secrets.token_urlsafe(12)

    def _retry_request(self, method: str, url: str, tries: int, *args, **kwargs) -> Response:
        tried: int = 0
        while tried < tries:
            try:
                resp = self.session.execute_request(method, url, *args, **kwargs)
                self.mscv = secrets.token_urlsafe(12)
                return resp
            except RequestError:
                pass
        raise Exception(f"Failed to execute request after {tries} tries")

    def _request(self, method: str, url: str, tries: int = 15, *args, **kwargs):
        return self._retry_request(method, url, tries, *args, **kwargs)

    def get_request(self, url, *args, **kwargs):
        return self._request("GET", url, *args, **kwargs)

    def post_request(self, url, *args, **kwargs):
        return self._request("POST", url, *args, **kwargs)

    def options_request(self, url, *args, **kwargs):
        return self._request("OPTIONS", url, *args, **kwargs)

    def head_request(self, url, *args, **kwargs):
        return self._request("HEAD", url, *args, **kwargs)

    def put_request(self, url, *args, **kwargs):
        return self._request("PUT", url, *args, **kwargs)

    def delete_request(self, url, *args, **kwargs):
        return self._request("DELETE", url, *args, **kwargs)

    def patch_request(self, url, *args, **kwargs):
        return self._request("PATCH", url, *args, **kwargs)
