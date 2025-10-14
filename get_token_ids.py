import requests
import json
import sys

# The market slug you want to fetch
MARKET_SLUG = "fed-decision-in-october"  # <<< UPDATED TO NEW SLUG

# FIXED: Correct URL format (no "slug=" in the path)
url = f"https://gamma-api.polymarket.com/markets/{MARKET_SLUG}"

print(f"Fetching data for market: {MARKET_SLUG}")
print(f"URL: {url}")

try:
    response = requests.get(url)
    response.raise_for_status()  # Check for HTTP errors (like 422)

    market_data = response.json()

    print("\n--- RAW API RESPONSE (Start) ---")
    print(json.dumps(market_data, indent=2))
    print("--- RAW API RESPONSE (End) ---\n")

    if not market_data:
        print("Error: The API returned an empty response. The market slug might be invalid or the market is unavailable.")
        sys.exit(1)

    tokens_json = market_data.get('tokens', '[]')
    
    # Try to load as JSON string, fallback to direct access if it's already an array
    try:
        tokens = json.loads(tokens_json)
    except (json.JSONDecodeError, TypeError):
        tokens = tokens_json if isinstance(tokens_json, list) else []

    print("\n--- Polymarket Token IDs (Asset IDs) ---")
    if not tokens:
        print("Error: Could not find token data in the response, check the raw output above.")
        sys.exit(1)

    for token in tokens:
        # The 'outcome' for this market will be one of: "25 bps decrease", "No change", etc.
        outcome_name = token.get('outcome', 'N/A')
        token_id = token.get('token_id', token.get('assetId', 'N/A'))
        print(f"Outcome: {str(outcome_name).ljust(10)} | Token ID: {token_id}")

    print("\n**Copy these Token IDs for use in your bot's POLYMARKET_MAPPING and PolymarketClient.**")

except requests.exceptions.RequestException as e:
    print(f"Error fetching market data (HTTP Error): {e}")
    sys.exit(1)

except json.JSONDecodeError:
    print("Error: Failed to decode JSON response. The API might have returned plain text or an error page.")
    sys.exit(1)