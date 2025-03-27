import requests
import json

# API endpoint for markets (not events)
url = "https://api.elections.kalshi.com/trade-api/v2/markets"

# Parameters for the markets API
params = {
    "event_ticker": "KXELONTWEETS-25MAR28",  # You can filter by event ticker
    "limit": 1000  # Maximum number of results per page
}

headers = {"accept": "application/json"}

# Make the request
response = requests.get(url, headers=headers, params=params)
markets_data = response.json()

# Save to JSON file
with open('markets-data.json', 'w') as file:
    json.dump(markets_data, file, indent=4)

print("Data saved to markets-data.json")
