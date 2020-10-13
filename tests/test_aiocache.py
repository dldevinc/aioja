import pytest

import aiocache
from aioja.bccache.aiocache import AioCacheBytecodeCache
from aioja.environment import Environment
from aioja.loaders import FileSystemLoader

aiocache.caches.set_config({
    'default': {
        'cache': "aiocache.SimpleMemoryCache",
        'serializer': {
            'class': "aiocache.serializers.StringSerializer"
        }
    },
    'redis': {
        'cache': "aiocache.RedisCache",
        'endpoint': "127.0.0.1",
        'port': 6379,
        'db': 0,
        'namespace': 'cache',
        'serializer': {
            'class': "aiocache.serializers.NullSerializer",
            'encoding': None,
        },
    }
})


@pytest.mark.asyncio
async def test_aiocache_bytecode_cache(aioredis_pool):
    env = Environment(
        trim_blocks=True,
        lstrip_blocks=True,
        loader=FileSystemLoader('tests/templates'),
        bytecode_cache=AioCacheBytecodeCache(cache_name='redis')
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
