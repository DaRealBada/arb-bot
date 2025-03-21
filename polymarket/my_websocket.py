from websocket import WebSocketApp  # Correct import
import json
import threading
from dotenv import load_dotenv
import os
import time

# Debug import (remove after confirmation)
import websocket
print(f"Using websocket from: {websocket.__file__}")
print(f"Version: {websocket.__version__}")

load_dotenv()

WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"

MARKET_DATA = [
    {"conditionId": "0xe667de9434da5c1fa9915f88ba82fc957e05c5f19624648d96856a3d36799d2f", 
     "clobTokenIds": ["62798322524535786524513525677873049907375257479617258254943730718028239887089", 
                      "25126133819089916865108464751652086184303058857837461200709396085257150589689"]}
]

CONDITION_IDS = [MARKET_DATA[0]["conditionId"]]
TOKEN_IDS = MARKET_DATA[0]["clobTokenIds"]

order_books = {}

def on_message(ws, message):
    data = json.loads(message)
    print("Received data:", json.dumps(data, indent=2))
    if data.get("event_type") == "book":
        asset_id = data["asset_id"]
        order_books[asset_id] = {
            "bids": [(float(bid["price"]), float(bid["size"])) for bid in data["buys"]],
            "asks": [(float(ask["price"]), float(ask["size"])) for ask in data["sells"]]
        }
        print(f"\nUpdated order book for asset {asset_id}:")
        print("Bids:", order_books[asset_id]["bids"])
        print("Asks:", order_books[asset_id]["asks"])
    else:
        print("Non-book message received, possibly a subscription response or error.")

def on_error(ws, error):
    print(f"Error details: {error}")
    if hasattr(error, 'args'):
        print(f"Error args: {error.args}")

def on_close(ws, close_status_code, close_msg):
    print(f"Connection closed - Status: {close_status_code}, Message: {close_msg}")

def on_open(ws):
    subscribe_message = {
        "markets": CONDITION_IDS,
        "assets_ids": TOKEN_IDS,
        "type": "market"
    }
    ws.send(json.dumps(subscribe_message))
    print(f"Subscription sent: {json.dumps(subscribe_message, indent=2)}")

def run_websocket():
    ws = WebSocketApp(
        WS_URL,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
        ping_interval=30,  # Send ping every 30 seconds
        ping_timeout=10    # Wait 10 seconds for pong
    )
    ws.run_forever()

if __name__ == "__main__":
    thread = threading.Thread(target=run_websocket)
    thread.start()
    print("WebSocket client started. Listening for market data...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")