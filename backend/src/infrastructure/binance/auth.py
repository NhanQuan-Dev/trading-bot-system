from urllib.parse import urlencode
import hmac
import hashlib
import time

class Auth:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret

    def _sign(self, params: dict) -> str:
        query = urlencode(params, True)
        return hmac.new(
            self.api_secret.encode(),
            query.encode(),
            hashlib.sha256
        ).hexdigest()

    def generate_signature(self, params: dict) -> str:
        params["timestamp"] = int(time.time() * 1000)
        params["signature"] = self._sign(params)
        return params

    def get_headers(self) -> dict:
        return {"X-MBX-APIKEY": self.api_key}