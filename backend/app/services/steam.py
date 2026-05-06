import logging
from datetime import datetime
from typing import Any

import httpx
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)

_INVENTORY_URL = "https://steamcommunity.com/inventory/{steam_id}/730/2"
_PRICE_HISTORY_URL = "https://steamcommunity.com/market/pricehistory/"


class SteamError(Exception):
    pass


class SteamAuthError(SteamError):
    pass


class SteamPrivateInventoryError(SteamError):
    pass


# ── Internal response models ──────────────────────────────────────────────────

class _SteamAsset(BaseModel):
    assetid: str
    classid: str


class _SteamDescription(BaseModel):
    classid: str
    market_hash_name: str = ""
    icon_url: str = ""
    marketable: int = 0


class _SteamInventoryResponse(BaseModel):
    assets: list[_SteamAsset] = []
    descriptions: list[_SteamDescription] = []
    success: int = 0
    more_items: int = 0
    last_assetid: str | None = None


# ── Public return types ───────────────────────────────────────────────────────

class InventoryItem(BaseModel):
    asset_id: str
    market_hash_name: str
    icon_url: str


class SteamPricePoint(BaseModel):
    recorded_at: datetime
    price_median: int  # EUR × 100, stored in cents
    volume: int


# ── Helpers ───────────────────────────────────────────────────────────────────

def parse_steam_date(date_str: str) -> datetime:
    # Steam format: "Apr 15 2021 01: +0"
    cleaned = date_str.replace(": +0", "").strip()
    return datetime.strptime(cleaned, "%b %d %Y %H")


# ── Client ────────────────────────────────────────────────────────────────────

class SteamClient:
    def __init__(self, steam_login_secure: str | None = None) -> None:
        cookies: dict[str, str] = {}
        if steam_login_secure:
            cookies["steamLoginSecure"] = steam_login_secure
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            cookies=cookies,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"},
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def get_inventory(self, steam_id: str) -> list[InventoryItem]:
        """
        Returns all CS2 items in the user's public Steam inventory, paginating
        automatically via more_items / last_assetid until the full inventory is fetched.
        Raises SteamPrivateInventoryError if the inventory is set to private.
        Returns [] without raising if the inventory is empty or the response is null.
        """
        url = _INVENTORY_URL.format(steam_id=steam_id)
        all_assets: list[_SteamAsset] = []
        desc_by_classid: dict[str, _SteamDescription] = {}
        start_assetid: str | None = None

        while True:
            params: dict[str, Any] = {"l": "english", "count": 75}
            if start_assetid is not None:
                params["start_assetid"] = start_assetid

            try:
                response = await self._client.get(url, params=params)
            except httpx.RequestError as exc:
                raise SteamError(f"Inventory request failed: {exc}") from exc

            if response.status_code == 403:
                raise SteamPrivateInventoryError(
                    f"Steam inventory is private for steam_id={steam_id}"
                )

            response.raise_for_status()

            raw_json = response.json()
            if not raw_json:
                logger.warning("Inventaire vide ou privé pour %s", steam_id)
                break

            try:
                data = _SteamInventoryResponse.model_validate(raw_json)
            except Exception as exc:
                logger.error(
                    "Failed to parse Steam inventory for steam_id=%s: %s", steam_id, exc
                )
                break

            if data.success != 1:
                logger.warning(
                    "Steam inventory success=%d for steam_id=%s", data.success, steam_id
                )
                break

            all_assets.extend(data.assets)
            for desc in data.descriptions:
                desc_by_classid.setdefault(desc.classid, desc)

            if data.more_items != 1 or not data.last_assetid:
                break

            start_assetid = data.last_assetid

        result: list[InventoryItem] = []
        for asset in all_assets:
            desc = desc_by_classid.get(asset.classid)
            if desc is None or not desc.market_hash_name:
                continue
            result.append(
                InventoryItem(
                    asset_id=asset.assetid,
                    market_hash_name=desc.market_hash_name,
                    icon_url=desc.icon_url,
                )
            )

        return result

    async def get_price_history(
        self, market_hash_name: str
    ) -> list[SteamPricePoint]:
        """
        Fetches Steam Market price history for backfill (EUR, stored as cents).
        Requires the steamLoginSecure cookie — raises SteamAuthError if absent or expired.
        Caller must enforce rate limiting: 1 request per 3 seconds minimum.
        """
        try:
            response = await self._client.get(
                _PRICE_HISTORY_URL,
                params={
                    "appid": 730,
                    "market_hash_name": market_hash_name,
                    "currency": 3,  # EUR
                },
            )
        except httpx.RequestError as exc:
            raise SteamError(f"Price history request failed: {exc}") from exc

        if response.status_code in (401, 403):
            logger.error(
                "Steam price history unauthorized for %r — check STEAM_LOGIN_SECURE",
                market_hash_name,
            )
            raise SteamAuthError(
                "Steam price history requires a valid steamLoginSecure cookie"
            )

        if response.status_code == 429:
            logger.warning(
                "Steam price history rate limited for %r — min 1 req/3s",
                market_hash_name,
            )
            raise SteamError("Steam rate limit — slow down requests to 1 req/3s minimum")

        response.raise_for_status()

        raw = response.json()
        entries: list[Any] = raw.get("prices", [])  # type: ignore[assignment]

        result: list[SteamPricePoint] = []
        for entry in entries:
            try:
                date_str, price_eur, volume_str = entry[0], entry[1], entry[2]
                recorded_at = parse_steam_date(str(date_str))
                price_cents = round(float(price_eur) * 100)
                volume = int(volume_str)
            except (ValueError, IndexError, TypeError) as exc:
                logger.warning("Skipping malformed Steam price entry %r: %s", entry, exc)
                continue
            result.append(
                SteamPricePoint(
                    recorded_at=recorded_at,
                    price_median=price_cents,
                    volume=volume,
                )
            )

        return result


steam_client = SteamClient(settings.STEAM_LOGIN_SECURE or None)
