# arbitrage_bot.py
import asyncio
import os
import logging
from data import OrderBookManager
from polymarket import PolymarketClient


class ArbitrageBot:
    def __init__(self, order_book_manager):
        self.order_book_manager = order_book_manager

    def find_arbitrage_opportunities(self):
        """
        Finds arbitrage opportunities (Polymarket-only version)
        """
        comparison = self.order_book_manager.compare_specific_markets()

        # --- MODIFIED: Use new market keys ---
        poly_2_cuts_bids = comparison["poly_2_cuts"]["yes"]["bids"]
        poly_2_cuts_asks = comparison["poly_2_cuts"]["yes"]["asks"]
        poly_3_cuts_bids = comparison["poly_3_cuts"]["yes"]["bids"]
        poly_3_cuts_asks = comparison["poly_3_cuts"]["yes"]["asks"]

        opportunities = []

        # Simple example: check spread between Polymarket submarkets
        if poly_2_cuts_bids and poly_3_cuts_asks:
            bid_price = poly_2_cuts_bids[0][0]
            ask_price = poly_3_cuts_asks[0][0]
            profit = bid_price - ask_price

            if profit > 0:
                opportunities.append({
                    # --- MODIFIED: Update formula and details for clarity ---
                    "formula": "Poly '2 Cuts' Bid - Poly '3 Cuts' Ask",
                    "type": "Polymarket internal spread",
                    "profit": profit,
                    "details": f"Buy '3 Cuts' YES at {ask_price:.4f}, Sell '2 Cuts' YES at {bid_price:.4f}"
                })

        return opportunities

    def print_opportunities(self):
        """Print identified arbitrage opportunities"""
        opportunities = self.find_arbitrage_opportunities()

        if not opportunities:
            print("\nNo arbitrage opportunities found.")
            return

        print("\n=== POLYMARKET OPPORTUNITIES ===")
        for i, opp in enumerate(opportunities, 1):
            print(f"\nOpportunity #{i}: {opp['type']}")
            print(f"  Formula: {opp['formula']}")
            print(f"  Profit: {opp['profit']:.4f}")
            print(f"  Details: {opp['details']}")

    def print_market_details(self):
        """Prints the best bid/ask for each tracked market."""
        comparison = self.order_book_manager.compare_specific_markets()

        # --- Existing Markets ---
        poly_2_cuts_bids = comparison["poly_2_cuts"]["yes"]["bids"]
        poly_2_cuts_asks = comparison["poly_2_cuts"]["yes"]["asks"]
        poly_3_cuts_bids = comparison["poly_3_cuts"]["yes"]["bids"]
        poly_3_cuts_asks = comparison["poly_3_cuts"]["yes"]["asks"]

        print("\n--- 2 Cuts / 3 Cuts Markets ---")
        print("  2 Cuts Market:")
        print(f"    Best Bid: {poly_2_cuts_bids[0][0]:.4f}, Size: {poly_2_cuts_bids[0][1]:.2f}" if poly_2_cuts_bids else "    No bids available")
        print(f"    Best Ask: {poly_2_cuts_asks[0][0]:.4f}, Size: {poly_2_cuts_asks[0][1]:.2f}" if poly_2_cuts_asks else "    No asks available")

        print("  3 Cuts Market:")
        print(f"    Best Bid: {poly_3_cuts_bids[0][0]:.4f}, Size: {poly_3_cuts_bids[0][1]:.2f}" if poly_3_cuts_bids else "    No bids available")
        print(f"    Best Ask: {poly_3_cuts_asks[0][0]:.4f}, Size: {poly_3_cuts_asks[0][1]:.2f}" if poly_3_cuts_asks else "    No asks available")

        # --- NEW: Print Solana Market Data ---
        poly_solana_up_bids = comparison["poly_solana_up"]["yes"]["bids"]
        poly_solana_up_asks = comparison["poly_solana_up"]["yes"]["asks"]
        poly_solana_down_bids = comparison["poly_solana_down"]["yes"]["bids"]
        poly_solana_down_asks = comparison["poly_solana_down"]["yes"]["asks"]

        print("\n--- Solana Up/Down Market ---")
        print("  UP Outcome:")
        print(f"    Best Bid: {poly_solana_up_bids[0][0]:.4f}, Size: {poly_solana_up_bids[0][1]:.2f}" if poly_solana_up_bids else "    No bids available")
        print(f"    Best Ask: {poly_solana_up_asks[0][0]:.4f}, Size: {poly_solana_up_asks[0][1]:.2f}" if poly_solana_up_asks else "    No asks available")

        print("  DOWN Outcome:")
        print(f"    Best Bid: {poly_solana_down_bids[0][0]:.4f}, Size: {poly_solana_down_bids[0][1]:.2f}" if poly_solana_down_bids else "    No bids available")
        print(f"    Best Ask: {poly_solana_down_asks[0][0]:.4f}, Size: {poly_solana_down_asks[0][1]:.2f}" if poly_solana_down_asks else "    No asks available")

        # --- END NEW SOLANA PRINT ---
        self.print_opportunities()


# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# --- Main Polymarket-only Arbitrage Runner ---
async def run_arbitrage_bot():
    polymarket_client = PolymarketClient()

    polymarket_client.run()
    if not polymarket_client.wait_for_initial_data(timeout=20): 
        print("Failed to get initial Polymarket data, exiting...")
        return

    order_book_manager = OrderBookManager(None, polymarket_client)

    await asyncio.sleep(2)

    try:
        while True:
            os.system("cls" if os.name == "nt" else "clear")

            order_book_manager.update_order_books()
            logger.debug(
                f"Polymarket order books: {len(order_book_manager.combined_order_books['polymarket'])} assets"
            )

            arb_bot = ArbitrageBot(order_book_manager)
            arb_bot.print_market_details()

            await asyncio.sleep(5)

    except KeyboardInterrupt:
        print("Shutting down...")


if __name__ == "__main__":
    asyncio.run(run_arbitrage_bot())