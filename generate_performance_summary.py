import pandas as pd
import os

log_path = "performance/performance_log.csv"
summary_path = "performance/performance_summary.md"

def generate_summary():
    if not os.path.exists(log_path):
        print("⚠️ No performance log found.")
        return

    df = pd.read_csv(log_path)
    total = len(df)
    wins = df[df["outcome"] == "Hit Target"]
    losses = df[df["outcome"] == "Hit Stop"]
    pending = df[df["outcome"] == "Pending"]

    win_rate = round(len(wins) / total * 100, 2) if total else 0
    avg_score = round(df["score"].mean(), 2)

    lines = [f"# 📊 FnO Performance Summary\n"]
    lines.append(f"- 📅 Total Trades: `{total}`")
    lines.append(f"- ✅ Wins: `{len(wins)}`")
    lines.append(f"- ❌ Losses: `{len(losses)}`")
    lines.append(f"- ⏳ Pending: `{len(pending)}`")
    lines.append(f"- 🎯 Win Rate: `{win_rate}%`")
    lines.append(f"- 🧮 Avg Signal Score: `{avg_score}`\n")

    # 🏆 Top trades
    top_trades = df.sort_values("score", ascending=False).head(3)
    lines.append("## 🏆 Top 3 Trades by Score")
    for _, row in top_trades.iterrows():
        lines.append(f"- `{row['date']}` | `{row['symbol']}` | Strike `{row['strike']}` | Score `{row['score']}` | Outcome `{row['outcome']}`")

    # 🖼️ Embed charts
    lines.append("\n## 📈 Charts")
    lines.append("![Signal Score Histogram](signal_score_histogram.png)")
    lines.append("![Trade Outcome Pie](trade_outcome_pie.png)")

    with open(summary_path, "w") as f:
        f.write("\n".join(lines))

    print(f"📝 Summary saved to {summary_path}")

if __name__ == "__main__":
    generate_summary()
