import aiohttp

async def get_weather(lat, lon):
    async with aiohttp.ClientSession() as session:
        url = f'https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true'
        async with session.get(url) as response:
            data = await response.json()
            if 'current_weather' in data:
                return data['current_weather']['temperature']
            else:
                return None