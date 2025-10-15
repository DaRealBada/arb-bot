import os
import requests
from dotenv import load_dotenv
from eth_account import Account
from web3 import Web3

load_dotenv()

PRIVATE_KEY = os.getenv("POLYMARKET_PRIVATE_KEY")
FUNDER_ADDRESS = os.getenv("POLYMARKET_FUNDER_ADDRESS")

print("="*80)
print("POLYMARKET SETUP VERIFICATION")
print("="*80)

# 1. Check if credentials exist
print("\n1️⃣ Checking .env configuration...")
if not PRIVATE_KEY:
    print("❌ POLYMARKET_PRIVATE_KEY is missing from .env")
else:
    print(f"✅ POLYMARKET_PRIVATE_KEY found (length: {len(PRIVATE_KEY)})")

if not FUNDER_ADDRESS:
    print("❌ POLYMARKET_FUNDER_ADDRESS is missing from .env")
else:
    print(f"✅ POLYMARKET_FUNDER_ADDRESS found: {FUNDER_ADDRESS}")

if not PRIVATE_KEY or not FUNDER_ADDRESS:
    print("\n⚠️  Please add missing values to your .env file")
    exit(1)

# 2. Verify private key format
print("\n2️⃣ Verifying private key format...")
try:
    # Add 0x prefix if not present
    if not PRIVATE_KEY.startswith('0x'):
        private_key_formatted = '0x' + PRIVATE_KEY
    else:
        private_key_formatted = PRIVATE_KEY
    
    # Derive the account from private key
    account = Account.from_key(private_key_formatted)
    derived_address = account.address
    
    print(f"✅ Private key is valid")
    print(f"   Derived address: {derived_address}")
    
except Exception as e:
    print(f"❌ Invalid private key format: {e}")
    exit(1)

# 3. Check if derived address matches funder address
print("\n3️⃣ Checking address consistency...")
funder_normalized = Web3.to_checksum_address(FUNDER_ADDRESS)
derived_normalized = Web3.to_checksum_address(derived_address)

if funder_normalized == derived_normalized:
    print(f"✅ Funder address matches derived address")
    print(f"   This is correct for EOA (Externally Owned Account)")
else:
    print(f"⚠️  Funder address does NOT match derived address")
    print(f"   Derived:  {derived_normalized}")
    print(f"   Funder:   {funder_normalized}")
    print(f"   This is normal for proxy wallets (Magic Link)")

# 4. Check Polygon balance
print("\n4️⃣ Checking Polygon (MATIC) balance...")
try:
    # Connect to Polygon RPC
    w3 = Web3(Web3.HTTPProvider('https://polygon-rpc.com'))
    
    # Check balance of funder address
    balance_wei = w3.eth.get_balance(funder_normalized)
    balance_matic = w3.from_wei(balance_wei, 'ether')
    
    print(f"   MATIC Balance: {balance_matic:.6f} MATIC")
    
    if balance_matic == 0:
        print(f"   ⚠️  No MATIC found - you need MATIC for gas fees")
    else:
        print(f"   ✅ Has MATIC for gas")
        
except Exception as e:
    print(f"   ❌ Could not check balance: {e}")

# 5. Check USDC balance on Polygon
print("\n5️⃣ Checking USDC balance on Polygon...")
try:
    # USDC contract on Polygon
    USDC_ADDRESS = "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"
    
    # ERC20 ABI (minimal - just balanceOf)
    ERC20_ABI = [
        {
            "constant": True,
            "inputs": [{"name": "_owner", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "balance", "type": "uint256"}],
            "type": "function"
        }
    ]
    
    usdc_contract = w3.eth.contract(address=USDC_ADDRESS, abi=ERC20_ABI)
    usdc_balance_raw = usdc_contract.functions.balanceOf(funder_normalized).call()
    usdc_balance = usdc_balance_raw / 1e6  # USDC has 6 decimals
    
    print(f"   USDC Balance: ${usdc_balance:.2f}")
    
    if usdc_balance == 0:
        print(f"   ❌ No USDC found - you need USDC to trade on Polymarket")
    else:
        print(f"   ✅ Has USDC for trading")
        
except Exception as e:
    print(f"   ⚠️  Could not check USDC balance: {e}")

# 6. Check if address is registered on Polymarket
print("\n6️⃣ Checking Polymarket registration...")
try:
    # Try to fetch user data from Polymarket API
    response = requests.get(
        f"https://gamma-api.polymarket.com/profile/{funder_normalized}",
        timeout=10
    )
    
    if response.status_code == 200:
        profile = response.json()
        print(f"   ✅ Address is registered on Polymarket")
        print(f"   Username: {profile.get('username', 'Not set')}")
    elif response.status_code == 404:
        print(f"   ⚠️  Address not found in Polymarket system")
        print(f"   You may need to make a trade on polymarket.com first")
    else:
        print(f"   ⚠️  Could not verify registration (status: {response.status_code})")
        
except Exception as e:
    print(f"   ⚠️  Could not check registration: {e}")

# Summary and recommendations
print("\n" + "="*80)
print("SUMMARY & RECOMMENDATIONS")
print("="*80)

recommendations = []

if balance_matic == 0:
    recommendations.append("❗ Get MATIC: Bridge small amount (~0.1 MATIC) for gas fees")

if usdc_balance == 0:
    recommendations.append("❗ Get USDC: Deposit USDC to start trading (minimum $10 recommended)")

if funder_normalized != derived_normalized:
    recommendations.append("ℹ️  Using proxy wallet - this is normal for Magic Link accounts")
else:
    recommendations.append("ℹ️  Using EOA wallet - make sure this matches your Polymarket login")

if not recommendations:
    print("✅ All checks passed! Your setup looks good.")
    print("   If API key creation still fails, try:")
    print("   1. Make at least one trade on polymarket.com to activate your account")
    print("   2. Wait 24 hours after first deposit/trade")
    print("   3. Contact Polymarket support if issues persist")
else:
    print("\nTo fix the 'Could not create api key' error:\n")
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec}")

print("\n" + "="*80)