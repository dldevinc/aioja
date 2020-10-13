from typing import TypeVar

from aioredis import ConnectionsPool, Redis

from . import AsyncBytecodeCache

RedisPool = TypeVar('RedisPool', Redis, ConnectionsPool)


class AioRedisBytecodeCache(AsyncBytecodeCache):
    def __init__(self, pool: RedisPool = None, prefix: str = 'jinja2'):
        self.pool = pool
        self.prefix = prefix

    def make_key(self, bucket):
        return '%s:%s' % (self.prefix, str(bucket.key))

    async def load_bytecode(self, bucket):
        key = self.make_key(bucket)
        bytecode = await self.pool.get(key)
        if bytecode:
            bucket.bytecode_from_string(bytecode)

    async def dump_bytecode(self, bucket):
        key = self.make_key(bucket)
        await self.pool.set(key, bucket.bytecode_to_string())
