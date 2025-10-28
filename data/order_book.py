# File: data/order_book.py

import logging
from threading import Lock
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

# Type for a single outcome's order book: List[Tuple[price, size]]
OrderBook = List[Tuple[float, float]]

class OrderBookManager:
    def __init__(self, polymarket_client, limitless_client, poly_mapping, limitless_mapping):
        """
        Initializes OrderBookManager to manage data from Polymarket and Limitless/Kalshi.
        
        Args:
            polymarket_client: Polymarket client instance.
            limitless_client: Limitless/Kalshi client instance (can be None).
            poly_mapping: { market_slug: { 'yes_token_id': str, 'no_token_id': str, 'question': str } }
            limitless_mapping: { market_slug: { 'pair_id': str, 'question': str } } or None
        """
        self.polymarket_client = polymarket_client
        self.limitless_client = limitless_client
        self.poly_mapping = poly_mapping if poly_mapping else {}
        self.limitless_mapping = limitless_mapping if limitless_mapping else {}
        
        self.market_info = {}       # { slug: { 'question': str, 'on_poly': bool, 'on_limitless': bool } }
        self.combined_order_books = {} # Master storage for normalized data
        self.lock = Lock()
        
        # --- Market Matching Check ---
        # A market is tracked if it exists in either mapping. 
        # A cross-platform check is possible only if the SLUG exists in BOTH.
        for slug, data in self.poly_mapping.items():
            is_limitless = slug in self.limitless_mapping
            self.market_info[slug] = {
                'question': data.get('question', slug), 
                'on_poly': True, 
                'on_limitless': is_limitless
            }
        
        for slug, data in self.limitless_mapping.items():
            if slug not in self.market_info:
                self.market_info[slug] = {
                    'question': data.get('question', slug), 
                    'on_poly': False, 
                    'on_limitless': True
                }
        
        logger.info(f"OrderBookManager initialized for {len(self.market_info)} total markets.")
        
        # Count common markets
        common_count = sum(1 for info in self.market_info.values() if info['on_poly'] and info['on_limitless'])
        if common_count > 0:
            logger.info(f"✅ Cross-platform markets detected: {common_count} markets on both platforms.")
        else:
            logger.warning("No common market slugs found for cross-platform arbitrage checks.")

    def update_order_books(self):
        """Pulls the latest data from all clients and updates the internal structure."""
        
        # 1. Get Polymarket data (already running in the background via WebSocket)
        poly_books_raw = self.polymarket_client.get_order_books()
        
        # 2. Get Limitless data (via REST poll, or empty dict if client is None)
        limitless_books_raw = {}
        if self.limitless_client:
            try:
                limitless_books_raw = self.limitless_client.fetch_all_order_books()
            except Exception as e:
                logger.error(f"Error fetching Limitless order books: {e}")
                limitless_books_raw = {}
        
        with self.lock:
            self.combined_order_books = {}  # Clear old data

            for slug, info in self.market_info.items():
                self.combined_order_books[slug] = {}
                
                # A. Process Polymarket Data
                if info.get('on_poly'):
                    map_data = self.poly_mapping.get(slug)
                    if map_data:
                        yes_id, no_id = map_data['yes_token_id'], map_data['no_token_id']
                        
                        yes_book = poly_books_raw.get(yes_id)
                        no_book = poly_books_raw.get(no_id)
                        
                        if yes_book and no_book:
                            self.combined_order_books[slug]['polymarket'] = {
                                'yes': yes_book,
                                'no': no_book
                            }

                # B. Process Limitless Data
                if info.get('on_limitless') and slug in limitless_books_raw:
                    limitless_book = limitless_books_raw.get(slug)
                    
                    if limitless_book:
                        self.combined_order_books[slug]['limitless'] = {
                            'yes': limitless_book.get('yes', {'bids': [], 'asks': []}),
                            'no': limitless_book.get('no', {'bids': [], 'asks': []})
                        }

    def compare_specific_markets(self) -> Dict[str, Dict[str, Any]]:
        """
        Returns structured order book data for all markets, grouped by platform.
        
        Output format:
        { 
          market_slug: { 
            "polymarket": { "yes": {...}, "no": {...} },
            "limitless": { "yes": {...}, "no": {...} }
          }
        }
        """
        with self.lock:
            structured = {}
            for slug, platform_data in self.combined_order_books.items():
                structured[slug] = {}
                for platform, data in platform_data.items():
                    structured[slug][platform] = {
                        'yes': {
                            'bids': sorted(data['yes'].get('bids', []), reverse=True),
                            'asks': sorted(data['yes'].get('asks', []))
                        },
                        'no': {
                            'bids': sorted(data['no'].get('bids', []), reverse=True),
                            'asks': sorted(data['no'].get('asks', []))
                        }
                    }
            return structured
    
    def get_market_info(self, market_slug):
        """Returns info dict for a specific market."""
        return self.market_info.get(market_slug, {})

    def get_market_list(self):
        """Returns list of market slugs being tracked."""
        return list(self.market_info.keys())
    
    def get_common_market_slugs(self):
        """
        Returns a list of market slugs that exist on BOTH Polymarket and Limitless.
        This is needed for cross-platform arbitrage checks.
        """
        return [slug for slug, info in self.market_info.items() 
                if info.get('on_poly') and info.get('on_limitless')]