import pytest
from aioredis import create_redis

from aioja.bccache.aioredis import AioRedisBytecodeCache
from aioja.environment import Environment
from aioja.loaders import FileSystemLoader


@pytest.mark.asyncio
async def test_aioredis_bytecode_cache(aioredis_pool):
    env = Environment(
        enable_async=True,
        trim_blocks=True,
        lstrip_blocks=True,
        loader=FileSystemLoader('tests/templates'),
        bytecode_cache=AioRedisBytecodeCache(aioredis_pool)
    )

    await _test_env(env)

    pool = await env.bytecode_cache.backend
    pool.close()
    await pool.wait_closed()


@pytest.mark.asyncio
async def test_aioredis_dsn_bytecode_cache():
    env = Environment(
        enable_async=True,
        trim_blocks=True,
        lstrip_blocks=True,
        loader=FileSystemLoader('tests/templates'),
        bytecode_cache=AioRedisBytecodeCache('redis://localhost:6379/0')
    )

    await _test_env(env)

    pool = await env.bytecode_cache.backend
    pool.close()
    await pool.wait_closed()


async def _test_env(env):
    bucket_key = '0d5e391ad86ee505e39df96fbcb5c9822224798f'
    redis_client = await create_redis('redis://localhost:6379/0')

    # clean bytecode cache
    cache_key = 'jinja2:%s' % bucket_key
    await redis_client.delete(cache_key)
    assert await redis_client.get(cache_key) is None

    # first load - from file
    file_template = await env.get_template('example.html')
    assert file_template is not None
    assert redis_client.get(cache_key) is not None

    # clean env cache
    env.cache.clear()

    # second load - from bytecode cache
    template = await env.get_template('example.html')
    assert template is not None

    content = await template.render_async(array=['One', 'Two', 'Three'])
    assert content == (
        '<ul>\n'
        '    <li>One</li>\n'
        '    <li>Two</li>\n'
        '    <li>Three</li>\n'
        '</ul>'
    )

    redis_client.close()
    await redis_client.wait_closed()
