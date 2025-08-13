import pandas as pd
import matplotlib.pyplot as plt
import os

# 📁 Paths
log_path = "performance/performance_log.csv"
os.makedirs("performance", exist_ok=True)

def analyze_performance():
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

    print(f"\n📊 Performance Summary")
    print(f"- Total Trades: {total}")
    print(f"- ✅ Wins: {len(wins)}")
    print(f"- ❌ Losses: {len(losses)}")
    print(f"- ⏳ Pending: {len(pending)}")
    print(f"- 🎯 Win Rate: {win_rate}%")
    print(f"- 🧮 Avg Signal Score: {avg_score}")

    # 📈 Score histogram
    plt.figure(figsize=(8, 4))
    df["score"].plot(kind="hist", bins=10, color="skyblue", edgecolor="black")
    plt.title("Signal Score Distribution")
    plt.xlabel("Score")
    plt.ylabel("Frequency")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("performance/signal_score_histogram.png")
    print("📊 Saved: signal_score_histogram.png")

    # 🥧 Outcome pie chart
    plt.figure(figsize=(6, 6))
    df["outcome"].value_counts().plot.pie(autopct="%1.1f%%", startangle=90, colors=["green", "red", "gray"])
    plt.title("Trade Outcome Distribution")
    plt.ylabel("")
    plt.tight_layout()
    plt.savefig("performance/trade_outcome_pie.png")
    print("🥧 Saved: trade_outcome_pie.png")

if __name__ == "__main__":
    analyze_performance()
