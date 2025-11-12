import requests
import logging

logger = logging.getLogger(__name__)

# --- CONFIGURATION (Based on Limitlex structure) ---
LIMITLEX_BASE_URL = "https://limitlex.com/api" 
ORDER_BOOK_ENDPOINT = "/public/order_book"

class LimitlessClient:
    """
    A client to fetch public order book data from Limitless (Limitlex) via REST API.
    """
    def __init__(self, market_mapping=None):
        """
        Initialize with a mapping from your internal market slugs to Limitless pair_ids.
        market_mapping: dict { 'my_slug': {'pair_id': str, ...} }
        """
        self.market_mapping = market_mapping if market_mapping is not None else {}
        self.order_books = {} # Storage: { slug: { 'yes': {'bids': [], 'asks': []}, 'no': {...} } }
        logger.info(f"LimitlessClient initialized with {len(self.market_mapping)} market IDs.")
        
    def _safe_float(self, value):
        """Helper function to safely convert a price or volume string to float."""
        try:
            # Strip whitespace and check if it's not None or an empty string before conversion
            if value is not None and str(value).strip():
                return float(value)
            return 0.0
        except ValueError:
            # Catches errors when the string is non-numeric (e.g., 'abc')
            logger.debug(f"Non-numeric value encountered: {value}")
            return 0.0


# File: limitless.py
# ... (rest of the file remains the same until fetch_orderbook) ...

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
                logger.error(f"Limitless API error for {pair_id}: {data['error'].get('message', 'Unknown error')}")
                return None
            
            # Defensive check for the top-level 'result' key
            result = data.get('result', {})
            
            # --- CRITICAL FIX: Isolate list comprehensions with try/except ---
            try:
                # Sanity check: Ensure 'bids' and 'asks' are lists if they exist
                bids_data = result.get('bids')
                if bids_data is None or not isinstance(bids_data, list):
                    bids_data = []

                asks_data = result.get('asks')
                if asks_data is None or not isinstance(asks_data, list):
                    asks_data = []

                # FINAL, ROBUST FIX: Use the sanitized data structures.
                bids = [(self._safe_float(b['price']), self._safe_float(b.get('size', b.get('amount_1', 0)))) 
                        for b in bids_data
                        if isinstance(b, dict) and 'price' in b]
                
                asks = [(self._safe_float(a['price']), self._safe_float(a.get('size', a.get('amount_1', 0)))) 
                        for a in asks_data
                        if isinstance(a, dict) and 'price' in a]
            
            except Exception as e:
                 # Catch any remaining iteration or key error explicitly here.
                logger.error(f"Error during list comprehension for {pair_id}: {e}")
                return None
            # ------------------------------------------------------------------

            return {'bids': bids, 'asks': asks}

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch Limitless order book for {pair_id}: {e}")
            return None
        except (ValueError, KeyError, TypeError) as e:
            # This block should now only catch errors in the initial response.json() or data access.
            logger.error(f"Error processing initial Limitless response for {pair_id}: {e}")
            return None
            
# ... (rest of the file remains the same) ...

    def fetch_all_order_books(self):
        """
        Fetches and updates real order books for all tracked pairs by utilizing
        the robust fetch_orderbook helper method.
        
        Returns:
            dict: { slug: { 'yes': {'bids': [...], 'asks': [...]}, 'no': {...} } }
        """
        new_books = {}
        
        if not self.market_mapping:
            logger.warning("No Limitless markets to fetch (empty market_mapping)")
            return new_books

        for internal_slug, data in self.market_mapping.items():
            if not data or 'pair_id' not in data:
                logger.warning(f"Invalid market data for {internal_slug}: missing 'pair_id'")
                continue
                
            pair_id = data['pair_id']
            
            # Call the robust single-market fetcher
            book_data = self.fetch_orderbook(pair_id)

            if book_data:
                # Map and store the successfully parsed book
                new_books[internal_slug] = {
                    "yes": {
                        "bids": book_data.get('bids', []),
                        "asks": book_data.get('asks', [])
                    },
                    "no": {
                        "bids": [], 
                        "asks": []
                    }
                }

        logger.info(f"Limitless: Updated {len(new_books)}/{len(self.market_mapping)} order books from API.")
        self.order_books = new_books
        return self.order_books