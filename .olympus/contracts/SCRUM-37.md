# Design Contract — SCRUM-37

> Add GET /api/v1/users/{user_id}/loyalty that computes a customer's loyalty tier and cashback rate from their COMPLETED order history.

## Endpoints
- `GET /api/v1/users/{user_id}/loyalty`

## Request
```json
{}
```

## Success
```json
{
  "status": 200,
  "body": {
    "user_id": "int (echoed from path)",
    "total_spend": "float (sum of COMPLETED orders, 2 decimals)",
    "tier": "Bronze|Silver|Gold|Platinum",
    "cashback_percent": "int 0|1|2|5",
    "next_tier": "Silver|Gold|Platinum|null",
    "spend_to_next_tier": "float (lower bound of next tier - total_spend, 2 decimals; 0 for Platinum)"
  }
}
```

## Error contract
- **user_id not found in users table** → `404` `{"detail": "User not found"}`

## Business rules
- total_spend = SUM(orders.amount) WHERE orders.user_id = {user_id} AND orders.status = 'COMPLETED'
- CANCELLED and PENDING orders are NOT counted in total_spend
- User with no orders has total_spend = 0
- Tier by total_spend (lower bound inclusive): Bronze 0-4,999 (cashback 0%), Silver 5,000-19,999 (cashback 1%), Gold 20,000-49,999 (cashback 2%), Platinum >= 50,000 (cashback 5%)
- spend_to_next_tier = (lower bound of next tier) - total_spend
- Platinum is top tier: next_tier = null, spend_to_next_tier = 0
- Round total_spend and spend_to_next_tier to 2 decimals
- The endpoint reads from the database (users, orders tables) — this is a stateful read endpoint

## Edge cases
- user with no orders (total_spend = 0 -> Bronze)
- total_spend exactly 4,999 (Bronze boundary)
- total_spend exactly 5,000 (Silver lower bound)
- total_spend exactly 19,999 (Silver upper bound)
- total_spend exactly 20,000 (Gold lower bound)
- total_spend exactly 49,999 (Gold upper bound)
- total_spend exactly 50,000 (Platinum lower bound)
- CANCELLED and PENDING orders excluded from sum
- user_id not in users table -> 404
- total_spend with fractional amounts (e.g. 12500.50) rounds to 2 decimals

## Worked examples (oracle)
- `{"user_id": 1, "orders": []}` → `{"user_id": 1, "total_spend": 0.0, "tier": "Bronze", "cashback_percent": 0, "next_tier": "Silver", "spend_to_next_tier": 5000.0}`
- `{"user_id": 2, "orders": [{"amount": 4999.0, "status": "COMPLETED"}]}` → `{"user_id": 2, "total_spend": 4999.0, "tier": "Bronze", "cashback_percent": 0, "next_tier": "Silver", "spend_to_next_tier": 1.0}`
- `{"user_id": 3, "orders": [{"amount": 5000.0, "status": "COMPLETED"}]}` → `{"user_id": 3, "total_spend": 5000.0, "tier": "Silver", "cashback_percent": 1, "next_tier": "Gold", "spend_to_next_tier": 15000.0}`
- `{"user_id": 4, "orders": [{"amount": 12500.0, "status": "COMPLETED"}]}` → `{"user_id": 4, "total_spend": 12500.0, "tier": "Silver", "cashback_percent": 1, "next_tier": "Gold", "spend_to_next_tier": 7500.0}`
- `{"user_id": 5, "orders": [{"amount": 20000.0, "status": "COMPLETED"}]}` → `{"user_id": 5, "total_spend": 20000.0, "tier": "Gold", "cashback_percent": 2, "next_tier": "Platinum", "spend_to_next_tier": 30000.0}`
- `{"user_id": 6, "orders": [{"amount": 49999.0, "status": "COMPLETED"}]}` → `{"user_id": 6, "total_spend": 49999.0, "tier": "Gold", "cashback_percent": 2, "next_tier": "Platinum", "spend_to_next_tier": 1.0}`
- `{"user_id": 7, "orders": [{"amount": 50000.0, "status": "COMPLETED"}]}` → `{"user_id": 7, "total_spend": 50000.0, "tier": "Platinum", "cashback_percent": 5, "next_tier": null, "spend_to_next_tier": 0.0}`
- `{"user_id": 8, "orders": [{"amount": 30000.0, "status": "COMPLETED"}, {"amount": 25000.0, "status": "CANCELLED"}]}` → `{"user_id": 8, "total_spend": 30000.0, "tier": "Gold", "cashback_percent": 2, "next_tier": "Platinum", "spend_to_next_tier": 20000.0}`
- `{"user_id": 9, "orders": [{"amount": 12500.5, "status": "COMPLETED"}]}` → `{"user_id": 9, "total_spend": 12500.5, "tier": "Silver", "cashback_percent": 1, "next_tier": "Gold", "spend_to_next_tier": 7499.5}`

## Files to touch
- src/routers/loyalty.py
- src/main.py

## Out of scope (regression guard)
- Authentication and authorization
- Creating or updating orders
- Actually applying cashback
- Any existing user or order endpoints must keep working unchanged
