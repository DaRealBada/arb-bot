from py_clob_client.client import ClobClient
from web3 import Web3
from dotenv import load_dotenv
import os

load_dotenv()
w3 = Web3()
private_key = os.getenv("POLYMARKET_PRIVATE_KEY")
host = "https://clob.polymarket.com"
chain_id = 137

address = w3.eth.account.from_key(private_key).address
print(f"Using Wallet Address: {address}")

client = ClobClient(host, key=private_key, chain_id=chain_id)
try:
    creds = client.derive_api_key(nonce=0)  # Default nonce is 0
    print("Derived API Credentials:", creds)
except Exception as e:
    print(f"Error deriving API key: {e}")