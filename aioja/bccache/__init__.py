from jinja2.bccache import Bucket, BytecodeCache, FileSystemBytecodeCache

from jinja2.utils import open_if_exists


class AsyncBytecodeCache(BytecodeCache):
    async def get_bucket(self, environment, name, filename, source):
        key = self.get_cache_key(name, filename)
        checksum = self.get_source_checksum(source)
        bucket = Bucket(environment, key, checksum)
        await self.load_bytecode(bucket)
        return bucket

    async def set_bucket(self, bucket):
        await self.dump_bytecode(bucket)


class AsyncFileSystemBytecodeCache(AsyncBytecodeCache, FileSystemBytecodeCache):
    async def load_bytecode(self, bucket):
        f = open_if_exists(self._get_cache_filename(bucket), "rb")
        if f is not None:
            try:
                bucket.load_bytecode(f)
            finally:
                f.close()

    async def dump_bytecode(self, bucket):
        f = open(self._get_cache_filename(bucket), "wb")
        try:
            bucket.write_bytecode(f)
        finally:
            f.close()
