import asyncio, httpx
from app.config import settings

async def test():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            'https://csfloat.com/api/v1/listings',
            headers={'Authorization': settings.CSFLOAT_API_KEY},
            params={
                'market_hash_name': 'M4A1-S | Cyrex (Minimal Wear)',
                'sort_by': 'lowest_price',
                'limit': 3,
                'type': 'buy_now',
                'tradable_to': 1
            }
        )
        print('URL:', response.url)
        data = response.json()
        for item in data.get('data', [])[:3]:
            print('Prix:', item['price'], '| tradable:', item['item']['tradable'])

asyncio.run(test())
