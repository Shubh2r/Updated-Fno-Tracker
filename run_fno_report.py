import subprocess

print("🔄 Fetching FnO data...")
subprocess.run(["python", "fetch_fno_data.py"])

print("🔍 Running analysis...")
subprocess.run(["python", "analyze_fno.py"])
