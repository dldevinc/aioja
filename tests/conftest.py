import pytest


@pytest.fixture
async def aioredis_pool():
    import aioredis
    pool = await aioredis.create_redis_pool('redis://localhost:6379/0')
    yield pool
    pool.close()
    await pool.wait_closed()
