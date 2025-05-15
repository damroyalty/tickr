import yfinance as yf
import requests
from datetime import datetime, timedelta
import time
from threading import Lock
import os

LAST_API_CALL = 0
API_CALL_DELAY = 1.5

def rate_limit():
    global LAST_API_CALL
    now = time.time()
    elapsed = now - LAST_API_CALL
    if elapsed < API_CALL_DELAY:
        time.sleep(API_CALL_DELAY - elapsed)
    LAST_API_CALL = time.time()

COINMARKETCAP_API_KEY = os.getenv('COINMARKETCAP_API_KEY', 'your-api-key-here')

CRYPTO_MAPPING = {
    'BTC': {'coingecko': 'bitcoin', 'coinmarketcap': '1'},
    'ETH': {'coingecko': 'ethereum', 'coinmarketcap': '1027'},
    'XRP': {'coingecko': 'ripple', 'coinmarketcap': '52'},
    'ADA': {'coingecko': 'cardano', 'coinmarketcap': '2010'},
    'SOL': {'coingecko': 'solana', 'coinmarketcap': '5426'},
    'DOGE': {'coingecko': 'dogecoin', 'coinmarketcap': '74'},
    'DOT': {'coingecko': 'polkadot', 'coinmarketcap': '6636'},
    'MATIC': {'coingecko': 'matic-network', 'coinmarketcap': '3890'},
    'BNB': {'coingecko': 'binancecoin', 'coinmarketcap': '1839'},
    'LTC': {'coingecko': 'litecoin', 'coinmarketcap': '2'}
}

DATA_CACHE = {}
CACHE_LOCK = Lock()
CACHE_TIMEOUT = 300

def get_cached_data(key):
    with CACHE_LOCK:
        if key in DATA_CACHE:
            data, timestamp = DATA_CACHE[key]
            if time.time() - timestamp < CACHE_TIMEOUT:
                return data
    return None

def set_cached_data(key, data):
    with CACHE_LOCK:
        DATA_CACHE[key] = (data, time.time())

def get_stock_data(ticker, force_refresh=False, time_range="1d"):
    cache_key = f"stock_{ticker}"
    if not force_refresh:
        cached_data = get_cached_data(cache_key)
        if cached_data:
            return cached_data

    try:
        stock = yf.Ticker(ticker)
        
        # basic info
        info = stock.info
        hist = stock.history(period="1y")
        
        if hist.empty:
            print(f"Warning: No data found for {ticker} (may be delisted)")
            return None
        
        # price data
        current_data = stock.history(period="1d")
        current = current_data["Close"].iloc[-1]
        open_price = current_data["Open"].iloc[-1] if not current_data["Open"].empty else info.get('regularMarketOpen', current)
        prev_close = info.get('regularMarketPreviousClose', hist["Close"].iloc[-1])
        
        # volume data
        volume = info.get('regularMarketVolume', hist["Volume"].iloc[-1])
        avg_volume = info.get('averageVolume', hist["Volume"].mean())
        
        # market data
        market_cap = info.get('marketCap')
        pe_ratio = info.get('trailingPE')
        
        # bid/ask
        bid = info.get('bid', current * 0.999)
        ask = info.get('ask', current * 1.001)
        
        result = {
            "symbol": ticker,
            "current": round(current, 2),
            "open": round(open_price, 2),
            "prev_close": round(prev_close, 2),
            "high": round(hist["High"].max(), 2),
            "low": round(hist["Low"].min(), 2),
            "change": round(current - prev_close, 2),
            "change_percent": round((current - prev_close) / prev_close * 100, 2),
            "pe_ratio": round(pe_ratio, 2) if pe_ratio else None,
            "market_cap": f"{market_cap/1e9:.2f}B" if market_cap else "--",
            "volume": int(volume) if volume else None,
            "avg_volume": int(avg_volume) if avg_volume else None,
            "bid": round(bid, 2),
            "ask": round(ask, 2),
            "data": hist["Close"].tolist(),
            "type": "stock",
            "last_updated": datetime.now().isoformat()
        }
        
        set_cached_data(cache_key, result)
        return result
        
    except Exception as e:
        print(f"Error fetching stock data for {ticker}: {str(e)}")
        return None

def get_crypto_data(symbol, force_refresh=False, time_range="1d"):
    cache_key = f"crypto_{symbol}"
    if not force_refresh:
        cached_data = get_cached_data(cache_key)
        if cached_data:
            return cached_data

    data = get_crypto_data_coingecko(symbol)
    if data:
        set_cached_data(cache_key, data)
        return data
    
    data = get_crypto_data_coinmarketcap(symbol)
    if data:
        set_cached_data(cache_key, data)
        return data
    
    data = get_crypto_data_yfinance(symbol)
    if data:
        set_cached_data(cache_key, data)
        return data
    
    return None

def get_crypto_data_coingecko(symbol):
    try:
        symbol_upper = symbol.upper()
        coin_id = CRYPTO_MAPPING.get(symbol_upper, {}).get('coingecko', symbol.lower())
        
        market_url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
        market_r = requests.get(market_url, timeout=10)
        market_r.raise_for_status()
        market_data = market_r.json()
        
        chart_url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        params = {"vs_currency": "usd", "days": "365"}
        chart_r = requests.get(chart_url, params=params, timeout=10)
        chart_r.raise_for_status()
        chart_data = chart_r.json()
        
        prices = [price[1] for price in chart_data["prices"]]
        if not prices:
            return None
            
        current = prices[-1]
        market_info = market_data.get('market_data', {})
        
        return {
            "symbol": symbol_upper,
            "current": round(current, 2),
            "open": round(market_info.get('current_price', {}).get('usd', current), 2),
            "prev_close": round(prices[-2] if len(prices) > 1 else current, 2),
            "high": round(max(prices), 2),
            "low": round(min(prices), 2),
            "change": round(current - prices[0], 2),
            "change_percent": round((current - prices[0]) / prices[0] * 100, 2),
            "pe_ratio": None,
            "market_cap": f"{market_info.get('market_cap', {}).get('usd', 0)/1e9:.2f}B",
            "volume": int(market_info.get('total_volume', {}).get('usd', 0)),
            "avg_volume": None,
            "bid": round(current * 0.999, 2),
            "ask": round(current * 1.001, 2),
            "data": prices,
            "type": "crypto",
            "last_updated": datetime.now().isoformat()
        }
    except Exception as e:
        print(f"CoinGecko API error for {symbol}: {str(e)}")
        return None

def get_crypto_data_coinmarketcap(symbol):
    try:
        if not COINMARKETCAP_API_KEY or COINMARKETCAP_API_KEY == 'your-api-key-here':
            return None
            
        symbol_upper = symbol.upper()
        coin_id = CRYPTO_MAPPING.get(symbol_upper, {}).get('coinmarketcap')
        if not coin_id:
            return None
        
        url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
        params = {'id': coin_id, 'convert': 'USD'}
        headers = {'X-CMC_PRO_API_KEY': COINMARKETCAP_API_KEY}
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        quote = data['data'][str(coin_id)]['quote']['USD']
        current = quote['price']
        
        prices = [current] * 30
        
        return {
            "symbol": symbol_upper,
            "current": round(current, 2),
            "open": round(quote.get('open_24h', current), 2),
            "prev_close": round(quote.get('open_24h', current), 2),
            "high": round(quote.get('high_24h', current), 2),
            "low": round(quote.get('low_24h', current), 2),
            "change": round(quote.get('percent_change_24h', 0) * current / 100, 2),
            "change_percent": round(quote.get('percent_change_24h', 0), 2),
            "pe_ratio": None,
            "market_cap": f"{quote.get('market_cap', 0)/1e9:.2f}B",
            "volume": int(quote.get('volume_24h', 0)),
            "avg_volume": None,
            "bid": round(current * 0.999, 2),
            "ask": round(current * 1.001, 2),
            "data": prices,
            "type": "crypto",
            "last_updated": datetime.now().isoformat()
        }
    except Exception as e:
        print(f"CoinMarketCap API error for {symbol}: {str(e)}")
        return None

def get_crypto_data_yfinance(symbol):
    try:
        data = get_stock_data(f"{symbol}-USD", force_refresh=True)
        if data:
            data["type"] = "crypto"
            data["symbol"] = symbol.upper()
            if 'data' not in data or not data['data']:
                if 'history' in data:
                    data['data'] = data['history']['Close'].tolist()
        return data
    except Exception as e:
        print(f"YFinance fallback failed for {symbol}: {str(e)}")
        return None