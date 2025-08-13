import pandas as pd
import os
from datetime import date, timedelta

# 📅 Today's date
today = date.today()
today_str = today.strftime("%Y-%m-%d")
os.makedirs("report", exist_ok=True)

def get_recent_dates(n=6):
    dates, d = [], today - timedelta(days=1)
    while len(dates) < n:
        if d.weekday() < 5:  # Skip weekends
            dates.append(d.strftime("%Y-%m-%d"))
        d -= timedelta(days=1)
    return dates[::-1]

def format_number(n):
    try:
        return f"{int(n):,}"
    except:
        return str(n)

summary_lines = [f"# 📊 FnO Report for {today_str}\n"]
recent_dates = get_recent_dates()

for symbol in ["BANKNIFTY", "NIFTY"]:
    path_today = f"data/{symbol}_{today_str}.csv"
    if not os.path.exists(path_today):
        summary_lines.append(f"⚠️ Missing file: `{path_today}`\n")
        continue

    df = pd.read_csv(path_today)
    ce_oi = df.get("CE_OI", pd.Series()).sum()
    pe_oi = df.get("PE_OI", pd.Series()).sum()
    pcr = round(pe_oi / ce_oi, 2) if ce_oi else "N/A"

    summary_lines.append(f"## 📘 {symbol}")
    summary_lines.append(f"- 🟦 Call OI: `{format_number(ce_oi)}`")
    summary_lines.append(f"- 🔴 Put OI: `{format_number(pe_oi)}`")
    summary_lines.append(f"- 🔄 PCR: `{pcr}`")

    top_col = "CE_TotVol" if pcr < 1 else "PE_TotVol"
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
                oi = row.get("CE_OI" if pcr < 1 else "PE_OI", pd.Series([0])).values[0]
                ltp = row.get("CE_LTP" if pcr < 1 else "PE_LTP", pd.Series([0])).values[0]
                ident = row.get("identifier_CE" if pcr < 1 else "identifier_PE", pd.Series([""])).values[0]
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
        vol_trend = "Increasing" if vols[-1] > vols[0] and vols[-2] > vols[1] else "Flat"
        oi_trend = "Increasing" if ois[-1] > ois[0] and ois[-2] > ois[1] else "Flat"

        summary_lines.append(f"- 📊 Strike `{top_strike}` Volume Trend: `{vol_trend}`")
        summary_lines.append(f"- 📊 Strike `{top_strike}` OI Trend: `{oi_trend}`")

        if vol_trend == "Increasing" and oi_trend == "Increasing":
            latest = trend_data[-1]
            entry = round(latest["ltp"], 2)
            target = round(entry * 1.5, 2)
            stop = round(entry * 0.7, 2)

            summary_lines.append(f"### 🧭 Trade Suggestion for {symbol}")
            summary_lines.append(f"- ✅ Direction: `{'Call' if pcr < 1 else 'Put'} Option`")
            summary_lines.append(f"- 🔢 Strike Price: `{top_strike}`")
            summary_lines.append(f"- 📆 Expiry: `{latest['expiry']}`")
            summary_lines.append(f"- 🎫 Symbol: `{latest['identifier']}`")
            summary_lines.append(f"- 💰 Entry: ₹{entry}")
            summary_lines.append(f"- 🎯 Target: ₹{target}")
            summary_lines.append(f"- ⛔ Stop-Loss: ₹{stop}")
        else:
            summary_lines.append(f"- ⚠️ Trends are weak. No trade suggested.")
    else:
        summary_lines.append(f"- ⚠️ Insufficient data for trend analysis.")

# Save markdown summary
with open(f"report/fno_summary_{today_str}.md", "w") as f:
    f.write("\n".join(summary_lines))
