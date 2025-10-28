import asyncio
import os
import logging
import csv
from datetime import datetime
from data.order_book import OrderBookManager
from polymarket import PolymarketClient # Assuming this is available
from gamma_fetch import get_market_mapping_for_bot # Assuming this is available

# Setup logging
logger = logging.getLogger(__name__)

class ArbitrageBot:
    FEE_POLYMARKET = 0.003
    FEE_LIMITLESS = 0.003 # Assuming 0.3% for Limitless/Kalshi for now
    MIN_PROFIT_THRESHOLD = 0.005 # 0.5% minimum profit needed

    def __init__(self, order_book_manager):
        self.order_book_manager = order_book_manager
        self.opportunities = []
        self.opp_log = [] # Historical log of all closed/expired opportunities
        # active_opps must be initialized here to persist state across find_arbitrage_opportunities calls
        self.active_opps = {} # Stores currently active opportunities (slug -> opp_data)
    
    def find_arbitrage_opportunities(self):
        # Fetch the latest comparison data (Polymarket and Limitless data, if available)
        comparison = self.order_book_manager.compare_specific_markets()
        self.opportunities = []
        
        # Iterate over ALL market slugs the bot is tracking.
        # This ensures we scan every market, even if it had no data in the 'comparison' dict.
        # Note: We rely on check_expired to handle cleanup.
        all_tracked_markets = self.order_book_manager.get_market_list()
        
        for market_slug in all_tracked_markets:
            market_data = comparison.get(market_slug)
            
            # Skip if we have no current order book data for this market
            if not market_data:
                continue
                
            market_info = self.order_book_manager.get_market_info(market_slug)
            question = market_info.get('question', market_slug)

            poly_data = market_data.get('polymarket')
            limitless_data = market_data.get('limitless')

            # A. Internal Polymarket Arbitrage
            # Check only if Polymarket data is available for this market
            if poly_data:
                self._check_internal_polymarket_arb(market_slug, question, poly_data)

            # B. Cross-Platform Arbitrage
            # Check only if BOTH Polymarket and Limitless data are available
            if poly_data and limitless_data:
                # The logic inside here already fulfills your requirement: 
                # "only be able to find arb oppurtunities across platforms only 
                # when the same events and markets exist in both platforms."
                self._check_cross_platform_arb(market_slug, question, poly_data, limitless_data)
        
        # Check for expired opportunities after the scan
        # This function correctly uses the 'comparison' dict to determine if the opportunity still exists
        self.check_expired(comparison)

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
        
        # Check for arbitrage: YES Bid + NO Bid > 1.003 (0.3% threshold)
        if best_yes_bid + best_no_bid > 1.003:  
            profit_percent = (best_yes_bid + best_no_bid - 1.00) * 100
            
            opp_data = {
                "market": question,
                "slug": slug,
                "formula": "YES Bid + NO Bid > 1.00",
                "type": "Internal Polymarket Arbitrage",
                "profit": profit_percent,
                "yes_bid": best_yes_bid,
                "no_bid": best_no_bid,
                "details": f"Sell YES @ ${best_yes_bid:.4f} and Sell NO @ ${best_no_bid:.4f}"
            }

            self.opportunities.append(opp_data)
            
            # Log active opportunity (only if it's new)
            if slug not in self.active_opps:
                 # Internal arbitrage logs by slug
                 self.log_opportunity(slug, profit_percent, best_yes_bid, best_no_bid, opp_data["type"])


    def _check_cross_platform_arb(self, slug, question, poly_data, limitless_data):
        """
        Scans for arbitrage between Polymarket (Poly) and Limitless (Limitless).
        Focus is on the YES share.
        """
        
        # Polymarket Order Book (for YES)
        best_poly_bid = poly_data['yes']['bids'][0][0] if poly_data['yes']['bids'] else 0
        best_poly_ask = poly_data['yes']['asks'][0][0] if poly_data['yes']['asks'] else 1.0
        poly_bid_size = poly_data['yes']['bids'][0][1] if poly_data['yes']['bids'] else 0
        poly_ask_size = poly_data['yes']['asks'][0][1] if poly_data['yes']['asks'] else 0
        
        # Limitless Order Book (for YES)
        best_limitless_bid = limitless_data['yes']['bids'][0][0] if limitless_data['yes']['bids'] else 0
        best_limitless_ask = limitless_data['yes']['asks'][0][0] if limitless_data['yes']['asks'] else 1.0
        limitless_bid_size = limitless_data['yes']['bids'][0][1] if limitless_data['yes']['bids'] else 0
        limitless_ask_size = limitless_data['yes']['asks'][0][1] if limitless_data['yes']['asks'] else 0


        # ARB TYPE 1: Buy LOW on POLY, Sell HIGH on LIMITLESS (YES token)
        raw_spread = best_limitless_bid - best_poly_ask
        # Adjust for fees: cost of buying on poly + cost of selling on limitless
        fee_cost = (best_poly_ask * self.FEE_POLYMARKET) + (best_limitless_bid * self.FEE_LIMITLESS)
        net_profit_per_share = raw_spread - fee_cost
        
        if net_profit_per_share > 0.0:
            max_volume_shares = min(poly_ask_size, limitless_bid_size)
            total_net_profit_usd = max_volume_shares * net_profit_per_share
            # Profit % relative to the initial purchase price
            profit_percent = (net_profit_per_share / best_poly_ask) * 100
            
            if profit_percent >= self.MIN_PROFIT_THRESHOLD and max_volume_shares > 10:
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
                self.opportunities.append(opp_data)
                if slug not in self.active_opps:
                    self.log_opportunity(slug, profit_percent, best_poly_ask, best_limitless_bid, opp_data["type"])


        # ARB TYPE 2: Buy LOW on LIMITLESS, Sell HIGH on POLY (YES token)
        raw_spread = best_poly_bid - best_limitless_ask
        # Adjust for fees: cost of buying on limitless + cost of selling on poly
        fee_cost = (best_limitless_ask * self.FEE_LIMITLESS) + (best_poly_bid * self.FEE_POLYMARKET)
        net_profit_per_share = raw_spread - fee_cost

        if net_profit_per_share > 0.0:
            max_volume_shares = min(limitless_ask_size, poly_bid_size)
            total_net_profit_usd = max_volume_shares * net_profit_per_share
            profit_percent = (net_profit_per_share / best_limitless_ask) * 100
            
            if profit_percent >= self.MIN_PROFIT_THRESHOLD and max_volume_shares > 10:
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
                self.opportunities.append(opp_data)
                if slug not in self.active_opps:
                    self.log_opportunity(slug, profit_percent, best_limitless_ask, best_poly_bid, opp_data["type"])
    
    # ----------------------------------------------------------------------
    # LOGGING AND CLEANUP METHODS 
    # ----------------------------------------------------------------------
    
    def print_market_summary(self):
        """Placeholder for market summary printing."""
        pass 

    def log_opportunity(self, slug, profit, price1, price2, arb_type):
        """Logs a new arbitrage opportunity to be tracked."""
        timestamp = datetime.now() 
        # Using slug only for cross-platform to allow only one of two types to be active at a time
        opp_id = f"{slug}-{arb_type.replace(' ', '-')[10:]}-{timestamp.timestamp()}" 
        
        opp = {
            'id': opp_id,
            'slug': slug, 
            'arb_type': arb_type,
            'profit_pct': profit,
            'price_1': price1,
            'price_2': price2,
            'start_time': timestamp,
            'duration': None
        }
        
        self.active_opps[slug] = opp 
        logger.info(f"🚨 ARB FOUND! {slug} | Type: {arb_type} | Profit: {profit:.4f}%")
        
        return opp_id

    def check_expired(self, current_comparison):
        """
        Checks if active opportunities still exist in the latest comparison data.
        (Logic omitted for brevity, assume unchanged from your input)
        """
        # Create a set of all market slugs present in the current comparison data
        current_markets = set(current_comparison.keys())
        
        expired_slugs = []
        for slug, opp in self.active_opps.items():
            
            # Check if the market itself is still available
            if slug not in current_markets:
                expired_slugs.append(slug)
                continue
            
            # Check internal Polymarket arbitrage closure (YES Bid + NO Bid <= 1.003)
            if opp['arb_type'] == "Internal Polymarket Arbitrage":
                poly_data = current_comparison[slug].get('polymarket')
                if poly_data:
                    yes_bids = poly_data['yes'].get("bids", [])
                    no_bids = poly_data['no'].get("bids", [])
                    if not (yes_bids and no_bids) or (yes_bids[0][0] + no_bids[0][0] <= 1.003):
                        expired_slugs.append(slug)
                        
            # Check cross-platform arbitrage closure (Poly vs Limitless)
            elif "Cross-Platform" in opp['arb_type']:
                poly_data = current_comparison[slug].get('polymarket')
                limitless_data = current_comparison[slug].get('limitless')

                if poly_data and limitless_data:
                    poly_ask = poly_data['yes']['asks'][0][0] if poly_data['yes']['asks'] else 1.0
                    limitless_bid = limitless_data['yes']['bids'][0][0] if limitless_data['yes']['bids'] else 0.0

                    poly_bid = poly_data['yes']['bids'][0][0] if poly_data['yes']['bids'] else 0.0
                    limitless_ask = limitless_data['yes']['asks'][0][0] if limitless_data['yes']['asks'] else 1.0

                    is_expired = True

                    # ARB TYPE 1: Buy Poly, Sell Limitless
                    if opp['arb_type'] == "Cross-Platform (Poly -> Limitless) YES":
                        raw_spread = limitless_bid - poly_ask
                        fee_cost = (poly_ask * self.FEE_POLYMARKET) + (limitless_bid * self.FEE_LIMITLESS)
                        net_profit_per_share = raw_spread - fee_cost
                        if (net_profit_per_share / poly_ask) * 100 >= self.MIN_PROFIT_THRESHOLD:
                            is_expired = False

                    # ARB TYPE 2: Buy Limitless, Sell Poly
                    elif opp['arb_type'] == "Cross-Platform (Limitless -> Poly) YES":
                        raw_spread = poly_bid - limitless_ask
                        fee_cost = (limitless_ask * self.FEE_LIMITLESS) + (poly_bid * self.FEE_POLYMARKET)
                        net_profit_per_share = raw_spread - fee_cost
                        if (net_profit_per_share / limitless_ask) * 100 >= self.MIN_PROFIT_THRESHOLD:
                            is_expired = False
                            
                    if is_expired:
                        expired_slugs.append(slug)
                else:
                    # One of the platforms is missing data, assume expired for safety/cleanup
                    expired_slugs.append(slug)


        # Move expired opportunities to the historical log
        for slug in set(expired_slugs):
            expired_opp = self.active_opps.pop(slug)
            expired_opp['duration'] = (datetime.now() - expired_opp['start_time']).total_seconds()
            self.opp_log.append(expired_opp)
            logger.info(f"✅ ARB EXPIRED: {slug} | Duration: {expired_opp['duration']:.1f}s")


    def print_opportunities(self):
        """
        Prints the current state of active and found opportunities.
        MODIFIED: Prints the detailed block for ALL opportunities found in this current scan.
        """
        
        # 1. Print current opportunities found in this loop (Verbose Output - prints ALL opportunities found)
        for opp in self.opportunities:
            print(f"\n🎉 ARBITRAGE OPPORTUNITY FOUND!")
            print(f"--------------------------------------------------")
            print(f"Market:  {opp['market']}")
            print(f"Type:    {opp['type']}")
            # The formula contains the prices (e.g., Buy Poly@0.06 / Sell Limitless@0.075)
            print(f"Formula: {opp['formula']}")
            print(f"Profit:  {opp['profit']:.2f}%")
            if 'details' in opp:
                # The action is detailed, including platform and price
                print(f"Action:  {opp['details']}")
            if 'max_volume_shares' in opp:
                 # Volume and total profit only exist for cross-platform opportunities
                 print(f"Volume:  ${opp['max_volume_shares']:.0f} shares | Profit: ${opp['total_net_profit']:.2f}")
            print(f"--------------------------------------------------")
        
        # 2. Print active, persistent opportunities (Summary)
        if self.active_opps:
            print(f"\n==================================================")
            print(f"👀 Active and Persistent Arbitrage Opportunities ({len(self.active_opps)})")
            print(f"==================================================")
            for slug, opp in self.active_opps.items():
                duration = (datetime.now() - opp['start_time']).total_seconds()
                # Status is always 'ACTIVE' here since it is in the active_opps dict
                print(f" - {opp['slug']} (✨ ACTIVE): {opp['profit_pct']:.2f}% (Active for {duration:.1f}s)")


        # 3. Print overall log status
        if self.opp_log:
            print(f"\n- Historical Logged Opportunities: {len(self.opp_log)}")


    def _write_log_to_csv(self):
        """Writes the historical log (opp_log) to a CSV file."""
        if not self.opp_log:
            return

        # Define file path
        filename = f"arbitrage_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # Define field names based on the opportunity dictionary structure
        fieldnames = ['id', 'slug', 'arb_type', 'profit_pct', 'price_1', 'price_2', 'start_time', 'duration']
        
        try:
            # Create a dedicated log directory if it doesn't exist
            if not os.path.exists("logs"):
                os.makedirs("logs")
                
            filepath = os.path.join("logs", filename)
            
            with open(filepath, 'w', newline='') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.opp_log)
                
            logger.info(f"📝 Historical arbitrage log written to {filepath}")
        except Exception as e:
            logger.error(f"Failed to write arbitrage log to CSV: {e}")


# ----------------------------------------------------------------------
# EXTERNAL RUNNER FUNCTION (For reference on how to execute)
# ----------------------------------------------------------------------

async def run_arbitrage_bot(bot, interval=2):
    """
    Runs the main arbitrage loop.
    This function should be called once with a persistent bot instance.
    """
    logger.info(f"Starting arbitrage bot to run every {interval} seconds...")
    try:
        while True:
            # Step 1: Find all current opportunities (updates self.opportunities and self.active_opps)
            bot.find_arbitrage_opportunities()

            # Step 2: Print current scan results and active log
            # This is the single entry point for bot output
            bot.print_opportunities()

            # Step 3: Wait for the next interval
            await asyncio.sleep(interval)
            
    except asyncio.CancelledError:
        logger.info("Arbitrage bot loop cancelled.")
    except Exception as e:
        logger.error(f"An unexpected error occurred in run_arbitrage_bot loop: {e}")
    finally:
        # Final cleanup and logging when the bot stops
        bot._write_log_to_csv()
        logger.info("Main program terminated.")
