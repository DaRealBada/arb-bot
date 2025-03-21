from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON

host = "https://clob.polymarket.com"
chain_id = POLYGON
private_key = "POLYMARKET_PRIVATE_KEY"
client = ClobClient(host, key=private_key, chain_id=chain_id)

token_id = "1742349222751"  # From the URL
order_book = client.get_order_book(token_id)

print("Bids (Buy Orders):")
for bid in order_book["bids"]:
    print(f"Price: {bid['price']}, Size: {bid['size']}")
print("Asks (Sell Orders):")
for ask in order_book["asks"]:
    print(f"Price: {ask['price']}, Size: {ask['size']}")