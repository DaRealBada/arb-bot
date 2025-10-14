# main.py
import asyncio
# from kalshi import KalshiClient  # Disabled Kalshi imports for Polymarket-only mode
from polymarket import PolymarketClient
from data import OrderBookManager
from arbitrage import ArbitrageBot, run_arbitrage_bot


# --- Kalshi function removed ---
# async def run_kalshi(kalshi_client):
#     await kalshi_client.run()


async def run_order_book_manager(order_book_manager):
    while True:
        order_book_manager.print_comparison()
        await asyncio.sleep(2)


async def main():
    # Choose which mode to run:
    # 1. Original order book comparison mode
    # 2. New arbitrage bot mode
    mode = "arbitrage"  # Change to "order_book" for the original comparison mode

    if mode == "arbitrage":
        # Run the Polymarket-only arbitrage bot
        await run_arbitrage_bot()

    else:
        # Polymarket-only order book comparison
        polymarket_client = PolymarketClient()
        polymarket_client.run()
        order_book_manager = OrderBookManager(None, polymarket_client)

        # Wait for initial data
        await asyncio.sleep(1)

        try:
            await run_order_book_manager(order_book_manager)
        except KeyboardInterrupt:
            print("Shutting down...")


if __name__ == "__main__":
    asyncio.run(main())
