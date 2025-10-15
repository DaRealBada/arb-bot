# arbitrage_bot.py
import asyncio
import os
import logging
from data.order_book import OrderBookManager
from polymarket.polymarket_client import PolymarketClient 
from gamma_fetch import get_market_mapping_for_bot # This is also missing


class ArbitrageBot:
    def __init__(self, order_book_manager):
        self.order_book_manager = order_book_manager
        self.opportunities = []

    def find_arbitrage_opportunities(self):
        """
        Finds arbitrage opportunities within the single Polymarket (US Recession)
        """
        comparison = self.order_book_manager.compare_specific_markets()
        self.opportunities = []
        market_slug = "poly_us_recession_2025"

        market_data = comparison.get(market_slug, {})
        
        # Get best bid for YES and best ask for NO
        yes_bids = market_data.get("yes", {}).get("bids", [])
        no_asks = market_data.get("no", {}).get("asks", [])
        
        # Get best bid for NO and best ask for YES
        no_bids = market_data.get("no", {}).get("bids", [])
        yes_asks = market_data.get("yes", {}).get("asks", [])
        
        if not (yes_bids and no_asks and no_bids and yes_asks):
            return

        best_yes_bid = yes_bids[0][0]
        best_no_ask = no_asks[0][0]
        best_no_bid = no_bids[0][0]
        best_yes_ask = yes_asks[0][0]
        
        # Arbitrage check 1: (YES Bid + NO Bid) > 1.00 - Not possible on Polymarket
        # Arbitrage check 2: Best YES Bid > 1.00 - Best NO Ask
        # If Best YES Bid + Best NO Bid > 1.00, we have an internal arb (highly unlikely, but possible)
        # We check for a bid/ask crossing (e.g. Sell YES and Buy NO where P_yes + P_no > 1)
        
        # Internal arbitrage opportunity: Bid/Ask cross where Bid(A) + Bid(B) > 1.00
        # Check if the highest price anyone is willing to buy for YES (Bid)
        # and the highest price anyone is willing to buy for NO (Bid) sum to more than 1.00
        if best_yes_bid + best_no_bid > 1.00:
            profit_percent = (best_yes_bid + best_no_bid - 1.00) * 100
            self.opportunities.append({
                "formula": "YES Bid + NO Bid > 1.00",
                "type": "Internal Market Arbitrage (Polymarket)",
                "profit": profit_percent,
                "details": f"Buy NO at {best_no_ask:.4f} and Sell YES at {best_yes_bid:.4f} for {profit_percent:.2f}% profit on the total position."
            })

    def print_opportunities(self):
        """Prints the discovered arbitrage opportunities."""
        if self.opportunities:
            print("\n🎉 ARBITRAGE OPPORTUNITY FOUND!")
            for opp in self.opportunities:
                print("--------------------------------------------------")
                print(f"Type:    {opp['type']}")
                print(f"Formula: {opp['formula']}")
                print(f"Profit:  {opp['profit']:.2f}%")
                print(f"Action:  {opp['details']}")
            print("--------------------------------------------------")
        else:
            print("\n... No arbitrage opportunities found (Internal market spread check).")

    def print_market_summary(self):
        """Prints summary of all tracked markets."""
        comparison = self.order_book_manager.compare_specific_markets()
        
        print("\n" + "="*80)
        print(f"📊 Market Summary - {len(comparison)} Markets")
        print("="*80)
        
        for slug, data in comparison.items():
            info = self.order_book_manager.get_market_info(slug)
            question = info.get('question', slug)
            
            yes_bids = data.get("yes", {}).get("bids", [])
            yes_asks = data.get("yes", {}).get("asks", [])
            no_bids = data.get("no", {}).get("bids", [])
            no_asks = data.get("no", {}).get("asks", [])
            
            print(f"\n{question}")
            if yes_bids and yes_asks:
                print(f"  YES: Bid ${yes_bids[0][0]:.4f} | Ask ${yes_asks[0][0]:.4f}")
            if no_bids and no_asks:
                print(f"  NO:  Bid ${no_bids[0][0]:.4f} | Ask ${no_asks[0][0]:.4f}")
            
            if yes_bids and no_bids:
                print(f"  Sum bids: {yes_bids[0][0] + no_bids[0][0]:.4f}")

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# --- Main Polymarket-only Arbitrage Runner ---
async def run_arbitrage_bot():
    polymarket_client = PolymarketClient()

    polymarket_client.run()
    if not polymarket_client.wait_for_initial_data(timeout=60):
        print("Failed to get initial Polymarket data, exiting...")
        return

    order_book_manager = OrderBookManager(None, polymarket_client)
    arb_bot = ArbitrageBot(order_book_manager)

    # await asyncio.sleep(2)

    try:
        while True:
            os.system("cls" if os.name == "nt" else "clear")

            order_book_manager.update_order_books()
            
            # Find and print opportunities
            arb_bot.find_arbitrage_opportunities()
            arb_bot.print_opportunities()
            
            # Show best bids/asks for the markets being compared
            comparison = order_book_manager.compare_specific_markets()
            market_data = comparison.get("poly_us_recession_2025", {})

            yes_bids = market_data.get("yes", {}).get("bids", [])
            yes_asks = market_data.get("yes", {}).get("asks", [])
            no_bids = market_data.get("no", {}).get("bids", [])
            no_asks = market_data.get("no", {}).get("asks", [])

            print("\n--- Market Data Snapshot: US Recession 2025 ---")
            print("YES Outcome (Token 1):")
            print(f"    Best Bid: {yes_bids[0][0]:.4f}, Size: {yes_bids[0][1]:.2f}" if yes_bids else "    No bids available")
            print(f"    Best Ask: {yes_asks[0][0]:.4f}, Size: {yes_asks[0][1]:.2f}" if yes_asks else "    No asks available")

            print("NO Outcome (Token 2):")
            print(f"    Best Bid: {no_bids[0][0]:.4f}, Size: {no_bids[0][1]:.2f}" if no_bids else "    No bids available")
            print(f"    Best Ask: {no_asks[0][0]:.4f}, Size: {no_asks[0][1]:.2f}" if no_asks else "    No asks available\n")


            await asyncio.sleep(0.5) 

    except KeyboardInterrupt:
        logger.info("Bot stopped manually.")
    except Exception as e:
        logger.error(f"An error occurred in the main loop: {e}")
        await asyncio.sleep(5)