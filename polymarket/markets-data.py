import requests
import json

url = "https://gamma-api.polymarket.com/events"
params = {
    "limit": 20,
    "active": True,
    "end_date_min": "2025-03-21T00:00:00Z",
    "end_date_max": "2025-03-21T23:59:59Z",    
    "slug": "elon-musk-of-tweets-mar-14-21"
}

response = requests.get(url, params=params)
markets = response.json()

# Save to JSON file
with open('markets_data.json', 'w') as file:
    json.dump(markets, file, indent=4)

print("Data saved to markets_data.json")