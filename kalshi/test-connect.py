import asyncio
import json
import base64
import time  # Added this import
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

# WebSocket connection
async def connect_websocket():
    headers = get_auth_headers(KEYID, private_key)
    try:
        async with websockets.connect(WS_URL, extra_headers=headers, ping_interval=10) as websocket:
            print("WebSocket connection established")
            # Subscribe to a ticker channel
            await websocket.send(json.dumps({
                "id": 1,
                "cmd": "subscribe",
                "params": {"channels": ["ticker"], "market_tickers": ["KXELONTWEETS-25MAR28"]}
            }))
            # Listen for messages
            async for message in websocket:
                data = json.loads(message)
                print("Received:", data)
    except Exception as e:
        print(f"Error: {e}")

# Run the WebSocket
asyncio.run(connect_websocket())