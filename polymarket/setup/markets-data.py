import requests
import json

url = "https://gamma-api.polymarket.com/events"
params = {
    "limit": 20,
    "active": True, 
    "slug": "elon-musk-of-tweets-mar-21-28"
}

response = requests.get(url, params=params)
markets = response.json()

# Save to JSON file
with open('markets_data.json', 'w') as file:
    json.dump(markets, file, indent=4)

print("Data saved to markets_data.json")