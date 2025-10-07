import asyncio
import random
from openai import AsyncOpenAI, RateLimitError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import ApiKey

BASE_URL = "https://api.longcat.chat/openai"

async def get_active_api_key(session: AsyncSession) -> str:
    stmt = select(ApiKey).where(ApiKey.is_active == 1)
    result = await session.execute(stmt)
    keys = result.scalars().all()
    if not keys:
        raise ValueError("No active API keys available")
    return random.choice(keys).key

async def mark_key_exhausted(session: AsyncSession, key: str):
    stmt = select(ApiKey).where(ApiKey.key == key)
    result = await session.execute(stmt)
    api_key = result.scalar_one_or_none()
    if api_key:
        api_key.is_active = 0
        await session.commit()

async def get_ai_response(messages: list, session: AsyncSession) -> str:
    max_retries = 5
    for attempt in range(max_retries):
        try:
            api_key = await get_active_api_key(session)
            print(f"🔑 Используется ключ: {api_key[:8]}...")  # ← для отладки
            client = AsyncOpenAI(api_key=api_key, base_url=BASE_URL)
            response = await client.chat.completions.create(
                model="LongCat-Flash-Chat",
                messages=messages,
                max_tokens=500,
                temperature=0.7,
                timeout=30.0
            )
            return response.choices[0].message.content
        except RateLimitError as e:
            error_data = e.body if hasattr(e, 'body') else {}
            if error_data.get("error", {}).get("code") == "rate_limit_exceeded":
                print(f"Rate limit hit for key {api_key}. Marking as exhausted.")
                await mark_key_exhausted(session, api_key)
                await asyncio.sleep(1)
                continue
            else:
                raise
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(1)
    raise Exception("Max retries exceeded for AI response")