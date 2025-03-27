import requests
import json
import time

url = "https://api.elections.kalshi.com/trade-api/v2/markets"
params = {"event_ticker": "KXELONTWEETS-25MAR28", "limit": 1000}
headers = {"accept": "application/json"}

while True:
    response = requests.get(url, headers=headers, params=params)
    markets_data = response.json()
    with open('polling-rest.json', 'w') as file:
        json.dump(markets_data, file, indent=4)
    print("Data saved to markets-data.json")
    time.sleep(10)  # Poll every 60 seconds