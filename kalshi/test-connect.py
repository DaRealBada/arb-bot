import os
import json
import asyncio
import websockets
import ssl
import signal
from dotenv import load_dotenv
import requests
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Kalshi API credentials
KALSHI_API_KEY = os.getenv('KALSHI_API_KEY')
KALSHI_SECRET = os.getenv('KALSHI_PRIVATE_KEY')

# Kalshi API URLs
KALSHI_WS_URL = "wss://api.elections.kalshi.com/trade-api/ws/v2"
KALSHI_API_URL = "https://api.elections.kalshi.com/trade-api/v2"

# Market details
EVENT_TICKER = "KXELONTWEETS-25MAR28"

# This will store our current view of the orderbooks
orderbooks = {}

async def get_markets_for_event():
    """Get all markets for a specific event using the REST API"""
    endpoint = f"{KALSHI_API_URL}/events/{EVENT_TICKER}/markets"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {KALSHI_API_KEY}"
    }
    
    try:
        response = requests.get(endpoint, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        if 'markets' in data:
            return [market['ticker'] for market in data['markets']]
        else:
            logger.error(f"Unexpected response format: {data}")
            return []
    except Exception as e:
        logger.error(f"Error fetching markets: {e}")
        return []

async def process_orderbook_snapshot(message):
    """Process orderbook snapshot messages"""
    market_ticker = message['msg']['market_ticker']
    orderbooks[market_ticker] = message['msg']
    logger.info(f"Updated orderbook for {market_ticker}")

async def process_orderbook_delta(message):
    """Process orderbook delta messages"""
    market_ticker = message['msg']['market_ticker']
    if market_ticker not in orderbooks:
        logger.warning(f"Received delta for unknown market: {market_ticker}")
        return
    
    side = message['msg']['side']
    price = message['msg']['price']
    delta = message['msg']['delta']
    
    # Update the orderbook
    if side not in orderbooks[market_ticker]:
        orderbooks[market_ticker][side] = []
    
    # Find if this price level already exists
    updated = False
    for i, level in enumerate(orderbooks[market_ticker][side]):
        if level[0] == price:
            # Update existing price level
            new_quantity = level[1] + delta
            if new_quantity <= 0:
                # Remove the price level if quantity becomes zero or negative
                orderbooks[market_ticker][side].pop(i)
            else:
                # Update the quantity
                orderbooks[market_ticker][side][i] = [price, new_quantity]
            updated = True
            break
    
    # If this is a new price level with positive quantity
    if not updated and delta > 0:
        orderbooks[market_ticker][side].append([price, delta])
        # Sort the levels - ascending for yes, descending for no
        if side == "yes":
            orderbooks[market_ticker][side].sort(key=lambda x: x[0])
        else:
            orderbooks[market_ticker][side].sort(key=lambda x: x[0], reverse=True)
    
    logger.info(f"Updated {side} side for {market_ticker} at price {price} with delta {delta}")

async def display_orderbooks():
    """Display current state of orderbooks for all markets"""
    while True:
        if orderbooks:
            for market, book in orderbooks.items():
                print(f"\n{'='*60}")
                print(f"Market: {market}")
                print(f"{'='*60}")
                
                print("YES side (bids):")
                if 'yes' in book and book['yes']:
                    for price, quantity in book['yes']:
                        print(f"  Price: ${price/100:.2f} - Quantity: {quantity}")
                else:
                    print("  No bids")
                
                print("\nNO side (asks):")
                if 'no' in book and book['no']:
                    for price, quantity in book['no']:
                        print(f"  Price: ${price/100:.2f} - Quantity: {quantity}")
                else:
                    print("  No asks")
        else:
            print("No orderbook data received yet")
        
        # Update every 5 seconds
        await asyncio.sleep(5)

async def handle_websocket_messages(websocket):
    """Process incoming websocket messages"""
    subscription_count = 0
    
    try:
        async for message in websocket:
            data = json.loads(message)
            msg_type = data.get('type')
            
            if msg_type == 'subscribed':
                subscription_count += 1
                logger.info(f"Successfully subscribed to channel: {data.get('msg', {}).get('channel')}")
            
            elif msg_type == 'orderbook_snapshot':
                await process_orderbook_snapshot(data)
            
            elif msg_type == 'orderbook_delta':
                await process_orderbook_delta(data)
            
            elif msg_type == 'error':
                logger.error(f"Received error: {data}")
    
    except Exception as e:
        logger.error(f"Error handling websocket message: {e}")

async def websocket_client():
    """Main function to handle the websocket connection and subscription"""
    # Get all markets for the event
    market_tickers = await get_markets_for_event()
    if not market_tickers:
        logger.error(f"No markets found for event {EVENT_TICKER}")
        return
    
    logger.info(f"Found {len(market_tickers)} markets for event {EVENT_TICKER}: {market_tickers}")
    
    # Create SSL context for secure connection
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    try:
        async with websockets.connect(
            KALSHI_WS_URL, 
            ssl=ssl_context, 
            extra_headers={"Authorization": f"Bearer {KALSHI_API_KEY}"}
        ) as websocket:
            logger.info("Connected to Kalshi websocket")
            
            # Subscribe to orderbook_delta channel for all markets in the event
            cmd_id = 1
            subscribe_cmd = {
                "id": cmd_id,
                "cmd": "subscribe",
                "params": {
                    "channels": ["orderbook_delta"],
                    "market_tickers": market_tickers
                }
            }
            await websocket.send(json.dumps(subscribe_cmd))
            logger.info(f"Sent subscription command: {subscribe_cmd}")
            
            # Start displaying orderbooks in the background
            display_task = asyncio.create_task(display_orderbooks())
            
            # Process incoming messages
            await handle_websocket_messages(websocket)
            
            # Cancel the display task
            display_task.cancel()
            try:
                await display_task
            except asyncio.CancelledError:
                pass
            
    except Exception as e:
        logger.error(f"Websocket connection error: {e}")

def handle_exit(signum, frame):
    """Handle clean exit on termination signals"""
    logger.info("Received exit signal. Shutting down...")
    # Let the asyncio loop handle cleanup
    raise KeyboardInterrupt

if __name__ == "__main__":
    # Register signal handlers for clean shutdown
    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)
    
    try:
        # Run the main function
        asyncio.run(websocket_client())
    except KeyboardInterrupt:
        logger.info("Program terminated by user")