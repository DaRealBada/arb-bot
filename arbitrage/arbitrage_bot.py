import logging
from typing import Dict, Any
from datetime import datetime
import time
import os

# --- CORRECTED IMPORTS based on your file structure ---
# Assuming OrderBookManager is defined in data/order_book.py
from data.order_book import OrderBookManager 

# --- CONFIGURATION (Copied from your provided code) ---
logger = logging.getLogger(__name__)

# --- ARBITRAGE BOT CLASS (The main state machine) ---

class ArbitrageBot:
    # Constants should be defined within the class or imported, using class attributes here
    FEE_POLYMARKET = 0.003
    FEE_LIMITLESS = 0.003
    MIN_PROFIT_THRESHOLD = 0.005
    MIN_DOLLAR_PROFIT_THRESHOLD = 1.00
    MAX_VALID_PRICE = 1.00
    MIN_VALID_PRICE = 0.00
    MIN_SAFE_DENOMINATOR = 0.05 
    
    def __init__(self, order_book_manager: OrderBookManager):
        """
        Initializes the ArbitrageBot using dependency injection.
        We only track two lists now: opportunities (current scan) and opp_log (historical).
        """
        self.order_book_manager = order_book_manager
        self.opportunities = [] # Opportunities found in the current scan (RESET EACH SCAN)
        self.opp_log = []       # Historical log of completed opportunities
    
    def find_arbitrage_opportunities(self):
        """Looks for internal and cross-platform arbitrage opportunities."""
        
        # CLEAR the list of opportunities from the previous scan
        self.opportunities = [] 
        
        comparison = self.order_book_manager.compare_specific_markets() 
        
        all_tracked_markets = self.order_book_manager.get_market_list()
        common_markets = self.order_book_manager.get_common_market_slugs() 
        has_common_markets = bool(common_markets)
        
        if not has_common_markets:
            logger.warning("No common market slugs available for cross-platform arbitrage checks.")
        
        for market_slug in all_tracked_markets:
            market_data = comparison.get(market_slug)
            
            if not market_data:
                continue
                
            market_info = self.order_book_manager.get_market_info(market_slug)
            question = market_info.get('question', market_slug)

            poly_data = market_data.get('polymarket')
            limitless_data = market_data.get('limitless')

            # A. Internal Polymarket Arbitrage
            if poly_data:
                self._check_internal_polymarket_arb(market_slug, question, poly_data)

            # B. Cross-Platform Arbitrage
            if has_common_markets and poly_data and limitless_data and market_slug in common_markets:
                self._check_cross_platform_arb(market_slug, question, poly_data, limitless_data)
        
        # Note: Since we removed the "Active Log", we no longer need check_expired.


    # ----------------------------------------------------------------------
    # ARBITRAGE HELPER METHODS
    # ----------------------------------------------------------------------

    def _check_internal_polymarket_arb(self, slug, question, poly_data):
        """Checks for YES Bid + NO Bid > 1.0 on Polymarket."""
        
        yes_bids = poly_data['yes'].get("bids", [])
        no_bids = poly_data['no'].get("bids", [])
        
        if not (yes_bids and no_bids):
            return

        best_yes_bid = yes_bids[0][0]
        best_no_bid = no_bids[0][0]
        
        if best_yes_bid + best_no_bid > 1.003:  # 0.3% threshold
            profit_percent = (best_yes_bid + best_no_bid - 1.00) * 100
            
            # Estimate volume and profit for internal arb
            max_volume_shares = min(yes_bids[0][1], no_bids[0][1])
            net_profit_per_share = best_yes_bid + best_no_bid - 1.00 - (1.00 * self.FEE_POLYMARKET * 2)
            total_net_profit_usd = max_volume_shares * net_profit_per_share
            
            opp_data = {
                "market": question,
                "slug": slug,
                "formula": "YES Bid + NO Bid > 1.00",
                "type": "Internal Polymarket Arbitrage",
                "profit": profit_percent,
                "yes_bid": best_yes_bid,
                "no_bid": best_no_bid,
                "max_volume_shares": max_volume_shares,
                "total_net_profit": total_net_profit_usd,
                "details": f"Sell YES @ ${best_yes_bid:.4f} and Sell NO @ ${best_no_bid:.4f}"
            }
            
            # Append ALL opportunities found to the list
            if total_net_profit_usd >= self.MIN_DOLLAR_PROFIT_THRESHOLD:
                self.opportunities.append(opp_data)
                logger.info(f"🚨 ARB FOUND! {slug} | Type: {opp_data['type']} | Profit: {profit_percent:.4f}% | Net Profit: ${total_net_profit_usd:.2f}")

    def _check_cross_platform_arb(self, slug, question, poly_data, limitless_data):
        """
        Scans for arbitrage between Polymarket (Poly) and Limitless (Limitless).
        """
        
        # Get Order Book Data
        best_poly_bid = poly_data['yes']['bids'][0][0] if poly_data['yes']['bids'] else 0
        best_poly_ask = poly_data['yes']['asks'][0][0] if poly_data['yes']['asks'] else 1.0
        poly_bid_size = poly_data['yes']['bids'][0][1] if poly_data['yes']['bids'] else 0
        poly_ask_size = poly_data['yes']['asks'][0][1] if poly_data['yes']['asks'] else 0
        
        best_limitless_bid = limitless_data['yes']['bids'][0][0] if limitless_data['yes']['bids'] else 0
        best_limitless_ask = limitless_data['yes']['asks'][0][0] if limitless_data['yes']['asks'] else 1.0
        limitless_bid_size = limitless_data['yes']['bids'][0][1] if limitless_data['yes']['bids'] else 0
        limitless_ask_size = limitless_data['yes']['asks'][0][1] if limitless_data['yes']['asks'] else 0


        # ARB TYPE 1: Buy LOW on POLY, Sell HIGH on LIMITLESS (YES token)
        if self.MIN_VALID_PRICE <= best_limitless_bid <= self.MAX_VALID_PRICE:
            raw_spread = best_limitless_bid - best_poly_ask
            fee_cost = (best_poly_ask * self.FEE_POLYMARKET) + (best_limitless_bid * self.FEE_LIMITLESS)
            net_profit_per_share = raw_spread - fee_cost
            
            if net_profit_per_share > 0.0:
                max_volume_shares = min(poly_ask_size, limitless_bid_size)
                total_net_profit_usd = max_volume_shares * net_profit_per_share
                
                buy_price = best_poly_ask
                safe_buy_price = buy_price if buy_price > 0.0001 else self.MIN_SAFE_DENOMINATOR
                profit_percent = (net_profit_per_share / safe_buy_price) * 100
                
                if total_net_profit_usd >= self.MIN_DOLLAR_PROFIT_THRESHOLD and profit_percent >= self.MIN_PROFIT_THRESHOLD and max_volume_shares > 10:
                    opp_data = {
                        "market": question,
                        "slug": slug,
                        "type": "Cross-Platform (Poly -> Limitless) YES",
                        "formula": f"Buy Poly@{best_poly_ask:.4f} / Sell Limitless@{best_limitless_bid:.4f}",
                        "profit": profit_percent,
                        "max_volume_shares": max_volume_shares,
                        "total_net_profit": total_net_profit_usd,
                        "details": f"Buy YES @ ${best_poly_ask:.4f} (Poly), Sell YES @ ${best_limitless_bid:.4f} (Limitless)"
                    }
                    # Append ALL opportunities found to the list
                    self.opportunities.append(opp_data)
                    logger.info(f"🚨 ARB FOUND! {slug} | Type: {opp_data['type']} | Profit: {profit_percent:.4f}% | Net Profit: ${total_net_profit_usd:.2f}")


        # ARB TYPE 2: Buy LOW on LIMITLESS, Sell HIGH on POLY (YES token)
        if self.MIN_VALID_PRICE <= best_limitless_ask <= self.MAX_VALID_PRICE:
            raw_spread = best_poly_bid - best_limitless_ask
            fee_cost = (best_limitless_ask * self.FEE_LIMITLESS) + (best_poly_bid * self.FEE_POLYMARKET)
            net_profit_per_share = raw_spread - fee_cost

            if net_profit_per_share > 0.0:
                max_volume_shares = min(limitless_ask_size, poly_bid_size)
                total_net_profit_usd = max_volume_shares * net_profit_per_share
                
                buy_price = best_limitless_ask
                safe_buy_price = buy_price if buy_price > 0.0001 else self.MIN_SAFE_DENOMINATOR
                profit_percent = (net_profit_per_share / safe_buy_price) * 100
                
                if total_net_profit_usd >= self.MIN_DOLLAR_PROFIT_THRESHOLD and profit_percent >= self.MIN_PROFIT_THRESHOLD and max_volume_shares > 10:
                    opp_data = {
                        "market": question,
                        "slug": slug,
                        "type": "Cross-Platform (Limitless -> Poly) YES",
                        "formula": f"Buy Limitless@{best_limitless_ask:.4f} / Sell Poly@{best_poly_bid:.4f}",
                        "profit": profit_percent,
                        "max_volume_shares": max_volume_shares,
                        "total_net_profit": total_net_profit_usd,
                        "details": f"Buy YES @ ${best_limitless_ask:.4f} (Limitless), Sell YES @ ${best_poly_bid:.4f} (Poly)"
                    }
                    # Append ALL opportunities found to the list
                    self.opportunities.append(opp_data)
                    logger.info(f"🚨 ARB FOUND! {slug} | Type: {opp_data['type']} | Profit: {profit_percent:.4f}% | Net Profit: ${total_net_profit_usd:.2f}")
    
    # ----------------------------------------------------------------------
    # LOGGING AND CLEANUP METHODS 
    # ----------------------------------------------------------------------

    def print_opportunities(self):
        """
        Prints the current scan results, ranked by Absolute Profit. 
        All opportunities found in the current scan are displayed.
        """
        
        # 1. RANKING - Current Scan (Rank by Absolute Profit)
        # This list holds ALL valid opportunities found in the *current* scan.
        rankable_opportunities = [
            opp for opp in self.opportunities if opp.get('total_net_profit') is not None
        ]
        
        # Sort them all by profit
        rankable_opportunities.sort(key=lambda x: x['total_net_profit'], reverse=True)


        if rankable_opportunities:
            print(f"\n==================================================")
            print(f"🥇 CURRENT SCAN: RANKED BY ABSOLUTE PROFIT (Top {len(rankable_opportunities)})")
            print(f"==================================================")
            # Iterate and print every opportunity in the list
            for i, opp in enumerate(rankable_opportunities):
                print(f"--- RANK #{i+1} ---")
                print(f"Market:  {opp['market']}")
                print(f"Type:    {opp['type']}")
                print(f"Profit:  {opp['profit']:.2f}%")
                
                total_profit = opp.get('total_net_profit', 0)
                volume = opp.get('max_volume_shares', 0)
                
                print(f"Action:  {opp['details']}")
                print(f"Volume:  ${volume:.0f} shares | **ABS PROFIT: ${total_profit:.2f}**")
                print(f"--------------------------------------------------")
        else:
            print(f"\n[INFO] No current opportunities found above the ${self.MIN_DOLLAR_PROFIT_THRESHOLD:.2f} threshold.")


    def _write_log_to_csv(self):
        """Simulates writing the historical log (opp_log) to a CSV file."""
        if not self.opp_log:
            return

        filename = f"arbitrage_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        # In this environment, we simulate the CSV writing
        logger.info(f"📝 Historical arbitrage log (Total {len(self.opp_log)} entries) would be written to logs/{filename}")


# ----------------------------------------------------------------------
# EXTERNAL RUNNER FUNCTION
# ----------------------------------------------------------------------
import asyncio
async def run_arbitrage_bot(bot, interval=5):
    """
    Runs the main arbitrage loop (as defined in your provided main execution block).
    """
    logger.info("Executing run_arbitrage_bot - relying on the calling script (main.py) to manage the loop.")
    try:
        # Simulate some activity for a few loops
        for i in range(1, 4):
            # Step 1: Update order books and find opportunities
            bot.order_book_manager.update_order_books()
            bot.find_arbitrage_opportunities()

            # Step 2: Print current scan results
            bot.print_opportunities()

            # Step 3: Wait for the next interval
            logger.info(f"\n--- Waiting for next scan in {interval} seconds... (Loop {i}/3) ---")
            await asyncio.sleep(interval)
    finally:
        bot._write_log_to_csv()
        logger.info("Arbitrage bot execution completed.")
