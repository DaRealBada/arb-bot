import asyncio
import json
import base64
import time
from dotenv import load_dotenv
import os
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
import websockets

# Load environment variables
load_dotenv()

# Get credentials from .env
KEYID = os.getenv("KALSHI_API_KEY")  # Your KEYID
KEYFILE = os.getenv("KALSHI_PRIVATE_KEY")  # Path to rsa-key.pem

# Load the private key
try:
    with open(KEYFILE, "rb") as key_file:
        private_key = serialization.load_pem_private_key(key_file.read(), password=None)
except FileNotFoundError:
    raise FileNotFoundError(f"Private key file not found at {KEYFILE}")

# WebSocket URL (production environment)
WS_URL = "wss://api.elections.kalshi.com/trade-api/ws/v2"

# Generate authentication headers
def get_auth_headers(key_id, private_key, path="/trade-api/ws/v2"):
    current_time_ms = int(time.time() * 1000)
    timestamp_str = str(current_time_ms)
    message = timestamp_str + "GET" + path
    signature = private_key.sign(
        message.encode('utf-8'),
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH),
        hashes.SHA256()
    )
    return {
        "Content-Type": "application/json",
        "KALSHI-ACCESS-KEY": key_id,
        "KALSHI-ACCESS-SIGNATURE": base64.b64encode(signature).decode('utf-8'),
        "KALSHI-ACCESS-TIMESTAMP": timestamp_str,
    }

# Maintain order book state
order_books = {}

def update_order_book(ticker, snapshot=None, delta=None):
    if ticker not in order_books:
        order_books[ticker] = {"yes": {}, "no": {}}
    
    if snapshot:
        # Reset order book with snapshot data
        order_books[ticker]["yes"] = {price: qty for price, qty in snapshot.get("yes", [])}
        order_books[ticker]["no"] = {price: qty for price, qty in snapshot.get("no", [])}
    elif delta:
        # Apply delta update
        side = delta["side"]
        price = delta["price"]
        delta_qty = delta["delta"]
        current_qty = order_books[ticker][side].get(price, 0)
        new_qty = current_qty + delta_qty
        if new_qty <= 0:
            order_books[ticker][side].pop(price, None)
        else:
            order_books[ticker][side][price] = new_qty

def print_order_book(ticker):
    print(f"\nOrder Book for {ticker}:")
    print("Yes Bids:", sorted([[price, qty] for price, qty in order_books[ticker]["yes"].items()], reverse=True))
    print("Yes Asks:", sorted([[price, qty] for price, qty in order_books[ticker]["yes"].items()]))
    print("No Bids:", sorted([[price, qty] for price, qty in order_books[ticker]["no"].items()], reverse=True))
    print("No Asks:", sorted([[price, qty] for price, qty in order_books[ticker]["no"].items()]))

# WebSocket connection
async def connect_websocket():
    headers = get_auth_headers(KEYID, private_key)
    try:
        async with websockets.connect(WS_URL, extra_headers=headers, ping_interval=10) as websocket:
            print("WebSocket connection established")
            
            # List of market tickers from the event
            market_tickers = [
                "KXELONTWEETS-25MAR28-849",
                "KXELONTWEETS-25MAR28-824.5",
                "KXELONTWEETS-25MAR28-774.5"
            ]
            
            # Subscribe to orderbook_delta channel
            subscription_message = json.dumps({
                "id": 1,
                "cmd": "subscribe",
                "params": {
                    "channels": ["orderbook_delta"],
                    "market_tickers": market_tickers
                }
            })
            print(f"Sending subscription: {subscription_message}")
            await websocket.send(subscription_message)
            
            # Listen for messages
            async for message in websocket:
                data = json.loads(message)
                if data.get("type") == "subscribed":
                    print(f"Subscribed to channel: {data['msg']['channel']} with sid: {data['msg']['sid']}")
                elif data.get("type") == "error":
                    print(f"Error received: {data}")
                elif data.get("type") == "orderbook_snapshot":
                    ticker = data["msg"]["market_ticker"]
                    update_order_book(ticker, snapshot=data["msg"])
                    print(f"\nReceived snapshot for {ticker}")
                    print_order_book(ticker)
                elif data.get("type") == "orderbook_delta":
                    ticker = data["msg"]["market_ticker"]
                    update_order_book(ticker, delta=data["msg"])
                    print(f"\nReceived delta update for {ticker}")
                    print_order_book(ticker)
                else:
                    print("Received:", data)
                    
    except Exception as e:
        print(f"Error: {e}")

# Run the WebSocket
asyncio.run(connect_websocket())