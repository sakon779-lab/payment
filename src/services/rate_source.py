"""Exchange rate source for SCRUM-5 payment intents.

Fetches the current fiat->crypto exchange rate from an external exchange API
(mock or public, e.g. CoinGecko/Binance). The URL is configurable via env var
so tests can point it at a mock and production can point it at a real source.

The handler calls `fetch_rate(...)` upstream of the pure pricing rule; the rule
itself never performs I/O.
"""
import os
import httpx

# Base URL of the rate source. In docker-compose this resolves to the mockserver
# service; in tests it is patched out entirely.
RATE_SOURCE_URL = os.getenv(
    "RATE_SOURCE_URL",
    "http://mockserver:1080/external/rate",
)


class RateUnavailable(Exception):
    """Raised when the rate source is unreachable or returns no usable rate."""


async def fetch_rate(token_symbol: str, network: str, fiat_currency: str = "THB") -> float:
    """Fetch the current exchange rate (fiat per 1 token) for token/network.

    Returns a positive float. Raises RateUnavailable on any failure so the
    route can translate it into a 502 'Exchange rate unavailable'.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                RATE_SOURCE_URL,
                params={
                    "token_symbol": token_symbol,
                    "network": network,
                    "fiat_currency": fiat_currency,
                },
            )
        if resp.status_code != 200:
            raise RateUnavailable("non-200 from rate source")
        data = resp.json()
        rate = data.get("rate")
        if rate is None:
            raise RateUnavailable("no rate in response")
        rate = float(rate)
        if rate <= 0:
            raise RateUnavailable("non-positive rate")
        return rate
    except RateUnavailable:
        raise
    except Exception as exc:  # network error, bad JSON, etc.
        raise RateUnavailable(str(exc)) from exc