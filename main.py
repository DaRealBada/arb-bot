import asyncio
from kalshi import KalshiClient
from polymarket import PolymarketClient
from data import OrderBookManager

async def run_kalshi(kalshi_client):
    await kalshi_client.run()

async def main():
    kalshi_client = KalshiClient()
    polymarket_client = PolymarketClient()
    polymarket_client.run()
    order_book_manager = OrderBookManager(kalshi_client, polymarket_client)
    kalshi_task = asyncio.create_task(run_kalshi(kalshi_client))
    
    # Wait longer for initial data
    await asyncio.sleep(5)

    try:
        while True:
            order_book_manager.print_comparison()
            await asyncio.sleep(2)
    except KeyboardInterrupt:
        print("Shutting down...")
        kalshi_task.cancel()
        try:
            await kalshi_task
        except asyncio.CancelledError:
            print("Kalshi task cancelled successfully")

if __name__ == "__main__":
    asyncio.run(main())