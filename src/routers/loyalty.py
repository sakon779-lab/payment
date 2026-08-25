from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.main import get_db, User, Order

router = APIRouter(prefix="/api/v1/users", tags=["loyalty"])

# Tier boundaries: (name, lower_bound_inclusive, cashback_percent)
TIERS = [
    ("Bronze",   0,     0),
    ("Silver",   5000,  1),
    ("Gold",     20000, 2),
    ("Platinum", 50000, 5),
]

def rules_code(total_spend):
    """Pure function: total_spend (THB) -> tier info."""
    ts = round(float(total_spend), 2)

    def money(x):
        x = round(x, 2)
        return int(x) if x == int(x) else x

    idx = 0
    for i, (_name, lb, _cb) in enumerate(TIERS):
        if ts >= lb:
            idx = i
    name, _lb, cb = TIERS[idx]

    if name == "Platinum":
        return {"tier": name, "cashback_percent": cb, "next_tier": None, "spend_to_next_tier": 0}

    nxt_name, nxt_lb, _nxt_cb = TIERS[idx + 1]
    return {
        "tier": name,
        "cashback_percent": cb,
        "next_tier": nxt_name,
        "spend_to_next_tier": money(nxt_lb - ts),
    }

@router.get("/{user_id}/loyalty")
def get_loyalty(user_id: int, db: Session = Depends(get_db)):
    # Check user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Compute total_spend from COMPLETED orders only
    total_spend = db.query(func.coalesce(func.sum(Order.amount), 0.0)).filter(
        Order.user_id == user_id,
        Order.status == "COMPLETED"
    ).scalar()

    total_spend = round(float(total_spend), 2)

    # Apply tier rules
    tier_info = rules_code(total_spend)

    return {
        "user_id": user_id,
        "total_spend": total_spend,
        **tier_info,
    }