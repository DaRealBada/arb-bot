import asyncio
import os
import logging
import sys
# Import the new dynamic classes/functions
from polymarket import PolymarketClient
from data.order_book import OrderBookManager 
from polymarket.polymarket_client import PolymarketClient
from arbitrage.arbitrage_bot import ArbitrageBot 
from gamma_fetch import get_market_mapping_for_bot # gamma_fetch is still in root

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --- Configuration for Dynamic Market Fetching ---
# Set the event slug you want to track
EVENT_SLUG = "us-recession-in-2025" 
# Set a minimum liquidity threshold (in USD) to filter out inactive markets
MIN_LIQUIDITY = 1000 

async def run_arbitrage_bot():
    """
    Orchestrates the dynamic market fetching, client connection, and arbitrage loop.
    """
    # 1. Fetch dynamic market mapping and tokens using gamma_fetch
    logger.info(f"Step 1: Fetching market mapping for event '{EVENT_SLUG}'...")
    market_mapping = get_market_mapping_for_bot(EVENT_SLUG, min_liquidity=MIN_LIQUIDITY)

    if not market_mapping:
        logger.error(f"Failed to find any active binary markets with >${MIN_LIQUIDITY} liquidity for {EVENT_SLUG}. Exiting.")
        sys.exit(1)

    market_count = len(market_mapping)
    token_count = market_count * 2
    logger.info(f"✅ Found {market_count} markets (total {token_count} tokens) to monitor.")

    # 2. Initialize Polymarket Client with the fetched tokens
    # PolymarketClient will extract the {yes_token_id, no_token_id} from the mapping
    polymarket_client = PolymarketClient(token_ids=market_mapping)
    polymarket_client.run()

    # Wait for the WebSocket to connect and receive initial data
    if not polymarket_client.wait_for_initial_data(timeout=60):
        logger.error("🚨 Failed to receive initial Polymarket data from WebSocket, check your .env credentials or network.")
        return
    
    # 3. Initialize OrderBookManager with the fetched mapping
    order_book_manager = OrderBookManager(None, polymarket_client, market_mapping)
    arb_bot = ArbitrageBot(order_book_manager)

    await asyncio.sleep(1) # Wait briefly for stable connection

    try:
        while True:
            # Clear screen for cleaner output
            os.system("cls" if os.name == "nt" else "clear")

            order_book_manager.update_order_books()
            
            # Find and print opportunities for ALL markets
            arb_bot.find_arbitrage_opportunities()
            arb_bot.print_opportunities()
            
            # Print a summary of ALL tracked markets
            arb_bot.print_market_summary()

            await asyncio.sleep(0.5) 

    except KeyboardInterrupt:
        logger.info("Bot stopped manually.")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")


async def main():
    await run_arbitrage_bot()


if __name__ == "__main__":
    try:
        # Start the asynchronous event loop
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Main program terminated.")