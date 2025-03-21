import websocket
import json
import time
import threading

# Your provided IDs (assuming validated by REST API)
CONDITION_ID = "0xe667de9434da5c1fa9915f88ba82fc957e05c5f19624648d96856a3d36799d2f"
TOKEN_IDS = [
    "62798322524535786524513525677873049907375257479617258254943730718028239887089",
    "25126133819089916865108464751652086184303058857837461200709396085257150589689"
]

def on_message(ws, message):
    print(f"Received: {message}")

def on_error(ws, error):
    print(f"Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print(f"Connection closed: {close_status_code} - {close_msg}")

def keep_alive(ws):
    while True:
        try:
            time.sleep(30)
            ws.send("ping")
            print("Sent ping")
        except Exception as e:
            print(f"Ping failed: {e}")
            break

def on_open(ws):
    print("Connection opened")
    # Subscription payload
    subscribe_payload = {
        "type": "market",
        "markets": [CONDITION_ID],
        "assets_ids": TOKEN_IDS
    }
    print("Sending subscription:", json.dumps(subscribe_payload, indent=2))
    ws.send(json.dumps(subscribe_payload))
    # Start keep-alive thread
    threading.Thread(target=keep_alive, args=(ws,), daemon=True).start()

ws_url = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
websocket.enableTrace(True)  # Enable detailed WebSocket logging
ws = websocket.WebSocketApp(ws_url,
                            on_open=on_open,
                            on_message=on_message,
                            on_error=on_error,
                            on_close=on_close)

ws.run_forever()