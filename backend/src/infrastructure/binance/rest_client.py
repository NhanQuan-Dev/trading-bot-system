from typing import Dict, Any
import requests
import time
import hmac
import hashlib
from urllib.parse import urlencode
from shared.exceptions.api_exception import APIException

class RestClient:
    def __init__(self, api_key: str, api_secret: str, base_url: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url

    def _sign(self, params: Dict[str, Any]) -> str:
        query = urlencode(params, True)
        return hmac.new(
            self.api_secret.encode(),
            query.encode(),
            hashlib.sha256
        ).hexdigest()

    def signed_get(self, path: str, params: Dict[str, Any]) -> dict:
        params["timestamp"] = int(time.time() * 1000)
        params.setdefault("recvWindow", 5000)
        params["signature"] = self._sign(params)

        headers = {"X-MBX-APIKEY": self.api_key}
        response = requests.get(
            f"{self.base_url}{path}",
            headers=headers,
            params=params,
            timeout=10,
        )
        
        if response.status_code != 200:
            raise APIException(f"Error {response.status_code}: {response.text}")
        
        return response.json()