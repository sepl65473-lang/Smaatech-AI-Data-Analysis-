import io
import requests

BASE = "http://127.0.0.1:8000"

# 1. Invalid file upload
r1 = requests.post(f"{BASE}/api/upload", files={"file": ("corrupt.pdf", io.BytesIO(b"Not a real PDF or statement"), "application/pdf")})
print("Corrupt file status:", r1.status_code, "->", r1.json().get("detail", r1.json().get("message")))
assert r1.status_code in (400, 422, 500)

# 2. Empty file upload
r2 = requests.post(f"{BASE}/api/upload", files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")})
print("Empty file status:", r2.status_code, "->", r2.json().get("detail", r2.json().get("message")))
assert r2.status_code in (400, 422)

# 3. Expired or non-existent session
r3 = requests.get(f"{BASE}/api/export/00000000-0000-0000-0000-000000000000?format=pdf")
print("Non-existent session status:", r3.status_code)
assert r3.status_code == 404

# 4. Cross-session isolation: create Session A and Session B with different statements
csv_a = "Date,Description,Debit,Credit,Balance\n2023-01-01,Session A Payment,1000,,9000\n"
csv_b = "Date,Description,Debit,Credit,Balance\n2023-02-01,Session B Payment,2000,,8000\n"

r_a = requests.post(f"{BASE}/api/upload", files={"file": ("stmt_a.csv", io.BytesIO(csv_a.encode('utf-8')), "text/csv")})
sid_a = r_a.json()["session_id"]

r_b = requests.post(f"{BASE}/api/upload", files={"file": ("stmt_b.csv", io.BytesIO(csv_b.encode('utf-8')), "text/csv")})
sid_b = r_b.json()["session_id"]

res_a = requests.get(f"{BASE}/api/results/{sid_a}").json()
res_b = requests.get(f"{BASE}/api/results/{sid_b}").json()

tx_a = [t["description"] for t in res_a["transactions"]]
tx_b = [t["description"] for t in res_b["transactions"]]
print("Session A transactions:", tx_a)
print("Session B transactions:", tx_b)
assert "Session A Payment" in tx_a[0]
assert "Session B Payment" in tx_b[0]
assert "Session B" not in tx_a[0]
assert "Session A" not in tx_b[0]
print("Cross-session isolation: PASS")

# 5. Secret leakage check
for fmt in ["html", "xlsx", "pdf"]:
    r = requests.get(f"{BASE}/api/export/{sid_a}?format={fmt}")
    content = str(r.content)
    assert "GROQ_API_KEY" not in content
    assert "GEMINI_API_KEY" not in content
    assert "sk-" not in content
print("Secret exposure check: PASS (No API keys or tokens found in exported files)")

print("Security and Edge Cases: 100% PASS")
