import requests
import json

url = "https://api.elections.kalshi.com/trade-api/v2/events"
params = {
    "event_ticker": "KXELONTWEETS-25MAR28",
    "series_ticker": "KXELONTWEETS",
    "sub_title": "Ending Mar 28, 2025",
    "title": "How many Elon Musk posts on X the week ending on Mar 28, 2025?",
    "collateral_return_type": "MECNET",
    "mutually_exclusive": True,
    "category": "Politics",
    "active": True
}

response = requests.get(url, params=params)
markets = response.json()

# Save to JSON file
with open('event-data.json', 'w') as file:
    json.dump(markets, file, indent=4)

print("Data saved to event-data.json")