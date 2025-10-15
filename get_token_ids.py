import requests
import json
import sys
import logging

# Set up logging for clarity
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
# The market slug for the Bitcoin price market
MARKET_SLUG = "what-price-will-bitcoin-hit-in-2025"

# The endpoint for fetching a comprehensive list of events/markets
# We use a high limit to ensure we capture the target market if it's recent
API_URL = f"https://gamma-api.polymarket.com/events?closed=false&limit=50"
# ---------------------

logger.info(f"Attempting to fetch market data via /events endpoint...")
logger.info(f"Using search URL: {API_URL}")

try:
    # 1. Fetch the data from the /events endpoint
    response = requests.get(API_URL)
    response.raise_for_status()

    events_data = response.json()

    if not events_data or 'events' not in events_data:
        logger.error("The API returned an unexpected or empty response from the /events endpoint.")
        sys.exit(1)

    target_market = None
    
    # 2. Iterate through all events to find the target market
    for event in events_data['events']:
        for market in event.get('markets', []):
            if market.get('slug') == MARKET_SLUG:
                target_market = market
                break
        if target_market:
            break

    if not target_market:
        logger.error(f"Error: Market with slug '{MARKET_SLUG}' was not found in the latest {len(events_data['events'])} events.")
        sys.exit(1)

    logger.info(f"Successfully located market data for: {target_market.get('question')}")
    
    # 3. Extract and parse the nested 'tokens' JSON string
    tokens_json_string = target_market.get('tokens')
    
    if not tokens_json_string:
        logger.error("The 'tokens' field was missing or empty in the market data.")
        # Print the relevant market data for manual inspection
        print("\n--- Market Data Snippet for Debugging ---")
        print(json.dumps(target_market, indent=2))
        print("-----------------------------------------\n")
        sys.exit(1)

    # CRITICAL STEP: Robustly parse the nested JSON string
    try:
        tokens_array = json.loads(tokens_json_string)
    except json.JSONDecodeError:
        logger.error(f"Failed to decode the nested 'tokens' JSON string. Data corrupted.")
        sys.exit(1)
    
    # 4. Extract and display Token IDs
    print("\n\n--- Polymarket Token IDs (Asset IDs) ---")
    
    if not tokens_array or not isinstance(tokens_array, list):
        logger.error("Token data was successfully parsed but is not a list or is empty.")
        sys.exit(1)

    for token in tokens_array:
        outcome_name = token.get('outcome', 'N/A')
        # Check for 'token_id' (common) and fallback to 'assetId' (sometimes used)
        token_id = token.get('token_id', token.get('assetId', 'N/A')) 
        
        if token_id != 'N/A':
            # Print cleanly
            print(f"Outcome: {str(outcome_name):<30} | Token ID: {token_id}")

    print("\n**SUCCESS: Copy the Token ID(s) needed for your bot's POLYMARKET_MAPPING.**")

except requests.exceptions.HTTPError as e:
    status_code = e.response.status_code
    logger.error(f"HTTP Error {status_code}: The API call failed. Check internet/firewall.")
    sys.exit(1)
except requests.exceptions.RequestException as e:
    logger.error(f"A connection error occurred: {e}")
    sys.exit(1)