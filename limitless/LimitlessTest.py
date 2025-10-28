# LimitlessTest.py
# Final verification script using the confirmed Limitlex REST API documentation.

import requests
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- CONFIGURATION BASED ON NEW DOCUMENTATION (Limitlex) ---
# Base API URL
LIMITLEX_BASE_URL = "https://limitlex.com/api" 
ORDER_BOOK_ENDPOINT = "/public/order_book"

# We must use an exchange 'pair_id' as this is a crypto exchange, not a prediction market.
# NOTE: This ID is a placeholder and may need to be replaced with a live trading pair ID 
# from Limitlex's /public/pairs endpoint if this specific ID is invalid.
TEST_PAIR_ID = "ab651a43-1fc9-4163-a31b-74e5f537e82f:bfd04d06-b97c-4287-8bb0-c18f2eb19157" 

def test_limitlex_connection(base_url, endpoint, pair_id):
    """Attempts to connect to the Limitlex REST API and fetch order book data."""
    
    api_url = f"{base_url}{endpoint}"
    
    # Limitlex uses application/x-www-form-urlencoded, so parameters can be sent in the body or as params
    params = {'pair_id': pair_id}
    
    logging.info(f"Attempting connection to Limitlex Order Book API: {api_url}")
    logging.info(f"Using Pair ID: {pair_id}")
    
    try:
        # Use GET for public endpoints as per docs (though POST is also supported)
        response = requests.get(api_url, params=params, timeout=10)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        
        data = response.json()

        if data.get('error'):
            logging.error(f"API returned an error: {data['error']['message']}")
            return False, data['error']['message']

        result = data.get('result', {})
        
        if not result.get('asks') or not result.get('bids'):
            logging.warning("Successfully connected, but no bids or asks found for this pair.")
            return True, "Empty order book received."
            
        logging.info("--------------------------------------------------")
        logging.info("✅ SUCCESS: Limitlex API Connection Confirmed!")
        logging.info(f"Top Ask Price (Sell): {result['asks'][0]['price']}")
        logging.info(f"Top Bid Price (Buy): {result['bids'][0]['price']}")
        
        return True, result

    except requests.exceptions.RequestException as e:
        logging.error(f"❌ ERROR: Failed to connect or receive response from Limitlex API.")
        logging.error(f"Details: {e}")
        return False, str(e)
    except Exception as e:
        logging.error(f"❌ ERROR: Failed to process Limitlex API response.")
        logging.error(f"Details: {e}")
        return False, str(e)


if __name__ == '__main__':
    success, result = test_limitlex_connection(LIMITLEX_BASE_URL, ORDER_BOOK_ENDPOINT, TEST_PAIR_ID)
    
    if success and result:
        print("\nLimitlex PoC Test Complete. We can proceed with the client implementation.")
    else:
        print("\nLimitlex PoC Test Failed. We must confirm a valid TEST_PAIR_ID.")
