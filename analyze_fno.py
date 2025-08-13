import pandas as pd
import os
from datetime import date, timedelta
from nsepython import nse_index_quote

# 📅 Today's date
today = date.today()
today_str = today.strftime("%Y-%m-%d")
os.makedirs("report", exist_ok=True)
os.makedirs("performance", exist_ok=True)

def get_recent_dates(n=6):
    dates, d = [], today - timedelta(days=1)
    while len(dates) < n:
        if d.weekday() < 5:
            dates.append(d.strftime("%Y-%m-%d"))
        d -= timedelta(days=1)
    return dates[::-1]

def format_number(n):
    try:
        return f"{int(n):,}"
    except:
        return str(n)

def interpret_pcr(pcr):
    if pcr == "N/A":
        return "Unknown"
    return "Bullish" if pcr < 0.9 else "Bearish" if pcr > 1.3 else "Neutral"

def score_trade(pcr_sentiment, vol_surge, oi_trend, vix_level):
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
    return score

# 📉 VIX Data
try:
    vix_data = nse_index_quote("India VIX")
    vix_value = float(vix_data.get("lastPrice", 0))
except:
    vix_value = 0

summary_lines = [f"# 📊 FnO Report for {today_str}\n"]
summary_lines.append(f"- 🌪️ India VIX: `{vix_value}`\n")
recent_dates = get_recent_dates()

log_rows = []

for symbol in ["BANKNIFTY", "NIFTY"]:
    path_today = f"data/{symbol}_{today_str}.csv"
    if not os.path.exists(path_today):
        summary_lines.append(f"⚠️ Missing file: `{path_today}`\n")
        continue

    df = pd.read_csv(path_today)
    ce_oi = df.get("CE_OI", pd.Series()).sum()
    pe_oi = df.get("PE_OI", pd.Series()).sum()
    pcr = round(pe_oi / ce_oi, 2) if ce_oi else "N/A"
    pcr_sentiment = interpret_pcr(pcr)

    summary_lines.append(f"## 📘 {symbol}")
    summary_lines.append(f"- 🟦 Call OI: `{format_number(ce_oi)}`")
    summary_lines.append(f"- 🔴 Put OI: `{format_number(pe_oi)}`")
    summary_lines.append(f"- 🔄 PCR: `{pcr}` → `{pcr_sentiment}`")

    top_col = "CE_TotVol" if pcr_sentiment == "Bullish" else "PE_TotVol"
    try:
        top_strike = df.sort_values(top_col, ascending=False).iloc[0]["strikePrice"]
    except:
        summary_lines.append(f"- ⚠️ No volume data for top strike.")
        continue

    trend_data = []
    for d in recent_dates:
        path = f"data/{symbol}_{d}.csv"
        if os.path.exists(path):
            df_day = pd.read_csv(path)
            row = df_day[df_day["strikePrice"] == top_strike]
            if not row.empty:
                vol = row.get(top_col, pd.Series([0])).values[0]
                oi = row.get("CE_OI" if pcr_sentiment == "Bullish" else "PE_OI", pd.Series([0])).values[0]
                ltp = row.get("CE_LTP" if pcr_sentiment == "Bullish" else "PE_LTP", pd.Series([0])).values[0]
                ident = row.get("identifier_CE" if pcr_sentiment == "Bullish" else "identifier_PE", pd.Series([""])).values[0]
                expiry = row.get("expiryDate", pd.Series(["N/A"])).values[0]

                if ltp and ident:
                    trend_data.append({
                        "date": d,
                        "vol": vol,
                        "oi": oi,
                        "ltp": ltp,
                        "identifier": ident,
                        "expiry": expiry
                    })

    if len(trend_data) >= 3:
        vols = [r["vol"] for r in trend_data]
        ois = [r["oi"] for r in trend_data]
        ltps = [r["ltp"] for r in trend_data]

        vol_trend = "Increasing" if vols[-1] > vols[0] and vols[-2] > vols[1] else "Flat"
        oi_trend = "Increasing" if ois[-1] > ois[0] and ois[-2] > ois[1] else "Flat"
        avg_vol = sum(vols[:-1]) / len(vols[:-1])
        vol_surge = vols[-1] > 2 * avg_vol

        summary_lines.append(f"- 📊 Strike `{top_strike}` Volume Trend: `{vol_trend}`")
        summary_lines.append(f"- 📊 Strike `{top_strike}` OI Trend: `{oi_trend}`")
        summary_lines.append(f"- 🚀 Volume Surge: `{vol_surge}`")

        if vol_trend == "Increasing" and oi_trend == "Increasing":
            latest = trend_data[-1]
            entry = round(latest["ltp"], 2)
            target = round(entry * 1.5, 2)
            stop = round(entry * 0.7, 2)
            score = score_trade(pcr_sentiment, vol_surge, oi_trend, vix_value)

            summary_lines.append(f"### 🧭 Trade Suggestion for {symbol}")
            summary_lines.append(f"- ✅ Direction: `{'Call' if pcr_sentiment == 'Bullish' else 'Put'} Option`")
            summary_lines.append(f"- 🔢 Strike Price: `{top_strike}`")
            summary_lines.append(f"- 📆 Expiry: `{latest['expiry']}`")
            summary_lines.append(f"- 🎫 Symbol: `{latest['identifier']}`")
            summary_lines.append(f"- 💰 Entry: ₹{entry}")
            summary_lines.append(f"- 🎯 Target: ₹{target}")
            summary_lines.append(f"- ⛔ Stop-Loss: ₹{stop}")
            summary_lines.append(f"- 🧮 Signal Score: `{score}`")

            log_rows.append({
                "date": today_str,
                "symbol": symbol,
                "strike": top_strike,
                "entry": entry,
                "target": target,
                "stop": stop,
                "expiry": latest["expiry"],
                "score": score,
                "outcome": "Pending"
            })
        else:
            summary_lines.append(f"- ⚠️ Trends are weak. No trade suggested.")
    else:
        summary_lines.append(f"- ⚠️ Insufficient data for trend analysis.")

# Save markdown summary
with open(f"report/fno_summary_{today_str}.md", "w") as f:
    f.write("\n".join(summary_lines))

# Save performance log
log_df = pd.DataFrame(log_rows)
log_path = "performance/performance_log.csv"
if os.path.exists(log_path):
    log_df.to_csv(log_path, mode="a", header=False, index=False)
else:
    log_df.to_csv(log_path, index=False)
