import websocket
import json
import ssl

# WebSocket URL
ws_url = "wss://api.elections.kalshi.com/trade-api/ws/v2"

# Replace with your actual API key
api_key = "ae6bd97f-d772-40be-b17e-2e44077c-0d6a-4574-b8c7-d0265fef6323"
headers = {
    "Authorization": f"Bearer {api_key}",
    "accept": "application/json"
}

# File to save data
output_file = "markets-data.json"

# Subscription command
subscription_cmd = {
    "id": 1,
    "cmd": "subscribe",
    "params": {
        "channels": ["ticker"],
        "market_tickers": ["KXELONTWEETS-25MAR28"]
    }
}

# Enable WebSocket debugging
websocket.enableTrace(True)

def on_open(ws):
    print("Connected to Kalshi WebSocket")
    ws.send(json.dumps(subscription_cmd))

def on_message(ws, message):
    data = json.loads(message)
    print("Received:", data)
    if data.get("type") == "subscribed":
        print(f"Subscribed to {data['msg']['channel']} with sid {data['msg']['sid']}")
    elif data.get("type") == "ticker":
        with open(output_file, 'w') as file:
            json.dump(data["msg"], file, indent=4)
        print(f"Ticker data saved to {output_file}")
    elif data.get("type") == "error":
        print(f"Error: {data['msg']}")

def on_error(ws, error):
    print("WebSocket error:", error)

def on_close(ws, close_status_code, close_msg):
    print("WebSocket closed:", close_msg, "Status code:", close_status_code)

# Set up and run WebSocket
print("Headers being sent:", headers)
ws = websocket.WebSocketApp(
    ws_url,
    header=headers,
    on_open=on_open,
    on_message=on_message,
    on_error=on_error,
    on_close=on_close
)

ws.run_forever(
    sslopt={"cert_reqs": ssl.CERT_REQUIRED},
    ping_interval=10,
    ping_timeout=5
)

print("WebSocket connection terminated")