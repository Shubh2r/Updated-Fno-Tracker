import pandas as pd
import os
import datetime
import argparse
import yfinance as yf
from nsepython import nse_index_quote

# 📁 Create folders
os.makedirs("data", exist_ok=True)
os.makedirs("report", exist_ok=True)
os.makedirs("performance", exist_ok=True)

# 📅 Dates
today = datetime.date.today()
tomorrow = today + datetime.timedelta(days=1)
today_str = today.strftime("%Y-%m-%d")
tomorrow_str = tomorrow.strftime("%Y-%m-%d")

# 🗂 Mode argument
parser = argparse.ArgumentParser()
parser.add_argument("--mode", choices=["evening", "morning"], default="evening")
args = parser.parse_args()
MODE = args.mode

# 🌐 Global indices
def fetch_global_indices():
    indices = {
        "Dow": "^DJI",
        "Nasdaq": "^IXIC",
        "S&P 500": "^GSPC",
        "SGX Nifty": "^NSEI"
    }
    summary = {}
    for name, ticker in indices.items():
        try:
            data = yf.download(ticker, period="2d", interval="1d", progress=False)
            if data.empty or len(data) < 2:
                summary[name] = {"error": "Insufficient data"}
                continue
            change = round(data["Close"].iloc[-1] - data["Close"].iloc[-2], 2)
            pct = round((change / data["Close"].iloc[-2]) * 100, 2)
            summary[name] = {"change": change, "percent": pct}
        except Exception as e:
            summary[name] = {"error": str(e)}
    return summary

# 🌪️ India VIX fetch using nse_index_quote (reliable method)
from nsepython import nsefetch

def fetch_vix():
    try:
        url = "https://www.nseindia.com/api/option-chain-indices?symbol=INDIA%20VIX"
        data = nsefetch(url)
        vix_value = float(data["records"]["underlyingValue"])
        print(f"🌪️ India VIX fetched: {vix_value}")
        return vix_value
    except Exception as e:
        print(f"⚠️ VIX fetch error: {e}")
        return 0

# 🧹 Clean and flatten option chain row
def extract_flattened_rows(option_data, spot):
    strike = option_data.get("strikePrice")
    expiry = option_data.get("expiryDate")
    ce = option_data.get("CE", {})
    pe = option_data.get("PE", {})

    if not ce.get("identifier") or not pe.get("identifier"):
        return None
    if ce.get("lastPrice", 0) == 0 and pe.get("lastPrice", 0) == 0:
        return None
    if abs(strike - spot) > 1500:
        return None
    try:
        exp_date = datetime.datetime.strptime(expiry, "%d-%b-%Y").date()
        if exp_date < today:
            return None
    except:
        return None

    return {
        "strikePrice": strike,
        "expiryDate": expiry,
        "identifier_CE": ce.get("identifier", ""),
        "identifier_PE": pe.get("identifier", ""),
        "CE_OI": ce.get("openInterest", 0),
        "PE_OI": pe.get("openInterest", 0),
        "CE_TotVol": ce.get("totalTradedVolume", 0),
        "PE_TotVol": pe.get("totalTradedVolume", 0),
        "CE_LTP": ce.get("lastPrice", 0),
        "PE_LTP": pe.get("lastPrice", 0)
    }

# 📦 Fetch and save FnO data
def fetch_and_save(symbol):
    try:
        url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
        data = nsefetch(url)
        spot = float(data["records"]["underlyingValue"])
        raw = data["records"]["data"]

        rows = [extract_flattened_rows(row, spot) for row in raw]
        clean_rows = [r for r in rows if r]
        date_save = date_str
        pd.DataFrame(clean_rows).to_csv(f"data/{symbol}_{date_save}.csv", index=False)

        print(f"✅ Saved {len(clean_rows)} rows for {symbol} ({MODE})")
        print(f"📁 Saved to: data/{symbol}_{date_save}.csv")
    except Exception as e:
        print(f"⚠️ Error fetching {symbol}: {e}")

# 🧠 Trade scoring
def interpret_pcr(pcr):
    if pcr == "N/A":
        return "Unknown"
    return "Bullish" if pcr < 0.9 else "Bearish" if pcr > 1.3 else "Neutral"

def score_trade(pcr_sentiment, vol_surge, oi_trend, vix_level, global_score):
    score = 0
    if pcr_sentiment == "Bullish":
        score += 25
    elif pcr_sentiment == "Neutral":
        score += 15
    if vol_surge:
        score += 25
    if oi_trend == "Increasing":
        score += 20
    if vix_level < 14:
        score += 15
    score += global_score
    return score

# 🔍 Analyze and suggest trades
def analyze(symbol, global_data, vix_level):
    date_to_use = tomorrow_str if MODE == "evening" else today_str
    filename = f"data/{symbol}_{date_to_use}.csv"
    if not os.path.exists(filename):
        return [f"⚠️ {symbol} data not available. Skipping..."]

    df = pd.read_csv(filename)
    ce_oi, pe_oi = df["CE_OI"].sum(), df["PE_OI"].sum()
    pcr = round(pe_oi / ce_oi, 2) if ce_oi else "N/A"
    pcr_sentiment = interpret_pcr(pcr)
    top_col = "CE_TotVol" if pcr_sentiment == "Bullish" else "PE_TotVol"

    try:
        top_strike = df.sort_values(top_col, ascending=False).iloc[0]["strikePrice"]
    except:
        return [f"⚠️ No valid volume data for {symbol}."]

    row = df[df["strikePrice"] == top_strike].iloc[0]
    vol = row[top_col]
    oi = row["CE_OI"] if pcr_sentiment == "Bullish" else row["PE_OI"]
    ltp = row["CE_LTP"] if pcr_sentiment == "Bullish" else row["PE_LTP"]
    ident = row["identifier_CE"] if pcr_sentiment == "Bullish" else row["identifier_PE"]
    expiry = row["expiryDate"]

    recent_vols = df[top_col].sort_values(ascending=False).head(5)
    avg_vol = recent_vols.mean()
    vol_surge = vol > 2 * avg_vol
    oi_trend = "Increasing" if oi > df[top_col].mean() else "Flat"

    try:
        global_score = sum(
            float(v.get("change", 0)) for v in global_data.values()
            if isinstance(v, dict) and "change" in v
        )
    except:
        global_score = 0

    entry = round(ltp, 2)
    target = round(entry * 1.5, 2)
    stop = round(entry * 0.7, 2)
    score = score_trade(pcr_sentiment, vol_surge, oi_trend, vix_level, global_score)

    tag = (
        "✅ Strong Signal" if score >= 80 else
        "⚠️ Moderate Signal" if score >= 50 else
        "❌ Weak Signal"
    )

    log_row = {
        "date": date_to_use,
        "symbol": symbol,
        "strike": top_strike,
        "entry": entry,
        "target": target,
        "stop": stop,
        "expiry": expiry,
        "score": score,
        "outcome": "Pending"
    }
    log_df = pd.DataFrame([log_row])
    log_path = "performance/performance_log.csv"
    if os.path.exists(log_path):
        log_df.to_csv(log_path, mode="a", header=False, index=False)
    else:
        log_df.to_csv(log_path, index=False)

    return [
        f"## 📘 {symbol} ({MODE.capitalize()} Mode)",
        f"- 🔄 PCR: `{pcr}` → `{pcr_sentiment}`",
        f"- 🔢 Top Strike: `{top_strike}`",
        f"- 📆 Expiry: `{expiry}`",
        f"- 🎫 Symbol: `{ident}`",
        f"- 💰 Entry: ₹{entry}",
        f"- 🎯 Target: ₹{target}",
        f"- ⛔ Stop-Loss: ₹{stop}",
        f"- 🚀 Volume Surge: `{vol_surge}`",
        f"- 🧮 Signal Score: `{score}`",
        f"### Trade Signal: {tag} ⇒ `{'Call' if pcr_sentiment == 'Bullish' else 'Put'}` Option"
    ]

# 📑 Generate markdown report
def generate_report():
    global_data = fetch_global_indices()
    vix_level = fetch_vix()
    date_to_use = tomorrow_str if MODE == "evening" else today_str
    summary_lines = [f"# 📊 FnO Tracker Report – {date_to_use}"]
    summary_lines.append(f"- 🌪️ India VIX: `{vix_level}`")

    for name, vals in global_data.items():
        if "error" in vals:
            summary_lines.append(f"- ⚠️ {name}: `{vals['error']}`")
        else:
            summary_lines.append(f"- 🌐 {name}: Change `{vals['change']}` ({vals['percent']}%)")

    for symbol in ["BANKNIFTY", "NIFTY"]:
        summary_lines += analyze(symbol, global_data, vix_level)

    file_name = f"report/fno_{MODE}_report_{date_to_use}.md"
    with open(file_name, "w") as f:
        f.write("\n".join(summary_lines))
    print(f"📝 Report saved as {file_name}")

# 🧾 Generate performance summary
def generate_performance_summary():
    try:
        import generate_performance_summary as gps
        gps.generate_summary()
    except Exception as e:
        print(f"⚠️ Error generating performance summary: {e}")

# 🚀 Final execution block
if __name__ == "__main__":
    import traceback
    try:
        fetch_and_save("BANKNIFTY")
        fetch_and_save("NIFTY")
        generate_report()
        generate_performance_summary()
    except Exception:
        traceback.print_exc()
        exit(1)
