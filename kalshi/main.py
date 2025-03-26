import requests
import json
import time

# Market details
event_ticker = "KXELONTWEETS-25MAR28"

# Kalshi API endpoint
PUBLIC_API_URL = "https://api.elections.kalshi.com/trade-api/v2"

def get_markets():
    """Get all markets for the given event."""
    url = f"{PUBLIC_API_URL}/markets"
    params = {
        "event_ticker": event_ticker,
        "limit": 1000
    }
    headers = {"accept": "application/json"}
    
    response = requests.get(url, headers=headers, params=params)
    return response.json()

def get_orderbook(market_id):
    """Get orderbook for a specific market."""
    url = f"{PUBLIC_API_URL}/markets/{market_id}/orderbook"
    headers = {"accept": "application/json"}
    
    response = requests.get(url, headers=headers)
    return response.json()

def display_orderbook(orderbook):
    """Display the orderbook in a readable format."""
    print("\n===== ORDERBOOK =====")
    
    # Display asks (sell orders) from highest to lowest price
    if "asks" in orderbook and orderbook["asks"]:
        print("\nASKS (Sell Orders):")
        for ask in sorted(orderbook["asks"], key=lambda x: float(x.get("price", 0)), reverse=True):
            print(f"Price: ${ask.get('price', 'N/A')} | Size: {ask.get('size', 'N/A')}")
    else:
        print("No asks available")
    
    # Display bids (buy orders) from highest to lowest price
    if "bids" in orderbook and orderbook["bids"]:
        print("\nBIDS (Buy Orders):")
        for bid in sorted(orderbook["bids"], key=lambda x: float(x.get("price", 0)), reverse=True):
            print(f"Price: ${bid.get('price', 'N/A')} | Size: {bid.get('size', 'N/A')}")
    else:
        print("No bids available")

def monitor_orderbook():
    """Main function to monitor the orderbook."""
    try:
        # Get all markets for the event
        print(f"Fetching markets for event: {event_ticker}")
        markets_data = get_markets()
        
        # Find markets containing our event ticker
        relevant_markets = []
        for market in markets_data.get("markets", []):
            if event_ticker in market.get("ticker", ""):
                relevant_markets.append({
                    "id": market.get("id"),
                    "ticker": market.get("ticker"),
                    "title": market.get("title")
                })
        
        # Display available markets
        print(f"\nFound {len(relevant_markets)} markets for this event:")
        for i, market in enumerate(relevant_markets):
            print(f"{i+1}. {market['ticker']} - {market['title']}")
        
        # Select market or use default
        if len(relevant_markets) > 1:
            choice = input("\nEnter market number to monitor (or press Enter for first market): ")
            index = 0 if choice == "" else int(choice) - 1
            
            if index < 0 or index >= len(relevant_markets):
                print("Invalid choice, using first market")
                index = 0
        else:
            index = 0
        
        # Get selected market
        selected_market = relevant_markets[index]
        print(f"\nMonitoring orderbook for: {selected_market['ticker']} - {selected_market['title']}")
        
        # Continuously monitor orderbook
        print("\nPress Ctrl+C to exit\n")
        
        while True:
            # Get orderbook data
            orderbook = get_orderbook(selected_market["id"])
            
            # Display orderbook
            display_orderbook(orderbook)
            
            # Wait before checking again
            print("\nUpdating in 5 seconds...")
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    monitor_orderbook()