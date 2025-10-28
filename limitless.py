import requests
import logging

logger = logging.getLogger(__name__)

# --- CONFIGURATION (Based on Limitlex structure) ---
LIMITLEX_BASE_URL = "https://limitlex.com/api" 
ORDER_BOOK_ENDPOINT = "/public/order_book"

class LimitlessClient:
    """
    A client to fetch public order book data from Limitless (Limitlex) via REST API.
    Since Limitless is an exchange, we are fetching order books based on pair_ids.
    """
    def __init__(self, market_mapping=None):
        """
        Initialize with a mapping from your internal market slugs to Limitless pair_ids.
        market_mapping: dict { 'my_slug': {'pair_id': str, ...} }
        """
        self.market_mapping = market_mapping if market_mapping is not None else {}
        self.order_books = {} # Storage: { slug: { 'yes': {'bids': [], 'asks': []}, 'no': {...} } }
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
                logger.error(f"Limitless API error for {pair_id}: {data['error'].get('message', 'Unknown error')}")
                return None
            
            result = data.get('result', {})
            
            # Convert raw exchange data (price/size strings) to standardized format (float, float)
            bids = [(float(b['price']), float(b.get('size', b.get('amount_1', 0)))) 
                    for b in result.get('bids', [])]
            asks = [(float(a['price']), float(a.get('size', a.get('amount_1', 0)))) 
                    for a in result.get('asks', [])]
            
            return {'bids': bids, 'asks': asks}

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch Limitless order book for {pair_id}: {e}")
            return None
        except (ValueError, KeyError, TypeError) as e:
            logger.error(f"Error processing Limitless response for {pair_id}: {e}")
            return None

    def fetch_all_order_books(self):
        """
        Fetches and updates real order books for all tracked pairs.
        
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
            url = f"{LIMITLEX_BASE_URL}{ORDER_BOOK_ENDPOINT}?pair_id={pair_id}"
            
            try:
                response = requests.get(url, timeout=5) 
                response.raise_for_status() 
                book_data = response.json()
            except requests.exceptions.RequestException as e:
                logger.warning(f"Failed to fetch order book for {internal_slug} ({pair_id}): {e}")
                continue
            except Exception as e:
                logger.error(f"Unexpected error fetching {internal_slug}: {e}")
                continue
            
            if not book_data.get('result'):
                logger.warning(f"No result in response for {internal_slug}")
                continue
                
            result = book_data['result']
            if 'asks' not in result or 'bids' not in result:
                logger.warning(f"Missing asks/bids in result for {internal_slug}")
                continue
            
            try:
                # Format order book data
                asks_list = []
                for item in result['asks']:
                    price = float(item['price'])
                    volume = float(item.get('amount_1', item.get('size', 0)))
                    asks_list.append((price, volume))

                bids_list = []
                for item in result['bids']:
                    price = float(item['price'])
                    volume = float(item.get('amount_1', item.get('size', 0)))
                    bids_list.append((price, volume))

                # Map base asset to 'yes' side for compatibility
                new_books[internal_slug] = {
                    "yes": {
                        "bids": bids_list,
                        "asks": asks_list
                    },
                    "no": {
                        "bids": [],  # Not used for exchange pairs
                        "asks": []
                    }
                }
            except (ValueError, KeyError, TypeError) as e:
                logger.error(f"Error parsing order book for {internal_slug}: {e}")
                continue

        logger.info(f"Limitless: Updated {len(new_books)}/{len(self.market_mapping)} order books from API.")
        self.order_books = new_books
        return self.order_books