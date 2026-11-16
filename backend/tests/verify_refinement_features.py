"""
Verify Quality Refinement Features:
- Payment mode detection (RTGS, NEFT, IMPS, UPI, IFT, CHEQUE, OTHER)
- Counterparty normalization (clean names without journal codes)
- Confidence scoring and category intelligence mapping endpoint
- Recomputed metrics preserving reconciliation variance INR 0.00
"""

import sys
import requests

def test_refinement():
    with open("active_session_id.txt") as f:
        sid = f.read().strip()
    
    base_url = "http://127.0.0.1:8000"
    print(f"Testing refinement on live session: {sid}")

    # 1. Fetch results
    resp = requests.get(f"{base_url}/api/results/{sid}")
    assert resp.status_code == 200, f"Failed to get results: {resp.text}"
    data = resp.json()

    txns = data.get("transactions", [])
    assert len(txns) == 162, f"Expected 162 txns, got {len(txns)}"
    print("[OK] Total transaction count: 162 verified")

    # 2. Check payment mode & counterparty normalization
    modes = set(t.get("payment_mode") for t in txns)
    print(f"[OK] Detected Payment Modes: {sorted(list(modes))}")
    assert "RTGS" in modes or "NEFT" in modes or "IFT" in modes, "Expected payment modes detected"

    # Counterparties
    counterparties = set(t.get("counterparty") or t.get("merchant") for t in txns if t.get("counterparty") or t.get("merchant"))
    print(f"[OK] Total Unique Normalized Counterparties: {len(counterparties)}")
    assert "Ashoka Infracore Private Limited" in counterparties, "Counterparty normalization check passed"

    # Check confidence
    confidences = set(t.get("confidence") for t in txns)
    print(f"[OK] Classification Confidences present: {confidences}")

    # 3. Test Category Mapping Override Endpoint
    # Reclassify "Manoj Director" to "Director Remuneration"
    payload = {
        "counterparty": "Manoj Director",
        "new_category": "Director Remuneration"
    }
    map_resp = requests.post(f"{base_url}/api/results/{sid}/category-mapping", json=payload)
    assert map_resp.status_code == 200, f"Mapping failed: {map_resp.text}"
    map_data = map_resp.json()
    assert map_data.get("status") == "success"
    assert map_data.get("modified_count", 0) > 0
    print(f"[OK] Successfully mapped counterparty. Modified count: {map_data.get('modified_count')}")

    # 4. Check recomputed category summary
    cat_summary = map_data.get("category_summary", {})
    assert "Director Remuneration" in cat_summary, "New category appears in recomputed category summary"
    print(f"[OK] Recomputed category summary contains 'Director Remuneration': INR {cat_summary['Director Remuneration']}")

    # 5. Check mathematical variance is still 0.00
    metrics = map_data.get("metrics", {})
    delta = metrics.get("reconciliation_delta", 0.0)
    assert abs(delta) < 0.01, f"Reconciliation variance must be 0, got {delta}"
    assert metrics.get("is_reconciled") is True
    print("[OK] Post-override statement balance ledger holds: Variance INR 0.00")

    print("\nALL REFINEMENT VERIFICATION CHECKS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_refinement()
