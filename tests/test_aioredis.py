import pytest

from aioja.bccache.aioredis import AioRedisBytecodeCache
from aioja.environment import Environment
from aioja.loaders import FileSystemLoader


@pytest.mark.asyncio
async def test_aioredis_bytecode_cache(aioredis_pool):
    env = Environment(
        trim_blocks=True,
        lstrip_blocks=True,
        loader=FileSystemLoader('tests/templates'),
        bytecode_cache=AioRedisBytecodeCache(aioredis_pool)
    )

    bucket_key = '0d5e391ad86ee505e39df96fbcb5c9822224798f'

    # clean bytecode cache
    cache_key = 'jinja2:%s' % bucket_key
    await aioredis_pool.delete(cache_key)
    assert await aioredis_pool.get(cache_key) is None

    # first load - from file
    file_template = await env.get_template('example.html')
    assert file_template is not None
    assert aioredis_pool.get(cache_key) is not None

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
