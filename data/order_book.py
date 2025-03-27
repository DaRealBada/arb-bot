class OrderBookManager:
    def __init__(self, kalshi_client, polymarket_client):
        self.kalshi_client = kalshi_client
        self.polymarket_client = polymarket_client
        self.combined_order_books = {"kalshi": {}, "polymarket": {}}

    def update_order_books(self):
        self.combined_order_books["kalshi"] = self.kalshi_client.get_order_books()
        self.combined_order_books["polymarket"] = self.polymarket_client.get_order_books()

    def compare_specific_markets(self):
        self.update_order_books()
        kalshi_ticker = "KXELONTWEETS-25MAR28-474.5"
        kalshi_book = self.combined_order_books["kalshi"].get(kalshi_ticker, {"yes": {}, "no": {}})
        # Normalize Kalshi prices to dollars
        kalshi_yes_bids = sorted([(float(price) / 100, qty) for price, qty in kalshi_book["yes"].items()], reverse=True)
        kalshi_yes_asks = sorted([(float(price) / 100, qty) for price, qty in kalshi_book["no"].items()])

        poly_450_474_yes = "8210590464497581946725445974017686999853198970871180813488940440519696534822"
        poly_450_474_no = "103375030657321264814701483740101162210535970159432445623129568287514615958573"
        poly_475_499_yes = "69442592080794478573959779833784433036273422503780746452193547006928387926589"
        poly_475_499_no = "78542726175952526631472130854138525311624553971570647007294131780992415355449"

        poly_450_474_book = {
            "yes": self.combined_order_books["polymarket"].get(poly_450_474_yes, {"bids": [], "asks": []}),
            "no": self.combined_order_books["polymarket"].get(poly_450_474_no, {"bids": [], "asks": []})
        }
        poly_475_499_book = {
            "yes": self.combined_order_books["polymarket"].get(poly_475_499_yes, {"bids": [], "asks": []}),
            "no": self.combined_order_books["polymarket"].get(poly_475_499_no, {"bids": [], "asks": []})
        }

        poly_450_474_yes_bids = sorted(poly_450_474_book["yes"]["bids"], reverse=True)
        poly_450_474_yes_asks = sorted(poly_450_474_book["yes"]["asks"])
        poly_475_499_yes_bids = sorted(poly_475_499_book["yes"]["bids"], reverse=True)
        poly_475_499_yes_asks = sorted(poly_475_499_book["yes"]["asks"])

        return {
            "kalshi_450_499": {"yes": {"bids": kalshi_yes_bids, "asks": kalshi_yes_asks}},
            "poly_450_474": {"yes": {"bids": poly_450_474_yes_bids, "asks": poly_450_474_yes_asks}},
            "poly_475_499": {"yes": {"bids": poly_475_499_yes_bids, "asks": poly_475_499_yes_asks}}
        }

    def print_comparison(self):
        comparison = self.compare_specific_markets()
        print("\nKalshi (450-499) vs Polymarket (450-474) vs Polymarket (475-499)")
        
        # Print Bids
        print("Bids:")
        kalshi_bids = comparison["kalshi_450_499"]["yes"]["bids"]
        poly_450_474_bids = comparison["poly_450_474"]["yes"]["bids"]
        poly_475_499_bids = comparison["poly_475_499"]["yes"]["bids"]
        max_bids = max(len(kalshi_bids), len(poly_450_474_bids), len(poly_475_499_bids))
        
        for i in range(max_bids):
            k_bid = kalshi_bids[i] if i < len(kalshi_bids) else (None, None)
            p1_bid = poly_450_474_bids[i] if i < len(poly_450_474_bids) else (None, None)
            p2_bid = poly_475_499_bids[i] if i < len(poly_475_499_bids) else (None, None)
            print(f"  Kalshi: {k_bid} | Poly 450-474: {p1_bid} | Poly 475-499: {p2_bid}")

        # Print Asks
        print("Asks:")
        kalshi_asks = comparison["kalshi_450_499"]["yes"]["asks"]
        poly_450_474_asks = comparison["poly_450_474"]["yes"]["asks"]
        poly_475_499_asks = comparison["poly_475_499"]["yes"]["asks"]
        max_asks = max(len(kalshi_asks), len(poly_450_474_asks), len(poly_475_499_asks))
        
        for i in range(max_asks):
            k_ask = kalshi_asks[i] if i < len(kalshi_asks) else (None, None)
            p1_ask = poly_450_474_asks[i] if i < len(poly_450_474_asks) else (None, None)
            p2_ask = poly_475_499_asks[i] if i < len(poly_475_499_asks) else (None, None)
            print(f"  Kalshi: {k_ask} | Poly 450-474: {p1_ask} | Poly 475-499: {p2_ask}")