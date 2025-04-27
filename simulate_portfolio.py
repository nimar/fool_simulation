"""
simulate_portfolio.py

This script reads Motley Fool stock recommendations from a CSV file (newrecs.csv),
simulates a portfolio by buying $10,000 of each stock on a 'buy' recommendation and
selling all shares on a 'sell' recommendation, and plots the portfolio value over time.

Dependencies:
- yfinance: For fetching historical stock prices
- matplotlib: For plotting the portfolio value
- csv: For reading the recommendations file

Usage:
    python simulate_portfolio.py

Make sure newrecs.csv is present in the same directory with columns:
    date,symbol,name,recommendation
"""
import sys
import csv
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime
from datetime import timedelta
import pandas as pd

INVESTMENT = 10000 # amount to invest on 'buy' recommendations
#CAP_TAX_RATE = 0.33
#INCOME_TAX_RATE = 0.50
SnP500 = "SPY"

def parse_date(date_str):
    for fmt in ("%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Date {date_str} is not in a recognized format.")

def read_recommendations(csv_path):
    """
    Reads recommendations from a CSV file and returns a list of dictionaries.
    Each dictionary contains: date, symbol, name, recommendation.
    """
    recs = []
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            row['date'] = parse_date(row['date'])
            recs.append(row)
    return recs

def get_history(symbol, start=None, end=None):
    """
    Fetches historical data for a stock symbol using yfinance.
    The returned DataFrame has a 'Date' column (type: date) and no duplicate dates.
    """
    ticker = yf.Ticker(symbol)
    hist = ticker.history(start=start, end=end)
    if hist.empty:
        print(f"Warning: No historical data for {symbol}.")
        return hist
    hist = hist.copy()
    hist['Date'] = hist.index.date
    hist = hist.reset_index(drop=True)
    # Sanity check for duplicate dates
    if hist['Date'].duplicated().any():
        raise ValueError(f"Duplicate dates found in history for {symbol}")
    hist.set_index('Date', inplace=True)
    return hist

def simulate_portfolio(recs, first_date, last_date):
    recs = sorted((x for x in recs if x['date'] > first_date), reverse=True, key=lambda x: x['date'])

    data = []
    portfolio = {}
    history = {}
    cash = 0
    investment = 0

    portfolio[SnP500] = 0
    history[SnP500] = get_history(SnP500, start=first_date, end=last_date)

    # Go through each day in the history of the S&P 500
    for current_date in history[SnP500].index:
        # see if we have a recommendation for this day
        while len(recs) and recs[-1]['date'] < current_date:
            rec = recs.pop()
            symbol = rec['symbol']
            if symbol not in history:
                hist = get_history(symbol, start=current_date, end=datetime.today())
                if hist.empty:
                    print(f"Warning: No historical data for {symbol} at {current_date}. Skipping.")
                    continue
                else:
                    history[symbol] = hist
                    print("Started tracking", symbol)
            # Find the price of the stock on the current date
            if current_date not in history[symbol].index:
                print(f"Warning: No price for {symbol} on {current_date}. Skipping action.")
                continue
            price = history[symbol].loc[current_date]
            action = rec['recommendation'].lower()
            if action == 'buy':
                shares = INVESTMENT / price['High'] # assume we buy at the high price
                if symbol not in portfolio:
                    portfolio[symbol] = shares
                    print(f"{current_date} Bought {shares} shares of {symbol} at {price['High']}.")
                else:
                    portfolio[symbol] += shares
                    print(f"{current_date} Added {shares} shares of {symbol} at {price['High']}. Total: {portfolio[symbol]}")
                if cash >= INVESTMENT:
                    cash -= INVESTMENT
                else:
                    purchase = INVESTMENT - cash
                    snp_price = history[SnP500].loc[current_date]['High']
                    portfolio[SnP500] += purchase / snp_price
                    print(f"{current_date} S&P 500 Bought {purchase / snp_price} shares at {snp_price}.")
                    investment += purchase
                    cash = 0
            elif action == 'sell':
                if symbol in portfolio:
                    shares = portfolio[symbol]
                    cash += shares * price['Low']   # assume we sell at the low price
                    print(f"{current_date} Sold {shares} shares of {symbol} at {price['Low']}. Position closed.")
                    del portfolio[symbol]
            elif action == "reduce":
                if symbol in portfolio:
                    shares = portfolio[symbol] // 2 # we reduce the position by half
                    cash += shares * price['Low']
                    portfolio[symbol] -= shares
                    print(f"{current_date} Sold half of {symbol} at {price['Low']}. Remaining shares: {portfolio[symbol]}")

        # add dividends to share amounts compute the portfolio
        fool_amount = cash
        snp_amount = 0
        for symbol in portfolio.keys():
            if current_date not in history[symbol].index:
                print(f"Warning: No price for {symbol} on {current_date}. Skipping valuation.")
                continue
            price = history[symbol].loc[current_date]
            # check if we have dividends for this day
            if price['Dividends'] > 0:
                portfolio[symbol] *= 1 + price['Dividends'] / 100.0
                print(f"{current_date} Received {price['Dividends']} dividends for {symbol}. New amount: {portfolio[symbol]}")
            amount = portfolio[symbol] * price['Close']
            if symbol == SnP500:
                snp_amount = amount
            else:
                fool_amount += amount
        data.append([current_date, investment, fool_amount, snp_amount])

        # if this is the last date of the month we will debug the portfolio
        # Check if we are at the end of a month by looking ahead to the next date in the index
        if current_date == history[SnP500].index[-1] or history[SnP500].index[history[SnP500].index.get_loc(current_date) + 1].month != current_date.month:
            print(f"End of month {current_date} portfolio:")
            for symbol in portfolio.keys():
                if symbol == SnP500:
                    continue
                price = history[symbol].loc[current_date]
                amount = portfolio[symbol] * price['Close']
                print(f"{symbol}: {amount} at {price['Close']}")
            print(f"S&P 500: {snp_amount}")
            print(f"Cash: {cash}")
            print(f"Total Fool Portfolio Value: {fool_amount + cash}")
            print(f"Total S&P 500 Value: {snp_amount}")

    return pd.DataFrame(data=data, columns=["Date", "Cumulative Investment", "Fool Portfolio", "S&P 500"])



if __name__ == "__main__":
    year = sys.argv[1] if len(sys.argv) > 1 else "2024"
    first_date = parse_date(f"01/01/{year}")
    last_date = parse_date(f"12/31/{sys.argv[2]}") if len(sys.argv) > 2 else datetime.today().date()
    recs = read_recommendations("newrecs.csv")
    data = simulate_portfolio(recs, first_date, last_date)
    print(data)
    # Plot the portfolio value over time
    plt.figure(figsize=(10, 6))
    plt.plot(data['Date'], data['Fool Portfolio'], label='Fool Portfolio', color='blue')
    plt.plot(data['Date'], data['S&P 500'], label='S&P 500', color='orange')
    plt.plot(data['Date'], data['Cumulative Investment'], label='Cumulative Investment', color='green')
    plt.axhline(y=0, color='black', linestyle='--')
    plt.fill_between(data['Date'], data['Fool Portfolio'], data['S&P 500'], where=(data['Fool Portfolio'] > data['S&P 500']), color='blue', alpha=0.25)
    plt.fill_between(data['Date'], data['Fool Portfolio'], data['S&P 500'], where=(data['Fool Portfolio'] < data['S&P 500']), color='orange', alpha=0.25)
    plt.xlabel('Date')
    plt.ylabel('Portfolio Value ($)')
    plt.title(f"Portfolio Simulation for {year}")
    plt.legend()
    plt.grid()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()
    # Save the plot to a file
    filename = f"portfolio_simulation_{year}.png"
    plt.savefig(filename)
    print(f"Saved portfolio simulation to {filename}")

"""
useful yfinance functions

>>> t2 = yf.Ticker('GOOG')
>>> t2.get_splits()
Date
2014-03-27 00:00:00-04:00     2.002000
2015-04-27 00:00:00-04:00     1.002746
2022-07-18 00:00:00-04:00    20.000000
Name: Stock Splits, dtype: float64

>>> t2.history(start='2014-3-25', end='2014-3-30')
                                Open       High        Low  ...     Volume  Dividends  Stock Splits
Date                                                        ...                                    
2014-03-25 00:00:00-04:00  28.904243  28.999433  28.433247  ...   96769361        0.0         0.000
2014-03-26 00:00:00-04:00  28.805334  29.042319  28.049015  ...  103586819        0.0         0.000
2014-03-27 00:00:00-04:00  28.188727  28.188727  27.440338  ...     262719        0.0         2.002
2014-03-28 00:00:00-04:00  27.851255  28.110810  27.725698  ...     824257        0.0         0.000

"""