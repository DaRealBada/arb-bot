import websocket
import json
import threading
import time
import logging
from threading import Lock

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class PolymarketClient:
    def __init__(self, token_ids=None):
        self.ws_url = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
        
        # Handle token IDs
        if token_ids is None:
            self.token_ids = []
        elif isinstance(token_ids, dict):
            all_tokens = []
            for m in token_ids.values():
                all_tokens.extend([m['yes_token_id'], m['no_token_id']])
            self.token_ids = all_tokens
            logger.info(f"Loaded {len(all_tokens)} tokens from {len(token_ids)} markets")
        else:
            self.token_ids = token_ids
            logger.info(f"Loaded {len(token_ids)} tokens")
        
        self.order_books = {}
        self.order_books_lock = Lock()
        self.is_running = False
        self.update_count = 0
        self.ws = None

    def _on_open(self, ws):
        logger.info("WebSocket opened. Subscribing to market channel...")
        self.is_running = True
        
        # Subscribe using correct format from docs
        subscription = {
            "assets_ids": self.token_ids,  # Note: assets_ids not asset_ids
            "type": "market"
        }
        
        ws.send(json.dumps(subscription))
        logger.info(f"Subscribed to {len(self.token_ids)} tokens")
        
        # Start ping thread
        def ping_loop():
            while self.is_running:
                try:
                    ws.send("PING")
                    time.sleep(10)
                except:
                    break
        
        ping_thread = threading.Thread(target=ping_loop, daemon=True)
        ping_thread.start()

    def _on_message(self, ws, message):
        try:
            # Handle PONG responses
            if message == "PONG":
                return
            
            data = json.loads(message)
            event_type = data.get("event_type")
            
            if event_type == "book":
                # Full book update
                asset_id = str(data["asset_id"])
                
                # Note: docs say "buys" and "sells" but also show "bids" and "asks"
                # Handle both formats
                bids_raw = data.get("bids", data.get("buys", []))
                asks_raw = data.get("asks", data.get("sells", []))
                
                bids = [(float(b["price"]), float(b["size"])) for b in bids_raw]
                asks = [(float(a["price"]), float(a["size"])) for a in asks_raw]
                
                with self.order_books_lock:
                    self.order_books[asset_id] = {"bids": bids, "asks": asks}
                    self.update_count += 1
                
                logger.info(f"Book update #{self.update_count} for {asset_id[:20]}...: {len(bids)}b {len(asks)}a")
            
            elif event_type == "price_change":
                # Incremental update
                for change in data.get("price_changes", []):
                    asset_id = str(change["asset_id"])
                    
                    # Update best bid/ask if available
                    if "best_bid" in change and "best_ask" in change:
                        with self.order_books_lock:
                            if asset_id not in self.order_books:
                                self.order_books[asset_id] = {"bids": [], "asks": []}
                            
                            # Simple update - replace with best bid/ask
                            # (For full book reconstruction you'd need more logic)
                            best_bid = float(change["best_bid"]) if change["best_bid"] != "0" else 0
                            best_ask = float(change["best_ask"]) if change["best_ask"] != "0" else 0
                            
                            if best_bid > 0:
                                self.order_books[asset_id]["bids"] = [(best_bid, 1.0)]
                            if best_ask > 0:
                                self.order_books[asset_id]["asks"] = [(best_ask, 1.0)]
                
                logger.debug(f"Price change for {len(data.get('price_changes', []))} assets")
            
            elif event_type == "last_trade_price":
                # Just log trade events
                logger.debug(f"Trade: {data.get('asset_id', 'unknown')[:20]}... @ {data.get('price')}")
            
            else:
                logger.debug(f"Unknown event type: {event_type}")
        
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            logger.debug(f"Message was: {message[:200]}...")

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
                    logger.info("Connecting to WebSocket...")
                    self.ws = websocket.WebSocketApp(
                        self.ws_url,
                        on_open=self._on_open,
                        on_message=self._on_message,
                        on_error=self._on_error,
                        on_close=self._on_close,
                    )
                    try:
                        self.ws.run_forever(ping_interval=30, ping_timeout=10)
                    except Exception as e:
                        logger.error(f"WebSocket failed: {e}")
                    
                    logger.info("Reconnecting in 5 seconds...")
                    time.sleep(5)
                else:
                    time.sleep(1)
        
        thread = threading.Thread(target=run_forever, daemon=True)
        thread.start()
        
        # Wait for connection
        timeout = 10
        start = time.time()
        while not self.is_running and time.time() - start < timeout:
            time.sleep(0.1)
        
        if not self.is_running:
            logger.warning("WebSocket did not connect within timeout")

    def get_order_books(self):
        with self.order_books_lock:
            return self.order_books.copy()

    def wait_for_initial_data(self, timeout=60):
        start = time.time()
        while time.time() - start < timeout:
            with self.order_books_lock:
                if len(self.order_books) >= len(self.token_ids) * 0.8:  # 80% received
                    logger.info(f"Initial data received for {len(self.order_books)}/{len(self.token_ids)} tokens")
                    return True
            time.sleep(0.1)
        
        with self.order_books_lock:
            received = len(self.order_books)
        
        logger.error(f"Timeout: received {received}/{len(self.token_ids)} orderbooks")
        return received > 0  # Return True if we got at least some data