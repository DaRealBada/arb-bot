import websocket
import json
import threading
import time
import logging
from threading import Lock

# Set up logging for debugging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

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
        self.order_books_lock = Lock()
        self.is_running = False
        self.last_update = 0
        self.update_count = 0  # Track number of updates received

    def _on_message(self, ws, message):
        try:
            data_list = json.loads(message)
            if not isinstance(data_list, list):
                data_list = [data_list]
            with self.order_books_lock:
                for data in data_list:
                    if data.get("event_type") == "book":
                        asset_id = data["asset_id"]
                        new_bids = [(float(bid["price"]), float(bid["size"])) for bid in data["bids"]]
                        new_asks = [(float(ask["price"]), float(ask["size"])) for ask in data["asks"]]
                        self.order_books[asset_id] = {"bids": new_bids, "asks": new_asks}
                        self.last_update = time.time()
                        self.update_count += 1
                        logger.info(f"Update #{self.update_count} for asset {asset_id}: {len(new_bids)} bids, {len(new_asks)} asks")
                    else:
                        logger.debug(f"Ignored message type: {data.get('event_type')}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def _on_open(self, ws):
        logger.info("WebSocket connection opened")
        self.is_running = True
        subscribe_message = {
            "assets_ids": self.token_ids,
            "type": "market"
        }
        ws.send(json.dumps(subscribe_message))
        logger.debug("Sent subscription message")

    def _on_error(self, ws, error):
        logger.error(f"WebSocket error: {error}")
        self.is_running = False

    def _on_close(self, ws, code, msg):
        logger.warning(f"WebSocket closed: code={code}, msg={msg}")
        self.is_running = False

    def run(self):
        def run_forever():
            while True:
                if not self.is_running:
                    logger.info("Attempting to connect to WebSocket")
                    ws = websocket.WebSocketApp(
                        self.ws_url,
                        on_open=self._on_open,
                        on_message=self._on_message,
                        on_error=self._on_error,
                        on_close=self._on_close
                    )
                    try:
                        ws.run_forever(ping_interval=30, ping_timeout=10)
                    except Exception as e:
                        logger.error(f"WebSocket run failed: {e}")
                    time.sleep(5)  # Wait before reconnecting
                else:
                    time.sleep(1)  # Check again soon

        wst = threading.Thread(target=run_forever)
        wst.daemon = True
        wst.start()
        
        timeout = 10
        start_time = time.time()
        while not self.is_running and time.time() - start_time < timeout:
            time.sleep(0.1)
        if not self.is_running:
            logger.warning("WebSocket did not connect within timeout")

    def get_order_books(self):
        with self.order_books_lock:
            if not self.order_books:
                logger.warning("Order books empty when accessed")
            else:
                logger.debug(f"Returning order books with {len(self.order_books)} assets")
            return self.order_books.copy()

    def wait_for_initial_data(self, timeout=10):
        start_time = time.time()
        while time.time() - start_time < timeout:
            with self.order_books_lock:
                if all(token_id in self.order_books for token_id in self.token_ids):
                    logger.info(f"Initial order book data received for all {len(self.token_ids)} tokens")
                    return True
            time.sleep(0.1)
        logger.warning("Timed out waiting for initial order book data")
        return False