import logging

import httpx
from pydantic import BaseModel

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.skinport.com/v1"


class SkinportError(Exception):
    pass


class SkinportRateLimitError(SkinportError):
    pass


class SkinportItemStats(BaseModel):
    median_cents: int | None
    min_cents: int | None
    max_cents: int | None
    quantity: int


class _SkinportItem(BaseModel):
    market_hash_name: str
    suggested_price: float | None = None
    min_price: float | None = None
    max_price: float | None = None
    mean_price: float | None = None
    median_price: float | None = None
    quantity: int = 0

    def to_median_cents(self) -> int | None:
        if self.median_price is None:
            return None
        return round(self.median_price * 100)

    def to_stats(self) -> SkinportItemStats:
        return SkinportItemStats(
            median_cents=round(self.median_price * 100) if self.median_price is not None else None,
            min_cents=round(self.min_price * 100) if self.min_price is not None else None,
            max_cents=round(self.max_price * 100) if self.max_price is not None else None,
            quantity=self.quantity,
        )


class SkinportClient:
    def __init__(self) -> None:
        # brotli package must be installed for br decompression
        self._client = httpx.AsyncClient(
            base_url=_BASE_URL,
            headers={"Accept-Encoding": "br"},
            timeout=httpx.Timeout(60.0),
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def get_item_prices(
        self, market_hash_names: list[str]
    ) -> dict[str, int]:
        """
        Returns {market_hash_name: median_price_cents} for the requested skins.
        Items absent from Skinport or with null median_price are not included.
        """
        raw_list = await self._fetch_items()
        if raw_list is None:
            return {}

        requested = set(market_hash_names)
        result: dict[str, int] = {}

        for entry in raw_list:
            try:
                item = _SkinportItem.model_validate(entry)
            except Exception as exc:
                logger.warning("Skipping malformed Skinport item: %s", exc)
                continue

            if item.market_hash_name not in requested:
                continue

            cents = item.to_median_cents()
            if cents is not None:
                result[item.market_hash_name] = cents

        return result

    async def get_item_stats(
        self, market_hash_names: list[str]
    ) -> dict[str, SkinportItemStats]:
        """
        Returns {market_hash_name: SkinportItemStats} with median/min/max/quantity
        for the requested skins. Skins absent from Skinport are not included.
        """
        raw_list = await self._fetch_items()
        if raw_list is None:
            return {}

        requested = set(market_hash_names)
        result: dict[str, SkinportItemStats] = {}

        for entry in raw_list:
            try:
                item = _SkinportItem.model_validate(entry)
            except Exception as exc:
                logger.warning("Skipping malformed Skinport item: %s", exc)
                continue
            if item.market_hash_name in requested:
                result[item.market_hash_name] = item.to_stats()

        return result

    async def _fetch_items(self) -> list[object] | None:
        """Shared fetch of the full /items catalogue."""
        try:
            response = await self._client.get(
                "/items",
                params={"app_id": 730, "currency": "EUR", "tradable": "false"},
            )
        except httpx.RequestError as exc:
            raise SkinportError(f"Network error: {exc}") from exc

        if response.status_code == 429:
            logger.warning("Skinport rate limit hit (8 req / 5 min)")
            raise SkinportRateLimitError("Skinport rate limit exceeded")

        if response.status_code >= 500:
            logger.error("Skinport server error: %d", response.status_code)
            raise SkinportError(f"Skinport server error {response.status_code}")

        response.raise_for_status()

        raw = response.json()
        if not isinstance(raw, list):
            logger.error(
                "Unexpected Skinport /items response format: %s", type(raw).__name__
            )
            return None

        return raw  # type: ignore[return-value]


skinport_client = SkinportClient()
