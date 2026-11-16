import requests
import json

session_id = open("active_session_id.txt").read().strip()
res = requests.get(f"http://127.0.0.1:8000/api/results/{session_id}").json()
metrics = res["metrics"]

print("=== EXPENSE CATEGORIES ===")
for c in metrics["top_categories"]:
    print(f"  {c['category']:<15}: INR {c['amount']:>12,.2f} ({c['percentage']:>5.1f}%)")

print("\n=== INTELLIGENCE METRICS ===")
for k, v in metrics["intelligence"].items():
    print(f"  {k:<30}: {v}")
