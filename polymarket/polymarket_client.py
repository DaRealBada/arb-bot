import websocket
import json
import threading
import time

class PolymarketClient:
    def __init__(self):
        self.ws_url = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
        self.token_ids = [
            "82105904644975819467254459740176869998531989708711808131488940440519696534822",  # 450-474 Yes
            "103375030657321264814701483740101162210535970159432445623129568287514615958573",  # 450-474 No
            "69442592080794478573959779833784433036273422503780746452193547006928387926589",  # 475-499 Yes
            "78542726175952526631472130854138525311624553971570647007294131780992415355449"   # 475-499 No
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