from typing import TypeVar, Union, Iterable

from aioredis import ConnectionsPool, Redis, create_pool

from . import AsyncBytecodeCache

RedisPool = TypeVar('RedisPool', Redis, ConnectionsPool)


class AioRedisBytecodeCache(AsyncBytecodeCache):
    def __init__(
        self,
        pool_or_addr: Union[str, Iterable, RedisPool] = None,
        prefix: str = 'jinja2'
    ):
        self._backend = None
        self._pool_or_addr = pool_or_addr
        self._prefix = prefix

    @property
    async def backend(self):
        if self._backend is None:
            if isinstance(self._pool_or_addr, (str, Iterable)):
                self._backend = await create_pool(self._pool_or_addr)
            else:
                self._backend = self._pool_or_addr
        return self._backend

    def make_key(self, bucket):
        return '%s:%s' % (self._prefix, str(bucket.key))

    async def load_bytecode(self, bucket):
        key = self.make_key(bucket)
        pool = await self.backend
        context = await pool
        with context as conn:
            conn = Redis(conn)
            bytecode = await conn.get(key)
        if bytecode:
            bucket.bytecode_from_string(bytecode)

    async def dump_bytecode(self, bucket):
        key = self.make_key(bucket)
        pool = await self.backend
        context = await pool
        with context as conn:
            conn = Redis(conn)
            await conn.set(key, bucket.bytecode_to_string())
