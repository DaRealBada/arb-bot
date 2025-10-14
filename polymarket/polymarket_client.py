import websocket
import json
import threading
import time
import logging
from threading import Lock

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class PolymarketClient:
    def __init__(self):
        # --- NEW URL: Using the official Real-Time Data Socket (RTDS) endpoint ---
        self.ws_url = "wss://ws-live-data.polymarket.com" 
        
        # --- CLEANED: Only keep the 5 Fed Rate Cuts tokens (Market ID: 519782) ---
        self.token_ids = [
            "13233824300645009841804910385973797437703578792070081033285141695415842858595", # 0 cuts
            "10045187747802872322312675685790615591321458882585258288544975549723385759902", # 1 cut
            "14093902307297906954201103723329972551406567362846995641774213702167306236968", # 2 cuts
            "15923832924375086576839356391965581692257002061291888365842600290947761007971", # 3 cuts
            "16838383218556485897042048995392576326164221761623916295744211186717523171887", # 4 cuts
        ]

        self.order_books = {}
        self.order_books_lock = Lock()
        self.is_running = False
        self.last_update = 0
        self.update_count = 0 
        self._last_status_print = 0 # Initialized for safe status printing

    def _on_open(self, ws):
        # ... (on_open logic is correct and remains the same)
        logger.info("WebSocket connection opened. Subscribing to CLOB markets...")
        self.is_running = True
        
        subscription_message = {
            "method": "subscribe",
            "topic": "clob_market",
            "type": "agg_orderbook",
            "filters": self.token_ids,
            "id": f"sub-{int(time.time() * 1000)}" 
        }
        
        try:
            ws.send(json.dumps(subscription_message))
            logger.info(f"Subscribed to {len(self.token_ids)} tokens for agg_orderbook.")
        except Exception as e:
            logger.error(f"Failed to send subscription message: {e}")

    # ... (_on_message, _on_error, _on_close, run, get_order_books remain the same)
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
                        logger.debug(f"Ignored message type: {data.get('type') or data.get('event_type')}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

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
                    logger.info("Attempting to connect to WebSocket...")
                    ws_app = websocket.WebSocketApp(
                        self.ws_url,
                        on_open=self._on_open,
                        on_message=self._on_message,
                        on_error=self._on_error,
                        on_close=self._on_close,
                    )
                    try:
                        ws_app.run_forever(ping_interval=30, ping_timeout=10)
                    except Exception as e:
                        logger.error(f"WebSocket run failed: {e}")
                    time.sleep(5)
                else:
                    time.sleep(1)

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

    def wait_for_initial_data(self, timeout=30):
        start_time = time.time()
        self._last_status_print = 0 

        while time.time() - start_time < timeout:
            with self.order_books_lock:
                missing_tokens = [
                    token_id 
                    for token_id in self.token_ids 
                    if token_id not in self.order_books
                ]

                if not missing_tokens:
                    logger.info(f"Initial order book data received for all {len(self.token_ids)} tokens")
                    return True
                
                # Corrected logic to print status every 5 seconds
                current_time = time.time()
                if current_time - self._last_status_print > 5:
                    logger.warning(f"Still waiting for {len(missing_tokens)} tokens after {int(current_time - start_time)}s. Missing: {missing_tokens[:2]}...")
                    self._last_status_print = current_time

            time.sleep(0.1)

        # FINAL check on timeout
        missing_tokens = [
            token_id 
            for token_id in self.token_ids 
            if token_id not in self.order_books
        ]
        
        if missing_tokens:
            logger.error(f"Timed out. Missing tokens: {missing_tokens}") 
        else:
            logger.warning("Timed out waiting for initial order book data")
        
        return False