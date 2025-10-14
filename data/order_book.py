import logging

logger = logging.getLogger(__name__)

# This dictionary connects the bot's market names to the client's token IDs.
# --- UPDATED: Only includes the 5 Fed Rate Cuts outcomes ---
POLYMARKET_MAPPING = { 
    "poly_fed_0_cuts": { 
        "yes_token_id": "13233824300645009841804910385973797437703578792070081033285141695415842858595"
    },
    "poly_fed_1_cuts": { 
        "yes_token_id": "10045187747802872322312675685790615591321458882585258288544975549723385759902"
    },
    "poly_fed_2_cuts": { 
        "yes_token_id": "14093902307297906954201103723329972551406567362846995641774213702167306236968"
    },
    "poly_fed_3_cuts": { 
        "yes_token_id": "15923832924375086576839356391965581692257002061291888365842600290947761007971"
    },
    "poly_fed_4_cuts": { 
        "yes_token_id": "16838383218556485897042048995392576326164221761623916295744211186717523171887"
    },
}

class OrderBookManager:
    def __init__(self, kalshi_client, polymarket_client):
        self.polymarket_client = polymarket_client
        self.combined_order_books = {"polymarket": {}}

    def update_order_books(self):
        """Fetches the latest order books from the Polymarket client."""
        if self.polymarket_client:
            self.combined_order_books["polymarket"] = self.polymarket_client.get_order_books()

    def compare_specific_markets(self):
        """
        Processes the raw order book data and organizes it using the readable names
        from POLYMARKET_MAPPING for the arbitrage bot.
        """
        structured_books = {}
        poly_books = self.combined_order_books.get("polymarket", {})

        if not poly_books:
            logger.warning("Polymarket order book data is empty in OrderBookManager.")
            for market_slug in POLYMARKET_MAPPING.keys():
                structured_books[market_slug] = {"yes": {"bids": [], "asks": []}}
            return structured_books

        for market_slug, token_info in POLYMARKET_MAPPING.items():
            yes_token_id = token_info["yes_token_id"]

            yes_order_book = poly_books.get(yes_token_id, {"bids": [], "asks": []})

            structured_books[market_slug] = {
                "yes": {
                    "bids": sorted(yes_order_book.get("bids", []), reverse=True),
                    "asks": sorted(yes_order_book.get("asks", []))
                }
            }
        
        return structured_books

    def print_comparison(self):
        print("Comparison printout is disabled in arbitrage mode.")