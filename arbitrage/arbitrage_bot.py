import asyncio
import os
import logging
from data import OrderBookManager
from kalshi import KalshiClient
from polymarket import PolymarketClient

class ArbitrageBot:
    def __init__(self, order_book_manager):
        self.order_book_manager = order_book_manager

    def find_arbitrage_opportunities(self):
        """
        Finds arbitrage opportunities with correctly sorted Kalshi asks based on converted prices
        """
        comparison = self.order_book_manager.compare_specific_markets()
    
        # Extract order books
        kalshi_bids = comparison["kalshi_450_499"]["yes"]["bids"]
        kalshi_asks = comparison["kalshi_450_499"]["yes"]["asks"]
        poly_450_474_bids = comparison["poly_450_474"]["yes"]["bids"]
        poly_450_474_asks = comparison["poly_450_474"]["yes"]["asks"]
        poly_475_499_bids = comparison["poly_475_499"]["yes"]["bids"]
        poly_475_499_asks = comparison["poly_475_499"]["yes"]["asks"]
    
        # Sort Kalshi asks by converted price (1 - price) in ascending order
        if kalshi_asks:
            kalshi_asks = sorted(kalshi_asks, key=lambda x: 1 - x[0])
    
        opportunities = []
    
        # Formula 1: Buy Kalshi YES (ask), Sell Polymarket YES (bids)
        if kalshi_asks and poly_450_474_bids and poly_475_499_bids:
            kalshi_ask_price, kalshi_ask_size = kalshi_asks[0]  # Best YES ask (highest YES = lowest NO)
            poly_450_474_bid_price, poly_450_474_bid_size = poly_450_474_bids[0]
            poly_475_499_bid_price, poly_475_499_bid_size = poly_475_499_bids[0]
        
            # Convert Kalshi YES ask to NO price (for display)
            kalshi_converted_ask = 1 - kalshi_ask_price
        
            # Profit: Sell Polymarket YES bids - Buy Kalshi YES ask
            profit = (poly_450_474_bid_price + poly_475_499_bid_price) - kalshi_ask_price
        
            max_size = min(kalshi_ask_size, poly_450_474_bid_size, poly_475_499_bid_size)
        
            if profit > 0:
                opportunities.append({
                    "formula": "Formula 1: (Poly_450_474_Bid + Poly_475_499_Bid) - Kalshi_Ask",
                    "type": "Buy Kalshi YES Ask, Sell Polymarket YES Bids",
                    "kalshi_price": kalshi_ask_price,
                    "kalshi_converted_price": kalshi_converted_ask,
                    "poly_450_474_price": poly_450_474_bid_price,
                    "poly_475_499_price": poly_475_499_bid_price,
                    "poly_combined": poly_450_474_bid_price + poly_475_499_bid_price,
                    "profit": profit,
                    "max_size": max_size,
                    "total_profit": profit * max_size
                })
    
        # Formula 2: Buy Polymarket YES (asks), Sell Kalshi YES (bid)
        if kalshi_bids and poly_450_474_asks and poly_475_499_asks:
            kalshi_bid_price, kalshi_bid_size = kalshi_bids[0]  # Best YES bid
            poly_450_474_ask_price, poly_450_474_ask_size = poly_450_474_asks[0]
            poly_475_499_ask_price, poly_475_499_ask_size = poly_475_499_asks[0]
        
            # Convert Kalshi YES bid to NO price (for display)
            kalshi_converted_bid = 1 - kalshi_bid_price
        
            # Profit: Sell Kalshi YES bid - Buy Polymarket YES asks
            profit = kalshi_bid_price - (poly_450_474_ask_price + poly_475_499_ask_price)
        
            max_size = min(kalshi_bid_size, poly_450_474_ask_size, poly_475_499_ask_size)
        
            if profit > 0:
                opportunities.append({
                    "formula": "Formula 2: Kalshi_Bid - (Poly_450_474_Ask + Poly_475_499_Ask)",
                    "type": "Buy Polymarket YES Asks, Sell Kalshi YES Bid",
                    "kalshi_price": kalshi_bid_price,
                    "kalshi_converted_price": kalshi_converted_bid,
                    "poly_450_474_price": poly_450_474_ask_price,
                    "poly_475_499_price": poly_475_499_ask_price,
                    "poly_combined": poly_450_474_ask_price + poly_475_499_ask_price,
                    "profit": profit,
                    "max_size": max_size,
                    "total_profit": profit * max_size
                })
    
        return opportunities

    def print_opportunities(self):
        """Print identified arbitrage opportunities"""
        opportunities = self.find_arbitrage_opportunities()
        
        if not opportunities:
            print("\nNo arbitrage opportunities found.")
            return
        
        print("\n=== ARBITRAGE OPPORTUNITIES ===")
        for i, opp in enumerate(opportunities, 1):
            print(f"\nOpportunity #{i}: {opp['type']}")
            print(f"  Using {opp['formula']}")
            print(f"  Profit: {opp['profit']:.4f}")
            
            if "Buy Kalshi Ask" in opp['type']:
                print(f"  Action: Buy on Kalshi at {opp['kalshi_price']:.4f} (Converted: {opp['kalshi_converted_price']:.4f})")
                print(f"          Sell on Polymarket 450-474 at {opp['poly_450_474_price']:.4f}")
                print(f"          Sell on Polymarket 475-499 at {opp['poly_475_499_price']:.4f}")
                print(f"          Combined Polymarket: {opp['poly_combined']:.4f}")
            else:
                print(f"  Action: Buy on Polymarket 450-474 at {opp['poly_450_474_price']:.4f}")
                print(f"          Buy on Polymarket 475-499 at {opp['poly_475_499_price']:.4f}")
                print(f"          Combined Polymarket: {opp['poly_combined']:.4f}")
                print(f"          Sell on Kalshi at {opp['kalshi_price']:.4f} (Converted: {opp['kalshi_converted_price']:.4f})")
            
            print(f"  Max Size: {opp['max_size']:.2f}")
            print(f"  Total Profit: ${opp['total_profit']:.2f}")

    def print_market_details(self):
        """Print current market details and calculate arbitrage opportunities"""
        comparison = self.order_book_manager.compare_specific_markets()
        
        print("\n=== CURRENT MARKET DETAILS ===")
        
        # Kalshi
        kalshi_bids = comparison["kalshi_450_499"]["yes"]["bids"]
        kalshi_asks = comparison["kalshi_450_499"]["yes"]["asks"]
        
        print("Kalshi 450-499:")
        if kalshi_bids:
            best_bid = kalshi_bids[0]
            print(f"  Best Bid: {best_bid[0]:.4f}, Size: {best_bid[1]:.2f}")
        else:
            print("  No bids available")
        
        if kalshi_asks:
            best_ask = kalshi_asks[0]
            print(f"  Best Ask: {best_ask[0]:.4f}, Size: {best_ask[1]:.2f}")
        else:
            print("  No asks available")
        
        # Polymarket 450-474
        poly_450_474_bids = comparison["poly_450_474"]["yes"]["bids"]
        poly_450_474_asks = comparison["poly_450_474"]["yes"]["asks"]
        
        print("Polymarket 450-474:")
        if poly_450_474_bids:
            best_bid = poly_450_474_bids[0]
            print(f"  Best Bid: {best_bid[0]:.4f}, Size: {best_bid[1]:.2f}")
        else:
            print("  No bids available")
        
        if poly_450_474_asks:
            best_ask = poly_450_474_asks[0]
            print(f"  Best Ask: {best_ask[0]:.4f}, Size: {best_ask[1]:.2f}")
        else:
            print("  No asks available")
        
        # Polymarket 475-499
        poly_475_499_bids = comparison["poly_475_499"]["yes"]["bids"]
        poly_475_499_asks = comparison["poly_475_499"]["yes"]["asks"]
        
        print("Polymarket 475-499:")
        if poly_475_499_bids:
            best_bid = poly_475_499_bids[0]
            print(f"  Best Bid: {best_bid[0]:.4f}, Size: {best_bid[1]:.2f}")
        else:
            print("  No bids available")
        
        if poly_475_499_asks:
            best_ask = poly_475_499_asks[0]
            print(f"  Best Ask: {best_ask[0]:.4f}, Size: {best_ask[1]:.2f}")
        else:
            print("  No asks available")
        
        # Calculate and display arbitrage opportunities
        print("\n=== ARBITRAGE OPPORTUNITIES ===")
        opportunities_found = False
        
        # Formula 1: (Polymarket_450_474_Bid + Polymarket_475_499_Bid) - Kalshi_Ask
        if kalshi_asks and poly_450_474_bids and poly_475_499_bids:
            kalshi_ask_price, kalshi_ask_size = kalshi_asks[0]
            poly_450_474_bid_price, poly_450_474_bid_size = poly_450_474_bids[0]
            poly_475_499_bid_price, poly_475_499_bid_size = poly_475_499_bids[0]
            
            profit = (poly_450_474_bid_price + poly_475_499_bid_price) - kalshi_ask_price
            max_size = min(kalshi_ask_size, poly_450_474_bid_size, poly_475_499_bid_size)
            
            if profit > 0:
                opportunities_found = True
                print("\nOpportunity #1: Buy Kalshi Ask, Sell Polymarket Bids")
                print(f"  Formula: (Poly_450_474_Bid + Poly_475_499_Bid) - Kalshi_Ask")
                print(f"  Profit per unit: {profit:.4f}")
                print(f"  Action: Buy on Kalshi at {kalshi_ask_price:.4f}")
                print(f"          Sell on Polymarket 450-474 at {poly_450_474_bid_price:.4f}")
                print(f"          Sell on Polymarket 475-499 at {poly_475_499_bid_price:.4f}")
                print(f"  Max Size: {max_size:.2f}")
                print(f"  Total Profit: ${profit * max_size:.2f}")
        
        # Formula 2: Kalshi_Bid - (Polymarket_450_474_Ask + Polymarket_475_499_Ask)
        if kalshi_bids and poly_450_474_asks and poly_475_499_asks:
            kalshi_bid_price, kalshi_bid_size = kalshi_bids[0]
            poly_450_474_ask_price, poly_450_474_ask_size = poly_450_474_asks[0]
            poly_475_499_ask_price, poly_475_499_ask_size = poly_475_499_asks[0]
            
            profit = kalshi_bid_price - (poly_450_474_ask_price + poly_475_499_ask_price)
            max_size = min(kalshi_bid_size, poly_450_474_ask_size, poly_475_499_ask_size)
            
            if profit > 0:
                opportunities_found = True
                print("\nOpportunity #2: Buy Polymarket Asks, Sell Kalshi Bid")
                print(f"  Formula: Kalshi_Bid - (Poly_450_474_Ask + Poly_475_499_Ask)")
                print(f"  Profit per unit: {profit:.4f}")
                print(f"  Action: Buy on Polymarket 450-474 at {poly_450_474_ask_price:.4f}")
                print(f"          Buy on Polymarket 475-499 at {poly_475_499_ask_price:.4f}")
                print(f"          Sell on Kalshi at {kalshi_bid_price:.4f}")
                print(f"  Max Size: {max_size:.2f}")
                print(f"  Total Profit: ${profit * max_size:.2f}")
        
        if not opportunities_found:
            print("No arbitrage opportunities found.")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

async def run_arbitrage_bot():
    kalshi_client = KalshiClient()
    polymarket_client = PolymarketClient()
    
    polymarket_client.run()
    if not polymarket_client.wait_for_initial_data(timeout=10):
        print("Failed to get initial Polymarket data, exiting...")
        return
    
    order_book_manager = OrderBookManager(kalshi_client, polymarket_client)
    kalshi_task = asyncio.create_task(run_kalshi(kalshi_client))
    
    await asyncio.sleep(2)
    
    try:
        while True:
            os.system('cls' if os.name == 'nt' else 'clear')
            
            # Fetch fresh data
            order_book_manager.update_order_books()
            logger.debug(f"Polymarket order books: {len(order_book_manager.combined_order_books['polymarket'])} assets")
            
            order_book_manager.print_comparison()
            arb_bot = ArbitrageBot(order_book_manager)
            arb_bot.print_market_details()
            
            await asyncio.sleep(5)
            
    except KeyboardInterrupt:
        print("Shutting down...")
        kalshi_task.cancel()
        try:
            await kalshi_task
        except asyncio.CancelledError:
            print("Kalshi task cancelled successfully")

async def run_kalshi(kalshi_client):
    await kalshi_client.run()

if __name__ == "__main__":
    asyncio.run(run_arbitrage_bot())