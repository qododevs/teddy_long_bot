# utils/openai_client.py
import asyncio
from datetime import datetime, timedelta
from openai import AsyncOpenAI, RateLimitError, AuthenticationError, APIError
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from models import ApiKey

BASE_URL = "https://api.longcat.chat/openai/v1"  # ← Обратите внимание: /v1 !
TIMEOUT = 30.0

async def get_active_api_key(session: AsyncSession) -> str:
    now = datetime.utcnow()
    stmt = select(ApiKey).where(
        (ApiKey.blocked_until.is_(None)) | (ApiKey.blocked_until < now)
    ).order_by(ApiKey.id)
    result = await session.execute(stmt)
    key_obj = result.scalars().first()
    if not key_obj:
        raise ValueError("No available API keys")
    return key_obj.key

async def block_key_for_24h(session: AsyncSession, key: str):
    now = datetime.utcnow()
    blocked_until = now + timedelta(hours=24)
    stmt = update(ApiKey).where(ApiKey.key == key).values(blocked_until=blocked_until)
    await session.execute(stmt)
    await session.commit()
    print(f"🔑 Ключ {key[:8]}... заблокирован до {blocked_until} UTC")

async def get_ai_response(messages: list, session: AsyncSession) -> str:
    max_retries = 10
    for attempt in range(max_retries):
        try:
            api_key = await get_active_api_key(session)
            client = AsyncOpenAI(
                api_key=api_key,
                base_url=BASE_URL,
                timeout=TIMEOUT
            )

            response = await client.chat.completions.create(
                model="LongCat-Flash-Chat",
                messages=messages,
                max_tokens=1000,
                temperature=0.9
            )
            return response.choices[0].message.content

        except RateLimitError as e:
            # Ошибка 429: лимит исчерпан
            print(f"⏳ Rate limit hit for key: {api_key[:8]}...")
            await block_key_for_24h(session, api_key)
            await asyncio.sleep(0.5)
            continue

        except AuthenticationError as e:
            # Ошибка 401: неверный ключ
            print(f"❌ 401 Unauthorized for key: {api_key[:8]}...")
            await block_key_for_24h(session, api_key)
            await asyncio.sleep(0.5)
            continue

        except APIError as e:
            # Другие ошибки API
            print(f"⚠️ API Error: {e}")
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(1)
            continue

        except Exception as e:
            print(f"💥 Неизвестная ошибка: {e}")
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(1)
            continue

    raise Exception("No valid API keys available after all retries")