"""
Script de test manuel des clients API. À supprimer après validation.
Usage : python test_clients.py
"""
import asyncio
import sys

STEAM_ID = "76561198391048053"  # Remplace par ton SteamID64
TEST_SKIN = "AK-47 | Redline (Field-Tested)"


async def test_csfloat() -> None:
    from app.services.csfloat import csfloat_client, CSFloatError

    print("\n── CSFloat ──────────────────────────────")
    try:
        price = await csfloat_client.get_listings(TEST_SKIN)
        if price is None:
            print(f"  OK  aucun listing trouvé pour {TEST_SKIN!r}")
        else:
            print(f"  OK  prix minimum = {price} centimes ({price / 100:.2f} €)")
    except CSFloatError as exc:
        print(f"  ERREUR  {exc}")
    finally:
        await csfloat_client.close()


async def test_skinport() -> None:
    from app.services.skinport import skinport_client, SkinportError

    print("\n── Skinport ─────────────────────────────")
    try:
        prices = await skinport_client.get_item_prices([TEST_SKIN])
        if not prices:
            print(f"  OK  aucun résultat pour {TEST_SKIN!r} (hors stock ou non trouvé)")
        else:
            for name, cents in prices.items():
                print(f"  OK  {name!r} → médiane = {cents} centimes ({cents / 100:.2f} €)")
    except SkinportError as exc:
        print(f"  ERREUR  {exc}")
    finally:
        await skinport_client.close()


async def test_steam() -> None:
    from app.services.steam import steam_client, SteamError, SteamPrivateInventoryError

    print("\n── Steam inventaire ─────────────────────")
    if STEAM_ID == "<TON_STEAM_ID>":
        print("  SKIP  remplace STEAM_ID dans le script avant de tester")
        return
    try:
        items = await steam_client.get_inventory(STEAM_ID)
        print(f"  OK  {len(items)} item(s) trouvé(s) dans l'inventaire")
        for item in items[:3]:
            print(f"       • {item.market_hash_name} (asset_id={item.asset_id})")
        if len(items) > 3:
            print(f"       … et {len(items) - 3} autre(s)")
    except SteamPrivateInventoryError:
        print("  ERREUR  inventaire privé — rends-le public sur Steam")
    except SteamError as exc:
        print(f"  ERREUR  {exc}")
    finally:
        await steam_client.close()


async def main() -> None:
    print(f"Skin testé : {TEST_SKIN!r}")
    await test_csfloat()
    await test_skinport()
    await test_steam()
    print()


if __name__ == "__main__":
    asyncio.run(main())
