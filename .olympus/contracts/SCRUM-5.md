# Design Contract — SCRUM-5

> Create a payment intent for an order: fetch the current exchange rate server-side, compute the crypto amount with a 1% buffer rounded up to 6 decimals, allocate a one-time wallet address, and return a 15-minute TTL — idempotent per order_id.

## Endpoints
- `POST /api/v1/payments`

## Request
```json
{
  "order_id": "string, required, non-empty",
  "fiat_amount": "number, required, > 0",
  "fiat_currency": "string, required, must be THB",
  "token_symbol": "string, required, one of USDT|USDC",
  "network": "string, required, one of POLYGON|ETHEREUM|BSC"
}
```

## Success
```json
{
  "status": 201,
  "body": {
    "payment_id": "server-generated PAY-<uuid>, e.g. \"PAY-UUID-789\"",
    "wallet_address": "one-time HD-wallet address, e.g. \"0x123...abc\"",
    "crypto_amount": "6-decimal fixed-point string, rounded up, e.g. \"28.500000\"",
    "exchange_rate": "2-decimal fixed-point string of the locked rate, e.g. \"35.50\"",
    "expires_at": "ISO-8601 UTC, now + 15 minutes, e.g. \"2023-10-27T10:15:00Z\"",
    "status": "PENDING"
  }
}
```

## Error contract
- **order_id missing or null** → `400` `{"detail": "Order ID is required"}`
- **order_id empty or whitespace-only** → `400` `{"detail": "Order ID is required"}`
- **fiat_amount missing or null** → `400` `{"detail": "Fiat amount is required"}`
- **fiat_amount not a number (e.g. "abc")** → `400` `{"detail": "Fiat amount must be a number"}`
- **fiat_amount <= 0** → `400` `{"detail": "Fiat amount must be greater than zero"}`
- **fiat_currency missing or null** → `400` `{"detail": "Fiat currency is required"}`
- **fiat_currency not THB** → `400` `{"detail": "Unsupported Currency"}`
- **token_symbol missing or null** → `400` `{"detail": "Token symbol is required"}`
- **token_symbol not in USDT|USDC** → `400` `{"detail": "Unsupported Currency"}`
- **network missing or null** → `400` `{"detail": "Network is required"}`
- **network not in POLYGON|ETHEREUM|BSC** → `400` `{"detail": "Unsupported Network"}`
- **the rate source (mock/public exchange API) is unreachable or returns no usable rate for the requested token/network** → `502` `{"detail": "Exchange rate unavailable"}`

## Business rules
- The endpoint is STATEFUL: it writes one row to payment_transactions (order_id, payment_address, amount_expected, status='PENDING', expires_at, created_at) and reads it back for idempotency.
- The exchange rate is NEVER a client-supplied request field. The handler fetches the current rate from the rate source (mock or public exchange API such as CoinGecko/Binance) via src/services/rate_source.py, upstream of the rule, and passes it into the rule as exchange_rate. The request body carries exactly five fields: order_id, fiat_amount, fiat_currency, token_symbol, network.
- Every request field is declared OPTIONAL in the pydantic model and validated explicitly in the route body, so each error detail string below is raised by an explicit HTTPException from the route (the src/routers/loyalty.py precedent) and the shared RequestValidationError handler in src/main.py is never reached and never modified.
- Validation order: order_id -> fiat_amount (present, numeric, > 0) -> fiat_currency -> token_symbol -> network -> rate fetch. The FIRST failing check returns its error_contract entry; later checks are not evaluated.
- fiat_currency must equal 'THB' (case-sensitive). Any other value -> 400 'Unsupported Currency'.
- token_symbol must be one of USDT, USDC (case-sensitive). Any other value (e.g. DOGE) -> 400 'Unsupported Currency'.
- network must be one of POLYGON, ETHEREUM, BSC (case-sensitive). Any other value -> 400 'Unsupported Network'.
- crypto_amount = (fiat_amount / exchange_rate) * 1.01, then rounded UP (ceiling) to exactly 6 decimal places, rendered as a fixed 6-decimal string (e.g. "28.500000").
- exchange_rate in the response is the locked rate rendered as a fixed 2-decimal string (e.g. "35.50").
- expires_at = server current time + 15 minutes, ISO-8601 UTC (e.g. "2023-10-27T10:15:00Z"). This is runtime-assigned and NOT part of the deterministic oracle.
- payment_id is a server-generated UUID prefixed PAY- (e.g. "PAY-UUID-789"); wallet_address is a one-time HD-wallet address (e.g. "0x123...abc"). Both are runtime-assigned and NOT part of the deterministic oracle.
- Idempotency: a repeat call with the SAME order_id while an existing PENDING row has expires_at > now returns the EXISTING payment_id, wallet_address, crypto_amount, exchange_rate, expires_at with status 201 and creates no new row. A repeat call after expiry creates a NEW intent (201).
- The rule receives exchange_rate as an input and never performs I/O; the fetch happens in the handler before the rule is called.
- payment_transactions.order_id is VARCHAR with NO foreign key to orders.id. The ticket's DB schema labels order_id as an FK, but orders.id is Integer while the card's own example order_id is the string "ORD-12345"; the FK is therefore impossible and must not be restored.
- The literal values "PAY-UUID-789", "0x123...abc", "28.500000" and "2023-10-27T10:15:00Z" in the ticket are ILLUSTRATIVE placeholders showing the response field FORMATS (UUID-prefixed id, hex address, 6-decimal amount, ISO-8601 UTC timestamp) — they are not fixed values the endpoint must return.

## Edge cases
- fiat_amount exactly at the smallest positive value (e.g. 0.01) — must succeed
- fiat_amount = 0 and fiat_amount < 0 — both rejected with 'Fiat amount must be greater than zero'
- fiat_amount as a non-numeric string "abc" — rejected with 'Fiat amount must be a number'
- fiat_amount as a numeric string "1000.00" — accepted (coerced to number)
- order_id whitespace-only "   " — rejected with 'Order ID is required'
- fiat_currency lowercase "thb" — rejected with 'Unsupported Currency' (case-sensitive)
- token_symbol "DOGE" — rejected with 'Unsupported Currency'
- network lowercase "polygon" — rejected with 'Unsupported Network' (case-sensitive)
- crypto_amount rounding: a value whose 7th decimal is non-zero must round UP, not to nearest
- rate source unreachable / returns no rate — 502 'Exchange rate unavailable'
- repeat call with same order_id inside the TTL — returns the existing intent, no new row
- repeat call with same order_id after expiry — creates a new intent
- order_id containing SQL/XSS payload (e.g. "'; DROP TABLE payment_transactions;--") — accepted as a valid non-empty string; assert it is stored/echoed without execution

## Worked examples (oracle)
- `{"order_id": "ORD-12345", "fiat_amount": 1000.0, "fiat_currency": "THB", "token_symbol": "USDT", "network": "POLYGON", "exchange_rate": 35.5}` → `{"crypto_amount": "28.450705", "exchange_rate": "35.50", "status": "PENDING"}`
- `{"order_id": "ORD-12345", "fiat_amount": 0.01, "fiat_currency": "THB", "token_symbol": "USDC", "network": "ETHEREUM", "exchange_rate": 35.5}` → `{"crypto_amount": "0.000285", "exchange_rate": "35.50", "status": "PENDING"}`
- `{"order_id": "ORD-12345", "fiat_amount": 1000.0, "fiat_currency": "THB", "token_symbol": "USDT", "network": "POLYGON", "exchange_rate": 33.333333}` → `{"crypto_amount": "30.300001", "exchange_rate": "33.33", "status": "PENDING"}`
- `{"order_id": "ORD-12345", "fiat_amount": 1000.0, "fiat_currency": "THB", "token_symbol": "DOGE", "network": "POLYGON", "exchange_rate": 35.5}` → `null`
- `{"order_id": "ORD-12345", "fiat_amount": "abc", "fiat_currency": "THB", "token_symbol": "USDT", "network": "POLYGON", "exchange_rate": 35.5}` → `null`

## Files to touch
- src/routers/payments.py — new APIRouter(prefix="/api/v1/payments") following the src/routers/loyalty.py precedent (from src.main import get_db, Base, ...)
- src/main.py — add the PaymentTransaction model beside User/Order/Base (a new models.py would create a second declarative_base() and the table would never be created on the engine's metadata); add the pydantic request/response models beside CheckoutRequest; include the payments router
- src/services/rate_source.py — the rate fetch required by the server-side rate rule (mock or public exchange API)

## Out of scope (regression guard)
- The shared RequestValidationError handler in src/main.py (lines ~55-56) must NOT be modified — no new field special-casing; all SCRUM-5 validation happens in the route body via explicit HTTPException
- POST /api/v1/checkout and its 'User not found' / 'Payment Declined' / 'Payment processing failed' behaviour must stay unchanged
- GET /api/v1/users/{user_id}/loyalty and its tier/cashback rules must stay unchanged
- GET /hello/{name}, GET /reverse/{text}, POST /check-password must stay unchanged
- The User and Order models and the existing orders table must not be altered
