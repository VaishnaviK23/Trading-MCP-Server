from typing import Any
import pandas as pd
import httpx
from mcp.server.fastmcp import FastMCP
from collections import defaultdict, deque
import os
from functools import lru_cache
import yfinance as yf

import sys
import site
import os

print("PYTHON EXECUTABLE:", sys.executable, file=sys.stderr)
print("PYTHON PATH:", sys.path, file=sys.stderr)
print("SITE PACKAGES:", site.getsitepackages(), file=sys.stderr)
print("CURRENT DIR:", os.getcwd(), file=sys.stderr)

# Try importing dateutil
try:
    import dateutil
    print("✅ dateutil imported successfully", file=sys.stderr)
except ImportError as e:
    print(f"❌ Failed to import dateutil: {e}", file=sys.stderr)

# Load trade data
TRADE_CSV_PATH = "data/trade_history.csv"
df = pd.read_csv(TRADE_CSV_PATH)

# Initialize FastMCP server
mcp = FastMCP("Trading")

def get_live_price(symbol: str) -> float:
    """Fetch the live price of a stock symbol."""
    try:
        ticker = yf.Ticker(symbol)
        price = ticker.fast_info.get("last_price")

        if price is None:
            return -1.0  # Could not fetch price

        return float(price)
    except Exception as e:
        return -1.0


@mcp.tool()
def portfolio() -> dict[str, int]:
    """Show current portfolio holdings.

    This tool calculates the net number of shares held for each stock symbol by
    summing all buy and sell trades in the trade history CSV.

    Returns:
        A dictionary mapping stock symbols to their current number of held shares.
        Only symbols with a positive balance are included.

    Example:
        portfolio() -> {"AAPL": 120, "GOOG": 60}
    """
    holdings = defaultdict(int)
    for _, row in df.iterrows():
        if row['type'] == 'Buy':
            holdings[row['symbol']] += row['shares']
        else:
            holdings[row['symbol']] -= row['shares']
    return {k: v for k, v in holdings.items() if v > 0}

@mcp.tool()
def realized_gains() -> float:
    """Calculate total realized gains using FIFO method.

    This tool goes through the trade history and tracks all buy transactions in a FIFO queue.
    For each sell, it matches shares with the earliest buys and calculates the realized profit
    or loss accordingly.

    Returns:
        A float representing the total realized gain or loss (in dollars), rounded to two decimal places.

    Example:
        realized_gains() -> 352.75
    """
    buy_queues = defaultdict(deque)
    gains = 0.0

    for _, row in df.iterrows():
        symbol = row['symbol']
        shares = row['shares']
        price = row['price_per_share']
        if row['type'] == 'Buy':
            buy_queues[symbol].append((shares, price))
        else:
            while shares > 0 and buy_queues[symbol]:
                buy_shares, buy_price = buy_queues[symbol][0]
                matched = min(shares, buy_shares)
                gains += matched * (price - buy_price)
                shares -= matched
                if matched == buy_shares:
                    buy_queues[symbol].popleft()
                else:
                    buy_queues[symbol][0] = (buy_shares - matched, buy_price)
    return round(gains, 2)

@mcp.tool()
def unrealized_gains() -> dict[str, float]:
    """Calculate unrealized gains for current holdings.

    This tool calculates unrealized profit or loss by comparing the average
    buy price for currently held shares against the current market price
    fetched live using yfinance.

    Returns:
        A dictionary mapping each stock symbol to its unrealized gain or loss in dollars.

    Example:
        unrealized_gains() -> {"AAPL": 125.50, "GOOG": -22.15}
    """
    holdings = defaultdict(list)

    for _, row in df.iterrows():
        if row['type'] == 'Buy':
            holdings[row['symbol']].append((row['shares'], row['price_per_share']))
        else:
            to_sell = row['shares']
            while to_sell > 0 and holdings[row['symbol']]:
                qty, price = holdings[row['symbol']][0]
                matched = min(qty, to_sell)
                if matched == qty:
                    holdings[row['symbol']].pop(0)
                else:
                    holdings[row['symbol']][0] = (qty - matched, price)
                to_sell -= matched

    results = {}
    for symbol, buys in holdings.items():
        total_cost = sum(q * p for q, p in buys)
        total_shares = sum(q for q, _ in buys)
        if total_shares == 0:
            continue
        avg_price = total_cost / total_shares
        current = get_live_price(symbol)
        results[symbol] = round((current - avg_price) * total_shares, 2)
    return results

@mcp.tool()
def current_price(symbol: str) -> float:
    """Fetch the live price of a stock symbol.

    Args:
        symbol: Stock ticker symbol (e.g. AAPL, TSLA)
            - This should be a valid symbol supported by Yahoo Finance.

    Returns:
        The current market price as a float, or -1.0 if the price could not be fetched.

    Example:
        get_live_price("AAPL") -> 193.45
    """
    return get_live_price(symbol)

@mcp.tool()
def validate_trades() -> list[str]:
    """Validate that no trades sell more shares than have been bought.

    Parses the trade history sequentially to ensure all sell transactions
    occur only after a corresponding quantity of shares has been bought.

    Returns:
        A list of error messages for invalid trades, if any.

    Example:
        validate_trades() -> ["Invalid sell on 2024-02-10: 20 shares of AAPL (owned: 10)"]
    """
    errors = []
    balances = defaultdict(int)
    for idx, row in df.iterrows():
        if row['type'] == 'Buy':
            balances[row['symbol']] += row['shares']
        else:
            if balances[row['symbol']] < row['shares']:
                errors.append(f"Invalid sell on {row['date']}: {row['shares']} shares of {row['symbol']} (owned: {balances[row['symbol']]})")
            balances[row['symbol']] -= row['shares']
    return errors

@mcp.tool()
def pnl() -> dict[str, float]:
    """Generate a Profit & Loss (P&L) summary.

    Combines realized and unrealized gains into a single financial overview.

    Returns:
        A dictionary with keys 'realized' and 'unrealized' representing the total gains.

    Example:
        pnl() -> {"realized": 320.75, "unrealized": 145.60}
    """
    return {
        'realized': realized_gains(),
        'unrealized': sum(unrealized_gains().values())
    }

@mcp.tool()
def trade_history(symbol: str) -> list[dict[str, Any]]:
    """Return the trade history for a specific stock symbol.

    Args:
        symbol: The stock ticker symbol (e.g., AMZN, MSFT)

    Returns:
        A list of dictionaries containing all trade records for that symbol.

    Example:
        trade_history("GOOG") -> [{"date": "2024-01-01", "type": "Buy", ...}, ...]
    """
    return df[df['symbol'] == symbol].to_dict(orient='records')

@mcp.tool()
def simulate_sell(symbol: str, shares: int) -> float:
    """Simulate selling a number of shares of a stock and estimate the profit or loss.

    Args:
        symbol: The stock ticker symbol to simulate the sale for (e.g., TSLA)
        shares: The number of shares to simulate selling.

    Returns:
        The estimated profit/loss from the simulated sale using FIFO matching, in dollars.

    Example:
        simulate_sell("AAPL", 50) -> 123.45
    """
    # Build current holdings for this symbol
    holdings = []
    for _, row in df.iterrows():
        if row['symbol'] != symbol:
            continue
        if row['type'] == 'Buy':
            holdings.append((row['shares'], row['price_per_share']))
        else:
            to_sell = row['shares']
            while to_sell > 0 and holdings:
                qty, price = holdings[0]
                matched = min(qty, to_sell)
                if matched == qty:
                    holdings.pop(0)
                else:
                    holdings[0] = (qty - matched, price)
                to_sell -= matched

    proceeds = 0.0
    sell_price = get_live_price(symbol)
    to_sell = shares

    while to_sell > 0 and holdings:
        qty, buy_price = holdings[0]
        matched = min(qty, to_sell)
        proceeds += matched * (sell_price - buy_price)
        if matched == qty:
            holdings.pop(0)
        else:
            holdings[0] = (qty - matched, buy_price)
        to_sell -= matched

    return round(proceeds, 2)

if __name__ == "__main__":
    mcp.run(transport="stdio")
