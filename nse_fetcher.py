# 📦 nse_fetcher.py
import requests
import time

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Referer": "https://www.nseindia.com"
}

def warmup_session():
    session = requests.Session()
    try:
        session.get("https://www.nseindia.com", headers=HEADERS, timeout=10)
        time.sleep(1)
    except Exception as e:
        print(f"⚠️ NSE warm-up failed: {e}")
    return session

def fetch_option_chain(symbol):
    url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
    session = warmup_session()
    try:
        response = session.get(url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}")
        data = response.json()
        return data.get("records", {})
    except Exception as e:
        print(f"⚠️ Option chain fetch failed for {symbol}: {e}")
        return {}

def fetch_vix():
    return fetch_option_chain("INDIA VIX")
