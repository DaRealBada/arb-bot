<img src="assets\arbitrage_opportunities.png">
# Arb-Bot
An arbitrage bot for Polymarket and Kalshi.

Overview
This project implements real-time market data monitoring and arbitrage opportunity detection across different prediction market platforms. It's designed to identify situations where the combined probability of split markets on one platform differs from the unified market on another platform, creating risk-free profit opportunities.

Key Features:

-Real-time order book monitoring for both Polymarket and Kalshi platforms<br>
-Cross-platform arbitrage detection using advanced pricing formulas<br>
-Automated opportunity identification with profit and maximum size calculations<br>
-Modular architecture for easy extension to other prediction markets<br>

Market Focus
This project is designed to operate in hard-to-predict markets.

Technology
Built with Python using asynchronous programming for efficient, real-time market data processing.

## Setup
1. Clone the repo: `git clone <repo-url>`
2. Create a virtual environment: `python3 -m venv venv`
3. Activate it: `source venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` and fill in your keys.
6. Run the bot: `python main.py`