import asyncio
import logging
from typing import Any

import httpx
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)

_BASE_URL = "https://csfloat.com/api/v1"


class CSFloatError(Exception):
    pass


class CSFloatRateLimitError(CSFloatError):
    pass


class _CSFloatItem(BaseModel):
    market_hash_name: str | None = None
    float_value: float | None = None


class _CSFloatListing(BaseModel):
    price: int
    item: _CSFloatItem | None = None


class CSFloatListingsStats(BaseModel):
    market_hash_name: str
    price_min_cents: int | None
    price_max_cents: int | None
    price_median_cents: int | None
    listing_count: int


class CSFloatClient:
    def __init__(self, api_key: str) -> None:
        self._client = httpx.AsyncClient(
            base_url=_BASE_URL,
            headers={"Authorization": api_key},
            timeout=httpx.Timeout(30.0),
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def _get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        max_attempts: int = 3,
    ) -> httpx.Response:
        delay = 4.0
        for attempt in range(max_attempts):
            try:
                response = await self._client.get(path, params=params)
            except httpx.RequestError as exc:
                if attempt >= max_attempts - 1:
                    raise CSFloatError(
                        f"Network error after {max_attempts} attempts: {exc}"
                    ) from exc
                logger.warning(
                    "CSFloat network error (attempt %d/%d): %s",
                    attempt + 1,
                    max_attempts,
                    exc,
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, 60.0)
                continue

            if response.status_code == 429:
                if attempt >= max_attempts - 1:
                    raise CSFloatRateLimitError(
                        f"Rate limit exceeded after {max_attempts} attempts"
                    )
                retry_after = float(response.headers.get("Retry-After", delay))
                wait = max(retry_after, delay)
                logger.warning(
                    "CSFloat 429 rate limit (attempt %d/%d), retrying in %.1fs",
                    attempt + 1,
                    max_attempts,
                    wait,
                )
                await asyncio.sleep(wait)
                delay = min(delay * 2, 60.0)
                continue

            if response.status_code == 401:
                logger.critical("CSFloat API key is invalid or expired")
                raise CSFloatError("Unauthorized — verify CSFLOAT_API_KEY")

            if response.status_code >= 500:
                if attempt >= max_attempts - 1:
                    raise CSFloatError(
                        f"CSFloat server error {response.status_code} after {max_attempts} attempts"
                    )
                logger.warning(
                    "CSFloat server error %d (attempt %d/%d), retrying in %.1fs",
                    response.status_code,
                    attempt + 1,
                    max_attempts,
                    delay,
                )
                await asyncio.sleep(delay)
                delay = min(delay * 2, 60.0)
                continue

            return response

        raise CSFloatError("Max retry attempts reached")

    async def get_listings(self, market_hash_name: str) -> int | None:
        """
        Returns the lowest listed price in cents for the given skin, or None if not listed.
        Sorted by lowest_price so the first result is the cheapest buy-now listing.
        """
        response = await self._get(
            "/listings",
            params={
                "market_hash_name": market_hash_name,
                "sort_by": "lowest_price",
                "type": "buy_now",
                "limit": 1,
            },
        )

        if response.status_code == 404:
            return None

        raw = response.json()
        # Handle both {"data": [...]} wrapper and plain list
        if isinstance(raw, dict):
            listings_raw = raw.get("data", [])
        elif isinstance(raw, list):
            listings_raw = raw
        else:
            logger.error(
                "Unexpected CSFloat response type %s for %r",
                type(raw).__name__,
                market_hash_name,
            )
            return None

        if not listings_raw:
            return None

        try:
            first = _CSFloatListing.model_validate(listings_raw[0])
        except Exception as exc:
            logger.error(
                "Failed to parse CSFloat listing for %r: %s", market_hash_name, exc
            )
            return None

        return first.price

    async def get_listings_stats(
        self, market_hash_name: str
    ) -> CSFloatListingsStats | None:
        """
        Returns min/max/median prices and listing count for a skin (up to 50 listings).
        Returns None if no listings exist (404).
        """
        response = await self._get(
            "/listings",
            params={
                "market_hash_name": market_hash_name,
                "sort_by": "lowest_price",
                "type": "buy_now",
                "limit": 50,
            },
        )

        if response.status_code == 404:
            return None

        raw = response.json()
        if isinstance(raw, dict):
            listings_raw = raw.get("data", [])
        elif isinstance(raw, list):
            listings_raw = raw
        else:
            logger.error(
                "Unexpected CSFloat response type %s for stats %r",
                type(raw).__name__,
                market_hash_name,
            )
            return None

        prices: list[int] = []
        for entry in listings_raw:
            try:
                prices.append(_CSFloatListing.model_validate(entry).price)
            except Exception:
                continue

        if not prices:
            return CSFloatListingsStats(
                market_hash_name=market_hash_name,
                price_min_cents=None,
                price_max_cents=None,
                price_median_cents=None,
                listing_count=0,
            )

        prices_sorted = sorted(prices)
        return CSFloatListingsStats(
            market_hash_name=market_hash_name,
            price_min_cents=prices_sorted[0],
            price_max_cents=prices_sorted[-1],
            price_median_cents=prices_sorted[len(prices_sorted) // 2],
            listing_count=len(prices_sorted),
        )


csfloat_client = CSFloatClient(settings.CSFLOAT_API_KEY)
