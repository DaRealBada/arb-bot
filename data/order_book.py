import logging

logger = logging.getLogger(__name__)

class OrderBookManager:
    def __init__(self, kalshi_client, polymarket_client, market_mapping=None):
        """
        Initialize OrderBookManager with dynamic market mapping.
        
        Args:
            kalshi_client: Kalshi client (can be None)
            polymarket_client: Polymarket client instance
            market_mapping: Dict mapping market slugs to token IDs
                           Format: {"slug": {"yes_token_id": "...", "no_token_id": "...", "question": "..."}}
        """
        self.polymarket_client = polymarket_client
        self.combined_order_books = {"polymarket": {}}
        
        # Use provided mapping or fall back to hardcoded default
        if market_mapping is None:
            logger.warning("No market mapping provided, using default US Recession market")
            self.market_mapping = {
                "us-recession-in-2025": { 
                    "question": "US recession in 2025?",
                    "yes_token_id": "104173557214744537570424345347209544585775842950109756851652855913015295701992",
                    "no_token_id": "44528029102356085806317866371026691780796471200782980570839327755136990994869"
                }
            }
        else:
            self.market_mapping = market_mapping
            logger.info(f"Loaded {len(market_mapping)} markets into OrderBookManager")

    def update_order_books(self):
        """Fetches the latest order books from the Polymarket client."""
        if self.polymarket_client:
            self.combined_order_books["polymarket"] = self.polymarket_client.get_order_books()

    def compare_specific_markets(self):
        """
        Processes the raw order book data and organizes it for the bot.
        Returns structured data for all markets in the mapping.
        """
        structured_books = {}
        poly_books = self.combined_order_books.get("polymarket", {})

        # Return default if data is empty
        if not poly_books:
            logger.warning("Polymarket order book data is empty in OrderBookManager.")
            for market_slug in self.market_mapping.keys():
                structured_books[market_slug] = {
                    "yes": {"bids": [], "asks": []}, 
                    "no": {"bids": [], "asks": []}
                }
            return structured_books

        # Process each market in the mapping
        for market_slug, token_info in self.market_mapping.items():
            yes_token_id = token_info["yes_token_id"]
            no_token_id = token_info["no_token_id"]

            yes_order_book = poly_books.get(yes_token_id, {"bids": [], "asks": []})
            no_order_book = poly_books.get(no_token_id, {"bids": [], "asks": []})

            structured_books[market_slug] = {
                "yes": {
                    "bids": sorted(yes_order_book.get("bids", []), reverse=True),
                    "asks": sorted(yes_order_book.get("asks", []))
                },
                "no": {
                    "bids": sorted(no_order_book.get("bids", []), reverse=True),
                    "asks": sorted(no_order_book.get("asks", []))
                }
            }
        
        return structured_books

    def get_market_list(self):
        """Returns list of market slugs being tracked."""
        return list(self.market_mapping.keys())
    
    def get_market_info(self, market_slug):
        """Returns info dict for a specific market."""
        return self.market_mapping.get(market_slug, {})

    def print_comparison(self):
        """Print comparison for all tracked markets."""
        comparison = self.compare_specific_markets()
        
        print("\n" + "="*80)
        print(f"Order Book Comparison - {len(comparison)} Markets")
        print("="*80)
        
        for market_slug, data in comparison.items():
            market_info = self.market_mapping.get(market_slug, {})
            question = market_info.get('question', market_slug)
            
            print(f"\n📊 {question}")
            print(f"   Slug: {market_slug}")
            
            yes_bids = data["yes"]["bids"]
            yes_asks = data["yes"]["asks"]
            no_bids = data["no"]["bids"]
            no_asks = data["no"]["asks"]
            
            print("   YES Outcome:")
            print(f"      Best Bid: {yes_bids[0][0]:.4f} (size: {yes_bids[0][1]:.2f})" if yes_bids else "      No bids")
            print(f"      Best Ask: {yes_asks[0][0]:.4f} (size: {yes_asks[0][1]:.2f})" if yes_asks else "      No asks")
            
            print("   NO Outcome:")
            print(f"      Best Bid: {no_bids[0][0]:.4f} (size: {no_bids[0][1]:.2f})" if no_bids else "      No bids")
            print(f"      Best Ask: {no_asks[0][0]:.4f} (size: {no_asks[0][1]:.2f})" if no_asks else "      No asks")
            print("-" * 80)