import requests
import logging
import json

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
GAMMA_BASE_URL = "https://gamma-api.polymarket.com"
CLOB_BASE_URL = "https://clob.polymarket.com"

def get_orderbook_prices(token_id):
    """
    Fetches the order book for a specific token ID from the CLOB API.
    Returns (best_bid, best_ask) as floats, or (None, None) if unavailable.
    """
    try:
        url = f"{CLOB_BASE_URL}/book?token_id={token_id}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        bids = data.get('bids', [])
        asks = data.get('asks', [])
        
        best_bid = float(bids[0]['price']) if bids else None
        best_ask = float(asks[0]['price']) if asks else None
        
        return best_bid, best_ask
        
    except requests.exceptions.RequestException as e:
        logger.warning(f"Error fetching orderbook for token {token_id}: {e}")
        return None, None
    except (ValueError, KeyError, IndexError) as e:
        logger.warning(f"Error parsing orderbook data for token {token_id}: {e}")
        return None, None


def fetch_market_details(market_id):
    """
    Fetches detailed market data including token IDs for a single market.
    Returns a dictionary with market info, or None on error.
    """
    market_detail_url = f"{GAMMA_BASE_URL}/markets/{market_id}"
    
    try:
        response = requests.get(market_detail_url, timeout=10)
        response.raise_for_status()
        market_data = response.json()
        
        # Parse token IDs if they're JSON strings
        clob_token_ids = market_data.get('clobTokenIds')
        if isinstance(clob_token_ids, str):
            try:
                clob_token_ids = json.loads(clob_token_ids)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse clobTokenIds for market {market_id}")
                return None
        
        # Parse outcomes if they're JSON strings
        outcomes = market_data.get('outcomes', [])
        if isinstance(outcomes, str):
            try:
                outcomes = json.loads(outcomes)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse outcomes for market {market_id}")
                outcomes = []
        
        return {
            'id': market_data.get('id'),
            'question': market_data.get('question'),
            'slug': market_data.get('slug'),
            'outcomes': outcomes,
            'clobTokenIds': clob_token_ids,
            'active': market_data.get('active', False),
            'closed': market_data.get('closed', True),
            'liquidity': market_data.get('liquidityNum', 0),
            'volume24hr': market_data.get('volume24hr', 0)
        }
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching market {market_id}: {e}")
        return None


def fetch_event_markets(event_slug, min_liquidity=0, only_active=True):
    """
    Fetches all markets for a given event slug.
    
    Args:
        event_slug: The Polymarket event slug (e.g., 'us-recession-in-2025')
        min_liquidity: Minimum liquidity filter (default: 0)
        only_active: Only return active, non-closed markets (default: True)
    
    Returns:
        List of market dictionaries with token IDs and metadata
    """
    # Step 1: Get Event ID
    event_url = f"{GAMMA_BASE_URL}/events/slug/{event_slug}"
    logger.info(f"Fetching event: {event_slug}")
    
    try:
        event_response = requests.get(event_url, timeout=10)
        event_response.raise_for_status()
        event_data = event_response.json()
        event_id = event_data.get("id")
        
        if not event_id:
            logger.error(f"No event ID found for slug: {event_slug}")
            return []
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching event: {e}")
        return []
    
    # Step 2: Get markets for this event
    closed_param = "false" if only_active else "true"
    markets_url = f"{GAMMA_BASE_URL}/markets?event_id={event_id}&closed={closed_param}"
    
    try:
        markets_response = requests.get(markets_url, timeout=10)
        markets_response.raise_for_status()
        markets_data = markets_response.json()
        
        all_markets = markets_data if isinstance(markets_data, list) else markets_data.get('markets', [])
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching markets: {e}")
        return []
    
    # Step 3: Fetch detailed data for each market
    detailed_markets = []
    
    for market_summary in all_markets:
        market_id = market_summary.get('id')
        if not market_id:
            continue
            
        market_details = fetch_market_details(market_id)
        
        if market_details and market_details.get('clobTokenIds'):
            # Apply filters
            if min_liquidity > 0 and market_details.get('liquidity', 0) < min_liquidity:
                continue
                
            detailed_markets.append(market_details)
    
    logger.info(f"Found {len(detailed_markets)} markets matching criteria")
    return detailed_markets


def get_market_mapping_for_bot(market_ids=None, min_liquidity=0):
    """
    Fetches markets and formats them for the bot's POLYMARKET_MAPPING structure.
    Only includes binary (Yes/No) markets.
    
    Args:
        market_ids: A list of market IDs to scan. If None or empty, all active Polymarket IDs are fetched.
        min_liquidity: Minimum liquidity filter.
        
    Returns:
        The bot-ready market mapping dictionary.
    """
    # 1. Determine which markets to scan
    if not market_ids:
        market_ids = fetch_all_active_market_ids()
    
    if not market_ids:
        logger.error("No market IDs to process.")
        return {}
        
    # 2. Fetch detailed data for each market
    mapping = {}
    
    for market_id in market_ids:
        market_details = fetch_market_details(market_id)
        
        if not market_details or not market_details.get('clobTokenIds'):
            continue
            
        # Apply filters
        if min_liquidity > 0 and market_details.get('liquidity', 0) < min_liquidity:
            continue
            
        # Only process binary markets (2 outcomes)
        if len(market_details.get('outcomes', [])) != 2 or len(market_details.get('clobTokenIds', [])) != 2:
            continue
            
        outcomes = market_details['outcomes']
        token_ids = market_details['clobTokenIds']
        
        # Determine which token is YES and which is NO (same logic as before)
        yes_idx = 0
        no_idx = 1
        for i, outcome in enumerate(outcomes):
            outcome_lower = str(outcome).lower()
            if outcome_lower == 'yes':
                yes_idx = i
                no_idx = 1 - i
            elif outcome_lower == 'no':
                no_idx = i
                yes_idx = 1 - i
        
        mapping[market_details['slug']] = {
            "question": market_details['question'],
            "yes_token_id": token_ids[yes_idx],
            "no_token_id": token_ids[no_idx],
            "liquidity": market_details.get('liquidity', 0),
            "volume24hr": market_details.get('volume24hr', 0)
        }

    logger.info(f"Successfully processed {len(mapping)} binary markets matching criteria.")
    return mapping    

    markets = fetch_event_markets(event_slug, min_liquidity=min_liquidity)
    mapping = {}
    
    for market in markets:
        # Only process binary markets (2 outcomes)
        if len(market.get('outcomes', [])) != 2 or len(market.get('clobTokenIds', [])) != 2:
            continue
        
        outcomes = market['outcomes']
        token_ids = market['clobTokenIds']
        
        # Determine which token is YES and which is NO
        yes_idx = 0
        no_idx = 1
        
        # Try to identify YES/NO based on outcome names
        for i, outcome in enumerate(outcomes):
            outcome_lower = str(outcome).lower()
            if outcome_lower == 'yes':
                yes_idx = i
                no_idx = 1 - i
            elif outcome_lower == 'no':
                no_idx = i
                yes_idx = 1 - i
        
        mapping[market['slug']] = {
            "question": market['question'],
            "yes_token_id": token_ids[yes_idx],
            "no_token_id": token_ids[no_idx],
            "liquidity": market.get('liquidity', 0),
            "volume24hr": market.get('volume24hr', 0)
        }
    
    return mapping
def fetch_all_active_market_ids():
    """
    Fetches the IDs of all active, non-closed markets on Polymarket.
    This is necessary because the /markets endpoint typically requires filters.
    """
    all_market_ids = set()
    page = 1
    page_size = 50 # Standard limit for many APIs

    logger.info("Fetching list of all active market IDs...")
    
    # Loop until no more markets are returned
    while True:
        try:
            # We use a broad search to retrieve all active markets
            markets_url = f"{GAMMA_BASE_URL}/markets?closed=false&page={page}&per_page={page_size}"
            response = requests.get(markets_url, timeout=10)
            response.raise_for_status()
            
            markets_data = response.json()
            # The API response structure might contain a 'markets' key or be a list itself
            markets_list = markets_data if isinstance(markets_data, list) else markets_data.get('markets', [])

            if not markets_list:
                break # Exit the loop if no markets were returned

            for market in markets_list:
                if market.get('active', False) and not market.get('closed', True):
                    all_market_ids.add(market['id'])
            
            # Check if we've reached the end of the results
            if len(markets_list) < page_size:
                break
                
            page += 1
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching active market IDs on page {page}: {e}")
            break
            
    logger.info(f"Found {len(all_market_ids)} total active market IDs.")
    return list(all_market_ids)


# --- For standalone script usage ---
def print_market_details(markets):
    """Pretty prints market details for debugging."""
    print("\n" + "="*80)
    print(f"Found {len(markets)} markets")
    print("="*80)
    
    for market in markets:
        print(f"\nMarket: {market['question']}")
        print(f"Slug: {market['slug']}")
        print(f"Outcomes: {market['outcomes']}")
        print(f"Token IDs: {market['clobTokenIds']}")
        print(f"Liquidity: ${market.get('liquidity', 0):,.2f}")
        print(f"24h Volume: ${market.get('volume24hr', 0):,.2f}")
        print("-" * 60)


if __name__ == "__main__":
    # Example usage when run as a script
    EVENT_SLUG = "us-recession-in-2025"
    
    print(f"Fetching markets for event: {EVENT_SLUG}")
    markets = fetch_event_markets(EVENT_SLUG, min_liquidity=0)
    print_market_details(markets)
    
    print("\n" + "="*80)
    print("Bot-ready mapping:")
    print("="*80)
    mapping = get_market_mapping_for_bot(EVENT_SLUG)
    for slug, info in mapping.items():
        print(f"\n'{slug}': {{")
        print(f"    'question': '{info['question']}',")
        print(f"    'yes_token_id': '{info['yes_token_id']}',")
        print(f"    'no_token_id': '{info['no_token_id']}'")
        print(f"}}")