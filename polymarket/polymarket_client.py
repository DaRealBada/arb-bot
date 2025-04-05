import websocket
import json
import threading
import time

class PolymarketClient:
    def __init__(self):
        self.ws_url = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
        self.token_ids = [
            "104581834088683874933735763737237194006527779800533746604473663562104487090909",  # 300-324 Yes
            "93466472616546736282903537705194142846363083134234705550446425815008134085963",  # 300-324 No
            "43922231291025458841678228188174245727138103045821098415263506359671185443258",  # 325-349 Yes
            "53375664434999366377314207204893340538836417260918196297938671959351160828263"   # 325-349 No
        ]
        self.order_books = {}

    def _on_message(self, ws, message):
        data_list = json.loads(message)
        if not isinstance(data_list, list):
            data_list = [data_list]
        for data in data_list:
            if data.get("event_type") == "book":
                asset_id = data["asset_id"]
                self.order_books[asset_id] = {
                    "bids": [(float(bid["price"]), float(bid["size"])) for bid in data["bids"]],
                    "asks": [(float(ask["price"]), float(ask["size"])) for ask in data["asks"]]
                }
            # Ignore price_change for now

    def _on_open(self, ws):
        subscribe_message = {
            "assets_ids": self.token_ids,
            "type": "market"
        }
        ws.send(json.dumps(subscribe_message))

    def run(self):
        ws = websocket.WebSocketApp(
            self.ws_url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=lambda ws, error: print(f"Error: {error}"),
            on_close=lambda ws, code, msg: print(f"Closed: {code}, {msg}")
        )
        wst = threading.Thread(target=ws.run_forever, kwargs={"ping_interval": 30, "ping_timeout": 10})
        wst.daemon = True
        wst.start()

    def get_order_books(self):
        return self.order_books