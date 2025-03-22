import websocket # type: ignore
import json
import threading
import time

# WebSocket URL remains the same
WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"

# Your condition ID and token IDs
CONDITION_ID = "0x7e444ac87ee6e0239207aadd7a9ffd6f7f308fa5dcc2e93bd9ea78290288e086"
TOKEN_IDS = [
    "85329773272943166129677849548761904296702187239360845432685251972069093480583",
    "63085860338801042630323550570156921700404382755089007440212233804977972103126",
]

# Global dictionary to store the latest order book for each asset
order_books = {}

def on_message(ws, message):
    """Handle incoming WebSocket messages."""
    try:
        data = json.loads(message)
        print("Received data:", json.dumps(data, indent=2))
        
        # Handle book updates
        if data.get("event_type") == "book":
            asset_id = data["asset_id"]
            order_books[asset_id] = {
                "bids": [(float(bid["price"]), float(bid["size"])) for bid in data["buys"]],
                "asks": [(float(ask["price"]), float(ask["size"])) for ask in data["sells"]]
            }
            print(f"\nUpdated order book for asset {asset_id}:")
            print("Bids:", order_books[asset_id]["bids"])
            print("Asks:", order_books[asset_id]["asks"])
        
        # Handle price change events
        elif data.get("event_type") == "price_change":
            asset_id = data["asset_id"]
            print(f"\nPrice change for asset {asset_id}:")
            for change in data["changes"]:
                print(f"Side: {change['side']}, Price: {change['price']}, Size: {change['size']}")
        
        # Handle tick size change events
        elif data.get("event_type") == "tick_size_change":
            asset_id = data["asset_id"]
            print(f"\nTick size change for asset {asset_id}:")
            print(f"Old tick size: {data['old_tick_size']}, New tick size: {data['new_tick_size']}")
            
    except Exception as e:
        print(f"Error processing message: {e}")
        print(f"Raw message: {message}")

def on_error(ws, error):
    """Handle WebSocket errors."""
    print(f"Error: {error}")

def on_close(ws, close_status_code, close_msg):
    """Handle WebSocket closure."""
    print(f"Connection closed. Status code: {close_status_code}, Message: {close_msg}")
    print("Attempting to reconnect in 5 seconds...")
    time.sleep(5)
    start_websocket()

def on_open(ws):
    """Subscribe to the market channel on connection."""
    # According to docs, for market channel, we only need to include assets_ids
    subscribe_message = {
        "assets_ids": TOKEN_IDS,
        "type": "market"
    }
    
    print("Sending subscription message:", json.dumps(subscribe_message, indent=2))
    ws.send(json.dumps(subscribe_message))
    print(f"Subscribed to assets: {TOKEN_IDS}")

def start_websocket():
    """Start a new WebSocket connection."""
    print("Starting WebSocket connection...")
    websocket.enableTrace(True)
    
    ws = websocket.WebSocketApp(
        WS_URL,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws.run_forever(ping_interval=30, ping_timeout=10)

def run_websocket():
    """Run the WebSocket client with reconnection logic."""
    while True:
        try:
            start_websocket()
        except Exception as e:
            print(f"Error in WebSocket connection: {e}")
            print("Retrying in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    # Run the WebSocket in a separate thread
    thread = threading.Thread(target=run_websocket)
    thread.daemon = True
    thread.start()
    print("WebSocket client started. Listening for market data...")
    
    # Keep the main thread alive
    try:
        while True:
            user_input = input("Press 'q' and Enter to quit: ")
            if user_input.lower() == 'q':
                break
    except KeyboardInterrupt:
        print("Shutting down...")
    print("Program terminated")