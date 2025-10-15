import websocket
import json

def on_message(ws, message):
    print(f"Received: {message}")

def on_open(ws):
    print("Connected!")
    # Try subscribing to one token
    sub = {
        "type": "subscribe",
        "channel": "orderbook",
        "market_id": "YOUR_TOKEN_ID_HERE"
    }
    ws.send(json.dumps(sub))

ws = websocket.WebSocketApp(
    "wss://ws-subscriptions-clob.polymarket.com/ws/market",
    on_message=on_message,
    on_open=on_open
)
ws.run_forever()