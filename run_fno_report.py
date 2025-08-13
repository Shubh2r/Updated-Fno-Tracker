import subprocess
import traceback

def run_script(name, args):
    print(f"\n🚀 Running: {name}")
    try:
        subprocess.run(["python", args], check=True)
        print(f"✅ Completed: {name}")
    except subprocess.CalledProcessError:
        print(f"❌ Failed: {name}")
        traceback.print_exc()

if __name__ == "__main__":
    print("🔄 Starting FnO Report Pipeline...\n")

    run_script("Fetch FnO Data", "fetch_fno_data.py")
    run_script("Analyze FnO Data", "analyze_fno.py")
    run_script("Performance Analyzer", "performance_analyzer.py")

    print("\n📊 FnO Report Pipeline Finished.")
