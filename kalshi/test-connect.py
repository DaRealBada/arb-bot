import asyncio
import websockets
import json
import requests
import os

from dotenv import load_dotenv #add this import.

load_dotenv() # Load environment variables from .env

KALSHI_WS_URL = "wss://api.elections.kalshi.com/trade-api/ws/v2"
KALSHI_API_URL = "https://api.elections.kalshi.com/trade-api/v2/markets"

async def connect_and_subscribe(api_key, event_ticker):
    """Connects to the Kalshi websocket and subscribes to orderbook data."""
    try:
        async with websockets.connect(KALSHI_WS_URL, extra_headers={"Authorization": f"Bearer {api_key}"}) as websocket:
            print("Connected to Kalshi websocket.")

            # Get market tickers for the event
            market_tickers = await get_market_tickers(event_ticker)
            if not market_tickers:
                print(f"No markets found for event ticker: {event_ticker}")
                return

            # Subscribe to orderbook_delta for each market
            subscribe_command = {
                "id": 1,
                "cmd": "subscribe",
                "params": {
                    "channels": ["orderbook_delta"],
                    "market_tickers": market_tickers,
                },
            }
            await websocket.send(json.dumps(subscribe_command))
            print(f"Subscribed to orderbook_delta for {len(market_tickers)} markets.")

            # Handle incoming messages
            while True:
                message = await websocket.recv()
                await process_message(message)

    except websockets.exceptions.ConnectionClosedError as e:
        print(f"Connection closed unexpectedly: {e}")
        # Implement reconnection logic here if needed.
    except Exception as e:
        print(f"An error occurred: {e}")

async def get_market_tickers(event_ticker):
    """Retrieves market tickers for a given event ticker from the Kalshi API."""
    params = {
        "event_ticker": event_ticker,
        "limit": 1000,
    }
    try:
        response = requests.get(KALSHI_API_URL, params=params)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        markets = response.json().get("markets", [])
        return [market["ticker"] for market in markets]
    except requests.exceptions.RequestException as e:
        print(f"Error fetching market tickers: {e}")
        return []

async def process_message(message):
    """Processes incoming websocket messages and extracts orderbook data."""
    try:
        data = json.loads(message)
        if data.get("type") == "orderbook_snapshot":
            market_ticker = data["msg"]["market_ticker"]
            yes_orders = data["msg"].get("yes", [])
            no_orders = data["msg"].get("no", [])

            top_yes_bid = yes_orders[-1][0] if yes_orders else None #last yes order is the highest bid.
            top_no_bid = no_orders[-1][0] if no_orders else None #last no order is the highest bid.
            top_yes_ask = yes_orders[0][0] if yes_orders else None #first yes order is the lowest ask
            top_no_ask = no_orders[0][0] if no_orders else None #first no order is the lowest ask
            print(f"Market: {market_ticker}")
            print(f"  Yes Bid: {top_yes_bid}, Yes Ask: {top_yes_ask}")
            print(f"  No Bid: {top_no_bid}, No Ask: {top_no_ask}")

        elif data.get("type") == "orderbook_delta":
            market_ticker = data["msg"]["market_ticker"]
            price = data["msg"]["price"]
            delta = data["msg"]["delta"]
            side = data["msg"]["side"]
            print(f"Orderbook Delta: {market_ticker}, Side: {side}, Price: {price}, Delta: {delta}")

        elif data.get("type") == "subscribed":
            print(f"Subscription successful: {data['msg']['channel']}")
        elif data.get("type") == "error":
            print(f"Error: {data}")
        else:
            print(f"Received message: {data}")

    except json.JSONDecodeError:
        print(f"Received invalid JSON: {message}")
    except KeyError as e:
        print(f"Missing key in message: {e}")
    except Exception as e:
        print(f"Error processing message: {e}")

async def main():
    """Main function to start the websocket connection."""
    api_key = os.environ.get("KALSHI_API_KEY")
    event_ticker = "KXELONTWEETS-25MAR28"

    if not api_key:
        print("Error: KALSHI_API_KEY environment variable not set.")
        return

    await connect_and_subscribe(api_key, event_ticker)

if __name__ == "__main__":
    asyncio.run(main())