import os
import asyncio
from dotenv import load_dotenv
from py_clob_client.client import ClobClient

# Load the .env file containing your PRIVATE KEY and FUNDER ADDRESS
load_dotenv()

# --- Configuration ---
HOST = "https://clob.polymarket.com"
CHAIN_ID = 137 # Polygon

PRIVATE_KEY = os.getenv("POLYMARKET_PRIVATE_KEY")
FUNDER_ADDRESS = os.getenv("POLYMARKET_FUNDER_ADDRESS") # NEW: Load the Funder Address

if not PRIVATE_KEY:
    raise ValueError("POLYMARKET_PRIVATE_KEY not found in .env file.")

# Check for funder address if the previous steps indicated it's a proxy wallet
# If you are using a Magic Link/Email account, the funder address is mandatory.
if not FUNDER_ADDRESS:
    # Based on the user's Magic Link setup, this should be the address 0x0d64B8536f2Dca9f18990cC896a50E087A3Bf027
    raise ValueError("POLYMARKET_FUNDER_ADDRESS not found in .env file. This is required for Magic Link accounts.")

# --- Derivation Function ---
async def derive_and_print_credentials():
    print("Connecting to CLOB and deriving new API credentials...")
    
    # Initialize the client using your Private Key for signing
    # NOTE: signature_type=1 is used for Magic Link/Email accounts
    client = ClobClient(
        host=HOST, 
        key=PRIVATE_KEY, 
        chain_id=CHAIN_ID, 
        signature_type=1, # Updated from 0 to 1 for Magic Link/Email
        funder=FUNDER_ADDRESS # Added the funder/proxy address
    )

    try:
        print("Attempting to CREATE a brand new, unique set of API credentials...")
        
        # 1. Force the creation of new credentials (instead of just deriving the old one)
        creds = client.create_api_key()
        
        # 2. Print the new values
        print("\n🎉 BRAND NEW CLOB API CREDENTIALS CREATED SUCCESSFULLY! 🎉")
        print("-----------------------------------------------------")
        print(f"Update POLYMARKET_API_KEY with:   {creds.apiKey}")
        print(f"Update POLYMARKET_API_SECRET with: {creds.secret}")
        print(f"Update POLYMARKET_PASSPHRASE with: {creds.passphrase}")
        print("-----------------------------------------------------")
        print("✅ THESE NEW KEYS MUST BE USED IN YOUR .env FILE.")

    except Exception as e:
        print(f"\n🚨 CRITICAL ERROR during NEW credential creation: {e}")
        print("This usually means the Private Key is invalid, the Funder Address is incorrect, or the account is not funded/onboarded.")
        # Re-raise the error for better debugging
        raise

if __name__ == "__main__":
    asyncio.run(derive_and_print_credentials())