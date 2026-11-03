"""
GET /api/results/{session_id}

Returns the full AnalysisResult for a given session.
Implemented fully in Phase 2.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.session.store import session_store
from app.services.metrics import compute_metrics, build_category_summary
from app.models.result import AnalysisResult
from app.models.transaction import Transaction

router = APIRouter(tags=["results"])


class CategoryOverrideRequest(BaseModel):
    transaction_id: Optional[str] = None
    counterparty: Optional[str] = None
    target_type: Optional[str] = None
    target_value: Optional[str] = None
    apply_to_future: Optional[bool] = False
    new_category: str


@router.get("/results/{session_id}")
async def get_results(session_id: str):
    """
    Retrieve analysis results for a previously uploaded statement.
    Returns 404 if the session does not exist or has expired.
    """
    data = session_store.get(session_id)
    if data is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found or expired. Please upload your statement again.",
        )
    return data


from datetime import datetime, timezone

@router.post("/results/{session_id}/category-mapping")
async def update_category_mapping(session_id: str, payload: CategoryOverrideRequest):
    """
    Update category for a specific transaction or all transactions for a counterparty.
    Recomputes metrics, category summary, preserves audit trail and maintains canonical consistency.
    """
    target_cp = payload.counterparty or (payload.target_value if payload.target_type == "counterparty" else None)
    target_tid = payload.transaction_id or (payload.target_value if payload.target_type in ("transaction", "transaction_id") else None)

    def apply_mapping(data: dict) -> dict:
        # This callback runs while the store holds the per-session process lock.
        txns: list[Transaction] = []
        for item in data.get("transactions", []):
            txns.append(item if isinstance(item, Transaction) else Transaction(**item))

        modified_txns: list[dict] = []
        for txn in txns:
            matches = bool(target_tid and txn.id == target_tid)
            if not matches and target_cp:
                cp = (txn.counterparty or txn.merchant or "").strip().casefold()
                matches = bool(cp and cp == target_cp.strip().casefold())
            if not matches:
                continue
            old_category = txn.category
            txn.category = payload.new_category
            txn.confidence = "High"
            txn.confidence_score = 1.0
            txn.classification_source = "user"
            txn.classification_reason = f"User confirmed category mapping to '{payload.new_category}'"
            modified_txns.append({
                "transaction_id": txn.id,
                "date": txn.date.isoformat() if hasattr(txn.date, "isoformat") else str(txn.date),
                "amount": txn.amount,
                "old_category": old_category,
                "new_category": payload.new_category,
                "counterparty": txn.counterparty or txn.merchant,
                "change_source": "user_ui_remapping",
            })

        data["transactions"] = [t.model_dump(mode="json") for t in txns]
        data["metrics"] = compute_metrics(txns).model_dump(mode="json")
        data["category_summary"] = build_category_summary(txns)
        data.setdefault("audit_trail", [])
        if not isinstance(data["audit_trail"], list):
            data["audit_trail"] = []

        old_categories = sorted({m["old_category"] for m in modified_txns})
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": "category_remap",
            "change_source": "user_ui_remapping",
            "target": target_cp or target_tid,
            "target_type": payload.target_type or ("counterparty" if target_cp else "transaction_id"),
            "counterparty": target_cp or (modified_txns[0]["counterparty"] if modified_txns else None),
            "transaction_ids": [m["transaction_id"] for m in modified_txns],
            "old_category": old_categories[0] if len(old_categories) == 1 else ", ".join(old_categories) or None,
            "new_category": payload.new_category,
            "modified_count": len(modified_txns),
            "changes": modified_txns,
        }
        data["audit_trail"].append(audit_entry)
        return {
            "status": "success",
            "modified_count": len(modified_txns),
            "new_category": payload.new_category,
            "metrics": data["metrics"],
            "category_summary": data["category_summary"],
            "audit_trail": data["audit_trail"],
        }

    try:
        _, response = session_store.update(session_id, apply_mapping)
        return response
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail="Session not found or expired. Please upload your statement again.",
        )
