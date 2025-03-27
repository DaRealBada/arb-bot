import asyncio
import json
import base64
import time
import os
from dotenv import load_dotenv # type: ignore
from cryptography.hazmat.primitives import serialization, hashes # type: ignore
from cryptography.hazmat.primitives.asymmetric import padding # type: ignore
import websockets # type: ignore

class KalshiClient:
    def __init__(self):
        load_dotenv()
        self.key_id = os.getenv("KALSHI_API_KEY")
        self.key_file = os.getenv("KALSHI_PRIVATE_KEY")
        self.ws_url = "wss://api.elections.kalshi.com/trade-api/ws/v2"
        self.order_books = {}
        self.private_key = self._load_private_key()

    def _load_private_key(self):
        with open(self.key_file, "rb") as key_file:
            return serialization.load_pem_private_key(key_file.read(), password=None)

    def _get_auth_headers(self, path="/trade-api/ws/v2"):
        current_time_ms = int(time.time() * 1000)
        timestamp_str = str(current_time_ms)
        message = timestamp_str + "GET" + path
        signature = self.private_key.sign(
            message.encode('utf-8'),
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH),
            hashes.SHA256()
        )
        return {
            "Content-Type": "application/json",
            "KALSHI-ACCESS-KEY": self.key_id,
            "KALSHI-ACCESS-SIGNATURE": base64.b64encode(signature).decode('utf-8'),
            "KALSHI-ACCESS-TIMESTAMP": timestamp_str,
        }

    def _update_order_book(self, ticker, snapshot=None, delta=None):
        if ticker not in self.order_books:
            self.order_books[ticker] = {"yes": {}, "no": {}}
        if snapshot:
            self.order_books[ticker]["yes"] = {price: qty for price, qty in snapshot.get("yes", [])}
            self.order_books[ticker]["no"] = {price: qty for price, qty in snapshot.get("no", [])}
        elif delta:
            side = delta["side"]
            price = delta["price"]
            delta_qty = delta["delta"]
            current_qty = self.order_books[ticker][side].get(price, 0)
            new_qty = current_qty + delta_qty
            if new_qty <= 0:
                self.order_books[ticker][side].pop(price, None)
            else:
                self.order_books[ticker][side][price] = new_qty

    async def run(self):
        headers = self._get_auth_headers()
        market_tickers = ["KXELONTWEETS-25MAR28-474.5"]
        async with websockets.connect(self.ws_url, extra_headers=headers, ping_interval=10) as websocket:
            subscription_message = json.dumps({
                "id": 1,
                "cmd": "subscribe",
                "params": {"channels": ["orderbook_delta"], "market_tickers": market_tickers}
            })
            await websocket.send(subscription_message)
            async for message in websocket:
                data = json.loads(message)
                if data.get("type") in ["orderbook_snapshot", "orderbook_delta"]:
                    ticker = data["msg"]["market_ticker"]
                    self._update_order_book(ticker, snapshot=data["msg"] if data["type"] == "orderbook_snapshot" else None,
                                            delta=data["msg"] if data["type"] == "orderbook_delta" else None)

    def get_order_books(self):
        return self.order_books