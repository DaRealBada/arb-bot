import asyncio
import websockets
import json
import logging
import os
import base64
import hmac
import hashlib
import time
from dotenv import load_dotenv
import requests

# Load environment variables from .env file
load_dotenv()

class KalshiWebSocketClient:
    def __init__(self, api_key, private_key, event_ticker="KXELONTWEETS-25MAR28"):
        self.websocket_url = "wss://api.elections.kalshi.com/trade-api/ws/v2"
        self.rest_base_url = "https://api.elections.kalshi.com/trade-api/v2"
        self.api_key = api_key
        self.private_key = private_key
        self.event_ticker = event_ticker
        self.market_ticker = None
        
        logging.basicConfig(level=logging.DEBUG, 
                          format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

    def generate_signature(self, timestamp):
        """Generate signature as per REST API pattern (assumed same for WS)."""
        message = f"{timestamp}{self.api_key}"
        signature = hmac.new(
            self.private_key.encode('utf-8'), 
            message.encode('utf-8'), 
            hashlib.sha256
        ).digest()
        return base64.b64encode(signature).decode('utf-8')

    def fetch_markets_by_event(self):
        """Fetch markets for the event ticker via REST API."""
        try:
            timestamp = int(time.time())
            signature = self.generate_signature(timestamp)

            headers = {
                'X-API-Key': self.api_key,
                'X-Timestamp': str(timestamp),
                'X-Signature': signature
            }

            params = {
                "event_ticker": self.event_ticker,
                "limit": 1000
            }

            response = requests.get(
                f"{self.rest_base_url}/markets",
                headers=headers,
                params=params
            )

            if response.status_code == 200:
                markets = response.json().get("markets", [])
                if not markets:
                    self.logger.warning(f"No markets found for event ticker: {self.event_ticker}")
                    return None
                tickers = [market["ticker"] for market in markets]
                self.logger.info(f"Markets found for event {self.event_ticker}:")
                for ticker in tickers:
                    self.logger.info(ticker)
                return tickers
            else:
                self.logger.error(f"Failed to fetch markets: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            self.logger.error(f"Error fetching markets: {e}")
            traceback.print_exc()
            return None

    async def connect_websocket(self, max_retries=3):
        """Connect to WebSocket and subscribe to orderbook_delta channel."""
        tickers = self.fetch_markets_by_event()
        if not tickers:
            self.logger.error("No valid market tickers available. Exiting.")
            return
        self.market_ticker = tickers[0]  # Use first market ticker
        self.logger.info(f"Selected market ticker: {self.market_ticker}")

        for attempt in range(max_retries):
            try:
                timestamp = int(time.time())  # Fresh timestamp
                signature = self.generate_signature(timestamp)

                headers = {
                    'X-API-Key': self.api_key,
                    'X-Timestamp': str(timestamp),
                    'X-Signature': signature
                }

                self.logger.debug(f"Attempt {attempt + 1}/{max_retries} - Headers: {headers}")

                async with websockets.connect(
                    self.websocket_url,
                    extra_headers=headers,
                    ping_interval=10,  # Client-side heartbeat every 10s
                    ping_timeout=20
                ) as websocket:
                    self.logger.info("WebSocket connection established successfully!")

                    # Subscribe to orderbook_delta channel
                    subscription_message = {
                        "id": 1,
                        "cmd": "subscribe",
                        "params": {
                            "channels": ["orderbook_delta"],
                            "market_tickers": [self.market_ticker]
                        }
                    }
                    await websocket.send(json.dumps(subscription_message))
                    self.logger.info(f"Sent subscription: {json.dumps(subscription_message)}")

                    # Listen for messages
                    while True:
                        try:
                            message = await websocket.recv()
                            data = json.loads(message)
                            self.process_message(data)
                        except websockets.ConnectionClosed:
                            self.logger.error("WebSocket connection closed unexpectedly")
                            break

            except websockets.exceptions.InvalidStatusCode as e:
                self.logger.error(f"WebSocket connection rejected: HTTP {e.status_code}")
                self.logger.debug(f"Response headers: {e.headers}")
                # Attempt to fetch the response body manually if possible
                if hasattr(e, 'response') and e.response:
                    try:
                        body = await e.response.read()
                        self.logger.debug(f"Response body: {body.decode('utf-8')}")
                    except Exception as read_err:
                        self.logger.debug(f"Could not read response body: {read_err}")
                if attempt < max_retries - 1:
                    self.logger.info("Retrying with fresh timestamp in 2 seconds...")
                    await asyncio.sleep(2)
                else:
                    self.logger.error("Max retries reached. Check credentials or signature format.")
                    break
            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")
                traceback.print_exc()
                break

    def process_message(self, data):
        """Process incoming WebSocket messages."""
        self.logger.debug(f"Received message: {json.dumps(data, indent=2)}")
        if data.get("type") == "subscribed":
            self.logger.info(f"Successfully subscribed to channel: {data['msg']['channel']} (sid: {data['msg']['sid']})")
        elif data.get("type") == "orderbook_snapshot":
            self.logger.info(f"Orderbook snapshot for {data['msg']['market_ticker']}:")
            self.logger.info(f"Yes: {data['msg'].get('yes', [])}")
            self.logger.info(f"No: {data['msg'].get('no', [])}")
        elif data.get("type") == "orderbook_delta":
            self.logger.info(f"Orderbook delta for {data['msg']['market_ticker']}: "
                           f"Price={data['msg']['price']}, Delta={data['msg']['delta']}, Side={data['msg']['side']}")
        elif data.get("type") == "error":
            self.logger.error(f"Error from server: {data['msg']['msg']} (code: {data['msg']['code']})")
        else:
            self.logger.info(f"Unhandled message type: {data.get('type')}")

def main():
    API_KEY = os.getenv('KALSHI_API_KEY')
    PRIVATE_KEY = os.getenv('KALSHI_PRIVATE_KEY')

    if not API_KEY or not PRIVATE_KEY:
        print("Error: KALSHI_API_KEY or KALSHI_PRIVATE_KEY not found in .env file")
        return

    client = KalshiWebSocketClient(API_KEY, PRIVATE_KEY)
    asyncio.run(client.connect_websocket())

if __name__ == "__main__":
    main()