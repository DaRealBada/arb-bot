// --- Smarkets API Integration Script (Node.js) ---

// NOTE: If using an older Node.js version, uncomment the line below after installing node-fetch:
// const fetch = require('node-fetch');

// Smarkets API Configuration
const SMARKETS_API_BASE = 'https://api.smarkets.com/v3';
// API endpoint to fetch the 50 most recently updated events (increased limit for better chance of finding a tradable contract).
// MODIFIED: Reverting to the most stable, unfiltered URL and relying entirely on the QUOTES fetch to prove liquidity.
const EVENTS_API_URL = `${SMARKETS_API_BASE}/events/?state=new&limit=50`;

/**
 * Helper function to fetch the full order book (quotes) for a specific market and contract.
 * @param {string} marketId - The ID of the market (e.g., '101234').
 * @param {string} contractId - The ID of the contract (e.g., '201234').
 * @returns {Promise<Object | null>} Structured market data or null if illiquid/error.
 */
async function fetchMarketQuotes(marketId, contractId) {
    // Smarkets quotes API does not accept the limit parameter
    const QUOTES_API_URL = `${SMARKETS_API_BASE}/markets/${marketId}/contracts/${contractId}/quotes/`;

    console.log(`\n--- Attempting Fetch: Market ID ${marketId} (Contract: ${contractId}) ---`);

    try {
        const response = await fetch(QUOTES_API_URL, { method: 'GET' });

        if (!response.ok) {
            const status = response.status;
            if (status === 404) {
                 console.log(`   [SKIP] Contract ID ${contractId} returned 404. Market may be closed or quote data unavailable.`);
                 return null;
            }
            throw new Error(`Quotes HTTP Error! Status: ${status}. Cannot fetch order book data.`);
        }

        const data = await response.json();
        
        // Smarkets provides prices in micro-units (value * 10,000). 
        const quotes = data.quotes?.[0]; 
        
        if (quotes && quotes.bids?.length > 0 && quotes.asks?.length > 0) {
            const bestBid = quotes.bids[0]; // Best price to SELL (highest price for 'Yes')
            const bestAsk = quotes.asks[0]; // Best price to BUY (lowest price for 'Yes')
            
            console.log('\n   BEST PRICES (Order Book)');
            // Bid: Price at which you can SELL shares (back/lay)
            console.log(`   Best Bid (SELL Price): ${(bestBid[0] / 10000).toFixed(4)} @ Volume: ${bestBid[1]}`);
            // Ask: Price at which you can BUY shares (back/lay)
            console.log(`   Best Ask (BUY Price):  ${(bestAsk[0] / 10000).toFixed(4)} @ Volume: ${bestAsk[1]}`);
            
            // Return structured data for the Arbitrage Engine
            return {
                marketId,
                contractId,
                bid: bestBid[0] / 10000,
                ask: bestAsk[0] / 10000,
                bidVolume: bestBid[1],
                askVolume: bestAsk[1]
            };
        } else {
            console.log('   [SKIP] Order book is empty or market is illiquid (no bids/asks).');
            return null;
        }

    } catch (error) {
        console.error(`\n!!! ERROR FETCHING QUOTES: ${error.message} !!!`);
        return null;
    }
}


/**
 * Fetches events, filters for 'open' state client-side, and continuously iterates through all markets
 * to find a liquid one and fetch its quotes.
 */
async function fetchSmarketsData() {
    console.log('--- Connecting to Smarkets API ---');
    console.log(`Fetching event list from: ${EVENTS_API_URL}\n`);

    try {
        // Step 1: Fetch Events (with increased limit and NO category filter)
        const response = await fetch(EVENTS_API_URL, {
            method: 'GET',
        });

        if (!response.ok) {
            const status = response.status;
            throw new Error(`Events HTTP Error! Status: ${status}. The Smarkets API is rejecting the initial events URL.`);
        }

        const data = await response.json();

        if (data.events && data.events.length > 0) {
            console.log(`SUCCESS: Found ${data.events.length} major events.`);
            console.log('---------------------------------');
            
            // Step 2: Iterate and attempt to fetch quotes for every available contract
            let marketData = null;
            let totalChecked = 0;
            
            for (const event of data.events) {
                // NEW CHECK: Skip events that have no markets defined, which are typically settled or upcoming.
                if (!event.markets || event.markets.length === 0) {
                    // console.log(`[SKIP EVENT] Event ${event.id} (${event.name}) has no markets.`);
                    continue;
                }
                
                if (event.markets && event.markets.length > 0) {
                    for (const market of event.markets) {
                        if (market.contracts && market.contracts.length > 0) {
                            
                            // Iterate through ALL contracts within the market (e.g., Yes/No)
                            for (const contract of market.contracts) {
                                totalChecked++;
                                
                                console.log(`\nTARGET CANDIDATE ${totalChecked}: ${event.name} -> ${market.name} (${contract.name})`);
                                
                                // Attempt to fetch quotes
                                marketData = await fetchMarketQuotes(market.id, contract.id);
                                
                                // If successful (i.e., we got a liquid quote), we are done!
                                if (marketData) {
                                    console.log('\n--- FIRST LIQUID MARKET FOUND AND QUOTES RETRIEVED ---');
                                    console.log(`EVENT: ${event.name}`);
                                    console.log(`MARKET: ${market.name} (${contract.name})`);
                                    console.log(`BEST BUY Price (Ask): ${marketData.ask} | BEST SELL Price (Bid): ${marketData.bid}`);
                                    return; // Successfully fetched, exit the entire function
                                }
                            }
                        }
                    }
                }
            }
            
            // This is only reached if the loops complete without finding a liquid market
            console.log(`\nINFO: Could not find any liquid market after checking ${totalChecked} contracts from ${data.events.length} events.`);

        } else {
            console.log('INFO: Smarkets API returned successfully, but no events were found.');
        }

    } catch (error) {
        console.error('\n!!! FATAL ERROR CONNECTING TO SMARKETS !!!');
        console.error(`ERROR: ${error.message}`);
    }
}

// Execute the main function
fetchSmarketsData();

// Export the function (optional, but good practice for modular code)
module.exports = { fetchSmarketsData };
