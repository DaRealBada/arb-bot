import websocket  # type: ignore
import os
from dotenv import load_dotenv  # type: ignore

load_dotenv()

# Configuration
WS_URL = "wss://api.kalshi.com/trade-api/ws/v2"  # General Kalshi endpoint
API_KEY = os.getenv('KALSHI_API_KEY')

if not API_KEY:
    raise ValueError("API_KEY not found in .env file")

def on_open(ws):
    print("Successfully connected to Kalshi WebSocket")

def on_message(ws, message):
    print(f"Received: {message}")

def on_error(ws, error):
    print(f"Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print(f"Connection closed: {close_status_code} - {close_msg}")

def connect_websocket():
    headers = {"Authorization": f"Bearer {API_KEY}"}
    print(f"Connecting to {WS_URL} with headers: {headers}")

    ws = websocket.WebSocketApp(
        WS_URL,
        header=headers,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    
    ws.run_forever(ping_interval=10, ping_timeout=8)

if __name__ == "__main__":
    websocket.enableTrace(True)  # Enable tracing
    connect_websocket()