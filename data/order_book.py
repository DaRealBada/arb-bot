# models/order_book.py
class OrderBook:
    """A class to manage and display order book data for prediction markets."""
    
    def __init__(self, market_id):
        """Initialize an empty order book for a market ID (e.g., asset_id or ticker)."""
        self.market_id = market_id
        self.bids = []  # List of [price, qty] pairs
        self.asks = []  # List of [price, qty] pairs
    
    def update_polymarket(self, bids=None, asks=None):
        """Update with Polymarket-style data."""
        try:
            if bids is not None:
                self.bids = [(float(price), float(size)) for price, size in bids]
                self.bids.sort(reverse=True)  # Highest bids first
            if asks is not None:
                self.asks = [(float(price), float(size)) for price, size in asks]
                self.asks.sort()  # Lowest asks first
        except (ValueError, TypeError) as e:
            print(f"Error updating Polymarket data for {self.market_id}: {e}")

    def update_kalshi(self, yes=None, no=None, delta=None):
        """Update with Kalshi-style data (snapshot or delta)."""
        try:
            if yes is not None:
                self.bids = [(float(price), float(qty)) for price, qty in yes]
                self.bids.sort(reverse=True)
            if no is not None:
                self.asks = [(float(price), float(qty)) for price, qty in no]
                self.asks.sort()
            if delta is not None:
                side = delta["side"]
                price = float(delta["price"])
                delta_qty = float(delta["delta"])
                target = self.bids if side == "yes" else self.asks
                # Find and update existing entry or append new one
                for i, (p, q) in enumerate(target):
                    if p == price:
                        new_qty = q + delta_qty
                        if new_qty <= 0:
                            target.pop(i)
                        else:
                            target[i] = (price, new_qty)
                        break
                else:
                    if delta_qty > 0:
                        target.append((price, delta_qty))
                target.sort(reverse=True) if side == "yes" else target.sort()
        except (ValueError, TypeError, KeyError) as e:
            print(f"Error updating Kalshi data for {self.market_id}: {e}")

    def display(self):
        """Display the full order book in a unified format."""
        print(f"\nOrder Book for {self.market_id}:")
        print("Bids (highest first):", self.bids)
        print("Asks (lowest first):", self.asks)