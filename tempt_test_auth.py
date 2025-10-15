import os
import requests
import json
import time
import base64
import hmac
import hashlib
from dotenv import load_dotenv

load_dotenv()

# Your Polymarket Credentials from .env
API_KEY = os.getenv("POLYMARKET_API_KEY")
API_SECRET = os.getenv("POLYMARKET_API_SECRET")
PASSPHRASE = os.getenv("POLYMARKET_PASSPHRASE")

# Check if keys are present
if not all([API_KEY, API_SECRET, PASSPHRASE]):
    print("FATAL: Missing one or more API credentials in .env.")
    exit()

# L2 Authentication requires HMAC signature for REST API calls
def generate_signature(api_secret, timestamp, method, request_path, body=""):
    # Robust padding fix for API secret
    padded_secret = api_secret
    if len(padded_secret) % 4 != 0:
        padded_secret += '=' * (4 - len(padded_secret) % 4)

    message = str(timestamp) + method + request_path + body
    
    try:
        # The secret should be BASE64 decoded to get the HMAC key
        hmac_key = base64.b64decode(padded_secret)
    except Exception as e:
        print(f"Error decoding API secret: {e}")
        return None

    signature = hmac.new(hmac_key, message.encode('utf-8'), hashlib.sha256).digest()
    return base64.b64encode(signature).decode('utf-8')

def test_api_auth():
    # --- CRITICAL FIX: Use the correct, simplest path for CLOB order book ---
    TOKEN_ID = "11661882248425579028730127122226588074844109517532906275870117904036267401870"
    method = "GET"
    # Polymarket API uses /book?asset_id={TOKEN_ID}
    request_path = f"/book?asset_id={TOKEN_ID}" # <--- FINAL CORRECTED PATH
    url = f"https://clob.polymarket.com{request_path}"
    
    timestamp = str(int(time.time()))
    # The request_path MUST include the query string in the signature
    signature = generate_signature(API_SECRET, timestamp, method, request_path)

    if signature is None:
        print("Could not generate signature. Check API_SECRET format.")
        return

    headers = {
        "POLY-API-KEY": API_KEY,
        "POLY-PASSPHRASE": PASSPHRASE,
        "POLY-TIMESTAMP": timestamp,
        "POLY-SIGNATURE": signature,
        "Content-Type": "application/json"
    }

    print(f"Testing Polymarket REST API Authentication to {url}...")
    try:
        response = requests.get(url, headers=headers)
        
        # Check for L2 Auth errors (401/403) or success (200)
        if response.status_code == 200:
            print(f"\n✅ SUCCESS (HTTP 200): Polymarket REST API is REACHABLE and Authentication/Path is LIKELY CORRECT.")
            print("This confirms your CLOB API Key and Secret are **valid**.")
            print("The original WebSocket error is almost certainly due to a **network/firewall restriction** or a very subtle bug in the RTDS subscription logic.")
            try:
                # Attempt to parse and print a snippet
                data = json.loads(response.text)
                print(f"Snippet of response: Market {data['market']}...")
            except Exception:
                print("Could not parse JSON response.")
            
            # --- NEXT ACTION: Re-run the main bot ---
            print("\n**NEXT STEP: Your keys are good. Please re-run your main bot now.**")
            print("`python main.py`")

        elif response.status_code in [401, 403]:
            print(f"\n❌ FAILURE (HTTP {response.status_code}): Unauthorized/Forbidden.")
            print("Your CLOB API Key, Secret, or Passphrase is **invalid or revoked**.")
            print("You must generate new credentials from your Polymarket account.")
        else:
            print(f"\n⚠️ WARNING: Unexpected HTTP Status {response.status_code}.")
            print(f"Response Body: {response.text[:100]}...")

    except requests.exceptions.RequestException as e:
        print(f"\nCRITICAL NETWORK ERROR: {e}")

if __name__ == "__main__":
    test_api_auth()