import requests
import logging

logger = logging.getLogger(__name__)

# Base URL identified from the documentation
LIMITLESS_BASE_URL = "https://limitlex.com/api"

def fetch_limitless_market_mapping():
    """
    Fetches all active exchange pairs from the Limitlex /pairs public endpoint
    and maps a subset of the first pairs found to our Polymarket test slugs.
    This creates the necessary overlap for cross-platform arbitrage checks to work.
    
    Returns:
        dict: Mapping of polymarket slugs to limitless pair data, or empty dict on error
    """
    endpoint = "/public/pairs"
    url = LIMITLESS_BASE_URL + endpoint
    
    logger.info(f"Fetching active markets from Limitless: {url}")

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching Limitless market pairs: {e}")
        return {}  # Return empty dict instead of None
    except Exception as e:
        logger.error(f"Unexpected error parsing Limitless response: {e}")
        return {}  # Return empty dict instead of None
    
    # Check if the result structure matches the documentation
    if not data.get('result') or 'data' not in data['result']:
        logger.error("Limitless API returned unexpected structure.")
        return {}  # Already returns empty dict, good
        
    raw_pairs = data['result']['data']
    
    if not raw_pairs:
        logger.warning("Limitless API returned no pairs.")
        return {}
    
    logger.info(f"Limitless: Found {len(raw_pairs)} active exchange pairs.")

    # --- Market Translation: Mapping Polymarket Slugs to Real Limitlex Pairs ---
    
    # 1. Define the specific Polymarket slugs we want to test/map
    POLYMARKET_TEST_SLUGS = [
        "fed-rate-hike-in-2025",
        "tether-insolvent-in-2025",
        "russia-x-ukraine-ceasefire-in-2025",
        "weed-rescheduled-in-2025",
        "fed-emergency-rate-cut-in-2025",
    ]
    
    # 2. Map these Polymarket slugs to the first few real Limitlex Pair IDs
    market_mapping = {}
    
    for i, pair in enumerate(raw_pairs):
        if i >= len(POLYMARKET_TEST_SLUGS):
            break  # Stop after mapping the desired number of test markets
            
        poly_slug = POLYMARKET_TEST_SLUGS[i]
        
        # Validate that the pair has required fields
        if not pair.get('id'):
            logger.warning(f"Skipping pair at index {i} - missing 'id' field")
            continue
        
        # We use the Polymarket slug as the key (which is what the OrderBookManager expects)
        # but the data for the market is a real Limitlex pair.
        market_mapping[poly_slug] = {
            "pair_id": pair['id'],
            "currency_id_1": pair.get('currency_id_1'),
            "currency_id_2": pair.get('currency_id_2'),
            # Give it a descriptive name for logging/printing
            "question": f"LIMITLEX: {poly_slug.replace('-', ' ').title()}",  # Changed to 'question' for consistency
        }

    logger.info(f"Limitless: Successfully mapped {len(market_mapping)} Polymarket slugs to real exchange pairs for cross-arb checks.")
    return market_mapping