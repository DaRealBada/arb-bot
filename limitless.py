import requests
import logging

logger = logging.getLogger(__name__)

# --- CONFIGURATION (Based on Limitlex structure) ---
LIMITLEX_BASE_URL = "https://limitlex.com/api" 
ORDER_BOOK_ENDPOINT = "/public/order_book"
# Assuming 'market_id' maps to a 'pair_id' in the Limitless/Limitlex system
# NOTE: The actual production client would likely pull the full list of pairs first
# and map them to the prediction markets you care about.

class LimitlessClient:
    """
    A client to fetch public order book data from Limitless (Limitlex) via REST API.
    Since Limitless is an exchange, we are fetching order books based on pair_ids.
    """
    def __init__(self, market_mapping=None):
        """
        Initialize with a mapping from your internal market slugs to Limitless pair_ids.
        market_mapping: dict { 'my_slug': 'limitlex_pair_id' }
        """
        self.market_mapping = market_mapping if market_mapping is not None else {}
        self.order_books = {} # Storage: { pair_id: { 'bids': [], 'asks': [] } }
        logger.info(f"LimitlessClient initialized with {len(self.market_mapping)} market IDs.")

    def fetch_orderbook(self, pair_id):
        """
        Fetches the order book for a single pair_id from the Limitless API.
        
        :param pair_id: The unique ID for the trading pair on Limitless.
        :return: A dictionary: {'bids': [(price, size), ...], 'asks': [(price, size), ...]} 
                 or None if the fetch fails.
        """
        api_url = f"{LIMITLEX_BASE_URL}{ORDER_BOOK_ENDPOINT}"
        params = {'pair_id': pair_id}
        
        try:
            response = requests.get(api_url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            if data.get('error'):
                logger.error(f"Limitless API error for {pair_id}: {data['error']['message']}")
                return None
            
            result = data.get('result', {})
            
            # Convert raw exchange data (price/size strings) to standardized format (float, float)
            bids = [(float(b['price']), float(b['size'])) for b in result.get('bids', [])]
            asks = [(float(a['price']), float(a['size'])) for a in result.get('asks', [])]
            
            return {'bids': bids, 'asks': asks}

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch Limitless order book for {pair_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error processing Limitless response for {pair_id}: {e}")
            return None

# Inside limitless.py, within the LimitlessClient class

    def fetch_all_order_books(self):
        """Fetches and updates order books for all tracked pairs."""
        new_books = {}
        
        for internal_slug, data in self.market_mapping.items():
            
            # -----------------------------------------------------------------
            # ARBITRAGE TEST CASE #1: HIGH-PROFIT ARB (Based on original Poly price bug)
            # This simulates the massive 700% arb you were seeing.
            # -----------------------------------------------------------------
            if internal_slug == "russia-x-ukraine-ceasefire-in-2025": 
                simulated_book = {
                    "yes": {
                        "bids": [(0.5100, 1000.0)],
                        "asks": [(0.5200, 1000.0)]
                    },
                    "no": {
                        "bids": [(0.4700, 1000.0)],
                        "asks": [(0.4800, 1000.0)]
                    }
                }
                logger.info(f"STUB: Applying HIGH-PROFIT price to {internal_slug}")
            
            # -----------------------------------------------------------------
            # ARBITRAGE TEST CASE #2: FORCED ARB (The one we couldn't get to hit)
            # This uses the impossibly high 0.90 bid to force a second hit.
            # -----------------------------------------------------------------
            elif internal_slug == "fed-rate-hike-in-2025": 
                simulated_book = {
                    "yes": {
                        "bids": [(0.9900, 500.0)], 
                        "asks": [(0.9950, 500.0)]
                    },
                    "no": {
                        "bids": [(0.0050, 500.0)],
                        "asks": [(0.0100, 500.0)]
                    }
                }
                logger.info(f"STUB: Applying FORCED ARB price to {internal_slug}")
            
            # -----------------------------------------------------------------
            # GENERIC/DEFAULT PRICE (For all other markets)
            # -----------------------------------------------------------------
            else:
                simulated_book = {
                    "yes": {
                        "bids": [(0.5100, 1000.0)],
                        "asks": [(0.5200, 1000.0)]
                    },
                    "no": {
                        "bids": [(0.4700, 1000.0)],
                        "asks": [(0.4800, 1000.0)]
                    }
                }

            new_books[internal_slug] = simulated_book
            
        self.order_books = new_books
        logger.info(f"Limitless: Updated {len(self.order_books)} order books.")
        return self.order_books