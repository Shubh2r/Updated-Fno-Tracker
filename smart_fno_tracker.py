import pandas as pd
import os
import datetime
import argparse
import yfinance as yf
from nsepython import nse_optionchain_scrapper

# 📁 Create folders if missing
os.makedirs("data", exist_ok=True)
os.makedirs("report", exist_ok=True)

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

# 📈 Fetch global indices
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
            data = yf.download(ticker, period="2d", interval="1d", progress=False, auto_adjust=False)
            if data.empty or len(data) < 2:
                summary[name] = {"error": "Insufficient data"}
                continue
            change = round(data["Close"].iloc[-1] - data["Close"].iloc[-2], 2)
            pct = round((change / data["Close"].iloc[-2]) * 100, 2)
            summary[name] = {"change": change, "percent": pct}
        except Exception as e:
            summary[name] = {"error": str(e)}
    return summary

# 🔍 Extract FnO data rows
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

# 📦 Fetch and save data
def fetch_and_save(symbol):
    try:
        chain = nse_optionchain_scrapper(symbol)
        spot = float(chain["records"]["underlyingValue"])
        raw = chain["records"]["data"]

        rows = [extract_flattened_rows(row, spot) for row in raw]
        clean_rows = [r for r in rows if r]
        date_save = tomorrow_str if MODE == "evening" else today_str
        pd.DataFrame(clean_rows).to_csv(f"data/{symbol}_{date_save}.csv", index=False)
        print(f"✅ Saved {len(clean_rows)} rows for {symbol} ({MODE})")
    except Exception as e:
        print(f"⚠️ Error fetching {symbol}: {e}")

# 🧠 Analyze and suggest trades
def analyze(symbol, global_data):
    date_to_use = tomorrow_str if MODE == "evening" else today_str
    filename = f"data/{symbol}_{date_to_use}.csv"
    if not os.path.exists(filename):
        return [f"⚠️ {symbol} data not available. Skipping..."]

    df = pd.read_csv(filename)
    ce_oi, pe_oi = df["CE_OI"].sum(), df["PE_OI"].sum()
    pcr = round(pe_oi / ce_oi, 2) if ce_oi else "N/A"
    top_col = "CE_TotVol" if pcr < 1 else "PE_TotVol"

    try:
        top_strike = df.sort_values(top_col, ascending=False).iloc[0]["strikePrice"]
    except:
        return [f"⚠️ No valid volume data for {symbol}."]

    row = df[df["strikePrice"] == top_strike].iloc[0]
    vol = row[top_col]
    oi = row["CE_OI"] if pcr < 1 else row["PE_OI"]
    ltp = row["CE_LTP"] if pcr < 1 else row["PE_LTP"]
    ident = row["identifier_CE"] if pcr < 1 else row["identifier_PE"]
    expiry = row["expiryDate"]

    entry = round(ltp, 2)
    target = round(entry * 1.5, 2)
    stop = round(entry * 0.7, 2)

    try:
        sentiment_float = sum(
            float(v.get("change", 0)) for v in global_data.values()
            if isinstance(v, dict) and "change" in v
        )
    except:
        sentiment_float = 0

    tag = (
        "✅ Confirmed" if MODE == "morning" and sentiment_float > 0
        else "⚠️ Global Risk" if sentiment_float < 0
        else "🔍 Prelim"
    )

    return [
        f"## 📘 {symbol} ({MODE.capitalize()} Mode)",
        f"- 📈 PCR: `{pcr}`",
        f"- 🔢 Top Strike: `{top_strike}`",
        f"- 📆 Expiry: `{expiry}`",
        f"- 🎫 Symbol: `{ident}`",
        f"- 💰 Entry: ₹{entry}",
        f"- 🎯 Target: ₹{target}",
        f"- ⛔ Stop-Loss: ₹{stop}",
        f"- 🌐 Global Sentiment: `{sentiment_float}`",
        f"### Trade Signal: {tag} ⇒ `{'Call' if pcr < 1 else 'Put'}` Option"
    ]

# 📑 Generate markdown report
def generate_report():
    global_data = fetch_global_indices()
    date_to_use = tomorrow_str if MODE == "evening" else today_str
    summary_lines = [f"# 📊 FnO Tracker Report – {date_to_use}"]

    for name, vals in global_data.items():
        if "error" in vals:
            summary_lines.append(f"- ⚠️ {name}: `{vals['error']}`")
        else:
            summary_lines.append(f"- 🌐 {name}: Change `{vals['change']}` ({vals['percent']}%)")

    for symbol in ["BANKNIFTY", "NIFTY"]:
        summary_lines += analyze(symbol, global_data)

    file_name = f"report/fno_{MODE}_report_{date_to_use}.md"
    with open(file_name, "w") as f:
        f.write("\n".join(summary_lines))
    print(f"📝 Report saved as {file_name}")

# 🚀 Final execution block with error trace
if __name__ == "__main__":
    import traceback
    try:
        fetch_and_save("BANKNIFTY")
        fetch_and_save("NIFTY")
        generate_report()
    except Exception:
        traceback.print_exc()
        exit(1)
