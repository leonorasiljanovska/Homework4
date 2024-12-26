import pandas as pd
import numpy as np
from models import db
from sqlalchemy import text


# RSI - Relative Strength Index
def calculate_rsi(prices, window=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


# Moving Average (MA)
def calculate_moving_average(prices, window=5):
    return prices.rolling(window=window).mean()


# Exponential Moving Average (EMA)
def calculate_ema(prices, window=14):
    return prices.ewm(span=window, adjust=False).mean()


# Bollinger Bands (BB)
def calculate_bollinger_bands(prices, window=14):
    sma = prices.rolling(window=window).mean()
    rolling_std = prices.rolling(window=window).std()
    upper_band = sma + (rolling_std * 2)
    lower_band = sma - (rolling_std * 2)
    return upper_band, lower_band


# Average True Range (ATR)
def calculate_atr(df, window=14):
    df['H-L'] = df['max_price'] - df['min_price']
    df['H-PC'] = abs(df['max_price'] - df['last_transaction_price'].shift(1))
    df['L-PC'] = abs(df['min_price'] - df['last_transaction_price'].shift(1))
    df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1)
    atr = df['TR'].rolling(window=window).mean()
    return atr


# MACD (Moving Average Convergence Divergence)
def calculate_macd(prices, short_window=12, long_window=26, signal_window=9):
    short_ema = calculate_ema(prices, short_window)
    long_ema = calculate_ema(prices, long_window)
    macd = short_ema - long_ema
    signal = calculate_ema(macd, signal_window)
    histogram = macd - signal
    return macd, signal, histogram


# Stochastic Oscillator
def calculate_stochastic(df, window=14):
    low_min = df['min_price'].rolling(window=window).min()
    high_max = df['max_price'].rolling(window=window).max()
    stochastic = 100 * (df['last_transaction_price'] - low_min) / (high_max - low_min)
    return stochastic


# Commodity Channel Index (CCI)
def calculate_cci(df, window=20):
    tp = (df['max_price'] + df['min_price'] + df['last_transaction_price']) / 3
    sma = tp.rolling(window=window).mean()
    mad = tp.rolling(window=window).apply(lambda x: np.fabs(x - x.mean()).mean())  # Mean Absolute Deviation
    cci = (tp - sma) / (0.015 * mad)
    return cci


# Williams %R
def calculate_williams_r(df, window=14):
    highest_high = df['max_price'].rolling(window=window).max()
    lowest_low = df['min_price'].rolling(window=window).min()
    williams_r = (highest_high - df['last_transaction_price']) / (highest_high - lowest_low) * -100
    return williams_r


# Calculate all indicators and oscillators for the date range
def calculate_for_date_range(date_range):
    start_date, end_date = date_range

    # Query the database for the date range (example using SQLAlchemy)
    data = db.session.execute(
        text("""
            SELECT date, last_transaction_price, max_price, min_price
            FROM public."CompaniesData"
            WHERE date BETWEEN :start_date AND :end_date
        """),
        {'start_date': start_date, 'end_date': end_date}
    ).fetchall()

    # Convert to a DataFrame for easier processing
    df = pd.DataFrame(data, columns=['date', 'last_transaction_price', 'max_price', 'min_price'])

    # Calculate indicators
    moving_average = calculate_moving_average(df['last_transaction_price'])
    ema = calculate_ema(df['last_transaction_price'])
    upper_band, lower_band = calculate_bollinger_bands(df['last_transaction_price'])
    atr = calculate_atr(df)
    macd, macd_signal, macd_histogram = calculate_macd(df['last_transaction_price'])

    # Calculate oscillators
    rsi = calculate_rsi(df['last_transaction_price'])
    stochastic = calculate_stochastic(df)
    cci = calculate_cci(df)
    williams_r = calculate_williams_r(df)

    # Combine results into dictionaries
    indicators = {
        "Moving Average": moving_average,
        "Exponential Moving Average": ema,
        "Bollinger Bands Upper": upper_band,
        "Bollinger Bands Lower": lower_band,
        "Average True Range": atr
    }

    oscillators = {
        "RSI": rsi,
        "Stochastic Oscillator": stochastic,
        "Commodity Channel Index": cci,
        "Williams %R": williams_r,
        "MACD Histogram": macd_histogram
    }

    return indicators, oscillators
